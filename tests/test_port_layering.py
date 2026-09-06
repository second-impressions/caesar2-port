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
    assert "c2_sdl_host_set_headless_arrow_keys" in smoke


def test_observation_sources_are_debug_only():
    cmake = (ROOT / "CMakeLists.txt").read_text()
    assert "$<$<CONFIG:Debug>:PORT_DEBUG_BUILD=1>" in cmake
    assert "$<$<CONFIG:Debug>:src/platform/common/c2_port_observation.c>" in cmake
    assert "$<$<CONFIG:Debug>:src/platform/sdl3/c2_sdl_smoke.c>" in cmake


def test_posix_crash_handler_ships_in_every_configuration_and_is_sanitizer_safe():
    cmake = (ROOT / "CMakeLists.txt").read_text()
    presets = (ROOT / "CMakePresets.json").read_text()
    assert "if(UNIX AND NOT EMSCRIPTEN AND PORT_ENABLE_POSIX_DEBUG_CRASH_HANDLER)" in cmake
    assert "target_sources(caesar2 PRIVATE src/platform/posix/c2_posix_debug.c)" in cmake
    # Crash logs must be readable as pasted into an issue: every build carries
    # debug information, exports its symbols, and symbolizes through the
    # distribution's libbacktrace when present.
    assert "add_compile_options(-g)" in cmake
    assert "set_target_properties(caesar2 PROPERTIES ENABLE_EXPORTS ON)" in cmake
    assert "find_package(LibBacktrace)" in cmake
    assert presets.count('"PORT_ENABLE_POSIX_DEBUG_CRASH_HANDLER": "OFF"') == 2


def test_wasm_reuses_the_sdl_host_and_recovered_engine_worker():
    cmake = (ROOT / "CMakeLists.txt").read_text()
    main = (SDL_BACKEND / "c2_sdl_main.c").read_text()
    assert "-sPTHREAD_POOL_SIZE=2" in cmake
    assert "-sINITIAL_MEMORY=100663296" in cmake
    assert "-sALLOW_MEMORY_GROWTH=0" in cmake
    assert "-sWASMFS" in cmake
    assert "wasmfs_create_opfs_backend" in main
    assert "c2_wasm_implicit_void.h" in cmake
    assert "src/platform/wasm" not in cmake
    assert 'C2_HOST_ACTIVE_CALLBACK_RATE "120"' in main
    assert 'C2_HOST_IDLE_CALLBACK_RATE "15"' in main
    # Pointer input is delivered when SDL pushes it, not at the callback rate.
    assert "static bool SDLCALL push_pointer_event" in main
    assert "SDL_AddEventWatch(push_pointer_event" in main
    assert "already delivered synchronously by watch" in main
    assert "c2_sdl_host_is_interactive()" in main
    assert "c2_host_sleep_ms(8)" not in main


def test_dependencies_come_from_the_build_host():
    """Packagers need every library to be found, never bundled: no submodules,
    no FetchContent, only the unpackaged decoders as plain files with
    provenance."""
    cmake = (ROOT / "CMakeLists.txt").read_text()
    assert not (ROOT / ".gitmodules").exists()
    assert "FetchContent" not in cmake
    assert "ExternalProject" not in cmake
    assert "find_package(SDL3" in cmake
    assert "find_package(ZLIB REQUIRED)" in cmake
    assert "add_subdirectory(third_party" not in cmake
    bundled = sorted(p.name for p in (ROOT / "third_party").iterdir() if p.is_dir())
    assert bundled == ["font8x8", "libsmacker", "nuked-opl3"]
    provenance = (ROOT / "third_party/README.md").read_text()
    for name in bundled:
        assert f"`{name}/`" in provenance


