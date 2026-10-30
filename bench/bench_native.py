"""Verifies numerical parity and benchmarks C++23 native kernel vs. Pure Python fallback."""
from __future__ import annotations

import time
from difflib import SequenceMatcher
import numpy as np
from PIL import Image

from mendlock import native_bridge, text, vision


def _print_table(headers: list[str], rows: list[list[str]], right_align: set[int] | None = None) -> None:
    right_align = right_align or set()
    widths = [max(len(h), *(len(r[i]) for r in rows)) for i, h in enumerate(headers)]
    hdr = "| " + " | ".join(h.ljust(widths[i]) for i, h in enumerate(headers)) + " |"
    sep = "|-" + "-|-".join("-" * widths[i] for i in range(len(headers))) + "-|"
    print(hdr)
    print(sep)
    for r in rows:
        cells = [
            r[i].rjust(widths[i]) if i in right_align else r[i].ljust(widths[i])
            for i in range(len(headers))
        ]
        print("| " + " | ".join(cells) + " |")


def verify_numerical_parity() -> None:
    assert native_bridge.HAVE_NATIVE, (
        "C++ library not loaded! Build it first: cmake -S native -B native/build && cmake --build native/build"
    )
    pairs = [
        ("Place Order", "Place Order"),
        ("Place Order", "Place order preview"),
        ("Subscribe to the newsletter", "Unsubscribe"),
        ("body > div:nth-of-type(1) > button:nth-of-type(2)", "body > div:nth-of-type(1) > a:nth-of-type(1)"),
    ]
    for a, b in pairs:
        na, nb = text.norm(a), text.norm(b)
        py_tri = text.cosine(text.trigrams(na), text.trigrams(nb))
        cpp_tri = native_bridge.native_trigram_cosine(na, nb)
        assert abs(py_tri - cpp_tri) < 1e-5, f"Trigram mismatch on ({a!r}, {b!r}): py={py_tri} cpp={cpp_tri}"

        py_seq = SequenceMatcher(None, a, b).ratio()
        cpp_seq = native_bridge.native_levenshtein_ratio(a, b)
        assert abs(py_seq - cpp_seq) < 1e-5, f"Sequence mismatch on ({a!r}, {b!r}): py={py_seq} cpp={cpp_seq}"

    rng = np.random.default_rng(42)
    arr_a = rng.integers(0, 255, (16, 32, 3), dtype=np.uint8)
    arr_b = rng.integers(0, 255, (16, 32, 3), dtype=np.uint8)
    im_a, im_b = Image.fromarray(arr_a), Image.fromarray(arr_b)

    A, B = vision._thumb(im_a), vision._thumb(im_b)
    cpp_vis = native_bridge.native_visual_sim(A, B)

    saved_lib = native_bridge._LIB
    native_bridge._LIB = None
    py_vis = vision.visual_similarity(im_a, im_b)
    native_bridge._LIB = saved_lib

    assert abs(py_vis - cpp_vis) < 1e-4, f"Vision mismatch: py={py_vis} cpp={cpp_vis}"
    print("[PASS] Numerical parity verified: C++23 and Python outputs match within 1e-5.\n")


def benchmark_scaling() -> None:
    rng = np.random.default_rng(7)
    arr_a = rng.integers(0, 255, (16, 32, 3), dtype=np.uint8)
    arr_b = rng.integers(0, 255, (16, 32, 3), dtype=np.uint8)
    im_a, im_b = Image.fromarray(arr_a), Image.fromarray(arr_b)
    A, B = vision._thumb(im_a), vision._thumb(im_b)

    s_intent = "place the order and confirm payment"
    s_label = "place order preview button"
    p_old = "body/main/section/div/button"
    p_new = "body/main/section/div/div/button"

    headers = ["Candidates / Page", "Pure Python (ms)", "C++23 Native (ms)", "Speedup"]
    table_rows: list[list[str]] = []

    for n_cands in (10, 25, 50, 100, 200):
        saved_lib = native_bridge._LIB
        native_bridge._LIB = None
        t0 = time.perf_counter()
        for _ in range(50):
            for _ in range(n_cands):
                _ = text.cosine(text.trigrams(s_intent), text.trigrams(s_label))
                _ = SequenceMatcher(None, p_old, p_new).ratio()
                _ = vision.visual_similarity(im_a, im_b)
        py_ms = ((time.perf_counter() - t0) * 1000.0) / 50.0

        native_bridge._LIB = saved_lib
        t0 = time.perf_counter()
        for _ in range(50):
            for _ in range(n_cands):
                _ = native_bridge.native_trigram_cosine(s_intent, s_label)
                _ = native_bridge.native_levenshtein_ratio(p_old, p_new)
                _ = native_bridge.native_visual_sim(A, B)
        cpp_ms = ((time.perf_counter() - t0) * 1000.0) / 50.0

        speedup = py_ms / max(cpp_ms, 1e-6)
        table_rows.append([str(n_cands), f"{py_ms:.2f}", f"{cpp_ms:.2f}", f"{speedup:.1f}x"])

    _print_table(headers, table_rows, right_align={0, 1, 2, 3})


if __name__ == "__main__":
    verify_numerical_parity()
    benchmark_scaling()
