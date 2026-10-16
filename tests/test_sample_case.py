# Golden check: the sample case must keep giving the same findings.
# Run: python tests/test_sample_case.py
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from nyaya.cli import run

good, rejected, cons, oms = run(ROOT / "sample_case")
assert (len(good), len(rejected), len(cons), len(oms)) == (8, 3, 2, 3)
assert sum(1 for m, *_ in oms if m) == 2  # knife threat + eyewitness
print("ok")
