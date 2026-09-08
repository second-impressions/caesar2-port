/* The helmet of web/favicon.svg as the window icon: what the taskbar,
 * Alt-Tab and the title bar show for the launcher and the game window.
 * packaging/icon/caesar2-256.png is compiled in (cmake/EmbedFile.cmake).
 * The desktop entry (Linux), the executable's resource (Windows) and the
 * bundle (macOS, where a window icon is a no-op) carry the same picture
 * for the places a running window does not reach. */
#include "c2_sdl_host.h"

#include <SDL3/SDL.h>

extern const unsigned char c2_window_icon_png[];
extern const unsigned int c2_window_icon_png_size;

void c2_sdl_set_window_icon(SDL_Window *window)
{
    SDL_IOStream *io;
    SDL_Surface *icon;

    if (window == NULL) return;
    io = SDL_IOFromConstMem(c2_window_icon_png, c2_window_icon_png_size);
    if (io == NULL) return;
    icon = SDL_LoadPNG_IO(io, true);
    if (icon == NULL) {
        SDL_Log("window icon: %s", SDL_GetError());
        return;
    }
    SDL_SetWindowIcon(window, icon);
    SDL_DestroySurface(icon);
}
