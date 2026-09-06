cmake_minimum_required(VERSION 3.25)

project(caesar2-port VERSION 1.0.0 LANGUAGES C)

list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}/cmake")

set(C2_BUILD_NUMBER "" CACHE STRING
    "Monotonic build number appended to the semantic version")
set(C2_GIT_HASH "" CACHE STRING
    "Short Git revision appended to the build version")
if(NOT C2_BUILD_NUMBER AND DEFINED ENV{C2_BUILD_NUMBER})
    set(C2_BUILD_NUMBER "$ENV{C2_BUILD_NUMBER}")
endif()
if(NOT C2_GIT_HASH AND DEFINED ENV{C2_GIT_HASH})
    set(C2_GIT_HASH "$ENV{C2_GIT_HASH}")
endif()
if(NOT C2_BUILD_NUMBER)
    execute_process(COMMAND git rev-list --count HEAD
        WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}"
        OUTPUT_VARIABLE C2_BUILD_NUMBER
        OUTPUT_STRIP_TRAILING_WHITESPACE
        ERROR_QUIET)
endif()
if(NOT C2_BUILD_NUMBER MATCHES "^[0-9]+$")
    set(C2_BUILD_NUMBER "0")
endif()
if(NOT C2_GIT_HASH)
    execute_process(COMMAND git rev-parse --short=8 HEAD
        WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}"
        OUTPUT_VARIABLE C2_GIT_HASH
        OUTPUT_STRIP_TRAILING_WHITESPACE
        ERROR_QUIET)
endif()
if(NOT C2_GIT_HASH MATCHES "^[0-9A-Fa-f]+$")
    set(C2_GIT_HASH "local")
else()
    string(LENGTH "${C2_GIT_HASH}" C2_GIT_HASH_LENGTH)
    if(C2_GIT_HASH_LENGTH GREATER 8)
        string(SUBSTRING "${C2_GIT_HASH}" 0 8 C2_GIT_HASH)
    endif()
endif()
# string(TIMESTAMP) honors SOURCE_DATE_EPOCH, which the Nix dev shell pins to
# 315532800; that would stamp every build 1980-01-01, so read the real clock
# and put the variable back for the rest of the configure.
set(C2_SAVED_SOURCE_DATE_EPOCH "$ENV{SOURCE_DATE_EPOCH}")
unset(ENV{SOURCE_DATE_EPOCH})
# A build from an edited worktree matches no commit, so a commit count and
# revision would misidentify it. Those builds are named after their configure
# time instead, which also keeps successive local builds distinguishable.
if(NOT DEFINED C2_LOCAL_BUILD_STAMP)
    execute_process(COMMAND git status --porcelain --untracked-files=no
        WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}"
        OUTPUT_VARIABLE C2_WORKTREE_STATUS
        OUTPUT_STRIP_TRAILING_WHITESPACE
        ERROR_QUIET)
    if(C2_WORKTREE_STATUS STREQUAL "")
        set(C2_LOCAL_BUILD_STAMP "")
    else()
        string(TIMESTAMP C2_LOCAL_BUILD_STAMP "%Y%m%d-%H%M%S" UTC)
    endif()
endif()
if(C2_SAVED_SOURCE_DATE_EPOCH)
    set(ENV{SOURCE_DATE_EPOCH} "${C2_SAVED_SOURCE_DATE_EPOCH}")
endif()
if(C2_LOCAL_BUILD_STAMP STREQUAL "")
    set(C2_VERSION_STRING "${PROJECT_VERSION}-${C2_BUILD_NUMBER}-${C2_GIT_HASH}")
else()
    set(C2_VERSION_STRING "${PROJECT_VERSION}-${C2_LOCAL_BUILD_STAMP}")
endif()
message(STATUS "Caesar II build version: ${C2_VERSION_STRING}")
configure_file(include/c2_version.h.in
    "${CMAKE_CURRENT_BINARY_DIR}/generated/c2_version.h" @ONLY)

set(C2_TEST_SAVE_FIXTURE "" CACHE FILEPATH
    "Original 225745-byte Caesar II save used by compatibility tests")
set(C2_TEST_GAME_DATA_SOURCES "" CACHE STRING
    "Optional semicolon-separated directories/ZIPs/ISOs/CUEs/packs for corpus smoke tests")
set(C2_LANGUAGE "en" CACHE STRING
    "Two-letter language tag for this distribution artifact")
string(TOLOWER "${C2_LANGUAGE}" C2_LANGUAGE)
if(NOT C2_LANGUAGE MATCHES "^[a-z][a-z]$")
    message(FATAL_ERROR
        "Invalid C2_LANGUAGE '${C2_LANGUAGE}'; use a two-letter tag")
endif()
set(C2_LANGUAGE "${C2_LANGUAGE}" CACHE STRING
    "Two-letter language tag for this distribution artifact" FORCE)
message(STATUS "Caesar II language build: ${C2_LANGUAGE}")

# ---- Dependencies ----------------------------------------------------------
# Every library comes from the build host and is located here, in one place:
# the distribution package on Linux and the MinGW cross sysroot, the vcpkg
# manifest (vcpkg.json) on MSVC, Emscripten's own ports for the web build.
# Nothing is fetched or bundled; the only third_party/ code is the two
# decoders no distribution packages (see third_party/README.md).
#
#   SDL3 >= 3.4        required   window, input, audio, filesystem
#   zlib               required   Deflate for the ZIP importer
#   libbacktrace       optional   source lines in native crash reports
#                                 (PORT_WITH_LIBBACKTRACE=AUTO|ON|OFF)
#   Unity              tests      only with BUILD_TESTING
if(EMSCRIPTEN)
    # `embuilder build sdl3-mt zlib` populates the ports; the SDL3 port's
    # config file carries no version to check against.
    find_package(SDL3 CONFIG REQUIRED)
    execute_process(COMMAND em-config CACHE
        OUTPUT_VARIABLE C2_EMSCRIPTEN_CACHE
        OUTPUT_STRIP_TRAILING_WHITESPACE)
    set(ZLIB_INCLUDE_DIR "${C2_EMSCRIPTEN_CACHE}/sysroot/include" CACHE PATH "" FORCE)
    set(ZLIB_LIBRARY "${C2_EMSCRIPTEN_CACHE}/sysroot/lib/wasm32-emscripten/libz.a" CACHE FILEPATH "" FORCE)
else()
    find_package(SDL3 3.4 CONFIG REQUIRED)
endif()
find_package(ZLIB REQUIRED)
set(PORT_WITH_LIBBACKTRACE AUTO CACHE STRING
    "Symbolize crash reports with source lines through the system libbacktrace: AUTO, ON (required), OFF")
