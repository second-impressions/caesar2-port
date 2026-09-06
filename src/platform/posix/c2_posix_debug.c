#define _GNU_SOURCE

#include <dlfcn.h>
#include <execinfo.h>
#include <signal.h>
#include <stddef.h>
#include <stdint.h>
#include <sys/wait.h>
#include <unistd.h>

#include "c2_debug_crash.h"

#define PORT_DEBUG_BACKTRACE_DEPTH 64
#define PORT_DEBUG_EXE_PATH_CAPACITY 1024

static volatile sig_atomic_t c2_handling_fatal_signal;
/* Resolved at install time: readlink is signal-safe but a fault may have
 * left the process unable to afford anything more than the write below. */
static char c2_executable_path[PORT_DEBUG_EXE_PATH_CAPACITY];
static const void *c2_executable_base;

static void write_all(const char *text, size_t length)
{
    while (length != 0) {
        ssize_t written;

        written = write(STDERR_FILENO, text, length);
        if (written <= 0) return;
        text += written;
        length -= (size_t)written;
    }
}

static void write_literal(const char *text, size_t length)
{
    write_all(text, length);
}

static void write_decimal(unsigned int value)
{
    char digits[16];
    size_t length;

    length = 0;
    do {
        digits[length++] = (char)('0' + value % 10);
        value /= 10;
    } while (value != 0);
    while (length != 0) {
        length--;
        write_all(&digits[length], 1);
    }
}

static void write_pointer(const void *pointer)
{
    static const char hex[] = "0123456789abcdef";
    uintptr_t value;
    char digits[sizeof(uintptr_t) * 2];
    size_t length;

    value = (uintptr_t)pointer;
    length = 0;
    do {
        digits[length++] = hex[value & 15];
        value >>= 4;
    } while (value != 0);
    write_literal("0x", 2);
    while (length != 0) {
        length--;
        write_all(&digits[length], 1);
    }
}

static void format_hex(uintptr_t value, char *out)
{
    static const char hex[] = "0123456789abcdef";
    char digits[sizeof(uintptr_t) * 2];
    size_t length;

    length = 0;
    do {
        digits[length++] = hex[value & 15];
        value >>= 4;
    } while (value != 0);
    *out++ = '0';
    *out++ = 'x';
    while (length != 0) *out++ = digits[--length];
    *out = '\0';
}

/*
 * backtrace_symbols_fd() names only dynamic symbols, and the engine exports
 * none, so it prints bare +0x offsets for every game frame. Every build
 * carries DWARF, so hand those offsets to addr2line when it is installed and
 * print the command otherwise, ready to paste. Frames past the faulting one
 * are return addresses; addr2line wants the call instruction, one byte back.
 */
static void symbolize_frames(void *const *frames, int frame_count, int first)
{
    static char offsets[PORT_DEBUG_BACKTRACE_DEPTH][2 + sizeof(uintptr_t) * 2 + 1];
    static char *argv[PORT_DEBUG_BACKTRACE_DEPTH + 8];
    size_t argc;
    int i;
    int status;
    pid_t child;

    if (c2_executable_base == NULL || c2_executable_path[0] == '\0') return;
    argc = 0;
    argv[argc++] = "addr2line";
    argv[argc++] = "-e";
    argv[argc++] = c2_executable_path;
    argv[argc++] = "-f";
    argv[argc++] = "-C";
    argv[argc++] = "-i";
    argv[argc++] = "-p";
    for (i = first; i < frame_count; i++) {
        Dl_info info;
        uintptr_t address;

        if (dladdr(frames[i], &info) == 0 || info.dli_fbase != c2_executable_base) continue;
        address = (uintptr_t)frames[i] - (uintptr_t)c2_executable_base;
        if (i > first) address--;
        format_hex(address, offsets[i]);
        argv[argc++] = offsets[i];
    }
    argv[argc] = NULL;
    if (argc == 7) return;

    write_literal("\nresolve with:", 14);
    for (i = 0; argv[i] != NULL; i++) {
        size_t length = 0;
        while (argv[i][length] != '\0') length++;
        write_literal(" ", 1);
        write_all(argv[i], length);
    }
    write_literal("\n\n", 2);

    child = fork();
    if (child == 0) {
        execvp(argv[0], argv);
        _exit(127);
    }
    if (child < 0) return;
    while (waitpid(child, &status, 0) < 0) {}
    if (WIFEXITED(status) && WEXITSTATUS(status) == 127) {
        write_literal("(addr2line is not installed; run the command above where it is)\n", 65);
    }
}

