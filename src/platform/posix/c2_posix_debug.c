#define _POSIX_C_SOURCE 200809L

#include <execinfo.h>
#include <signal.h>
#include <stddef.h>
#include <stdint.h>
#include <unistd.h>

#include "c2_debug_crash.h"

#define PORT_DEBUG_BACKTRACE_DEPTH 64

static volatile sig_atomic_t c2_handling_fatal_signal;

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
    action.sa_sigaction = fatal_signal_handler;
    sigemptyset(&action.sa_mask);
    action.sa_flags = SA_SIGINFO | SA_RESETHAND;
    for (i = 0; i < sizeof(fatal_signals) / sizeof(fatal_signals[0]); i++) {
        if (sigaction(fatal_signals[i], &action, NULL) != 0) return 0;
    }
    return 1;
}
