import re
from pathlib import Path


def load_para(folder):
    # Returns {(filename,page,para): text} for every .txt file
    paras = {}
    for file in sorted(Path(folder).glob("*.txt")):
        text = file.read_text(encoding="utf-8")
        pages = re.split(r"^\[page \d+\]\s*$", text, flags=re.M)
        pages = pages[1:]  # drop the empty chunk before [page 1]
        for page_no, page in enumerate(pages, 1):
            blocks = re.split(r"\n\s*\n", page)
            for para_no, block in enumerate([b for b in blocks if b.strip()], 1):
                paras[(file.name, page_no, para_no)] = block.strip()
    return paras


def norm(s):  # lowercase and collapse whitespace
    return re.sub(r"\s+", " ", s or "").strip().lower()
