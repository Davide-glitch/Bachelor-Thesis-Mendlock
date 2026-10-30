"""Exact UTF-8 byte-span AST source patcher for Python test files."""
from __future__ import annotations

import ast
import difflib
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class PatchResult:
    path: str
    line: int
    old: str
    new: str
    replaced: int
    diff: str
    applied: bool


def _literals(tree: ast.AST, line: int, old: str, method: str) -> list:
    hits = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        name = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", None)
        if name != method or not (node.lineno <= line <= (node.end_lineno or node.lineno)):
            continue
        for a in list(node.args) + [k.value for k in node.keywords]:
            if isinstance(a, ast.Constant) and isinstance(a.value, str) and a.value == old:
                hits.append(a)
    return hits


def patch_selector(path, line: int, old: str, new: str, *, method: str = "click",
                   apply: bool = False) -> PatchResult | None:
    p = Path(path)
    data = p.read_bytes()
    hits = _literals(ast.parse(data.decode("utf-8")), line, old, method)
    if not hits:
        return None
    starts = [0]
    for ln in data.splitlines(keepends=True):
        starts.append(starts[-1] + len(ln))
    edits = []
    for a in hits:
        s = starts[a.lineno - 1] + a.col_offset
        e = starts[a.end_lineno - 1] + a.end_col_offset
        single = data[s:e].lstrip(b"rRuU")[:1] == b"'"
        literal = repr(new) if single else json.dumps(new, ensure_ascii=False)
        edits.append((s, e, literal.encode("utf-8")))
    out = data
    for s, e, lit in sorted(edits, reverse=True):
        out = out[:s] + lit + out[e:]
    diff = "".join(difflib.unified_diff(
        data.decode("utf-8").splitlines(keepends=True),
        out.decode("utf-8").splitlines(keepends=True),
        fromfile=f"a/{p.name}",
        tofile=f"b/{p.name}",
    ))
    if apply:
        p.write_bytes(out)
    return PatchResult(str(p), line, old, new, len(edits), diff, apply)