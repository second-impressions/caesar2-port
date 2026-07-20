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


def _portable_slots():
    return set(re.findall(
        r"(?m)^C2_ROUTINE_[A-Z0-9_]+\(([^,\)]+)",
        DEFINITIONS.read_text(),
    ))


def test_every_callable_assembly_export_has_one_portable_slot():
    assembly = _assembly_exports()
    portable = _portable_slots()
    assert len(assembly) == 87
    assert len(portable) == 87
    assert portable == assembly
