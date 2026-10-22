"""Local HTTP API. Listens on 127.0.0.1 only and is guarded by a per-launch token, a Host
check and an Origin check, because any web page open in the browser can reach localhost."""
import json
import os
import re
import secrets
import shutil
import contextlib
import tempfile
import threading
import time
import zipfile
from pathlib import Path

from fastapi import APIRouter, Depends, FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from starlette.background import BackgroundTask
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .archive import ArchiveError, digest, read_archive, write_archive
from .backends import GEMINI_MODEL, BackendUnavailable, gemini_generate, ollama_embed, ollama_generate, using_gemini
from .cloud import Cloud, CloudError, check_config
from .extract import extract_claims
from .parse import ParseError, build_paras
from .pipeline import analyze
from .store import STATES, Store
from .vault import Vault, VaultError, WrongPassphrase

DOCTYPES = {"police_statement": "earlier", "fir": "earlier", "chargesheet": "earlier",
            "examination_in_chief": "court", "cross_examination": "court"}
MAX_UPLOAD = 50 * 1024 * 1024
IDLE_SECONDS = 15 * 60
DEMO = Path(__file__).resolve().parent.parent / "sample_case"
WEB = Path(__file__).resolve().parent.parent / "site" / "dist"  # the website, app included (site/ -> npm run build)
# The page shows privileged text: only our own scripts, no external fetches, no framing
CSP = ("default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self' data:; "
       "connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")


class Website(StaticFiles):
    # Page routes such as /app or /features are handled by the React router, so they get index.html
    async def get_response(self, path, scope):
        r = await super().get_response(path, scope)
        return await super().get_response("index.html", scope) if r.status_code == 404 and "." not in path else r


class Session:
    def __init__(self, vault, store):
        self.vault, self.store, self.lock, self.last = vault, store, threading.RLock(), time.monotonic()


class NewCase(BaseModel):
    label: str
    passphrase: str


class Passphrase(BaseModel):
    passphrase: str


class AnalyzeRequest(BaseModel):
    mode: str = "ollama"  # "ollama" runs the extractor; "import" takes claims from the request
    claims: list[dict] | None = None
    model: str | None = None


class FindingState(BaseModel):
    state: str


class CloudConfig(BaseModel):
    api_url: str
    region: str
    client_id: str


class CloudLogin(BaseModel):
    username: str
    password: str


class Code(BaseModel):
    code: str


class PullRequest(BaseModel):
    label: str | None = None
    force: bool = False


