"""Optional: run the real Ollama models over a case folder and report the gate pass rate.
Needs Ollama running locally:  ollama pull llama3.2:3b  and  ollama pull all-minilm
Run: python scripts/live_extract_check.py [folder] [model]
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from nyaya.backends import BackendUnavailable, ollama_embed, ollama_generate
from nyaya.extract import extract_claims
from nyaya.parse import load_para
from nyaya.pipeline import analyze

folder = Path(sys.argv[1] if len(sys.argv) > 1 else "sample_case")
model = sys.argv[2] if len(sys.argv) > 2 else "llama3.2:3b"
paras = load_para(folder)
docs = json.loads((folder / "case.json").read_text(encoding="utf-8"))["documents"]

try:
    claims, errors = extract_claims(paras, docs, ollama_generate(model))
    good, rejected, cons, oms = analyze(claims, paras, docs, embed=ollama_embed())
except BackendUnavailable as e:
    sys.exit(str(e))

print(f"{len(paras)} paragraphs, {len(claims)} claims, {len(errors)} unreadable replies")
print(f"gate pass rate: {len(good)}/{len(claims)}")
for c, reason in rejected:
    print(f"  rejected: {reason}: {c['exact_quote'][:70]}")
print(f"{len(cons)} contradictions, {len(oms)} omissions")
