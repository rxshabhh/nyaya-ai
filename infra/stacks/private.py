"""Private plane: encrypted case sync for signed-in advocates. The cloud stores ciphertext only; the app
encrypts on the laptop with a key AWS never sees. KMS, S3 and DynamoDB encryption are extra layers, not the
primary protection."""
from pathlib import Path

from aws_cdk import CfnOutput, Duration, RemovalPolicy, Stack
from aws_cdk import aws_apigatewayv2 as apigw
from aws_cdk import aws_apigatewayv2_authorizers as authorizers
from aws_cdk import aws_apigatewayv2_integrations as integrations
from aws_cdk import aws_cloudtrail as cloudtrail
from aws_cdk import aws_cloudwatch as cw
from aws_cdk import aws_cloudwatch_actions as cw_actions
from aws_cdk import aws_cognito as cognito
from aws_cdk import aws_dynamodb as ddb
from aws_cdk import aws_kms as kms
from aws_cdk import aws_lambda as _lambda
from aws_cdk import aws_logs as logs
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_sns as sns
from aws_cdk import aws_sns_subscriptions as subs
from constructs import Construct

LAMBDA_DIR = Path(__file__).resolve().parent.parent / "lambda"
ACCESS_LOG = ('{"requestId":"$context.requestId","ip":"$context.identity.sourceIp","route":"$context.routeKey",'
              '"status":"$context.status","user":"$context.authorizer.claims.sub","responseLength":"$context.responseLength",'
              '"error":"$context.integrationErrorMessage"}')
ROUTES = [  # (method, path): every one sits behind the Cognito JWT authorizer
    (apigw.HttpMethod.GET, "/cases"),
    (apigw.HttpMethod.POST, "/cases/{caseId}/push"),
    (apigw.HttpMethod.POST, "/cases/{caseId}/commit"),
    (apigw.HttpMethod.GET, "/cases/{caseId}/pull"),
    (apigw.HttpMethod.DELETE, "/cases/{caseId}"),
]


