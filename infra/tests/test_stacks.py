# Security properties of the synthesized CloudFormation, checked offline (no AWS account needed).
# Run: infra/.venv/Scripts/python infra/tests/test_stacks.py
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import aws_cdk as cdk
from aws_cdk.assertions import Template

from stacks.private import PrivateStack
from stacks.public import PublicStack

env = cdk.Environment(account="111111111111", region="ap-south-1")
private = Template.from_stack(PrivateStack(cdk.App(), "P", env=env)).to_json()["Resources"]  # one App per stack:
public = Template.from_stack(PublicStack(cdk.App(), "W", env=env)).to_json()["Resources"]   # synthesis is one-shot


def of(resources, type_):
    return {k: v for k, v in resources.items() if v["Type"] == type_}


def statements(resources):
    for r in of(resources, "AWS::IAM::Policy").values():
        yield from r["Properties"]["PolicyDocument"]["Statement"]
    for r in of(resources, "AWS::S3::BucketPolicy").values():
        yield from r["Properties"]["PolicyDocument"]["Statement"]


def as_list(x):
    return x if isinstance(x, list) else [x]


for name, res in (("private", private), ("public", public)):
    # every bucket: all public access blocked, TLS enforced, encrypted
    buckets = of(res, "AWS::S3::Bucket")
    assert buckets, name
    for k, b in buckets.items():
        p = b["Properties"]
        assert all(p["PublicAccessBlockConfiguration"].values()) and len(p["PublicAccessBlockConfiguration"]) == 4, k
        assert p["BucketEncryption"]["ServerSideEncryptionConfiguration"], k
        assert b.get("DeletionPolicy") == "Retain", f"{k} would be deleted with the stack"
    denies_http = sum(1 for s in statements(res) if s.get("Effect") == "Deny" and
                      json.dumps(s.get("Condition", {})).find('"aws:SecureTransport": "false"') >= 0)
    assert denies_http >= len(buckets), f"{name}: a bucket allows plain http"
    # nothing is granted to everyone, and no IAM statement uses a wildcard action
    for s in statements(res):
        if s["Effect"] == "Allow":
            assert s.get("Principal") != "*" and s.get("Principal") != {"AWS": "*"}, s
            assert "*" not in as_list(s["Action"]), s

# ---- private plane ----
vault = next(b["Properties"] for b in of(private, "AWS::S3::Bucket").values() if "VersioningConfiguration" in b["Properties"]
             and b["Properties"]["BucketEncryption"]["ServerSideEncryptionConfiguration"][0]["ServerSideEncryptionByDefault"]["SSEAlgorithm"] == "aws:kms")
assert vault["VersioningConfiguration"]["Status"] == "Enabled"
assert [k for k in of(private, "AWS::KMS::Key").values()][0]["Properties"]["EnableKeyRotation"] is True

table = next(iter(of(private, "AWS::DynamoDB::Table").values()))["Properties"]
assert table["PointInTimeRecoverySpecification"]["PointInTimeRecoveryEnabled"] is True
assert table["SSESpecification"]["SSEEnabled"] is True and table["SSESpecification"]["SSEType"] == "KMS"
assert table["DeletionProtectionEnabled"] is True and table["BillingMode"] == "PAY_PER_REQUEST"

pool = next(iter(of(private, "AWS::Cognito::UserPool").values()))["Properties"]
assert pool["MfaConfiguration"] == "ON" and pool["EnabledMfas"] == ["SOFTWARE_TOKEN_MFA"]
assert pool["AdminCreateUserConfig"]["AllowAdminCreateUserOnly"] is True  # no self sign-up
assert pool["Policies"]["PasswordPolicy"]["MinimumLength"] >= 12
client = next(iter(of(private, "AWS::Cognito::UserPoolClient").values()))["Properties"]
assert client["GenerateSecret"] is False and client["PreventUserExistenceErrors"] == "ENABLED"
assert client["ExplicitAuthFlows"] == ["ALLOW_USER_PASSWORD_AUTH", "ALLOW_REFRESH_TOKEN_AUTH"]

routes = of(private, "AWS::ApiGatewayV2::Route")
assert sorted(r["Properties"]["RouteKey"] for r in routes.values()) == [
    "DELETE /cases/{caseId}", "GET /cases", "GET /cases/{caseId}/pull", "POST /cases/{caseId}/commit", "POST /cases/{caseId}/push"]
assert all(r["Properties"]["AuthorizationType"] == "JWT" for r in routes.values()), "a route is open to anonymous callers"
stage = next(iter(of(private, "AWS::ApiGatewayV2::Stage").values()))["Properties"]
assert stage["DefaultRouteSettings"]["ThrottlingRateLimit"] > 0 and "AccessLogSettings" in stage

fn = next(r["Properties"] for r in of(private, "AWS::Lambda::Function").values() if r["Properties"].get("Handler") == "handler.handler")
assert fn["Runtime"] == "python3.12" and fn["Architectures"] == ["arm64"] and fn["TracingConfig"]["Mode"] == "Active"
assert {"TABLE", "BUCKET", "URL_TTL", "MAX_BYTES"} <= set(fn["Environment"]["Variables"])
trail = next(iter(of(private, "AWS::CloudTrail::Trail").values()))["Properties"]
assert trail["EnableLogFileValidation"] is True and trail["EventSelectors"][0]["DataResources"][0]["Type"] == "AWS::S3::Object"
assert len(of(private, "AWS::CloudWatch::Alarm")) == 3

# ---- public plane ----
dist = next(iter(of(public, "AWS::CloudFront::Distribution").values()))["Properties"]["DistributionConfig"]
assert dist["DefaultCacheBehavior"]["ViewerProtocolPolicy"] == "redirect-to-https"
assert dist["CacheBehaviors"][0]["ViewerProtocolPolicy"] == "https-only"
assert dist["HttpVersion"] == "http2and3" and "ViewerCertificate" not in dist  # default *.cloudfront.net cert: AWS cannot enforce TLS 1.2 here
custom = Template.from_stack(PublicStack(cdk.App(context={"domain_name": "nyaya.example.in", "certificate_arn":
    "arn:aws:acm:us-east-1:111111111111:certificate/00000000-0000-0000-0000-000000000000"}), "C", env=env)).to_json()["Resources"]
cdist = next(iter(of(custom, "AWS::CloudFront::Distribution").values()))["Properties"]["DistributionConfig"]
assert cdist["ViewerCertificate"]["MinimumProtocolVersion"] == "TLSv1.2_2021" and cdist["Aliases"] == ["nyaya.example.in"]
assert {e["ErrorCode"] for e in dist["CustomErrorResponses"]} == {403, 404}  # single-page app routing
headers = next(iter(of(public, "AWS::CloudFront::ResponseHeadersPolicy").values()))["Properties"]["ResponseHeadersPolicyConfig"]["SecurityHeadersConfig"]
assert {"ContentSecurityPolicy", "StrictTransportSecurity", "FrameOptions", "ContentTypeOptions", "ReferrerPolicy"} <= set(headers)
assert len(of(public, "AWS::CloudFront::OriginAccessControl")) == 2  # buckets readable only through the CDN

print("ok")
