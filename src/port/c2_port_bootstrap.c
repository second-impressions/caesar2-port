#include <string.h>

#include "c2_data.h"
#include "c2_port.h"

#define C2_FONT1_BYTES 9460
#define C2_FONT2_BYTES 28248
#define C2_MICE_BYTES 8630
#define C2_SYSTEM_PANEL_BYTES 41672
#define C2_GAME_PANELS_BYTES 23441
#define C2_MISC_BYTES 3584
#define C2_TEXT_BUFFER_BYTES 40000

extern int readfile(const char *filename, void *buffer, int size, int offset);

int c2_port_load_startup_ui(void)
{
    if (readfile("font_c2.pl8", font1, C2_FONT1_BYTES, 0) == 0) return 0;
    if (readfile("font3c2.pl8", font2, C2_FONT2_BYTES, 0) == 0) return 0;
    if (readfile("mouse.pl8", mice, C2_MICE_BYTES, 0) == 0) return 0;
    if (readfile("system.pl8", system_panel, C2_SYSTEM_PANEL_BYTES, 0) == 0) return 0;
    if (readfile("panels.pl8", game_panels, C2_GAME_PANELS_BYTES, 0) == 0) return 0;
    if (readfile("misc.pl8", misc, C2_MISC_BYTES, 0) == 0) return 0;
    if (readfile("c2.eng", text_buffer, C2_TEXT_BUFFER_BYTES, 0) == 0) return 0;
    memcpy(c2inf.player_name, "Octavian", sizeof("Octavian"));
    c2inf.skill_level = 0;
    c2inf.peace_mode = 0;
    return 1;
}
