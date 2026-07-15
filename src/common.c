// D:\C2\CODE\common.c

#include "common.h"
#include "c2_data.h"
#include "c2_types.h"

/* ── TU-owned file-scope variables (PS.EXE _BSS, original declaration
   order).  Recovered so the functional rebuild (`c2 rebuild`) links
   self-sustained -- no auto-stubbed storage.  Extern decls: c2_data.h. */
int ferret_targ_x;
int ferret_targ_y;
int anti_ferret_moves;
int last_anti_ferret_dirc;
int tb_ptr;
int anti_ferret_running;
int clock_ferret_moves;
int clock_ferret_ptr;
int tb_x;
int tb_y;
int ferret_map_hi;
int clock_ferret_count;
int clock_ferret_running;
int ferret_map_wi;
unsigned char * ferret_map;
int anti_ferret_count;
int anti_ferret_ptr;
int ferret_vert_off;
int ferret_home;
int clock_ferret_y;
int anti_ferret_x;
int anti_ferret_y;
int last_clock_ferret_dirc;
int ferret_targ_ptr;
int ferret_horiz_off;
int clock_ferret_x;
int ferret_energy;
char tb_occ_b_flag;
char tb_road_flag;
char tb_prev_flag;
char tb_occ_a_flag;

/* army_rec now in c2_types.h, storage in formulae.c */

/* Forward declarations */
heading_t get_heading(int sx, int sy, int ex, int ey, char mode);
void init_bd(int x1, int y1, int x2, int y2);
signed char check_clock_ferret_move(signed char dir);
signed char check_anti_ferret_move(signed char dir);
unsigned char ferret_heading(int x, int y);
unsigned char get_tb_value(int dir);
unsigned char get_ferret2(int dir);

// FUNCTION: C2 0x2A907
// WIN: 0x004691b0
// Lines 52–104
//
// The create_* family was off-by-one in CAESAR2.EXE (its first slot,
// create_citizen @0x004691b0, had been left unmapped, shifting every
// later create_* up one).  Recovered via AST call-graph + per-slot
// global signature: this slot refs citizen_a/citizen_b/created_citizen_no.
int create_citizen(int type, int x, int y, char is_barb)
{
    int ref;
    char terrain;
    char cx;
    char cy;

    if (x < 0 || x >= 0x50 || y < 0 || y >= 0x50)
        return 0;

    ref = (y * 0x50 + x) * 0x14;
    terrain = CM_CELL((ref)).terrain;
    citizen_a = (unsigned char)CM_CELL((ref)).citizen_a;
    citizen_b = (unsigned char)CM_CELL((ref)).citizen_b;
    if ((citizen_a == 0 || citizen_b == 0) && (terrain & 0x8b) == 0) {
        if (is_barb != 0) {                          /* PS layout: else-first */
            if ((terrain & 0x20) == 0)
                return 0;
        } else {
            if ((terrain & 0x54) != 0)
                return 0;
        }
        for (created_citizen_no = 1; created_citizen_no < 0xC9; created_citizen_no++) {
            if (citizen_list[created_citizen_no].exists == 0) {
                citizen_list[created_citizen_no].exists = 1;
                citizen_list[created_citizen_no].evolve_timer = (evolve_count + (short)rand128) & 0x7fff;
                cx = x;
                cy = y;
                citizen_list[created_citizen_no].type = type;
                citizen_list[created_citizen_no].x = cx;
                citizen_list[created_citizen_no].dest_x = cx;
                citizen_list[created_citizen_no].y = cy;
                citizen_list[created_citizen_no].dest_y = cy;
                citizen_list[created_citizen_no].map_ref = ref;
                citizen_list[created_citizen_no].pixel_x = cx << 4;
                citizen_list[created_citizen_no].pixel_y = cy << 4;
                citizen_list[created_citizen_no].world_dir = 1;
                citizen_list[created_citizen_no].speed = 5;
                citizen_list[created_citizen_no].state = 0;
                if (citizen_a == 0) {
                    CM_CELL((ref)).citizen_a = created_citizen_no;
                } else {
                    CM_CELL((ref)).citizen_b = created_citizen_no;
                }
                CM_CELL((ref)).edge_bits = CM_CELL((ref)).edge_bits | 1;
                if (is_barb != 0) {                              /* PS layout: else-first */
                    citizen_list[created_citizen_no].is_barbarian = 1;
                } else {
                    citizen_list[created_citizen_no].is_barbarian = 0;
                }
                if (type == 3) {
                    citizen_list[created_citizen_no].name_id = barbarian_name_count;
                } else {
                    citizen_list[created_citizen_no].name_id = roman_name_count;
                }
                roman_name_count++;
                if (roman_name_count >= 0x20)             // Rule 4
                    roman_name_count = 0;
                barbarian_name_count++;
                if (barbarian_name_count >= 0x10)         // Rule 4
                    barbarian_name_count = 0;
                return 1;
            }
        }
    }
    return 0;
}

// FUNCTION: C2 0x2AB1A
// WIN: 0x004695b9
// Lines 106–145
// (CAESAR2.EXE 0x004695b9 refs army_a/army_list/rand128 — create_army.)
int create_army(int type, int x, int y, char mode)
{
    int ref;
    char terrain;

    if (x < 0)
        return 0;
    if (x >= 0x3C)
        return 0;
    if (y < 0)
        return 0;
    if (y >= 0x3C)
        return 0;

    ref = (x + y * 0x3C) * 8;
    terrain = RM_CELL(ref).terrain;
    army_a = (unsigned char)RM_CELL(ref).occupant;
    if (army_a != 0)
        return 0;

    if (mode == 1) {
        if ((terrain & 8) == 0)
            return 0;
    } else if (mode == 2) {
        if ((terrain & 0x1F) != 0)
            return 0;
    }

    for (created_army_no = 1; created_army_no < 0x19; created_army_no++) {
        if (army_list[created_army_no].exists == 0) {
            clear_army(&army_list[created_army_no]);
            army_list[created_army_no].exists = 1;
            army_list[created_army_no].morale = 2;
            army_list[created_army_no].evolve_timer = (evolve_count + (short)rand128) & 0x7fff;
            army_list[created_army_no].type = type;
            army_list[created_army_no].x = x;
            army_list[created_army_no].target_x = x;
            army_list[created_army_no].y = y;
            army_list[created_army_no].target_y = y;
            army_list[created_army_no].map_ref = ref;
            army_list[created_army_no].home_ref = ref;
            army_list[created_army_no].fort_ref = ref;
            army_list[created_army_no].pixel_x = x << 4;
            army_list[created_army_no].pixel_y = y << 4;
            army_list[created_army_no].world_dir = 1;
            army_list[created_army_no].heading = 5;
            army_list[created_army_no].flags |= 1;
            RM_CELL(ref).occupant = created_army_no;
            RM_CELL(ref).edge_bits |= 1;
            return 1;
        }
    }
    return 0;
}

// FUNCTION: C2 0x2AC8B
// WIN: 0x0046993d
// Lines 147–161
// (CAESAR2.EXE 0x0046993d refs created_unit_no — create_unit.)
int create_unit(int owner, int x, int y, int type)
{
    for (created_unit_no = 1; created_unit_no < 0x33; created_unit_no++) {
        if (unit_list[created_unit_no].exists == 0) {
            unit_list[created_unit_no].exists = 1;
            unit_list[created_unit_no].owner = owner;
            unit_list[created_unit_no].x = x;
            unit_list[created_unit_no].prev_x = x;
            unit_list[created_unit_no].y = y;
            unit_list[created_unit_no].prev_y = y;
            unit_list[created_unit_no].state = 0;
            unit_list[created_unit_no].type = type;
            return 1;
        }
    }
    return 0;
}

// FUNCTION: C2 0x2ACFB
// WIN: 0x00469aa3
// Lines 163–190
// (CAESAR2.EXE 0x00469aa3 refs created_figure_no — create_figure.)
int create_figure(int sprite_type, int base_x, int off_x, int base_y, int off_y, int owner, int unit_no)
{
    for (created_figure_no = 1; created_figure_no < 0xC9; created_figure_no++) {
        if (figure_list[created_figure_no].exists == 0) {
            figure_list[created_figure_no].exists = 1;
            figure_list[created_figure_no].owner = owner;
            base_x = base_x + off_x;
            base_y = base_y + off_y;
            figure_list[created_figure_no].grid_x = base_x;
            figure_list[created_figure_no].grid_y = base_y;
            figure_list[created_figure_no].map_ref = (base_x + base_y * 0x34) * 4;
            if (((unsigned char *)battle_map)[figure_list[created_figure_no].map_ref + 1] != 0)
                return 0;
            ((unsigned char *)battle_map)[figure_list[created_figure_no].map_ref + 1] = created_figure_no;
            figure_list[created_figure_no].sprite_type = sprite_type;
            figure_list[created_figure_no].unit_ref = unit_no;
            figure_list[created_figure_no].unit_type = unit_list[unit_no].fig_count;
            figure_list[created_figure_no].offset_x = off_x;
            figure_list[created_figure_no].offset_y = off_y;
            if (unit_list[unit_no].heading == -1)
                figure_list[created_figure_no].direction = 4;
            else
                figure_list[created_figure_no].direction = 0;
            figure_list[created_figure_no].anim_state = figure_list[created_figure_no].direction;
            figure_list[created_figure_no].prev_grid_x = base_x;
            figure_list[created_figure_no].prev_grid_y = base_y;
            figure_list[created_figure_no].is_visible = 1;
            return 1;
        }
    }
    return 0;
}

