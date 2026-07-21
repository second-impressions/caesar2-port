import os
from pathlib import Path
import shutil
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "tests" / "asm_oracle" / "diamond_oracle.c"
FRAMEBUFFER_WIDTH = 641
FRAMEBUFFER_ROWS = 64
FRAMEBUFFER_SIZE = FRAMEBUFFER_WIDTH * FRAMEBUFFER_ROWS


def _case_names():
    cases = []
    hat_names = (
        "small-full", "small-left", "small-right",
        "medium-full", "medium-left", "medium-right",
        "large-full", "large-left", "large-right",
    )
    half_hat_names = (
        "small-left-half", "small-right-half",
        "medium-left-half", "medium-right-half",
        "large-left-half", "large-right-half",
    )
    roof_names = (
        "small-roof", "small-leftroof", "small-rightroof",
        "medium-roof", "medium-leftroof", "medium-rightroof",
        "large-roof", "large-leftroof", "large-rightroof",
    )
    half_roof_names = (
        "small-left-halfroof", "small-right-halfroof",
        "medium-left-halfroof", "medium-right-halfroof",
        "large-left-halfroof", "large-right-halfroof",
    )
    for name in hat_names:
        for depth in (0, 2, 5):
            for height in (1, 4, 8):
                cases.append(f"{name} d{depth} h{height}")
    for name in half_hat_names:
        for depth in (0, 2, 5):
            for height in (1, 4, 8, 16):
                for seam in (0, 2):
                    cases.append(f"{name} d{depth} h{height} s{seam}")
    for name in roof_names:
        for height in (1, 4, 8, 16):
            cases.append(f"{name} h{height}")
    for name in half_roof_names:
        for height in (1, 4, 8, 15, 16, 17, 20):
            for seam in (0, 2):
                cases.append(f"{name} h{height} s{seam}")
    return cases


def _run(command, cwd):
    result = subprocess.run(
        command, cwd=cwd, check=False, capture_output=True, text=True
    )
    assert result.returncode == 0, (
        f"command failed ({result.returncode}): {' '.join(map(os.fspath, command))}\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )


@pytest.mark.skipif(
    not all(shutil.which(tool) for tool in ("wasm", "wcl386", "cc")),
    reason="OpenWatcom and a native C compiler are required",
)
def test_portable_diamond_renderers_match_compiled_original_assembly(tmp_path):
    assembly_files = (
        ROOT / "src" / "dia_smal.asm",
        ROOT / "src" / "dia_medi.asm",
        ROOT / "src" / "dialarga.asm",
        ROOT / "src" / "dialargb.asm",
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
        ["cc", "-std=c11", "-DC2_FIX_MEDIUM_RIGHT_HAT_OFFSET=0",
         "-DC2_FIX_LARGE_RIGHT_HALFROOF_SEAM_PAIR=0",
         f"-I{ROOT / 'include'}", os.fspath(HARNESS),
         os.fspath(ROOT / "src" / "asm" / "c2_asm_diamond_image.c"),
         os.fspath(ROOT / "src" / "asm" / "c2_asm_stubs.c"),
         "-o", os.fspath(portable)],
        tmp_path,
    )

    original_output = subprocess.check_output([original])
    portable_output = subprocess.check_output([portable])
    cases = _case_names()
    expected_size = len(cases) * FRAMEBUFFER_SIZE

    assert len(original_output) == expected_size
    assert len(portable_output) == expected_size
    if portable_output != original_output:
        difference = next(
            index for index, (original_byte, portable_byte) in enumerate(
                zip(original_output, portable_output)
            )
            if original_byte != portable_byte
        )
        case_index, pixel_offset = divmod(difference, FRAMEBUFFER_SIZE)
        x = pixel_offset % FRAMEBUFFER_WIDTH
        y = pixel_offset // FRAMEBUFFER_WIDTH
        pytest.fail(
            f"framebuffer mismatch in {cases[case_index]} at "
            f"offset {pixel_offset} ({x}, {y}): "
            f"original={original_output[difference]:#04x}, "
            f"portable={portable_output[difference]:#04x}"
        )
