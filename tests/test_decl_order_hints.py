"""Unit tests for ``c2.commands.decl_order_hints`` -- the Rule 115
candidate detector.

The detector is the asm + source bridge: layer-3 register-identity swap
(from regalloc_explain) ∧ ≥2 named int-class locals at top scope (from
pycparser AST) → name the candidate pair to reorder.

Tests cover:
  * Gate behaviour (layer != 3, no swap rows, no source, <2 locals).
  * Type-class filtering (short / char / float / struct excluded).
  * Hint-schema parsing (both row['hint'] dict and row['rule_hints'] list).
  * Pair refinement (unambiguous N=2 case; closest-line N>2 case).
  * Render output contains the swap regs and the local names.
"""

from __future__ import annotations

import pycparser.c_ast as c_ast
import pytest

from c2.commands import decl_order_hints
from c2.commands.decl_order_hints import (
    DeclOrderHint,
    LocalDecl,
    _canonical,
    _is_int_class,
    _is_reg_swap_row,
    _swap_register_pair,
    _top_scope_int_locals,
    detect,
    render,
    to_json,
)


# ── _canonical: register name canonicalisation ─────────────────────────────

def test_canonical_byte_to_32bit():
    assert _canonical("ch") == "ecx"
    assert _canonical("al") == "eax"
    assert _canonical("BH") == "ebx"


def test_canonical_word_to_32bit():
    assert _canonical("si") == "esi"
    assert _canonical("dx") == "edx"


def test_canonical_already_32bit():
    assert _canonical("esi") == "esi"
    assert _canonical("EBP") == "ebp"


# ── _is_int_class: type-class filtering ────────────────────────────────────

def _make_decl(c_type_text: str) -> c_ast.Decl:
    """Helper: parse ``T name;`` and return its Decl node."""
    from c2.commands.c_source import parse_c
    ast = parse_c(f"void f(void) {{ {c_type_text} x; }}")
    return ast.ext[0].body.block_items[0]


@pytest.mark.parametrize("type_text,expected", [
    ("int", True),
    ("unsigned int", True),
    ("long", True),
    ("signed", True),
    ("unsigned", True),
    ("short", False),
    ("unsigned short", False),
    ("char", False),
    ("signed char", False),
    ("float", False),
    ("double", False),
])
def test_is_int_class_scalar(type_text: str, expected: bool):
    d = _make_decl(type_text)
    assert _is_int_class(d.type) is expected


def test_is_int_class_pointer():
    # Pointers route through DoubleRegs regardless of pointee type.
    d = _make_decl("char *")
    assert _is_int_class(d.type) is True
    d = _make_decl("int *")
    assert _is_int_class(d.type) is True


# ── _top_scope_int_locals: AST extraction ──────────────────────────────────

def _func_def_from_src(src: str) -> tuple[c_ast.FuncDef, int]:
    from c2.commands.c_source import parse_c
    ast = parse_c(src)
    func = ast.ext[0]
    return func, (func.decl.coord.line if func.decl.coord else 1)


def test_top_scope_int_locals_picks_int_skips_short_char():
    src = """
void f(void) {
    int a;
    short b;
    int c;
    char d;
    long e;
}
"""
    func, start = _func_def_from_src(src)
    locals_ = _top_scope_int_locals(func, start)
    names = [l.name for l in locals_]
    assert names == ["a", "c", "e"]


def test_top_scope_int_locals_ignores_nested_scope():
    src = """
void f(void) {
    int a;
    { int b; }       /* nested -- NOT top-scope */
    int c;
}
"""
    func, start = _func_def_from_src(src)
    names = [l.name for l in _top_scope_int_locals(func, start)]
    assert names == ["a", "c"]


def test_top_scope_int_locals_skips_static():
    # `static int` is a different IL path and shouldn't show up.
    src = """
void f(void) {
    int a;
    static int b;
    int c;
}
"""
    func, start = _func_def_from_src(src)
    names = [l.name for l in _top_scope_int_locals(func, start)]
    assert names == ["a", "c"]


# ── Row-hint parsing ───────────────────────────────────────────────────────

def test_is_reg_swap_row_dict_form():
    row = {"kind": "replace", "hint": {"rule": "Reg swap", "summary": "..."}}
    assert _is_reg_swap_row(row) is True


def test_is_reg_swap_row_list_form_legacy():
    row = {"kind": "replace", "rule_hints": [{"rule": "Byte-reg swap"}]}
    assert _is_reg_swap_row(row) is True


def test_is_reg_swap_row_negative():
    assert _is_reg_swap_row({"kind": "equal"}) is False
    assert _is_reg_swap_row({"kind": "replace",
                              "hint": {"rule": "Rule 16"}}) is False


def test_swap_register_pair_backticks():
    """Parses the verify-json format: `ch` / `al` in summary."""
    rows = [{"kind": "replace", "hint": {
        "rule": "Byte-reg swap",
        "summary": "byte-register identity swap (PS uses `ch`, recomp uses `al`)",
        "fix": "...",
    }}]
    pair = _swap_register_pair(rows)
    assert pair == ("ecx", "eax")        # canonicalised to 32-bit


