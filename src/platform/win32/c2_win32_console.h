#ifndef C2_WIN32_CONSOLE_H
#define C2_WIN32_CONSOLE_H

/* Attach the terminal that started the game, when there is one, so the
 * windowed executable can still print (src/platform/win32/c2_win32_console.c). */
void c2_win32_attach_parent_console(void);

#endif /* C2_WIN32_CONSOLE_H */
