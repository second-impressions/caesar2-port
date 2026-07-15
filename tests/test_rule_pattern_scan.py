"""Corpus-wide rule-pattern guard tests.

For rules whose hint is "REMOVE this source pattern", this test asserts the
pattern stays GONE across the corpus.  When the assertion fails, a candidate
function name is printed -- that function is the regression to investigate.

See :mod:`c2.commands.rule_pattern_scan` for the AST-level detectors.
"""
from __future__ import annotations

import pytest

from pycparser import c_ast

from c2.commands.rule_pattern_scan import (
    Candidate,
    find_candidates,
    find_rule_17b_candidates,    # back-compat helper
    scan_corpus,
)
from c2.commands.c_source import parse_c


# ── Detector unit tests ───────────────────────────────────────────────────

_PRE_FIX_MARKET_IMAGE = """
extern unsigned char city_map[];
extern int cm_sptr;
extern int evolve_tick4;
void change_sized(int a, int b, int c, int d);

void market_image(void)
{
    unsigned char shape = city_map[cm_sptr];
    unsigned char state = city_map[cm_sptr + 9];
    unsigned char halfA = state & 0x03;
    unsigned char halfB = state & 0x0c;
    unsigned char target = halfA;
    if (halfB == 0) target = 1;

    if (halfA != 0 && (evolve_tick4 & 1)) {
        unsigned char s = city_map[cm_sptr + 9] & 0xfc;
        city_map[cm_sptr + 9] = s;
        if (halfA == 2) {
            city_map[cm_sptr + 9] = s | 1;
        } else if (halfA == 3) {
            city_map[cm_sptr + 9] = s | 2;
        }
    }
}
"""

_POST_FIX_MARKET_IMAGE = """
extern unsigned char city_map[];
extern int cm_sptr;
extern int evolve_tick4;

void market_image(void)
{
    unsigned char state = city_map[cm_sptr + 9];
    unsigned char halfA = state & 0x03;
    unsigned char halfB = state & 0x0c;

    if (halfA != 0 && (evolve_tick4 & 1)) {
        city_map[cm_sptr + 9] &= 0xfc;
        if (halfA == 2) {
            city_map[cm_sptr + 9] |= 1;
        } else if (halfA == 3) {
            city_map[cm_sptr + 9] |= 2;
        }
    }
}
"""


def _funcdefs(text: str) -> dict:
    """Parse a snippet and return its top-level FuncDefs by name."""
    ast = parse_c(text, "snippet.c")
    return {n.decl.name: n for n in ast.ext
            if isinstance(n, c_ast.FuncDef) and n.decl.name}


def test_detector_finds_old_market_image_shape():
    """The OLD market_image source (before the b22dde4 fix) MUST be detected
    as a Rule 17b candidate.  Sanity check that the AST scanner works."""
    cands = find_rule_17b_candidates(_funcdefs(_PRE_FIX_MARKET_IMAGE))
    assert len(cands) == 1
    c = cands[0]
    assert c.rule_id == "17b"
    assert c.func == "market_image"
    assert c.detail["temp_name"] == "s"
    # The lhs key normalises whitespace, so we just check the prefix:
    assert "city_map" in c.detail["lhs_key"]
    assert c.detail["or_uses"] == 2


def test_detector_does_not_match_post_fix_market_image():
    """The CURRENT market_image source (after the temp `s` was removed)
    must NOT match -- the direct `X &= MASK;` / `X |= BIT;` form is what
    the rule recommends."""
    cands = find_rule_17b_candidates(_funcdefs(_POST_FIX_MARKET_IMAGE))
    assert cands == []


def test_detector_ignores_unrelated_temps():
    """A temp that isn`t paired with a `X = temp;` + `X = temp | ...;` must
    not be flagged."""
    snippet = """
    void noop(int *p) {
        unsigned char a = (*p) & 0x03;
        unsigned char b = (*p) & 0x0c;
        /* Neither a nor b is assigned back to *p. */
    }
    """
    assert find_rule_17b_candidates(_funcdefs(snippet)) == []


def test_detector_ignores_or_without_plain_assign():
    """The pattern needs both `X = temp;` AND `X = temp | ...;`.  An OR
    without a plain assign isn`t the Rule 17b shape."""
    snippet = """
    extern unsigned char city_map[];
    extern int cm_sptr;
    void f(void) {
        unsigned char s = city_map[cm_sptr] & 0xfc;
        city_map[cm_sptr] = s | 1;
    }
    """
    # No plain `city_map[cm_sptr] = s;` between the decl and the OR-assign.
    assert find_rule_17b_candidates(_funcdefs(snippet)) == []


# ── Corpus-wide guard ─────────────────────────────────────────────────────

def test_rule_17b_pattern_stays_gone_corpus_wide():
    """Rule 17b's hint is "remove the intermediate temp".  After the
    market_image fix (commit b22dde4) the corpus had 0 instances.  This
    test fails (with the offending function name + line) if a future edit
    re-introduces the pattern.

    Empirical baseline at the time this test was written:
      * 1444 functions indexed
      * 0 Rule 17b candidates
      * (market_image 113b -> 0b after removing the temp `s`)
    """
    cands_by_rule = scan_corpus(rule_ids=["17b"])
    cands = cands_by_rule.get("17b", [])
    if cands:
        lines = "\n".join(
            f"  - {c.file}:{c.line}  {c.func}::{c.detail.get('temp_name','?')}  "
            f"LHS={c.detail.get('lhs_key','?')}  "
            f"({c.detail.get('or_uses',0)} OR uses)"
            for c in cands
        )
        pytest.fail(
            f"{len(cands)} Rule 17b candidate(s) found.  Remove the "
            f"intermediate temp and use direct `X &= MASK; X |= BIT;`:\n"
            + lines
        )
