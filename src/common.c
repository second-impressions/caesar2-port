
#include "common.h"
#include "c2_data.h"
#include "c2_types.h"

/* File-local state. */
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

// Creates citizen.
// FUNCTION: C2 0x2a907
// FUNCTION: C2WIN 0x004691b0
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
                if (roman_name_count >= 0x20)
                    roman_name_count = 0;
                barbarian_name_count++;
                if (barbarian_name_count >= 0x10)
                    barbarian_name_count = 0;
                return 1;
            }
        }
    }
    return 0;
}

// Creates army.
// FUNCTION: C2 0x2ab1a
// FUNCTION: C2WIN 0x004695b9
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

// Creates unit.
// FUNCTION: C2 0x2ac8b
// FUNCTION: C2WIN 0x0046993d
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

// Creates figure.
// FUNCTION: C2 0x2acfb
// FUNCTION: C2WIN 0x00469aa3
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

// Creates arrow.
// FUNCTION: C2 0x2ae0e
// FUNCTION: C2WIN 0x00469d49
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

// Clears citizen.
// FUNCTION: C2 0x2af5a
// FUNCTION: C2WIN 0x00469f7e
void clear_citizen(struct citizen_rec *p)
{
    unsigned int i;
    char *bytes = (char *)p;
    for (i = 0; i < sizeof(struct citizen_rec); i++) {
        bytes[i] = 0;
    }
}

// Clears army.
// FUNCTION: C2 0x2af6d
// FUNCTION: C2WIN 0x00469f9c
void clear_army(struct army_rec *p)
{
    unsigned int i;
    char *bytes = (char *)p;
    for (i = 0; i < sizeof(struct army_rec); i++) {
        bytes[i] = 0;
    }
}

// Clears every field in a unit record.
// FUNCTION: C2 0x2afbc
void clear_unit(struct unit_rec *p)
{
    unsigned int i;
    char *bytes = (char *)p;
    for (i = 0; i < sizeof(struct unit_rec); i++) {
        bytes[i] = 0;
    }
}

// Clears figure.
// FUNCTION: C2 0x2af8e REORDERED
// FUNCTION: C2WIN 0x00469fb7
void clear_figure(struct figure_rec *p)
{
    unsigned int i;
    char *bytes = (char *)p;
    for (i = 0; i < sizeof(struct figure_rec); i++) {
        bytes[i] = 0;
    }
}

// Clears arrow.
// FUNCTION: C2 0x2afa1
// FUNCTION: C2WIN 0x00469fd2
void clear_arrow(struct arrow_rec *p)
{
    unsigned int i;
    char *bytes = (char *)p;
    for (i = 0; i < sizeof(struct arrow_rec); i++) {
        bytes[i] = 0;
    }
}

// Removes unit.
// FUNCTION: C2 0x2afb4
// FUNCTION: C2WIN 0x00469fed
void remove_unit(int n)
{
    clear_unit(&unit_list[n]);
}

// Removes figure.
// FUNCTION: C2 0x2afc3
// FUNCTION: C2WIN 0x0046a016
void remove_figure(int n)
{
    char zero = 0;
    int ref = figure_list[n].map_ref;
    ((unsigned char *)battle_map)[(ref) + 1] = zero;
    clear_figure(&figure_list[n]);
}

// Removes citizen.
// FUNCTION: C2 0x2afe3
// FUNCTION: C2WIN 0x0046a055
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

// Removes army.
// FUNCTION: C2 0x2b02a
// FUNCTION: C2WIN 0x0046a102
void remove_army(int n)
{
    char zero = 0;
    int ref = army_list[n].map_ref;
    RM_CELL(ref).occupant = zero;
    clear_army(&army_list[n]);
}

// Clears unit list.
// FUNCTION: C2 0x2b04d
// FUNCTION: C2WIN 0x0046a146
void clear_unit_list(void)
{
    for (unit_no = 1; unit_no < 0x33; unit_no++) {
        clear_unit(&unit_list[unit_no]);
    }
}

// Clears figure list.
// FUNCTION: C2 0x2b079
// FUNCTION: C2WIN 0x0046a19d
void clear_figure_list(void)
{
    for (figure_no = 1; figure_no < 0xC9; figure_no++) {
        clear_figure(&figure_list[figure_no]);
    }
}