set_property(CACHE PORT_WITH_LIBBACKTRACE PROPERTY STRINGS AUTO ON OFF)
if(UNIX AND NOT EMSCRIPTEN AND NOT PORT_WITH_LIBBACKTRACE STREQUAL "OFF")
    if(PORT_WITH_LIBBACKTRACE STREQUAL "ON")
        find_package(LibBacktrace REQUIRED)
    else()
        find_package(LibBacktrace)
    endif()
endif()

# Every configuration carries debug information, so a crash in a release
# binary can be symbolized the same way as one in a Debug build (gdb, lldb,
# addr2line on the crash handler's +0x offsets, browser DevTools). Release
# code generation is unchanged; only the debug sections grow.
if(MSVC)
    set(CMAKE_MSVC_DEBUG_INFORMATION_FORMAT ProgramDatabase)
    add_link_options(/DEBUG)
else()
    add_compile_options(-g)
    if(EMSCRIPTEN)
        # Optimized links keep the wasm name section (function names in
        # browser stack traces) and write index.wasm.map beside the module so
        # DevTools shows source lines; the module itself stays free of DWARF.
        # Debug links keep the DWARF inline.
        add_link_options(
            $<$<CONFIG:Debug>:-g>
            $<$<NOT:$<CONFIG:Debug>>:-gsource-map>
            $<$<NOT:$<CONFIG:Debug>>:--profiling-funcs>)
    endif()
endif()

# Nuked OPL3 (LGPL-2.1-or-later): the FM chip behind the port's Miles
# OPL3 music driver.
add_library(c2_nuked_opl3 STATIC third_party/nuked-opl3/opl3.c)
target_compile_features(c2_nuked_opl3 PRIVATE c_std_11)
target_include_directories(c2_nuked_opl3 PUBLIC third_party/nuked-opl3)

# XMIDI sequencer and Miles OPL3 driver, reimplemented from the AIL 3.x
# library in PS.EXE and the shipped OPL3.MDI driver.
add_library(c2_xmidi STATIC
    src/xmidi/xmidi.c
    src/xmidi/miles_opl.c
    src/xmidi/miles_opl_tables.c)
target_compile_features(c2_xmidi PRIVATE c_std_11)
target_include_directories(c2_xmidi PUBLIC include)
target_link_libraries(c2_xmidi PRIVATE c2_nuked_opl3)

# Renders an XMIDI score through the driver to WAV for listening tests.
add_executable(c2-xmi-render EXCLUDE_FROM_ALL tools/c2-xmi-render.c)
target_compile_features(c2-xmi-render PRIVATE c_std_11)
target_link_libraries(c2-xmi-render PRIVATE c2_xmidi)

add_library(c2_libsmacker STATIC third_party/libsmacker/smacker.c)
target_compile_features(c2_libsmacker PRIVATE c_std_11)
target_include_directories(c2_libsmacker PUBLIC third_party)

add_library(c2_import_core STATIC
    src/platform/common/c2_iso.c
    src/platform/common/c2_cue.c
    src/platform/sdl3/c2_zip.c
    src/platform/sdl3/c2_import_fs.c
    src/platform/sdl3/c2_cdrom_fs.c
    src/platform/sdl3/c2_pack.c)
target_compile_features(c2_import_core PRIVATE c_std_11)
target_include_directories(c2_import_core PUBLIC include)
target_link_libraries(c2_import_core PUBLIC ZLIB::ZLIB SDL3::SDL3)

option(PORT_FIX_MEDIUM_RIGHT_HAT_OFFSET
    "Correct the misplaced pixel pair in the medium right diamond hat" ON)
option(PORT_FIX_LARGE_RIGHT_HALFROOF_SEAM_PAIR
    "Suppress the stray seam pair in the large right half-roof" ON)
option(PORT_FIX_GFX_BUFFER_DOUBLE_FREE
    "Clear released graphics pointers to prevent repeated frees" ON)
option(PORT_FIX_HELP_SMART_PUNCTUATION
    "Repair Windows smart punctuation embedded in help text" ON)
option(PORT_FIX_PLAYER_NAME_PADDING
    "Trim fixed-width trailing spaces before editing player names" ON)
option(PORT_FIX_LARGE_XMI_ASSETS
    "Accept official XMIDI assets larger than the legacy tune buffer" ON)
option(C2_FIX_MOSAIC_RANDOM_SENTINEL
    "Define the mosaic walk's accidental byte-64 sentinel explicitly" ON)
option(PORT_ENABLE_TEXT_ASSET_COMPAT
    "Adapt versioned engine UI to the structure of the loaded text asset" ON)
option(PORT_ENABLE_ARROW_KEY_SCROLL
    "Use held arrow keys to pan the active map instead of moving the cursor" ON)
option(PORT_ENABLE_POSIX_DEBUG_CRASH_HANDLER
    "Install native fatal-signal diagnostics in POSIX builds" ON)
option(PORT_ASAN_DISABLE_GLOBALS
    "Disable ASan global instrumentation for the recovered global data image" OFF)
if(PORT_ASAN_DISABLE_GLOBALS)
    if(NOT CMAKE_C_COMPILER_ID MATCHES "Clang")
        message(FATAL_ERROR "PORT_ASAN_DISABLE_GLOBALS requires Clang")
    endif()
    # Compile-only options belong here, not in CMAKE_*_FLAGS: CMake also puts
    # those flags on feature-check link commands, where Clang 21 warns.
    add_compile_options(-mllvm -asan-globals=0)
endif()
set(C2_WASM_ASSET_ROOT "" CACHE PATH
    "Original Caesar II asset directory to package into the WASM build")

add_library(c2_asm_portable STATIC
    src/asm/c2_asm_diamond_image.c
    src/asm/c2_asm_diamond_ptr.c
    src/asm/c2_asm_internal_raster.c
    src/asm/c2_asm_memory.c
    src/asm/c2_asm_sprite.c
    src/asm/c2_asm_state.c
    src/asm/c2_asm_stubs.c
)
target_compile_features(c2_asm_portable PRIVATE c_std_11)
target_include_directories(c2_asm_portable PUBLIC include)
if(PORT_FIX_MEDIUM_RIGHT_HAT_OFFSET)
    target_compile_definitions(c2_asm_portable PUBLIC
        PORT_FIX_MEDIUM_RIGHT_HAT_OFFSET=1)
else()
    target_compile_definitions(c2_asm_portable PUBLIC
        PORT_FIX_MEDIUM_RIGHT_HAT_OFFSET=0)
