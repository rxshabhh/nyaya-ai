# Nyaya Ai prototype: find contradictions and omissions in witness statements

import re
import json
from pathlib import Path

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

if __name__ == "__main__":

    paras = load_para("sample_case")

    claims = json.loads(open("sample_case/claims.json",encoding="utf-8").read())

    for c in claims:
        reason = verify(c,paras)
        print("REJECTED:" if reason else "OK:  ", c["exact_quote"][:50], reason or "")