// Clears arrow list.
// FUNCTION: C2 0x2b0a7
// FUNCTION: C2WIN 0x0046a1f3
void clear_arrow_list(void)
{
    for (arrow_no = 1; arrow_no < 0xC9; arrow_no++) {
        clear_arrow(&arrow_list[arrow_no]);
    }
}

// Checks citizen list and returns the result.
// FUNCTION: C2 0x2b0e3
// FUNCTION: C2WIN 0x0046a245
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

// Checks army list and returns the result.
// FUNCTION: C2 0x2b1ba
// FUNCTION: C2WIN 0x0046a3ed
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

// Clears citizen list.
// FUNCTION: C2 0x2b282
// FUNCTION: C2WIN 0x0046a551
void clear_citizen_list(void)
{
    for (citizen_no = 1; citizen_no < 0xC9; citizen_no++) {
        remove_citizen(citizen_no);
    }
}

// Clears army list.
// FUNCTION: C2 0x2b2a8
// FUNCTION: C2WIN 0x0046a59b
void clear_army_list(void)
{
    for (army_no = 1; army_no < 0x1A; army_no++) {
        remove_army(army_no);
    }
}

// Normalizes temporary army existence states after restoring a game.
// FUNCTION: C2 0x2b2cc
// FUNCTION: C2WIN 0x0046a5e3
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

// Normalizes temporary army states and reports whether any army is still being built.
// FUNCTION: C2 0x2b31d
// FUNCTION: C2WIN 0x0046a6b4
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

// Removes armies left in the temporary building state.
// FUNCTION: C2 0x2b37b
// FUNCTION: C2WIN 0x0046a75f
void army_building_adjusts(void)
{
    for (army_no = 0; army_no < 0x1A; army_no++) {
        if (army_list[army_no].exists == 3) {
            remove_army(army_no);
        }
    }
}

// Clears army from fort ref.
// FUNCTION: C2 0x2b3b3
// FUNCTION: C2WIN 0x0046a7c6
void clear_army_from_fort_ref(int ref)
{
    for (army_no = 0; army_no < 26; army_no++) {
        if (army_list[army_no].exists != 0 && ref == army_list[army_no].fort_ref) {
            army_list[army_no].exists = 3;
            return;
        }
    }
}

// Returns army name from fort ref.
// FUNCTION: C2 0x2b3f9
// FUNCTION: C2WIN 0x0046a85b
int get_army_name_from_fort_ref(int ref)
{
    int result;
    /* Callers guarantee a matching fort reference. */
    for (army_no = 0; army_no < 26; army_no++) {
        if (army_list[army_no].exists != 0 && ref == army_list[army_no].fort_ref) {
            result = army_list[army_no].cohort_id;           /* signed-char movsx */
            return result;
        }
    }
    return result;
}

// Returns nearest army to track.
// FUNCTION: C2 0x2b442
// FUNCTION: C2WIN 0x0046a8f0
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

