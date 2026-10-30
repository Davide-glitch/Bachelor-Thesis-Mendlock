"""Multi-signal feature extraction comparing candidates against a recorded fingerprint."""
from __future__ import annotations

import math
import re
from difflib import SequenceMatcher

import numpy as np

from . import vision
from .native_bridge import native_levenshtein_ratio
from .text import jaccard, norm, trigram_sim

FEATURES = [
    "tag_match", "role_match", "text_sim", "text_exact", "attr_sim", "class_sim", "id_sim",
    "path_sim", "pos_sim", "size_sim", "vis_sim", "intent_sim", "ctx_sim",
]

GROUPS = {
    "visual": ["vis_sim"],
    "intent": ["intent_sim", "ctx_sim"],
    "geometry": ["pos_sim", "size_sim"],
    "structure": ["tag_match", "role_match", "path_sim"],
    "attributes": ["attr_sim", "class_sim", "id_sim"],
    "text": ["text_sim", "text_exact"],
}


def own_text(c) -> str:
    return c.text or c.attrs.get("aria-label", "") or c.attrs.get("value", "") or c.attrs.get("title", "")


def label_of(c) -> str:
    a = c.attrs
    id_words = " ".join(re.findall(r"[A-Za-z]{3,}", c.id))
    parts = [c.text, a.get("aria-label", ""), a.get("title", ""), a.get("value", ""), a.get("placeholder", ""), id_words]
    return " ".join(p for p in parts if p)


def _attr_tokens(c) -> set:
    return {f"{k}={v}" for k, v in c.attrs.items() if k != "id" and v}


def _id_key(s: str) -> str:
    return re.sub(r"\d+", "#", s.lower())


def _seq_sim(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    nat = native_levenshtein_ratio(a, b)
    if nat is not None:
        return nat
    return SequenceMatcher(None, a, b).ratio()


def _center(bbox, dw: float, dh: float):
    return ((bbox[0] + bbox[2] / 2) / max(dw, 1.0), (bbox[1] + bbox[3] / 2) / max(dh, 1.0))


def compute(fp, cands: list, intent: str, crops: list, backend, doc_size) -> np.ndarray:
    n = len(cands)
    X = np.zeros((n, len(FEATURES)), dtype=float)
    if n == 0:
        return X
    old = fp.element
    intent_s = backend.sim(intent, [label_of(c) for c in cands])
    ctx_s = backend.sim(intent, [c.context for c in cands])
    old_text = own_text(old)
    old_norm = norm(old_text)
    old_attrs = _attr_tokens(old)
    old_center = _center(old.bbox, fp.doc_size[0], fp.doc_size[1])
    ow, oh = max(old.bbox[2], 1e-6), max(old.bbox[3], 1e-6)
    ref = vision.decode_b64(fp.ref_png_b64) if fp.ref_png_b64 else None
    old_id_k = _id_key(old.id)
    old_path_str = "/".join(old.path)

    for i, c in enumerate(cands):
        t = own_text(c)
        t_norm = norm(t)
        exact = float(bool(old_norm) and old_norm == t_norm)
        t_sim = trigram_sim(old_text, t)
        dist = math.dist(old_center, _center(c.bbox, doc_size[0], doc_size[1]))
        w, h = max(c.bbox[2], 1e-6), max(c.bbox[3], 1e-6)
        X[i] = [
            float(c.tag == old.tag),
            float(bool(old.role) and c.role == old.role),
            t_sim,
            exact,
            jaccard(old_attrs, _attr_tokens(c)),
            jaccard(old.classes, c.classes),
            _seq_sim(old_id_k, _id_key(c.id)) if (old.id and c.id) else 0.0,
            _seq_sim(old_path_str, "/".join(c.path)),
            max(0.0, 1.0 - dist / 0.75),
            (min(w, ow) / max(w, ow)) * (min(h, oh) / max(h, oh)),
            vision.visual_similarity(ref, crops[i]) if (ref is not None and crops[i] is not None) else 0.0,
            intent_s[i],
            ctx_s[i],
        ]
    return X