endif()
if(PORT_FIX_GFX_BUFFER_DOUBLE_FREE)
    add_compile_definitions(PORT_FIX_GFX_BUFFER_DOUBLE_FREE=1)
else()
    add_compile_definitions(PORT_FIX_GFX_BUFFER_DOUBLE_FREE=0)
endif()
if(PORT_FIX_HELP_SMART_PUNCTUATION)
    add_compile_definitions(PORT_FIX_HELP_SMART_PUNCTUATION=1)
else()
    add_compile_definitions(PORT_FIX_HELP_SMART_PUNCTUATION=0)
endif()
if(PORT_FIX_PLAYER_NAME_PADDING)
    add_compile_definitions(PORT_FIX_PLAYER_NAME_PADDING=1)
else()
    add_compile_definitions(PORT_FIX_PLAYER_NAME_PADDING=0)
endif()
if(PORT_FIX_LARGE_XMI_ASSETS)
    add_compile_definitions(PORT_FIX_LARGE_XMI_ASSETS=1)
else()
    add_compile_definitions(PORT_FIX_LARGE_XMI_ASSETS=0)
endif()
if(C2_FIX_MOSAIC_RANDOM_SENTINEL)
    add_compile_definitions(C2_FIX_MOSAIC_RANDOM_SENTINEL=1)
else()
    add_compile_definitions(C2_FIX_MOSAIC_RANDOM_SENTINEL=0)
endif()
if(PORT_ENABLE_TEXT_ASSET_COMPAT)
    add_compile_definitions(PORT_FEAT_TEXT_ASSET_COMPAT=1)
else()
    add_compile_definitions(PORT_FEAT_TEXT_ASSET_COMPAT=0)
endif()
if(PORT_ENABLE_ARROW_KEY_SCROLL)
    add_compile_definitions(PORT_FEAT_ARROW_KEY_SCROLL=1)
else()
    add_compile_definitions(PORT_FEAT_ARROW_KEY_SCROLL=0)
endif()
if(PORT_FIX_LARGE_RIGHT_HALFROOF_SEAM_PAIR)
    target_compile_definitions(c2_asm_portable PUBLIC
        PORT_FIX_LARGE_RIGHT_HALFROOF_SEAM_PAIR=1)
else()
    target_compile_definitions(c2_asm_portable PUBLIC
        PORT_FIX_LARGE_RIGHT_HALFROOF_SEAM_PAIR=0)
endif()
if(CMAKE_C_COMPILER_ID MATCHES "Clang|GNU")
    target_compile_options(c2_asm_portable PRIVATE
        -Wall
        -Wextra
        -Wpedantic
        -Wno-unused-parameter
    )
endif()

add_executable(caesar2
    src/action.c
    src/battle.c
    src/bbarian.c
    src/c2.c
    src/c2_vars.c
    src/census.c
    src/common.c
    src/controls.c
    src/contrdat.c
    src/data.c
    src/datainit.c
    src/debug.c
    src/display.c
    src/empire.c
    src/evolver.c
    src/formulae.c
    src/gloops.c
    src/hotkeys.c
    src/int_c2.c
    src/landfill.c
    src/lib32.c
    src/loadsave.c
    src/map.c
    src/message.c
    src/mmedia.c
    src/pm_map0.c
    src/pm_map1.c
    src/pm_map2.c
    src/pm_map3.c
    src/pcsound.c
    src/pump.c
    src/refresh.c
    src/rot_data.c
    src/screens.c
    src/speech.c
    src/titles.c
    src/web.c
    src/platform/common/c2_port_app.c
    src/platform/common/c2_port_audio.c
    src/platform/common/c2_port_bugfixes.c
    src/platform/common/c2_port_compat.c
    src/platform/common/c2_port_input.c
    src/platform/common/c2_port_keymap.c
    src/platform/common/c2_port_mouse.c
    src/platform/common/c2_port_music.c
    src/platform/common/c2_port_save.c
    src/platform/common/c2_port_save_compat.c
    src/platform/common/c2_port_pause.c
    src/platform/common/c2_port_selection.c
    src/platform/common/c2_port_save_registry.c
    src/platform/common/c2_port_text_compat.c
    src/platform/common/c2_port_timing.c
    src/platform/common/c2_port_video.c
    src/platform/sdl3/c2_sdl_audio.c
    src/platform/sdl3/c2_sdl_main.c
    src/platform/sdl3/c2_sdl_host.c
    src/platform/sdl3/c2_setup_ui.c
)

target_sources(caesar2 PRIVATE
    $<$<CONFIG:Debug>:src/platform/common/c2_port_observation.c>
    $<$<CONFIG:Debug>:src/platform/sdl3/c2_sdl_smoke.c>
)

target_compile_features(caesar2 PRIVATE c_std_11)
set_target_properties(caesar2 PROPERTIES
    C_STANDARD 11
    C_STANDARD_REQUIRED YES
    C_EXTENSIONS OFF
)

# PORT_PLATFORM_WIN32 is the modern Windows host continuation.  It is deliberately
# not PLATFORM_WINDOWS, which selects recovered 1996 Windows engine behavior.
if(EMSCRIPTEN)
    set(C2_PLATFORM_LEAF PORT_PLATFORM_WASM)
elseif(WIN32)
    set(C2_PLATFORM_LEAF PORT_PLATFORM_WIN32)
else()
    set(C2_PLATFORM_LEAF PORT_PLATFORM_LINUX)
endif()
message(STATUS "Caesar II target platform: ${C2_PLATFORM_LEAF}")

target_compile_definitions(caesar2 PRIVATE
    PORT_PLATFORM=1
    ${C2_PLATFORM_LEAF}=1
    $<$<CONFIG:Debug>:PORT_DEBUG_BUILD=1>
)
# Import readers are a separate target and need the same host leaf; otherwise
# Windows silently takes the POSIX fseeko path (MinGW happens to provide it,
# MSVC does not).
target_compile_definitions(c2_import_core PRIVATE
    PORT_PLATFORM=1
    ${C2_PLATFORM_LEAF}=1
)

