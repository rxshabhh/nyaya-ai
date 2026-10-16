import re
from datetime import date

from .parse import norm


def parse_date(s):
    m = re.search(r"(\d{1,2})(?:/(\d{1,2}))?[./-](\d{1,2})[./-](\d{4})", s or "")
    if not m:
        return None
    d1, d2, month, year = m.groups()
    return date(int(year), int(month), int(d1)), date(int(year), int(month), int(d2 or d1))


def parse_time(s):  # minutes since midnight
    m = re.search(r"(\d{1,2})(?:[.:](\d{2}))?\s*([ap])\.?\s*m", norm(s))
    if not m:
        return None
    hour = int(m[1]) % 12 + (12 if m[3] == "p" else 0)
    return hour * 60 + int(m[2] or 0)


def parse_amount(s):
    m = re.search(r"rs\.?\s*([\d,]+)", norm(s))
    return int(m[1].replace(",", "")) if m else None


def compare(a, b):
    # List the fields where two claims about the same event disagree
    diffs = []
    da, db = parse_date(a.get("date")), parse_date(b.get("date"))
    if da and db and (da[1] < db[0] or db[1] < da[0]):  # no overlap at all
        diffs.append("date")
    ta, tb = parse_time(a.get("time")), parse_time(b.get("time"))
    if ta is not None and tb is not None and abs(ta - tb) > 30:  # "at about" allows 30 min
        diffs.append("time")
    if a.get("place") and b.get("place") and norm(a["place"]) != norm(b["place"]):
        diffs.append("place")
    aa, ab = parse_amount(a.get("amount")), parse_amount(b.get("amount"))
    if aa and ab and aa != ab:
        diffs.append("amount")
    return diffs


def find_contradictions(good, docs):
    # Same witness, same event, different documents
    out = []
    for i, a in enumerate(good):
        for b in good[i + 1:]:
            same_witness = docs[a["doc"]]["witness"] == docs[b["doc"]]["witness"]
            if same_witness and a["event"] == b["event"] and a["doc"] != b["doc"]:
                diffs = compare(a, b)
                if diffs:
                    out.append((a, b, diffs))
    return out
