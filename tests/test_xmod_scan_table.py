"""Regression tests for the cross-module trailing scan-table classifier
(`_next_fn_scan_table_only`).

The false-positive it guards against (found 2026-07-11): when the RC link
order does NOT differ -- the next symbol is adjacent in RC too, i.e.
``rc_next_off == recomp_off + len(orig)`` -- the "re-anchored" trailing
slice is byte-for-byte the slice the naive comparison already diffed.
Re-running `_compare_bytes` on the short sub-buffer can then only flip the
verdict via a framing artifact: an in-function rel8 branch whose target
falls outside the sub-buffer is masked as "cross-function", hiding a
genuine code diff.  Observed on place_a_building_roof /
place2_a_building_roof (PS `jmp` back to a distant duplicated tail vs RC
`jmp` forward to the near copy -- live code, not a table).
"""

from c2.commands.decomp_verify import _next_fn_scan_table_only


def _mk_table_case():
    """Synthetic last-in-module function followed by a next-fn scan table.

    orig  : 8 code bytes ending in `ret`, then a 16-byte fixup-bearing
            table region (all diff vs the naively-sliced RC bytes).
    recomp: unrelated code where the naive slice sits, with the SAME
            16 table bytes placed just before the RC next-symbol site.
    """
    code = bytes([0x31, 0xC0, 0x40, 0x40, 0x40, 0x40, 0x40, 0xC3])  # ret @7
    table = bytes(range(0x10, 0x20))                                # 16b
    orig = code + table
    orig_off = 0x1000
    # fixups: one 4-byte entry per 4 table bytes (both sides)
    orig_fix = {orig_off + 8 + i for i in range(16)}

    # RC: naive slice holds garbage where the table would be; the real
    # table bytes live at rc_next_off - 16 somewhere else entirely.
    recomp_off = 0x2000
    naive = code + bytes([0xEE] * 16)
    rc_next_off = 0x3000
    recomp_code = bytearray(0x3100)
    recomp_code[recomp_off : recomp_off + len(naive)] = naive
    recomp_code[rc_next_off - 16 : rc_next_off] = table
    recomp_fix = {rc_next_off - 16 + i for i in range(16)}
    diffs = list(range(8, 24))  # every table byte diffs in the naive slice
    return (orig, bytes(recomp_code), diffs, orig_off, recomp_off,
            orig_fix, recomp_fix, rc_next_off)


def test_genuine_xmod_table_still_classified():
    (orig, recomp_code, diffs, orig_off, recomp_off,
     orig_fix, recomp_fix, rc_next_off) = _mk_table_case()
    assert _next_fn_scan_table_only(
        orig, recomp_code, diffs, orig_off, recomp_off,
        rc_next_off, orig_fix, recomp_fix)


def test_identity_reanchor_rejected():
    """Adjacent RC next symbol == identity re-anchor == no independent
    evidence: must NOT reclassify, even if the sub-buffer compare would
    pass (the place*_a_building_roof false-exact)."""
    (orig, recomp_code, diffs, orig_off, recomp_off,
     orig_fix, recomp_fix, _) = _mk_table_case()
    # Make the naive RC slice's trailing region byte-identical to PS's
    # (so a sub-buffer re-compare WOULD pass) and anchor the next symbol
    # adjacently -- the guard must still reject.
    rc = bytearray(recomp_code)
    rc[recomp_off + 8 : recomp_off + 24] = orig[8:24]
    rc_next_off = recomp_off + len(orig)
    recomp_fix = recomp_fix | {recomp_off + 8 + i for i in range(16)}
    assert not _next_fn_scan_table_only(
        orig, bytes(rc), diffs, orig_off, recomp_off,
        rc_next_off, orig_fix, recomp_fix)
