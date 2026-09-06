/*
 * Runtime defaults for sanitizer builds (compiled only when CMake sees a
 * -fsanitize=address flag). A developer binary is copied to other machines;
 * a report from there must still come back with function names and lines.
 * The sanitizer runtime only looks for llvm-symbolizer on its own, so when
 * that is absent point it at binutils' addr2line, which it also understands.
 *
 * __asan_default_options() runs from the runtime's preinit hook, before
 * libc has set `environ` and before the interceptors work, so this file is
 * compiled uninstrumented, uses raw syscalls only, and reads the
 * environment from /proc/self/environ as the runtime itself does.
 */
#define _GNU_SOURCE

#include <fcntl.h>
#include <stddef.h>
#include <sys/syscall.h>
#include <unistd.h>

#define C2_SANITIZER_OPTIONS_CAPACITY 4096
#define C2_SANITIZER_ENVIRON_CAPACITY 65536

static char c2_sanitizer_options[C2_SANITIZER_OPTIONS_CAPACITY];
static char c2_sanitizer_environ[C2_SANITIZER_ENVIRON_CAPACITY];
static long c2_sanitizer_environ_size = -1;

static void load_environment(void)
{
    long fd;
    long total = 0;
    if (c2_sanitizer_environ_size >= 0) return;
    c2_sanitizer_environ_size = 0;
    fd = syscall(SYS_openat, AT_FDCWD, "/proc/self/environ", O_RDONLY);
    if (fd < 0) return;
    for (;;) {
        long got = syscall(SYS_read, fd, c2_sanitizer_environ + total,
                           C2_SANITIZER_ENVIRON_CAPACITY - 1 - total);
        if (got <= 0) break;
        total += got;
        if (total >= C2_SANITIZER_ENVIRON_CAPACITY - 1) break;
    }
    syscall(SYS_close, fd);
    c2_sanitizer_environ[total] = '\0';
    c2_sanitizer_environ_size = total;
}

static const char *environment_value(const char *name)
{
    const char *e;
    load_environment();
    e = c2_sanitizer_environ;
    while (e < c2_sanitizer_environ + c2_sanitizer_environ_size) {
        const char *entry = e;
        const char *n = name;
        while (*n != '\0' && *e == *n) { e++; n++; }
        if (*n == '\0' && *e == '=') return e + 1;
        e = entry;
        while (*e != '\0') e++;
        e++;
    }
    return NULL;
}

static int executable(const char *path)
{
    return syscall(SYS_access, path, X_OK) == 0;
}

/* First executable `name` on PATH, written to out[capacity]; 0 if none. */
static int find_on_path(const char *name, char *out, size_t capacity)
{
    const char *path = environment_value("PATH");
    while (path != NULL && *path != '\0') {
        size_t length = 0;
        size_t i;
        while (path[length] != '\0' && path[length] != ':') length++;
        if (length > 0) {
            size_t n = 0;
            for (i = 0; i < length && n + 1 < capacity; i++) out[n++] = path[i];
            if (n + 1 < capacity) out[n++] = '/';
            for (i = 0; name[i] != '\0' && n + 1 < capacity; i++) out[n++] = name[i];
            out[n] = '\0';
            if (name[i] == '\0' && executable(out)) return 1;
        }
        path += length;
        if (*path == ':') path++;
    }
    return 0;
}

const char *__asan_default_options(void)
{
    /* Malloc stacks unwound through frame pointers stop at the first frame
     * without one (Mesa, libc); the slow unwinder walks through them. */
    static const char base[] = "fast_unwind_on_malloc=0:external_symbolizer_path=";
    char tool[C2_SANITIZER_OPTIONS_CAPACITY - sizeof(base)];
    size_t n = 0;
    size_t i;

    if (environment_value("ASAN_SYMBOLIZER_PATH") != NULL ||
        find_on_path("llvm-symbolizer", tool, sizeof(tool)) ||
        !find_on_path("addr2line", tool, sizeof(tool))) {
        return "fast_unwind_on_malloc=0";
    }
    for (i = 0; base[i] != '\0'; i++) c2_sanitizer_options[n++] = base[i];
    for (i = 0; tool[i] != '\0'; i++) c2_sanitizer_options[n++] = tool[i];
    c2_sanitizer_options[n] = '\0';
    return c2_sanitizer_options;
}

/*
 * Exit-time leaks inside system libraries are theirs to fix and only bury
 * the port's own. Matching is by module or function name anywhere in the
 * allocation stack. The media library is deliberately not listed as a
 * module, since most of the port's allocations pass through its allocator;
 * only its ALSA device enumeration is.
 */
const char *__lsan_default_suppressions(void)
{
    return
        "leak:libasound\n"
        "leak:ALSA_HotplugIteration\n"
        "leak:ALSA_DetectDevices\n"
        "leak:libpulse\n"
        "leak:libpipewire\n"
        "leak:libjack\n"
        "leak:libdbus\n"
        "leak:libX11\n"
        "leak:libxcb\n"
        "leak:libXcursor\n"
        "leak:libwayland\n"
        "leak:libdecor\n"
        "leak:libgtk\n"
        "leak:libglib\n"
        "leak:libgobject\n"
        "leak:libfontconfig\n"
        "leak:libGL\n"
        "leak:libEGL\n"
        "leak:libvulkan\n"
        "leak:_dri.so\n"
        "leak:libudev\n";
}
