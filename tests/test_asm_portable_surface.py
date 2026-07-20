"""Keep the portable C surface identical to the recovered assembly ABI."""

import re
from pathlib import Path


ROOT = Path(__file__).parents[1]
DEFINITIONS = ROOT / "include" / "c2_asm_routines.def"


def _assembly_exports():
    exports = set()
    for path in sorted((ROOT / "src").glob("*.asm")):
        for match in re.finditer(r"(?mi)^PUBLIC\s+([^\r\n]+)", path.read_text()):
            for decorated in match.group(1).replace(",", " ").split():
                name = decorated.removesuffix("_").removeprefix("_")
                if name.startswith("lib_ret") or name.startswith("lib_para"):
                    continue
                exports.add(name)
    return exports


def _portable_slots(state=None):
    pattern = r"(?m)^C2_ASM_(STUB|IMPLEMENTED)\([^,]+,\s*([^,\)]+)"
    entries = re.findall(pattern, DEFINITIONS.read_text())
    if state is not None:
        entries = [entry for entry in entries if entry[0] == state]
    return {entry[1] for entry in entries}


def test_every_callable_assembly_export_has_one_portable_slot():
    assembly = _assembly_exports()
    portable = _portable_slots()
    assert len(assembly) == 87
    assert len(portable) == 87
    assert portable == assembly


def test_every_slot_has_exactly_one_implementation_state():
    stubs = _portable_slots("STUB")
    implemented = _portable_slots("IMPLEMENTED")
    assert not stubs & implemented
    assert len(stubs) == 13
    assert implemented == {
        "copy", "compress", "depress",
        "show_internal_point", "show_internal_2point", "show_internal_2x8",
        "show_internal_4point", "xor_internal_2point",
        "place_2x2_block", "place_4x4_block", "place_6x6_block",
        "place_8x8_block", "show_fast_rect",
        "write_i_font", "write_i_left_font", "write_i_right_font",
        "place_i_sprite", "write_i_sprite", "write_i_left_sprite",
        "write_i_right_sprite", "place_16x16_block", "place_24x24_block",
        "place_32x32_block", "pick_up_mouse_background",
        "put_down_mouse_background",
        "write_i_large_diamond_ptr", "write_i_large_diamond_ptr_left",
        "write_i_large_diamond_ptr_right", "write_i_medium_diamond_ptr",
        "write_i_medium_diamond_ptr_left", "write_i_medium_diamond_ptr_right",
        "write_i_small_diamond_ptr", "write_i_small_diamond_ptr_left",
        "write_i_small_diamond_ptr_right",
        "place_i_small_diamond", "place_i_small_diamond_lefthalf",
        "place_i_small_diamond_righthalf",
        "place_i_medium_diamond", "place_i_medium_diamond_lefthalf",
        "place_i_medium_diamond_righthalf", "place_i_large_diamond",
        "place_i_large_diamond_lefthalf", "place_i_large_diamond_righthalf",
        "call_address",
        "write_small_diamond_hat", "write_small_diamond_lefthat",
        "write_small_diamond_righthat", "write_medium_diamond_hat",
        "write_medium_diamond_lefthat", "write_medium_diamond_righthat",
        "write_large_diamond_hat", "write_large_diamond_lefthat",
        "write_large_diamond_righthat",
        "write_small_diamond_roof", "write_small_diamond_leftroof",
        "write_small_diamond_rightroof", "write_medium_diamond_roof",
        "write_medium_diamond_leftroof", "write_medium_diamond_rightroof",
        "write_large_diamond_roof", "write_large_diamond_leftroof",
        "write_large_diamond_rightroof",
        "write_small_diamond_lefthalfhat",
        "write_small_diamond_righthalfhat",
        "write_medium_diamond_lefthalfhat",
        "write_medium_diamond_righthalfhat",
        "write_large_diamond_lefthalfhat",
        "write_large_diamond_righthalfhat",
        "write_small_diamond_lefthalfroof",
        "write_small_diamond_righthalfroof",
        "write_medium_diamond_lefthalfroof",
        "write_medium_diamond_righthalfroof",
        "write_large_diamond_lefthalfroof",
        "write_large_diamond_righthalfroof",
    }


def test_engine_declarations_expose_the_portable_surface():
    shared_declarations = (ROOT / "include" / "c2_data.h").read_text()
    assert '#include "c2_asm_routines.h"' in shared_declarations
