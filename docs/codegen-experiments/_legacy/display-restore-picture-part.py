"""restore_picture_part — add-destination register choice experiment."""

from c2.commands.cgex import Experiment

exp = Experiment(
    name="display-restore-picture-part",
    ps_function="restore_picture_part",
    externs={"place_i_sprite": 'extern void place_i_sprite(int sprite_addr);'},
    prelude="""
extern int data_ptr;
extern int sprite_width;
extern int sprite_height;
extern int sprite_start;
extern int sprite_x;
extern int sprite_y;
extern int x_wrap;
""",
    extra_defs="""
int data_ptr;
int sprite_width;
int sprite_height;
int sprite_start;
int sprite_x;
int sprite_y;
int x_wrap;
""",
)

base = r'''
void restore_picture_part(int sprite_addr, int sprite_idx)
{
    unsigned char *p;

    data_ptr = sprite_idx * 16 + 8;
    p = (unsigned char *)sprite_addr + data_ptr;
    sprite_width  = (p[1] << 8) + p[0];
    sprite_height = p[2] + (p[3] << 8);
    sprite_start  = p[4] + (p[5] << 8) + (p[6] << 16);
    if (sprite_start > 0x4baf0) return;
    if (sprite_width <= 0) return;
    if (sprite_width > 0x280) return;
    if (sprite_height <= 0) return;
    if (sprite_height > 0x1e0) return;
    sprite_x = (p[9] << 8) + p[8];
    sprite_y = p[10] + (p[11] << 8);
    x_wrap = 0x280 - sprite_width;
    place_i_sprite(sprite_addr);
}
'''
exp.add("baseline", base, note="current source: 4b add/store register choice")

exp.add("reverse-first-and-x", base.replace("(p[1] << 8) + p[0]", "p[0] + (p[1] << 8)").replace("(p[9] << 8) + p[8]", "p[8] + (p[9] << 8)"), note="obvious lo+hi order")

exp.add("hi-temp-order", r'''
void restore_picture_part(int sprite_addr, int sprite_idx)
{
    unsigned char *p;
    int hi;

    data_ptr = sprite_idx * 16 + 8;
    p = (unsigned char *)sprite_addr + data_ptr;
    hi = p[1] << 8;
    sprite_width = hi + p[0];
    sprite_height = p[2] + (p[3] << 8);
    sprite_start  = p[4] + (p[5] << 8) + (p[6] << 16);
    if (sprite_start > 0x4baf0) return;
    if (sprite_width <= 0) return;
    if (sprite_width > 0x280) return;
    if (sprite_height <= 0) return;
    if (sprite_height > 0x1e0) return;
    hi = p[9] << 8;
    sprite_x = hi + p[8];
    sprite_y = p[10] + (p[11] << 8);
    x_wrap = 0x280 - sprite_width;
    place_i_sprite(sprite_addr);
}
''', note="name hi but keep hi+lo")

exp.add("u16-macro", r'''
#define U16(off) ((unsigned short)(p[(off)] + (p[(off)+1] << 8)))
void restore_picture_part(int sprite_addr, int sprite_idx)
{
    unsigned char *p;

    data_ptr = sprite_idx * 16 + 8;
    p = (unsigned char *)sprite_addr + data_ptr;
    sprite_width  = U16(0);
    sprite_height = U16(2);
    sprite_start  = p[4] + (p[5] << 8) + (p[6] << 16);
    if (sprite_start > 0x4baf0) return;
    if (sprite_width <= 0) return;
    if (sprite_width > 0x280) return;
    if (sprite_height <= 0) return;
    if (sprite_height > 0x1e0) return;
    sprite_x = U16(8);
    sprite_y = U16(10);
    x_wrap = 0x280 - sprite_width;
    place_i_sprite(sprite_addr);
}
#undef U16
''', note="lo+hi macro")

exp.add("word-cast", r'''
void restore_picture_part(int sprite_addr, int sprite_idx)
{
    unsigned char *p;

    data_ptr = sprite_idx * 16 + 8;
    p = (unsigned char *)sprite_addr + data_ptr;
    sprite_width  = *(unsigned short *)(p + 0);
    sprite_height = *(unsigned short *)(p + 2);
    sprite_start  = p[4] + (p[5] << 8) + (p[6] << 16);
    if (sprite_start > 0x4baf0) return;
    if (sprite_width <= 0) return;
    if (sprite_width > 0x280) return;
    if (sprite_height <= 0) return;
    if (sprite_height > 0x1e0) return;
    sprite_x = *(unsigned short *)(p + 8);
    sprite_y = *(unsigned short *)(p + 10);
    x_wrap = 0x280 - sprite_width;
    place_i_sprite(sprite_addr);
}
''', note="unaligned word loads")

