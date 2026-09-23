# Nyaya Ai prototype: find contradictions and omissions in witness statements

import re
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

if __name__ == "__main__":

    for key, text in load_para("sample_case").items():
        print(key,text[:60])