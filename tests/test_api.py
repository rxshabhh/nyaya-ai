# API checks through FastAPI's test client (no network, fake model backends).
# Run: python tests/test_api.py
import json
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from fastapi.testclient import TestClient

from nyaya.api import create_app
from nyaya.backends import BackendUnavailable
from test_parse import make_pdf  # noqa: E402  (also runs the parser test, which is quick)

FAST = {"time": 1, "memory_kib": 1024, "parallelism": 1}
PASS, NEW = "correct horse battery", "another long passphrase"
TOKEN = "test-token"
CASE = ROOT / "tests" / "corpus" / "01_robbery_shop"
HOST = "http://127.0.0.1:8765"
H = {"X-Nyaya-Token": TOKEN}


def make_client(tmp, **kw):
    app = create_app(tmp, TOKEN, kdf=FAST, embed_factory=lambda: None, **kw)
    return TestClient(app, base_url=HOST)


def wait(c, case, job):
    for _ in range(100):
        r = c.get(f"/api/cases/{case}/jobs/{job}", headers=H).json()
        if r["state"] != "running":
            return r
        time.sleep(0.05)
    raise SystemExit("job did not finish")


def upload(c, case, path, witness, doctype, date, data=None, name=None):
    return c.post(f"/api/cases/{case}/documents", headers=H, data={"witness": witness, "doctype": doctype, "date": date},
                  files={"file": (name or path.name, data if data is not None else path.read_bytes())})


with tempfile.TemporaryDirectory() as tmp:
    c = make_client(tmp)

    # guards: token, host, origin
    assert c.get("/api/health").json() == {"ok": True}
    assert c.get("/api/cases").status_code == 401
    assert c.get("/api/cases", headers={"X-Nyaya-Token": "nope"}).status_code == 401
    assert c.get("/api/cases", headers={**H, "Host": "evil.example"}).status_code == 403
    assert c.get("/api/cases", headers={**H, "Origin": "http://evil.example"}).status_code == 403
    assert c.get("/api/cases", headers={**H, "Origin": HOST}).status_code == 200

    # create a case; short passphrase refused
    assert c.post("/api/cases", headers=H, json={"label": "A", "passphrase": "short"}).status_code == 400
    case = c.post("/api/cases", headers=H, json={"label": "Case A", "passphrase": PASS}).json()["id"]
    assert c.get("/api/cases", headers=H).json() == [{"id": case, "label": "Case A", "unlocked": True}]

    # uploads: good files, then every kind of bad one
    meta = json.loads((CASE / "case.json").read_text(encoding="utf-8"))["documents"]
    for name, m in meta.items():
        doctype = "police_statement" if m["kind"] == "earlier" else "examination_in_chief"
        assert upload(c, case, CASE / name, m["witness"], doctype, m["date"]).status_code == 201
    assert upload(c, case, CASE / "AV_police.txt", "Anil Verma", "police_statement", "15.06.2022").status_code == 409
    assert upload(c, case, None, "W", "police_statement", "15.06.2022", data=b"x", name="a.exe").status_code == 422
    assert upload(c, case, None, "W", "diary", "15.06.2022", data=b"[page 1]\n\nhi", name="b.txt").status_code == 422
    assert upload(c, case, None, "W", "fir", "2022-06-15", data=b"[page 1]\n\nhi", name="c.txt").status_code == 422
    assert upload(c, case, None, " ", "fir", "15.06.2022", data=b"[page 1]\n\nhi", name="d.txt").status_code == 422
    scan = upload(c, case, None, "W", "fir", "15.06.2022", data=make_pdf([[(700, "Text")], []]), name="e.pdf")
    assert scan.status_code == 422 and "page(s) 2" in scan.json()["detail"]
    assert len(c.get(f"/api/cases/{case}/documents", headers=H).json()) == 2

    # analyze with imported claims, as a background job
    claims = json.loads((CASE / "claims.json").read_text(encoding="utf-8"))
    assert c.post(f"/api/cases/{case}/analyze", headers=H, json={"mode": "import"}).status_code == 422
    job = c.post(f"/api/cases/{case}/analyze", headers=H, json={"mode": "import", "claims": claims}).json()["job"]
    assert wait(c, case, job)["state"] == "done"
    res = c.get(f"/api/cases/{case}/results", headers=H).json()
    assert res["counts"] == {"verified": 8, "rejected": 1, "contradictions": 1, "omissions": 2}
    assert len(res["rejected"]) == 1 and len(res["findings"]) == 3

    # Confirm / Dismiss, then lock, wrong passphrase, unlock: state persists
    key = res["findings"][0]["key"]
    assert c.put(f"/api/cases/{case}/findings/{key}", headers=H, json={"state": "maybe"}).status_code == 422
    assert c.put(f"/api/cases/{case}/findings/nope", headers=H, json={"state": "confirmed"}).status_code == 404
    assert c.put(f"/api/cases/{case}/findings/{key}", headers=H, json={"state": "confirmed"}).status_code == 200
    assert c.post(f"/api/cases/{case}/lock", headers=H).status_code == 200
    assert c.get(f"/api/cases/{case}/results", headers=H).status_code == 423
    assert c.post(f"/api/cases/{case}/unlock", headers=H, json={"passphrase": "wrong wrong"}).status_code == 401
    assert c.post(f"/api/cases/{case}/unlock", headers=H, json={"passphrase": PASS}).status_code == 200
    states = {f["key"]: f["state"] for f in c.get(f"/api/cases/{case}/results", headers=H).json()["findings"]}
    assert states[key] == "confirmed"

    # model backend problems become a failed job with a message, not a crash
    def broken(model):
        raise BackendUnavailable("Ollama is not answering")
    c2 = make_client(tmp, generate_factory=broken)
    c2.post(f"/api/cases/{case}/unlock", headers=H, json={"passphrase": PASS})
    job = c2.post(f"/api/cases/{case}/analyze", headers=H, json={"mode": "ollama"}).json()["job"]
    r = wait(c2, case, job)
    assert r["state"] == "failed" and "Ollama" in r["message"]

    # passphrase change, document delete
    assert c.post(f"/api/cases/{case}/passphrase", headers=H, json={"passphrase": NEW}).status_code == 200
    c.post(f"/api/cases/{case}/lock", headers=H)
    assert c.post(f"/api/cases/{case}/unlock", headers=H, json={"passphrase": PASS}).status_code == 401
    assert c.post(f"/api/cases/{case}/unlock", headers=H, json={"passphrase": NEW}).status_code == 200
    doc = c.get(f"/api/cases/{case}/documents", headers=H).json()[0]["id"]
    assert c.delete(f"/api/cases/{case}/documents/{doc}", headers=H).status_code == 200
    assert c.delete(f"/api/cases/{case}/documents/{doc}", headers=H).status_code == 404

    # nothing readable in the data folder
    blobs = [p.read_bytes() for p in Path(tmp).rglob("*") if p.is_file()]
    assert not any(b"Anil" in b or b"grocery" in b for b in blobs)

    # delete the case
    assert c.delete(f"/api/cases/{case}", headers=H).status_code == 200
    assert c.get("/api/cases", headers=H).json() == [] and not (Path(tmp) / "cases" / case).exists()

    # demo case reproduces the README numbers
    demo = c.post("/api/demo", headers=H, json={"passphrase": PASS}).json()["id"]
    assert c.get(f"/api/cases/{demo}/results", headers=H).json()["counts"] == \
        {"verified": 8, "rejected": 3, "contradictions": 2, "omissions": 3}

