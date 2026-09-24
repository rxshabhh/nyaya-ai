# Nyaya Ai prototype: find contradictions and omissions in witness statements

import re
import json
import html
from pathlib import Path

from datetime import date
from string import Template

MATERIAL_HINTS = ("weapon", "knife", "threat", "injur", "kill", "eyewitness", "identif")

BUTTONS = ('<div><button onclick="mark(this,\'ok\')">Confirm</button> '
           '<button onclick="mark(this,\'no\')">Dismiss</button></div>')

def load_para(folder):
    # Returns {(filename,page,para): text} for every .txt file

    paras = {}

    for file in sorted(Path(folder).glob("*.txt")):
        text = file.read_text(encoding="utf-8")

        pages = re.split(r"^\[page \d+\]\s*$",text,flags=re.M)
        pages = pages[1:] # clear empty space before [page 1]

        for page_no, page in enumerate(pages,1):
            blocks = re.split(r"\n\s*\n",page)
            non_empty = [b for b in blocks if b.strip()]

            for para_no, block in enumerate(non_empty,1):
                paras[(file.name,page_no,para_no)] = block.strip()
    
    return paras


def norm(s): #normalize the text
    return re.sub(r"\s+"," ",s or "").strip().lower()


def verify(claim, paras):
    # Return none if claim is OK, else rejected
    key = (claim["doc"],claim["page"],claim["para"])
    if key not in paras:
        return "cited page/paragraph does not exist"
    
    quote = norm(claim["exact_quote"])
    if quote not in norm(paras[key]):
        return "quote not found at the cited paragraph"

    for field in ("date","time","place","amount"):
        if claim.get(field) and norm(claim[field]) not in quote:
            return f"{field} '{claim[field]}' is not in the quote"
    return None

def parse_date(s): 
    m = re.search(r"(\d{1,2})(?:/(\d{1,2}))?[./-](\d{1,2})[./-](\d{4})", s or "")
    if not m:
        return None
    d1,d2,month,year = m.groups()

    return date(int(year), int(month), int(d1)), date(int(year), int(month), int(d2 or d1))

def parse_time(s): # converted to mins

    m = re.search(r"(\d{1,2})(?:[.:](\d{2}))?\s*([ap])\.?\s*m", norm(s))
    if not m:
        return None
    hour =  int(m[1]) % 12 + (12 if m[3] == "p" else 0)
    return hour *60+ int(m[2] or 0)

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

def find_omissions(good, docs):
    # Events a witness mentioned in one statement but not in their other one
    results = []
    witnesses = {docs[c["doc"]]["witness"] for c in good}
    for w in witnesses:
        mine = [c for c in good if docs[c["doc"]]["witness"] == w]
        earlier = {c["event"] for c in mine if docs[c["doc"]]["kind"] == "earlier"}
        court = {c["event"] for c in mine if docs[c["doc"]]["kind"] == "court"}
        if not earlier or not court:
            continue  # need both statements to compare
        for c in mine:
            in_court = docs[c["doc"]]["kind"] == "court"
            other_side = earlier if in_court else court
            if c["event"] not in other_side:
                material = any(h in c["event"] for h in MATERIAL_HINTS)
                kind = "said first in Court, not told to police" if in_court else "told police, not repeated in Court"
                results.append((material, w, kind, c))
    return sorted(results, key=lambda r: not r[0])  # likely-material first


def cite(c):
    return f'{c["doc"]} p.{c["page"]} para {c["para"]}'


def quote(c):
    return f'<blockquote>"{html.escape(c["exact_quote"])}"<cite>{html.escape(cite(c))}</cite></blockquote>'


def build_report(good, rejected, contradictions, omissions):
    cons = "".join(
        f'<div class="card"><b>Contradiction: {", ".join(d)} differ</b>'
        f'<div class="pair">{quote(a)}{quote(b)}</div>{BUTTONS}</div>'
        for a, b, d in contradictions)
    oms = "".join(
        f'<div class="card"><b>{"Likely material" if m else "Check materiality"}: '
        f'{html.escape(w)}, {k}</b>{quote(c)}{BUTTONS}</div>'
        for m, w, k, c in omissions)
    rej = "".join(f'<li>{html.escape(r)}: "{html.escape(c["exact_quote"])}"</li>' for c, r in rejected)

    template = Template(Path("report_template.html").read_text(encoding="utf-8"))
    return template.substitute(
        verified=len(good), rejected_count=len(rejected),
        contradiction_count=len(contradictions), contradictions=cons,
        omission_count=len(omissions), omissions=oms, rejected=rej)

# it verifies claims first and then compares the good ones

if __name__ == "__main__":
    paras = load_para("sample_case")
    claims = json.loads(open("sample_case/claims.json", encoding="utf-8").read())
    docs = json.loads(open("sample_case/case.json", encoding="utf-8").read())["documents"]

    good, rejected = [], []
    for c in claims:
        reason = verify(c, paras)
        if reason:
            rejected.append((c, reason))
        else:
            good.append(c)

    contradictions = []
    for i, a in enumerate(good):
        for b in good[i + 1:]:
            if a["event"] == b["event"] and a["doc"] != b["doc"]:
                diffs = compare(a, b)
                if diffs:
                    contradictions.append((a, b, diffs))

    omissions = find_omissions(good, docs)

    open("report.html", "w", encoding="utf-8").write(build_report(good, rejected, contradictions, omissions))
    print(f"{len(good)} verified, {len(rejected)} rejected, "
          f"{len(contradictions)} contradictions, {len(omissions)} omissions -> report.html")