// FUNCTION: C2 0x2AE0E
// WIN: 0x00469d49
// Lines 192–215
// (CAESAR2.EXE 0x00469d49 refs arrow_no/created_arrow_no — create_arrow.)
int create_arrow(unsigned char *arrow_data_ptr, int owner, int sx, int sy, int ex, int ey)
{
    for (created_arrow_no = 1; created_arrow_no < 0xC9; created_arrow_no++) {
        if (arrow_list[created_arrow_no].exists == 0) {
            arrow_list[created_arrow_no].exists = 1;
            arrow_list[created_arrow_no].owner = owner;
            arrow_list[created_arrow_no].end_x = ex * 7;
            arrow_list[created_arrow_no].end_y = ey * 7;
            arrow_list[created_arrow_no].start_x = (short)sx * 7;
            arrow_list[created_arrow_no].start_y = sy * 7;
            arrow_list[created_arrow_no].grid_x = sx;
            arrow_list[created_arrow_no].grid_y = sy;
            arrow_list[created_arrow_no].map_ref = (arrow_list[created_arrow_no].grid_x + arrow_list[created_arrow_no].grid_y * 0x34) * 4;
            arrow_list[created_arrow_no].heading = get_heading(sx, sy, ex, ey, 0);
            arrow_list[created_arrow_no].arrow_data_ptr = arrow_data_ptr;
            arrow_list[created_arrow_no].anim_count = 0;
            arrow_no = created_arrow_no;
            init_bd(arrow_list[created_arrow_no].start_x, arrow_list[created_arrow_no].start_y,
                    arrow_list[created_arrow_no].end_x, arrow_list[created_arrow_no].end_y);
            return 1;
        }
    }
    high_beep();
    return 0;
}

// FUNCTION: C2 0x2AF5A
// WIN: 0x00469f7e  (unverified)
// Lines 221–225
void clear_citizen(struct citizen_rec *p)
{
    unsigned int i;
    char *bytes = (char *)p;
    for (i = 0; i < sizeof(struct citizen_rec); i++) {
        bytes[i] = 0;
    }
}

// FUNCTION: C2 0x2AF6D
// WIN: 0x00469f9c  (unverified)
// Lines 226–230
void clear_army(struct army_rec *p)
{
    unsigned int i;
    char *bytes = (char *)p;
    for (i = 0; i < sizeof(struct army_rec); i++) {
        bytes[i] = 0;
    }
}

// FUNCTION: C2 0x2AFBC
// Lines 231–235 — SOURCE POSITION IS LOAD-BEARING (Rule 125, haul-DOWN).
//
// The symbol 0x2AFBC is the HAULED HEAD, not the source position.  The
// "orphan tail" at clear_army+0x15 (0x2AF82, 10 bytes: a 0x4E-byte
// clear loop + pop/ret with no prologue) is THIS function's body:
// clear_unit is defined HERE in PS source (lines 231-235, right after
// clear_army — its body's surviving line records L234/L235 at
// 0x2AF82/0x2AF8C prove it; the head lines' records were orphaned and
// collapsed per Rule 125).  remove_unit's tail call
// `clear_unit(&unit_list[n])` became `jmp clear_unit` (CallRet) and
// StraightenCode "pushed the code down to the jump": clear_unit's head
// (entry label; push ebx; mov ebx,eax; xor eax,eax; jmp Lcmp — label
// through first unconditional jmp) moved into remove_unit at 0x2AFBC,
// jumping BACK to the loop left behind at 0x2AF87.  The entry label —
// and therefore the PUBDEF symbol — traveled with the moved head,
// which is why clear_unit's symbol sits inside remove_unit's range.
void clear_unit(struct unit_rec *p)
{
    unsigned int i;
    char *bytes = (char *)p;
    for (i = 0; i < sizeof(struct unit_rec); i++) {
        bytes[i] = 0;
    }
}

// FUNCTION: C2 0x2AF8E
// WIN: 0x00469fb7  (unverified)
// Lines 236–240
void clear_figure(struct figure_rec *p)
{
    unsigned int i;
    char *bytes = (char *)p;
    for (i = 0; i < sizeof(struct figure_rec); i++) {
        bytes[i] = 0;
    }
}

// FUNCTION: C2 0x2AFA1
// WIN: 0x00469fd2  (unverified)
// Lines 241–245
void clear_arrow(struct arrow_rec *p)
{
    unsigned int i;
    char *bytes = (char *)p;
    for (i = 0; i < sizeof(struct arrow_rec); i++) {
        bytes[i] = 0;
    }
}

// FUNCTION: C2 0x2AFB4
// WIN: 0x00469fed
// Lines 247–247
//
// PS emits imul/add then falls into clear_unit's hauled-down head (see
// the static clear_unit above, Rule 125).
void remove_unit(int n)
{
    clear_unit(&unit_list[n]);
}

// FUNCTION: C2 0x2AFC3
// WIN: 0x0046a016
// Lines 248–252
void remove_figure(int n)
{
    char zero = 0;
    int ref = figure_list[n].map_ref;
    ((unsigned char *)battle_map)[(ref) + 1] = zero;
    clear_figure(&figure_list[n]);
}

// FUNCTION: C2 0x2AFE3
// Lines 255–260
void remove_citizen(int n)
{
    char zero = 0;
    int ref = citizen_list[n].map_ref;
    if (CM_CELL((ref)).citizen_a == n) {
        CM_CELL((ref)).citizen_a = zero;
    } else if (CM_CELL((ref)).citizen_b == n) {
        CM_CELL((ref)).citizen_b = zero;
    }
    clear_citizen(&citizen_list[n]);
}

// FUNCTION: C2 0x2B02A
// WIN: 0x0046a102
// Lines 262–266
void remove_army(int n)
{
    char zero = 0;
    int ref = army_list[n].map_ref;
    RM_CELL(ref).occupant = zero;
    clear_army(&army_list[n]);
}

// FUNCTION: C2 0x2B04D
// WIN: 0x0046a146
// Lines 269–273
void clear_unit_list(void)
{
    for (unit_no = 1; unit_no < 0x33; unit_no++) {
        clear_unit(&unit_list[unit_no]);
    }
}

// FUNCTION: C2 0x2B079
// WIN: 0x0046a19d
// Lines 274–278
void clear_figure_list(void)
{
    for (figure_no = 1; figure_no < 0xC9; figure_no++) {
        clear_figure(&figure_list[figure_no]);
    }
}

// FUNCTION: C2 0x2B0A7
// WIN: 0x0046a1f3
// Lines 279–283
void clear_arrow_list(void)
{
    for (arrow_no = 1; arrow_no < 0xC9; arrow_no++) {
        clear_arrow(&arrow_list[arrow_no]);
    }
}

// FUNCTION: C2 0x2B0E3
// WIN: 0x0046a245
// Lines 287–311
void check_citizen_list(void)
{
    int i;
    /* Clear citizen slots in city_map (unrolled 4x, 20 bytes/cell) */
    i = 0;
    do {
        CM_CELL((i)).citizen_a = 0;
        CM_CELL((i)).citizen_b = 0;
        CM_CELL((i + 1 * CITY_CELL_BYTES)).citizen_a = 0;
        CM_CELL((i + 1 * CITY_CELL_BYTES)).citizen_b = 0;
        CM_CELL((i + 2 * CITY_CELL_BYTES)).citizen_a = 0;
        CM_CELL((i + 2 * CITY_CELL_BYTES)).citizen_b = 0;
        CM_CELL((i + 3 * CITY_CELL_BYTES)).citizen_a = 0;
        CM_CELL((i + 3 * CITY_CELL_BYTES)).citizen_b = 0;
        i += 80;
    } while (i < 128000);
    /* Re-assign citizens to their map cells */
    for (citizen_no = 1; citizen_no < 201; citizen_no++) {
        if (citizen_list[citizen_no].exists != 0) {
            int ref = citizen_list[citizen_no].map_ref;
            citizen_a = (unsigned char)CM_CELL((ref)).citizen_a;
            citizen_b = (unsigned char)CM_CELL((ref)).citizen_b;
            if (citizen_a == 0) {
                CM_CELL((ref)).citizen_a = citizen_no;
            } else if (citizen_b == 0) {
                CM_CELL((ref)).citizen_b = citizen_no;
            } else {
                clear_citizen(&citizen_list[citizen_no]);
            }
        }
    }
}

