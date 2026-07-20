cmake_minimum_required(VERSION 3.25)

project(caesar2-port VERSION 0.1.0 LANGUAGES C)

find_package(SDL3 3.2 CONFIG REQUIRED)

add_library(c2_asm_portable STATIC
    src/portable/asm/c2_asm_stubs.c
)
target_compile_features(c2_asm_portable PRIVATE c_std_11)
target_include_directories(c2_asm_portable PUBLIC include)
if(CMAKE_C_COMPILER_ID MATCHES "Clang|GNU")
    target_compile_options(c2_asm_portable PRIVATE
        -Wall
        -Wextra
        -Wpedantic
        -Wno-unused-parameter
    )
endif()

add_executable(caesar2
    src/controls.c
    src/contrdat.c
    src/data.c
    src/display.c
    src/screens.c
    src/port/c2_port_app.c
    src/port/c2_port_compat.c
    src/port/c2_port_ui.c
    src/platform/sdl3/c2_sdl_main.c
    src/platform/sdl3/c2_sdl_host.c
)

target_compile_features(caesar2 PRIVATE c_std_11)
set_target_properties(caesar2 PROPERTIES
    C_STANDARD 11
    C_STANDARD_REQUIRED YES
    C_EXTENSIONS OFF
)

target_compile_definitions(caesar2 PRIVATE
    PLATFORM_PORTABLE=1
)

target_include_directories(caesar2 PRIVATE
    include
    src/port
    src/platform/sdl3
)

target_link_libraries(caesar2 PRIVATE SDL3::SDL3)

if(CMAKE_C_COMPILER_ID MATCHES "Clang|GNU")
    set_source_files_properties(src/display.c PROPERTIES
        COMPILE_OPTIONS -Wno-implicit-function-declaration
    )
    set_source_files_properties(
        src/controls.c
        src/contrdat.c
        src/data.c
        src/screens.c
        PROPERTIES COMPILE_OPTIONS -Wno-implicit-function-declaration
    )
    set_source_files_properties(
        src/platform/sdl3/c2_sdl_main.c
        src/platform/sdl3/c2_sdl_host.c
        src/port/c2_port_app.c
        src/port/c2_port_compat.c
        src/port/c2_port_ui.c
        PROPERTIES COMPILE_OPTIONS -Wpedantic
    )
    target_compile_options(caesar2 PRIVATE
        -Wall
        -Wextra
        -fms-extensions
        -ffunction-sections
        -fdata-sections
        $<$<C_COMPILER_ID:Clang>:-Wno-microsoft-anon-tag>
    )
    target_link_options(caesar2 PRIVATE -Wl,--gc-sections)
endif()

include(CTest)

set(C2_TEST_DATA_DIR "" CACHE PATH "Original Caesar II data directory used by smoke tests")
if(BUILD_TESTING AND C2_TEST_DATA_DIR)
    add_test(
        NAME startup-reaches-game-options
        COMMAND caesar2 --headless --data-dir "${C2_TEST_DATA_DIR}"
    )
    set_tests_properties(startup-reaches-game-options PROPERTIES
        PASS_REGULAR_EXPRESSION "game settings framebuffer fnv1a64=b9da7d0a15d22865"
    )
endif()
