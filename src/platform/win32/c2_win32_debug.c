/*
 * Fatal-error reports on Windows: the unhandled-exception filter and the
 * CRT's abort() path both produce the same report as the POSIX handler,
 * symbolized through dbghelp from the caesar2.pdb shipped next to the
 * executable, plus a minidump for what a text trace cannot show. A player
 * who double-clicked the game has no console, so the report goes to a file
 * in the user-data directory and a message box says where.
 */
#include <windows.h>
#include <dbghelp.h>

#include <signal.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "c2_debug_crash.h"
#include "c2_version.h"

#define C2_ISSUE_URL "https://github.com/second-impressions/caesar2-port/issues"
#define PORT_DEBUG_BACKTRACE_DEPTH 64
#define PORT_DEBUG_PATH_CAPACITY 1024

static char c2_report_path[PORT_DEBUG_PATH_CAPACITY];
static char c2_dump_path[PORT_DEBUG_PATH_CAPACITY];
static HANDLE c2_report_file = INVALID_HANDLE_VALUE;
static volatile LONG c2_handling;
static int c2_symbols_ready;

static void write_handle(HANDLE handle, const char *text, size_t length)
{
    DWORD written;

    if (handle == INVALID_HANDLE_VALUE || handle == NULL) return;
    while (length != 0) {
        if (!WriteFile(handle, text, (DWORD)length, &written, NULL) || written == 0) return;
        text += written;
        length -= written;
    }
}

static void write_all(const char *text)
{
    size_t length = strlen(text);

    write_handle(GetStdHandle(STD_ERROR_HANDLE), text, length);
    write_handle(c2_report_file, text, length);
}

static void write_format(const char *format, ...)
{
    char line[1024];
    va_list args;
    int length;

    va_start(args, format);
    length = vsnprintf(line, sizeof(line), format, args);
    va_end(args);
    if (length < 0) return;
    if ((size_t)length >= sizeof(line)) line[sizeof(line) - 1] = '\0';
    write_all(line);
}

/* PDB paths are absolute with backslashes; show them relative to the
 * repository, as the POSIX report does. */
static const char *relative_source(const char *filename)
{
    const char *root = PORT_SOURCE_ROOT;
    size_t i;

    for (i = 0; root[i] != '\0'; i++) {
        char a = filename[i];
        char b = root[i];
        if (a == '\\') a = '/';
        if (b == '\\') b = '/';
        if (a >= 'A' && a <= 'Z') a = (char)(a - 'A' + 'a');
        if (b >= 'A' && b <= 'Z') b = (char)(b - 'A' + 'a');
        if (a != b) return filename;
    }
    return filename + i;
}

static void print_frame(int index, DWORD64 address)
{
    union {
        SYMBOL_INFO info;
        char bytes[sizeof(SYMBOL_INFO) + 256];
    } symbol;
    IMAGEHLP_LINE64 line;
    DWORD64 displacement = 0;
    DWORD line_displacement = 0;

    write_format("#%d 0x%016llx ", index, (unsigned long long)address);
    memset(&symbol, 0, sizeof(symbol));
    symbol.info.SizeOfStruct = sizeof(SYMBOL_INFO);
    symbol.info.MaxNameLen = 255;
    if (c2_symbols_ready && SymFromAddr(GetCurrentProcess(), address, &displacement, &symbol.info)) {
        write_format("%s+0x%llx", symbol.info.Name, (unsigned long long)displacement);
    } else {
        write_all("??");
    }
    memset(&line, 0, sizeof(line));
    line.SizeOfStruct = sizeof(line);
    if (c2_symbols_ready && SymGetLineFromAddr64(GetCurrentProcess(), address, &line_displacement, &line)) {
        write_format(" at %s:%lu", relative_source(line.FileName), (unsigned long)line.LineNumber);
    }
    write_all("\n");
}