// FUNCTION: C2 0x2B1BA
// WIN: 0x0046a3ed
// Lines 313–337
void check_army_list(void)
{
    int i;
    /* Clear army slots in region_map where terrain bit 0 is clear (unrolled 4x, 8 bytes/cell) */
    i = 0;
    do {
        if ((RM_CELL(i).terrain & 1) == 0)
            RM_CELL(i).occupant = 0;
        if ((RM_CELL(i + 8).terrain & 1) == 0)
            RM_CELL(i + 8).occupant = 0;
        if ((RM_CELL(i + 16).terrain & 1) == 0)
            RM_CELL(i + 16).occupant = 0;
        if ((RM_CELL(i + 24).terrain & 1) == 0)
            RM_CELL(i + 24).occupant = 0;
        i += 32;
    } while (i < 28800);
    /* Re-assign armies to their map cells */
    for (army_no = 1; army_no < 26; army_no++) {
        if (army_list[army_no].exists != 0) {
            army_a = (unsigned char)RM_CELL(army_list[army_no].map_ref).occupant;
            if (army_a == 0) {
                RM_CELL(army_list[army_no].map_ref).occupant = army_no;
            }
        }
    }
}

// FUNCTION: C2 0x2B282
// WIN: 0x0046a551
// Lines 339–344
void clear_citizen_list(void)
{
    for (citizen_no = 1; citizen_no < 0xC9; citizen_no++) {
        remove_citizen(citizen_no);
    }
}

// FUNCTION: C2 0x2B2A8
// WIN: 0x0046a59b
// Lines 346–351
void clear_army_list(void)
{
    for (army_no = 1; army_no < 0x1A; army_no++) {
        remove_army(army_no);
    }
}

// FUNCTION: C2 0x2B2CC
// WIN: 0x0046a5e3
// Lines 353–361
void army_restoring_adjusts(void)
{
    for (army_no = 0; army_no < 0x1A; army_no++) {
        if (army_list[army_no].exists != 0) {
            if (army_list[army_no].exists == 2) {
                army_list[army_no].exists = 0;
            } else if (army_list[army_no].exists == 3) {
                army_list[army_no].exists = 1;
            }
        }
    }
}

// FUNCTION: C2 0x2B31D
// WIN: 0x0046a6b4
// Lines 363–372
int any_army_building_adjusts(void)
{
    int result = 0;
    for (army_no = 0; army_no < 0x1A; army_no++) {
        if (army_list[army_no].exists == 2) {
            army_list[army_no].exists = 1;
        }
        if (army_list[army_no].exists == 3) {
            result = 1;
        }
    }
    return result;
}

// FUNCTION: C2 0x2B37B
// WIN: 0x0046a75f
// Lines 374–378
void army_building_adjusts(void)
{
    for (army_no = 0; army_no < 0x1A; army_no++) {
        if (army_list[army_no].exists == 3) {
            remove_army(army_no);
        }
    }
}

// FUNCTION: C2 0x2B3B3
// WIN: 0x0046a7c6
// Lines 380–387
void clear_army_from_fort_ref(int ref)
{
    for (army_no = 0; army_no < 26; army_no++) {   // Watcom preserves <26 vs <=25 literally
        if (army_list[army_no].exists != 0 && ref == army_list[army_no].fort_ref) {
            army_list[army_no].exists = 3;
            return;
        }
    }
}

// FUNCTION: C2 0x2B3F9
// WIN: 0x0046a85b
// Lines 389–396
int get_army_name_from_fort_ref(int ref)
{
    int result;
    /* No-match path returns whatever EBX holds on entry (PS bug:
       no explicit init).  Matches PS asm where EBX is only written
       inside the match branch.  Callers guarantee a match. */
    for (army_no = 0; army_no < 26; army_no++) {     // Rule 4
        if (army_list[army_no].exists != 0 && ref == army_list[army_no].fort_ref) {
            result = army_list[army_no].cohort_id;           /* signed-char movsx */
            return result;
        }
    }
    return result;
}

// FUNCTION: C2 0x2B442
// WIN: 0x0046a8f0
// Lines 398–412
int get_nearest_army_to_track(int x, int y)
{
    int dist;
    int best = 9999;
    for (army_no = 0; army_no < 26; army_no++) {
        if (army_list[army_no].exists != 0 && army_list[army_no].type == 1
            && army_list[army_no].map_x != 0 && army_list[army_no].map_y != 0) {
            dist = get_longest_distance(army_list[army_no].map_x,
                                        army_list[army_no].map_y, x, y);
            if (dist < best) {
                tracking_army = army_no;
                best = dist;
            }
        }
    }
    return best;
}

// FUNCTION: C2 0x2B4CB
// WIN: 0x0046aa26
// Lines 414–426
int get_nearest_enemy_to_track(int x, int y)
{
    int dist;
    int best = 9999;
    for (army_no = 0; army_no < 26; army_no++) {
        if (army_list[army_no].exists != 0
            && army_list[army_no].type >= 2                /* Rule 4 */
            && army_list[army_no].type <= 5
            && army_list[army_no].map_x != 0 && army_list[army_no].map_y != 0) {
            dist = get_longest_distance(army_list[army_no].map_x,
                                        army_list[army_no].map_y, x, y);
            if (dist < best) {
                hunting_army = army_no;
                best = dist;
            }
        }
    }
    return best;
}

// FUNCTION: C2 0x2B557
// WIN: 0x0046ab7e
// Lines 430–436
int get_tracking_army_distance(int n, int x, int y)
{
    if (army_list[n].map_x == 0 || army_list[n].map_y == 0) return 999;
    return get_longest_distance(army_list[n].map_x,
                                army_list[n].map_y, x, y);
}

// FUNCTION: C2 0x2B593
// WIN: 0x0046ac17
// Lines 442–442
int get_a_unit_centered_on_mouse(void)
{
    if (mouse_left_preclick == 0) {
        return 0;
    }
    temp_unit = find_figure(1);
    return temp_unit;
}

// FUNCTION: C2 0x2B59C
// (no confirmed CAESAR2.EXE slot; old 0x00482825 was a placeholder magnet.)
// Lines 446–448
int find_figure(int mode)
{
    return 0;
}

// FUNCTION: C2 0x2B5B1
// WIN: 0x0046ac54
// Lines 450–458
int get_a_shootable_unit(void)
{
    for (temp_unit = 1; temp_unit < 0x33; temp_unit++) {
        unit_list[temp_unit].is_target = 0;
    }
    temp_unit = find_figure(0);
    unit_list[temp_unit].is_target = 1;
    return temp_unit;
}

// FUNCTION: C2 0x2B5F5
// Lines 488–510
heading_t get_heading(int sx, int sy, int ex, int ey, char mode)
{
    heading_t heading;
    if (sx > ex) {                                     /* PS: cmp eax,ebx; jle (Rule 4) */
        if (sy > ey) heading = HEADING_NW;
        else if (sy == ey) heading = HEADING_W;
        else if (sy < ey) heading = HEADING_SW;
    } else if (sx == ex) {
        if (sy > ey) heading = HEADING_N;
        else if (sy == ey) heading = mode + HEADING_STILL;
        else if (sy < ey) heading = HEADING_S;
    } else if (sx < ex) {
        if (sy > ey) heading = HEADING_NE;
        else if (sy == ey) heading = HEADING_E;
        else if (sy < ey) heading = HEADING_SE;
    }
    return heading;
}

// FUNCTION: C2 0x2B662
// WIN: 0x0046ae0d
// Lines 564–621
void clear_ferret_map(int margin, unsigned char *map_base, int map_wi, int map_hi,
                      int cell_size, int x1, int y1, int x2, int y2)
{
    /* Decl order is load-bearing (Rule 115/107): y-pair before x-pair,
     * and ey before ex, reproduce PS's parm homes (x1=ebx y1=esi x2=edx,
     * y2 memory) + spill-slot layout.  Shape from Mac PPC build. */
    int miny;
    int maxy;
    int minx;
    int maxx;
    int sx;
    int sy;
    int ey;
    int ex;
    int ptr;
    int x;
    int y;
    int tmp;
    unsigned char terrain;
    unsigned char val;

    if (x1 <= x2) {
        minx = x1;
        maxx = x2;
    } else {
        minx = x2;
        maxx = x1;
    }
    if (y1 <= y2) {
        miny = y1;
        maxy = y2;
    } else {
        miny = y2;
        maxy = y1;
    }
    sx = minx - margin;
    sy = miny - margin;
    ex = maxx + margin;
    ey = maxy + margin;
    if (sx < 0) sx = 0;
    if (sy < 0) sy = 0;
    if (ex >= map_wi) ex = map_wi - 1;
    if (ey >= map_hi) ey = map_hi - 1;

    ptr = cell_size * (sx + sy * map_wi);
    for (y = sy; y <= ey; y++, ptr += map_wi * cell_size) {
        for (x = sx, tmp = ptr; x <= ex; x++, tmp += cell_size) {
            if (y == sy)
                val = 0xFF;
            else if (y == ey)
                val = 0xFF;
            else if (x == sx)
                val = 0xFF;
            else if (x == ex)
                val = 0xFF;
            else {
                val = 0;
                terrain = *(map_base + tmp + 1);
                if ((terrain & 1) != 0) {
                    val = 0xFE;
                } else if ((terrain & 4) != 0) {
                    if (citizen_list[citizen_no].type == 3) {
                        val = 0xFE;
                    } else if ((terrain & 0x20) != 0) {
                        *(map_base + tmp + 6) = 0;
                        *(map_base + tmp + 5) = 1;
                    } else {
                        val = 0xFE;
                    }
                } else {
                    *(map_base + tmp + 6) = 0;
                    if ((terrain & 0x20) != 0) {
                        *(map_base + tmp + 5) = 1;
                    } else if (terrain != 0) {
                        val = 0xFE;
                        *(map_base + tmp + 5) = 0;
                    } else {
                        *(map_base + tmp + 5) = 2;
                    }
                }
            }
            *(map_base + tmp + 2) = val;
        }
    }
}