if(UNIX AND NOT EMSCRIPTEN AND PORT_ENABLE_POSIX_DEBUG_CRASH_HANDLER)
    target_sources(caesar2 PRIVATE src/platform/posix/c2_posix_debug.c)
    target_compile_definitions(caesar2 PRIVATE PORT_ENABLE_POSIX_CRASH_HANDLER=1)
    target_link_libraries(caesar2 PRIVATE ${CMAKE_DL_LIBS})
    # backtrace_symbols_fd() names frames from the dynamic symbol table only.
    # Export the executable's symbols so a crash log names the engine
    # functions as printed, without addr2line or the matching binary.
    set_target_properties(caesar2 PROPERTIES ENABLE_EXPORTS ON)
    # With the distribution's libbacktrace (GCC's DWARF symbolizer) the
    # report also shows source file and line per frame.
    if(LibBacktrace_FOUND)
        message(STATUS "Crash reports: libbacktrace source lines (${LibBacktrace_LIBRARIES})")
        target_link_libraries(caesar2 PRIVATE LibBacktrace::LibBacktrace)
        target_compile_definitions(caesar2 PRIVATE
            PORT_ENABLE_LIBBACKTRACE=1
            "PORT_SOURCE_ROOT=\"${CMAKE_CURRENT_SOURCE_DIR}/\"")
    else()
        message(STATUS "Crash reports: function names only (libbacktrace not found)")
    endif()
endif()

target_include_directories(caesar2 PRIVATE
    include
    "${CMAKE_CURRENT_BINARY_DIR}/generated"
    src/platform/common
    src/platform/sdl3
)

# The original build exposed an independently ordered extern stream to each
# engine translation unit, always under the logical name c2_data.h.  Preserve
# that spelling while selecting the corresponding recovered stream.
set(C2_EXTERN_STREAM_TUS
    action battle bbarian c2 c2_vars census common controls contrdat data
    datainit debug display empire evolver formulae gloops hotkeys int_c2
    landfill lib32 loadsave map message mmedia pcsound pm_map0 pm_map1 pm_map2
    pm_map3 pump refresh rot_data screens smacker speech titles web winplatform
)
foreach(tu IN LISTS C2_EXTERN_STREAM_TUS)
    set(C2_EXTERN_STREAM_HEADER "c2_data_${tu}.h")
    set(stream_dir "${CMAKE_CURRENT_BINARY_DIR}/extern-streams/${tu}")
    file(MAKE_DIRECTORY "${stream_dir}")
    configure_file(
        cmake/c2_data_tu.h.in
        "${stream_dir}/c2_data.h"
        @ONLY
    )
    set_property(SOURCE "src/${tu}.c" APPEND PROPERTY
        INCLUDE_DIRECTORIES "${stream_dir}"
    )
endforeach()

target_link_libraries(caesar2 PRIVATE
    c2_asm_portable
    c2_import_core
    c2_libsmacker
    c2_xmidi
    SDL3::SDL3)

if(EMSCRIPTEN)
    if(C2_WASM_ASSET_ROOT)
        set(C2_HAS_BUNDLED_ASSETS 1)
    else()
        set(C2_HAS_BUNDLED_ASSETS 0)
    endif()
    set(C2_WASM_SHELL "${CMAKE_CURRENT_BINARY_DIR}/caesar2-shell.html")
    set(C2_WASM_UI_JS "${CMAKE_CURRENT_BINARY_DIR}/c2-shell.js")
    configure_file(web/caesar2.html "${C2_WASM_SHELL}" @ONLY)
    configure_file(web/c2_shell.js.in "${C2_WASM_UI_JS}" @ONLY)
    configure_file(web/c2_shell.css
        "${CMAKE_CURRENT_BINARY_DIR}/c2-shell.css" COPYONLY)
    # The worker carries the build version so browsers see a changed file and
    # install it; a byte-identical worker is never replaced.
    configure_file(web/coi-serviceworker.js
        "${CMAKE_CURRENT_BINARY_DIR}/coi-serviceworker.js" @ONLY)
    configure_file(web/vendor/pico.min.css
        "${CMAKE_CURRENT_BINARY_DIR}/pico.min.css" COPYONLY)
    configure_file(web/caesar2-background.jpg
        "${CMAKE_CURRENT_BINARY_DIR}/caesar2-background.jpg" COPYONLY)
    configure_file(web/caesar2-background-light.jpg
        "${CMAKE_CURRENT_BINARY_DIR}/caesar2-background-light.jpg" COPYONLY)
    configure_file(web/favicon.svg
        "${CMAKE_CURRENT_BINARY_DIR}/favicon.svg" COPYONLY)
    file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/version.txt"
        "${C2_VERSION_STRING}\n")
    configure_file(LICENSE "${CMAKE_CURRENT_BINARY_DIR}/LICENSE" COPYONLY)
    set_target_properties(caesar2 PROPERTIES
        OUTPUT_NAME "index"
        LINK_DEPENDS
            "${C2_WASM_SHELL};${C2_WASM_UI_JS};${CMAKE_CURRENT_SOURCE_DIR}/LICENSE;${CMAKE_CURRENT_SOURCE_DIR}/web/c2_shell.css;${CMAKE_CURRENT_SOURCE_DIR}/web/c2_browser.js;${CMAKE_CURRENT_SOURCE_DIR}/web/coi-serviceworker.js;${CMAKE_CURRENT_SOURCE_DIR}/web/vendor/pico.min.css;${CMAKE_CURRENT_SOURCE_DIR}/web/caesar2-background.jpg;${CMAKE_CURRENT_SOURCE_DIR}/web/caesar2-background-light.jpg;${CMAKE_CURRENT_SOURCE_DIR}/web/favicon.svg"
        SUFFIX ".html")
    target_compile_options(caesar2 PRIVATE
        -pthread
        -include "${CMAKE_CURRENT_SOURCE_DIR}/include/c2_wasm_implicit_void.h"
    )
    target_link_options(caesar2 PRIVATE
        -pthread
        -sPTHREAD_POOL_SIZE=2
        # The recovered game fit in 64 MiB. WasmFS plus the complete SDL/game
        # startup peaks just above 71 MiB, so reserve a fixed 96 MiB while
        # keeping imported assets in OPFS rather than enabling heap growth.
        -sINITIAL_MEMORY=100663296
        -sALLOW_MEMORY_GROWTH=0
        -sWASMFS
        -sFORCE_FILESYSTEM
        -sUSE_ZLIB=1
        -sINVOKE_RUN=0
        -sEXPORTED_RUNTIME_METHODS=callMain
        -sEXIT_RUNTIME=0
        "--shell-file=${C2_WASM_SHELL}"
        "--js-library=${CMAKE_CURRENT_SOURCE_DIR}/web/c2_browser.js"
    )
    if(C2_WASM_ASSET_ROOT)
        if(NOT IS_DIRECTORY "${C2_WASM_ASSET_ROOT}")
            message(FATAL_ERROR
                "C2_WASM_ASSET_ROOT is not a directory: ${C2_WASM_ASSET_ROOT}")
        endif()
        function(c2_require_language_asset filename)
            file(GLOB root_entries LIST_DIRECTORIES false
                "${C2_WASM_ASSET_ROOT}/*")
            string(TOLOWER "${filename}" required_name)
            set(found FALSE)
            foreach(entry IN LISTS root_entries)
                get_filename_component(entry_name "${entry}" NAME)
                string(TOLOWER "${entry_name}" entry_name)
                if(entry_name STREQUAL required_name)
                    set(found TRUE)
                    break()
                endif()
            endforeach()
            if(NOT found)
                message(FATAL_ERROR
                    "The ${C2_LANGUAGE} asset tree is missing ${filename}: "
                    "${C2_WASM_ASSET_ROOT}")
            endif()
        endfunction()
        c2_require_language_asset("c2.eng")
        c2_require_language_asset("help.eng")
        target_link_options(caesar2 PRIVATE
            "--preload-file=${C2_WASM_ASSET_ROOT}@/assets")
    else()
        message(STATUS
            "C2_WASM_ASSET_ROOT is empty; the web page will request a "
            "directory, ZIP, optimized pack, ISO, or BIN/CUE on first use")
    endif()
