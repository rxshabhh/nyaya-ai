from .parse import norm


def verify(claim, paras):
    # Return None if claim is OK, else the rejection reason
    key = (claim["doc"], claim["page"], claim["para"])
    if key not in paras:
        return "cited page/paragraph does not exist"
    quote = norm(claim["exact_quote"])
    if quote not in norm(paras[key]):
        return "quote not found at the cited paragraph"
    for field in ("date", "time", "place", "amount"):
        if claim.get(field) and norm(claim[field]) not in quote:
            return f"{field} '{claim[field]}' is not in the quote"
    return None


def split_claims(claims, paras):
    good, rejected = [], []
    for c in claims:
        reason = verify(c, paras)
        if reason:
            rejected.append((c, reason))
        else:
            good.append(c)
    return good, rejected
