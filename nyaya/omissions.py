MATERIAL_HINTS = ("weapon", "knife", "threat", "injur", "kill", "eyewitness", "identif")


def find_omissions(good, docs):
    # Events a witness mentioned in one statement but not in their other one
    results = []
    for w in {docs[c["doc"]]["witness"] for c in good}:
        mine = [c for c in good if docs[c["doc"]]["witness"] == w]
        earlier = {c["event"] for c in mine if docs[c["doc"]]["kind"] == "earlier"}
        court = {c["event"] for c in mine if docs[c["doc"]]["kind"] == "court"}
        if not earlier or not court:
            continue  # need both statements to compare
        for c in mine:
            in_court = docs[c["doc"]]["kind"] == "court"
            if c["event"] not in (earlier if in_court else court):
                material = any(h in c["event"] for h in MATERIAL_HINTS)
                kind = "said first in Court, not told to police" if in_court else "told police, not repeated in Court"
                results.append((material, w, kind, c))
    return sorted(results, key=lambda r: not r[0])  # likely-material first
