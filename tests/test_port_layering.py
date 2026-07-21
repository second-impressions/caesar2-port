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


def test_recovered_sources_do_not_call_the_host_boundary_directly():
    offenders = []
    for path in sorted((*SRC.glob("*.c"), *SRC.glob("*.h"))):
        if "c2_host_" in path.read_text():
            offenders.append(str(path.relative_to(ROOT)))
    assert not offenders, "recovered source calls the host directly:\n" + "\n".join(offenders)


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


def test_observation_sources_are_debug_only():
    cmake = (ROOT / "CMakeLists.txt").read_text()
    assert "$<$<CONFIG:Debug>:C2_DEBUG_BUILD=1>" in cmake
    assert "$<$<CONFIG:Debug>:src/platform/common/c2_port_observation.c>" in cmake
    assert "$<$<CONFIG:Debug>:src/platform/sdl3/c2_sdl_smoke.c>" in cmake


def test_posix_crash_handler_is_debug_only_and_sanitizer_safe():
    cmake = (ROOT / "CMakeLists.txt").read_text()
    presets = (ROOT / "CMakePresets.json").read_text()
    assert "if(UNIX AND NOT EMSCRIPTEN AND C2_ENABLE_POSIX_DEBUG_CRASH_HANDLER)" in cmake
    assert "$<$<CONFIG:Debug>:src/platform/posix/c2_posix_debug.c>" in cmake
    assert presets.count('"C2_ENABLE_POSIX_DEBUG_CRASH_HANDLER": "OFF"') == 2


def test_wasm_reuses_the_sdl_host_and_recovered_engine_worker():
    cmake = (ROOT / "CMakeLists.txt").read_text()
    main = (SDL_BACKEND / "c2_sdl_main.c").read_text()
    assert "SDL_EMSCRIPTEN_PERSISTENT_PATH" in cmake
    assert "-sPTHREAD_POOL_SIZE=2" in cmake
    assert "-sINITIAL_MEMORY=67108864" in cmake
    assert "ALLOW_MEMORY_GROWTH" not in cmake
    assert "c2_wasm_implicit_void.h" in cmake
    assert "#if !C2_FEAT_BROWSER_RUNTIME" in main
    assert "src/platform/wasm" not in cmake


def test_language_builds_split_artifacts_without_branching_the_engine():
    cmake = (ROOT / "CMakeLists.txt").read_text()
    assert 'set(C2_LANGUAGE "en" CACHE STRING' in cmake
    assert 'OUTPUT_NAME "caesar2-${C2_LANGUAGE}"' in cmake
    assert 'c2_require_language_asset("c2.eng")' in cmake
    assert 'c2_require_language_asset("help.eng")' in cmake

    offenders = []
    for path in _source_files(SRC):
        if "C2_LANGUAGE" in path.read_text():
            offenders.append(str(path.relative_to(ROOT)))
    assert not offenders, "language build tag escaped into the engine:\n" + "\n".join(offenders)


def test_wasm_shell_is_unframed_and_reports_downloads_in_megabytes():
    cmake = (ROOT / "CMakeLists.txt").read_text()
    shell = (ROOT / "web" / "caesar2.html").read_text()
    assert 'LINK_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/web/caesar2.html"' in cmake
    assert "radial-gradient" not in shell
    assert "box-shadow" not in shell
    assert "width: 100vw" in shell
    assert "height: 100vh" in shell
    assert "resizeCanvasToIntegerScale" in shell
    assert "devicePixelRatio || 1" in shell
    assert "Math.floor(fit)" in shell
    assert "--c2-canvas-width" in shell
    assert "Math.ceil(logicalWidth * scale / density)" in shell
    assert "Number(match[1]) / 1_000_000" in shell
    assert "MB)…" in shell


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


def test_portable_helpers_do_not_pose_as_recovered_translation_units():
    misplaced = [
        SRC / "c2_bugfixes.c",
        SRC / "c2_save_compat.c",
        SRC / "c2_text_compat.c",
    ]
    assert not [path for path in misplaced if path.exists()]
    expected = [
        PLATFORM_COMMON / "c2_port_bugfixes.c",
        PLATFORM_COMMON / "c2_port_save_compat.c",
        PLATFORM_COMMON / "c2_port_text_compat.c",
    ]
    assert all(path.is_file() for path in expected)


def test_portable_asm_manifest_does_not_reach_the_watcom_source_path():
    data_header = (ROOT / "include" / "c2_data.h").read_text()
    guarded_include = (
        '#if PLATFORM_PORTABLE\n#include "c2_asm_routines.h"\n#endif'
    )
    assert guarded_include in data_header


def test_mouse_lock_is_cli_policy_above_a_backend_neutral_cursor():
    main = (SDL_BACKEND / "c2_sdl_main.c").read_text()
    host = (SDL_BACKEND / "c2_sdl_host.c").read_text()
    common_mouse = (PLATFORM_COMMON / "c2_port_mouse.c").read_text()
    assert '"--mouse-lock"' in main
    assert '"--no-mouse-lock"' in main
    assert "SDL_SetWindowMouseGrab" in host
    assert "SDL_SetWindowRelativeMouseMode" in host
    assert "SDL_" not in common_mouse


def test_sdl_uses_exact_nearest_neighbor_scaling():
    host = (SDL_BACKEND / "c2_sdl_host.c").read_text()
    assert "SDL_SetTextureScaleMode(c2_texture, SDL_SCALEMODE_NEAREST)" in host
    assert "window_flags |= SDL_WINDOW_HIGH_PIXEL_DENSITY" in host
    assert "presentation = SDL_LOGICAL_PRESENTATION_INTEGER_SCALE" in host
