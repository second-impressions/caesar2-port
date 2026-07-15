"""mid2_line_no_sides_base — loop-index scratch register (eax vs ebx).

PS.EXE `mid2_line_no_sides_base` (294 b @ 0x398A6) computes the
`pseudo_map[pm_shown_y][pm_shown_x]` index using EAX as the
strength-reduction scratch (reused immediately for the pseudo_map load),
and `i` (the loop counter) lives in ECX:

    xor ecx, ecx                       ; i -> ECX
    ...
    mov edx, [pm_shown_y]
    mov eax, edx ; shl eax,2 ; add eax,edx ; shl eax,4   ; EAX scratch
    add edx, eax ; shl edx, 2                              ; edx = y*324
    mov eax, [pm_shown_x] ; mov ebx, eax ; inc eax ; …     ; ebx = x
    mov eax, [edx + ebx*4 + pseudo_map]                    ; EAX = cell

The faithful PS source (debug line numbers L187/L188/L189) is the
SEPARATE assignment with `map_direction >> 1` inlined:

    sprite_image_no = region_map[pm_shown_ptr];
    sprite_image_no = rotated2_map[sprite_image_no].dir[map_direction >> 1];
    sprite_image_no += 0x10;

Our default build of that separate form pushes the index scratch into
EBX (whole-function regalloc cascade) -> 59 b diff.  The INLINE form
`rotated2_map[region_map[ptr]].dir[map_direction>>1]` keeps the scratch
in EAX (+0x25 region exact) but is missing PS's intermediate
`mov [sprite_image_no], eax` store, leaving a 12 b residue at +0xBA.

This experiment isolates the source shape that gives BOTH the EAX
scratch AND the intermediate store.

Run::

    uv run c2 cgex run mid2_line_no_sides_base
    uv run c2 cgex run mid2_line_no_sides_base --trial separate
"""

from c2.commands.cgex import Experiment

# Faithful hand-roll of the entities.h types this function touches (cgex
# compiles one isolated TU with no -I to decomp/include, so the real header
# can't be #included).  rotated2_map's 4-byte element stride and the
# pseudo_map[161][81] (=324-byte row) stride are what drive the codegen, so
# they must match the real declarations exactly.
_TYPES = """
struct rotated_sprite_rec { unsigned char dir[4]; };
extern int pseudo_map[161][81];
extern unsigned char region_map[];
extern struct rotated_sprite_rec rotated2_map[];
extern int pm_screen_x_start, sprite_x, pm_x, pm_shown_x, pm_shown_y;
extern int pm_shown_ptr, sprite_image_no, map_direction;
extern int pm_diamond_width, pm_diamond_half_height, sprite_y, pm_y_clip;
extern int pm_screen_width;
extern void place2_a_building_base(int);
extern void print2_test_info(void);
extern void refresh_a_square(int, int, int);
extern void place_diamond(int);
"""

# PM_IS_SPRITE / PM_SPRITE_KIND are kept as macros so the trial bodies read
# verbatim like decomp/src/pm_map2.c (entities.h spells them the same way).
_PRELUDE = _TYPES + """
#define PM_IS_SPRITE(v)   ((v) >= 0x0FFF0000)
#define PM_SPRITE_KIND(v) ((v) - 0x0FFF0000)
"""

# defs.c provides the actual storage + stub bodies the externs resolve to.
_DEFS = """
struct rotated_sprite_rec { unsigned char dir[4]; };
int pseudo_map[161][81];
unsigned char region_map[80000];
struct rotated_sprite_rec rotated2_map[256];
int pm_screen_x_start, sprite_x, pm_x, pm_shown_x, pm_shown_y;
int pm_shown_ptr, sprite_image_no, map_direction;
int pm_diamond_width, pm_diamond_half_height, sprite_y, pm_y_clip;
int pm_screen_width;
void place2_a_building_base(int a){(void)a;}
void print2_test_info(void){}
void refresh_a_square(int a,int b,int c){(void)a;(void)b;(void)c;}
void place_diamond(int a){(void)a;}
"""

