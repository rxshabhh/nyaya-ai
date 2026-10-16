from .compare import find_contradictions
from .embed import make_similar
from .omissions import find_omissions
from .verify import split_claims


def analyze(claims, paras, docs, embed=None):
    # Verify claims first, then compare only the good ones. `embed` pairs claims outside the event vocabulary.
    good, rejected = split_claims(claims, paras)
    similar = make_similar(embed) if embed else None
    return good, rejected, find_contradictions(good, docs, similar), find_omissions(good, docs, similar)