// FUNCTION: C2 0x2B7E0
// WIN: 0x0046b083
// Lines 624–708
void clear_region_ferret_map(int mode, int margin, unsigned char *map_base, int map_wi,
                             int map_hi, int cell_size, int x1, int y1,
                             int x2, int y2)
{
    /* Shape from the Mac PPC build (c2 mac-fn), semantics confirmed against
     * PS x86: separate else-if val chains (no &&/goto funnels), cell0/cell7
     * loaded up-front as byte locals, no cached cell pointer, and a dead
     * re-test of (terrain & 8) in the tail that PS's CSE hoists. */
    int maxy;
    int miny;
    int minx;
    int maxx;
    int sx;
    int sy;
    int ey;
    int ex;
    int ptr;
    int tmp;
    int x;
    int y;
    unsigned char terrain;
    unsigned char val;
    unsigned char cell0;
    unsigned char cell7;

    if (x1 <= x2) {
        minx = x1;
        maxx = x2;
    } else {
        minx = x2;
        maxx = x1;
    }
    if (y1 <= y2) {
        miny = y1;
        maxy = y2;
    } else {
        miny = y2;
        maxy = y1;
    }
    sx = minx - margin;
    sy = miny - margin;
    ex = maxx + margin;
    ey = maxy + margin;
    if (sx < 0) sx = 0;
    if (sy < 0) sy = 0;
    if (ex >= map_wi) ex = map_wi - 1;
    if (ey >= map_hi) ey = map_hi - 1;

    ptr = cell_size * (sx + sy * map_wi);
    for (y = sy; y <= ey; y++, ptr += map_wi * cell_size) {
        for (x = sx, tmp = ptr; x <= ex; x++, tmp += cell_size) {
            if (y == sy)
                val = 0xFF;
            else if (y == ey)
                val = 0xFF;
            else if (x == sx)
                val = 0xFF;
            else if (x == ex)
                val = 0xFF;
            else {
                val = 0;
                terrain = *(map_base + tmp + 1);
                cell0 = *(map_base + tmp);
                cell7 = *(map_base + tmp + 7);

                *(map_base + tmp + 6) = 0;
                *(map_base + tmp + 5) = 0;
                if ((terrain & 1) != 0) {
                    if (army_list[army_no].type == 1) {
                        val = 0xFE;
                    } else if (cell0 >= 0x93 && cell0 <= 0x9B) {
                        val = 0xFE;
                    } else {
                        *(map_base + tmp + 5) = 1;
                    }
                } else if ((terrain & 4) != 0) {
                    if (army_list[army_no].type == 1) {
                        *(map_base + tmp + 5) = 1;
                    } else {
                        val = 0xFE;
                    }
                } else if ((terrain & 2) != 0) {
                    if (army_list[army_no].type == 1) {
                        if ((terrain & 0x20) != 0) {
                            *(map_base + tmp + 5) = 1;
                        } else {
                            val = 0xFE;
                        }
                    } else if (mode != 0) {
                        *(map_base + tmp + 5) = 1;
                    } else {
                        val = 0xFE;
                    }
                } else if ((terrain & 0x20) != 0) {
                    *(map_base + tmp + 5) = 1;
                } else if ((terrain & 8) != 0) {
                    if ((terrain & 0x10) != 0) {
                        val = 0xFE;
                    } else if (army_list[army_no].type != 1) {
                        val = 0xFE;
                    } else if (army_list[army_no].state_idx != 4) {
                        val = 0xFE;
                    } else if (cell7 == 0) {
                        val = 0xFE;
                    } else if (cell7 != army_list[army_no].army_id) {
                        val = 0xFE;
                    } else {
                        *(map_base + tmp + 5) = 2;
                    }
                } else if ((terrain & 0x10) != 0) {
                    val = 0xFE;
                } else if ((terrain & 8) != 0) {
                    val = 0xFE;
                } else {
                    *(map_base + tmp + 5) = 2;
                }
            }
            *(map_base + tmp + 2) = val;
        }
    }
}

// FUNCTION: C2 0x2BA5E
// Lines 711–757
void clear_sea_ferret_map(int unused, int margin, unsigned char *map_base, int map_wi,
                          int map_hi, int cell_size, int x1, int y1,
                          int x2, int y2)
{
    int miny;
    int maxy;
    int minx;
    int maxx;
    int sx;
    int sy;
    int ey;
    int ex;
    int ptr;
    int tmp;
    int x;
    int y;
    unsigned char terrain;
    unsigned char val;

    if (x1 <= x2) {
        minx = x1;
        maxx = x2;
    } else {
        minx = x2;
        maxx = x1;
    }
    if (y1 <= y2) {
        miny = y1;
        maxy = y2;
    } else {
        miny = y2;
        maxy = y1;
    }
    sx = minx - margin;
    sy = miny - margin;
    ex = maxx + margin;
    ey = maxy + margin;
    if (sx < 0) sx = 0;
    if (sy < 0) sy = 0;
    if (ex >= map_wi) ex = map_wi - 1;
    if (ey >= map_hi) ey = map_hi - 1;

    ptr = cell_size * (sx + sy * map_wi);
    for (y = sy; y <= ey; y++, ptr += map_wi * cell_size) {
        for (x = sx, tmp = ptr; x <= ex; x++, tmp += cell_size) {
            if (y == sy)
                val = 0xFF;
            else if (y == ey)
                val = 0xFF;
            else if (x == sx)
                val = 0xFF;
            else if (x == ex)
                val = 0xFF;
            else {
                val = 0xFE;
                terrain = *(map_base + tmp + 1);
                *(map_base + tmp + 6) = 0;
                *(map_base + tmp + 5) = 0;
                if ((terrain & 0x10) != 0) {
                    if ((terrain & 8) != 0) {
                        val = 0;
                        *(map_base + tmp + 5) = 1;
                    }
                }
            }
            *(map_base + tmp + 2) = val;
        }
    }
}

// FUNCTION: C2 0x2BB7B
// WIN: 0x0046b68b
// Lines 759–802
int run_2_map_ferrets(int param1, unsigned char *map_base, int map_wi, int map_hi,
                      int cell_size, int start_x, int start_y,
                      int targ_x, int targ_y)
{
    int i;

    anti_ferret_x = start_x;
    clock_ferret_x = start_x;
    anti_ferret_y = start_y;
    clock_ferret_y = start_y;
    anti_ferret_ptr = cell_size * (start_y * map_wi + start_x);
    clock_ferret_ptr = anti_ferret_ptr;
    anti_ferret_running = 1;
    clock_ferret_running = 1;
    anti_ferret_count = *(map_base + clock_ferret_ptr + 5) + 1;
    clock_ferret_count = anti_ferret_count;
    *(map_base + clock_ferret_ptr + 2) = 1;
    ferret_energy = 200;
    ferret_home = 0;
    ferret_horiz_off = cell_size;
    ferret_vert_off = cell_size * map_wi;
    ferret_targ_x = targ_x;
    ferret_targ_y = targ_y;
    ferret_targ_ptr = cell_size * (targ_y * map_wi + targ_x);
    ferret_map_wi = map_wi;
    ferret_map_hi = map_hi;
    ferret_map = map_base;
    last_clock_ferret_dirc = 0;
    last_anti_ferret_dirc = 0;

    while (clock_ferret_running != 0 || anti_ferret_running != 0) {
        run_clock_ferret();
        run_anti_ferret();
        if (ferret_home != 0) break;
        ferret_energy--;
        if (ferret_energy <= 0) break;              // Rule 4 (enables `test`)
    }

    for (i = 0; i < 20; i++)
        ferret_run[i] = 0;                          /* Watcom lowers this to `call __STOSB` */

    if (ferret_home != 0) {
        smooth_ferret_run(param1, map_base, map_wi, map_hi,
                          cell_size, start_x, start_y, targ_x, targ_y);
        if (trace_back_ferret() != 0) {
            load_ferret_run(start_x, start_y, 20);
            return 1;
        }
    }
    return 0;
}

// FUNCTION: C2 0x2BCEB
// WIN: 0x0046b875
// Lines 804–825
void load_ferret_run(int x, int y, int max_len)
{
    unsigned char dir;
    unsigned char back;

    ferret_run_length = 0;
    tb_x = x;
    tb_y = y;
    tb_ptr = (x + y * ferret_map_wi) * ferret_horiz_off;
    back = 8;
    while (max_len > ferret_run_length) {
        for (dir = 0; dir < 8; dir++) {
            if (get_ferret2(dir) == 1 && dir != back) break;
        }
        if (dir >= 8) return;
        back = (dir + 4) % 8;
        ferret_run[ferret_run_length++] = dir;
        move_to_tb_value(dir);
    }
}

