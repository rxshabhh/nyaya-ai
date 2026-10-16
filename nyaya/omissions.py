from .compare import same_event


def omission_code(label):  # stable machine name for the human label find_omissions returns
    return "court_only" if label.startswith("said first") else "earlier_only"


MATERIAL_HINTS = ("weapon", "knife", "threat", "injur", "kill", "eyewitness", "identif")


def find_omissions(good, docs, similar=None):
    # Events a witness mentioned in one statement but not in their other one
    results = []
    for w in {docs[c["doc"]]["witness"] for c in good}:
        # "other" claims cannot be matched without an embedder, so they are left out rather than all flagged
        mine = [c for c in good if docs[c["doc"]]["witness"] == w and (c["event"] != "other" or similar)]
        earlier = [c for c in mine if docs[c["doc"]]["kind"] == "earlier"]
        court = [c for c in mine if docs[c["doc"]]["kind"] == "court"]
        if not earlier or not court:
            continue  # need both statements to compare
        for c in mine:
            in_court = docs[c["doc"]]["kind"] == "court"
            if not any(same_event(c, o, similar) for o in (earlier if in_court else court)):
                label = f'{c["event"]} {c.get("event_text", "")}'
                material = any(h in label for h in MATERIAL_HINTS)
                kind = "said first in Court, not told to police" if in_court else "told police, not repeated in Court"
                results.append((material, w, kind, c))
    return sorted(results, key=lambda r: not r[0])  # likely-material first
