import io
import re
from pathlib import Path
from statistics import median

import pdfplumber
from docx import Document

class ParseError(ValueError):
    """A document cannot be read reliably; the message is shown to the advocate."""


def _split_blocks(text):
    return [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]


def _read_txt(name, data):
    chunks = re.split(r"^\[page \d+\]\s*$", data.decode("utf-8"), flags=re.M)
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


def _read_pdf(name, data):
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        pages = [_pdf_page_paragraphs(p) for p in pdf.pages]
    empty = [str(n) for n, p in enumerate(pages, 1) if not p]
    if empty:
        raise ParseError(f"{name}: page(s) {', '.join(empty)} have no text layer (scanned?). "
                         "Scanned PDFs are not supported yet.")
    return pages


def _read_docx(name, data):
    pages, current = [], []
    for p in Document(io.BytesIO(data)).paragraphs:
        if p.text.strip():
            current.append(p.text.strip())
        if 'w:type="page"' in p._p.xml:  # hard page break; docx has no other page numbers
            pages.append(current)
            current = []
    pages.append(current)
    return [p for p in pages if p]  # ponytail: tables and headers are ignored


READERS = {".txt": _read_txt, ".pdf": _read_pdf, ".docx": _read_docx}


def build_paras(files):
    # files: {filename: bytes} -> {(filename,page,para): text}; nothing is read from disk here
    paras = {}
    for name, data in files.items():
        read = READERS.get(Path(name).suffix.lower())
        if not read:
            raise ParseError(f"{name}: unsupported file type (use .txt, .pdf or .docx)")
        for page_no, page in enumerate(read(name, data), 1):
            for para_no, block in enumerate(page, 1):
                paras[(name, page_no, para_no)] = block
    return paras


def load_para(folder):
    # Same, for a plain folder; files of other types are skipped
    files = {f.name: f.read_bytes() for f in sorted(Path(folder).iterdir())
             if f.suffix.lower() in READERS}
    return build_paras(files)


def norm(s):  # lowercase and collapse whitespace
    return re.sub(r"\s+", " ", s or "").strip().lower()