class PrivateStack(Stack):
    def __init__(self, scope: Construct, id: str, **kw):
        super().__init__(scope, id, **kw)
        ctx = self.node.try_get_context
        keep = RemovalPolicy.RETAIN  # case data and identities outlive a stack deletion by default

        # ---- encryption key (customer managed, rotated yearly) ----
        key = kms.Key(self, "VaultKey", alias="alias/nyaya-vault", enable_key_rotation=True, removal_policy=keep,
                      description="Encrypts the Nyaya AI vault bucket and case index")

        # ---- storage ----
        vault = s3.Bucket(
            self, "VaultBucket", encryption=s3.BucketEncryption.KMS, encryption_key=key, bucket_key_enabled=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL, enforce_ssl=True, versioned=True,
            object_ownership=s3.ObjectOwnership.BUCKET_OWNER_ENFORCED, removal_policy=keep,
            lifecycle_rules=[s3.LifecycleRule(noncurrent_version_expiration=Duration.days(30),
                                              abort_incomplete_multipart_upload_after=Duration.days(7))])
        table = ddb.Table(
            self, "CasesTable", partition_key=ddb.Attribute(name="pk", type=ddb.AttributeType.STRING),  # user id
            sort_key=ddb.Attribute(name="sk", type=ddb.AttributeType.STRING),  # case id
            billing_mode=ddb.BillingMode.PAY_PER_REQUEST, encryption=ddb.TableEncryption.CUSTOMER_MANAGED,
            encryption_key=key, point_in_time_recovery_specification=ddb.PointInTimeRecoverySpecification(
                point_in_time_recovery_enabled=True), deletion_protection=True, removal_policy=keep)

        # ---- identity: invited users only, MFA always ----
        pool = cognito.UserPool(
            self, "Users", user_pool_name="nyaya-ai-advocates", self_sign_up_enabled=False,
            sign_in_aliases=cognito.SignInAliases(email=True), auto_verify=cognito.AutoVerifiedAttrs(email=True),
            mfa=cognito.Mfa.REQUIRED, mfa_second_factor=cognito.MfaSecondFactor(otp=True, sms=False),
            password_policy=cognito.PasswordPolicy(min_length=12, require_lowercase=True, require_uppercase=True,
                                                   require_digits=True, require_symbols=True,
                                                   temp_password_validity=Duration.days(3)),
            account_recovery=cognito.AccountRecovery.NONE,  # an administrator resets accounts
            deletion_protection=True, removal_policy=keep)
        client = pool.add_client(
            "DesktopApp", generate_secret=False, prevent_user_existence_errors=True, enable_token_revocation=True,
            auth_flows=cognito.AuthFlow(user_password=True),
            id_token_validity=Duration.hours(1), access_token_validity=Duration.hours(1),
            refresh_token_validity=Duration.days(30))

        # ---- API: one small Lambda behind an HTTP API ----
        fn = _lambda.Function(
            self, "VaultApi", runtime=_lambda.Runtime.PYTHON_3_12, architecture=_lambda.Architecture.ARM_64,
            handler="handler.handler", code=_lambda.Code.from_asset(str(LAMBDA_DIR)), memory_size=256,
            timeout=Duration.seconds(10), tracing=_lambda.Tracing.ACTIVE,
            log_group=logs.LogGroup(self, "ApiLogs", retention=logs.RetentionDays.THREE_MONTHS, removal_policy=keep),
            environment={"TABLE": table.table_name, "BUCKET": vault.bucket_name, "URL_TTL": "300",
                         "MAX_BYTES": str(1024 ** 3)})
        vault.grant_read_write(fn)   # includes the KMS permissions needed to sign and serve encrypted objects
        vault.grant_delete(fn)       # delete a case's object versions
        table.grant_read_write_data(fn)

        api = apigw.HttpApi(self, "Api", api_name="nyaya-vault")
        authorizer = authorizers.HttpJwtAuthorizer(
            "Cognito", f"https://cognito-idp.{self.region}.amazonaws.com/{pool.user_pool_id}",
            jwt_audience=[client.user_pool_client_id])
        integration = integrations.HttpLambdaIntegration("VaultIntegration", fn)
        for method, path in ROUTES:
            api.add_routes(path=path, methods=[method], integration=integration, authorizer=authorizer)
        stage = api.default_stage
        access_logs = logs.LogGroup(self, "AccessLogs", retention=logs.RetentionDays.THREE_MONTHS, removal_policy=keep)
        cfn_stage = stage.node.default_child
        cfn_stage.add_property_override("DefaultRouteSettings", {"ThrottlingRateLimit": 20, "ThrottlingBurstLimit": 40})
        cfn_stage.add_property_override("AccessLogSettings", {"DestinationArn": access_logs.log_group_arn, "Format": ACCESS_LOG})

        # ---- audit and alarms ----
        if ctx("enable_cloudtrail") != "false":
            trail_logs = s3.Bucket(
                self, "AuditBucket", block_public_access=s3.BlockPublicAccess.BLOCK_ALL, enforce_ssl=True,
                encryption=s3.BucketEncryption.S3_MANAGED, removal_policy=keep,
                lifecycle_rules=[s3.LifecycleRule(expiration=Duration.days(365))])
            trail = cloudtrail.Trail(self, "Audit", bucket=trail_logs, enable_file_validation=True)
            trail.add_s3_event_selector([cloudtrail.S3EventSelector(bucket=vault)],
                                        read_write_type=cloudtrail.ReadWriteType.ALL)  # who touched which object

        topic = sns.Topic(self, "Alarms", enforce_ssl=True)
        if ctx("alarm_email"):
            topic.add_subscription(subs.EmailSubscription(ctx("alarm_email")))
        for name, metric in (("LambdaErrors", fn.metric_errors(period=Duration.minutes(5))),
                             ("LambdaThrottles", fn.metric_throttles(period=Duration.minutes(5))),
                             ("Api5xx", api.metric_server_error(period=Duration.minutes(5)))):
            cw.Alarm(self, name, metric=metric, threshold=1, evaluation_periods=1,
                     comparison_operator=cw.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
                     treat_missing_data=cw.TreatMissingData.NOT_BREACHING).add_alarm_action(cw_actions.SnsAction(topic))

        # ---- values the desktop app asks for (Settings > Cloud) ----
        CfnOutput(self, "ApiUrl", value=api.api_endpoint)
        CfnOutput(self, "Region", value=self.region)
        CfnOutput(self, "UserPoolId", value=pool.user_pool_id)
        CfnOutput(self, "ClientId", value=client.user_pool_client_id)
        CfnOutput(self, "VaultBucketName", value=vault.bucket_name)
