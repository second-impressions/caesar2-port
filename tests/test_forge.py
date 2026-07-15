"""Smoke tests for the forge harness (tree-sitter preset architecture).

In-process only -- no podman, no compile, no PS.EXE load.  Exercises
TextEdit composition, the preset registry + candidate generation, the
metric-gaming width guard, and a DSL smoke path.  The expensive
integration path (warm container -> compile -> score) is exercised by
``c2 forge solve``.

Presets are pure ``(forge, **opts) -> int`` functions that only touch
``forge.text``, ``forge.function`` and ``forge.candidate(...)`` -- so a
tiny stub stands in for a real Forge for the synthetic-source tests.
"""

from __future__ import annotations

from pathlib import Path

import pytest


def _maybe_skip(path: str) -> Path:
    p = Path(path)
    if not p.exists():
        pytest.skip(f"{path} not present in this checkout")
    return p


class _Stub:
    """Minimal Forge stand-in for preset tests: the presets read
    ``.text`` / ``.function`` and append via ``.candidate``."""

    def __init__(self, text: str, function: str = "f"):
        self.text = text
        self.function = function
        self.cands: list = []

    def candidate(self, name, *edits):
        self.cands.append((name, edits))
        return self


def _apply(src: str, edits) -> str:
    from c2.forge.edits import EditPlan
    proxy = type("_C", (), {"edits": tuple(edits)})()
    return EditPlan(candidates=(proxy,)).apply(src)


# edits

def test_textedit_overlap_detection():
    from c2.forge import TextEdit
    a = TextEdit(start=10, end=20, replacement="x")
    b = TextEdit(start=15, end=25, replacement="y")
    c = TextEdit(start=30, end=40, replacement="z")
    assert a.overlaps(b)
    assert b.overlaps(a)
    assert not a.overlaps(c)


def test_edit_plan_applies_in_reverse_order():
    from c2.forge import EditPlan, Candidate, TextEdit
    base = "0123456789ABCDEFGHIJ"
    c1 = Candidate(name="early", edits=(TextEdit(4, 6, "??"),))
    c2 = Candidate(name="late", edits=(TextEdit(12, 15, "###"),))
    out = EditPlan(candidates=(c1, c2)).apply(base)
    assert out == base[:4] + "??" + base[6:12] + "###" + base[15:], out


def test_baseline_plan_is_identity():
    from c2.forge import EditPlan
    assert EditPlan(candidates=()).apply("hello\nworld") == "hello\nworld"


# registry

def test_preset_registry_has_documented_keys():
    from c2.forge import PRESETS
    for required in ("tie_group", "decl_swap_all", "stmt_swap_adjacent",
                     "commute_all", "relorder_all", "type_sweep",
                     "param_type_sweep"):
        assert required in PRESETS, f"preset {required!r} missing"


def test_skill_path_resolves():
    from c2.forge import skill_path
    p = skill_path()
    assert p.name == "SKILL.md"
    assert "forge" in str(p)


# synthetic-source preset behaviour (stub forge)

def test_preset_type_sweep_restrict_only_touches_named_local():
    from c2.forge.presets import preset_type_sweep
    s = _Stub("void f(void){\n    int seed; short q;\n    seed = 0; q = 0;\n}\n")
    n = preset_type_sweep(s, restrict=["seed"])
    assert n >= 1
    assert all("seed" in name for name, _ in s.cands), s.cands
    # never re-spells its own type
    assert not any("=int" in name.replace(" ", "") for name, _ in s.cands)


def test_preset_shift1_toggles_both_directions_parenthesised():
    from c2.forge.presets import preset_shift1
    src = "void f(void){\n    int a, x;\n    a = x << 1;\n    a = x + x;\n}\n"
    s = _Stub(src)
    assert preset_shift1(s) == 2
    for _name, edits in s.cands:
        for e in edits:
            assert e.replacement.startswith("(") and e.replacement.endswith(")")
        assert _apply(src, edits)          # applies cleanly