exp = Experiment(
    name="mid2_line_no_sides_base",
    ps_function="mid2_line_no_sides_base",
    externs={},
    prelude=_PRELUDE,
    extra_defs=_DEFS,
)


# ── separate: the faithful PS source (separate assignment, inline dir) ──
exp.add(
    "separate",
    """
void mid2_line_no_sides_base(void)
{
    int i;
    int h;

    sprite_x = pm_screen_x_start;
    i = 0;
    pm_shown_x = pm_x;
    for (; i < pm_screen_width; i++) {
        pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x++];
        if (PM_IS_SPRITE(pm_shown_ptr)) {
            sprite_image_no = PM_SPRITE_KIND(pm_shown_ptr);
        } else if (region_map[pm_shown_ptr] > 0x7c) {
            place2_a_building_base(0);
            print2_test_info();
            continue;
        } else {
            if ((region_map[pm_shown_ptr + 3] & 1) != 0) {
                region_map[pm_shown_ptr + 3] &= 0xfe;
                refresh_a_square(sprite_x >> 4, sprite_y >> 4, 2);
            }
            sprite_image_no = region_map[pm_shown_ptr];
            sprite_image_no = rotated2_map[sprite_image_no].dir[map_direction >> 1];
            sprite_image_no += 0x10;
        }
        place_diamond(0);
        sprite_x += pm_diamond_width;
        print2_test_info();
    }
    h = pm_diamond_half_height;
    sprite_y  += h;
    pm_shown_y++;
    pm_y_clip += h;
}
""",
    note="separate assignment, inline map_direction>>1 (PS line shape)",
)


# ── inline: the 12b residue form (no intermediate store) ──
exp.add(
    "inline",
    """
void mid2_line_no_sides_base(void)
{
    int i;
    int h;

    sprite_x = pm_screen_x_start;
    i = 0;
    pm_shown_x = pm_x;
    for (; i < pm_screen_width; i++) {
        pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x++];
        if (PM_IS_SPRITE(pm_shown_ptr)) {
            sprite_image_no = PM_SPRITE_KIND(pm_shown_ptr);
        } else if (region_map[pm_shown_ptr] > 0x7c) {
            place2_a_building_base(0);
            print2_test_info();
            continue;
        } else {
            if ((region_map[pm_shown_ptr + 3] & 1) != 0) {
                region_map[pm_shown_ptr + 3] &= 0xfe;
                refresh_a_square(sprite_x >> 4, sprite_y >> 4, 2);
            }
            sprite_image_no = rotated2_map[region_map[pm_shown_ptr]].dir[map_direction >> 1];
            sprite_image_no += 0x10;
        }
        place_diamond(0);
        sprite_x += pm_diamond_width;
        print2_test_info();
    }
    h = pm_diamond_half_height;
    sprite_y  += h;
    pm_shown_y++;
    pm_y_clip += h;
}
""",
    note="inline index (12b residue: EAX scratch ok, missing store)",
)


# ── battery: vary only the `else` rotated-index block ──
def _body(inner):
    return """
void mid2_line_no_sides_base(void)
{
    int i;
    int h;
    int dir;

    sprite_x = pm_screen_x_start;
    i = 0;
    pm_shown_x = pm_x;
    for (; i < pm_screen_width; i++) {
        pm_shown_ptr = pseudo_map[pm_shown_y][pm_shown_x++];
        if (PM_IS_SPRITE(pm_shown_ptr)) {
            sprite_image_no = PM_SPRITE_KIND(pm_shown_ptr);
        } else if (region_map[pm_shown_ptr] > 0x7c) {
            place2_a_building_base(0);
            print2_test_info();
            continue;
        } else {
            if ((region_map[pm_shown_ptr + 3] & 1) != 0) {
                region_map[pm_shown_ptr + 3] &= 0xfe;
                refresh_a_square(sprite_x >> 4, sprite_y >> 4, 2);
            }
""" + inner + """
        }
        place_diamond(0);
        sprite_x += pm_diamond_width;
        print2_test_info();
    }
    h = pm_diamond_half_height;
    sprite_y  += h;
    pm_shown_y++;
    pm_y_clip += h;
}
"""