exp.add("assign-temp-width-x", r'''
void restore_picture_part(int sprite_addr, int sprite_idx)
{
    unsigned char *p;
    int v;

    data_ptr = sprite_idx * 16 + 8;
    p = (unsigned char *)sprite_addr + data_ptr;
    v = (p[1] << 8) + p[0];
    sprite_width = v;
    sprite_height = p[2] + (p[3] << 8);
    sprite_start  = p[4] + (p[5] << 8) + (p[6] << 16);
    if (sprite_start > 0x4baf0) return;
    if (sprite_width <= 0) return;
    if (sprite_width > 0x280) return;
    if (sprite_height <= 0) return;
    if (sprite_height > 0x1e0) return;
    v = (p[9] << 8) + p[8];
    sprite_x = v;
    sprite_y = p[10] + (p[11] << 8);
    x_wrap = 0x280 - sprite_width;
    place_i_sprite(sprite_addr);
}
''', note="explicit result temp")

exp.add("only-width-reverse", base.replace("(p[1] << 8) + p[0]", "p[0] + (p[1] << 8)"), note="reverse width only")
exp.add("only-x-reverse", base.replace("(p[9] << 8) + p[8]", "p[8] + (p[9] << 8)"), note="reverse x only")

exp.add("width-hi-temp-x-base", r'''
void restore_picture_part(int sprite_addr, int sprite_idx)
{
    unsigned char *p;
    int hi;

    data_ptr = sprite_idx * 16 + 8;
    p = (unsigned char *)sprite_addr + data_ptr;
    hi = p[1] << 8;
    sprite_width = hi + p[0];
    sprite_height = p[2] + (p[3] << 8);
    sprite_start  = p[4] + (p[5] << 8) + (p[6] << 16);
    if (sprite_start > 0x4baf0) return;
    if (sprite_width <= 0) return;
    if (sprite_width > 0x280) return;
    if (sprite_height <= 0) return;
    if (sprite_height > 0x1e0) return;
    sprite_x = (p[9] << 8) + p[8];
    sprite_y = p[10] + (p[11] << 8);
    x_wrap = 0x280 - sprite_width;
    place_i_sprite(sprite_addr);
}
''', note="hi temp for width only")

exp.add("width-base-x-hi-temp", r'''
void restore_picture_part(int sprite_addr, int sprite_idx)
{
    unsigned char *p;
    int hi;

    data_ptr = sprite_idx * 16 + 8;
    p = (unsigned char *)sprite_addr + data_ptr;
    sprite_width  = (p[1] << 8) + p[0];
    sprite_height = p[2] + (p[3] << 8);
    sprite_start  = p[4] + (p[5] << 8) + (p[6] << 16);
    if (sprite_start > 0x4baf0) return;
    if (sprite_width <= 0) return;
    if (sprite_width > 0x280) return;
    if (sprite_height <= 0) return;
    if (sprite_height > 0x1e0) return;
    hi = p[9] << 8;
    sprite_x = hi + p[8];
    sprite_y = p[10] + (p[11] << 8);
    x_wrap = 0x280 - sprite_width;
    place_i_sprite(sprite_addr);
}
''', note="hi temp for x only")

exp.add("subtract-negative-low", base.replace("(p[1] << 8) + p[0]", "(p[1] << 8) - -p[0]").replace("(p[9] << 8) + p[8]", "(p[9] << 8) - -p[8]"), note="hi - -lo")

exp.add("cast-hi-int", base.replace("(p[1] << 8) + p[0]", "((int)p[1] << 8) + p[0]").replace("(p[9] << 8) + p[8]", "((int)p[9] << 8) + p[8]"), note="explicit int high")

# A precomputed-lo into a named local: maybe T_lo gets a shorter
# conflict and result coalesces with it.
exp.add("lo-named-local", r'''
void restore_picture_part(int sprite_addr, int sprite_idx)
{
    unsigned char *p;
    unsigned char lo;

    data_ptr = sprite_idx * 16 + 8;
    p = (unsigned char *)sprite_addr + data_ptr;
    lo = p[0]; sprite_width  = (p[1] << 8) + lo;
    sprite_height = p[2] + (p[3] << 8);
    sprite_start  = p[4] + (p[5] << 8) + (p[6] << 16);
    if (sprite_start > 0x4baf0) return;
    if (sprite_width <= 0) return;
    if (sprite_width > 0x280) return;
    if (sprite_height <= 0) return;
    if (sprite_height > 0x1e0) return;
    lo = p[8]; sprite_x = (p[9] << 8) + lo;
    sprite_y = p[10] + (p[11] << 8);
    x_wrap = 0x280 - sprite_width;
    place_i_sprite(sprite_addr);
}
''', note="lo loaded into named local before add")