endif()

if(CMAKE_C_COMPILER_ID MATCHES "Clang|GNU")
    set_source_files_properties(src/display.c PROPERTIES
        COMPILE_OPTIONS -Wno-implicit-function-declaration
    )
    set_source_files_properties(
        src/controls.c
        src/contrdat.c
        src/action.c
        src/battle.c
        src/bbarian.c
        src/c2.c
        src/c2_vars.c
        src/census.c
        src/common.c
        src/data.c
        src/datainit.c
        src/debug.c
        src/empire.c
        src/evolver.c
        src/formulae.c
        src/gloops.c
        src/hotkeys.c
        src/int_c2.c
        src/landfill.c
        src/lib32.c
        src/loadsave.c
        src/map.c
        src/message.c
        src/mmedia.c
        src/pm_map0.c
        src/pm_map1.c
        src/pm_map2.c
        src/pm_map3.c
        src/pcsound.c
        src/pump.c
        src/refresh.c
        src/rot_data.c
        src/screens.c
        src/speech.c
        src/titles.c
        src/web.c
        PROPERTIES COMPILE_OPTIONS -Wno-implicit-function-declaration
    )
    set_source_files_properties(
        src/platform/sdl3/c2_sdl_main.c
        src/platform/sdl3/c2_sdl_audio.c
        src/platform/sdl3/c2_sdl_host.c
        src/platform/sdl3/c2_setup_ui.c
        src/platform/sdl3/c2_sdl_smoke.c
        src/platform/common/c2_port_app.c
        src/platform/common/c2_port_audio.c
        src/platform/common/c2_port_bugfixes.c
        src/platform/common/c2_port_compat.c
        src/platform/common/c2_port_input.c
        src/platform/common/c2_port_keymap.c
            src/platform/common/c2_port_mouse.c
        src/platform/common/c2_port_observation.c
        src/platform/common/c2_port_save.c
        src/platform/common/c2_port_save_compat.c
        src/platform/common/c2_port_save_registry.c
        src/platform/common/c2_port_text_compat.c
        src/platform/common/c2_port_timing.c
        src/platform/common/c2_port_video.c
        PROPERTIES COMPILE_OPTIONS -Wpedantic
    )
    target_compile_options(caesar2 PRIVATE
        -Wall
        -Wextra
        -Wno-incompatible-pointer-types
        -Wno-return-mismatch
        -fno-strict-aliasing
        -funsigned-char
        -fwrapv
        -fms-extensions
        -ffunction-sections
        -fdata-sections
        $<$<C_COMPILER_ID:Clang>:-Wno-microsoft-anon-tag>
    )
    target_link_options(caesar2 PRIVATE -Wl,--gc-sections)
elseif(MSVC)
    # The recovered engine relies on the same legacy semantics the GNU/Clang
    # branch selects above: plain char is unsigned, signed overflow wraps,
    # type-based aliasing is not assumed, and anonymous nested structs are
    # accepted.  /J and the default /fp and /volatile settings cover those;
    # MSVC performs no strict-aliasing optimization to disable.
    target_compile_options(caesar2 PRIVATE
        /W3
        /J
        /Gy
        /wd4996   # POSIX/CRT deprecation of the recovered descriptor calls
    )
    target_compile_definitions(caesar2 PRIVATE
        _CRT_SECURE_NO_WARNINGS
        _CRT_NONSTDC_NO_WARNINGS
        WIN32_LEAN_AND_MEAN
        NOMINMAX
    )
    target_link_options(caesar2 PRIVATE /OPT:REF)
endif()

# ---- Installation ----------------------------------------------------------
# `cmake --install` lays the game out for a package: the binary, a desktop
# entry, an AppStream description and the icon on freedesktop hosts; the
# binary with the DLLs it needs on Windows. Game data is never installed;
# the launcher imports the player's own copy.
if(NOT EMSCRIPTEN)
    include(GNUInstallDirs)
    install(TARGETS caesar2 RUNTIME DESTINATION "${CMAKE_INSTALL_BINDIR}")
    install(FILES LICENSE DESTINATION "${CMAKE_INSTALL_DATAROOTDIR}/licenses/caesar2")
    install(FILES third_party/README.md
        DESTINATION "${CMAKE_INSTALL_DATAROOTDIR}/licenses/caesar2"
        RENAME THIRD_PARTY.md)
    install(FILES third_party/libsmacker/COPYING
        DESTINATION "${CMAKE_INSTALL_DATAROOTDIR}/licenses/caesar2"
        RENAME LICENSE.libsmacker)
    install(FILES third_party/nuked-opl3/LICENSE
        DESTINATION "${CMAKE_INSTALL_DATAROOTDIR}/licenses/caesar2"
        RENAME LICENSE.nuked-opl3)
    if(WIN32)
        install(FILES $<TARGET_RUNTIME_DLLS:caesar2>
            DESTINATION "${CMAKE_INSTALL_BINDIR}")
        # FindZLIB imports an UNKNOWN target, which TARGET_RUNTIME_DLLS
        # cannot see; the MinGW sysroot keeps the DLL beside the import lib.
        # vcpkg installs its own DLLs (X_VCPKG_APPLOCAL_DEPS_INSTALL).
        if(NOT MSVC)
            get_filename_component(C2_ZLIB_LIBDIR "${ZLIB_LIBRARY}" DIRECTORY)
            find_file(C2_ZLIB_DLL NAMES zlib1.dll libz.dll
                HINTS "${C2_ZLIB_LIBDIR}/../bin" "${C2_ZLIB_LIBDIR}")
            if(C2_ZLIB_DLL)
                install(FILES "${C2_ZLIB_DLL}" DESTINATION "${CMAKE_INSTALL_BINDIR}")
            endif()
        endif()
    else()
        install(FILES packaging/io.github.second_impressions.caesar2.desktop
            DESTINATION "${CMAKE_INSTALL_DATAROOTDIR}/applications")
        install(FILES packaging/io.github.second_impressions.caesar2.metainfo.xml
            DESTINATION "${CMAKE_INSTALL_DATAROOTDIR}/metainfo")
        install(FILES web/favicon.svg
            DESTINATION "${CMAKE_INSTALL_DATAROOTDIR}/icons/hicolor/scalable/apps"
            RENAME io.github.second_impressions.caesar2.svg)
    endif()
