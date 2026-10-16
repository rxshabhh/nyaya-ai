# Nyaya AI input spec (v1)

## Files accepted

| Format | How it is read | Notes |
|---|---|---|
| `.txt` | Used as is | Page breaks marked `[page N]` on their own line |
| Digital `.pdf` | Text layer per real page | Scanned PDFs are detected (no text layer) and refused with a clear message |
| `.docx` | Paragraphs in order | No page numbers in docx, so the whole file is page 1 unless it has hard page breaks |

Language: English. Encoding: UTF-8. No OCR in v1.

## Paragraph addressing

Every paragraph is addressed `(document, page, paragraph)`, both 1-based. A paragraph is a block of text between blank lines (`.txt`), a PDF text block, or a docx paragraph. This address is the citation shown to the advocate and the key the verification gate checks against.

## Document kinds

Each uploaded document gets metadata, entered on an upload form with filename hints prefilled and confirmed by the advocate.

| doctype | Side | Meaning |
|---|---|---|
| `police_statement` | earlier | Statement recorded by police (s.180 BNSS, formerly s.161 CrPC) |
| `fir` | earlier | First information report, the informant's earlier statement |
| `chargesheet` | earlier | Contains several witnesses' statements, split per witness (below) |
| `examination_in_chief` | court | Court testimony led by the party calling the witness |
| `cross_examination` | court | Court testimony under cross, same side as `examination_in_chief` |

Required per document: `witness` (the person), `doctype`, `date` (DD.MM.YYYY). The `side` (`earlier` or `court`) follows from the doctype. A witness's `examination_in_chief` and `cross_examination` count together as that witness's court testimony.

## Chargesheet splitting

A chargesheet holds many witnesses. The app looks for headings such as `Statement of PW-2 ...` or `Statement of Witness No. 2` and proposes sections. The advocate confirms or corrects the split on the upload form. Each section is then treated as its own `police_statement` for that witness, with the chargesheet name and page kept in the citation.

## Witness identity

`case.json` `aliases` maps names and roles to one person (PW-1, PW1, complainant, Ramesh). The form lets the advocate add aliases once per case. Matching is exact on the normalised alias. No fuzzy matching in v1.

## Claim schema (extractor output, verifier input)

```
doc, page, para                 citation; must exist
witness                         canonical name after alias resolution
actor                           who did the thing
event                           snake_case label from the event vocabulary
date, time, place, amount       optional; each must appear inside exact_quote
exact_quote                     must appear in the cited paragraph
```

Change from today: `witness` is added to the claim so pairing no longer depends on looking the document up. Event vocabulary is defined with the extractor step.

## Pairing rule (target, not yet implemented)

Compare claims only for the same `witness`, earlier side against court side, same `event`. Today's code compares any two documents; fixing that is a separate tested step.

## Output

For each case: contradictions (field-level differences with both quotes), omissions (ranked, likely-material first), and rejected claims with reasons. Every finding carries its citations and a Confirm or Dismiss state saved in the case database.