// FUNCTION: C2 0x2BD7C
// WIN: 0x0046b96b
// Lines 827–885
void smooth_ferret_run(int margin, unsigned char *map_base, int map_wi, int map_hi,
                       int cell_size, int x1, int y1, int x2, int y2)
{
    int minx;
    int miny;
    int maxx;
    int maxy;
    int sx;
    int sy;
    int ey;
    int ex;
    int ptr;
    int dir;
    unsigned char saved_targ;
    unsigned char cur_val;
    unsigned char best_val;
    unsigned char tb_val;
    unsigned char slot2;
    unsigned char slot1;

    saved_targ = *(map_base + ferret_targ_ptr + 2);

    if (x1 <= x2) {
        minx = x1;
        maxx = x2;
    } else {
        minx = x2;
        maxx = x1;
    }
    if (y1 <= y2) {
        miny = y1;
        maxy = y2;
    } else {
        miny = y2;
        maxy = y1;
    }
    sx = minx - margin;
    sy = miny - margin;
    ex = maxx + margin;
    ey = maxy + margin;
    if (sx < 0) sx = 0;
    if (sy < 0) sy = 0;
    if (ex >= map_wi) ex = map_wi - 1;
    if (ey >= map_hi) ey = map_hi - 1;

    ptr = (sx + sy * map_wi) * cell_size;
    for (tb_y = sy; tb_y <= ey; tb_y++, ptr += map_wi * cell_size) {
        for (tb_x = sx, tb_ptr = ptr; tb_x <= ex; tb_x++, tb_ptr += cell_size) {
            cur_val = *(map_base + tb_ptr + 2);
            slot1 = *(map_base + tb_ptr + 7);
            slot2 = *(map_base + tb_ptr + 8);
            if (cur_val < 0xFE) {
                if (cur_val == 0) {
                    best_val = 0xFA;
                } else {
                    best_val = cur_val;
                }
                for (dir = 0; dir < 8; dir++) {
                    tb_val = get_tb_value(dir);
                    if (tb_val < 0xFE && tb_val != 0) {
                        if (tb_road_flag == 1) {
                            tb_val++;
                        } else if (tb_road_flag == 2) {
                            tb_val += 2;
                        } else {
                            continue;
                        }
                        if (tb_val < best_val) {
                            best_val = tb_val;
                        }
                    }
                }
                if (cur_val == 0 || best_val != cur_val) {
                    *(map_base + tb_ptr + 2) = best_val;
                    if (slot1 != 0 && slot2 != 0) {
                        *(map_base + tb_ptr + 2) = 0xFE;
                    }
                }
            }
        }
    }
    *(map_base + ferret_targ_ptr + 2) = saved_targ;
}

// FUNCTION: C2 0x2BF23
// WIN: 0x0046bc3b
// Lines 887–918
int trace_back_ferret(void)
{
    unsigned char cur_val;
    unsigned char best_val;
    int best_dir;
    int dir;
    int energy;

    tb_x = ferret_targ_x;
    tb_y = ferret_targ_y;
    tb_ptr = (ferret_targ_x + ferret_targ_y * ferret_map_wi) * ferret_horiz_off;
    cur_val = *(ferret_map + tb_ptr + 2);
    *(ferret_map + tb_ptr + 6) = 1;
    energy = 100;

    while (cur_val > 1) {
        energy--;
        if (energy < 0) return 0;
        cur_val++;                             /* PS: inc bh; mov bl, bh */
        best_val = cur_val;
        best_dir = 0;
        for (dir = 0; dir < 8; dir++) {
            unsigned char val = get_tb_value(dir);
            if (val != 0) {
                if (val < best_val) {
                    best_val = val;
                    best_dir = dir;
                } else if (val == best_val && tb_road_flag == 1) {
                    best_dir = dir;
                }
            }
        }
        if (best_val == cur_val) return 0;      /* cur_val was pre-incremented */
        cur_val = best_val;
        move_to_tb_value(best_dir);
    }
    return 1;
}

// FUNCTION: C2 0x2BFCA
// WIN: 0x0046bd96
// Lines 920–947
int trace_forward_ferret(int steps)
{
    unsigned char cur_val;
    unsigned char best_val;
    int best_dir;
    int dir;

    tb_x = clock_ferret_x;
    tb_y = clock_ferret_y;
    tb_ptr = clock_ferret_ptr;
    cur_val = *(ferret_map + tb_ptr + 2);
    *(ferret_map + tb_ptr + 6) = 1;

    while (steps-- > 0) {
        best_val = cur_val;
        best_dir = 0;
        for (dir = 0; dir < 8; dir++) {
            unsigned char val = get_tb_value(dir);
            if (val != 0 && val < 0xFE) {
                if (val > best_val) { best_val = val; best_dir = dir; }
                else if (val == best_val && tb_road_flag == 1) best_dir = dir;
            }
        }
        if (best_val == cur_val) return 0;
        cur_val = best_val;
        move_to_tb_value(best_dir);
    }
    return 1;
}

// FUNCTION: C2 0x2C062
// WIN: 0x0046bedd
// Lines 950–992
void run_clock_ferret(void)
{
    unsigned char heading;
    int result;
    int count;
    int dir;

    if (clock_ferret_running == 0) return;

    heading = ferret_heading(clock_ferret_x, clock_ferret_y);
    if (heading == 8) {
        ferret_home = 1;
        return;
    }

    dir = heading;
    count = 0;
    /* NB: the `(signed char)dir` casts below are LOAD-BEARING, not
     * redundant: move_clock_ferret / check_clock_ferret_move are called
     * here BEFORE their definitions (unprototyped), so the cast is the
     * only thing narrowing `dir` (int) to the callee's signed-char
     * width.  Dropping it regresses byte-exactness (a width divergence);
     * decl-audit flags it as "cast == real param" but do NOT remove. */
    do {
        result = (unsigned char)check_clock_ferret_move((signed char)dir);
        if (tb_occ_a_flag != 0 && tb_occ_b_flag != 0) result = 0xFE;
        if (result == 0xFF) { clock_ferret_running = 0; return; }
        if (result == 0) {
            move_clock_ferret((signed char)dir, 0);
            last_clock_ferret_dirc = dir;
            return;
        }
        if (++dir >= 8) dir = 0;
    } while (++count < 8);

    dir = last_clock_ferret_dirc;
    count = 0;
    do {
        result = (unsigned char)check_clock_ferret_move((signed char)dir);
        if (tb_occ_a_flag != 0 && tb_occ_b_flag != 0) result = 0xFE;
        if (result < 0xFE && tb_prev_flag == 0) {
            move_clock_ferret((signed char)dir, 1);
            *(ferret_map + clock_ferret_ptr + 5) |= 0x80;
            return;
        }
        if (++dir >= 8) dir = 0;
    } while (++count < 8);

    count = 0;
    do {
        result = (unsigned char)check_clock_ferret_move((signed char)dir);
        if (result < 0xFE) {
            move_clock_ferret((signed char)dir, 1);
            return;
        }
        if (++dir >= 8) dir = 0;
    } while (++count < 8);
    clock_ferret_running = 0;
}

// FUNCTION: C2 0x2C1AB
// WIN: 0x0046c10f
// Lines 994–1036
void run_anti_ferret(void)
{
    unsigned char heading;
    int result;
    int count;
    int dir;

    if (anti_ferret_running == 0) return;

    heading = ferret_heading(anti_ferret_x, anti_ferret_y);
    if (heading == 8) {
        ferret_home = 1;
        return;
    }

    dir = heading;
    count = 0;
    do {
        result = (unsigned char)check_anti_ferret_move((signed char)dir);
        if (tb_occ_a_flag != 0 && tb_occ_b_flag != 0) result = 0xFE;
        if (result == 0xFF) { anti_ferret_running = 0; return; }
        if (result == 0) {
            move_anti_ferret((signed char)dir, 0);
            last_anti_ferret_dirc = dir;
            return;
        }
        if (--dir < 0) dir = 7;
    } while (++count < 8);

    dir = last_anti_ferret_dirc;
    count = 0;
    do {
        result = (unsigned char)check_anti_ferret_move((signed char)dir);
        if (tb_occ_a_flag != 0 && tb_occ_b_flag != 0) result = 0xFE;
        if (result < 0xFE && tb_prev_flag == 0) {
            move_anti_ferret((signed char)dir, 1);
            *(ferret_map + anti_ferret_ptr + 5) |= 0x40;
            return;
        }
        if (--dir < 0) dir = 7;
    } while (++count < 8);

    count = 0;
    do {
        result = (unsigned char)check_anti_ferret_move((signed char)dir);
        if (result < 0xFE) {
            move_anti_ferret((signed char)dir, 1);
            return;
        }
        if (--dir < 0) dir = 7;
    } while (++count < 8);
    anti_ferret_running = 0;
}