def test_language_builds_split_artifacts_without_branching_the_engine():
    cmake = (ROOT / "CMakeLists.txt").read_text()
    assert 'set(C2_LANGUAGE "en" CACHE STRING' in cmake
    assert 'OUTPUT_NAME "index"' in cmake
    assert "target_compile_definitions(c2_import_core PRIVATE" in cmake
    assert "${C2_PLATFORM_LEAF}=1" in cmake
    assert "target_link_libraries(c2_import_core PUBLIC ZLIB::ZLIB SDL3::SDL3)" in cmake
    assert 'c2_require_language_asset("c2.eng")' in cmake
    assert 'c2_require_language_asset("help.eng")' in cmake

    offenders = []
    for path in _source_files(SRC):
        if "C2_LANGUAGE" in path.read_text():
            offenders.append(str(path.relative_to(ROOT)))
    assert not offenders, "language build tag escaped into the engine:\n" + "\n".join(offenders)


def test_wasm_shell_owns_import_switching_and_save_export():
    cmake = (ROOT / "CMakeLists.txt").read_text()
    shell = "\n".join(
        (ROOT / "web" / path).read_text()
        for path in ("caesar2.html", "c2_shell.css", "c2_shell.js.in")
    )
    assert "configure_file(web/caesar2.html" in cmake
    assert "configure_file(web/c2_shell.js.in" in cmake
    assert "configure_file(web/c2_shell.css" in cmake
    assert 'src="c2-shell.js"' in shell
    assert 'href="c2-shell.css"' in shell
    assert "--js-library=${CMAKE_CURRENT_SOURCE_DIR}/web/c2_browser.js" in cmake
    assert "resizeCanvasToIntegerScale" in shell
    assert "devicePixelRatio || 1" in shell
    assert "Math.floor" in shell
    assert "--c2-canvas-width" in shell
    assert "navigator.storage.getDirectory" in shell
    assert "navigator.storage.persist" in shell
    assert 'id="folder-input"' in shell
    assert 'id="file-input" type="file" accept=".zip,.c2assets,.iso,.bin,.cue,.img" multiple' in shell
    assert "webkitdirectory" in shell
    # One drop zone and two browse actions replace the per-format buttons;
    # the importer classifies content itself.
    assert 'id="source-drop" class="c2-drop-zone' in shell
    assert "async function fileLooksImportable" in shell
    assert "async function importDrop" in shell
    assert "webkitGetAsEntry" in shell
    assert 'id="operation-dialog"' in shell
    assert 'id="operation-progress"' in shell
    assert "beginOperation(\"Checking game data\", 0, \"Reading source catalog…\")" in shell
    assert "elapsed" not in shell
    assert "onImportProgress(phase, completedKiB, totalKiB" in shell
    assert "onImportError(message)" in shell
    assert "A CUE sheet needs its BIN image; select the BIN file" in shell
    assert "use Browse folder or drop the whole folder" in shell
    assert "beginOperation(\"Removing cached assets\"" in shell
    assert "writeBrowserFile(root, relative, file, onBytes)" in shell
    assert "Browse folder" in shell
    assert "Browse file" in shell
    assert "ISO image" not in shell
    assert "BIN + CUE" not in shell
    assert 'id="pane-assets"' in shell
    assert "Load your Caesar II game data to play." in shell
    assert "Preparing…" not in shell
    assert "Load game data" in shell
    assert "Replace game data" in shell
    assert "Change assets" not in shell
    # Play stays disabled and explains itself until validated data exists.
    assert 'data-tooltip="Load assets first"' in shell
    # Uploads are imported without starting the engine.
    assert "--prepare-assets" in shell
    sdl_main = (SDL_BACKEND / "c2_sdl_main.c").read_text()
    assert "--prepare-assets" in sdl_main
    assert "prepare_assets" in sdl_main
    assert "create_prepare_thread(app)" in sdl_main
    assert "SDL_PROP_THREAD_CREATE_STACKSIZE_NUMBER, 1024 * 1024" in sdl_main
    assert "SDL_GetAtomicInt(&app->prepare_result)" in sdl_main
    assert "prepare-assets-rejects-missing-source" in cmake
    assert "startGame(pending" not in shell
    # Play is offered for remembered, cached, or bundled data alike.
    assert "async function discoverSource" in shell
    assert '/persistent/game-data/${name}' in shell
    assert 'id="forget-button"' in shell
    assert "Cached assets" in shell
    assert 'id="play-button" type="button" aria-disabled="true"' in shell
    assert "C2_HAS_BUNDLED_ASSETS" in cmake
    assert "HAS_BUNDLED_ASSETS" in shell
    assert 'id="pane-userdata"' in shell
    assert 'id="userdata-input" type="file" accept=".sav,.dat,.inf,.zip" multiple' in shell
    assert 'id="userdata-drop" class="c2-drop-zone' in shell
    assert 'id="userdata-import"' in shell
    assert "async function importUserData" in shell
    # The user-data pane uses the same reusable setting components.
    assert 'class="c2-settings-row"' in shell
    assert 'class="c2-compact-action' in shell
    # The Rendering tab owns presentation settings.
    assert 'id="pane-rendering"' in shell
    assert 'data-pane="rendering"' in shell
    assert '>Rendering</button>' in shell
    assert 'id="pane-game"' not in shell
    assert 'id="fullscreen-toggle"' in shell
    assert 'name="c2-scaling"' in shell
    assert 'requestFullscreen()' in shell
    assert 'scalingMode === "fractional"' in shell
    assert 'args.push("--fractional-scaling")' in shell
    assert "Module._c2_browser_set_fractional_scaling" in shell
    assert "Module._c2_browser_set_canvas_size(cssWidth, cssHeight)" in shell
    host = (SDL_BACKEND / "c2_sdl_host.c").read_text()
    assert "void c2_host_set_canvas_size" in host
    assert "SDL_SetWindowSize(c2_window, width, height)" in host
    assert "void c2_host_set_fractional_scaling" in host
    assert "SDL_LOGICAL_PRESENTATION_LETTERBOX" in host
    assert "SDL_LOGICAL_PRESENTATION_INTEGER_SCALE" in host
    # Fullscreen exits report the previous viewport for a frame or two.
    assert "function scheduleCanvasResize" in shell
    assert 'addEventListener("resize", scheduleCanvasResize)' in shell
    assert "Math.ceil(640 * scale" not in shell
    # Host chrome pauses the running game through the engine's own action.
    assert "setChromePause(true)" in shell
    assert "Module._c2_browser_set_pause" in shell
    pause = (ROOT / "src" / "platform" / "common" / "c2_port_pause.c").read_text()
    assert "act_pause();" in pause
    assert "c2_host_take_pause_request" in pause
    assert "c2inf.paused" in pause
    gloops = (ROOT / "src" / "gloops.c").read_text()
    assert "#if PORT_FEAT_HOST_PAUSE" in gloops
    # Generic UI, city, and battle loops each have their own frame entry.
    assert gloops.count("c2_port_apply_pause_request();") == 3
    assert gloops.count("!c2_port_host_pause_active()") == 2
    target_header = (ROOT / "include" / "c2_target.h").read_text()
    assert "#define PORT_FEAT_HOST_PAUSE PORT_PLATFORM" in target_header
    # The continuation has no native Windows repaint path; retain the DOS
    # dirty-tile invalidation contract to avoid stale province diamonds.
    assert "#elif PORT_PLATFORM" in target_header
    for feature in (
        "C2_FEAT_REGION_SIDED_DRAW",
        "C2_FEAT_CITY_TOP_DIRECTION_INIT",
        "C2_FEAT_BATTLE_ZOOM2_ROTATE_CLAMP",
        "C2_FEAT_SOFTWARE_BATTLE_SETUP",
    ):
        assert f"#  define {feature}" in target_header
    assert "PORT_FEAT_REGION_SIDED_DRAW" not in target_header
    assert "#define PORT_FEAT_STICKY_DROPDOWNS PORT_PLATFORM" in target_header
    assert "#define PORT_FIX_PAUSED_MUSIC_VARIETY PORT_PLATFORM" in target_header
    assert "#define PORT_FIX_REGION_IDLE_CLICK_FUNDS PORT_PLATFORM" in target_header
    action_source = (SRC / "action.c").read_text()
    loadsave = (SRC / "loadsave.c").read_text()
    assert "if (reg_placing_type == 0) return;" in action_source
    assert "#if PORT_FIX_REGION_IDLE_CLICK_FUNDS\n                    clear_mouse();" in loadsave
    music = (SRC / "pcsound.c").read_text()
    assert "c2_port_city_music_branch" in music
    assert "c2inf.paused != 0" in music
    assert "c2_port_paused_music_branch" in music
    action = (SRC / "action.c").read_text()
    controls = (SRC / "controls.c").read_text()
    # Armed once per command strip dispatcher (city and province), not per
    # list: every icon-opened list gets the same click-to-open behaviour.
    assert action.count("c2_port_selection_begin(mouse_x, mouse_y);") == 2
    assert action.count("c2_port_selection_end();") == 2
    for dispatcher in ("city_actions[last_icon_over - 4]();",
                       "region_actions[last_icon_over - 4]();"):
        armed = action.index(dispatcher)
        assert action.rfind("c2_port_selection_begin(mouse_x, mouse_y);",
                            0, armed) > armed - 300
        assert action.find("c2_port_selection_end();", armed) < armed + 200
    assert "c2_port_selection_consume_release(mouse_x, mouse_y)" in controls
    selection = (SRC / "platform/common/c2_port_selection.c").read_text()
    assert "PORT_SELECTION_CLICK_SLOP 4" in selection
    assert "initial_release_pending = 0;" in selection
    pm_map2 = (SRC / "pm_map2.c").read_text()
    assert pm_map2.count("#if C2_FEAT_REGION_SIDED_DRAW") == 6
    assert '<div class="actions">\n              <button id="userdata-export"' not in shell
    assert "importUserZip" in shell
    assert "User-data ZIP exceeds the 8 MiB limit" in shell
    assert "await reader.cancel()" in shell
    assert "ZIP paths are not valid user-data names" in shell
    assert '>Export</button>' in shell
    assert "history.dat" in shell
    assert "caesar2.inf" in shell
    assert "caesar2-user-data.zip" in shell
    assert "zipStore" in shell
    assert "async function exportUserData()" in shell
    assert "link.click();" in shell
    assert 'id="include-settings"' not in shell
    assert 'id="user-downloads"' not in shell
    assert "Download all saves" not in shell
    assert 'id="profile-select"' in shell
    assert 'id="profile-input"' not in shell
    assert 'id="single-language"' not in shell
    assert 'id="language-label"' not in shell
    assert "knownEditions" in shell
    # The assets modal reports what was actually loaded.
    assert 'id="assets-summary"' in shell
    assert "updateAssetsSummary" in shell
    assert "originLabel" in shell
    assert '["Edition", info.edition]' in shell
    assert 'rows.push(["Layout", info.layout])' in shell
    assert "DOS/Win95 hybrid · DOS assets" in shell
    assert 'assetsButton.textContent = info.available ? "Replace game data" : "Load game data"' in shell
    assert "Change assets" not in shell
    assert "sourceInfo" in shell
    assert '<title>Caesar II — @C2_VERSION_STRING@</title>' in shell
    assert 'id="about-dialog"' in shell
    assert "❧" not in shell
    assert "@C2_VERSION_STRING@" in shell
    assert 'href="pico.min.css"' in shell
    assert 'url("caesar2-background.jpg")' in shell
    assert 'url("caesar2-background-light.jpg")' in shell
    assert "configure_file(web/vendor/pico.min.css" in cmake
    assert "configure_file(web/caesar2-background.jpg" in cmake
    assert "configure_file(web/caesar2-background-light.jpg" in cmake
    # The production favicon ships with the page; candidate galleries live in
    # the separate second-impressions/assets repository.
    favicon = (ROOT / "web" / "favicon.svg").read_text()
    assert favicon.startswith('<svg xmlns="http://www.w3.org/2000/svg"')
    assert 'viewBox="0 0 64 64"' in favicon
    assert '<link rel="icon" href="favicon.svg" type="image/svg+xml" sizes="any">' in shell
    assert "configure_file(web/favicon.svg" in cmake
    workflow_text = (ROOT / ".github" / "workflows" / "ci.yml").read_text()
    assert "build/ci-wasm/favicon.svg" in workflow_text
    assert "favicon.svg; do" in workflow_text  # copied into the published site
    assert not (ROOT / "web" / "favicon-gallery.html").exists()
    assert not (ROOT / "web" / "favicon-candidates").exists()
    assert (ROOT / "web" / "vendor" / "pico.min.css").stat().st_size > 10_000
    assert (ROOT / "web" / "caesar2-background.jpg").stat().st_size > 100_000
    assert (ROOT / "web" / "caesar2-background-light.jpg").stat().st_size > 100_000
    # Theme follows the system unless the user picks one in the top bar.
    assert 'id="settings-dialog"' in shell
    # One settings modal with categories on the left, content on the right.
    assert 'role="tablist"' in shell
    assert 'class="c2-settings-tab"' in shell
    assert 'id="pane-general"' in shell
    assert "function selectSettingsPane" in shell
    assert "grid-template-columns: 8.5rem 1fr" in shell
    # Shared primitives and spacing tokens own component geometry.
    assert "--c2-space-4: .7rem" in shell
    assert ".c2-stack {" in shell
    assert ".c2-surface {" in shell
    assert ".c2-action-grid {" in shell
    assert 'class="c2-surface c2-splash c2-stack"' in shell
    assert 'class="c2-settings-row"' in shell
    for legacy_class in ("setting", "setting-action", "segmented", "hint",
                         "actions", "choices"):
        assert f'class="{legacy_class}"' not in shell
    components_doc = (ROOT / "web" / "COMPONENTS.md").read_text()
    assert "Vertical rhythm belongs to the parent" in components_doc
    # The dialog keeps one size and empty status lines take no space.
    assert ".c2-settings-panes { height: 15rem; overflow: visible; }" in shell
    assert ".c2-hint:empty { display: none; }" in shell
    # Top-bar links use the brand colour, and About sits last.
    assert ".topbar .nav-action" in shell
    assert shell.index('id="settings-button"') < shell.index('id="about-button"')
    assert 'id="settings-button"' in shell
    assert "https://github.com/second-impressions/caesar2-port" in shell
    assert "https://github.com/second-impressions/caesar2-reconstruction" in shell
    assert "game assets are not distributed" in shell
    assert "supplied by the user" in shell
    assert 'href="LICENSE"' in shell
    assert "AGPL-3.0-or-later" in shell
    license_text = (ROOT / "LICENSE").read_text()
    assert "GNU AFFERO GENERAL PUBLIC LICENSE" in license_text
    assert "Version 3, 19 November 2007" in license_text
    assert 'configure_file(LICENSE "${CMAKE_CURRENT_BINARY_DIR}/LICENSE" COPYONLY)' in cmake
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text()
    assert "build/ci-wasm/LICENSE" in workflow
    assert "version.txt LICENSE favicon.svg; do" in workflow  # published with the site
    assert (shell.index('id="pane-general"') <
            shell.index('id="confirm-close-toggle"') <
            shell.index('id="pane-rendering"'))
    assert 'role="radiogroup"' in shell
    assert 'value="system"' in shell
    assert 'value="light"' in shell
    assert 'value="dark"' in shell
    assert "class=\"c2-segmented\"" in shell
    assert 'systemDark.addEventListener("change"' in shell
    assert 'id="theme-toggle"' not in shell
    assert 'id="theme-menu"' not in shell
    # Pico's own light palette outranks a plain :root rule, so the accent
    # mapping must be more specific than :root:not([data-theme=dark]).
    assert ":root:root:root {" in shell
    assert "Ready to rule" not in shell
    assert "tagline" not in shell
    for slogan in ("Veni, Vidi, Vici", "Pictura praeferenda est mille verbis",
                   "Tempus figit", "Carpe diem", "Impera!",
                   "Build a city… Build an empire!"):
        assert slogan not in shell
    # The assets modal owns its own state: summary plus removal, or choices.
    assert 'id="assets-loaded"' in shell
    assert "No game data has been loaded yet" in shell
    assert "Drop new game data here to replace the current set" in shell
    assert 'if (pane === "assets") {' in shell
    assert "updateAssetsSummary().catch(error =>" in shell
    assert 'beginOperation("Removing cached assets", targets.length)' in shell
    assert "updateOperation(removed, targets.length" in shell
    assert "@media (prefers-color-scheme: light)" in shell
    assert ':root:not([data-theme])' in shell
    assert 'localStorage.getItem("c2.theme.v1")' in shell
    # The backdrop stays blurred and dims while the game runs.
    assert "--c2-backdrop-blur" in shell
    assert "--c2-backdrop-playing: .25" in shell
    assert "body.playing::before" in shell
    # Provenance is the label of the choice the user pressed, never invented.
    assert "Previously imported game data" not in shell
    assert "chosenSourceLabel = label; input.click()" in shell
    assert "Module.callMain" in shell
    assert "noInitialRun: true" in shell
    # A stopped SDL/engine instance is not reinitialized in-place.
    assert "if (engineHasRun)" in shell
    assert "sessionStorage.setItem(AUTOSTART_SOURCE, source)" in shell
    assert "location.reload();" in shell
    # Right-click belongs to a running game only; elsewhere the browser keeps
    # its ordinary context menu.
    assert 'canvas.addEventListener("contextmenu", e =>' in shell
    assert "if (!gameRunning) return;" in shell
    assert "e.preventDefault();" in shell
    assert 'document.addEventListener("contextmenu", e =>' not in shell
    assert "c2_browser_show_restart();" in (
        SDL_BACKEND / "c2_sdl_main.c"
    ).read_text()
    # Fixed filenames mean a cached mix of two builds would be fatal.
    worker = (ROOT / "web" / "coi-serviceworker.js").read_text()
    assert 'fetch(request, {cache: "no-cache"})' in worker
    assert 'updateViaCache: "none"' in worker
    # A byte-identical worker is never reinstalled, so it carries the version.
    assert 'const C2_BUILD_VERSION = "@C2_VERSION_STRING@";' in worker
    assert 'configure_file(web/coi-serviceworker.js\n        "${CMAKE_CURRENT_BINARY_DIR}/coi-serviceworker.js" @ONLY)' in cmake
    assert 'navigator.serviceWorker.addEventListener("controllerchange"' in worker
    assert 'document.body?.classList.contains("playing")' in worker
    assert "globalThis.crossOriginIsolated && !navigator.serviceWorker.controller" in worker
    assert "registration.update().catch" in worker
    # Losing an unsaved city to a closed tab is opt-in protected.
    assert 'id="confirm-close-toggle"' in shell
    assert 'addEventListener("beforeunload"' in shell
    assert '"c2.confirm-close.v1"' in shell
    # The page repairs a stale cache itself rather than asking the user to.
    assert 'const BUILD_VERSION = "@C2_VERSION_STRING@";' in shell
    assert "async function ensureCurrentBuild" in shell
    assert 'fetch(`version.txt?ts=${Date.now()}`, {cache: "no-store"})' in shell
    assert "registration.unregister()" in shell
    assert "caches.delete(key)" in shell
    assert "locateFile:" in shell
    assert "`${generated.src}?v=${encodeURIComponent(BUILD_VERSION)}`" in shell
    assert 'self.send_header("Cache-Control", "no-store, must-revalidate")' in (
        ROOT / "tools" / "serve-wasm.py"
    ).read_text()
    browser_bridge = (ROOT / "web" / "c2_browser.js").read_text()
    assert "c2_browser_import_progress" in browser_bridge
    assert "c2_browser_import_error" in browser_bridge
    assert 'c2_browser_show_restart__proxy: "sync"' in browser_bridge
    wasm_smoke = (ROOT / "tools/smoke-wasm.mjs").read_text()
    assert 'save: "save/load disk and full-state verification restored"' in wasm_smoke
    assert 'Module["onGameExit"]()' in browser_bridge
    video = (ROOT / "src" / "platform" / "common" / "c2_port_video.c").read_text()
    assert "static int show_movie_fallback" in video
    assert "if (c2inf.anims_on == 0)" in video
    assert 'memcpy(extension + 1, "pl8", 4)' in video
    assert 'memcpy(extension + 1, "256", 4)' in video


