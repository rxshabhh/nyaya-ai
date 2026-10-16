import html
from pathlib import Path
from string import Template

TEMPLATE = Path(__file__).with_name("report_template.html")

BUTTONS = ('<div><button onclick="mark(this,\'ok\')">Confirm</button> '
           '<button onclick="mark(this,\'no\')">Dismiss</button></div>')


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
    return Template(TEMPLATE.read_text(encoding="utf-8")).substitute(
        verified=len(good), rejected_count=len(rejected),
        contradiction_count=len(contradictions), contradictions=cons,
        omission_count=len(omissions), omissions=oms, rejected=rej)