// FUNCTION: C2 0x2C31B
// WIN: 0x0046c335
// Lines 1038–1104
/* BYTE-EXACT 2026-06-12 (was 686 b).  Shape from Mac PPC + PS x86:
 * per-case inline cell reads, tb_prev_flag = cell[5] & 0x80, and — THE
 * lever — every bounds check is an inline `return -1;` (Mac: one
 * `li r3,0xff; b end` PER site), NOT a `break` to a shared return.
 * The old "Rule 111 value-number overflow" theory was wrong: the
 * control-flow shape of the per-site returns is what reproduces PS's
 * per-case CSE pattern (ingredient recompute in early cases, cached
 * address in later ones) and the cross-function tail-merge of the
 * return -1 block. */
signed char check_clock_ferret_move(signed char dir)
{
    switch (dir) {
    case 0:
        if (clock_ferret_y <= 0) return -1;
        tb_prev_flag = *(ferret_map + clock_ferret_ptr - ferret_vert_off + 5) & 0x80;
        tb_occ_a_flag = *(ferret_map + clock_ferret_ptr - ferret_vert_off + 7);
        tb_occ_b_flag = *(ferret_map + clock_ferret_ptr - ferret_vert_off + 8);
        if (clock_ferret_ptr - ferret_vert_off == ferret_targ_ptr) tb_occ_a_flag = 0;
        return *(ferret_map + clock_ferret_ptr - ferret_vert_off + 2);
    case 1:
        if (clock_ferret_y <= 0) return -1;
        if (ferret_map_wi - 1 <= clock_ferret_x) return -1;
        tb_prev_flag = *(ferret_map + clock_ferret_ptr - ferret_vert_off + ferret_horiz_off + 5) & 0x80;
        tb_occ_a_flag = *(ferret_map + clock_ferret_ptr - ferret_vert_off + ferret_horiz_off + 7);
        tb_occ_b_flag = *(ferret_map + clock_ferret_ptr - ferret_vert_off + ferret_horiz_off + 8);
        if (clock_ferret_ptr - ferret_vert_off + ferret_horiz_off == ferret_targ_ptr) tb_occ_a_flag = 0;
        return *(ferret_map + clock_ferret_ptr - ferret_vert_off + ferret_horiz_off + 2);
    case 2:
        if (ferret_map_wi - 1 <= clock_ferret_x) return -1;
        tb_prev_flag = *(ferret_map + clock_ferret_ptr + ferret_horiz_off + 5) & 0x80;
        tb_occ_a_flag = *(ferret_map + clock_ferret_ptr + ferret_horiz_off + 7);
        tb_occ_b_flag = *(ferret_map + clock_ferret_ptr + ferret_horiz_off + 8);
        if (clock_ferret_ptr + ferret_horiz_off == ferret_targ_ptr) tb_occ_a_flag = 0;
        return *(ferret_map + clock_ferret_ptr + ferret_horiz_off + 2);
    case 3:
        if (ferret_map_hi - 1 <= clock_ferret_y) return -1;
        if (ferret_map_wi - 1 <= clock_ferret_x) return -1;
        tb_prev_flag = *(ferret_map + clock_ferret_ptr + ferret_vert_off + ferret_horiz_off + 5) & 0x80;
        tb_occ_a_flag = *(ferret_map + clock_ferret_ptr + ferret_vert_off + ferret_horiz_off + 7);
        tb_occ_b_flag = *(ferret_map + clock_ferret_ptr + ferret_vert_off + ferret_horiz_off + 8);
        if (clock_ferret_ptr + ferret_vert_off + ferret_horiz_off == ferret_targ_ptr) tb_occ_a_flag = 0;
        return *(ferret_map + clock_ferret_ptr + ferret_vert_off + ferret_horiz_off + 2);
    case 4:
        if (ferret_map_hi - 1 <= clock_ferret_y) return -1;
        tb_prev_flag = *(ferret_map + clock_ferret_ptr + ferret_vert_off + 5) & 0x80;
        tb_occ_a_flag = *(ferret_map + clock_ferret_ptr + ferret_vert_off + 7);
        tb_occ_b_flag = *(ferret_map + clock_ferret_ptr + ferret_vert_off + 8);
        if (clock_ferret_ptr + ferret_vert_off == ferret_targ_ptr) tb_occ_a_flag = 0;
        return *(ferret_map + clock_ferret_ptr + ferret_vert_off + 2);
    case 5:
        if (ferret_map_hi - 1 <= clock_ferret_y) return -1;
        if (clock_ferret_x <= 0) return -1;
        tb_prev_flag = *(ferret_map + clock_ferret_ptr + ferret_vert_off - ferret_horiz_off + 5) & 0x80;
        tb_occ_a_flag = *(ferret_map + clock_ferret_ptr + ferret_vert_off - ferret_horiz_off + 7);
        tb_occ_b_flag = *(ferret_map + clock_ferret_ptr + ferret_vert_off - ferret_horiz_off + 8);
        if (clock_ferret_ptr + ferret_vert_off - ferret_horiz_off == ferret_targ_ptr) tb_occ_a_flag = 0;
        return *(ferret_map + clock_ferret_ptr + ferret_vert_off - ferret_horiz_off + 2);
    case 6:
        if (clock_ferret_x <= 0) return -1;
        tb_prev_flag = *(ferret_map + clock_ferret_ptr - ferret_horiz_off + 5) & 0x80;
        tb_occ_a_flag = *(ferret_map + clock_ferret_ptr - ferret_horiz_off + 7);
        tb_occ_b_flag = *(ferret_map + clock_ferret_ptr - ferret_horiz_off + 8);
        if (clock_ferret_ptr - ferret_horiz_off == ferret_targ_ptr) tb_occ_a_flag = 0;
        return *(ferret_map + clock_ferret_ptr - ferret_horiz_off + 2);
    case 7:
        if (clock_ferret_y <= 0) return -1;
        if (clock_ferret_x <= 0) return -1;
        tb_prev_flag = *(ferret_map + clock_ferret_ptr - ferret_vert_off - ferret_horiz_off + 5) & 0x80;
        tb_occ_a_flag = *(ferret_map + clock_ferret_ptr - ferret_vert_off - ferret_horiz_off + 7);
        tb_occ_b_flag = *(ferret_map + clock_ferret_ptr - ferret_vert_off - ferret_horiz_off + 8);
        if (clock_ferret_ptr - ferret_vert_off - ferret_horiz_off == ferret_targ_ptr) tb_occ_a_flag = 0;
        return *(ferret_map + clock_ferret_ptr - ferret_vert_off - ferret_horiz_off + 2);
    }
    return -1;
}

// FUNCTION: C2 0x2C70B
// WIN: 0x0046c965
// Lines 1106–1162
void move_clock_ferret(signed char dir, char mode)
{
    unsigned char val;
    unsigned char road;

    switch (dir) {
    case 0:
        --clock_ferret_y;
        clock_ferret_ptr -= ferret_vert_off;
        break;
    case 1:
        --clock_ferret_y;
        ++clock_ferret_x;
        clock_ferret_ptr -= ferret_vert_off;
        clock_ferret_ptr += ferret_horiz_off;
        break;
    case 2:
        ++clock_ferret_x;
        clock_ferret_ptr += ferret_horiz_off;
        break;
    case 3:
        ++clock_ferret_y;
        ++clock_ferret_x;
        clock_ferret_ptr += ferret_vert_off;
        clock_ferret_ptr += ferret_horiz_off;
        break;
    case 4:
        ++clock_ferret_y;
        clock_ferret_ptr += ferret_vert_off;
        break;
    case 5:
        ++clock_ferret_y;
        --clock_ferret_x;
        clock_ferret_ptr += ferret_vert_off;
        clock_ferret_ptr -= ferret_horiz_off;
        break;
    case 6:
        --clock_ferret_x;
        clock_ferret_ptr -= ferret_horiz_off;
        break;
    case 7:
        --clock_ferret_y;
        --clock_ferret_x;
        clock_ferret_ptr -= ferret_vert_off;
        clock_ferret_ptr -= ferret_horiz_off;
        break;
    }
    val = *(ferret_map + clock_ferret_ptr + 2);
    road = *(ferret_map + clock_ferret_ptr + 5) & 3;
    if (val == 0) {
        *(ferret_map + clock_ferret_ptr + 2) = clock_ferret_count;
        clock_ferret_count += road;
        clock_ferret_moves++;
    } else if (mode != 0) {
        clock_ferret_count = val + road;
    }
}

// FUNCTION: C2 0x2C883
// WIN: 0x0046cb49
// Lines 1164–1230
/* BYTE-EXACT 2026-06-12 (was 608 b).  Mirror of check_clock_ferret_move
 * with the ANTI mask: tb_prev_flag = cell[5] & 0x40 (PS `and al,0x40`;
 * the old 0x80 was copied from the clock twin — semantic fix).  Same
 * per-site `return -1;` lever; its return -1 block tail-merges
 * backward into the clock twin's (Rule 42 — the jle targets land
 * before this function's entry). */