// Returns nearest enemy to track.
// FUNCTION: C2 0x2b4cb
// FUNCTION: C2WIN 0x0046aa26
int get_nearest_enemy_to_track(int x, int y)
{
    int dist;
    int best = 9999;
    for (army_no = 0; army_no < 26; army_no++) {
        if (army_list[army_no].exists != 0
            && army_list[army_no].type >= 2
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

// Returns tracking army distance.
// FUNCTION: C2 0x2b557
// FUNCTION: C2WIN 0x0046ab7e
int get_tracking_army_distance(int n, int x, int y)
{
    if (army_list[n].map_x == 0 || army_list[n].map_y == 0) return 999;
    return get_longest_distance(army_list[n].map_x,
                                army_list[n].map_y, x, y);
}

// Returns a unit centered on mouse.
// FUNCTION: C2 0x2b593
// FUNCTION: C2WIN 0x0046ac17
int get_a_unit_centered_on_mouse(void)
{
    if (mouse_left_preclick == 0) {
        return 0;
    }
    temp_unit = find_figure(1);
    return temp_unit;
}

// Returns 0 for the find figure query.
// FUNCTION: C2 0x2b59c
int find_figure(int mode)
{
    return 0;
}

// Returns a shootable unit.
// FUNCTION: C2 0x2b5b1
// FUNCTION: C2WIN 0x0046ac54
int get_a_shootable_unit(void)
{
    for (temp_unit = 1; temp_unit < 0x33; temp_unit++) {
        unit_list[temp_unit].is_target = 0;
    }
    temp_unit = find_figure(0);
    unit_list[temp_unit].is_target = 1;
    return temp_unit;
}

// Returns heading.
// FUNCTION: C2 0x2b5f5
// FUNCTION: C2WIN 0x0046ad14
heading_t get_heading(int sx, int sy, int ex, int ey, char mode)
{
    heading_t heading;
    if (sx > ex) {
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

// Clears ferret map.
// FUNCTION: C2 0x2b662
// FUNCTION: C2WIN 0x0046ae0d
void clear_ferret_map(int margin, unsigned char *map_base, int map_wi, int map_hi,
                      int cell_size, int x1, int y1, int x2, int y2)
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

// Clears region ferret map.
// FUNCTION: C2 0x2b7e0
// FUNCTION: C2WIN 0x0046b083
void clear_region_ferret_map(int mode, int margin, unsigned char *map_base, int map_wi,
                             int map_hi, int cell_size, int x1, int y1,
                             int x2, int y2)
{
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

// Clears sea ferret map.
// FUNCTION: C2 0x2ba5e
// FUNCTION: C2WIN 0x0046b4a9
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

// Runs 2 map ferrets.
// FUNCTION: C2 0x2bb7b
// FUNCTION: C2WIN 0x0046b68b
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
        if (ferret_energy <= 0) break;
    }

    for (i = 0; i < 20; i++)
        ferret_run[i] = 0;

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

// Loads ferret run.
// FUNCTION: C2 0x2bceb
// FUNCTION: C2WIN 0x0046b875
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

// Relaxes pathfinding costs within the corridor around the current ferret route.
// FUNCTION: C2 0x2bd7c
// FUNCTION: C2WIN 0x0046b96b
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

// Traces a ferret route backward from the target along decreasing path costs.
// FUNCTION: C2 0x2bf23
// FUNCTION: C2WIN 0x0046bc3b
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
        cur_val++;
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

// Traces a ferret route forward for a bounded number of steps.
// FUNCTION: C2 0x2bfca
// FUNCTION: C2WIN 0x0046bd96
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

// Runs clock ferret.
// FUNCTION: C2 0x2c062
// FUNCTION: C2WIN 0x0046bedd
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

// Runs anti ferret.
// FUNCTION: C2 0x2c1ab
// FUNCTION: C2WIN 0x0046c10f
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

// Checks clock ferret move and returns the result.
// FUNCTION: C2 0x2c31b
// FUNCTION: C2WIN 0x0046c335
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

// Moves the clockwise path probe one cell and stamps its accumulated route cost.
// FUNCTION: C2 0x2c70b
// FUNCTION: C2WIN 0x0046c965
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

// Checks anti ferret move and returns the result.
// FUNCTION: C2 0x2c883
// FUNCTION: C2WIN 0x0046cb49
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

// Moves the anticlockwise path probe one cell and stamps its accumulated route cost.
// FUNCTION: C2 0x2cc73
// FUNCTION: C2WIN 0x0046d179
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

// Returns the compass direction from a point toward the ferret target.
// FUNCTION: C2 0x2cdcd
// FUNCTION: C2WIN 0x0046d35d
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

// Returns tb value.
// FUNCTION: C2 0x2ce5b
// FUNCTION: C2WIN 0x0046d47e
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

// Returns ferret2.
// FUNCTION: C2 0x2cfef
// FUNCTION: C2WIN 0x0046d7dd
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

// Advances the current ferret trace and marks the destination cell.
// FUNCTION: C2 0x2d1ef
// FUNCTION: C2WIN 0x0046db8c
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

// Returns over coords.
// FUNCTION: C2 0x2d305
// FUNCTION: C2WIN 0x0046dd00
void get_over_coords(void)
{
    over_ptr = pm_over_cm_ptr / map_actual_atom;
    over_x = over_ptr % map_actual_width;
    over_y = over_ptr / map_actual_width;
}

// Returns whether the current overview coordinates lie on a map edge.
// FUNCTION: C2 0x2d349
// FUNCTION: C2WIN 0x0046dd3f
int at_edge_of_map(int x, int y)
{
    if (x <= 0) return 1;
    if (x >= map_actual_width - 1) return 1;
    if (y <= 0) return 1;
    if (y >= map_actual_height - 1) return 1;
    return 0;
}

// Returns over army.
// FUNCTION: C2 0x2d372
// FUNCTION: C2WIN 0x0046ddab
void get_over_army(void)
{
    int sy;
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
