"""Public plane: the website and the downloads. Nothing here is private; it is static content on a CDN."""
from pathlib import Path

from aws_cdk import CfnOutput, Duration, RemovalPolicy, Stack
from aws_cdk import aws_certificatemanager as acm
from aws_cdk import aws_cloudfront as cf
from aws_cdk import aws_cloudfront_origins as origins
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_s3_deployment as deploy
from constructs import Construct

SITE_DIST = Path(__file__).resolve().parent.parent.parent / "site" / "dist"
# Same policy the local app uses: our own scripts only, no outside requests, no framing.
CSP = ("default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; font-src 'self' data:; "
       "connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")


def private_bucket(scope, id, **kw):
    return s3.Bucket(scope, id, block_public_access=s3.BlockPublicAccess.BLOCK_ALL, enforce_ssl=True,
                     encryption=s3.BucketEncryption.S3_MANAGED, removal_policy=RemovalPolicy.RETAIN,
                     object_ownership=s3.ObjectOwnership.BUCKET_OWNER_ENFORCED, **kw)


class PublicStack(Stack):
    def __init__(self, scope: Construct, id: str, **kw):
        super().__init__(scope, id, **kw)
        # Buckets are private: only CloudFront can read them, through Origin Access Control.
        site = private_bucket(self, "SiteBucket")
        downloads = private_bucket(self, "DownloadsBucket", versioned=True)  # installer, model weights

        headers = cf.ResponseHeadersPolicy(
            self, "SecurityHeaders",
            security_headers_behavior=cf.ResponseSecurityHeadersBehavior(
                content_security_policy=cf.ResponseHeadersContentSecurityPolicy(content_security_policy=CSP, override=True),
                strict_transport_security=cf.ResponseHeadersStrictTransportSecurity(
                    access_control_max_age=Duration.days(365), include_subdomains=True, preload=True, override=True),
                content_type_options=cf.ResponseHeadersContentTypeOptions(override=True),
                frame_options=cf.ResponseHeadersFrameOptions(frame_option=cf.HeadersFrameOption.DENY, override=True),
                referrer_policy=cf.ResponseHeadersReferrerPolicy(
                    referrer_policy=cf.HeadersReferrerPolicy.NO_REFERRER, override=True)))

        domain = self.node.try_get_context("domain_name")
        cert_arn = self.node.try_get_context("certificate_arn")  # must live in us-east-1 for CloudFront
        custom = {"domain_names": [domain], "certificate": acm.Certificate.from_certificate_arn(self, "Cert", cert_arn)} \
            if domain and cert_arn else {}

        dist = cf.Distribution(
            self, "Cdn", comment="Nyaya AI website and downloads",
            default_root_object="index.html", price_class=cf.PriceClass.PRICE_CLASS_200,  # includes India
            http_version=cf.HttpVersion.HTTP2_AND_3, minimum_protocol_version=cf.SecurityPolicyProtocol.TLS_V1_2_2021,
            default_behavior=cf.BehaviorOptions(
                origin=origins.S3BucketOrigin.with_origin_access_control(site),
                viewer_protocol_policy=cf.ViewerProtocolPolicy.REDIRECT_TO_HTTPS, compress=True,
                cache_policy=cf.CachePolicy.CACHING_OPTIMIZED, response_headers_policy=headers),
            additional_behaviors={"downloads/*": cf.BehaviorOptions(
                origin=origins.S3BucketOrigin.with_origin_access_control(downloads),
                viewer_protocol_policy=cf.ViewerProtocolPolicy.HTTPS_ONLY, compress=False,
                cache_policy=cf.CachePolicy.CACHING_OPTIMIZED, response_headers_policy=headers)},
            # Single-page app: unknown paths (and S3's 403 for missing keys) serve index.html so /faq works on refresh.
            error_responses=[cf.ErrorResponse(http_status=s, response_http_status=200, response_page_path="/index.html",
                                              ttl=Duration.seconds(0)) for s in (403, 404)],
            **custom)

        if SITE_DIST.is_dir():  # build first: cd site && npm run build
            deploy.BucketDeployment(self, "DeploySite", sources=[deploy.Source.asset(str(SITE_DIST))],
                                    destination_bucket=site, distribution=dist, distribution_paths=["/*"], prune=True)

        CfnOutput(self, "SiteUrl", value=f"https://{domain or dist.distribution_domain_name}")
        CfnOutput(self, "DistributionId", value=dist.distribution_id)
        CfnOutput(self, "DownloadsBucketName", value=downloads.bucket_name,
                  description="Upload installers and model weights under the downloads/ prefix")