signed char check_anti_ferret_move(signed char dir)
{
    switch (dir) {
    case 0:
        if (anti_ferret_y <= 0) return -1;
        tb_prev_flag = *(ferret_map + anti_ferret_ptr - ferret_vert_off + 5) & 0x40;
        tb_occ_a_flag = *(ferret_map + anti_ferret_ptr - ferret_vert_off + 7);
        tb_occ_b_flag = *(ferret_map + anti_ferret_ptr - ferret_vert_off + 8);
        if (anti_ferret_ptr - ferret_vert_off == ferret_targ_ptr) tb_occ_a_flag = 0;
        return *(ferret_map + anti_ferret_ptr - ferret_vert_off + 2);
    case 1:
        if (anti_ferret_y <= 0) return -1;
        if (ferret_map_wi - 1 <= anti_ferret_x) return -1;
        tb_prev_flag = *(ferret_map + anti_ferret_ptr - ferret_vert_off + ferret_horiz_off + 5) & 0x40;
        tb_occ_a_flag = *(ferret_map + anti_ferret_ptr - ferret_vert_off + ferret_horiz_off + 7);
        tb_occ_b_flag = *(ferret_map + anti_ferret_ptr - ferret_vert_off + ferret_horiz_off + 8);
        if (anti_ferret_ptr - ferret_vert_off + ferret_horiz_off == ferret_targ_ptr) tb_occ_a_flag = 0;
        return *(ferret_map + anti_ferret_ptr - ferret_vert_off + ferret_horiz_off + 2);
    case 2:
        if (ferret_map_wi - 1 <= anti_ferret_x) return -1;
        tb_prev_flag = *(ferret_map + anti_ferret_ptr + ferret_horiz_off + 5) & 0x40;
        tb_occ_a_flag = *(ferret_map + anti_ferret_ptr + ferret_horiz_off + 7);
        tb_occ_b_flag = *(ferret_map + anti_ferret_ptr + ferret_horiz_off + 8);
        if (anti_ferret_ptr + ferret_horiz_off == ferret_targ_ptr) tb_occ_a_flag = 0;
        return *(ferret_map + anti_ferret_ptr + ferret_horiz_off + 2);
    case 3:
        if (ferret_map_hi - 1 <= anti_ferret_y) return -1;
        if (ferret_map_wi - 1 <= anti_ferret_x) return -1;
        tb_prev_flag = *(ferret_map + anti_ferret_ptr + ferret_vert_off + ferret_horiz_off + 5) & 0x40;
        tb_occ_a_flag = *(ferret_map + anti_ferret_ptr + ferret_vert_off + ferret_horiz_off + 7);
        tb_occ_b_flag = *(ferret_map + anti_ferret_ptr + ferret_vert_off + ferret_horiz_off + 8);
        if (anti_ferret_ptr + ferret_vert_off + ferret_horiz_off == ferret_targ_ptr) tb_occ_a_flag = 0;
        return *(ferret_map + anti_ferret_ptr + ferret_vert_off + ferret_horiz_off + 2);
    case 4:
        if (ferret_map_hi - 1 <= anti_ferret_y) return -1;
        tb_prev_flag = *(ferret_map + anti_ferret_ptr + ferret_vert_off + 5) & 0x40;
        tb_occ_a_flag = *(ferret_map + anti_ferret_ptr + ferret_vert_off + 7);
        tb_occ_b_flag = *(ferret_map + anti_ferret_ptr + ferret_vert_off + 8);
        if (anti_ferret_ptr + ferret_vert_off == ferret_targ_ptr) tb_occ_a_flag = 0;
        return *(ferret_map + anti_ferret_ptr + ferret_vert_off + 2);
    case 5:
        if (ferret_map_hi - 1 <= anti_ferret_y) return -1;
        if (anti_ferret_x <= 0) return -1;
        tb_prev_flag = *(ferret_map + anti_ferret_ptr + ferret_vert_off - ferret_horiz_off + 5) & 0x40;
        tb_occ_a_flag = *(ferret_map + anti_ferret_ptr + ferret_vert_off - ferret_horiz_off + 7);
        tb_occ_b_flag = *(ferret_map + anti_ferret_ptr + ferret_vert_off - ferret_horiz_off + 8);
        if (anti_ferret_ptr + ferret_vert_off - ferret_horiz_off == ferret_targ_ptr) tb_occ_a_flag = 0;
        return *(ferret_map + anti_ferret_ptr + ferret_vert_off - ferret_horiz_off + 2);
    case 6:
        if (anti_ferret_x <= 0) return -1;
        tb_prev_flag = *(ferret_map + anti_ferret_ptr - ferret_horiz_off + 5) & 0x40;
        tb_occ_a_flag = *(ferret_map + anti_ferret_ptr - ferret_horiz_off + 7);
        tb_occ_b_flag = *(ferret_map + anti_ferret_ptr - ferret_horiz_off + 8);
        if (anti_ferret_ptr - ferret_horiz_off == ferret_targ_ptr) tb_occ_a_flag = 0;
        return *(ferret_map + anti_ferret_ptr - ferret_horiz_off + 2);
    case 7:
        if (anti_ferret_y <= 0) return -1;
        if (anti_ferret_x <= 0) return -1;
        tb_prev_flag = *(ferret_map + anti_ferret_ptr - ferret_vert_off - ferret_horiz_off + 5) & 0x40;
        tb_occ_a_flag = *(ferret_map + anti_ferret_ptr - ferret_vert_off - ferret_horiz_off + 7);
        tb_occ_b_flag = *(ferret_map + anti_ferret_ptr - ferret_vert_off - ferret_horiz_off + 8);
        if (anti_ferret_ptr - ferret_vert_off - ferret_horiz_off == ferret_targ_ptr) tb_occ_a_flag = 0;
        return *(ferret_map + anti_ferret_ptr - ferret_vert_off - ferret_horiz_off + 2);
    }
    return -1;
}

// FUNCTION: C2 0x2CC73
// WIN: 0x0046d179
// Lines 1232–1287
void move_anti_ferret(signed char dir, char mode)
{
    unsigned char val;
    unsigned char road;

    switch (dir) {
    case 0:
        --anti_ferret_y;
        anti_ferret_ptr -= ferret_vert_off;
        break;
    case 1:
        --anti_ferret_y;
        ++anti_ferret_x;
        anti_ferret_ptr -= ferret_vert_off;
        anti_ferret_ptr += ferret_horiz_off;
        break;
    case 2:
        ++anti_ferret_x;
        anti_ferret_ptr += ferret_horiz_off;
        break;
    case 3:
        ++anti_ferret_y;
        ++anti_ferret_x;
        anti_ferret_ptr += ferret_vert_off;
        anti_ferret_ptr += ferret_horiz_off;
        break;
    case 4:
        ++anti_ferret_y;
        anti_ferret_ptr += ferret_vert_off;
        break;
    case 5:
        ++anti_ferret_y;
        --anti_ferret_x;
        anti_ferret_ptr += ferret_vert_off;
        anti_ferret_ptr -= ferret_horiz_off;
        break;
    case 6:
        --anti_ferret_x;
        anti_ferret_ptr -= ferret_horiz_off;
        break;
    case 7:
        --anti_ferret_y;
        --anti_ferret_x;
        anti_ferret_ptr -= ferret_vert_off;
        anti_ferret_ptr -= ferret_horiz_off;
        break;
    }
    val = *(ferret_map + anti_ferret_ptr + 2);
    road = *(ferret_map + anti_ferret_ptr + 5) & 3;
    if (val == 0) {
        *(ferret_map + anti_ferret_ptr + 2) = anti_ferret_count;
        anti_ferret_count += road;
        anti_ferret_moves++;
    } else if (mode != 0) {
        anti_ferret_count = val + road;
    }
}

// FUNCTION: C2 0x2CDCD
// WIN: 0x0046d35d
// Lines 1290–1311
unsigned char ferret_heading(int x, int y)
{
    if (x > ferret_targ_x) {
        if (y > ferret_targ_y) return 7;
        if (y == ferret_targ_y) return 6;
        if (y < ferret_targ_y) return 5;
    } else if (x == ferret_targ_x) {
        if (y > ferret_targ_y) return 0;
        if (y == ferret_targ_y) return 8;
        if (y < ferret_targ_y) return 4;
    } else if (x < ferret_targ_x) {
        if (y > ferret_targ_y) return 1;
        if (y == ferret_targ_y) return 2;
        if (y < ferret_targ_y) return 3;
    }
    return 8;
}

