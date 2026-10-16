import json
import sys
from pathlib import Path

from .compare import find_contradictions
from .omissions import find_omissions
from .parse import load_para
from .report import build_report
from .verify import split_claims


def run(folder):
    # Verify claims first, then compare only the good ones
    folder = Path(folder)
    paras = load_para(folder)
    claims = json.loads((folder / "claims.json").read_text(encoding="utf-8"))
    docs = json.loads((folder / "case.json").read_text(encoding="utf-8"))["documents"]
    good, rejected = split_claims(claims, paras)
    return good, rejected, find_contradictions(good, docs), find_omissions(good, docs)


def main(argv=None):
    folder = (argv or sys.argv[1:] or ["sample_case"])[0]
    good, rejected, cons, oms = run(folder)
    Path("report.html").write_text(build_report(good, rejected, cons, oms), encoding="utf-8")
    print(f"{len(good)} verified, {len(rejected)} rejected, "
          f"{len(cons)} contradictions, {len(oms)} omissions -> report.html")
