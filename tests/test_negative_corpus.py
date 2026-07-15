"""Tests for the negative-corpus tool (c2/commands/negative_corpus.py).

Feature extraction is exercised on real parse trees; the stratified-lift
math is exercised on synthetic populations (no Watcom container needed).
"""

import math

import pycparser.c_ast as c_ast

from c2.commands.c_source import parse_c
from c2.commands.negative_corpus import (
    extract_features, compute_model, _score_function, _size_bucket,
    rank_functions, feature_table,
)


def _features(body: str) -> dict[str, int]:
    ast = parse_c(body, "<t>")
    func = next(n for n in ast.ext if isinstance(n, c_ast.FuncDef))
    return extract_features(func)


# ── AST feature extraction ───────────────────────────────────────────────────

def test_ternary_detected():
    assert "ternary" in _features("int f(int x){ return x==0?8:x; }")


def test_nested_ternary_detected():
    f = _features("int f(int x){ return x?1:x?2:3; }")
    assert "ternary" in f and "nested-ternary" in f


def test_switch_detected():
    assert "switch" in _features(
        "int f(int x){ switch(x){case 1: return 2; default: return 0;} }")


def test_goto_detected():
    assert "goto" in _features(
        "int f(int x){ if(x) goto e; return 1; e: return 0; }")


def test_multi_return():
    assert "multi-return" in _features(
        "int f(int x){ if(x) return 1; return 0; }")
    assert "multi-return" not in _features("int f(int x){ return x; }")


def test_many_locals():
    body = "int f(void){" + "".join(f"int v{i};" for i in range(12)) + "g(); return 0; }"
    assert "many-locals>=10" in _features(body)
    assert "many-locals>=10" not in _features("int f(void){ int a; int b; return a+b; }")


def test_compound_assign():
    assert "compound-assign" in _features("void f(int x){ x += 2; }")


def test_shl1():
    assert "shl1" in _features("int f(int x){ return x<<1; }")


def test_deep_nest():
    body = ("int f(int a){ if(a){ if(a){ while(a){ if(a){ return 1; } } } } "
            "return 0; }")
    assert "deep-nest>=4" in _features(body)


def test_ptr_cache():
    f = _features("void f(void){ char *p = &arr[i]; g(p); }")
    assert "ptr-cache" in f


def test_register_keyword():
    assert "register" in _features("void f(void){ register int x=0; g(x); }")


def test_clean_function_few_features():
    f = _features("int add(int a, int b){ return a + b; }")
    assert "ternary" not in f and "goto" not in f and "switch" not in f


# ── size buckets ─────────────────────────────────────────────────────────────

def test_size_buckets():
    assert _size_bucket(10) == "<80"
    assert _size_bucket(100) == "80-200"
    assert _size_bucket(300) == "200-500"
    assert _size_bucket(900) == "500+"


# ── stratified-lift model ────────────────────────────────────────────────────

def _synthetic():
    """A population where 'smell' is size-confounded but still has residual
    lift, and 'neutral' is pure size confound.

    Big functions (size 600) diff at a high base rate; small (size 50) rarely.
    'smell' appears in all big functions that diff AND a few small exact ones.
    """
    funcs = {}
    # 10 small exact, 2 small diff (base small-rate low)
    for i in range(10):
        funcs[f"se{i}"] = ({"neutral": 1}, 50, False)
    for i in range(2):
        funcs[f"sd{i}"] = ({"neutral": 1, "smell": 1}, 50, True)
    # 10 big diff (smell), 4 big exact (neutral) — within big bucket smell
    # still over-represented among diffs
    for i in range(10):
        funcs[f"bd{i}"] = ({"neutral": 1, "smell": 1}, 600, True)
    for i in range(4):
        funcs[f"be{i}"] = ({"neutral": 1}, 600, False)
    return funcs


def test_model_base_rate_per_bucket():
    m = compute_model(_synthetic())
    # small bucket: 2 diff / 12 ; big bucket: 10 diff / 14
    assert math.isclose(m.base_rate["<80"], 2 / 12, rel_tol=1e-6)
    assert math.isclose(m.base_rate["500+"], 10 / 14, rel_tol=1e-6)


def test_neutral_feature_has_unit_lift():
    m = compute_model(_synthetic())
    # 'neutral' is carried by everyone, so observed == expected → lift ~1.
    assert math.isclose(m.stats["neutral"].lift, 1.0, rel_tol=1e-6)


def test_smell_has_lift_above_one():
    m = compute_model(_synthetic())
    st = m.stats["smell"]
    # raw enrichment is large, but the key assertion is the size-controlled
    # lift is > 1 (over-represented among diffs even controlling for size).
    assert st.lift > 1.0
    assert st.enrichment > st.lift  # confound inflates raw enrichment


def test_score_rewards_smell_carriers():
    m = compute_model(_synthetic())
    smell_fn = _score_function("bd0", m)
    neutral_fn = _score_function("be0", m)
    assert smell_fn.score > neutral_fn.score


def test_rank_functions_diff_only_by_default():
    m = compute_model(_synthetic())
    names = {f.name for f in rank_functions(m)}
    # exact functions excluded by default; diffing ones present
    assert "be0" not in names and "se0" not in names
    assert "bd0" in names
    # --all includes exact
    all_names = {f.name for f in rank_functions(m, include_exact=True)}
    assert "be0" in all_names


def test_feature_table_sorted_by_lift():
    m = compute_model(_synthetic())
    tbl = feature_table(m)
    lifts = [s.lift for s in tbl]
    assert lifts == sorted(lifts, reverse=True)