// FUNCTION: C2 0x2CE5B
// WIN: 0x0046d47e
// Lines 1313–1355
unsigned char get_tb_value(int dir)
{
    switch (dir) {
    case 0:
        if (tb_y <= 0) return 0xFF;
        tb_road_flag = *(ferret_map + tb_ptr - ferret_vert_off + 5) & 3;
        return *(ferret_map + tb_ptr - ferret_vert_off + 2);
    case 1:
        if (tb_y <= 0) return 0xFF;
        if (ferret_map_wi - 1 <= tb_x) return 0xFF;
        tb_road_flag = *(ferret_map + tb_ptr - ferret_vert_off + ferret_horiz_off + 5) & 3;
        return *(ferret_map + tb_ptr - ferret_vert_off + ferret_horiz_off + 2);
    case 2:
        if (ferret_map_wi - 1 <= tb_x) return 0xFF;
        tb_road_flag = *(ferret_map + tb_ptr + ferret_horiz_off + 5) & 3;
        return *(ferret_map + tb_ptr + ferret_horiz_off + 2);
    case 3:
        if (ferret_map_hi - 1 <= tb_y) return 0xFF;
        if (ferret_map_wi - 1 <= tb_x) return 0xFF;
        tb_road_flag = *(ferret_map + tb_ptr + ferret_vert_off + ferret_horiz_off + 5) & 3;
        return *(ferret_map + tb_ptr + ferret_vert_off + ferret_horiz_off + 2);
    case 4:
        if (ferret_map_hi - 1 <= tb_y) return 0xFF;
        tb_road_flag = *(ferret_map + tb_ptr + ferret_vert_off + 5) & 3;
        return *(ferret_map + tb_ptr + ferret_vert_off + 2);
    case 5:
        if (ferret_map_hi - 1 <= tb_y) return 0xFF;
        if (tb_x <= 0) return 0xFF;
        tb_road_flag = *(ferret_map + tb_ptr + ferret_vert_off - ferret_horiz_off + 5) & 3;
        return *(ferret_map + tb_ptr + ferret_vert_off - ferret_horiz_off + 2);
    case 6:
        if (tb_x <= 0) return 0xFF;
        tb_road_flag = *(ferret_map + tb_ptr - ferret_horiz_off + 5) & 3;
        return *(ferret_map + tb_ptr - ferret_horiz_off + 2);
    case 7:
        if (tb_y <= 0) return 0xFF;
        if (tb_x <= 0) return 0xFF;
        tb_road_flag = *(ferret_map + tb_ptr - ferret_vert_off - ferret_horiz_off + 5) & 3;
        return *(ferret_map + tb_ptr - ferret_vert_off - ferret_horiz_off + 2);
    }
    return 0xFF;
}

// FUNCTION: C2 0x2CFEF
// WIN: 0x0046d7dd
// Lines 1358–1400
unsigned char get_ferret2(int dir)
{
    switch (dir) {
    case 0:
        if (tb_y <= 0) return 0xFF;
        if (*(ferret_map + tb_ptr - ferret_vert_off + 2) == 0xFE) return 0xFF;
        return *(ferret_map + tb_ptr - ferret_vert_off + 6);
    case 1:
        if (tb_y <= 0) return 0xFF;
        if (ferret_map_wi - 1 <= tb_x) return 0xFF;
        if (*(ferret_map + tb_ptr - ferret_vert_off + ferret_horiz_off + 2) == 0xFE) return 0xFF;
        return *(ferret_map + tb_ptr - ferret_vert_off + ferret_horiz_off + 6);
    case 2:
        if (ferret_map_wi - 1 <= tb_x) return 0xFF;
        if (*(ferret_map + tb_ptr + ferret_horiz_off + 2) == 0xFE) return 0xFF;
        return *(ferret_map + tb_ptr + ferret_horiz_off + 6);
    case 3:
        if (ferret_map_hi - 1 <= tb_y) return 0xFF;
        if (ferret_map_wi - 1 <= tb_x) return 0xFF;
        if (*(ferret_map + tb_ptr + ferret_vert_off + ferret_horiz_off + 2) == 0xFE) return 0xFF;
        return *(ferret_map + tb_ptr + ferret_vert_off + ferret_horiz_off + 6);
    case 4:
        if (ferret_map_hi - 1 <= tb_y) return 0xFF;
        if (*(ferret_map + tb_ptr + ferret_vert_off + 2) == 0xFE) return 0xFF;
        return *(ferret_map + tb_ptr + ferret_vert_off + 6);
    case 5:
        if (ferret_map_hi - 1 <= tb_y) return 0xFF;
        if (tb_x <= 0) return 0xFF;
        if (*(ferret_map + tb_ptr + ferret_vert_off - ferret_horiz_off + 2) == 0xFE) return 0xFF;
        return *(ferret_map + tb_ptr + ferret_vert_off - ferret_horiz_off + 6);
    case 6:
        if (tb_x <= 0) return 0xFF;
        if (*(ferret_map + tb_ptr - ferret_horiz_off + 2) == 0xFE) return 0xFF;
        return *(ferret_map + tb_ptr - ferret_horiz_off + 6);
    case 7:
        if (tb_y <= 0) return 0xFF;
        if (tb_x <= 0) return 0xFF;
        if (*(ferret_map + tb_ptr - ferret_vert_off - ferret_horiz_off + 2) == 0xFE) return 0xFF;
        return *(ferret_map + tb_ptr - ferret_vert_off - ferret_horiz_off + 6);
    }
    return 0xFF;
}

// FUNCTION: C2 0x2D1EF
// WIN: 0x0046db8c
// Lines 1402–1447
//
// BYTE-EXACT 2026-06-12 (was 96 b).  Two fixes:
//   1. The function was MISSING its final statement
//      `*(ferret_map + tb_ptr + 6) = 1;` (PS L1447 marks the
//      destination ferret cell) — semantic bug, 96→36 b.
//   2. Prefix `--tb_y;` / `++tb_x;` forms (Rule 72), not postfix:
//      flips the CSE pass's discovery order so the six hoisted
//      candidate values (tb_y±1, tb_x±1, tb_ptr±vert) are emitted
//      in PS's order/homes (edi,ebx,eax,ecx,esi,edx), 36→0 b.
// The pre-dispatch hoist block itself is Watcom's own cross-case
// CSE (no line records in PS) — the per-case RMW source below IS
// the original shape (confirmed by the Mac PPC build, which keeps
// per-case lwz/addi/stw with no hoist).
void move_to_tb_value(int dir)
{
    switch (dir) {
    case 0:
        --tb_y;
        tb_ptr -= ferret_vert_off;
        break;
    case 1:
        --tb_y;
        ++tb_x;
        tb_ptr -= ferret_vert_off;
        tb_ptr += ferret_horiz_off;
        break;
    case 2:
        ++tb_x;
        tb_ptr += ferret_horiz_off;
        break;
    case 3:
        ++tb_y;
        ++tb_x;
        tb_ptr += ferret_vert_off;
        tb_ptr += ferret_horiz_off;
        break;
    case 4:
        ++tb_y;
        tb_ptr += ferret_vert_off;
        break;
    case 5:
        ++tb_y;
        --tb_x;
        tb_ptr += ferret_vert_off;
        tb_ptr -= ferret_horiz_off;
        break;
    case 6:
        --tb_x;
        tb_ptr -= ferret_horiz_off;
        break;
    case 7:
        --tb_y;
        --tb_x;
        tb_ptr -= ferret_vert_off;
        tb_ptr -= ferret_horiz_off;
        break;
    }
    *(ferret_map + tb_ptr + 6) = 1;
}

// FUNCTION: C2 0x2D305
// WIN: 0x0046dd00
// Lines 1450–1455
void get_over_coords(void)
{
    over_ptr = pm_over_cm_ptr / map_actual_atom;
    over_x = over_ptr % map_actual_width;
    over_y = over_ptr / map_actual_width;
}

// FUNCTION: C2 0x2D349
// WIN: 0x0046dd3f
// Lines 1457–1464
int at_edge_of_map(int x, int y)
{
    if (x <= 0) return 1;
    if (x >= map_actual_width - 1) return 1;
    if (y <= 0) return 1;
    if (y >= map_actual_height - 1) return 1;
    return 0;
}

// FUNCTION: C2 0x2D372
// WIN: 0x0046ddab
// Lines 1466–1502
void get_over_army(void)
{
    int sy; /* declaration order drives regalloc */
    int sx;
    int ey;
    int ex;
    int ref;
    int idx;                               /* signed: PS does signed compare */

    over_an_army = 0;
    if (map_mode != 1 || pointer_mode != 0 || pm_over == 0)
        return;
    if ((RM_CELL(pm_over_cm_ptr).terrain & 1) != 0)
        return;

    army_a = (unsigned char)RM_CELL(pm_over_cm_ptr).occupant;
    if (army_a != 0 && pm_over_cm_ptr == army_list[army_a].map_ref) {
        over_an_army = army_a;
        return;
    }

    sx = over_x - 1;
    if (sx < 0) sx = 0;
    sy = over_y - 1;
    if (sy < 0) sy = 0;
    ex = over_x + 1;
    if (ex >= map_actual_width) ex = map_actual_width - 1;
    ey = over_y + 1;
    if (ey >= map_actual_height) ey = map_actual_height - 1;

    for (; sy <= ey; sy++) {
        int tx;
        for (tx = sx; tx <= ex; tx++) {
            ref = (map_actual_width * sy + tx) * map_actual_atom;
            army_a = (unsigned char)RM_CELL(ref).occupant;
            if ((RM_CELL(ref).terrain & 1) == 0
                && army_a != 0
                && army_a >= 0) {                    /* explicit signed-short >=0 test */
                idx = army_a;
                if (idx < 26 && army_list[idx].home_ref == pm_over_cm_ptr) {
                    over_an_army = idx;
                }
            }
        }
    }
}
