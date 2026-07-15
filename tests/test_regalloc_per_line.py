"""Tests for the prominent per-source-line regalloc view (Path E).

The trace data already pinpoints which named variable / anonymous temp lives
at every source line.  ``regalloc_hints.render_per_line`` surfaces it as a
mirror of the source structure, so the user can map each diverging asm byte
back to its IR origin.
"""
from __future__ import annotations

from c2.commands.regalloc_hints import (
    RegallocHint, render_per_line, render_lines,
)


def _mk_hint(by_line: dict[int, list], **kw) -> RegallocHint:
    """Build a minimal RegallocHint for render testing."""
    return RegallocHint(
        func=kw.get("func", "test"),
        cost_model=kw.get("cost_model", {"load_cost": 2, "store_cost": 2,
                                          "use_save": 1, "def_save": 1,
                                          "push_cost": 1, "pop_cost": 1}),
        loop_base=kw.get("loop_base", 10),
        allocs=kw.get("allocs", []),
        spilled=kw.get("spilled", 0),
        by_line=by_line,
    )


def test_render_per_line_empty():
    assert render_per_line(_mk_hint({})) == []


def test_render_per_line_shows_each_line_with_named_var():
    h = _mk_hint({
        1696: [{"conf": "1414ec", "name": "bb910", "savings": 7,
                "regclass_name": "dword", "reg_name": "ECX",
                "nameclass_name": "N_TEMP", "var": "cm_ptr"}],
        1707: [{"conf": "14137c", "name": "bd3f0", "savings": 9,
                "regclass_name": "dword", "reg_name": "EBX",
                "nameclass_name": "N_TEMP", "var": "code"}],
    })
    out = render_per_line(h)
    assert out[0] == "regalloc by source line:"
    assert "L1696" in out[1]
    assert "cm_ptr->ECX" in out[1]
    assert "L1707" in out[2]
    assert "code->EBX" in out[2]


def test_render_per_line_anonymous_temp_falls_back_to_conf_tail():
    # No `var` -> render uses a `t.<last-4-hex>` placeholder.
    h = _mk_hint({
        1707: [{"conf": "abcdef12", "name": "xx", "savings": 2,
                "regclass_name": "dword", "reg_name": "ESI",
                "nameclass_name": "N_TEMP", "var": None}],
    })
    out = render_per_line(h)
    assert "t.ef12->ESI" in out[1]


def test_render_per_line_sorts_within_line_by_savings_desc():
    # Multiple conflicts at the same line render highest-savings first
    # (the more interesting deciders for the asm).
    h = _mk_hint({
        1707: [
            {"conf": "aaaa", "name": "n1", "savings": 2,
             "regclass_name": "dword", "reg_name": "ESI",
             "nameclass_name": "N_TEMP", "var": None},
            {"conf": "bbbb", "name": "n2", "savings": 9,
             "regclass_name": "dword", "reg_name": "EBX",
             "nameclass_name": "N_TEMP", "var": "code"},
        ],
    })
    out = render_per_line(h)
    # First entry within the line should be the savings=9 one.
    parts = out[1].split(":", 1)[1]
    assert parts.lstrip().startswith("s9:code->EBX")


def test_render_per_line_separates_synthetic_l0_conflicts():
    # L0 (prolog / synthetic) conflicts are noise for source-side levers.
    # They render last on a labeled line so users can ignore them quickly.
    h = _mk_hint({
        0: [{"conf": "11", "name": "n1", "savings": 8,
             "regclass_name": "dword", "reg_name": "EBX",
             "nameclass_name": "N_TEMP", "var": None}],
        1707: [{"conf": "22", "name": "n2", "savings": 9,
                "regclass_name": "dword", "reg_name": "EBX",
                "nameclass_name": "N_TEMP", "var": "code"}],
    })
    out = render_per_line(h)
    # L1707 first, L0 last (clearly labeled).
    assert "L1707" in out[1]
    assert "synthetic/prolog" in out[2]


def test_render_lines_detailed_includes_per_line_view():
    h = _mk_hint(
        by_line={
            1707: [{"conf": "aaaa", "name": "n1", "savings": 9,
                    "regclass_name": "dword", "reg_name": "EBX",
                    "nameclass_name": "N_TEMP", "var": "code"}],
        },
        allocs=[{"savings": 9, "regclass_name": "dword",
                 "reg_name": "EBX", "nameclass_name": "N_TEMP"}],
    )
    compact = render_lines(h, detailed=False)
    detailed = render_lines(h, detailed=True)
    # Compact has the savings/reg summary line(s) only.
    assert any("regalloc by source line:" in l for l in detailed)
    assert not any("regalloc by source line:" in l for l in compact)


def test_per_line_view_pinpoints_rule5c_divergence():
    # The actual get_region_2x2_start case: L1707 has the divisor temp
    # (s=2->ESI), L1708 does NOT have one.  This is the visible Rule 5c
    # miss -- the trace makes it OBVIOUS in the per-line view.
    h = _mk_hint({
        1707: [
            {"conf": "14137c", "name": "bd3f0", "savings": 9,
             "regclass_name": "dword", "reg_name": "EBX",
             "nameclass_name": "N_TEMP", "var": "code"},
            {"conf": "f995c", "name": "bbb74", "savings": 2,
             "regclass_name": "dword", "reg_name": "ESI",
             "nameclass_name": "N_TEMP", "var": None},  # the divisor temp
        ],
        1708: [
            {"conf": "141434", "name": "dc550", "savings": 4,
             "regclass_name": "dword", "reg_name": "ESI",
             "nameclass_name": "N_TEMP", "var": "col"},
        ],
    })
    out = render_per_line(h)
    l1707 = next(l for l in out if "L1707" in l)
    l1708 = next(l for l in out if "L1708" in l)
    # L1707 has BOTH `code` and an anonymous temp (the divisor for % 2).
    assert "code->EBX" in l1707
    assert "t.995c->ESI" in l1707
    # L1708 has ONLY `col`, no second anonymous temp -- the / 2 didn't
    # create a divisor temp.  This is the Rule 5c miss made obvious.
    assert "col->ESI" in l1708
    # The presence of TWO confs at L1707 vs ONE at L1708 -- when both
    # operations are divisions of the same constant -- is the trace
    # signature of a Rule 5c miss.
    l1707_confs = l1707.count("->")
    l1708_confs = l1708.count("->")
    assert l1707_confs == 2 and l1708_confs == 1