static const char *signal_name(int signal_number, size_t *length)
{
    switch (signal_number) {
    case SIGSEGV: *length = 7; return "SIGSEGV";
    case SIGABRT: *length = 7; return "SIGABRT";
    case SIGBUS:  *length = 6; return "SIGBUS";
    case SIGILL:  *length = 6; return "SIGILL";
    case SIGFPE:  *length = 6; return "SIGFPE";
    default:      *length = 6; return "signal";
    }
}

static void fatal_signal_handler(int signal_number, siginfo_t *info,
                                 void *context)
{
    struct sigaction default_action;
    sigset_t unblock_set;
    void *frames[PORT_DEBUG_BACKTRACE_DEPTH];
    const char *name;
    size_t name_length;
    int frame_count;

    (void)context;
    if (c2_handling_fatal_signal) _exit(128 + signal_number);
    c2_handling_fatal_signal = 1;

    name = signal_name(signal_number, &name_length);
    write_literal("\ncaesar2 debug: fatal ", 22);
    write_all(name, name_length);
    write_literal(" (", 2);
    write_decimal((unsigned int)signal_number);
    if (info != NULL && info->si_code > 0) {
        write_literal(") at ", 5);
        write_pointer(info->si_addr);
    } else {
        write_literal(") raised externally", 19);
    }
    write_literal("\n", 1);

    frame_count = backtrace(frames, PORT_DEBUG_BACKTRACE_DEPTH);
    backtrace_symbols_fd(frames, frame_count, STDERR_FILENO);
    /* Frame 0 is this handler and frame 1 the kernel's signal trampoline;
     * frame 2 is the faulting instruction itself, not a return address. */
    symbolize_frames(frames, frame_count, frame_count > 2 ? 2 : 0);

    default_action.sa_handler = SIG_DFL;
    sigemptyset(&default_action.sa_mask);
    default_action.sa_flags = 0;
    sigaction(signal_number, &default_action, NULL);
    sigemptyset(&unblock_set);
    sigaddset(&unblock_set, signal_number);
    sigprocmask(SIG_UNBLOCK, &unblock_set, NULL);
    kill(getpid(), signal_number);
    _exit(128 + signal_number);
}

int c2_debug_install_crash_handlers(void)
{
    static const int fatal_signals[] = {
        SIGSEGV, SIGABRT, SIGBUS, SIGILL, SIGFPE
    };
    struct sigaction action;
    void *warmup_frame;
    size_t i;

    /* Load the unwinder before a fault, where lazy loading could be unsafe. */
    (void)backtrace(&warmup_frame, 1);
    {
        Dl_info info;
        ssize_t length;

        if (dladdr((const void *)&c2_debug_install_crash_handlers, &info) != 0) {
            c2_executable_base = info.dli_fbase;
        }
        length = readlink("/proc/self/exe", c2_executable_path,
                          sizeof(c2_executable_path) - 1);
        if (length > 0) c2_executable_path[length] = '\0';
        else c2_executable_path[0] = '\0';
    }
    action.sa_sigaction = fatal_signal_handler;
    sigemptyset(&action.sa_mask);
    action.sa_flags = SA_SIGINFO | SA_RESETHAND;
    for (i = 0; i < sizeof(fatal_signals) / sizeof(fatal_signals[0]); i++) {
        if (sigaction(fatal_signals[i], &action, NULL) != 0) return 0;
    }
    return 1;
}
