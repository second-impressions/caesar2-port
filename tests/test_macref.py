"""Mac PPC reference-binary pipeline (c2.macref).

Skipped wholesale when the gitignored binaries aren't extracted (see
MAC/ANALYSIS.md + c2/macref.py header for the recipes).
"""
import pytest

from c2 import macref

_have_fr = macref.BUILDS["fr"].exists()
_have_demo = macref.BUILDS["demo"].exists()

pytestmark = pytest.mark.skipif(
    not (_have_fr or _have_demo),
    reason="Mac binaries not extracted (MAC/extracted/ is gitignored)")


@pytest.fixture(scope="module")
def fr():
    if not _have_fr:
        pytest.skip("French retail PEF not extracted")
    return macref.get("fr")


@pytest.fixture(scope="module")
def demo():
    if not _have_demo:
        pytest.skip("Mac demo not extracted")
    return macref.get("demo")


def test_fr_index_headcount(fr):
    # 1,575 traceback-named functions in the French retail (full game).
    assert len(fr.index) == 1575
    assert fr.sha.startswith("23357e53")     # pinned in MAC/ANALYSIS.md


def test_demo_index_headcount(demo):
    assert len(demo.index) == 1309
    assert demo.sha.startswith("cdddbc60")


def test_ranges_are_disjoint_and_ordered(fr):
    prev_end = 0
    for s, e, _n in fr.index:
        assert prev_end <= s < e
        prev_end = e


def test_devolve_evolve_validation_case(demo):
    """The validation pair: structure facts that grounded the 2026-06-12
    source recovery must read straight off the demo disasm."""
    d = demo.disasm("devolve_a_building")
    ev = demo.disasm("evolve_a_building")
    # devolve guards count>0 and decrements; evolve guards count<3 and
    # increments -- the recovered-source delta, visible verbatim.
    assert "cmpwi    r31, 0" in d and "addi     r31, r31, -1" in d
    assert "cmpwi    r31, 3" in ev and "addi     r31, r31, 1" in ev
    # both arms converge on the shared change_sized call (the goto/
    # do_call idiom); call target resolved by name.
    assert "<change_sized>" in d and "<change_sized>" in ev
    # the 0x5DF threshold block exists in devolve ONLY (Mac evolve lacks
    # it -- independently confirmed our recovery).
    assert "0x5df" in d and "0x5df" not in ev
    # Mac evolve is a FULL body (no PC-style merge into devolve).
    s, e = demo.by_name["evolve_a_building"]
    assert e - s > 200


def test_kind_constants_visible(demo):
    d = demo.disasm("devolve_a_building")
    assert "cmplwi   r3, 0xdb" in d
    assert "cmplwi   r7, 0xdf" in d


def test_func_bytes_roundtrip(demo):
    s, e = demo.by_name["devolve_a_building"]
    b = demo.func_bytes("devolve_a_building")
    assert len(b) == e - s
    assert b[-4:] == b"\x4e\x80\x00\x20"        # ends in blr


def test_grep_and_missing(fr):
    assert "get_tb_value" in fr.grep("^get_tb")
    with pytest.raises(KeyError):
        fr.func_bytes("definitely_not_a_function")


def test_hard_list_coverage(fr):
    """The decomp hard-list coverage that motivated the pipeline:
    29/30 across builds; FR alone carries all but restore_picture_part."""
    hard = ["figure_go_to_target", "region_go_to_target", "sail_to_target",
            "try_this_regionmap_square", "get_wf_dirc", "get_start_points",
            "one_aquaduct_ramification", "reg_road_ramifications",
            "put_reg_x1_area", "get_random_start_points_from_dirc",
            "get_tb_value", "get_ferret2", "font_format_split",
            "find_enemy", "goto_flag_marker_mode", "control_buttons",
            "sa12_army_sail_home", "build_region_item",
            "get_nearest_reg_building", "pos_sound", "ferret_heading",
            "push_shell", "evolve_region",
            "check_goods_in_region_warehouses", "colour_cycle_delay1"]
    missing = [n for n in hard if n not in fr.by_name]
    assert missing == []


def test_toc_annotation_present(fr):
    # TOC-relative global loads get a stable per-global annotation:
    # resolved slots print &name, unresolved keep the raw toc[key] form.
    d = fr.disasm("pos_sound")
    assert "toc[" in d or "; &" in d


def test_toc_name_map(fr):
    """TOC->PC-global map: seeds are ground truth from byte-exact
    recoveries; the built map must honor them and pass the violation
    gate (skip if not yet built -- `c2 mac-fn --rebuild-toc-map`)."""
    tm = macref.load_toc_map("fr")
    if not tm:
        pytest.skip("toc map not built")
    for k, g in macref.TOC_SEEDS.items():
        assert tm.get(k) == g
    assert len(tm) >= 200
    # annotation shows up in disasm
    assert "&samples_running" in fr.disasm("pos_sound")
