# Store checks: findings saved, state persists across reopen and re-run, vanished findings go stale,
# and no plaintext database exists. Run: python tests/test_store.py
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from nyaya.pipeline import analyze
from nyaya.store import Store
from nyaya.vault import Vault

FAST = {"time": 1, "memory_kib": 1024, "parallelism": 1}
PASS = "correct horse battery"
SAMPLE = ROOT / "sample_case"


def run_into(store, vault, claims):
    result = analyze(claims, vault.paras(), vault.docs())
    store.save_analysis(*result, vault.docs())


with tempfile.TemporaryDirectory() as tmp:
    path = Path(tmp) / "case"
    vault = Vault.create(path, PASS, FAST)
    meta = json.loads((SAMPLE / "case.json").read_text(encoding="utf-8"))["documents"]
    for name, m in meta.items():
        vault.add_document(name, (SAMPLE / name).read_bytes(), m)
    claims = json.loads((SAMPLE / "claims.json").read_text(encoding="utf-8"))

    store = Store.open(vault)
    run_into(store, vault, claims)
    assert store.counts() == {"verified": 8, "rejected": 3, "contradictions": 2, "omissions": 3}
    assert all(f["state"] == "open" for f in store.findings())
    assert len(store.claims("rejected")) == 3

    # confirm one, dismiss another; reopen from disk with the passphrase
    first, second = store.findings()[0], store.findings()[1]
    store.set_state(first["key"], "confirmed")
    store.set_state(second["key"], "dismissed")
    store = Store.open(Vault.open(path, PASS))
    states = {f["key"]: f["state"] for f in store.findings()}
    assert states[first["key"]] == "confirmed" and states[second["key"]] == "dismissed"

    # a re-run producing the same findings keeps every decision
    vault = Vault.open(path, PASS)
    run_into(store, vault, claims)
    assert {f["key"]: f["state"] for f in store.findings()} == states

    # drop the claims behind a confirmed finding: it goes stale but keeps its state
    gone = {(c["doc"], c["page"], c["para"]) for c in (first["a"], first["b"])} if first["kind"] == "contradiction" \
        else {(first["claim"]["doc"], first["claim"]["page"], first["claim"]["para"])}
    run_into(store, vault, [c for c in claims if (c["doc"], c["page"], c["para"]) not in gone])
    assert first["key"] not in {f["key"] for f in store.findings()}
    stale = [f for f in store.findings(include_stale=True) if f["stale"]]
    assert [f["key"] for f in stale] == [first["key"]] and stale[0]["state"] == "confirmed"

    # it comes back un-stale, still confirmed
    run_into(store, vault, claims)
    assert {f["key"]: f["state"] for f in store.findings()} == states

    try:
        store.set_state(first["key"], "maybe")
        raise SystemExit("bad state accepted")
    except ValueError:
        pass

    # no plaintext database anywhere
    files = [p for p in path.rglob("*") if p.is_file()]
    assert not any(p.suffix in (".db", ".sqlite") for p in files)
    assert not any(b"SQLite format" in p.read_bytes() or b"Suresh" in p.read_bytes() for p in files)

print("ok")
