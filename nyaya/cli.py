import json
import sys
from pathlib import Path

from .parse import load_para
from .pipeline import analyze


def run(folder):
    folder = Path(folder)
    paras = load_para(folder)
    claims = json.loads((folder / "claims.json").read_text(encoding="utf-8"))
    docs = json.loads((folder / "case.json").read_text(encoding="utf-8"))["documents"]
    return analyze(claims, paras, docs)


def main(argv=None):
    # `python -m nyaya` opens the website with the app; `serve` is still accepted
    from .api import serve
    return serve(browser="--no-browser" not in (argv or sys.argv[1:]))
