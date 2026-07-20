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
    assert len(stubs) == 74
    assert implemented == {
        "copy", "compress", "depress",
        "show_internal_point", "show_internal_2point", "show_internal_2x8",
        "show_internal_4point", "xor_internal_2point",
        "place_2x2_block", "place_4x4_block", "place_6x6_block",
        "place_8x8_block", "show_fast_rect",
    }


def test_engine_declarations_expose_the_portable_surface():
    shared_declarations = (ROOT / "include" / "c2_data.h").read_text()
    assert '#include "c2_asm_routines.h"' in shared_declarations
