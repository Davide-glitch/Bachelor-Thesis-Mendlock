"""Visual similarity using structural gradient correlation and normalized cross-correlation."""
from __future__ import annotations

import base64
import io

import numpy as np
from PIL import Image

from .native_bridge import native_visual_sim

THUMB = (32, 16)


def decode_png(png: bytes) -> Image.Image:
    return Image.open(io.BytesIO(png)).convert("RGB")


def crop_bbox(img: Image.Image, bbox):
    x, y, w, h = bbox
    left, top = max(0, int(round(x))), max(0, int(round(y)))
    right, bottom = min(img.width, int(round(x + w))), min(img.height, int(round(y + h)))
    if right - left < 3 or bottom - top < 3:
        return None
    return img.crop((left, top, right, bottom))


def encode_b64(img: Image.Image, max_side: int = 96) -> str:
    im = img.copy()
    im.thumbnail((max_side, max_side))
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def decode_b64(s: str) -> Image.Image:
    return Image.open(io.BytesIO(base64.b64decode(s))).convert("RGB")


def _thumb(img: Image.Image) -> np.ndarray:
    return np.asarray(img.resize(THUMB, Image.BILINEAR), dtype=np.float32) / 255.0


def _ncc(x: np.ndarray, y: np.ndarray) -> float:
    sx, sy = float(x.std()), float(y.std())
    if sx < 1e-3 or sy < 1e-3:
        return 1.0 if (sx < 1e-3 and sy < 1e-3) else 0.0
    return max(0.0, float(((x - x.mean()) * (y - y.mean())).mean() / (sx * sy)))


def visual_similarity(a: Image.Image, b: Image.Image) -> float:
    """Combines edge-gradient NCC (50%), luminance NCC (30%), and color similarity (20%)."""
    A, B = _thumb(a), _thumb(b)
    nat = native_visual_sim(A, B)
    if nat is not None:
        return nat

    color = 1.0 - float(np.abs(A.mean(axis=(0, 1)) - B.mean(axis=(0, 1))).mean())
    ga, gb = A.mean(axis=2), B.mean(axis=2)
    lum_ncc = _ncc(ga.ravel(), gb.ravel())

    gx_a = np.diff(ga, axis=1)
    gy_a = np.diff(ga, axis=0)
    mag_a = np.hypot(gx_a[:-1, :], gy_a[:, :-1]).ravel()

    gx_b = np.diff(gb, axis=1)
    gy_b = np.diff(gb, axis=0)
    mag_b = np.hypot(gx_b[:-1, :], gy_b[:, :-1]).ravel()

    grad_ncc = _ncc(mag_a, mag_b)
    return float(0.20 * color + 0.30 * lum_ncc + 0.50 * grad_ncc)