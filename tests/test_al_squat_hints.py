"""Tests for the AL-squat int-widen lever gate (Rule 126).

The gate (`_int_widen_candidate`) fires only on the bare-AND byte-mask
shape (≥2 `unsigned char` locals, no shift operators) — the shape where
widening to `int` escapes the AL-squat byte-seat coloring
(get_education_ov_image 92b→44b).  It must NOT fire on shifted siblings
(`(field & MASK) >> n`), which the lever regresses.
"""
from __future__ import annotations

import pycparser.c_ast as c_ast

from c2.commands import al_squat_hints, style_check
from c2.commands.c_source import parse_c


def _index_from(src: str) -> dict:
    ast = parse_c(src, "t.c")
    idx = {}
    for node in ast.ext:
        if isinstance(node, c_ast.FuncDef) and node.decl.name:
            start = node.decl.coord.line if node.decl.coord else 0
            idx[node.decl.name] = ("t.c", node, start)
    return idx


def _run(monkeypatch, src: str, func: str):
    idx = _index_from(src)
    monkeypatch.setattr(style_check, "_source_index", lambda: idx)
    return al_squat_hints._int_widen_candidate(func, "t.c")


BARE_AND = """
void f(void) {
    unsigned char kind;
    unsigned char flags;
    unsigned char school;
    unsigned char academy;
    kind = g[0];
    flags = g[1];
    school = flags & 0x10;
    academy = flags & 0x20;
    out[0] = kind + school + academy;
}
"""

SHIFTED = """
void f(void) {
    unsigned char kind;
    unsigned char flags;
    unsigned char theatre;
    unsigned char arena;
    kind = g[0];
    flags = g[1];
    theatre = flags & 3;
    arena = (flags & 0xc) >> 2;
    out[0] = kind + theatre + arena;
}
"""

ONE_LOCAL = """
void f(void) {
    unsigned char kind;
    kind = g[0] & 0xf;
    out[0] = kind;
}
"""


def test_bare_and_fires(monkeypatch):
    got = _run(monkeypatch, BARE_AND, "f")
    assert got is not None
    assert set(got) == {"kind", "flags", "school", "academy"}


def test_shifted_excluded(monkeypatch):
    # A `>>` anywhere in the body suppresses the lever (regressing sibling).
    assert _run(monkeypatch, SHIFTED, "f") is None


def test_single_local_excluded(monkeypatch):
    # Needs ≥2 unsigned char locals.
    assert _run(monkeypatch, ONE_LOCAL, "f") is None


def test_unknown_function(monkeypatch):
    assert _run(monkeypatch, BARE_AND, "nonexistent") is None