def test_preset_bytemask_casts_and_0xff():
    from c2.forge.presets import preset_bytemask
    src = "void f(void){\n    int a, b, c;\n    b = a & 0xff; c = (a + 1) & 0xff;\n}\n"
    s = _Stub(src)
    assert preset_bytemask(s) >= 1
    assert any("(unsigned char)" in _apply(src, e) for _n, e in s.cands)


def test_preset_relorder_flips_the_compare():
    from c2.forge.presets import preset_relorder_all
    src = "void f(void){\n    int a, b;\n    if (a + 1 < b) a = 0;\n}\n"
    s = _Stub(src)
    assert preset_relorder_all(s) >= 1
    rep = s.cands[0][1][0].replacement
    assert ">" in rep and "a" in rep and "b" in rep, rep   # < flipped to >


def test_preset_commute_emits_and_applies():
    from c2.forge.presets import preset_commute_all
    src = "void f(void){\n    int a, b, c;\n    c = a + b;\n}\n"
    s = _Stub(src)
    assert preset_commute_all(s) >= 1
    for _n, edits in s.cands:
        assert _apply(src, edits)


def test_compound_expand_is_statement_scoped_on_packed_lines():
    """`sy -= h;` at the END of a packed line expands to `sy = sy - h;`
    WITHOUT swallowing the preceding statements (place2_sprite class)."""
    from c2.forge.presets import preset_compound_assign_expand
    src = ("int sx, sy, dx, dy, h;\n"
           "void f(void){\n"
           "    sx += dx; sy += dy; sy -= h;\n"
           "}\n")
    s = _Stub(src)
    preset_compound_assign_expand(s)
    assert any("-=" in name for name, _ in s.cands), s.cands
    for name, edits in s.cands:
        for e in edits:
            # never swallow a neighbouring statement's `;`
            assert src[e.start:e.end].count(";") <= 1, (name, src[e.start:e.end])
            assert " = " in e.replacement, e.replacement


def test_compound_contract_is_statement_scoped_on_packed_lines():
    from c2.forge.presets import preset_compound_assign_contract
    src = ("int sy, h, sx, dx;\n"
           "void f(void){\n"
           "    sx += dx; sy = sy & h;\n"
           "}\n")
    s = _Stub(src)
    preset_compound_assign_contract(s)
    assert s.cands, "contract site on the packed line must be found"
    for name, edits in s.cands:
        for e in edits:
            assert src[e.start:e.end].count(";") <= 1, (name, src[e.start:e.end])
            assert e.replacement.strip().rstrip(";") == "sy &= h", e.replacement


def test_incdec_full_form_no_duplication_on_packed_lines():
    from c2.forge.presets import preset_incdec_toggle
    src = "int x, y;\nvoid f(void){\n    x++; y++;\n}\n"
    s = _Stub(src)
    preset_incdec_toggle(s)
    assert s.cands, "packed ++ statements must still yield candidates"
    for name, edits in s.cands:
        for e in edits:
            # never swallow a neighbouring statement (packed-line bug)
            assert src[e.start:e.end].count(";") <= 1, (name, src[e.start:e.end])


# param_type_sweep (the signature-parameter type flipper)

def test_preset_param_type_sweep_emits_synced_proto_and_def_edits():
    """param_type_sweep re-types signature params and keeps any same-TU
    prototype in sync (mirror of the city_test_for_road win a64b9900)."""
    _maybe_skip("decomp/src/int_c2.c")
    from c2.forge import Forge
    from c2.forge.presets import preset_param_type_sweep
    f = Forge("city_test_for_road", file="int_c2.c")
    try:
        n = preset_param_type_sweep(f)
    finally:
        f.close()
    cands = [c for c in f.candidates() if c.name.startswith("paramtype(")]
    assert n == len(cands) and cands, "no param-type candidates emitted"
    # int_c2.c carries a top-of-file prototype, so each candidate must
    # carry BOTH the definition edit and the prototype edit (else the
    # variant fails to compile on a prototype/definition type mismatch).
    for c in cands:
        assert len(c.edits) >= 2, (c.name, len(c.edits))


