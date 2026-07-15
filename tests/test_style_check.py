"""Tests for the decomp-verify source style check (c2/commands/style_check.py).

The checker is AST-based (pycparser), so these exercise real parse trees,
not regex matches.
"""

from c2.commands.style_check import detect_style_hints_in_body


def _cats(body):
    return {(h.severity, h.category) for h in detect_style_hints_in_body(body)}


# ── not-observed (warn) ──────────────────────────────────────────────────────

def test_register_keyword_warns():
    assert ("warn", "register") in _cats("void f(register int x){ return; }")


def test_register_local_warns():
    assert ("warn", "register") in _cats("void f(void){ register int x = 0; g(x); }")


def test_yoda_warns():
    assert ("warn", "yoda") in _cats("void f(int x){ if(3==x) g(); }")


def test_yoda_in_logical_chain_warns():
    assert ("warn", "yoda") in _cats("void f(int x){ if(a && 5==x) g(); }")


def test_arithmetic_left_operand_is_not_yoda():
    # `selected - 1 == shown`: the literal 1 is part of a larger expression.
    assert ("warn", "yoda") not in _cats("void f(void){ if(selected-1==shown) g(); }")


def test_var_eq_literal_is_not_yoda():
    assert ("warn", "yoda") not in _cats("void f(int x){ if(x==3) g(); }")


def test_c99_mixed_decl_warns():
    assert ("warn", "c99-decl") in _cats("void f(void){ int a; a=1; int b; b=2; }")


def test_c89_top_decls_ok():
    assert ("warn", "c99-decl") not in _cats("void f(void){ int a; int b; a=1; b=2; }")


def test_multi_declarator_warns():
    body = "void f(void){\n int a, b;\n a=1; b=2;\n}"
    assert ("warn", "multi-decl") in _cats(body)


def test_multi_declarator_with_inits_warns():
    body = "void f(void){\n int a = 0, b = 0;\n a=b;\n}"
    assert ("warn", "multi-decl") in _cats(body)


def test_one_per_line_decls_ok():
    body = "void f(void){\n int a;\n int b;\n a=1; b=2;\n}"
    assert ("warn", "multi-decl") not in _cats(body)


def test_pointer_to_array_decl_not_flagged():
    body = "void f(void){ int (*l)[20]=p; int r; g(); }"
    assert ("warn", "c99-decl") not in _cats(body)


def test_array_initializer_not_flagged():
    body = "void f(void){ int x[4]={1,2,3,4}; int i; g(); }"
    assert ("warn", "c99-decl") not in _cats(body)


def test_register_qualified_decl_no_c99_cascade():
    body = "void f(void){ register unsigned char t; unsigned char k; g(); }"
    cats = _cats(body)
    assert ("warn", "register") in cats
    assert ("warn", "c99-decl") not in cats


def test_nested_ternary_warns():
    assert ("warn", "nested-ternary") in _cats("int f(int x){ return x?1:x?2:3; }")


def test_assign_in_if_warns():
    assert ("warn", "assign-in-if") in _cats("void f(void){ if((p=q)) g(); }")


def test_assign_in_while_is_intentional_not_flagged():
    # while-assignment IS house style (string_to_upper, get_free_memory).
    body = "void f(char *s){ char c; while((c=*s)!=0) s++; }"
    cats = _cats(body)
    assert ("warn", "assign-in-if") not in cats
    assert all(sev != "warn" for sev, _ in cats)


# ── noise (info) ─────────────────────────────────────────────────────────────

def test_single_ternary_is_not_flagged():
    # A plain ternary is the correct Rule 82 idiom — must NOT warn or noise.
    assert _cats("int f(int x){ return x==0?8:x; }") == set()


def test_while1_is_noise():
    assert ("info", "noise-while1") in _cats("void f(void){ while(1){ g(); } }")


def test_if_not_is_noise():
    assert ("info", "noise-not") in _cats("void f(int x){ if(!x) g(); }")


def test_shl1_is_noise():
    assert ("info", "noise-shl1") in _cats("int f(int x){ return x<<1; }")


def test_scope_block_is_noise():
    assert ("info", "noise-scope") in _cats("void f(void){ g(); { int d=1; h(d); } }")


# ── dedup: repeated noise of the same category collapses ─────────────────────

def test_repeated_noise_deduped():
    body = "void f(int a,int b){ if(!a) g(); if(!b) h(); }"
    nots = [h for h in detect_style_hints_in_body(body)
            if h.category == "noise-not"]
    assert len(nots) == 1


# ── precision: canonical-style function produces no hints ────────────────────

def test_canonical_function_is_clean():
    body = ("int mouse_in_area(int x, int y, int w, int h){\n"
            "    if (x > mouse_x)      goto fail;\n"
            "    if (x + w <= mouse_x) goto fail;\n"
            "    return 1;\n"
            "fail:\n"
            "    return 0;\n"
            "}")
    assert _cats(body) == set()


def test_unparseable_body_returns_empty():
    assert detect_style_hints_in_body("this is not C") == []


# ── Rule 113: 2-D cell offset operand order (row-first vs column-first) ───────

def test_offset_row_first_flagged():
    # `(y*W + x)*C` with a map-width stride — row term on the left.
    assert ("info", "offset-order") in _cats(
        "void f(int x,int y){ int s; s=(y*80+x)*20; g(s); }")


def test_offset_column_first_ok():
    # `(x + y*W)*C` — column-first is the PS form; not flagged.
    assert ("info", "offset-order") not in _cats(
        "void f(int x,int y){ int s; s=(x+y*80)*20; g(s); }")


def test_offset_bare_pseudo_map_row_first_flagged():
    # PM_OFF-style `(y*W + x)` with no cell-byte multiply still flags.
    assert ("info", "offset-order") in _cats(
        "void f(int x,int y){ int s; s=y*81+x; g(s); }")


def test_offset_small_multiply_not_flagged():
    # `a*4 + b` is not a 2-D offset (stride < 16) — no false positive.
    assert ("info", "offset-order") not in _cats(
        "void f(int a,int b){ int c; c=a*4+b; g(c); }")


def test_offset_both_strided_not_flagged():
    # Ambiguous `a*80 + b*8` (both strided) — skipped, no FP.
    assert ("info", "offset-order") not in _cats(
        "void f(int a,int b){ int c; c=a*80+b*8; g(c); }")
