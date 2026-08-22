# Cross-compile the Windows target from a Linux host with MinGW-w64.
#
# This is the cheap Windows canary: it exercises the LLP64 data model
# (32-bit long, 64-bit pointer) and the Win32 headers without needing a
# Windows runner.  It is NOT a substitute for the MSVC build, which uses a
# different CRT and a different diagnostic set; both run in CI.
#
# Override the triple with -DC2_MINGW_TRIPLE=i686-w64-mingw32 for a 32-bit
# build.

set(CMAKE_SYSTEM_NAME Windows)
set(CMAKE_SYSTEM_PROCESSOR x86_64)

if(NOT C2_MINGW_TRIPLE)
    set(C2_MINGW_TRIPLE "x86_64-w64-mingw32")
endif()

set(CMAKE_C_COMPILER   "${C2_MINGW_TRIPLE}-gcc")
set(CMAKE_CXX_COMPILER "${C2_MINGW_TRIPLE}-g++")
set(CMAKE_RC_COMPILER  "${C2_MINGW_TRIPLE}-windres")

# Look for headers and libraries only in the target sysroot, but keep host
# programs (cmake helpers, generators) resolvable from the host PATH.
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM BEFORE)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)

# SDL3 comes from the pinned submodule on this target, so no SDL sysroot
# package needs to be discoverable.
set(C2_VENDORED_SDL ON CACHE BOOL "" FORCE)

# The Unity host test suite is not cross-executable; CI runs it on Linux.
set(BUILD_TESTING OFF CACHE BOOL "" FORCE)