static void print_backtrace(CONTEXT *context)
{
    STACKFRAME64 frame;
    DWORD machine;
    int index = 0;

    memset(&frame, 0, sizeof(frame));
#if defined(_M_X64)
    machine = IMAGE_FILE_MACHINE_AMD64;
    frame.AddrPC.Offset = context->Rip;
    frame.AddrFrame.Offset = context->Rbp;
    frame.AddrStack.Offset = context->Rsp;
#elif defined(_M_ARM64)
    machine = IMAGE_FILE_MACHINE_ARM64;
    frame.AddrPC.Offset = context->Pc;
    frame.AddrFrame.Offset = context->Fp;
    frame.AddrStack.Offset = context->Sp;
#else
    machine = IMAGE_FILE_MACHINE_I386;
    frame.AddrPC.Offset = context->Eip;
    frame.AddrFrame.Offset = context->Ebp;
    frame.AddrStack.Offset = context->Esp;
#endif
    frame.AddrPC.Mode = AddrModeFlat;
    frame.AddrFrame.Mode = AddrModeFlat;
    frame.AddrStack.Mode = AddrModeFlat;
    while (index < PORT_DEBUG_BACKTRACE_DEPTH &&
           StackWalk64(machine, GetCurrentProcess(), GetCurrentThread(), &frame, context,
                       NULL, SymFunctionTableAccess64, SymGetModuleBase64, NULL)) {
        if (frame.AddrPC.Offset == 0) break;
        /* Past the faulting frame these are return addresses; the call is
         * one byte back, which is what puts them on the right line. */
        print_frame(index, index == 0 ? frame.AddrPC.Offset : frame.AddrPC.Offset - 1);
        index++;
    }
}

static const char *exception_name(DWORD code)
{
    switch (code) {
    case EXCEPTION_ACCESS_VIOLATION: return "access violation";
    case EXCEPTION_ARRAY_BOUNDS_EXCEEDED: return "array bounds exceeded";
    case EXCEPTION_ILLEGAL_INSTRUCTION: return "illegal instruction";
    case EXCEPTION_INT_DIVIDE_BY_ZERO: return "integer division by zero";
    case EXCEPTION_STACK_OVERFLOW: return "stack overflow";
    case EXCEPTION_IN_PAGE_ERROR: return "in-page error";
    case EXCEPTION_PRIV_INSTRUCTION: return "privileged instruction";
    default: return "exception";
    }
}

