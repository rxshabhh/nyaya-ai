import re
from pathlib import Path
from statistics import median

import pdfplumber
from docx import Document

SUPPORTED = (".txt", ".pdf", ".docx")


class ParseError(ValueError):
    """A document cannot be read reliably; the message is shown to the advocate."""


def _split_blocks(text):
    return [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]


def _read_txt(path):
    chunks = re.split(r"^\[page \d+\]\s*$", path.read_text(encoding="utf-8"), flags=re.M)
    return [_split_blocks(c) for c in chunks[1:]]  # chunks[0] is the empty text before [page 1]


def _pdf_page_paragraphs(page):
    lines = page.extract_text_lines()
    if not lines:
        return []
    pitch = [b["top"] - a["top"] for a, b in zip(lines, lines[1:])]
    normal = median(pitch) if pitch else 0
    paras, current = [], [lines[0]["text"]]
    for gap, line in zip(pitch, lines[1:]):
        if gap > 1.4 * normal:  # a blank-line sized jump starts a new paragraph
            paras.append(" ".join(current))
            current = []
        current.append(line["text"])
    paras.append(" ".join(current))
    # ponytail: uniform spacing between one-line paragraphs merges them; upgrade to indent/sentence rules
    return paras


def _read_pdf(path):
    with pdfplumber.open(path) as pdf:
        pages = [_pdf_page_paragraphs(p) for p in pdf.pages]
    empty = [str(n) for n, p in enumerate(pages, 1) if not p]
    if empty:
        raise ParseError(f"{path.name}: page(s) {', '.join(empty)} have no text layer (scanned?). "
                         "Scanned PDFs are not supported yet.")
    return pages


def _read_docx(path):
    pages, current = [], []
    for p in Document(path).paragraphs:
        if p.text.strip():
            current.append(p.text.strip())
        if 'w:type="page"' in p._p.xml:  # hard page break; docx has no other page numbers
            pages.append(current)
            current = []
    pages.append(current)
    return [p for p in pages if p]  # ponytail: tables and headers are ignored


READERS = {".txt": _read_txt, ".pdf": _read_pdf, ".docx": _read_docx}


def load_para(folder):
    # Returns {(filename,page,para): text} for every supported file
    paras = {}
    for file in sorted(Path(folder).iterdir()):
        read = READERS.get(file.suffix.lower())
        if not read:
            continue
        for page_no, page in enumerate(read(file), 1):
            for para_no, block in enumerate(page, 1):
                paras[(file.name, page_no, para_no)] = block
    return paras


def norm(s):  # lowercase and collapse whitespace
    return re.sub(r"\s+", " ", s or "").strip().lower()
