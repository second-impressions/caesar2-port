cmake_minimum_required(VERSION 3.25)

project(caesar2-port VERSION 0.1.0 LANGUAGES C)

find_package(SDL3 3.2 CONFIG REQUIRED)

add_executable(caesar2
    src/display.c
    src/platform/sdl3/c2_sdl_main.c
    src/platform/sdl3/c2_sdl_platform.c
)

target_compile_features(caesar2 PRIVATE c_std_11)
set_target_properties(caesar2 PROPERTIES
    C_STANDARD 11
    C_STANDARD_REQUIRED YES
    C_EXTENSIONS OFF
)

target_compile_definitions(caesar2 PRIVATE
    C2_TARGET_PORTABLE=1
)

target_include_directories(caesar2 PRIVATE
    include
    src/platform/sdl3
)

target_link_libraries(caesar2 PRIVATE SDL3::SDL3)

if(CMAKE_C_COMPILER_ID MATCHES "Clang|GNU")
    set_source_files_properties(src/display.c PROPERTIES
        COMPILE_OPTIONS -Wno-implicit-function-declaration
    )
    set_source_files_properties(
        src/platform/sdl3/c2_sdl_main.c
        src/platform/sdl3/c2_sdl_platform.c
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
        NAME title-screen-loads
        COMMAND caesar2 --headless --data-dir "${C2_TEST_DATA_DIR}"
    )
    set_tests_properties(title-screen-loads PROPERTIES
        PASS_REGULAR_EXPRESSION "title framebuffer fnv1a64=4955dda40cb075e6"
    )
endif()
