import os
from pathlib import Path
import shutil
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "tests" / "asm_oracle" / "diamond_oracle.c"


def _run(command, cwd):
    subprocess.run(command, cwd=cwd, check=True, capture_output=True, text=True)


@pytest.mark.skipif(
    not all(shutil.which(tool) for tool in ("wasm", "wcl386", "cc")),
    reason="OpenWatcom and a native C compiler are required",
)
def test_portable_hats_match_compiled_original_assembly(tmp_path):
    assembly_files = (
        ROOT / "src" / "dia_smal.asm",
        ROOT / "src" / "dia_medi.asm",
        ROOT / "src" / "dialarga.asm",
    )
    objects = []
    for assembly in assembly_files:
        object_path = tmp_path / f"{assembly.stem}.o"
        _run(
            ["wasm", "-zq", "-bt=linux", "-4r", f"-fo={object_path}",
             os.fspath(assembly)],
            tmp_path,
        )
        objects.append(object_path)

    original = tmp_path / "diamond-original"
    _run(
        ["wcl386", "-q", "-bcl=linux", "-4r", os.fspath(HARNESS),
         *(os.fspath(path) for path in objects), f"-fe={original}"],
        tmp_path,
    )

    portable = tmp_path / "diamond-portable"
    _run(
        ["cc", "-std=c11", f"-I{ROOT / 'include'}", os.fspath(HARNESS),
         os.fspath(ROOT / "src" / "portable" / "asm" /
                   "c2_asm_diamond_image.c"),
         os.fspath(ROOT / "src" / "portable" / "asm" / "c2_asm_stubs.c"),
         "-o", os.fspath(portable)],
        tmp_path,
    )

    original_output = subprocess.check_output([original], text=True)
    portable_output = subprocess.check_output([portable], text=True)
    assert portable_output == original_output
