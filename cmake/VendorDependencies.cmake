# Portable Linux binary: SDL3 and libbacktrace from pinned sources, linked
# statically together with zlib. Everything SDL3 talks to at runtime (X11,
# Wayland, ALSA, PulseAudio, PipeWire, libdecor ...) it loads with dlopen,
# so their development headers must be present when SDL3 is configured
# but nothing but the C library is needed to run the result. Build on an
# old glibc (the release workflow uses Ubuntu 22.04) and it runs anywhere
# newer.
include(FetchContent)
include(ExternalProject)

set(C2_SDL3_VERSION 3.4.16)
set(C2_SDL3_SHA256 7322236cd12090c3eb40b9728be4d49c76f66ad17d04369584d4ecad5cf77c68)
set(C2_LIBBACKTRACE_COMMIT 0b9b49cf4a2c9229fc052d6716e1528b2f23e91a)

set(SDL_SHARED OFF CACHE BOOL "" FORCE)
set(SDL_STATIC ON CACHE BOOL "" FORCE)
set(SDL_TEST_LIBRARY OFF CACHE BOOL "" FORCE)
set(SDL_TESTS OFF CACHE BOOL "" FORCE)
set(SDL_EXAMPLES OFF CACHE BOOL "" FORCE)
set(SDL_INSTALL OFF CACHE BOOL "" FORCE)
FetchContent_Declare(SDL3
    URL "https://github.com/libsdl-org/SDL/releases/download/release-${C2_SDL3_VERSION}/SDL3-${C2_SDL3_VERSION}.tar.gz"
    URL_HASH "SHA256=${C2_SDL3_SHA256}")
FetchContent_MakeAvailable(SDL3)
if(NOT TARGET SDL3::SDL3)
    message(FATAL_ERROR "vendored SDL3 did not provide SDL3::SDL3")
endif()

set(ZLIB_USE_STATIC_LIBS ON)

# libbacktrace is autotools; build it once into the build tree.
set(C2_LIBBACKTRACE_PREFIX "${CMAKE_CURRENT_BINARY_DIR}/libbacktrace")
ExternalProject_Add(libbacktrace_vendored
    GIT_REPOSITORY https://github.com/ianlancetaylor/libbacktrace.git
    GIT_TAG "${C2_LIBBACKTRACE_COMMIT}"
    GIT_SHALLOW OFF
    UPDATE_DISCONNECTED ON
    CONFIGURE_COMMAND <SOURCE_DIR>/configure --prefix=<INSTALL_DIR>
        --disable-shared --enable-static --with-pic
        "CC=${CMAKE_C_COMPILER}" "CFLAGS=-O2 -g"
    BUILD_COMMAND make -j
    INSTALL_COMMAND make install
    INSTALL_DIR "${C2_LIBBACKTRACE_PREFIX}"
    BUILD_BYPRODUCTS "${C2_LIBBACKTRACE_PREFIX}/lib/libbacktrace.a")
file(MAKE_DIRECTORY "${C2_LIBBACKTRACE_PREFIX}/include")
add_library(LibBacktrace::LibBacktrace STATIC IMPORTED)
set_target_properties(LibBacktrace::LibBacktrace PROPERTIES
    IMPORTED_LOCATION "${C2_LIBBACKTRACE_PREFIX}/lib/libbacktrace.a"
    INTERFACE_INCLUDE_DIRECTORIES "${C2_LIBBACKTRACE_PREFIX}/include")
set(LibBacktrace_FOUND TRUE)
set(LibBacktrace_LIBRARIES "${C2_LIBBACKTRACE_PREFIX}/lib/libbacktrace.a")