endif()

include(CTest)

if(BUILD_TESTING)
    add_test(NAME version-string COMMAND caesar2 --version)
    # Published builds carry a commit count and revision; local builds from an
    # edited worktree carry their configure time instead.
    set_tests_properties(version-string PROPERTIES
        PASS_REGULAR_EXPRESSION
            "Caesar II 1\\.0\\.0-([0-9]+-[0-9A-Fa-f]+|[0-9]{8}-[0-9]{6})")

    # Importing game data must not start the engine, so the browser shell can
    # validate an upload and return to its main window.
    add_test(NAME prepare-assets-rejects-missing-source
        COMMAND caesar2 --prepare-assets
            --game-data "${CMAKE_CURRENT_BINARY_DIR}/no-such-game-data.zip"
            --user-data-dir "${CMAKE_CURRENT_BINARY_DIR}/prepare-assets-test")
    set_tests_properties(prepare-assets-rejects-missing-source PROPERTIES
        WILL_FAIL TRUE)

    find_path(C2_UNITY_INCLUDE_DIR NAMES unity/unity.h REQUIRED)
    find_library(C2_UNITY_LIBRARY NAMES unity REQUIRED)
    add_library(c2_unity_framework UNKNOWN IMPORTED)
    set_target_properties(c2_unity_framework PROPERTIES
        IMPORTED_LOCATION "${C2_UNITY_LIBRARY}"
        INTERFACE_INCLUDE_DIRECTORIES "${C2_UNITY_INCLUDE_DIR}"
    )

    add_executable(c2-bugfixes-test
        tests/c2_bugfixes_test.c
        src/data.c
        src/platform/common/c2_port_bugfixes.c)
    target_compile_features(c2-bugfixes-test PRIVATE c_std_11)
    target_include_directories(c2-bugfixes-test PRIVATE include)
    target_compile_definitions(c2-bugfixes-test PRIVATE
        PORT_PLATFORM=1
        PORT_PLATFORM_LINUX=1)
    if(CMAKE_C_COMPILER_ID MATCHES "Clang|GNU")
        target_compile_options(c2-bugfixes-test PRIVATE -fms-extensions)
    endif()
    add_test(NAME bugfixes COMMAND c2-bugfixes-test)

    add_executable(c2-text-compat-test
        tests/c2_text_compat_test.c
        src/platform/common/c2_port_text_compat.c)
    target_compile_features(c2-text-compat-test PRIVATE c_std_11)
    target_include_directories(c2-text-compat-test PRIVATE include)
    add_test(NAME text-compat COMMAND c2-text-compat-test)

    add_executable(c2-port-timing-test
        tests/c2_port_timing_test.c
        src/platform/common/c2_port_timing.c)
    target_compile_features(c2-port-timing-test PRIVATE c_std_11)
    target_include_directories(c2-port-timing-test PRIVATE
        include
        src/platform/common)
    add_test(NAME port-timing COMMAND c2-port-timing-test)

    add_executable(c2-port-keymap-test
        tests/c2_port_keymap_test.c
        src/platform/common/c2_port_keymap.c)
    target_compile_features(c2-port-keymap-test PRIVATE c_std_11)
    target_include_directories(c2-port-keymap-test PRIVATE
        include
        src/platform/common)
    add_test(NAME port-keymap COMMAND c2-port-keymap-test)

    add_executable(c2-port-mouse-test
        tests/c2_port_mouse_test.c
        src/platform/common/c2_port_mouse.c)
    target_compile_features(c2-port-mouse-test PRIVATE c_std_11)
    target_include_directories(c2-port-mouse-test PRIVATE
        src/platform/common)
    target_link_libraries(c2-port-mouse-test PRIVATE c2_unity_framework)
    add_test(NAME port-mouse COMMAND c2-port-mouse-test)

    add_executable(c2-port-music-test
        tests/c2_port_music_test.c
        src/platform/common/c2_port_music.c)
    target_compile_features(c2-port-music-test PRIVATE c_std_11)
    target_compile_definitions(c2-port-music-test PRIVATE
        PORT_PLATFORM=1
        PORT_PLATFORM_LINUX=1)
    target_include_directories(c2-port-music-test PRIVATE
        include
        src/platform/common)
    target_link_libraries(c2-port-music-test PRIVATE c2_unity_framework)
    add_test(NAME port-music COMMAND c2-port-music-test)

    add_executable(c2-port-selection-test
        tests/c2_port_selection_test.c
        src/platform/common/c2_port_selection.c)
    target_compile_features(c2-port-selection-test PRIVATE c_std_11)
    target_compile_definitions(c2-port-selection-test PRIVATE
        PORT_PLATFORM=1
        PORT_PLATFORM_LINUX=1)
    target_include_directories(c2-port-selection-test PRIVATE
        include
        src/platform/common)
    target_link_libraries(c2-port-selection-test PRIVATE c2_unity_framework)
    add_test(NAME port-selection COMMAND c2-port-selection-test)

    add_executable(c2-port-pause-test
        tests/c2_port_pause_test.c
        src/platform/common/c2_port_pause.c)
    target_compile_features(c2-port-pause-test PRIVATE c_std_11)
    target_compile_definitions(c2-port-pause-test PRIVATE
        PORT_PLATFORM=1
        PORT_PLATFORM_LINUX=1)
    target_include_directories(c2-port-pause-test PRIVATE
        include
        src/platform/common)
    if(CMAKE_C_COMPILER_ID MATCHES "Clang|GNU")
        target_compile_options(c2-port-pause-test PRIVATE -fms-extensions)
    endif()
    target_link_libraries(c2-port-pause-test PRIVATE c2_unity_framework)
    add_test(NAME port-pause COMMAND c2-port-pause-test)

    add_executable(c2-save-compat-test
        tests/c2_save_compat_test.c
        src/platform/common/c2_port_save_compat.c
        src/platform/common/c2_port_save_registry.c)
    target_compile_features(c2-save-compat-test PRIVATE c_std_11)
    target_compile_definitions(c2-save-compat-test PRIVATE PORT_PLATFORM_LINUX=1)
    target_include_directories(c2-save-compat-test PRIVATE
        include
        src/platform/common)
    if(CMAKE_C_COMPILER_ID MATCHES "Clang|GNU")
        target_compile_options(c2-save-compat-test PRIVATE -fms-extensions)
    endif()
    add_test(NAME save-compat COMMAND c2-save-compat-test)
    if(C2_TEST_SAVE_FIXTURE)
        set_tests_properties(save-compat PROPERTIES
            ENVIRONMENT "C2_TEST_SAVE_FIXTURE=${C2_TEST_SAVE_FIXTURE}")
    endif()

    add_executable(c2-port-save-test
        tests/c2_port_save_test.c
        src/platform/common/c2_port_mouse.c
        src/platform/common/c2_port_save_compat.c
        src/platform/common/c2_port_save.c
        src/platform/common/c2_port_save_registry.c
        src/platform/sdl3/c2_sdl_audio.c
        src/platform/sdl3/c2_sdl_host.c)
    target_compile_features(c2-port-save-test PRIVATE c_std_11)
    target_compile_definitions(c2-port-save-test PRIVATE PORT_PLATFORM_LINUX=1)
    target_include_directories(c2-port-save-test PRIVATE
        include
        src/platform/common
        src/platform/sdl3)
    target_link_libraries(c2-port-save-test PRIVATE SDL3::SDL3)
    add_test(NAME port-save COMMAND c2-port-save-test)

    add_executable(c2-user-files-test
        tests/c2_user_files_test.c
        src/platform/common/c2_port_mouse.c
        src/platform/sdl3/c2_sdl_audio.c
        src/platform/sdl3/c2_sdl_host.c)
    target_compile_features(c2-user-files-test PRIVATE c_std_11)
    target_compile_definitions(c2-user-files-test PRIVATE PORT_PLATFORM_LINUX=1)
    target_include_directories(c2-user-files-test PRIVATE
        include
        src/platform/common
        src/platform/sdl3)
    target_link_libraries(c2-user-files-test PRIVATE SDL3::SDL3)
    add_test(NAME user-files COMMAND c2-user-files-test)

    add_executable(c2-import-test tests/c2_import_test.c)
    target_compile_features(c2-import-test PRIVATE c_std_11)
    target_include_directories(c2-import-test PRIVATE include)
    target_link_libraries(c2-import-test PRIVATE c2_import_core)
    add_test(NAME import-readers COMMAND c2-import-test)

    add_executable(c2-sdl-audio-test
        tests/c2_sdl_audio_test.c
        src/platform/sdl3/c2_sdl_audio.c)
    target_compile_features(c2-sdl-audio-test PRIVATE c_std_11)
    target_compile_definitions(c2-sdl-audio-test PRIVATE PORT_PLATFORM_LINUX=1)
    target_include_directories(c2-sdl-audio-test PRIVATE include)
    target_link_libraries(c2-sdl-audio-test PRIVATE SDL3::SDL3)
    add_test(NAME sdl-audio COMMAND c2-sdl-audio-test)

    add_executable(c2-smacker-test tests/c2_smacker_test.c)
    target_compile_features(c2-smacker-test PRIVATE c_std_11)
    target_link_libraries(c2-smacker-test PRIVATE c2_libsmacker)
    add_test(NAME smacker-decoder COMMAND c2-smacker-test)
    if(C2_TEST_DATA_DIR)
        set_tests_properties(smacker-decoder PROPERTIES
            ENVIRONMENT "C2_TEST_DATA_DIR=${C2_TEST_DATA_DIR}")
    endif()

    add_executable(c2-xmidi-test tests/c2_xmidi_test.c)
    target_compile_features(c2-xmidi-test PRIVATE c_std_11)
    target_link_libraries(c2-xmidi-test PRIVATE c2_xmidi c2_nuked_opl3)
    add_test(NAME xmidi-music COMMAND c2-xmidi-test)
    if(C2_TEST_DATA_DIR)
        set_tests_properties(xmidi-music PROPERTIES
            ENVIRONMENT "C2_TEST_DATA_DIR=${C2_TEST_DATA_DIR}")
    endif()

    add_executable(c2-asm-memory-test tests/c2_asm_memory_test.c)
    target_compile_features(c2-asm-memory-test PRIVATE c_std_11)
    target_link_libraries(c2-asm-memory-test PRIVATE c2_asm_portable)
    add_test(NAME asm-memory COMMAND c2-asm-memory-test)

    add_executable(c2-asm-internal-raster-test
        tests/c2_asm_internal_raster_test.c)
    target_compile_features(c2-asm-internal-raster-test PRIVATE c_std_11)
    target_link_libraries(c2-asm-internal-raster-test PRIVATE c2_asm_portable)
    add_test(NAME asm-internal-raster COMMAND c2-asm-internal-raster-test)

    add_executable(c2-asm-sprite-test tests/c2_asm_sprite_test.c)
    target_compile_features(c2-asm-sprite-test PRIVATE c_std_11)
    target_link_libraries(c2-asm-sprite-test PRIVATE c2_asm_portable)
    add_test(NAME asm-sprite COMMAND c2-asm-sprite-test)

    add_executable(c2-asm-diamond-ptr-test tests/c2_asm_diamond_ptr_test.c)
    target_compile_features(c2-asm-diamond-ptr-test PRIVATE c_std_11)
    target_link_libraries(c2-asm-diamond-ptr-test PRIVATE c2_asm_portable)
    add_test(NAME asm-diamond-ptr COMMAND c2-asm-diamond-ptr-test)

    add_executable(c2-asm-diamond-image-test
        tests/c2_asm_diamond_image_test.c)
    target_compile_features(c2-asm-diamond-image-test PRIVATE c_std_11)
    target_link_libraries(c2-asm-diamond-image-test PRIVATE c2_asm_portable)
    add_test(NAME asm-diamond-image COMMAND c2-asm-diamond-image-test)

    set(C2_UNITY_TEST_TARGETS
        c2-bugfixes-test
        c2-text-compat-test
        c2-port-timing-test
        c2-port-keymap-test
        c2-save-compat-test
        c2-port-save-test
        c2-user-files-test
        c2-import-test
        c2-sdl-audio-test
        c2-smacker-test
        c2-xmidi-test
        c2-asm-memory-test
        c2-asm-internal-raster-test
        c2-asm-sprite-test
        c2-asm-diamond-ptr-test
        c2-asm-diamond-image-test
    )
    foreach(test_target IN LISTS C2_UNITY_TEST_TARGETS)
        target_sources(${test_target} PRIVATE tests/c2_unity.c)
        target_link_libraries(${test_target} PRIVATE c2_unity_framework)
    endforeach()
