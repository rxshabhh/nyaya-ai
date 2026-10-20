import json
import sys
from pathlib import Path

from .parse import ParseError, load_para
from .pipeline import analyze
from .report import build_report


def run(folder):
    folder = Path(folder)
    paras = load_para(folder)
    claims = json.loads((folder / "claims.json").read_text(encoding="utf-8"))
    docs = json.loads((folder / "case.json").read_text(encoding="utf-8"))["documents"]
    return analyze(claims, paras, docs)


def main(argv=None):
    args = argv or sys.argv[1:]
    if args[:1] == ["serve"]:
        from .api import serve
        return serve(browser="--no-browser" not in args)
    folder = (args or ["sample_case"])[0]
    try:
        good, rejected, cons, oms = run(folder)
    except ParseError as e:
        sys.exit(f"Cannot read case: {e}")
    Path("report.html").write_text(build_report(good, rejected, cons, oms), encoding="utf-8")
    print(f"{len(good)} verified, {len(rejected)} rejected, "
          f"{len(cons)} contradictions, {len(oms)} omissions -> report.html")
