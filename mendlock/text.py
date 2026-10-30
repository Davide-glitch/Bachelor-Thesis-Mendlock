"""Text similarity backends (lexical character trigrams and optional SBERT)."""
from __future__ import annotations

import math
import re
from collections import Counter

from .native_bridge import native_trigram_cosine

_WORD = re.compile(r"[a-z0-9]+")
_STOP = {
    "the", "a", "an", "and", "or", "to", "of", "on", "in", "for", "with",
    "your", "my", "this", "that", "button", "click", "press", "please",
}


def norm(s: str) -> str:
    return " ".join(_WORD.findall((s or "").lower()))


def tokens(s: str) -> list[str]:
    return [t for t in _WORD.findall((s or "").lower()) if t not in _STOP]


def stem(t: str) -> str:
    for suf in ("ing", "ed", "es", "s"):
        if len(t) > len(suf) + 2 and t.endswith(suf):
            return t[: -len(suf)]
    return t


def trigrams(s: str) -> Counter:
    n = norm(s)
    if not n:
        return Counter()
    n = f"  {n} "
    return Counter(n[i : i + 3] for i in range(len(n) - 2))


def cosine(a: Counter, b: Counter) -> float:
    if not a or not b:
        return 0.0
    dot = sum(v * b.get(k, 0) for k, v in a.items())
    den = math.sqrt(sum(v * v for v in a.values())) * math.sqrt(sum(v * v for v in b.values()))
    return dot / den if den else 0.0


def trigram_sim(a: str, b: str) -> float:
    na, nb = norm(a), norm(b)
    if not na or not nb:
        return 0.0
    res = native_trigram_cosine(na, nb)
    if res is not None:
        return res
    return cosine(trigrams(na), trigrams(nb))


def jaccard(a, b) -> float:
    sa, sb = set(a), set(b)
    return len(sa & sb) / len(sa | sb) if (sa or sb) else 0.0


def _prep(s: str) -> str:
    return " ".join(stem(t) for t in tokens(s))


class LexicalBackend:
    name = "lexical"

    def sim(self, query: str, texts: list[str]) -> list[float]:
        qp = _prep(query)
        q_tri = trigrams(qp)
        out = []
        for t in texts:
            tp = _prep(t)
            nat = native_trigram_cosine(qp, tp)
            out.append(nat if nat is not None else cosine(q_tri, trigrams(tp)))
        return out


class SbertBackend:
    name = "sbert"

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        from sentence_transformers import SentenceTransformer
        self._m = SentenceTransformer(model_name)

    def sim(self, query: str, texts: list[str]) -> list[float]:
        if not texts:
            return []
        vecs = self._m.encode([query] + list(texts), normalize_embeddings=True)
        return [float(max(0.0, v @ vecs[0])) for v in vecs[1:]]


def get_backend(name: str = "lexical"):
    if name == "lexical":
        return LexicalBackend()
    if name == "sbert":
        return SbertBackend()
    raise ValueError(f"Unknown text backend {name!r}; expected 'lexical' or 'sbert'")