def test_browser_smokes_use_managed_playwright_chromium():
    flake = (ROOT / "flake.nix").read_text()
    smoke = (ROOT / "tools" / "smoke-wasm.mjs").read_text()
    assert "pkgs.playwright-test" in flake
    assert "pkgs.playwright-driver.browsers" in flake
    assert 'require("playwright")' in smoke
    assert "await chromium.launch" in smoke


def test_asan_preset_instruments_globals():
    """Layout-dependent reads past a global (the bath SIGFPE, the
    our_battle_army save entry) are only visible with global redzones."""
    presets = (ROOT / "CMakePresets.json").read_text()
    cmake = (ROOT / "CMakeLists.txt").read_text()
    assert '"PORT_ASAN_DISABLE_GLOBALS": "ON"' not in presets
    assert '"CMAKE_C_FLAGS": "-fsanitize=address,undefined -fno-omit-frame-pointer"' in presets
    assert "src/platform/posix/c2_posix_sanitizer.c" in cmake
    # The opt-out stays compile-only so it never reaches feature-check links.
    assert "add_compile_options(-mllvm -asan-globals=0)" in cmake


def test_music_library_is_plain_c_without_a_midi_dependency():
    cmake = (ROOT / "CMakeLists.txt").read_text()
    audio = (ROOT / "src/platform/common/c2_port_audio.c").read_text()
    assert "LANGUAGES C)" in cmake
    assert "CXX" not in cmake
    assert "ADLMIDI" not in cmake
    assert "add_library(c2_xmidi STATIC" in cmake
    assert "third_party/nuked-opl3/opl3.c" in cmake
    assert '#include "xmidi/xmidi.h"' in audio
    assert "adl_" not in audio
    # The driver tables are exported so the test can verify them against the
    # shipped OPL3.MDI image.
    header = (ROOT / "include/xmidi/miles_opl.h").read_text()
    test = (ROOT / "tests/c2_xmidi_test.c").read_text()
    for table in ("fnum_table", "velocity_table", "init_registers",
                  "4op_enable_mask"):
        assert "miles_opl_" + table in header
        assert "miles_opl_" + table in test
    assert '"OPL3.MDI"' in test


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
        SRC / "c2_text.c",
    ]
    assert not [path for path in misplaced if path.exists()]
    expected = [
        PLATFORM_COMMON / "c2_port_bugfixes.c",
        PLATFORM_COMMON / "c2_port_save_compat.c",
        PLATFORM_COMMON / "c2_port_text.c",
    ]
    assert all(path.is_file() for path in expected)


def test_portable_asm_manifest_does_not_reach_the_watcom_source_path():
    data_header = (ROOT / "include" / "c2_data.h").read_text()
    guarded_include = (
        '#if PORT_PLATFORM\n#include "c2_asm_routines.h"\n#endif'
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
    # Physical pixels on every target, so integer multiples are real ones.
    assert "SDL_WINDOW_RESIZABLE | SDL_WINDOW_HIGH_PIXEL_DENSITY" in host
    assert "SDL_GetWindowPixelDensity(c2_window)" in host
    assert "? SDL_LOGICAL_PRESENTATION_LETTERBOX" in host
    assert ": SDL_LOGICAL_PRESENTATION_INTEGER_SCALE" in host