endif()

set(C2_TEST_DATA_DIR "" CACHE PATH "Original Caesar II data directory used by smoke tests")
if(BUILD_TESTING AND C2_TEST_DATA_DIR AND
   (CMAKE_CONFIGURATION_TYPES OR CMAKE_BUILD_TYPE STREQUAL "Debug"))
    file(MAKE_DIRECTORY
        "${CMAKE_CURRENT_BINARY_DIR}/test-user-data/province-smoke"
        "${CMAKE_CURRENT_BINARY_DIR}/test-user-data/city-smoke"
        "${CMAKE_CURRENT_BINARY_DIR}/test-user-data/tutorial-smoke"
        "${CMAKE_CURRENT_BINARY_DIR}/test-user-data/save-load-smoke"
        "${CMAKE_CURRENT_BINARY_DIR}/test-user-data/music-buffer-smoke"
        "${CMAKE_CURRENT_BINARY_DIR}/test-user-data/campania-transition-smoke"
        "${CMAKE_CURRENT_BINARY_DIR}/test-user-data/province-build-smoke"
    )
    add_test(
        NAME startup-reaches-province-selection
        COMMAND caesar2 --smoke-test --asset-root "${C2_TEST_DATA_DIR}"
                --user-data-dir
                "${CMAKE_CURRENT_BINARY_DIR}/test-user-data/province-smoke"
    )
    set_tests_properties(startup-reaches-province-selection PROPERTIES
        CONFIGURATIONS Debug
        PASS_REGULAR_EXPRESSION "recovered province-selection smoke completed"
        TIMEOUT 50
    )
    add_test(
        NAME recovered-city-loop-smoke
        COMMAND caesar2 --city-smoke-test --asset-root "${C2_TEST_DATA_DIR}"
                --user-data-dir
                "${CMAKE_CURRENT_BINARY_DIR}/test-user-data/city-smoke"
    )
    set_tests_properties(recovered-city-loop-smoke PROPERTIES
        CONFIGURATIONS Debug
        PASS_REGULAR_EXPRESSION "recovered city-loop smoke completed"
        TIMEOUT 50
    )
    add_test(
        NAME recovered-campania-transition-smoke
        COMMAND caesar2 --campania-transition-smoke-test
                --asset-root "${C2_TEST_DATA_DIR}"
                --user-data-dir
                "${CMAKE_CURRENT_BINARY_DIR}/test-user-data/campania-transition-smoke"
    )
    set_tests_properties(recovered-campania-transition-smoke PROPERTIES
        CONFIGURATIONS Debug
        PASS_REGULAR_EXPRESSION
            "Campania speech transition smoke completed"
        TIMEOUT 50
    )
    add_test(
        NAME recovered-province-build-smoke
        COMMAND caesar2 --province-build-smoke-test
                --asset-root "${C2_TEST_DATA_DIR}"
                --user-data-dir
                "${CMAKE_CURRENT_BINARY_DIR}/test-user-data/province-build-smoke"
    )
    set_tests_properties(recovered-province-build-smoke PROPERTIES
        CONFIGURATIONS Debug
        PASS_REGULAR_EXPRESSION "province build smoke completed"
        TIMEOUT 60
    )
    add_test(
        NAME recovered-tutorial-flow-smoke
        COMMAND caesar2 --tutorial-smoke-test
                --asset-root "${C2_TEST_DATA_DIR}"
                --user-data-dir
                "${CMAKE_CURRENT_BINARY_DIR}/test-user-data/tutorial-smoke"
    )
    set_tests_properties(recovered-tutorial-flow-smoke PROPERTIES
        CONFIGURATIONS Debug
        PASS_REGULAR_EXPRESSION "recovered tutorial flow smoke completed"
        TIMEOUT 50
    )
    add_test(
        NAME recovered-save-load-smoke
        COMMAND caesar2 --save-load-smoke-test
                --asset-root "${C2_TEST_DATA_DIR}"
                --user-data-dir
                "${CMAKE_CURRENT_BINARY_DIR}/test-user-data/save-load-smoke"
    )
    set_tests_properties(recovered-save-load-smoke PROPERTIES
        CONFIGURATIONS Debug
        PASS_REGULAR_EXPRESSION
            "save/load disk and full-state verification restored"
        TIMEOUT 100
    )
    add_test(
        NAME recovered-music-buffer-smoke
        COMMAND caesar2 --music-buffer-smoke-test
                --asset-root "${C2_TEST_DATA_DIR}"
                --user-data-dir
                "${CMAKE_CURRENT_BINARY_DIR}/test-user-data/music-buffer-smoke"
    )
    set_tests_properties(recovered-music-buffer-smoke PROPERTIES
        CONFIGURATIONS Debug
        PASS_REGULAR_EXPRESSION "music buffer smoke completed"
        TIMEOUT 60
    )
