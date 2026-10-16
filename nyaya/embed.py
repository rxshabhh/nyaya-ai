import math

DEFAULT_THRESHOLD = 0.75  # ponytail: a guess, not tuned; measure on real cases once the real embedder runs


def cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return dot / norm if norm else 0.0


def make_similar(embed, threshold=DEFAULT_THRESHOLD):
    # similar(a, b): do two claims describe the same event, judged by their quotes
    cache = {}

    def vector(claim):
        quote = claim["exact_quote"]
        if quote not in cache:
            cache[quote] = embed([quote])[0]  # ponytail: one call per quote; batch when the NPU backend lands
        return cache[quote]

    return lambda a, b: cosine(vector(a), vector(b)) >= threshold
