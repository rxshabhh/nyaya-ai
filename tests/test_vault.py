# Vault checks: round trip, wrong passphrase, nothing readable on disk, tampering, passphrase change.
# Run: python tests/test_vault.py
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from nyaya.parse import load_para
from nyaya.vault import CorruptVault, Vault, VaultError, WrongPassphrase

FAST = {"time": 1, "memory_kib": 1024, "parallelism": 1}  # weak KDF only to keep the test quick
PASS, NEW = "correct horse battery", "another long passphrase"
SAMPLE = ROOT / "sample_case"


def raises(exc, fn, *a):
    try:
        fn(*a)
    except exc:
        return
    raise SystemExit(f"expected {exc.__name__}")


with tempfile.TemporaryDirectory() as tmp:
    path = Path(tmp) / "case"
    v = Vault.create(path, PASS, FAST)
    ids = {}
    for f in sorted(SAMPLE.glob("*.txt")):
        ids[f.name] = v.add_document(f.name, f.read_bytes(), {"witness": "x"})

    # round trip: parsing from the vault equals parsing the plain folder
    assert Vault.open(path, PASS).paras() == load_para(SAMPLE)

    # nothing readable on disk: no real names, no plaintext
    files = [p for p in path.rglob("*") if p.is_file()]
    assert not any("PW1" in p.name for p in files)
    assert not any(b"Suresh" in p.read_bytes() or b"Ramesh" in p.read_bytes() for p in files)

    raises(WrongPassphrase, Vault.open, path, "not the passphrase")
    raises(VaultError, v.add_document, "PW1_court_deposition.txt", b"x")  # duplicate name
    raises(VaultError, Vault.create, Path(tmp) / "short", "short")
    raises(VaultError, Vault.create, path, PASS)  # folder not empty

    # tampering: flip one byte in a ciphertext
    victim = path / "files" / f"{ids['PW1_court_deposition.txt']}.enc"
    good = victim.read_bytes()
    victim.write_bytes(good[:-1] + bytes([good[-1] ^ 1]))
    raises(CorruptVault, Vault.open(path, PASS).read, ids["PW1_court_deposition.txt"])
    victim.write_bytes(good)

    # swapping two ciphertexts is caught too (the file id is bound into the encryption)
    other = path / "files" / f"{ids['PW1_earlier_statement.txt']}.enc"
    other_good = other.read_bytes()
    other.write_bytes(good)
    raises(CorruptVault, Vault.open(path, PASS).read, ids["PW1_earlier_statement.txt"])
    other.write_bytes(other_good)

    # passphrase change rewraps the key only; documents are untouched
    before = {p.name: p.read_bytes() for p in (path / "files").iterdir()}
    v.change_passphrase(NEW)
    assert before == {p.name: p.read_bytes() for p in (path / "files").iterdir()}
    raises(WrongPassphrase, Vault.open, path, PASS)
    assert Vault.open(path, NEW).paras() == load_para(SAMPLE)

    # remove
    w = Vault.open(path, NEW)
    w.remove(ids["PW2_earlier_statement.txt"])
    assert "PW2_earlier_statement.txt" not in {m["name"] for m in Vault.open(path, NEW).documents().values()}

print("ok")