endif()

# Copyrighted corpora are never fetched or enabled by default. Developers can
# supply any mix of installations, ZIPs, optimized packs, ISOs, and CUEs; each
# source runs through the same importer and recovered province-selection path.
if(BUILD_TESTING AND C2_TEST_GAME_DATA_SOURCES AND
   (CMAKE_CONFIGURATION_TYPES OR CMAKE_BUILD_TYPE STREQUAL "Debug"))
    set(corpus_index 0)
    foreach(corpus_source IN LISTS C2_TEST_GAME_DATA_SOURCES)
        math(EXPR corpus_index "${corpus_index} + 1")
        set(corpus_user_dir
            "${CMAKE_CURRENT_BINARY_DIR}/test-user-data/corpus-${corpus_index}")
        file(MAKE_DIRECTORY "${corpus_user_dir}")
        add_test(
            NAME game-data-corpus-${corpus_index}
            COMMAND caesar2 --smoke-test --game-data "${corpus_source}"
                    --user-data-dir "${corpus_user_dir}")
        set_tests_properties(game-data-corpus-${corpus_index} PROPERTIES
            CONFIGURATIONS Debug
            LABELS "game-data-corpus;requires-original-assets"
            PASS_REGULAR_EXPRESSION
                "recovered province-selection smoke completed"
            TIMEOUT 180)
    endforeach()
endif()
