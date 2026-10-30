"""C/C++ native compute bridge via ctypes with automatic Python fallback."""
from __future__ import annotations

import ctypes
from pathlib import Path
import numpy as np

_LIB = None
_SEARCH_PATHS = [
    Path(__file__).parent / "native" / "libmendlock_core.so",
    Path(__file__).parent / "native" / "libmendlock_core.dylib",
    Path(__file__).parent / "native" / "mendlock_core.dll",
    Path(__file__).parent.parent / "native" / "build" / "libmendlock_core.so",
    Path(__file__).parent.parent / "native" / "build" / "mendlock_core.dll",
]

for _p in _SEARCH_PATHS:
    if _p.exists():
        try:
            _LIB = ctypes.CDLL(str(_p.resolve()))
            _LIB.mendlock_trigram_cosine.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
            _LIB.mendlock_trigram_cosine.restype = ctypes.c_float

            _LIB.mendlock_levenshtein_ratio.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
            _LIB.mendlock_levenshtein_ratio.restype = ctypes.c_float

            _LIB.mendlock_visual_similarity.argtypes = [
                ctypes.POINTER(ctypes.c_float),
                ctypes.POINTER(ctypes.c_float),
                ctypes.c_int,
                ctypes.c_int,
            ]
            _LIB.mendlock_visual_similarity.restype = ctypes.c_float
            break
        except OSError:
            _LIB = None

HAVE_NATIVE = _LIB is not None


def native_trigram_cosine(a: str, b: str) -> float | None:
    if _LIB is None:
        return None
    return float(_LIB.mendlock_trigram_cosine(a.encode("utf-8"), b.encode("utf-8")))


def native_levenshtein_ratio(a: str, b: str) -> float | None:
    if _LIB is None:
        return None
    return float(_LIB.mendlock_levenshtein_ratio(a.encode("utf-8"), b.encode("utf-8")))


def native_visual_sim(a: np.ndarray, b: np.ndarray) -> float | None:
    if _LIB is None:
        return None
    a_c = np.ascontiguousarray(a, dtype=np.float32)
    b_c = np.ascontiguousarray(b, dtype=np.float32)
    h, w = a_c.shape[:2]
    ptr_a = a_c.ctypes.data_as(ctypes.POINTER(ctypes.c_float))
    ptr_b = b_c.ctypes.data_as(ctypes.POINTER(ctypes.c_float))
    return float(_LIB.mendlock_visual_similarity(ptr_a, ptr_b, int(w), int(h)))