exp.add("dir-local-after", _body(
    "            sprite_image_no = region_map[pm_shown_ptr];\n"
    "            dir = map_direction >> 1;\n"
    "            sprite_image_no = rotated2_map[sprite_image_no].dir[dir];\n"
    "            sprite_image_no += 0x10;"),
    note="separate + dir local AFTER sprite_image_no (exact-sibling order)")

exp.add("dir-local-before", _body(
    "            dir = map_direction >> 1;\n"
    "            sprite_image_no = region_map[pm_shown_ptr];\n"
    "            sprite_image_no = rotated2_map[sprite_image_no].dir[dir];\n"
    "            sprite_image_no += 0x10;"),
    note="separate + dir local BEFORE sprite_image_no")

exp.add("temp-v", _body(
    "            { int v = region_map[pm_shown_ptr];\n"
    "              sprite_image_no = v;\n"
    "              sprite_image_no = rotated2_map[v].dir[map_direction >> 1]; }\n"
    "            sprite_image_no += 0x10;"),
    note="explicit int v temp for region value")

exp.add("cast-uchar", _body(
    "            sprite_image_no = (unsigned char)region_map[pm_shown_ptr];\n"
    "            sprite_image_no = rotated2_map[sprite_image_no].dir[map_direction >> 1];\n"
    "            sprite_image_no += 0x10;"),
    note="(unsigned char) cast on region read")

exp.add("reindex-global", _body(
    "            sprite_image_no = region_map[pm_shown_ptr];\n"
    "            sprite_image_no = rotated2_map[region_map[pm_shown_ptr]].dir[map_direction >> 1];\n"
    "            sprite_image_no += 0x10;"),
    note="store then re-read region_map[ptr] for the index")

exp.add("dir-first-noassign", _body(
    "            dir = map_direction >> 1;\n"
    "            sprite_image_no = rotated2_map[region_map[pm_shown_ptr]].dir[dir];\n"
    "            sprite_image_no += 0x10;"),
    note="dir local first, inline region index (no separate store)")

exp.add("ptr-deref", _body(
    "            sprite_image_no = region_map[pm_shown_ptr];\n"
    "            sprite_image_no = rotated2_map[sprite_image_no].dir[(map_direction >> 1)];\n"
    "            sprite_image_no = sprite_image_no + 0x10;"),
    note="separate, parenthesised dir, +0x10 as binary")


# ── round 2: get dir into EDX, computed after the store, no cascade ──
exp.add("dir-half-expr", _body(
    "            sprite_image_no = region_map[pm_shown_ptr];\n"
    "            dir = map_direction / 2;\n"
    "            sprite_image_no = rotated2_map[sprite_image_no].dir[dir];\n"
    "            sprite_image_no += 0x10;"),
    note="dir = map_direction / 2 after store")

exp.add("dir-comma", _body(
    "            dir = map_direction >> 1,\n"
    "            sprite_image_no = region_map[pm_shown_ptr];\n"
    "            sprite_image_no = rotated2_map[sprite_image_no].dir[dir];\n"
    "            sprite_image_no += 0x10;"),
    note="dir then region via comma sequence")

exp.add("manual-ptr", _body(
    "            sprite_image_no = region_map[pm_shown_ptr];\n"
    "            sprite_image_no = ((unsigned char *)rotated2_map)\n"
    "                [sprite_image_no * 4 + (map_direction >> 1)];\n"
    "            sprite_image_no += 0x10;"),
    note="manual byte-pointer: X*4 + dir")

exp.add("manual-ptr-dirlocal", _body(
    "            dir = map_direction >> 1;\n"
    "            sprite_image_no = region_map[pm_shown_ptr];\n"
    "            sprite_image_no = ((unsigned char *)rotated2_map)\n"
    "                [sprite_image_no * 4 + dir];\n"
    "            sprite_image_no += 0x10;"),
    note="manual byte-pointer with dir local before")

