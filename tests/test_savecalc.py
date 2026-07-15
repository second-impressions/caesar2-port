"""Parsing + reconstruction tests for the `cv` (CalcSavings breakdown) record.

The cv stream captures CalcSavings' per-block raw unit sums at the
_UpdateCost join (OW c/regsave.c + h/savcode.h), BEFORE the Weight
multiply.  Invariant: final savings == sum((save-cost) * W^min(depth,4)),
W = loop_base (10 for the PS flags), clamped to 0 / MAX_SAVE-1.

The fixture numbers are the real probe transcript (simple.c
`int add(int a,int b){int i,s=0;for(i=0;i<a;i++)s+=b;return s;}`,
2026-06-11 image): four conflicts whose cv breakdowns reconstruct their
`sl` savings 12 / 12 / 23 / 31 exactly.
"""
from c2.regalloc.trace import parse, savecalc_savings


def _trace():
    return (
        "~WV1 lwt 128\n"                       # loop_base = 20*128//256 = 10
        "~WV1 fb\n"
        "~WV1 fn\n"
        "~WV1 cv 99188 9a1c4 2 0 0\n"
        "~WV1 cv 99188 99ccc 0 0 0\n"
        "~WV1 cv 99188 99724 1 0 1\n"
        "~WV1 cv 99188 99aac 0 0 1\n"
        "~WV1 cv 991e4 9a1c4 2 0 0\n"
        "~WV1 cv 991e4 99724 0 0 1\n"
        "~WV1 cv 991e4 99aac 1 0 1\n"
        "~WV1 cv 99240 99ccc 1 0 0\n"
        "~WV1 cv 99240 99aac 2 0 1\n"
        "~WV1 cv 99240 9966c 2 0 0\n"
        "~WV1 cv 9929c 99ccc 1 0 0\n"
        "~WV1 cv 9929c 99724 1 0 1\n"
        "~WV1 cv 9929c 99aac 2 0 1\n"
        "~WV1 sl 99188 12\n"
        "~WV1 sl 991e4 12\n"
        "~WV1 sl 99240 23\n"
        "~WV1 sl 9929c 31\n"
        "~WV1 fc 99 0 0\n"
    )


def test_cv_parses_into_savecalc():
    td = parse(_trace())
    r = td["routines"][0]
    sc = r["savecalc"]
    assert set(sc) == {"99188", "991e4", "99240", "9929c"}
    assert sc["99188"][0] == {"blk": "9a1c4", "save": 2, "cost": 0, "depth": 0}
    assert len(sc["99188"]) == 4


def test_cv_reconstructs_sl_savings():
    td = parse(_trace())
    r = td["routines"][0]
    base = td["loop_base"]
    assert base == 10
    want = {e["node"]: e["savings"] for e in r["presort"]}
    for conf, entries in r["savecalc"].items():
        assert savecalc_savings(entries, base) == want[conf], conf


def test_cv_clamps():
    # save <= cost -> 0 (the `if( save <= cost )` early-zero)
    assert savecalc_savings(
        [{"blk": "0", "save": 1, "cost": 5, "depth": 0}], 10) == 0
    # depth caps at 4 (loop_weight has MAX_LOOP+1 entries)
    deep = savecalc_savings([{"blk": "0", "save": 1, "cost": 0, "depth": 9}], 10)
    assert deep == 10 ** 4
    # MAX_SAVE-1 cap (conflict.h MAX_SAVE 0xFFFFFFFF)
    big = savecalc_savings(
        [{"blk": "0", "save": 2 ** 40, "cost": 0, "depth": 0}], 10)
    assert big == 0xfffffffe
