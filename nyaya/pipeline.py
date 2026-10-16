from .compare import find_contradictions
from .omissions import find_omissions
from .verify import split_claims


def analyze(claims, paras, docs):
    # Verify claims first, then compare only the good ones
    good, rejected = split_claims(claims, paras)
    return good, rejected, find_contradictions(good, docs), find_omissions(good, docs)
