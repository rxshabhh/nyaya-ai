# Extractor and pairing checks with a fake model and a fake embedder (no Ollama needed).
# Run: python tests/test_extract.py
import json
import re
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from nyaya.backends import BackendUnavailable, ollama_generate
from nyaya.extract import EVENT_VOCAB, build_prompt, extract_claims
from nyaya.omissions import omission_code
from nyaya.parse import load_para
from nyaya.pipeline import analyze

CASE = ROOT / "tests" / "corpus" / "01_robbery_shop"
docs = {k: v for k, v in json.loads((CASE / "case.json").read_text(encoding="utf-8"))["documents"].items()}
paras = load_para(CASE)


def fake_embed(texts):  # bag of words hashed into 512 buckets; enough to tell paraphrase from unrelated
    out = []
    for t in texts:
        v = [0.0] * 512
        for w in re.findall(r"[a-z0-9]+", t.lower()):
            v[zlib.crc32(w.encode()) % 512] += 1
        out.append(v)
    return out


def reply(*claims, fence=False):
    body = json.dumps({"claims": list(claims)})
    return f"Sure!\n```json\n{body}\n```" if fence else body


def c(event, quote, **kw):
    return {"event": event, "event_text": kw.pop("text", event), "exact_quote": quote, **kw}


CANNED = {
    "I am Anil Verma and I run a grocery shop at Gandhi Chowk.":
        reply(c("other", "I run a grocery shop at Gandhi Chowk.", text="shop_ownership", place="Gandhi Chowk")),
    "On 14.06.2022 at about 10 pm I was closing my shop when two men entered the shop.":
        reply(c("other", "On 14.06.2022 at about 10 pm I was closing my shop when two men entered the shop.",
                text="men_enter", date="14.06.2022", time="10 pm", place="shop"), fence=True),
    "One of them showed a pistol and demanded the cash box.":
        reply(c("weapon_shown", "One of them showed a pistol and demanded the cash box.")),
    "They took Rs. 12,000 from the cash box and ran away towards the bus stand.":
        reply(c("cash_taken", "They took Rs. 12,000 from the cash box and ran away", amount="Rs. 12,000",
                doc="WRONG.txt", page=99),  # a bogus citation from the model must be ignored
              c("property_taken", "They also stole a gold chain.")),  # invented quote
    "I run a grocery shop at Gandhi Chowk.":
        reply(c("other", "I run a grocery shop at Gandhi Chowk.", text="shop_ownership", place="Gandhi Chowk")),
    "On 14.06.2022 at about 8 pm I was closing my shop when two men entered the shop.":
        reply(c("other", "On 14.06.2022 at about 8 pm I was closing my shop when two men entered the shop.",
                text="men_enter", date="14.06.2022", time="8 pm", place="shop")),
    "They took Rs. 12,000 from the cash box and ran away.":
        reply(c("cash_taken", "They took Rs. 12,000 from the cash box and ran away", amount="Rs. 12,000")),
    "I identified the accused Rakesh in the test identification parade.":
        reply(c("identification_of_accused", "I identified the accused Rakesh in the test identification parade.")),
}


def fake_generate(prompt):
    return CANNED[prompt.split("Paragraph:\n", 1)[1].strip()]


claims, errors = extract_claims(paras, docs, fake_generate)
assert not errors and len(claims) == 9
assert all(cl["doc"] != "WRONG.txt" and cl["page"] == 1 for cl in claims)  # citation set by code
assert all(cl["witness"] == "Anil Verma" for cl in claims)
assert {cl["event"] for cl in claims} <= set(EVENT_VOCAB)
assert all(e in build_prompt("x") for e in ("weapon_shown", "other", "exact_quote"))

# with an embedder: the gate rejects the invented quote, "other" claims pair by meaning
good, rejected, cons, oms = analyze(claims, paras, docs, embed=fake_embed)
assert (len(good), len(rejected)) == (8, 1) and "not found" in rejected[0][1]
assert len(cons) == 1 and cons[0][2] == ["time"] and cons[0][0]["event_text"] == "men_enter"
assert sorted((cl["event"], omission_code(k), m) for m, _, k, cl in oms) == [
    ("identification_of_accused", "court_only", True), ("weapon_shown", "earlier_only", True)]

# without an embedder: "other" claims cannot be paired, so they are left out, not flagged
_, _, cons, oms = analyze(claims, paras, docs)
assert cons == [] and len(oms) == 2

# an unrelated "other" claim on one side only is a (non-material) omission when the embedder is on
extra_docs = {"p.txt": {"witness": "W", "kind": "earlier"}, "c.txt": {"witness": "W", "kind": "court"}}
extra_paras = {("p.txt", 1, 1): "The accused came at night.", ("c.txt", 1, 1): "My cousin brought us tea."}
extra = [{"doc": "p.txt", "page": 1, "para": 1, "event": "other", "event_text": "arrival", "exact_quote": "The accused came at night."},
         {"doc": "c.txt", "page": 1, "para": 1, "event": "other", "event_text": "tea", "exact_quote": "My cousin brought us tea."}]
_, _, cons, oms = analyze(extra, extra_paras, extra_docs, embed=fake_embed)
assert cons == [] and len(oms) == 2 and not any(m for m, *_ in oms)

# bad model output is reported, not crashed on
_, errors = extract_claims({("p.txt", 1, 1): "x"}, extra_docs, lambda p: "I cannot do that")
assert errors and "no JSON" in errors[0]["error"]
_, errors = extract_claims({("p.txt", 1, 1): "x"}, extra_docs, lambda p: '{"claims": [{"event": "other"}]}')
assert errors and "exact_quote" in errors[0]["error"]

# model hosts must be local; an unreachable server gives a clear message
try:
    ollama_generate(host="http://example.com:11434")("hi")
    raise SystemExit("remote host accepted")
except ValueError:
    pass
try:
    ollama_generate(host="http://127.0.0.1:1", timeout=2)("hi")
    raise SystemExit("expected BackendUnavailable")
except BackendUnavailable as e:
    assert "Ollama" in str(e)

print("ok")
