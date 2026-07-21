"""Architectural checks for the portable host boundary."""

from pathlib import Path


ROOT = Path(__file__).parents[1]
SRC = ROOT / "src"
PLATFORM_COMMON = SRC / "platform" / "common"
SDL_BACKEND = SRC / "platform" / "sdl3"
ASM = SRC / "asm"
HOST_HEADER = ROOT / "include" / "c2_host.h"


def _source_files(root: Path):
    return sorted((*root.rglob("*.c"), *root.rglob("*.h")))


def test_sdl_api_stays_below_the_host_boundary():
    offenders = []
    for path in _source_files(SRC):
        if path.is_relative_to(SDL_BACKEND):
            continue
        text = path.read_text()
        if "SDL_" in text or "<SDL3/" in text:
            offenders.append(str(path.relative_to(ROOT)))
    assert not offenders, "SDL escaped its backend:\n" + "\n".join(offenders)


def test_common_platform_layer_does_not_reach_into_sdl_backend():
    offenders = []
    for path in [HOST_HEADER, *_source_files(PLATFORM_COMMON)]:
        text = path.read_text()
        if "c2_sdl_" in text:
            offenders.append(str(path.relative_to(ROOT)))
    assert not offenders, "common platform layer depends on SDL backend:\n" + "\n".join(offenders)


def test_sdl_callback_does_not_mutate_legacy_game_state():
    main = (SDL_BACKEND / "c2_sdl_main.c").read_text()
    forbidden = ("c2inf", "internal_screen", "current_palette", "show_skill")
    offenders = [symbol for symbol in forbidden if symbol in main]
    assert not offenders, f"SDL callback reaches legacy state: {offenders}"


def test_smoke_driver_observes_without_reaching_into_legacy_state():
    smoke = (SDL_BACKEND / "c2_sdl_smoke.c").read_text()
    forbidden = ("c2inf", "province_is", "pm_x", "pm_y", "internal_screen")
    offenders = [symbol for symbol in forbidden if symbol in smoke]
    assert not offenders, f"smoke driver reaches legacy state: {offenders}"
    assert "c2_host_observation_snapshot" in smoke
    assert "c2_sdl_host_set_headless_mouse" in smoke


def test_optional_media_is_an_explicit_host_capability():
    header = HOST_HEADER.read_text()
    backend = (SDL_BACKEND / "c2_sdl_host.c").read_text()
    assert "C2_HOST_CAPABILITY_MUSIC" in header
    assert "C2_HOST_CAPABILITY_VIDEO" in header
    assert "int c2_host_has_capability" in backend


def test_asm_translations_remain_engine_side():
    offenders = []
    for path in _source_files(ASM):
        if "c2_host_" in path.read_text():
            offenders.append(str(path.relative_to(ROOT)))
    assert not offenders, "legacy engine support reaches the host:\n" + "\n".join(offenders)


def test_port_adapter_does_not_reimplement_engine_control_flow():
    app = (PLATFORM_COMMON / "c2_port_app.c").read_text()
    forbidden = (
        "skill1_buttons",
        "skill2_buttons",
        "show_skill",
        "initreg_game_loop",
        "c2inf",
        "startup_stage",
    )
    offenders = [symbol for symbol in forbidden if symbol in app]
    assert not offenders, f"port adapter owns recovered game flow: {offenders}"
    assert "c2_engine_main(0, NULL)" in app


def test_build_uses_recovered_driver_and_lib32():
    cmake = (ROOT / "CMakeLists.txt").read_text()
    assert "src/c2.c" in cmake
    assert "src/lib32.c" in cmake
    assert "src/platform/common/c2_port_app.c" in cmake
    assert "src/platform/sdl3/c2_sdl_main.c" in cmake
    assert "src/asm/c2_asm_memory.c" in cmake
    assert "src/port/" not in cmake
    assert "src/portable/" not in cmake


def test_source_layout_has_one_platform_hierarchy():
    assert not (SRC / "port").exists()
    assert not (SRC / "portable").exists()
    assert PLATFORM_COMMON.is_dir()
    assert SDL_BACKEND.is_dir()
