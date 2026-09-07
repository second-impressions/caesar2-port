#ifndef C2_DEBUG_CRASH_H
#define C2_DEBUG_CRASH_H

/*
 * Fatal-error reports. The handler prints the build version, what faulted
 * and a symbolized backtrace to stderr, and, once a directory is known,
 * to crash-<UTC time of this run>.txt in it, so a player who started the
 * game from a desktop icon still has something to attach to an issue.
 */
int c2_debug_install_crash_handlers(void);
void c2_debug_set_crash_report_directory(const char *directory);
/* The report file this run would write (empty until a directory is set). */
const char *c2_debug_crash_report_path(void);

#define C2_CRASH_REPORT_PREFIX "crash-"
#define C2_CRASH_REPORT_SUFFIX ".txt"

#endif /* C2_DEBUG_CRASH_H */
