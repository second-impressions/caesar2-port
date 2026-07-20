"""Architectural checks for the portable host boundary."""

from pathlib import Path


ROOT = Path(__file__).parents[1]
SRC = ROOT / "src"
PORT = SRC / "port"
SDL_BACKEND = SRC / "platform" / "sdl3"
PORTABLE_LIB32 = SRC / "portable" / "lib32"
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


def test_portable_layers_do_not_reach_back_into_the_sdl_backend():
    offenders = []
    for path in [HOST_HEADER, *_source_files(PORT)]:
        text = path.read_text()
        if "c2_sdl_" in text:
            offenders.append(str(path.relative_to(ROOT)))
    assert not offenders, "portable layer depends on SDL backend:\n" + "\n".join(offenders)


def test_sdl_callback_does_not_mutate_legacy_game_state():
    main = (SDL_BACKEND / "c2_sdl_main.c").read_text()
    forbidden = ("c2inf", "internal_screen", "current_palette", "show_skill")
    offenders = [symbol for symbol in forbidden if symbol in main]
    assert not offenders, f"SDL callback reaches legacy state: {offenders}"


def test_optional_media_is_an_explicit_host_capability():
    header = HOST_HEADER.read_text()
    backend = (SDL_BACKEND / "c2_sdl_host.c").read_text()
    assert "C2_HOST_CAPABILITY_MUSIC" in header
    assert "C2_HOST_CAPABILITY_VIDEO" in header
    assert "int c2_host_has_capability" in backend


def test_portable_lib32_slice_remains_engine_side():
    offenders = []
    for path in _source_files(PORTABLE_LIB32):
        if "c2_host_" in path.read_text():
            offenders.append(str(path.relative_to(ROOT)))
    assert not offenders, "legacy engine support reaches the host:\n" + "\n".join(offenders)