def create_app(data_dir, token, port=8765, idle_seconds=IDLE_SECONDS, kdf=None, extra_origins=(),
               generate_factory=None, embed_factory=None, cloud_factory=None):
    data_dir = Path(data_dir)
    (data_dir / "cases").mkdir(parents=True, exist_ok=True)
    registry_path = data_dir / "cases.json"
    cloud_path = data_dir / "cloud.json"  # endpoints only (no secrets); sign-in tokens stay in memory
    # NYAYA_COGNITO_ENDPOINT points sign-in at a local fake (infra/tests/fakecloud.py); https or loopback only
    cloud_factory = cloud_factory or (lambda cfg: Cloud(cfg, cognito_endpoint=os.environ.get("NYAYA_COGNITO_ENDPOINT")))
    # Gemini while GEMINI_API_KEY is set (a stand-in), else Ollama on this machine. Gemini runs without the
    # embedder, so claims outside the event vocabulary are not paired by meaning.
    generate_factory = generate_factory or (
        lambda model: gemini_generate(model or GEMINI_MODEL) if using_gemini() else ollama_generate(model or "llama3.2:3b"))
    embed_factory = embed_factory or (lambda: None if using_gemini() else ollama_embed())
    hosts = {"127.0.0.1", "localhost"}
    origins = {f"http://{h}:{port}" for h in hosts} | set(extra_origins)
    sessions, jobs, reg_lock = {}, {}, threading.Lock()

    def load_registry():
        return json.loads(registry_path.read_text(encoding="utf-8")) if registry_path.exists() else {}

    def save_registry(reg):
        tmp = registry_path.with_name("cases.json.tmp")
        tmp.write_text(json.dumps(reg, indent=2), encoding="utf-8")
        os.replace(tmp, registry_path)

    def case_path(case_id):
        return data_dir / "cases" / case_id

    def known(case_id):
        if case_id not in load_registry():
            raise HTTPException(404, "no such case")

    def session(case_id):
        known(case_id)
        s = sessions.get(case_id)
        if s is None:
            raise HTTPException(423, "case is locked")
        if time.monotonic() - s.last > idle_seconds:
            sessions.pop(case_id, None)
            raise HTTPException(423, "case locked after being idle")
        s.last = time.monotonic()
        return s

    def make_case(label, passphrase):
        try:
            case_id = secrets.token_hex(8)
            vault = Vault.create(case_path(case_id), passphrase, kdf)
        except VaultError as e:
            raise HTTPException(400, str(e))
        with reg_lock:
            reg = load_registry()
            reg[case_id] = {"label": label.strip() or "Untitled case"}
            save_registry(reg)
        sessions[case_id] = Session(vault, Store.open(vault))
        return case_id

    def add_doc(vault, name, data, witness, doctype, date):
        witness = witness.strip()
        if doctype not in DOCTYPES:
            raise HTTPException(422, f"document type must be one of {', '.join(DOCTYPES)}")
        if not witness:
            raise HTTPException(422, "witness name is required")
        if not re.fullmatch(r"\d{2}\.\d{2}\.\d{4}", date):
            raise HTTPException(422, "date must be DD.MM.YYYY")
        try:
            if not build_paras({name: data}):
                raise ParseError(f"{name}: no readable text found")
            return vault.add_document(name, data, {"witness": witness, "doctype": doctype,
                                                   "kind": DOCTYPES[doctype], "date": date})
        except ParseError as e:
            raise HTTPException(422, str(e))
        except VaultError as e:
            raise HTTPException(409, str(e))

    def run_job(job, s, case_id, req):
        def progress(done, total):
            job.update(done=done, total=total)
        try:
            with s.lock:
                paras, docs = s.vault.paras(), s.vault.docs()
            if req.mode == "import":
                claims, errors = req.claims or [], []
            else:
                claims, errors = extract_claims(paras, docs, generate_factory(req.model), on_progress=progress)
            result = analyze(claims, paras, docs, embed=embed_factory())  # slow model calls stay outside the lock
            with s.lock:
                s.store.save_analysis(*result, docs)
            job.update(state="done", errors=errors)
        except (BackendUnavailable, ParseError, VaultError, ValueError, KeyError) as e:
            job.update(state="failed", message=str(e))

    app = FastAPI(title="Nyaya AI", docs_url=None, redoc_url=None, openapi_url=None)

    @app.middleware("http")
    async def local_only(request: Request, call_next):
        if request.headers.get("host", "").rsplit(":", 1)[0] not in hosts:
            return JSONResponse({"detail": "bad host"}, status_code=403)  # blocks DNS rebinding
        origin = request.headers.get("origin")
        if origin and origin not in origins:
            return JSONResponse({"detail": "bad origin"}, status_code=403)  # blocks other websites
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = CSP
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    app.add_middleware(CORSMiddleware, allow_origins=sorted(origins), allow_methods=["*"],
                       allow_headers=["X-Nyaya-Token", "Content-Type"])

    def auth(x_nyaya_token: str = Header(None)):
        if not x_nyaya_token or not secrets.compare_digest(x_nyaya_token, token):
            raise HTTPException(401, "missing or wrong token")

    @app.get("/api/health")
    def health():
        return {"ok": True}

    api = APIRouter(prefix="/api", dependencies=[Depends(auth)])

    @api.get("/model")
    def model_backend():
        if using_gemini():
            return {"backend": "gemini", "default_model": GEMINI_MODEL, "local": False}
        return {"backend": "ollama", "default_model": "llama3.2:3b", "local": True}

    @api.get("/cases")
    def list_cases():
        return [{"id": i, "label": c["label"], "unlocked": i in sessions, "cloud_version": c.get("cloud", {}).get("version")}
                for i, c in load_registry().items()]

    @api.post("/cases", status_code=201)
    def new_case(body: NewCase):
        case_id = make_case(body.label, body.passphrase)
        return {"id": case_id, "label": load_registry()[case_id]["label"]}

    @api.post("/demo", status_code=201)
    def demo(body: Passphrase):
        case_id = make_case("Demo case", body.passphrase)
        s = sessions[case_id]
        meta = json.loads((DEMO / "case.json").read_text(encoding="utf-8"))["documents"]
        for name, m in meta.items():
            doctype = "police_statement" if m["kind"] == "earlier" else "examination_in_chief"
            add_doc(s.vault, name, (DEMO / name).read_bytes(), m["witness"], doctype, m["date"])
        claims = json.loads((DEMO / "claims.json").read_text(encoding="utf-8"))
        s.store.save_analysis(*analyze(claims, s.vault.paras(), s.vault.docs()), s.vault.docs())
        return {"id": case_id, "label": "Demo case"}

    @api.get("/cases/{case_id}/export")
    def export_case(case_id: str):
        # The vault is already encrypted, so the archive is just its files in a zip. No unlock needed.
        known(case_id)
        s = sessions.get(case_id)
        tmp = tempfile.NamedTemporaryFile(suffix=".nyaya", delete=False)
        tmp.close()
        with s.lock if s else contextlib.nullcontext():  # no write lands halfway through the copy
            write_archive(case_path(case_id), tmp.name)
        name = re.sub(r"[^\w.-]+", "_", load_registry()[case_id]["label"]) or "case"
        return FileResponse(tmp.name, media_type="application/octet-stream", filename=f"{name}.nyaya",
                            background=BackgroundTask(os.unlink, tmp.name))

    def register(case_id, label, **extra):
        with reg_lock:
            reg = load_registry()
            reg[case_id] = {"label": label.strip() or "Imported case", **extra}
            save_registry(reg)
        return reg[case_id]

    @api.post("/cases/import", status_code=201)
    def import_case(file: UploadFile = File(...), label: str = Form(...)):
        case_id = secrets.token_hex(8)
        try:
            read_archive(file.file, case_path(case_id))
        except ArchiveError as e:
            shutil.rmtree(case_path(case_id), ignore_errors=True)
            raise HTTPException(e.status, str(e))
        return {"id": case_id, "label": register(case_id, label)["label"]}  # still locked: needs its passphrase

    @api.post("/cases/{case_id}/unlock")
    def unlock(case_id: str, body: Passphrase):
        known(case_id)
        try:
            vault = Vault.open(case_path(case_id), body.passphrase)
        except WrongPassphrase:
            raise HTTPException(401, "wrong passphrase")
        except VaultError as e:
            raise HTTPException(500, str(e))
        sessions[case_id] = Session(vault, Store.open(vault))
        return {"unlocked": True}

    @api.post("/cases/{case_id}/lock")
    def lock(case_id: str):
        known(case_id)
        sessions.pop(case_id, None)
        return {"unlocked": False}

    @api.post("/cases/{case_id}/passphrase")
    def change_passphrase(case_id: str, body: Passphrase):
        s = session(case_id)
        try:
            with s.lock:
                s.vault.change_passphrase(body.passphrase)
        except VaultError as e:
            raise HTTPException(400, str(e))
        return {"changed": True}

    @api.delete("/cases/{case_id}")
    def delete_case(case_id: str):
        session(case_id)  # only an unlocked case can be deleted
        sessions.pop(case_id, None)
        with reg_lock:
            reg = load_registry()
            reg.pop(case_id, None)
            save_registry(reg)
        shutil.rmtree(case_path(case_id), ignore_errors=True)
        return {"deleted": True}

    @api.get("/cases/{case_id}/documents")
    def documents(case_id: str):
        s = session(case_id)
        with s.lock:
            return [{"id": i, **m} for i, m in s.vault.documents().items()]

    @api.post("/cases/{case_id}/documents", status_code=201)
    def upload(case_id: str, file: UploadFile = File(...), witness: str = Form(...), doctype: str = Form(...),
               date: str = Form(...)):
        s = session(case_id)
        name = Path(file.filename or "").name
        if Path(name).suffix.lower() not in (".txt", ".pdf", ".docx"):
            raise HTTPException(422, "only .txt, .pdf and .docx files are supported")
        data = file.file.read(MAX_UPLOAD + 1)
        if len(data) > MAX_UPLOAD:
            raise HTTPException(413, "file is larger than 50 MB")
        with s.lock:
            doc_id = add_doc(s.vault, name, data, witness, doctype, date)
        return {"id": doc_id, "name": name}

    @api.delete("/cases/{case_id}/documents/{doc_id}")
    def delete_document(case_id: str, doc_id: str):
        s = session(case_id)
        try:
            with s.lock:
                s.vault.remove(doc_id)
        except VaultError as e:
            raise HTTPException(404, str(e))
        return {"deleted": True}

    @api.post("/cases/{case_id}/analyze", status_code=202)
    def start_analysis(case_id: str, body: AnalyzeRequest):
        s = session(case_id)
        if body.mode not in ("ollama", "import"):
            raise HTTPException(422, "mode must be 'ollama' or 'import'")
        if body.mode == "import" and body.claims is None:
            raise HTTPException(422, "import mode needs a claims list")
        with s.lock:
            if not s.vault.documents():
                raise HTTPException(400, "add documents first")
        if any(j["case"] == case_id and j["state"] == "running" for j in jobs.values()):
            raise HTTPException(409, "an analysis is already running for this case")
        job_id = secrets.token_hex(8)
        jobs[job_id] = job = {"case": case_id, "state": "running", "done": 0, "total": 0, "message": "", "errors": []}
        threading.Thread(target=run_job, args=(job, s, case_id, body), daemon=True).start()
        return {"job": job_id}

    @api.get("/cases/{case_id}/jobs/{job_id}")
    def job_status(case_id: str, job_id: str):
        session(case_id)
        job = jobs.get(job_id)
        if not job or job["case"] != case_id:
            raise HTTPException(404, "no such job")
        return {k: v for k, v in job.items() if k != "case"}

    @api.get("/cases/{case_id}/results")
    def results(case_id: str):
        s = session(case_id)
        with s.lock:
            return {"counts": s.store.counts(), "findings": s.store.findings(include_stale=True),
                    "rejected": s.store.claims("rejected")}

    @api.put("/cases/{case_id}/findings/{key}")
    def set_finding(case_id: str, key: str, body: FindingState):
        s = session(case_id)
        if body.state not in STATES:
            raise HTTPException(422, f"state must be one of {', '.join(STATES)}")
        try:
            with s.lock:
                s.store.set_state(key, body.state)
        except KeyError:
            raise HTTPException(404, "no such finding")
        return {"key": key, "state": body.state}

    # ---- optional cloud sync (see infra/ and docs/aws/): moves encrypted archives, nothing else ----
    cloud = {"c": cloud_factory(json.loads(cloud_path.read_text(encoding="utf-8"))) if cloud_path.exists() else None}

    def need_cloud(signed=True):
        c = cloud["c"]
        if c is None:
            raise HTTPException(409, "Cloud sync is not set up. Add the endpoints from your administrator first.")
        if signed and not c.signed_in:
            raise HTTPException(409, "Sign in to the cloud first.")
        return c

    def via_cloud(fn, *args):
        try:
            return fn(*args)
        except CloudError as e:
            raise HTTPException(e.status if 400 <= e.status < 600 else 502, str(e))

    @api.get("/cloud")
    def cloud_status():
        c = cloud["c"]
        return {"configured": c is not None, "signed_in": bool(c and c.signed_in), "user": c.username if c else None,
                "waiting_for_code": bool(c and c.pending), "config": c.cfg if c else None}

    @api.put("/cloud/config")
    def cloud_config(body: CloudConfig):
        cfg = via_cloud(check_config, body.model_dump())
        cloud_path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
        cloud["c"] = cloud_factory(cfg)
        return cloud_status()

    @api.delete("/cloud/config")
    def cloud_disconnect():
        cloud_path.unlink(missing_ok=True)
        cloud["c"] = None
        return cloud_status()

    @api.post("/cloud/login")
    def cloud_login(body: CloudLogin):
        return via_cloud(need_cloud(signed=False).login, body.username.strip(), body.password)

    @api.post("/cloud/mfa")
    def cloud_mfa(body: Code):
        return via_cloud(need_cloud(signed=False).submit_code, body.code)

    @api.post("/cloud/logout")
    def cloud_logout():
        if cloud["c"]:
            cloud["c"].sign_out()
        return cloud_status()

    @api.get("/cloud/cases")
    def cloud_cases():
        reg = load_registry()
        return [{**r, "local": r["id"] in reg, "label": reg.get(r["id"], {}).get("label"),
                 "synced_version": reg.get(r["id"], {}).get("cloud", {}).get("version")}
                for r in via_cloud(need_cloud().list_cases)]

    @api.get("/cases/{case_id}/cloud")
    def case_cloud(case_id: str):
        known(case_id)
        c = load_registry()[case_id].get("cloud")
        return {"version": c["version"] if c else None,
                "dirty": c is None or digest(case_path(case_id)) != c["digest"]}  # changed since the last sync

    @api.post("/cases/{case_id}/cloud/push")
    def cloud_push(case_id: str):
        cl = need_cloud()
        known(case_id)
        s = sessions.get(case_id)
        base = load_registry()[case_id].get("cloud", {}).get("version", 0)
        tmp = tempfile.NamedTemporaryFile(suffix=".nyaya", delete=False)
        tmp.close()
        try:
            with s.lock if s else contextlib.nullcontext():  # snapshot under the lock, upload outside it
                write_archive(case_path(case_id), tmp.name)
                snapshot = digest(case_path(case_id))
            version = via_cloud(cl.push, case_id, tmp.name, base)
        finally:
            os.unlink(tmp.name)
        with reg_lock:
            reg = load_registry()
            reg[case_id]["cloud"] = {"version": version, "digest": snapshot}
            save_registry(reg)
        return {"version": version}

    @api.get("/cases/{case_id}/cloud/inspect")
    def cloud_inspect(case_id: str):
        # Proof for the advocate: fetch the latest cloud copy and show exactly what AWS holds, and whether
        # any word of this case's readable text appears anywhere in it
        cl = need_cloud()
        s = session(case_id)  # unlocked, so the readable words can be listed for the search
        with s.lock:
            words = {w for t in s.vault.paras().values() for w in re.findall(r"[A-Za-z]{5,}", t)} | set(s.vault.docs())
        tmp = tempfile.NamedTemporaryFile(suffix=".nyaya", delete=False)
        tmp.close()
        try:
            version = via_cloud(cl.pull, case_id, tmp.name)
            size = os.path.getsize(tmp.name)
            with zipfile.ZipFile(tmp.name) as z:
                blobs = {n: z.read(n) for n in z.namelist()}
        except zipfile.BadZipFile:
            raise HTTPException(502, "The cloud copy is not a valid archive")
        finally:
            os.unlink(tmp.name)
        # vault.json is readable on purpose (key-derivation settings and the wrapped key), so it is listed, not searched
        enc = [b for n, b in blobs.items() if n != "vault.json"]
        return {"version": version, "size": size,
                "index": next((r for r in via_cloud(cl.list_cases) if r["id"] == case_id), None),
                "files": [{"name": n, "size": len(b), "starts": b[:16].hex()} for n, b in blobs.items()],
                "words_checked": len(words), "found": sorted(w for w in words if any(w.encode() in b for b in enc))}

    @api.post("/cloud/cases/{case_id}/pull")
    def cloud_pull(case_id: str, body: PullRequest):
        cl = need_cloud()
        local = load_registry().get(case_id)
        if local:  # refuse to silently destroy work that was never uploaded
            c = local.get("cloud")
            if not body.force and (c is None or digest(case_path(case_id)) != c["digest"]):
                raise HTTPException(409, "This laptop has changes that were never uploaded. Downloading replaces them.")
        tmp = tempfile.NamedTemporaryFile(suffix=".nyaya", delete=False)
        tmp.close()
        staging = data_dir / "cases" / f"{case_id}.new"
        old = data_dir / "cases" / f"{case_id}.old"
        try:
            version = via_cloud(cl.pull, case_id, tmp.name)
            shutil.rmtree(staging, ignore_errors=True)
            try:
                with open(tmp.name, "rb") as f:
                    read_archive(f, staging)
            except ArchiveError as e:
                raise HTTPException(502, f"The cloud copy is not a valid archive: {e}")
            sessions.pop(case_id, None)  # the passphrase may differ in the cloud copy; unlock again
            shutil.rmtree(old, ignore_errors=True)
            if case_path(case_id).exists():
                os.replace(case_path(case_id), old)
            os.replace(staging, case_path(case_id))
            shutil.rmtree(old, ignore_errors=True)
        finally:
            os.unlink(tmp.name)
            shutil.rmtree(staging, ignore_errors=True)
        label = (local or {}).get("label") or (body.label or "").strip() or f"Cloud case {case_id[:4]}"
        register(case_id, label, cloud={"version": version, "digest": digest(case_path(case_id))})
        return {"id": case_id, "label": label, "version": version, "replaced": bool(local)}

    @api.delete("/cloud/cases/{case_id}")
    def cloud_delete(case_id: str):
        via_cloud(need_cloud().delete, case_id)
        with reg_lock:
            reg = load_registry()
            if case_id in reg:
                reg[case_id].pop("cloud", None)
                save_registry(reg)
        return {"deleted": True}

    app.include_router(api)
    if WEB.is_dir():
        app.mount("/", Website(directory=WEB, html=True), name="web")
    return app


def default_data_dir():
    return Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "NyayaAI"


def serve(port=8765, data_dir=None, browser=True):
    import uvicorn
    import webbrowser
    token = secrets.token_urlsafe(32)
    app = create_app(data_dir or default_data_dir(), token, port)
    url = f"http://127.0.0.1:{port}/app#token={token}"  # fragment: never sent to the server or written to logs
    print(f"Nyaya AI on {url}", flush=True)
    if not WEB.is_dir():
        print("Website not built yet: cd site && npm install && npm run build  (the API works without it)", flush=True)
    elif browser:
        threading.Timer(1.0, webbrowser.open, [url]).start()
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
