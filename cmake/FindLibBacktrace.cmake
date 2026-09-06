# FindLibBacktrace
# ----------------
# Locates libbacktrace, the DWARF symbolizer maintained with GCC
# (https://github.com/ianlancetaylor/libbacktrace), as installed by the
# distribution: header backtrace.h and library libbacktrace.
#
# Result variables:
#   LibBacktrace_FOUND, LibBacktrace_INCLUDE_DIRS, LibBacktrace_LIBRARIES
# Imported target:
#   LibBacktrace::LibBacktrace
# Hints:
#   LibBacktrace_ROOT, or the usual CMAKE_PREFIX_PATH.

find_path(LibBacktrace_INCLUDE_DIR
    NAMES backtrace.h
    DOC "libbacktrace include directory")
find_library(LibBacktrace_LIBRARY
    NAMES backtrace
    DOC "libbacktrace library")

include(FindPackageHandleStandardArgs)
find_package_handle_standard_args(LibBacktrace
    REQUIRED_VARS LibBacktrace_LIBRARY LibBacktrace_INCLUDE_DIR)

if(LibBacktrace_FOUND)
    set(LibBacktrace_INCLUDE_DIRS "${LibBacktrace_INCLUDE_DIR}")
    set(LibBacktrace_LIBRARIES "${LibBacktrace_LIBRARY}")
    if(NOT TARGET LibBacktrace::LibBacktrace)
        add_library(LibBacktrace::LibBacktrace UNKNOWN IMPORTED)
        set_target_properties(LibBacktrace::LibBacktrace PROPERTIES
            IMPORTED_LOCATION "${LibBacktrace_LIBRARY}"
            INTERFACE_INCLUDE_DIRECTORIES "${LibBacktrace_INCLUDE_DIR}")
    endif()
endif()
mark_as_advanced(LibBacktrace_INCLUDE_DIR LibBacktrace_LIBRARY)
