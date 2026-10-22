# End-to-end check of cloud sync with no AWS account: the real Lambda code runs against moto (a local fake of
# S3 and DynamoDB), behind a fake API Gateway and Cognito (infra/tests/fakecloud.py), driven by the real client
# in nyaya/cloud.py and by the real local app API.
# Run: infra/.venv/Scripts/python infra/tests/test_cloud.py
import json
import sys
import tempfile
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import fakecloud as fc  # noqa: E402  (sets up sys.path and the AWS environment)
from fakecloud import CODE, EXPIRES, SECRET, USERS  # noqa: E402

import handler  # noqa: E402
from nyaya.archive import digest, read_archive, write_archive  # noqa: E402
from nyaya.cloud import Cloud, CloudError  # noqa: E402
from nyaya.vault import Vault  # noqa: E402

FAST = {"time": 1, "memory_kib": 1024, "parallelism": 1}
PASS = "correct horse battery"
cloud_stack = fc.start()
CFG, COGNITO, s3, ddb = cloud_stack.cfg, cloud_stack.cognito, cloud_stack.s3, cloud_stack.ddb
API_PORT = int(CFG["api_url"].split(":")[2].split("/")[0])
ALICE, MALLORY, BOB = "alice@example.com", "mallory@example.com", "bob@example.com"

def signed_in(user):
    c = Cloud(CFG, cognito_endpoint=f"http://127.0.0.1:{API_PORT}/cognito")
    assert c.login(user, USERS[user][0])["state"] == "mfa"
    assert c.submit_code(CODE)["state"] == "ok"
    return c


def expect(status, fn, *a):
    try:
        fn(*a)
    except CloudError as e:
        assert e.status == status, (e.status, str(e))
        return str(e)
    raise AssertionError(f"expected CloudError {status}")