static void write_minidump(EXCEPTION_POINTERS *pointers)
{
    HANDLE file;
    MINIDUMP_EXCEPTION_INFORMATION info;
    BOOL ok;

    if (c2_dump_path[0] == '\0') return;
    file = CreateFileA(c2_dump_path, GENERIC_WRITE, FILE_SHARE_READ, NULL,
                       CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
    if (file == INVALID_HANDLE_VALUE) return;
    info.ThreadId = GetCurrentThreadId();
    info.ExceptionPointers = pointers;
    info.ClientPointers = FALSE;
    ok = MiniDumpWriteDump(GetCurrentProcess(), GetCurrentProcessId(), file,
                           (MINIDUMP_TYPE)(MiniDumpWithDataSegs | MiniDumpWithIndirectlyReferencedMemory),
                           pointers ? &info : NULL, NULL, NULL);
    CloseHandle(file);
    if (ok) write_format("A minidump was written to %s\n", c2_dump_path);
    else DeleteFileA(c2_dump_path);
}

static void report(const char *what, EXCEPTION_POINTERS *pointers, CONTEXT *context)
{
    char message[PORT_DEBUG_PATH_CAPACITY + 256];

    if (c2_report_path[0] != '\0') {
        c2_report_file = CreateFileA(c2_report_path, GENERIC_WRITE, FILE_SHARE_READ, NULL,
                                     CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
    }
    write_format("\nCaesar II " C2_VERSION_STRING " crashed: %s", what);
    if (pointers != NULL && pointers->ExceptionRecord != NULL) {
        const EXCEPTION_RECORD *record = pointers->ExceptionRecord;
        write_format(" (0x%08lx) at 0x%p", (unsigned long)record->ExceptionCode,
                     record->ExceptionAddress);
        if (record->ExceptionCode == EXCEPTION_ACCESS_VIOLATION &&
            record->NumberParameters >= 2) {
            write_format(", %s address 0x%p",
                         record->ExceptionInformation[0] == 0 ? "reading" :
                         record->ExceptionInformation[0] == 8 ? "executing" : "writing",
                         (void *)(ULONG_PTR)record->ExceptionInformation[1]);
        }
    }
    write_all("\n");
    if (c2_symbols_ready) {
        print_backtrace(context);
    } else {
        write_all("(symbols unavailable: caesar2.pdb is not next to caesar2.exe)\n");
    }
    write_minidump(pointers);
    write_all("\nThis is a bug in the port. Please open an issue at\n  " C2_ISSUE_URL
              "\nand paste everything above, with what you were doing in the game.\n");
    if (c2_report_file != INVALID_HANDLE_VALUE) {
        CloseHandle(c2_report_file);
        c2_report_file = INVALID_HANDLE_VALUE;
        write_format("This report was also written to %s\n", c2_report_path);
        snprintf(message, sizeof(message),
                 "Caesar II crashed.\n\nA report was written to\n%s\n\n"
                 "This is a bug in the port. Please open an issue at\n" C2_ISSUE_URL
                 "\nand attach the report, with what you were doing in the game.",
                 c2_report_path);
    } else {
        snprintf(message, sizeof(message),
                 "Caesar II crashed.\n\nThis is a bug in the port. Please open an issue at\n"
                 C2_ISSUE_URL);
    }
    MessageBoxA(NULL, message, "Caesar II", MB_OK | MB_ICONERROR | MB_SETFOREGROUND);
}

static LONG WINAPI unhandled_exception_filter(EXCEPTION_POINTERS *pointers)
{
    CONTEXT context;

    if (InterlockedCompareExchange(&c2_handling, 1, 0) != 0) return EXCEPTION_EXECUTE_HANDLER;
    context = *pointers->ContextRecord;   /* StackWalk64 modifies it */
    report(exception_name(pointers->ExceptionRecord->ExceptionCode), pointers, &context);
    return EXCEPTION_EXECUTE_HANDLER;
}

/* abort() (assertion failures, the CRT's own checks) raises SIGABRT
 * rather than an exception; capture this thread's context ourselves. */
static void abort_handler(int signal_number)
{
    CONTEXT context;

    (void)signal_number;
    if (InterlockedCompareExchange(&c2_handling, 1, 0) != 0) _exit(3);
    RtlCaptureContext(&context);
    report("abort", NULL, &context);
    _exit(3);
}

int c2_debug_install_crash_handlers(void)
{
    SymSetOptions(SYMOPT_LOAD_LINES | SYMOPT_UNDNAME | SYMOPT_DEFERRED_LOADS | SYMOPT_FAIL_CRITICAL_ERRORS);
    c2_symbols_ready = SymInitialize(GetCurrentProcess(), NULL, TRUE) ? 1 : 0;
    /* No Windows Error Reporting dialog in front of ours, no abort() box. */
    SetErrorMode(SEM_FAILCRITICALERRORS | SEM_NOGPFAULTERRORBOX);
    _set_abort_behavior(0, _WRITE_ABORT_MSG | _CALL_REPORTFAULT);
    signal(SIGABRT, abort_handler);
    SetUnhandledExceptionFilter(unhandled_exception_filter);
    return 1;
}

void c2_debug_set_crash_report_directory(const char *directory)
{
    SYSTEMTIME now;
    int length;

    c2_report_path[0] = '\0';
    c2_dump_path[0] = '\0';
    if (directory == NULL || directory[0] == '\0') return;
    CreateDirectoryA(directory, NULL);
    GetSystemTime(&now);
    length = snprintf(c2_report_path, sizeof(c2_report_path),
                      "%s\\" C2_CRASH_REPORT_PREFIX "%04u%02u%02u-%02u%02u%02u" C2_CRASH_REPORT_SUFFIX,
                      directory, now.wYear, now.wMonth, now.wDay, now.wHour, now.wMinute, now.wSecond);
    if (length < 0 || (size_t)length >= sizeof(c2_report_path)) { c2_report_path[0] = '\0'; return; }
    length = snprintf(c2_dump_path, sizeof(c2_dump_path),
                      "%s\\" C2_CRASH_REPORT_PREFIX "%04u%02u%02u-%02u%02u%02u.dmp",
                      directory, now.wYear, now.wMonth, now.wDay, now.wHour, now.wMinute, now.wSecond);
    if (length < 0 || (size_t)length >= sizeof(c2_dump_path)) c2_dump_path[0] = '\0';
}

const char *c2_debug_crash_report_path(void)
{
    return c2_report_path;
}
