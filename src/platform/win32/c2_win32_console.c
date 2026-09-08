/*
 * Windows has two kinds of program and Caesar II is both. Built for the
 * console subsystem, every start opens a black window that stays behind the
 * game until it quits; built for the windows subsystem, that window is gone
 * but so is anywhere for --version, the usage line or a fatal message to go.
 *
 * The executable is a windows-subsystem one (CMake's WIN32_EXECUTABLE; SDL
 * supplies the WinMain), and this attaches the terminal's console when the
 * game was started from one, before anything is printed. Started from
 * Explorer or the Start menu there is no console to attach and nothing
 * happens; started with the output redirected or piped, the handles are
 * already inherited and are left exactly as they are.
 */
#include <windows.h>

#include <stdio.h>

#include "c2_win32_console.h"

/* A standard handle is already usable when the shell redirected it: a file,
 * a pipe, or a console the process inherited. */
static int handle_is_usable(DWORD std_handle)
{
    HANDLE handle = GetStdHandle(std_handle);

    return handle != NULL && handle != INVALID_HANDLE_VALUE;
}

static void reopen(const char *device, const char *mode, FILE *stream)
{
    FILE *reopened = NULL;

    if (freopen_s(&reopened, device, mode, stream) != 0) return;
    setvbuf(stream, NULL, _IONBF, 0);
}

void c2_win32_attach_parent_console(void)
{
    int stdout_taken = handle_is_usable(STD_OUTPUT_HANDLE);
    int stderr_taken = handle_is_usable(STD_ERROR_HANDLE);

    if (stdout_taken && stderr_taken) return;   /* redirected: leave it */
    if (!AttachConsole(ATTACH_PARENT_PROCESS)) return;  /* no terminal */

    if (!stdout_taken) reopen("CONOUT$", "w", stdout);
    if (!stderr_taken) reopen("CONOUT$", "w", stderr);
    if (!handle_is_usable(STD_INPUT_HANDLE)) reopen("CONIN$", "r", stdin);
    /* The shell printed its prompt the moment it started a windowed
     * program, so the first line would land beside it. */
    fputc('\n', stdout);
}
