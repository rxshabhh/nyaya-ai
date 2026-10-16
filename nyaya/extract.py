"""Claim extraction. The model only proposes; verify.py decides.

`generate` is any function str -> str (Ollama on CPU today, Genie on the NPU later), so the
prompt, the JSON handling and the citation logic are all testable without a model.
"""
import json
import re

OTHER = "other"
EVENT_VOCAB = (
    "accused_arrives", "accused_seen", "accused_leaves", "accused_flees", "weapon_shown", "weapon_carried",
    "threat_made", "assault", "injury_to_person", "killing", "property_taken", "cash_taken",
    "property_damaged", "money_given", "cheque_issued", "promise_made", "document_signed",
    "complaint_made", "police_informed", "eyewitness_present", "identification_of_accused",
    "victim_taken_to_hospital", "vehicle_collision", "vehicle_flees", "argument", "abuse_given",
    "demand_made", OTHER,
)

PROMPT = """You extract factual claims from ONE paragraph of a witness statement.
Return only JSON: {{"claims": [{{"event": ..., "event_text": ..., "actor": ..., "date": ..., "time": ..., "place": ..., "amount": ..., "exact_quote": ...}}]}}

Rules:
- "event" must be one of: {vocab}. Use "other" if none fits.
- "event_text" is a short snake_case label in your own words.
- "exact_quote" is copied word for word from the paragraph: the shortest sentence or phrase that states the claim.
- date, time, place and amount: fill only if they appear word for word inside exact_quote, otherwise null.
- One claim per event. If the paragraph states no event, return {{"claims": []}}.

Paragraph:
{paragraph}
"""


def build_prompt(paragraph, vocab=EVENT_VOCAB):
    return PROMPT.format(vocab=", ".join(vocab), paragraph=paragraph)


def _snake(s):
    return re.sub(r"[^a-z0-9]+", "_", str(s or "").lower()).strip("_")


def _parse(text):
    # Models wrap JSON in code fences or chatter; take the outermost braces or brackets
    m = re.search(r"\{.*\}|\[.*\]", text, re.S)
    if not m:
        raise ValueError("no JSON in the model reply")
    data = json.loads(m.group(0))
    if isinstance(data, dict):
        data = data.get("claims", [])
    if not isinstance(data, list):
        raise ValueError("claims is not a list")
    return data


def extract_claims(paras, docs, generate, vocab=EVENT_VOCAB):
    # Citation (doc, page, para) and witness come from our code, never from the model.
    claims, errors = [], []
    for (doc, page, para), text in paras.items():
        where = {"doc": doc, "page": page, "para": para}
        try:
            items = _parse(generate(build_prompt(text, vocab)))
        except ValueError as e:  # includes json.JSONDecodeError
            errors.append({**where, "error": str(e)})
            continue
        for it in items:
            if not isinstance(it, dict) or not isinstance(it.get("exact_quote"), str):
                errors.append({**where, "error": "claim without an exact_quote"})
                continue
            label = _snake(it.get("event"))
            witness = docs[doc]["witness"]
            claim = {**where, "witness": witness, "actor": str(it.get("actor") or witness),
                     "event": label if label in vocab else OTHER,
                     "event_text": _snake(it.get("event_text")) or label,
                     "exact_quote": it["exact_quote"]}
            for f in ("date", "time", "place", "amount"):
                if it.get(f) not in (None, ""):
                    claim[f] = str(it[f])
            claims.append(claim)
    return claims, errors
