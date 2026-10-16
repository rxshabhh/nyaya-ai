# Runs every case in tests/corpus and scores findings against expected.json.
# Run: python tests/test_corpus.py   (exit 1 if a non-xfail case is wrong)
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from nyaya.cli import run
from nyaya.omissions import omission_code


def actual(folder):
    good, rejected, cons, oms = run(folder)
    return {
        "verified": len(good), "rejected": len(rejected),
        "contradictions": {(a["event"], tuple(sorted(d))) for a, _, d in cons},
        "omissions": {(w, c["event"], omission_code(k), m)
                      for m, w, k, c in oms},
    }


def expected(folder):
    e = json.loads((folder / "expected.json").read_text(encoding="utf-8"))
    return {
        "verified": e["verified"], "rejected": e["rejected"], "xfail": e.get("xfail"),
        "contradictions": {(c["event"], tuple(sorted(c["fields"]))) for c in e["contradictions"]},
        "omissions": {(o["witness"], o["event"], o["kind"], o["material"]) for o in e["omissions"]},
    }


tp = fp = fn = 0
failed = []
for folder in sorted((ROOT / "tests" / "corpus").iterdir()):
    got, want = actual(folder), expected(folder)
    c_tp = c_fp = c_fn = 0
    for key in ("contradictions", "omissions"):
        c_tp += len(got[key] & want[key])
        c_fp += len(got[key] - want[key])
        c_fn += len(want[key] - got[key])
    tp, fp, fn = tp + c_tp, fp + c_fp, fn + c_fn
    ok = c_fp == c_fn == 0 and (got["verified"], got["rejected"]) == (want["verified"], want["rejected"])
    if ok:
        status = "ok" if not want["xfail"] else "UNEXPECTED PASS (remove xfail)"
    else:
        status = "KNOWN GAP: " + want["xfail"] if want["xfail"] else "FAIL"
        if not want["xfail"]:
            failed.append(folder.name)
    print(f"{folder.name:24} verified {got['verified']}/{want['verified']} rejected {got['rejected']}/{want['rejected']} "
          f"tp {c_tp} fp {c_fp} fn {c_fn}  {status}")

print(f"precision {tp / (tp + fp):.2f}  recall {tp / (tp + fn):.2f}  (all cases, xfail included)")
sys.exit(1 if failed else 0)
