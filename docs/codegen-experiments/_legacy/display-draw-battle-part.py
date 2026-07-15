"""draw_battle_part — display.c register-allocation knockout experiment."""

from c2.commands.cgex import Experiment

exp = Experiment(
    name="display-draw-battle-part",
    ps_function="draw_battle_part",
    externs={
        "readfile": 'extern int readfile(char *fname, void *buf, int size, int offset);',
        "place_i_sprite": 'extern void place_i_sprite(int sprite_addr);',
    },
    prelude="""
extern short int_battle_header[];
extern int sprite_start;
extern int sprite_width;
extern int sprite_height;
extern int sprite_x;
extern int sprite_y;
extern int scratch_buffer;
extern int x_wrap;
""",
    extra_defs="""
short int_battle_header[64];
int sprite_start;
int sprite_width;
int sprite_height;
int sprite_x;
int sprite_y;
int scratch_buffer;
int x_wrap;
""",
)

exp.add(
    "current",
    """
void draw_battle_part(int n)
{
    int saved_n = n;
    int offset;
    int y;

    offset = (unsigned short)int_battle_header[n * 8 + 6];
    offset += ((unsigned short)int_battle_header[n * 8 + 7]) << 16;
    sprite_start  = 0;
    sprite_width  = (unsigned short)int_battle_header[n * 8 + 4];
    sprite_height = (unsigned short)int_battle_header[n * 8 + 5];
    sprite_x      = (unsigned short)int_battle_header[n * 8 + 8];
    y = (unsigned short)int_battle_header[n * 8 + 9];
    if (saved_n >= 4) y += 0xc8;
    sprite_y = y;
    readfile("int_batl.pl8", (void *)scratch_buffer, sprite_width * sprite_height, offset);
    x_wrap = 0x280 - sprite_width;
    place_i_sprite(scratch_buffer);
}
""",
    note="current display.c source (60b diff in full TU)",
)

exp.add(
    "ps-order-y-store-before-if",
    """
void draw_battle_part(int n)
{
    int saved_n = n;
    int offset;

    offset = (unsigned short)int_battle_header[n * 8 + 6];
    offset += ((unsigned short)int_battle_header[n * 8 + 7]) << 16;
    sprite_start  = 0;
    sprite_width  = (unsigned short)int_battle_header[n * 8 + 4];
    sprite_height = (unsigned short)int_battle_header[n * 8 + 5];
    sprite_x      = (unsigned short)int_battle_header[n * 8 + 8];
    sprite_y      = (unsigned short)int_battle_header[n * 8 + 9];
    if (saved_n >= 4) sprite_y += 0xc8;
    readfile("int_batl.pl8", (void *)scratch_buffer, sprite_width * sprite_height, offset);
    x_wrap = 0x280 - sprite_width;
    place_i_sprite(scratch_buffer);
}
""",
    note="PS stores y before n>=4 adjustment",
)

exp.add(
    "base-index-local",
    """
void draw_battle_part(int n)
{
    int saved_n = n;
    int base = n * 8;
    int offset;

    offset = (unsigned short)int_battle_header[base + 6];
    offset += ((unsigned short)int_battle_header[base + 7]) << 16;
    sprite_start  = 0;
    sprite_width  = (unsigned short)int_battle_header[base + 4];
    sprite_height = (unsigned short)int_battle_header[base + 5];
    sprite_x      = (unsigned short)int_battle_header[base + 8];
    sprite_y      = (unsigned short)int_battle_header[base + 9];
    if (saved_n >= 4) sprite_y += 0xc8;
    readfile("int_batl.pl8", (void *)scratch_buffer, sprite_width * sprite_height, offset);
    x_wrap = 0x280 - sprite_width;
    place_i_sprite(scratch_buffer);
}
""",
    note="named n*8 index",
)

exp.add(
    "param-mutate",
    """
void draw_battle_part(int n)
{
    int saved_n = n;
    int offset;

    n *= 8;
    offset = (unsigned short)int_battle_header[n + 6];
    offset += ((unsigned short)int_battle_header[n + 7]) << 16;
    sprite_start  = 0;
    sprite_width  = (unsigned short)int_battle_header[n + 4];
    sprite_height = (unsigned short)int_battle_header[n + 5];
    sprite_x      = (unsigned short)int_battle_header[n + 8];
    sprite_y      = (unsigned short)int_battle_header[n + 9];
    if (saved_n >= 4) sprite_y += 0xc8;
    readfile("int_batl.pl8", (void *)scratch_buffer, sprite_width * sprite_height, offset);
    x_wrap = 0x280 - sprite_width;
    place_i_sprite(scratch_buffer);
}
""",
    note="mutate n into table index",
)

exp.add(
    "offset-first-after-dims",
    """
void draw_battle_part(int n)
{
    int saved_n = n;
    int offset;

    sprite_start  = 0;
    sprite_width  = (unsigned short)int_battle_header[n * 8 + 4];
    sprite_height = (unsigned short)int_battle_header[n * 8 + 5];
    offset = (unsigned short)int_battle_header[n * 8 + 6];
    offset += ((unsigned short)int_battle_header[n * 8 + 7]) << 16;
    sprite_x      = (unsigned short)int_battle_header[n * 8 + 8];
    sprite_y      = (unsigned short)int_battle_header[n * 8 + 9];
    if (saved_n >= 4) sprite_y += 0xc8;
    readfile("int_batl.pl8", (void *)scratch_buffer, sprite_width * sprite_height, offset);
    x_wrap = 0x280 - sprite_width;
    place_i_sprite(scratch_buffer);
}
""",
    note="field order changed",
)

exp.add(
    "signed-n-compare",
    """
void draw_battle_part(int n)
{
    int saved_n = n;
    int offset;

    offset = (unsigned short)int_battle_header[n * 8 + 6];
    offset += ((unsigned short)int_battle_header[n * 8 + 7]) << 16;
    sprite_start  = 0;
    sprite_width  = (unsigned short)int_battle_header[n * 8 + 4];
    sprite_height = (unsigned short)int_battle_header[n * 8 + 5];
    sprite_x      = (unsigned short)int_battle_header[n * 8 + 8];
    sprite_y      = (unsigned short)int_battle_header[n * 8 + 9];
    if (n >= 4) sprite_y += 0xc8;
    readfile("int_batl.pl8", (void *)scratch_buffer, sprite_width * sprite_height, offset);
    x_wrap = 0x280 - sprite_width;
    place_i_sprite(scratch_buffer);
}
""",
    note="no explicit saved_n local",
)
