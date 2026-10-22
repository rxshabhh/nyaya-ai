"""Nyaya AI cloud vault API (AWS Lambda behind API Gateway HTTP API with a Cognito JWT authorizer).

Stores only encrypted case archives. File bytes never pass through this function: it hands out short-lived
presigned S3 URLs and keeps a tiny index (version, size, time) in DynamoDB. A user can only ever address
their own prefix, because the owner comes from the verified token (`sub`), never from the request.
"""
import json
import os
import re
import time
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key
from botocore.config import Config
from botocore.exceptions import ClientError

CASE = re.compile(r"[0-9a-f]{16}")
KEEP_VERSIONS = 3  # newest versions kept for rollback; older ones are pruned after each commit
_clients = {}


class Http(Exception):
    def __init__(self, status, message, **extra):
        super().__init__(message)
        self.status, self.extra = status, extra


def _env(name, default=None):
    return os.environ.get(name, default)


def _table():
    if "table" not in _clients:
        _clients["table"] = boto3.resource("dynamodb").Table(_env("TABLE"))
    return _clients["table"]


def _s3():
    if "s3" not in _clients:
        _clients["s3"] = boto3.client("s3", config=Config(signature_version="s3v4", s3={"addressing_style": "path"}))
    return _clients["s3"]


def _key(user, case, version):
    return f"{user}/{case}/{version}.nyaya"


def _json(v):
    if isinstance(v, Decimal):
        return int(v)
    raise TypeError(type(v))


def _reply(status, body):
    return {"statusCode": status, "headers": {"Content-Type": "application/json", "Cache-Control": "no-store"},
            "body": json.dumps(body, default=_json)}


def _current(user, case):
    item = _table().get_item(Key={"pk": user, "sk": case}).get("Item")
    return int(item["version"]) if item else 0, item


def list_cases(user, case, body, query):
    rows = _table().query(KeyConditionExpression=Key("pk").eq(user))["Items"]
    return 200, [{"id": r["sk"], "version": int(r["version"]), "size": int(r["size"]), "updated": r["updated"]}
                 for r in sorted(rows, key=lambda r: r["updated"], reverse=True)]


def push(user, case, body, query):
    base, size = body.get("base_version"), body.get("size")
    if not isinstance(base, int) or not isinstance(size, int) or isinstance(base, bool) or isinstance(size, bool):
        raise Http(422, "base_version and size must be integers")
    if not 0 < size <= int(_env("MAX_BYTES", 1024 ** 3)):
        raise Http(413, "archive is empty or larger than the allowed size")
    current, _ = _current(user, case)
    if base != current:
        raise Http(409, f"The cloud has a newer version (v{current}). Download it first.", current=current)
    new = current + 1
    url = _s3().generate_presigned_url(
        "put_object", HttpMethod="PUT", ExpiresIn=int(_env("URL_TTL", 300)),
        Params={"Bucket": _env("BUCKET"), "Key": _key(user, case, new), "ContentLength": size,
                "ContentType": "application/octet-stream"})
    return 200, {"version": new, "url": url}


def commit(user, case, body, query):
    version = body.get("version")
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        raise Http(422, "version must be a positive integer")
    current, _ = _current(user, case)
    if version != current + 1:
        raise Http(409, f"The cloud is at v{current}; start the upload again.", current=current)
    try:
        size = _s3().head_object(Bucket=_env("BUCKET"), Key=_key(user, case, version))["ContentLength"]
    except ClientError:
        raise Http(409, "The upload did not arrive. Try again.")
    try:
        _table().update_item(
            Key={"pk": user, "sk": case},
            UpdateExpression="SET #v = :v, #s = :s, #u = :u",  # aliased: "size" is a DynamoDB reserved word
            ExpressionAttributeNames={"#v": "version", "#s": "size", "#u": "updated"},
            ConditionExpression="attribute_not_exists(pk)" if current == 0 else "#v = :cur",
            ExpressionAttributeValues={":v": version, ":s": size, ":u": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                                       **({} if current == 0 else {":cur": current})})
    except ClientError as e:  # two devices committed at once: only one wins
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise Http(409, "Another device uploaded at the same time. Download its version first.")
        raise
    if version > KEEP_VERSIONS:
        try:
            _s3().delete_object(Bucket=_env("BUCKET"), Key=_key(user, case, version - KEEP_VERSIONS))
        except ClientError:
            pass  # pruning is best effort; the lifecycle rule still expires old versions
    return 200, {"version": version}


def pull(user, case, body, query):
    current, _ = _current(user, case)
    if not current:
        raise Http(404, "No such case in the cloud.")
    try:
        version = int(query.get("version") or current)
    except ValueError:
        raise Http(422, "version must be a number")
    if not max(1, current - KEEP_VERSIONS + 1) <= version <= current:
        raise Http(404, f"Only the newest {KEEP_VERSIONS} versions are kept (v{current} is the latest).")
    url = _s3().generate_presigned_url("get_object", ExpiresIn=int(_env("URL_TTL", 300)),
                                       Params={"Bucket": _env("BUCKET"), "Key": _key(user, case, version)})
    return 200, {"version": version, "latest": current, "url": url}


def delete(user, case, body, query):
    _table().delete_item(Key={"pk": user, "sk": case})
    paginator = _s3().get_paginator("list_object_versions")
    for page in paginator.paginate(Bucket=_env("BUCKET"), Prefix=f"{user}/{case}/"):
        objs = [{"Key": o["Key"], "VersionId": o["VersionId"]} for o in page.get("Versions", []) + page.get("DeleteMarkers", [])]
        if objs:
            _s3().delete_objects(Bucket=_env("BUCKET"), Delete={"Objects": objs, "Quiet": True})
    return 200, {"deleted": True}


ROUTES = {
    "GET /cases": list_cases,
    "POST /cases/{caseId}/push": push,
    "POST /cases/{caseId}/commit": commit,
    "GET /cases/{caseId}/pull": pull,
    "DELETE /cases/{caseId}": delete,
}


def handler(event, context=None):
    route = event.get("routeKey")
    user = None
    try:
        user = ((event.get("requestContext") or {}).get("authorizer") or {}).get("jwt", {}).get("claims", {}).get("sub")
        if not user or not re.fullmatch(r"[\w-]{8,64}", user):
            raise Http(401, "Not signed in.")
        fn = ROUTES.get(route)
        if not fn:
            raise Http(404, "Not found.")
        case = (event.get("pathParameters") or {}).get("caseId")
        if case is not None and not CASE.fullmatch(case):
            raise Http(400, "Bad case id.")
        try:
            body = json.loads(event.get("body") or "{}")
        except ValueError:
            raise Http(400, "Body must be JSON.")
        if not isinstance(body, dict):
            raise Http(400, "Body must be a JSON object.")
        status, out = fn(user, case, body, event.get("queryStringParameters") or {})
    except Http as e:
        status, out = e.status, {"message": str(e), **e.extra}
    except Exception as e:  # never leak internals to the caller; the type is enough to find it in the logs
        status, out = 500, {"message": "Something went wrong in the cloud service."}
        print(json.dumps({"route": route, "error": type(e).__name__}))
    print(json.dumps({"route": route, "status": status, "user": user}))  # no bodies, names or URLs in logs
    return _reply(status, out)
