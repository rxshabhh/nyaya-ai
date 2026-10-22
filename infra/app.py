#!/usr/bin/env python3
"""CDK app. Two independent stacks: the public website and the private encrypted vault.
Synthesize without an AWS account:  python app.py   (writes cdk.out/)
Deploy:                             see docs/aws/DEPLOY.md"""
import os

import aws_cdk as cdk

from stacks.private import PrivateStack
from stacks.public import PublicStack

app = cdk.App()
# Mumbai keeps case data in India (DPDP Act and client expectations). Override: -c region=...
env = cdk.Environment(account=os.environ.get("CDK_DEFAULT_ACCOUNT"), region=app.node.try_get_context("region") or "ap-south-1")
PublicStack(app, "NyayaPublic", env=env, description="Nyaya AI website and downloads (static, CDN)")
PrivateStack(app, "NyayaPrivate", env=env, description="Nyaya AI encrypted case vault, sign-in and sync API")
cdk.Tags.of(app).add("project", "nyaya-ai")
app.synth()