exp.add("hi-and-lo-named", r'''
void restore_picture_part(int sprite_addr, int sprite_idx)
{
    unsigned char *p;
    int hi;
    unsigned char lo;

    data_ptr = sprite_idx * 16 + 8;
    p = (unsigned char *)sprite_addr + data_ptr;
    hi = p[1] << 8; lo = p[0]; sprite_width = hi + lo;
    sprite_height = p[2] + (p[3] << 8);
    sprite_start  = p[4] + (p[5] << 8) + (p[6] << 16);
    if (sprite_start > 0x4baf0) return;
    if (sprite_width <= 0) return;
    if (sprite_width > 0x280) return;
    if (sprite_height <= 0) return;
    if (sprite_height > 0x1e0) return;
    hi = p[9] << 8; lo = p[8]; sprite_x = hi + lo;
    sprite_y = p[10] + (p[11] << 8);
    x_wrap = 0x280 - sprite_width;
    place_i_sprite(sprite_addr);
}
''', note="hi int + lo char locals")

exp.add("compound-or", base.replace("(p[1] << 8) + p[0]", "(p[1] << 8) | p[0]").replace("(p[9] << 8) + p[8]", "(p[9] << 8) | p[8]"), note="bitwise OR")

exp.add("p0-then-shift-add", r'''
void restore_picture_part(int sprite_addr, int sprite_idx)
{
    unsigned char *p;

    data_ptr = sprite_idx * 16 + 8;
    p = (unsigned char *)sprite_addr + data_ptr;
    sprite_width  = p[0];
    sprite_width += p[1] << 8;
    sprite_height = p[2] + (p[3] << 8);
    sprite_start  = p[4] + (p[5] << 8) + (p[6] << 16);
    if (sprite_start > 0x4baf0) return;
    if (sprite_width <= 0) return;
    if (sprite_width > 0x280) return;
    if (sprite_height <= 0) return;
    if (sprite_height > 0x1e0) return;
    sprite_x = p[8];
    sprite_x += p[9] << 8;
    sprite_y = p[10] + (p[11] << 8);
    x_wrap = 0x280 - sprite_width;
    place_i_sprite(sprite_addr);
}
''', note="store lo first, += hi")

exp.add("addr-cast-short-deref", r'''
void restore_picture_part(int sprite_addr, int sprite_idx)
{
    unsigned char *p;

    data_ptr = sprite_idx * 16 + 8;
    p = (unsigned char *)sprite_addr + data_ptr;
    sprite_width  = ((unsigned int)p[0]) + (((unsigned int)p[1]) << 8);
    sprite_height = ((unsigned int)p[2]) + (((unsigned int)p[3]) << 8);
    sprite_start  = ((unsigned int)p[4]) + (((unsigned int)p[5]) << 8) + (((unsigned int)p[6]) << 16);
    if (sprite_start > 0x4baf0) return;
    if (sprite_width <= 0) return;
    if (sprite_width > 0x280) return;
    if (sprite_height <= 0) return;
    if (sprite_height > 0x1e0) return;
    sprite_x = ((unsigned int)p[8]) + (((unsigned int)p[9]) << 8);
    sprite_y = ((unsigned int)p[10]) + (((unsigned int)p[11]) << 8);
    x_wrap = 0x280 - sprite_width;
    place_i_sprite(sprite_addr);
}
''', note="explicit unsigned int casts")

exp.add("two-step-shift", r'''
void restore_picture_part(int sprite_addr, int sprite_idx)
{
    unsigned char *p;
    int v;

    data_ptr = sprite_idx * 16 + 8;
    p = (unsigned char *)sprite_addr + data_ptr;
    v = p[1]; v <<= 8;
    sprite_width = v + p[0];
    sprite_height = p[2] + (p[3] << 8);
    sprite_start  = p[4] + (p[5] << 8) + (p[6] << 16);
    if (sprite_start > 0x4baf0) return;
    if (sprite_width <= 0) return;
    if (sprite_width > 0x280) return;
    if (sprite_height <= 0) return;
    if (sprite_height > 0x1e0) return;
    v = p[9]; v <<= 8;
    sprite_x = v + p[8];
    sprite_y = p[10] + (p[11] << 8);
    x_wrap = 0x280 - sprite_width;
    place_i_sprite(sprite_addr);
}
''', note="explicit shift-in-place")

exp.add("p1-load-shift-then-add-p0", r'''
void restore_picture_part(int sprite_addr, int sprite_idx)
{
    unsigned char *p;
    unsigned int hi;

    data_ptr = sprite_idx * 16 + 8;
    p = (unsigned char *)sprite_addr + data_ptr;
    hi = (unsigned int)p[1] << 8;
    sprite_width = hi + (unsigned int)p[0];
    sprite_height = p[2] + (p[3] << 8);
    sprite_start  = p[4] + (p[5] << 8) + (p[6] << 16);
    if (sprite_start > 0x4baf0) return;
    if (sprite_width <= 0) return;
    if (sprite_width > 0x280) return;
    if (sprite_height <= 0) return;
    if (sprite_height > 0x1e0) return;
    hi = (unsigned int)p[9] << 8;
    sprite_x = hi + (unsigned int)p[8];
    sprite_y = p[10] + (p[11] << 8);
    x_wrap = 0x280 - sprite_width;
    place_i_sprite(sprite_addr);
}
''', note="hi unsigned + casts")