# archive: export a case, import it as a new locked case, open it with the same passphrase
with tempfile.TemporaryDirectory() as tmp:
    import io
    import zipfile
    c = make_client(tmp)
    case = c.post("/api/demo", headers=H, json={"passphrase": PASS}).json()["id"]
    raw = c.get(f"/api/cases/{case}/export", headers=H)
    assert raw.status_code == 200 and "Demo_case.nyaya" in raw.headers["content-disposition"]
    arc = zipfile.ZipFile(io.BytesIO(raw.content))
    assert not any(b"Suresh" in arc.read(n) for n in arc.namelist())
    bad = io.BytesIO()
    with zipfile.ZipFile(bad, "w") as z:
        z.writestr("vault.json", "{}")
        z.writestr("../evil.txt", "x")
    imp = lambda data: c.post("/api/cases/import", headers=H, data={"label": "Restored"}, files={"file": ("a.nyaya", data)})
    assert imp(bad.getvalue()).status_code == 422 and imp(b"not a zip").status_code == 422
    assert not (Path(tmp) / "evil.txt").exists() and not (Path(tmp) / "cases" / "evil.txt").exists()
    new = imp(raw.content).json()["id"]
    assert new != case and c.get(f"/api/cases/{new}/results", headers=H).status_code == 423  # imported locked
    c.post(f"/api/cases/{case}/lock", headers=H)
    assert c.post(f"/api/cases/{new}/unlock", headers=H, json={"passphrase": "wrong wrong"}).status_code == 401
    assert c.post(f"/api/cases/{new}/unlock", headers=H, json={"passphrase": PASS}).status_code == 200
    assert c.get(f"/api/cases/{new}/results", headers=H).json()["counts"]["contradictions"] == 2

# auto-lock after idle
with tempfile.TemporaryDirectory() as tmp:
    c = make_client(tmp, idle_seconds=0.2)
    case = c.post("/api/cases", headers=H, json={"label": "x", "passphrase": PASS}).json()["id"]
    assert c.get(f"/api/cases/{case}/documents", headers=H).status_code == 200
    time.sleep(0.4)
    assert c.get(f"/api/cases/{case}/documents", headers=H).status_code == 423

print("ok")
