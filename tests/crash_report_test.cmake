# Runs the game's deliberate fault (--crash-test, Debug builds) and checks
# that the report reached the user-data directory with what an issue needs.
#   cmake -DCAESAR2=<exe> -DUSER_DATA=<dir> [-DSOURCE_LINES=ON] -P crash_report_test.cmake
file(REMOVE_RECURSE "${USER_DATA}")
file(MAKE_DIRECTORY "${USER_DATA}")
execute_process(
    COMMAND "${CAESAR2}" --crash-test --headless --skip-launcher --user-data-dir "${USER_DATA}"
    RESULT_VARIABLE status
    OUTPUT_VARIABLE out
    ERROR_VARIABLE err)
if(status EQUAL 0)
    message(FATAL_ERROR "the crash test exited normally")
endif()
file(GLOB reports "${USER_DATA}/crash-*.txt")
list(LENGTH reports count)
if(NOT count EQUAL 1)
    message(FATAL_ERROR "expected one crash report, found ${count}: ${reports}\n${err}")
endif()
file(READ "${reports}" report)
foreach(needle "crashed:" "Please open an issue")
    if(NOT report MATCHES "${needle}")
        message(FATAL_ERROR "report lacks '${needle}':\n${report}")
    endif()
endforeach()
if(SOURCE_LINES AND NOT report MATCHES "c2_sdl_main\\.c:[0-9]+")
    message(FATAL_ERROR "report has no source line for the fault:\n${report}")
endif()
if(NOT err MATCHES "This report was also written to")
    message(FATAL_ERROR "stderr does not name the report:\n${err}")
endif()
message(STATUS "crash report: ${reports}")