try:
    # ---- sign-in: wrong password, MFA, first-login MFA enrolment, wrong code ----
    c = Cloud(CFG, cognito_endpoint=f"http://127.0.0.1:{API_PORT}/cognito")
    assert "Wrong username" in expect(401, c.login, ALICE, "nope")
    assert c.login(ALICE, "pw-alice") == {"state": "mfa"} and not c.signed_in
    assert "code is wrong" in expect(401, c.submit_code, "000000")
    assert c.submit_code(CODE) == {"state": "ok"} and c.signed_in
    c2 = Cloud(CFG, cognito_endpoint=c.cognito)
    setup = c2.login(BOB, "pw-bob")
    assert setup["state"] == "mfa_setup" and setup["secret"] == SECRET and setup["uri"].startswith("otpauth://totp/NyayaAI:bob%40example.com")
    expect(401, c2.submit_code, "000000")
    assert c2.submit_code(CODE) == {"state": "ok"} and c2.signed_in
    expect(401, Cloud(CFG, cognito_endpoint=c.cognito).list_cases)  # not signed in
    expect(400, Cloud, {**CFG, "api_url": "http://example.com/api"})  # never plain http to a real host
    expect(422, Cloud, {**CFG, "region": "mars"})

    # ---- a real vault, pushed as ciphertext ----
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        vault_dir = tmp / "case"
        vault = Vault.create(vault_dir, PASS, FAST)
        vault.add_document("PW1.txt", b"[page 1]\n\nSuresh took Rs. 5,000 from the cash box.", {"witness": "Ramesh", "kind": "earlier", "date": "13.03.2021"})
        case = "0123456789abcdef"
        arc = tmp / "a.nyaya"
        write_archive(vault_dir, arc)
        d1 = digest(vault_dir)

        assert c.push(case, arc, 0) == 1
        assert [(x["id"], x["version"]) for x in c.list_cases()] == [(case, 1)]
        vault.add_document("PW2.txt", b"[page 1]\n\nMani saw the accused running away.", {"witness": "Mani", "kind": "earlier", "date": "13.03.2021"})
        write_archive(vault_dir, arc)
        assert digest(vault_dir) != d1  # local change is detectable
        assert c.push(case, arc, 1) == 2
        assert "newer version" in expect(409, c.push, case, arc, 1)  # stale base: someone else pushed first

        # the cloud holds ciphertext only: no plaintext anywhere in S3 or DynamoDB
        objs = [o["Key"] for o in s3.list_objects_v2(Bucket="nyaya-vault")["Contents"]]
        assert objs == [f"sub-alice-00000000/{case}/1.nyaya", f"sub-alice-00000000/{case}/2.nyaya"], objs
        import zipfile
        for k in objs:
            z = zipfile.ZipFile(__import__("io").BytesIO(s3.get_object(Bucket="nyaya-vault", Key=k)["Body"].read()))
            assert not any(b"Suresh" in z.read(n) or b"Ramesh" in z.read(n) for n in z.namelist())
        assert b"Suresh" not in json.dumps(ddb.scan(TableName="nyaya-cases")["Items"]).encode()

        # ---- restore on a "new laptop" and open with the passphrase ----
        got = tmp / "pulled.nyaya"
        assert c.pull(case, got) == 2
        restored = tmp / "restored"
        with open(got, "rb") as f:
            read_archive(f, restored)
        assert digest(restored) == digest(vault_dir)
        assert len(Vault.open(restored, PASS).documents()) == 2
        try:
            Vault.open(restored, "wrong passphrase")
            raise AssertionError("wrong passphrase opened the vault")
        except Exception as e:
            assert "passphrase" in str(e).lower()

        # ---- isolation: another user cannot see, pull, or overwrite alice's case ----
        m = signed_in(MALLORY)
        assert m.list_cases() == []
        expect(404, m.pull, case, tmp / "x")
        assert m.push(case, arc, 0) == 1  # same case id, separate namespace
        assert sorted(x["Key"] for x in s3.list_objects_v2(Bucket="nyaya-vault", Prefix="sub-alice")["Contents"]) == objs[:2]

        # ---- only the newest versions are kept ----
        for base in (2, 3, 4):
            assert c.push(case, arc, base) == base + 1
        assert c.pull(case, tmp / "v3", version=3) == 3
        expect(404, c.pull, case, tmp / "v2", 2)  # v2 pruned after v5

        # ---- token refresh, then delete removes every object version ----
        EXPIRES["seconds"] = 1
        c.expires = 0  # force a refresh on the next call
        assert [x["version"] for x in c.list_cases()] == [5]
        c.delete(case)
        assert c.list_cases() == []
        left = s3.list_object_versions(Bucket="nyaya-vault", Prefix="sub-alice")
        assert not left.get("Versions") and not left.get("DeleteMarkers"), left
        assert len(m.list_cases()) == 1  # mallory untouched

    # ---- two laptops through the real local app API ----
    from fastapi.testclient import TestClient

    from nyaya.api import create_app

    H = {"X-Nyaya-Token": "t"}
    make = lambda d: TestClient(create_app(d, "t", kdf=FAST, embed_factory=lambda: None,
                                           cloud_factory=lambda cfg: Cloud(cfg, cognito_endpoint=f"http://127.0.0.1:{API_PORT}/cognito")),
                                base_url="http://127.0.0.1:8765")
    add = lambda cl, cid, name, text: cl.post(f"/api/cases/{cid}/documents", headers=H, data={"witness": "Ramesh", "doctype": "police_statement", "date": "13.03.2021"},
                                              files={"file": (name, text)})
    with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
        one, two = make(d1), make(d2)
        assert one.get("/api/cloud", headers=H).json()["configured"] is False
        assert one.post("/api/cloud/login", headers=H, json={"username": ALICE, "password": "pw-alice"}).status_code == 409  # not set up
        assert one.put("/api/cloud/config", headers=H, json={**CFG, "region": "mars"}).status_code == 422
        assert one.put("/api/cloud/config", headers=H, json={**CFG, "api_url": "http://example.com"}).status_code == 400
        for cl in (one, two):
            assert cl.put("/api/cloud/config", headers=H, json=CFG).json()["configured"]
            assert cl.post("/api/cloud/login", headers=H, json={"username": ALICE, "password": "pw-alice"}).json() == {"state": "mfa"}
            assert cl.post("/api/cloud/mfa", headers=H, json={"code": "000000"}).status_code == 401
            assert cl.post("/api/cloud/mfa", headers=H, json={"code": CODE}).json() == {"state": "ok"}
            assert cl.get("/api/cloud", headers=H).json()["signed_in"]
        assert "token" not in json.dumps(one.get("/api/cloud", headers=H).json()).lower()  # no secrets in status
        assert not any("id_token" in p.read_text() for p in Path(d1).rglob("cloud.json"))  # tokens never on disk

        cid = one.post("/api/cases", headers=H, json={"label": "SC-114", "passphrase": PASS}).json()["id"]
        assert add(one, cid, "a.txt", b"[page 1]\n\nSuresh took Rs. 5,000.").status_code == 201
        assert one.get(f"/api/cases/{cid}/cloud", headers=H).json() == {"version": None, "dirty": True}
        assert one.post(f"/api/cases/{cid}/cloud/push", headers=H).json() == {"version": 1}
        assert one.get(f"/api/cases/{cid}/cloud", headers=H).json() == {"version": 1, "dirty": False}
        seen = one.get(f"/api/cases/{cid}/cloud/inspect", headers=H).json()  # the in-app proof
        assert seen["version"] == 1 and seen["index"]["id"] == cid and seen["words_checked"] >= 2, seen
        assert seen["found"] == [] and {f["name"] for f in seen["files"]} >= {"vault.json", "manifest.enc"}, seen
        assert add(one, cid, "b.txt", b"[page 1]\n\nMani saw him run.").status_code == 201
        assert one.get(f"/api/cases/{cid}/cloud", headers=H).json()["dirty"] is True
        assert one.post(f"/api/cases/{cid}/cloud/push", headers=H).json() == {"version": 2}

        # laptop two: the case is listed, downloaded, and opened with the passphrase
        row = two.get("/api/cloud/cases", headers=H).json()[0]
        assert (row["id"], row["version"], row["local"]) == (cid, 2, False)
        got = two.post(f"/api/cloud/cases/{cid}/pull", headers=H, json={"label": "SC-114 (laptop 2)"}).json()
        assert got["version"] == 2 and got["replaced"] is False
        assert two.post(f"/api/cases/{cid}/unlock", headers=H, json={"passphrase": "wrong wrong"}).status_code == 401
        assert two.post(f"/api/cases/{cid}/unlock", headers=H, json={"passphrase": PASS}).status_code == 200
        assert len(two.get(f"/api/cases/{cid}/documents", headers=H).json()) == 2

        # conflict: laptop two pushes v3, laptop one (now stale) cannot push or silently download over its own edits
        assert add(two, cid, "c.txt", b"[page 1]\n\nA third statement.").status_code == 201
        assert two.post(f"/api/cases/{cid}/cloud/push", headers=H).json() == {"version": 3}
        assert add(one, cid, "d.txt", b"[page 1]\n\nLaptop one edit.").status_code == 201
        r = one.post(f"/api/cases/{cid}/cloud/push", headers=H)
        assert r.status_code == 409 and "newer version" in r.json()["detail"]
        r = one.post(f"/api/cloud/cases/{cid}/pull", headers=H, json={})
        assert r.status_code == 409 and "never uploaded" in r.json()["detail"]
        assert len(one.get(f"/api/cases/{cid}/documents", headers=H).json()) == 3  # nothing was destroyed
        forced = one.post(f"/api/cloud/cases/{cid}/pull", headers=H, json={"force": True}).json()
        assert forced["replaced"] and forced["version"] == 3
        assert one.get(f"/api/cases/{cid}/documents", headers=H).status_code == 423  # locked again after replacing
        one.post(f"/api/cases/{cid}/unlock", headers=H, json={"passphrase": PASS})
        assert sorted(x["name"] for x in one.get(f"/api/cases/{cid}/documents", headers=H).json()) == ["a.txt", "b.txt", "c.txt"]
        assert not list((Path(d1) / "cases").glob("*.new")) and not list((Path(d1) / "cases").glob("*.old"))

        # delete from the cloud keeps the local copy; sign out and disconnect work
        assert one.delete(f"/api/cloud/cases/{cid}", headers=H).status_code == 200
        assert one.get("/api/cloud/cases", headers=H).json() == []
        assert one.get(f"/api/cases/{cid}/cloud", headers=H).json()["version"] is None
        assert one.post("/api/cloud/logout", headers=H).json()["signed_in"] is False
        assert one.get("/api/cloud/cases", headers=H).status_code == 409
        assert one.delete("/api/cloud/config", headers=H).json()["configured"] is False

    # ---- handler guards ----
    ev = lambda **k: {"routeKey": "GET /cases", "requestContext": {"authorizer": {"jwt": {"claims": {"sub": "sub-alice-00000000"}}}}, **k}
    assert handler.handler({"routeKey": "GET /cases", "requestContext": {}})["statusCode"] == 401
    assert handler.handler(ev(routeKey="GET /nope"))["statusCode"] == 404
    assert handler.handler(ev(routeKey="POST /cases/{caseId}/push", pathParameters={"caseId": "../../etc"}))["statusCode"] == 400
    assert handler.handler(ev(routeKey="POST /cases/{caseId}/push", pathParameters={"caseId": case}, body="[]"))["statusCode"] == 400
    assert handler.handler(ev(routeKey="POST /cases/{caseId}/push", pathParameters={"caseId": case}, body='{"base_version": 0, "size": 99999999999}'))["statusCode"] == 413
    assert handler.handler(ev(routeKey="POST /cases/{caseId}/push", pathParameters={"caseId": case}, body='{"base_version": true, "size": 5}'))["statusCode"] == 422
    print("ok")
finally:
    cloud_stack.stop()