exp.add("dir-before-nostore", _body(
    "            dir = map_direction >> 1;\n"
    "            sprite_image_no = rotated2_map[region_map[pm_shown_ptr]].dir[dir];\n"
    "            sprite_image_no += 0x10;"),
    note="dir local before, inline region (no separate store)")

exp.add("uint-cast", _body(
    "            sprite_image_no = region_map[pm_shown_ptr];\n"
    "            sprite_image_no = rotated2_map[(unsigned)sprite_image_no]\n"
    "                .dir[map_direction >> 1];\n"
    "            sprite_image_no += 0x10;"),
    note="(unsigned) cast on the X subscript")


# ── round 3: type/cast/order levers to coalesce scratch+X into EAX ──
exp.add("uc-temp", _body(
    "            { unsigned char uc = region_map[pm_shown_ptr];\n"
    "              sprite_image_no = uc;\n"
    "              dir = map_direction >> 1;\n"
    "              sprite_image_no = rotated2_map[uc].dir[dir]; }\n"
    "            sprite_image_no += 0x10;"),
    note="unsigned char uc temp + dir local")

exp.add("uint-temp", _body(
    "            { unsigned int uv = region_map[pm_shown_ptr];\n"
    "              sprite_image_no = uv;\n"
    "              dir = map_direction >> 1;\n"
    "              sprite_image_no = rotated2_map[uv].dir[dir]; }\n"
    "            sprite_image_no += 0x10;"),
    note="unsigned int uv temp + dir local")

exp.add("explicit-and", _body(
    "            sprite_image_no = region_map[pm_shown_ptr] & 0xff;\n"
    "            dir = map_direction >> 1;\n"
    "            sprite_image_no = rotated2_map[sprite_image_no].dir[dir];\n"
    "            sprite_image_no += 0x10;"),
    note="explicit & 0xff on region read + dir local")

exp.add("dir-div2", _body(
    "            dir = map_direction / 2;\n"
    "            sprite_image_no = region_map[pm_shown_ptr];\n"
    "            sprite_image_no = rotated2_map[sprite_image_no].dir[dir];\n"
    "            sprite_image_no += 0x10;"),
    note="dir = map_direction/2 before (vs >>1)")

exp.add("reread-x", _body(
    "            sprite_image_no = region_map[pm_shown_ptr];\n"
    "            dir = map_direction >> 1;\n"
    "            sprite_image_no =\n"
    "                rotated2_map[region_map[pm_shown_ptr]].dir[dir];\n"
    "            sprite_image_no += 0x10;"),
    note="store sprite_image_no then re-read region for index + dir local")

exp.add("dir-uint", _body(
    "            sprite_image_no = region_map[pm_shown_ptr];\n"
    "            { unsigned int d = map_direction >> 1;\n"
    "              sprite_image_no = rotated2_map[sprite_image_no].dir[d]; }\n"
    "            sprite_image_no += 0x10;"),
    note="dir as local unsigned, after store")

exp.add("ptr-cache", _body(
    "            sprite_image_no = region_map[pm_shown_ptr];\n"
    "            { struct rotated_sprite_rec *rp =\n"
    "                  &rotated2_map[sprite_image_no];\n"
    "              dir = map_direction >> 1;\n"
    "              sprite_image_no = rp->dir[dir]; }\n"
    "            sprite_image_no += 0x10;"),
    note="cache &rotated2_map[X] pointer + dir local")


# ── round 4: cleanest temp form (plain int, and minimal) ──
exp.add("int-temp", _body(
    "            { int t = region_map[pm_shown_ptr];\n"
    "              sprite_image_no = t;\n"
    "              dir = map_direction >> 1;\n"
    "              sprite_image_no = rotated2_map[t].dir[dir]; }\n"
    "            sprite_image_no += 0x10;"),
    note="plain int temp + dir local")

exp.add("int-temp-nodirlocal", _body(
    "            { int t = region_map[pm_shown_ptr];\n"
    "              sprite_image_no = t;\n"
    "              sprite_image_no = rotated2_map[t].dir[map_direction >> 1]; }\n"
    "            sprite_image_no += 0x10;"),
    note="plain int temp, inline dir (no dir local)")