def test_swap_register_pair_arrow_form():
    """Parses the 'register identity swap (ecx↔ebx)' form."""
    rows = [{"kind": "replace", "hint": {
        "rule": "Reg swap",
        "summary": "register identity swap (`ecx`↔`ebx`)",
        "fix": "...",
    }}]
    pair = _swap_register_pair(rows)
    assert pair == ("ecx", "ebx")


def test_swap_register_pair_structured():
    rows = [{"kind": "replace", "hint": {
        "rule": "Reg swap",
        "regs": ["si", "di"],
        "summary": "...",
    }}]
    assert _swap_register_pair(rows) == ("esi", "edi")


# ── detect: full integration with the in-process source index ──────────────

def _stub_source_index(monkeypatch, name: str, src: str):
    """Patch ``_source_index`` to expose a one-function tree."""
    from c2.commands.c_source import parse_c
    ast = parse_c(src)
    func = ast.ext[0]
    start = func.decl.coord.line if func.decl.coord else 1
    monkeypatch.setattr(
        decl_order_hints,
        "_source_index",
        lambda: {name: ("<test>", func, start)},
    )


def _swap_rows(rule: str = "Reg swap",
                summary: str = "register identity swap (`esi`↔`edi`)") -> list[dict]:
    return [
        {"kind": "replace", "ln": None,
         "hint": {"rule": rule, "summary": summary, "fix": ""}},
        {"kind": "replace", "ln": None,
         "hint": {"rule": rule, "summary": summary, "fix": ""}},
    ]


def test_detect_gates_on_layer3(monkeypatch):
    """layer != 3 -> no hint."""
    _stub_source_index(monkeypatch, "f", "void f(void) { int a; int b; }")
    rows = _swap_rows()
    assert detect("f", regalloc_layer=2, diff_rows=rows) is None
    assert detect("f", regalloc_layer=None, diff_rows=rows) is None


def test_detect_no_swap_rows(monkeypatch):
    _stub_source_index(monkeypatch, "f", "void f(void) { int a; int b; }")
    rows = [{"kind": "replace", "ln": 5,
              "hint": {"rule": "Rule 16", "summary": "...", "fix": ""}}]
    assert detect("f", regalloc_layer=3, diff_rows=rows) is None


def test_detect_under_2_locals(monkeypatch):
    _stub_source_index(monkeypatch, "f", "void f(void) { int a; short b; }")
    assert detect("f", regalloc_layer=3, diff_rows=_swap_rows()) is None


def test_detect_unindexed_function(monkeypatch):
    monkeypatch.setattr(decl_order_hints, "_source_index", lambda: {})
    assert detect("unknown", regalloc_layer=3, diff_rows=_swap_rows()) is None


def test_detect_n2_pairs_unambiguously(monkeypatch):
    _stub_source_index(monkeypatch, "f", "void f(void) { int a; int b; b = a; }")
    hint = detect("f", regalloc_layer=3, diff_rows=_swap_rows())
    assert hint is not None
    assert hint.candidate_pair == ("a", "b")
    assert hint.swap_regs == ("esi", "edi")
    assert hint.swap_row_count == 2


def test_detect_n_locals_unrefined_pair(monkeypatch):
    """4 locals + no source-line info -> all locals listed, no narrow pair."""
    _stub_source_index(
        monkeypatch, "f",
        "void f(void) { int a; int b; int c; int d; d=a+b+c; }",
    )
    hint = detect("f", regalloc_layer=3, diff_rows=_swap_rows())
    assert hint is not None
    assert len(hint.locals) == 4
    assert {l.name for l in hint.locals} == {"a", "b", "c", "d"}
    # Cannot pin a refined pair without line refinement.
    assert hint.candidate_pair is None


# ── render / to_json ───────────────────────────────────────────────────────

def _hint(**kw) -> DeclOrderHint:
    base = dict(
        swap_regs=("esi", "edi"),
        layer3_reg_swap=True,
        locals=[
            LocalDecl("text_x", line=2, abs_line=2),
            LocalDecl("text_lines", line=3, abs_line=3),
        ],
        candidate_pair=("text_x", "text_lines"),
        swap_row_count=11,
        actionable=True,
    )
    base.update(kw)
    return DeclOrderHint(**base)


def test_render_names_pair_when_known():
    out = render(_hint())
    assert "ESI↔EDI" in out
    assert "11 row(s)" in out
    assert "`text_x`" in out
    assert "`text_lines`" in out
    assert "Rule 115" in out


def test_render_lists_locals_when_pair_unknown():
    h = _hint(candidate_pair=None,
              locals=[LocalDecl(f"v{i}", line=i, abs_line=i) for i in range(8)])
    out = render(h)
    assert "8 top-scope int locals" in out
    # Truncated to 6 with `…`.
    assert "+2" in out
    assert "Rule 28a lever first" in out


def test_to_json_roundtrip():
    h = _hint()
    data = to_json(h)
    assert data["swap_regs"] == ["esi", "edi"]
    assert data["candidate_pair"] == ["text_x", "text_lines"]
    assert data["actionable"] is True
    assert [l["name"] for l in data["locals"]] == ["text_x", "text_lines"]