def test_param_type_sweep_synthetic_no_prototype_single_edit():
    """Without a same-TU prototype, one edit per candidate (definition
    only)."""
    from c2.forge.presets import preset_param_type_sweep
    s = _Stub("int f(int world_dir)\n{\n    return world_dir;\n}\n")
    n = preset_param_type_sweep(s)
    assert n >= 1
    assert all(name.startswith("paramtype(") for name, _ in s.cands)
    assert all(len(edits) == 1 for _n, edits in s.cands)


# real-Forge preset smoke

def test_preset_decl_swap_all_emits_pair_candidates():
    _maybe_skip("decomp/src/bbarian.c")
    from c2.forge import Forge
    f = Forge("get_random_start_points_from_dirc", file="bbarian.c")
    try:
        f.preset("decl_swap_all")
        added = len(f.candidates())
    finally:
        f.close()
    assert added >= 1


def test_preset_all_battery_includes_param_type_sweep():
    _maybe_skip("decomp/src/int_c2.c")
    from c2.forge import Forge
    f = Forge("city_test_for_road", file="int_c2.c")
    try:
        f.preset("all")
        names = [c.name for c in f.candidates()]
    finally:
        f.close()
    assert any(nm.startswith("paramtype(") for nm in names), \
        "param_type_sweep must be in the default battery"


def test_try_type_emits_one_candidate_per_alternative():
    _maybe_skip("decomp/src/bbarian.c")
    from c2.forge import Forge
    f = Forge("get_random_start_points_from_dirc", file="bbarian.c")
    try:
        # pick a body-declared local (params raise KeyError in try_type)
        picked = None
        for name in sorted(f.fs.local_names()):
            try:
                f.try_type(name, ["short", "int", "unsigned int"])
                picked = name
                break
            except KeyError:
                continue
        if picked is None:
            pytest.skip("no body-declared local in fixture")
        cands = [c for c in f.candidates() if f"type({picked}=" in c.name]
    finally:
        f.close()
    assert len(cands) == 3, [c.name for c in cands]


# DecisionMatrix / winners

def test_winners_type_width_guard():
    """A plan with a type(...) or paramtype(...) candidate that
    REGRESSES the width layer must not win even when ir drops (the
    short-gaming class, 2026-07-03); the same width regression from a
    NON-type plan stays a winner (legitimate alignment reveal)."""
    from c2.forge.edits import Candidate, EditPlan, TextEdit
    from c2.forge.experiment import PlanResult, Summary
    from c2.forge.judge import Score

    def _score(ir, width, bytes_):
        return Score(ok=True, bytes=bytes_, size=100, size_delta=0,
                     shape={"ir": ir, "islands": ir, "width": width,
                            "spill": 0, "seat": 0})

    def _plan(name):
        return EditPlan(candidates=(
            Candidate(name=name,
                      edits=(TextEdit(start=0, end=1, replacement="y"),)),
        ))

    baseline = _score(ir=10, width=0, bytes_=450)
    gamed = PlanResult(plan=_plan("type(i=short)"),
                       score=_score(ir=9, width=4, bytes_=510))
    gamed_param = PlanResult(plan=_plan("paramtype(i=short)"),
                             score=_score(ir=9, width=4, bytes_=510))
    reveal = PlanResult(plan=_plan("swap_stmts(L1,L2)"),
                        score=_score(ir=9, width=4, bytes_=510))
    fix = PlanResult(plan=_plan("type(i=char)"),
                     score=_score(ir=9, width=0, bytes_=440))
    s = Summary(function="f", file="f.c", baseline=baseline,
                plans=[gamed, gamed_param, reveal, fix])
    names = [p.plan.name for p in s.winners()]
    assert "type(i=short)" not in names, "gamed type plan must be filtered"
    assert "paramtype(i=short)" not in names, "gamed param-type plan filtered"
    assert "swap_stmts(L1,L2)" in names, "non-type reveal must survive"
    assert "type(i=char)" in names, "width-fixing type plan must survive"
