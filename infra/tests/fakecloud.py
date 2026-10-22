"""A local stand-in for the AWS side of Nyaya AI, so cloud sync can be tested and demoed with no AWS account.

Runs the real Lambda code (infra/lambda/handler.py) against moto (fake S3 and DynamoDB), behind a fake API Gateway
(JWT check + Lambda proxy) and a fake Cognito (password, then TOTP; first-login users enrol an authenticator).

Demo:  infra/.venv/Scripts/python infra/tests/fakecloud.py     (prints the three values the app asks for)
Sign in with  alice@example.com / pw-alice  and the code 123456.
"""
import json
import os
import re
import socket
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qsl, urlparse

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "infra" / "lambda"))
sys.path.insert(0, str(ROOT))

import handler  # noqa: E402  (the real Lambda, infra/lambda/handler.py)

ROUTES = [("GET", r"/cases", "GET /cases"), ("POST", r"/cases/([^/]+)/push", "POST /cases/{caseId}/push"),
          ("POST", r"/cases/([^/]+)/commit", "POST /cases/{caseId}/commit"), ("GET", r"/cases/([^/]+)/pull", "GET /cases/{caseId}/pull"),
          ("DELETE", r"/cases/([^/]+)", "DELETE /cases/{caseId}")]
USERS = {"alice@example.com": ("pw-alice", "SOFTWARE_TOKEN_MFA"), "bob@example.com": ("pw-bob", "MFA_SETUP"), "mallory@example.com": ("pw-mallory", "SOFTWARE_TOKEN_MFA")}
CODE, SECRET = "123456", "JBSWY3DPEHPK3PXP"
EXPIRES = {"seconds": 3600}


class Fake(BaseHTTPRequestHandler):
    """API Gateway (JWT authorizer + Lambda proxy) at /api and Cognito at /cognito."""
    def log_message(self, *a):
        pass

    def send(self, status, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def body(self):
        return self.rfile.read(int(self.headers.get("Content-Length") or 0))

    def do_POST(self):
        self.route()

    do_GET = do_DELETE = do_POST

    def route(self):
        url = urlparse(self.path)
        raw = self.body()
        if url.path == "/cognito":
            return self.cognito(json.loads(raw))
        m = re.fullmatch(r"/api(/.*)", url.path)
        auth = self.headers.get("Authorization", "")
        if not m or not auth.startswith("Bearer user:"):
            return self.send(401, {"message": "Unauthorized"})
        for method, pattern, key in ROUTES:
            mm = re.fullmatch(pattern, m.group(1))
            if mm and method == self.command:
                user = auth.removeprefix("Bearer user:")
                event = {"routeKey": key, "pathParameters": {"caseId": mm.group(1)} if mm.groups() else None,
                         "queryStringParameters": dict(parse_qsl(url.query)) or None, "body": raw.decode() or None,
                         "requestContext": {"authorizer": {"jwt": {"claims": {"sub": f"sub-{user.split('@')[0]}-00000000"}}}}}
                out = handler.handler(event)
                return self.send(out["statusCode"], out["body"].encode())
        self.send(404, {"message": "Not Found"})

    def cognito(self, b):
        target = self.headers["X-Amz-Target"].split(".")[-1]
        err = lambda t: self.send(400, {"__type": t, "message": "x"})
        ok = lambda: {"AuthenticationResult": {"IdToken": f"user:{b['_user']}", "RefreshToken": "refresh", "ExpiresIn": EXPIRES["seconds"]}}
        if target == "InitiateAuth" and b["AuthFlow"] == "USER_PASSWORD_AUTH":
            u, p = b["AuthParameters"]["USERNAME"], b["AuthParameters"]["PASSWORD"]
            if u not in USERS or USERS[u][0] != p:
                return err("NotAuthorizedException")
            return self.send(200, {"ChallengeName": USERS[u][1], "Session": f"sess-{u}"})
        if target == "InitiateAuth" and b["AuthFlow"] == "REFRESH_TOKEN_AUTH":
            return self.send(200, {"AuthenticationResult": {"IdToken": "user:alice", "ExpiresIn": 3600}})
        if target == "AssociateSoftwareToken":
            return self.send(200, {"SecretCode": SECRET, "Session": b["Session"] + "-a"})
        if target == "VerifySoftwareToken":
            return self.send(200, {"Status": "SUCCESS" if b["UserCode"] == CODE else "ERROR", "Session": b["Session"] + "-v"})
        if target == "RespondToAuthChallenge":
            r = b["ChallengeResponses"]
            if b["ChallengeName"] == "SOFTWARE_TOKEN_MFA" and r["SOFTWARE_TOKEN_MFA_CODE"] != CODE:
                return err("CodeMismatchException")
            return self.send(200, {"AuthenticationResult": {"IdToken": f"user:{r['USERNAME']}", "RefreshToken": "refresh", "ExpiresIn": EXPIRES["seconds"]}})
        err("InvalidParameterException")



def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def start(moto_port=None, api_port=None):
    """Start everything; returns an object with .cfg (what the app is configured with), .cognito and .stop()."""
    moto_port, api_port = moto_port or free_port(), api_port or free_port()
    os.environ.update(AWS_ENDPOINT_URL=f"http://127.0.0.1:{moto_port}", AWS_ACCESS_KEY_ID="test", AWS_SECRET_ACCESS_KEY="test",
                      AWS_DEFAULT_REGION="ap-south-1", TABLE="nyaya-cases", BUCKET="nyaya-vault", URL_TTL="300")
    import boto3
    from moto.server import ThreadedMotoServer
    moto = ThreadedMotoServer(port=moto_port, verbose=False)
    moto.start()
    s3, ddb = boto3.client("s3"), boto3.client("dynamodb")
    s3.create_bucket(Bucket="nyaya-vault", CreateBucketConfiguration={"LocationConstraint": "ap-south-1"})
    s3.put_bucket_versioning(Bucket="nyaya-vault", VersioningConfiguration={"Status": "Enabled"})
    ddb.create_table(TableName="nyaya-cases", BillingMode="PAY_PER_REQUEST",
                     AttributeDefinitions=[{"AttributeName": "pk", "AttributeType": "S"}, {"AttributeName": "sk", "AttributeType": "S"}],
                     KeySchema=[{"AttributeName": "pk", "KeyType": "HASH"}, {"AttributeName": "sk", "KeyType": "RANGE"}])
    api = ThreadingHTTPServer(("127.0.0.1", api_port), Fake)
    threading.Thread(target=api.serve_forever, daemon=True).start()

    def stop():
        api.shutdown()
        moto.stop()
    return SimpleNamespace(cfg={"api_url": f"http://127.0.0.1:{api_port}/api", "region": "ap-south-1", "client_id": "abcdefghij1234567890"},
                           cognito=f"http://127.0.0.1:{api_port}/cognito", s3=s3, ddb=ddb, stop=stop)


if __name__ == "__main__":
    fc = start(moto_port=8798, api_port=8799)  # fixed ports so inspect_cloud.py can find the fake S3
    print("Fake AWS is running. In the app, Cloud sync > set up with:")
    print("  API address :", fc.cfg["api_url"])
    print("  Region      :", fc.cfg["region"])
    print("  App client  :", fc.cfg["client_id"])
    print("Sign in: alice@example.com / pw-alice, code 123456  (bob@example.com / pw-bob enrols the authenticator on first sign-in)")
    print("The app must be started with:  NYAYA_COGNITO_ENDPOINT=" + fc.cognito)
    print(r"To see what the cloud stores:  infra\.venv\Scripts\python infra\tests\inspect_cloud.py")
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        fc.stop()
