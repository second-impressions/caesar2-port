cmake_minimum_required(VERSION 3.25)

project(caesar2-port VERSION 0.1.0 LANGUAGES C)

find_package(SDL3 3.2 CONFIG REQUIRED)

option(C2_FIX_MEDIUM_RIGHT_HAT_OFFSET
    "Correct the misplaced pixel pair in the medium right diamond hat" ON)
option(C2_FIX_LARGE_RIGHT_HALFROOF_SEAM_PAIR
    "Suppress the stray seam pair in the large right half-roof" ON)
option(C2_FIX_GFX_BUFFER_DOUBLE_FREE
    "Clear released graphics pointers to prevent repeated frees" ON)
option(C2_FIX_HELP_SMART_PUNCTUATION
    "Repair Windows smart punctuation embedded in help text" ON)
option(C2_ENABLE_TEXT_ASSET_COMPAT
    "Adapt versioned engine UI to the structure of the loaded text asset" ON)
option(C2_ENABLE_POSIX_DEBUG_CRASH_HANDLER
    "Install native fatal-signal diagnostics in POSIX Debug builds" ON)

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
if(C2_FIX_MEDIUM_RIGHT_HAT_OFFSET)
    target_compile_definitions(c2_asm_portable PUBLIC
        C2_FIX_MEDIUM_RIGHT_HAT_OFFSET=1)
else()
    target_compile_definitions(c2_asm_portable PUBLIC
        C2_FIX_MEDIUM_RIGHT_HAT_OFFSET=0)
endif()
if(C2_FIX_GFX_BUFFER_DOUBLE_FREE)
    add_compile_definitions(C2_FIX_GFX_BUFFER_DOUBLE_FREE=1)
else()
    add_compile_definitions(C2_FIX_GFX_BUFFER_DOUBLE_FREE=0)
endif()
if(C2_FIX_HELP_SMART_PUNCTUATION)
    add_compile_definitions(C2_FIX_HELP_SMART_PUNCTUATION=1)
else()
    add_compile_definitions(C2_FIX_HELP_SMART_PUNCTUATION=0)
endif()
if(C2_ENABLE_TEXT_ASSET_COMPAT)
    add_compile_definitions(C2_FEAT_TEXT_ASSET_COMPAT=1)
else()
    add_compile_definitions(C2_FEAT_TEXT_ASSET_COMPAT=0)
endif()
if(C2_FIX_LARGE_RIGHT_HALFROOF_SEAM_PAIR)
    target_compile_definitions(c2_asm_portable PUBLIC
        C2_FIX_LARGE_RIGHT_HALFROOF_SEAM_PAIR=1)
else()
    target_compile_definitions(c2_asm_portable PUBLIC
        C2_FIX_LARGE_RIGHT_HALFROOF_SEAM_PAIR=0)
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
    src/c2_bugfixes.c
    src/c2_text_compat.c
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
    src/pump.c
    src/refresh.c
    src/rot_data.c
    src/screens.c
    src/speech.c
    src/titles.c
    src/web.c
    src/platform/common/c2_port_app.c
    src/platform/common/c2_port_audio.c
    src/platform/common/c2_port_compat.c
    src/platform/common/c2_port_input.c
    src/platform/common/c2_port_timing.c
    src/platform/common/c2_port_video.c
    src/platform/sdl3/c2_sdl_main.c
    src/platform/sdl3/c2_sdl_host.c
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

target_compile_definitions(caesar2 PRIVATE
    PLATFORM_PORTABLE=1
    $<$<CONFIG:Debug>:C2_DEBUG_BUILD=1>
)

if(UNIX AND C2_ENABLE_POSIX_DEBUG_CRASH_HANDLER)
    target_sources(caesar2 PRIVATE
        $<$<CONFIG:Debug>:src/platform/posix/c2_posix_debug.c>
    )
    target_compile_definitions(caesar2 PRIVATE
        $<$<CONFIG:Debug>:C2_ENABLE_POSIX_CRASH_HANDLER=1>
    )
endif()

target_include_directories(caesar2 PRIVATE
    include
    src/platform/common
    src/platform/sdl3
)

target_link_libraries(caesar2 PRIVATE c2_asm_portable SDL3::SDL3)

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
        src/platform/sdl3/c2_sdl_host.c
        src/platform/sdl3/c2_sdl_smoke.c
        src/platform/common/c2_port_app.c
        src/platform/common/c2_port_audio.c
        src/platform/common/c2_port_compat.c
        src/platform/common/c2_port_input.c
        src/platform/common/c2_port_observation.c
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
endif()

include(CTest)

if(BUILD_TESTING)
    add_executable(c2-bugfixes-test
        tests/c2_bugfixes_test.c
        src/c2_bugfixes.c)
    target_compile_features(c2-bugfixes-test PRIVATE c_std_11)
    target_include_directories(c2-bugfixes-test PRIVATE include)
    add_test(NAME bugfixes COMMAND c2-bugfixes-test)

    add_executable(c2-text-compat-test
        tests/c2_text_compat_test.c
        src/c2_text_compat.c)
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
endif()

set(C2_TEST_DATA_DIR "" CACHE PATH "Original Caesar II data directory used by smoke tests")
if(BUILD_TESTING AND C2_TEST_DATA_DIR AND
   (CMAKE_CONFIGURATION_TYPES OR CMAKE_BUILD_TYPE STREQUAL "Debug"))
    file(MAKE_DIRECTORY
        "${CMAKE_CURRENT_BINARY_DIR}/test-user-data/province-smoke"
        "${CMAKE_CURRENT_BINARY_DIR}/test-user-data/city-smoke"
    )
    add_test(
        NAME startup-reaches-province-selection
        COMMAND caesar2 --smoke-test --data-dir "${C2_TEST_DATA_DIR}"
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
        COMMAND caesar2 --city-smoke-test --data-dir "${C2_TEST_DATA_DIR}"
                --user-data-dir
                "${CMAKE_CURRENT_BINARY_DIR}/test-user-data/city-smoke"
    )
    set_tests_properties(recovered-city-loop-smoke PROPERTIES
        CONFIGURATIONS Debug
        PASS_REGULAR_EXPRESSION "recovered city-loop smoke completed"
        TIMEOUT 50
    )
endif()
