
#include "c2_data.h"

/* File-local state. */
int revolt_size;
int barb_ptr;
int barb_entry_count;
int barb_x;
int barb_y;
// Shared no-op early-exit target for `region_trouble`.
// FUNCTION: C2 0x52e1b
// FUNCTION: C2WIN 0x00401384
void city_trouble(void)
{
}

// Monthly trouble cascade: peace mode short-circuits; otherwise roll each of
// revolt/raider/horde/war in turn, stopping on the first one that fires.
// FUNCTION: C2 0x52e1c
// FUNCTION: C2WIN 0x0046e7c3
void region_trouble(void)
{
    if (c2inf.peace_mode != 0) return;
    if (revolt_trouble()) return;
    if (raider_trouble()) return;
    if (horde_trouble()) return;
    war_trouble();
}

// Reset the five `months_since_last_*` dry-spell counters used by the trouble-spawn timers (war /
// horde / raider / revolt / city_attack). Called once at the start of every new game.
// FUNCTION: C2 0x52fa2
// FUNCTION: C2WIN 0x0046e82a
void init_region_trouble(void)
{
    months_since_last_war           = 0;
    months_since_last_horde         = 0;
    months_since_last_raider        = 0;
    months_since_last_revolt        = 0;
    months_since_last_city_attack   = 0;
}

// Monthly rebel-army spawn. On success, revolt_in_region() has created an army at barb_x/barb_y;
// this routine fills its tribe and troop counts, plays the uprising cue, and lowers Pax Romana.
// FUNCTION: C2 0x52fc5
// FUNCTION: C2WIN 0x0046e867
int revolt_trouble(void)
{
    months_since_last_revolt++;
    if (chance_of_attack(0, months_since_last_revolt, 0, 0) && revolt_in_region(0, 0)) {
        army_list[created_army_no].source_region = province_is;
        army_list[created_army_no].tribe_id = tribe_type[province_is];

        army_list[created_army_no].num_specials      = tribe_to_troop_numbers[army_list[created_army_no].tribe_id].specials * revolt_size;
        army_list[created_army_no].num_horse     = tribe_to_troop_numbers[army_list[created_army_no].tribe_id].horse * revolt_size;
        army_list[created_army_no].num_regulars      = tribe_to_troop_numbers[army_list[created_army_no].tribe_id].regulars * revolt_size;
        army_list[created_army_no].num_irregulars    = tribe_to_troop_numbers[army_list[created_army_no].tribe_id].irregulars * revolt_size;
        army_list[created_army_no].num_auxillaries   = tribe_to_troop_numbers[army_list[created_army_no].tribe_id].auxiliaries * revolt_size;
        army_list[created_army_no].total_troops = army_list[created_army_no].num_specials + army_list[created_army_no].num_horse +
                             army_list[created_army_no].num_regulars + army_list[created_army_no].num_irregulars +
                             army_list[created_army_no].num_auxillaries;

        set_sound("uprise.wav", 1);
        pax_romanum -= 6;
        if (pax_romanum < 0) pax_romanum = 0;
        months_since_last_revolt = 0;
        return 1;
    }
    return 0;
}

// Monthly raider roll: bump the dry-spell counter, ask chance_of_attack(kind=1) whether a raid
// lands this month, and (if so) ask raider_in_region() to nominate an attacking region.
// FUNCTION: C2 0x53132
// FUNCTION: C2WIN 0x0046eb23
int raider_trouble(void)
{
    int   total;

    months_since_last_raider++;

    if (chance_of_attack(1, months_since_last_raider, 0, 0) && raider_in_region(attack_direction, attack_from_sea)) {

        army_list[created_army_no].source_region = attacking_region;
        army_list[created_army_no].tribe_id = tribe_type[attacking_region];

        army_list[created_army_no].num_specials    = tribe_to_troop_numbers[army_list[created_army_no].tribe_id].specials * 3;
        army_list[created_army_no].num_horse   = tribe_to_troop_numbers[army_list[created_army_no].tribe_id].horse * 3;
        army_list[created_army_no].num_regulars    = tribe_to_troop_numbers[army_list[created_army_no].tribe_id].regulars * 3;
        army_list[created_army_no].num_irregulars  = tribe_to_troop_numbers[army_list[created_army_no].tribe_id].irregulars * 3;
        army_list[created_army_no].num_auxillaries = tribe_to_troop_numbers[army_list[created_army_no].tribe_id].auxiliaries * 3;

        total = army_list[created_army_no].num_specials + army_list[created_army_no].num_horse
              + army_list[created_army_no].num_regulars + army_list[created_army_no].num_irregulars
              + army_list[created_army_no].num_auxillaries;
        army_list[created_army_no].total_troops = total;

        set_sound("marchb2.wav", 1);

        pax_romanum -= 12;
        if (pax_romanum < 0) pax_romanum = 0;
        months_since_last_raider = 0;
        return 1;
    }
    return 0;
}

// Attempts to spawn a barbarian horde and scales its troops for the current difficulty.
// FUNCTION: C2 0x5329d
// FUNCTION: C2WIN 0x0046edd3
int horde_trouble(void)
{
    int total;

    months_since_last_horde++;

    if (chance_of_attack(2, months_since_last_horde, 0, 0) && barbarian_in_region(attack_direction, attack_from_sea)) {

        army_list[created_army_no].source_region = attacking_region;
        army_list[created_army_no].tribe_id = tribe_type[attacking_region];

        army_list[created_army_no].num_specials    = tribe_to_troop_numbers[army_list[created_army_no].tribe_id].specials * 6;
        army_list[created_army_no].num_horse   = tribe_to_troop_numbers[army_list[created_army_no].tribe_id].horse * 6;
        army_list[created_army_no].num_regulars    = tribe_to_troop_numbers[army_list[created_army_no].tribe_id].regulars * 6;
        army_list[created_army_no].num_irregulars  = tribe_to_troop_numbers[army_list[created_army_no].tribe_id].irregulars * 6;
        army_list[created_army_no].num_auxillaries = tribe_to_troop_numbers[army_list[created_army_no].tribe_id].auxiliaries * 6;

        total = army_list[created_army_no].num_specials + army_list[created_army_no].num_horse
              + army_list[created_army_no].num_regulars + army_list[created_army_no].num_irregulars
              + army_list[created_army_no].num_auxillaries;
        army_list[created_army_no].total_troops = total;

        set_sound("marchb2.wav", 1);

        pax_romanum -= 18;
        if (pax_romanum < 0) pax_romanum = 0;
        months_since_last_horde = 0;
        return 1;
    }
    return 0;
}

// Attempts to start a foreign invasion based on difficulty and time since the last war.
// FUNCTION: C2 0x52e40 REORDERED
// FUNCTION: C2WIN 0x0046f08d
int war_trouble(void)
{
    int   total;

    months_since_last_war++;

    if (chance_of_attack(3, months_since_last_war, 0, 1) && empire_in_region(attack_direction, attack_from_sea)) {

        army_list[created_army_no].source_region = attacking_region;
        army_list[created_army_no].tribe_id = tribe_type[attacking_region];

        army_list[created_army_no].num_specials    = tribe_to_troop_numbers[army_list[created_army_no].tribe_id].specials * 8;
        army_list[created_army_no].num_horse   = tribe_to_troop_numbers[army_list[created_army_no].tribe_id].horse * 8;
        army_list[created_army_no].num_regulars    = tribe_to_troop_numbers[army_list[created_army_no].tribe_id].regulars * 8;
        army_list[created_army_no].num_irregulars  = tribe_to_troop_numbers[army_list[created_army_no].tribe_id].irregulars * 8;
        army_list[created_army_no].num_auxillaries = tribe_to_troop_numbers[army_list[created_army_no].tribe_id].auxiliaries * 8;

        total = army_list[created_army_no].num_specials + army_list[created_army_no].num_horse
              + army_list[created_army_no].num_regulars + army_list[created_army_no].num_irregulars
              + army_list[created_army_no].num_auxillaries;
        army_list[created_army_no].total_troops = total;

        set_sound("marchb2.wav", 1);

        pax_romanum -= 24;
        if (pax_romanum < 0) pax_romanum = 0;
        months_since_last_war = 0;
        return 1;
    }
    return 0;
}

// Returns whether a monthly attack event passes its difficulty and cooldown checks.
// FUNCTION: C2 0x5341a
// FUNCTION: C2WIN 0x0046f33d
int chance_of_attack(int trouble_type, int months_since,
                     int probe_only, int p4)
{
    int honeymoon;
    int frequency;
    int debar;

    attack_from_sea = 0;
    honeymoon = skill_to_trouble_honeymoons[c2inf.skill_level][trouble_type];
    frequency = skill_to_trouble_frequency[c2inf.skill_level][trouble_type];
    debar     = skill_to_trouble_debar[c2inf.skill_level][trouble_type];

    if (honeymoon > years_elapsed_in_region) return 0;
    if (months_since <= debar)               return 0;
    random();
    if (rand128 < 20)                        return 0;
    if (frequency + 20 <= rand128)           return 0;

    if (probe_only == 0) {
        attack_direction = get_attackers(rand128 & 3, p4);
        if (attack_direction >= 8) return 0;
        if (attack_direction == 0 && north_trader_is == 1) attack_from_sea = 1;
        if (attack_direction == 2 && east_trader_is  == 1) attack_from_sea = 1;
        if (attack_direction == 4 && south_trader_is == 1) attack_from_sea = 1;
        if (attack_direction == 6 && west_trader_is  == 1) attack_from_sea = 1;
    }
    return 1;
}

// Pick an attack direction for chance_of_attack. region_borders is laid out as 4 bytes per
// province (one per cardinal direction); a neighbour kind in {6, 0xf, 0x12, 0x22} is considered
// hostile and is selected if its empire[kind] entry is anything other than 6 (= friendly empire).
// FUNCTION: C2 0x534fd
// FUNCTION: C2WIN 0x0046f4d0
int get_attackers(int dir, int scan_all)
{
    int kind;
    int i;

    if (scan_all) {
        /* Scan all four borders; return the first one whose kind is a
           known hostile category (6/f/12/22) and whose empire entry is
           not the friendly value (6). */
        for (i = 0; i < 4; i++) {
            kind = region_borders[province_is].u.dir[i];
            if (kind == 6 || kind == 0xf || kind == 0x12 || kind == 0x22) {
                if (empire[kind] != 6) {
                    attacking_region = kind;
                    return i + i;
                }
            }
        }
    }
    else {
        /* Single-direction probe with the opposite eligibility test:
           the four "hostile" kinds (6/f/12/22) are rejected here, only
           neighbours outside that set are candidates. */
        kind = region_borders[province_is].u.dir[dir];
        if (kind == 6)    return 8;
        if (kind == 0xf)  return 8;
        if (kind == 0x12) return 8;
        if (kind == 0x22) return 8;
        if (empire[kind] == 6) return 8;
        attacking_region = kind;
        return dir * 2;
    }
    return 8;
}

// Spawn a raider army at one of the region's invasion points. When from_sea is non-zero, drop a
// sea-based raider (mode=1, state_idx 0xe = sea-prowl); otherwise a land-based one (mode=2,
// state_idx 1 with wait_count 0x14).
// FUNCTION: C2 0x5358c
// FUNCTION: C2WIN 0x0046f5e3
int raider_in_region(int dirc, int from_sea)
{
    int map_ref;

    if (get_region_invasion_points(dirc, from_sea) == 0) return 0;

    if (from_sea != 0) {
        if (create_army(4, barb_x, barb_y, 1) == 0) return 0;
        army_list[created_army_no].state_idx        = 0xe;
        army_list[created_army_no].wait_count       = 0;
        army_list[created_army_no].morale = 3;
        army_list[created_army_no].saved_state_idx  = 6;
        army_list[created_army_no].army_id = (rand128 & 1);
    } else {
        if (create_army(4, barb_x, barb_y, 2) == 0) return 0;
        army_list[created_army_no].state_idx        = 1;
        army_list[created_army_no].wait_count       = 0x14;
        army_list[created_army_no].morale = 3;
        army_list[created_army_no].saved_state_idx  = 6;
    }

    army_list[created_army_no].target_y = 0;
    army_list[created_army_no].target_x = 0;

    map_ref = army_list[created_army_no].map_ref;
    if (map_ref == 0) map_ref = 8;
    put_message(0x5b, map_ref, 0x11);
    return 1;
}

// Twin of raider_in_region but for barbarian armies: create_army with type=3, saved_state_idx=7,
// target_kind=4 (vs raider 6/3), and the player notice message is 0x5d ("barbarians have invaded
// ...").
// FUNCTION: C2 0x53688
// FUNCTION: C2WIN 0x0046f7fd
int barbarian_in_region(int dirc, int from_sea)
{
    int map_ref;

    if (get_region_invasion_points(dirc, from_sea) == 0) return 0;

    if (from_sea != 0) {
        if (create_army(3, barb_x, barb_y, 1) == 0) return 0;
        army_list[created_army_no].state_idx        = 0xe;
        army_list[created_army_no].wait_count       = 0;
        army_list[created_army_no].morale = 4;
        army_list[created_army_no].saved_state_idx  = 7;
        army_list[created_army_no].army_id = (rand128 & 1);
    } else {
        if (create_army(3, barb_x, barb_y, 2) == 0) return 0;
        army_list[created_army_no].state_idx        = 1;
        army_list[created_army_no].wait_count       = 0x14;
        army_list[created_army_no].morale = 4;
        army_list[created_army_no].saved_state_idx  = 7;
    }

    map_ref = army_list[created_army_no].map_ref;
    map_ref = map_ref == 0 ? 8 : map_ref;
    put_message(0x5d, map_ref, 0x11);
    return 1;
}

// Twin of barbarian_in_region but for hostile-empire armies (create_army type=2, message 0x5e).
// Saved_state_idx = 7, target_kind = 4 — same as barbarian.
// FUNCTION: C2 0x53776
// FUNCTION: C2WIN 0x0046f9ce
int empire_in_region(int dirc, int from_sea)
{
    int map_ref;

    if (get_region_invasion_points(dirc, from_sea) == 0) return 0;

    if (from_sea != 0) {
        if (create_army(2, barb_x, barb_y, 1) == 0) return 0;
        army_list[created_army_no].state_idx        = 0xe;
        army_list[created_army_no].wait_count       = 0;
        army_list[created_army_no].morale = 4;
        army_list[created_army_no].saved_state_idx  = 7;
        army_list[created_army_no].army_id = (rand128 & 1);
    } else {
        if (create_army(2, barb_x, barb_y, 2) == 0) return 0;
        army_list[created_army_no].state_idx        = 1;
        army_list[created_army_no].wait_count       = 0x14;
        army_list[created_army_no].morale = 4;
        army_list[created_army_no].saved_state_idx  = 7;
    }

    map_ref = army_list[created_army_no].map_ref;
    map_ref = map_ref == 0 ? 8 : map_ref;
    put_message(0x5e, map_ref, 0x11);
    return 1;
}

// Spawn a revolt army at (barb_x, barb_y) with revolt_size set from the region-points roll.
// Returns 1 on success, 0 if the roll or the create_army call fails.
// FUNCTION: C2 0x53861
// FUNCTION: C2WIN 0x0046fb9f
int revolt_in_region(int dirc, int from_sea)
{
    (void)dirc;
    (void)from_sea;
    revolt_size = get_region_revolt_points();
    if (revolt_size == 0) return 0;
    if (create_army(5, barb_x, barb_y, 2) == 0) return 0;
    army_list[created_army_no].state_idx       = 1;
    army_list[created_army_no].wait_count      = 0x14;
    army_list[created_army_no].morale          = 2;
    army_list[created_army_no].saved_state_idx = 7;
    put_message(0x5c, army_list[created_army_no].map_ref, 0x11);
    return 1;
}

// Tries up to 20 random edge positions to find a valid land or sea invasion point.
// FUNCTION: C2 0x538d6
// FUNCTION: C2WIN 0x0046fc82
int get_region_invasion_points(int dirc, int from_sea)
{
    int i;
    char t;

    i = 0;
    while (i++ < 20) {
        get_random_start_points_from_dirc(dirc, 0x3c, 0x3f);
        barb_ptr = (barb_x + barb_y * REGION_W) * REGION_CELL_BYTES;
        t = (*(struct region_cell *)((unsigned char *)region_map + (barb_ptr))).terrain;
        if (from_sea != 0) {
            if ((t & 8) != 0)
                return 1;
        } else {
            if ((t & 0x1c) == 0) {
                clear_a_reg_area(barb_x, barb_y, barb_x, barb_y, 1);
                return 1;
            }
        }
    }
    return 0;
}

// Pick one of the four rebel-hut anchor tiles, then choose the first adjacent clear tile in
// N/E/S/W order. Returns hut kind minus 0x92 (1..4) and writes barb_x/barb_y for the army spawn,
// or 0 if the chosen hut/adjacent cells are unsuitable.
// FUNCTION: C2 0x5395c
// FUNCTION: C2WIN 0x0046fd4f
int get_region_revolt_points(void)
{
    int n;
    int off;
    char tile;
    char occ;
    char t;

    n = rand128 & 3;
    off = hut_list[n].x * REGION_CELL_BYTES;
    off += hut_list[n].y * REGION_W * REGION_CELL_BYTES;
    tile = RM_CELL(off).base_kind;
    if (tile >= 0x93 && tile <= 0x96) {
        t   = (*(struct region_cell *)((unsigned char *)region_map + (barb_ptr - 480))).terrain;
        occ = (*(struct region_cell *)((unsigned char *)region_map + (barb_ptr - 480))).occupant;
        if ((t & 8) == 0 && occ == 0) { barb_x = hut_list[n].x; barb_y = hut_list[n].y - 1; return tile - 0x92; }
        t   = (*(struct region_cell *)((unsigned char *)region_map + (barb_ptr + 8))).terrain;
        occ = (*(struct region_cell *)((unsigned char *)region_map + (barb_ptr + 8))).occupant;
        if ((t & 8) == 0 && occ == 0) { barb_x = hut_list[n].x + 1; barb_y = hut_list[n].y; return tile - 0x92; }
        t   = (*(struct region_cell *)((unsigned char *)region_map + (barb_ptr + 480))).terrain;
        occ = (*(struct region_cell *)((unsigned char *)region_map + (barb_ptr + 480))).occupant;
        if ((t & 8) == 0 && occ == 0) { barb_x = hut_list[n].x; barb_y = hut_list[n].y + 1; return tile - 0x92; }
        t   = (*(struct region_cell *)((unsigned char *)region_map + (barb_ptr - 8))).terrain;
        occ = (*(struct region_cell *)((unsigned char *)region_map + (barb_ptr - 8))).occupant;
        if ((t & 8) == 0 && occ == 0) { barb_x = hut_list[n].x - 1; barb_y = hut_list[n].y; return tile - 0x92; }
    }
    return 0;
}


// Spawn a wave of barbarian citizens inside the city when an auto-resolved (or unopposed)
// barbarian army reaches the walls. Wave size scales with the attacker's total_troops in bands of
// 800/600/400/200 → 9/7/5/3 invaders (2 below 200).
// FUNCTION: C2 0x53ac3
// FUNCTION: C2WIN 0x0046ff71
int barbarian_invades_city(int army_idx)
{
    int   count;
    int   dir;
    int   placed;
    int   attempts;
    unsigned char terrain;

    if      (army_list[army_idx].total_troops >= 0x320) count = 9;
    else if (army_list[army_idx].total_troops >= 0x258) count = 7;
    else if (army_list[army_idx].total_troops >= 0x190) count = 5;
    else if (army_list[army_idx].total_troops >=  0xc8) count = 3;
    else                                                count = 2;

    dir = (army_list[army_idx].world_dir + 4) % 8;

    for (placed = 0; placed < count; placed++) {
        for (attempts = 0; attempts++ < 10; ) {
            get_random_start_points_from_dirc(dir, 0x50, 0x3f);
            barb_ptr = (barb_y * CITY_W + barb_x) * CITY_CELL_BYTES;
            terrain = (*(struct city_cell *)((unsigned char *)city_map + (barb_ptr))).terrain;
            if (terrain & 0xe7) {
                clear_an_area(barb_x, barb_y, barb_x, barb_y);
            }
            if (create_citizen(3, barb_x, barb_y, 0) == 0) goto finished;
            break;
        }

        citizen_list[created_citizen_no].state_idx       = 1;
        citizen_list[created_citizen_no].saved_state_idx = 5;
        citizen_list[created_citizen_no].wait_count      = 0x14;
        citizen_list[created_citizen_no].dest_x          = top_lv_x;
        citizen_list[created_citizen_no].dest_y          = top_lv_y;
    }

finished:
    if (placed == 0) return 0;

    put_message(0x53, citizen_list[created_citizen_no].map_ref, 0x17);

    pax_romanum -= 0x40;
    if (pax_romanum < 0) pax_romanum = 0;
    return 1;
}

// Drop `count` type-3 barbarians (raiders/horde footsoldiers) on random map-edge cells indicated
// by `dirc`. Each spawn rolls an edge cell, clears the 1×1 area if any road/wall/aqueduct bits
// (mask 0xE7) are set, then creates a citizen aimed at the player's last-viewed tile.
// FUNCTION: C2 0x53c43
// FUNCTION: C2WIN 0x00470206
void barbarians_drop_by_city(int dirc, int count)
{
    int i;
    int attempts;
    unsigned char terrain;

    for (i = 0; i < count; i++) {
        for (attempts = 0; attempts++ < 10; ) {
            get_random_start_points_from_dirc(dirc, 0x50, 0x3f);
            barb_ptr = (barb_y * CITY_W + barb_x) * CITY_CELL_BYTES;
            terrain = (*(struct city_cell *)((unsigned char *)city_map + (barb_ptr))).terrain;
            if (terrain & 0xe7) {
                clear_an_area(barb_x, barb_y, barb_x, barb_y);
            }
            if (create_citizen(3, barb_x, barb_y, 0) == 0) goto finished;
            break;
        }
        citizen_list[created_citizen_no].state_idx       = 1;
        citizen_list[created_citizen_no].saved_state_idx = 5;
        citizen_list[created_citizen_no].wait_count      = 0x14;
        citizen_list[created_citizen_no].dest_x          = top_lv_x;
        citizen_list[created_citizen_no].dest_y          = top_lv_y;
    }

finished:
    if (i != 0) {
        put_message(0x53, citizen_list[created_citizen_no].map_ref, 0x17);
        pax_romanum -= 0x40;
        if (pax_romanum < 0) pax_romanum = 0;
    }
}

// Pick a pseudo-random barbarian entry point on the edge indicated by `dirc` (0..7). `size` is the
// map dimension (normally 60) and `mask` is the random mask (normally 0x3f).
// FUNCTION: C2 0x53d4e
// FUNCTION: C2WIN 0x004703be
void get_random_start_points_from_dirc(int dirc, int size, int mask)
{
    int wrapped;
    int seed;
    int x;
    int y;

    barb_entry_count++;
    seed = (rand128 + barb_entry_count) & mask;
    x = (size - mask) / 2;
    if (x < 0) x = 0;
    y = size - mask / 4;
    if (y < 0) y = 0;
    x += seed;
    y += seed / 2;
    wrapped = 0;
    if (x >= size) x /= 2;
    if (y >= size) { y -= size; wrapped = 1; }

    if (dirc == 0) { barb_x = x; barb_y = 0; }
    else if (dirc == 1) {
        if (wrapped) { barb_x = size - 1; barb_y = y; }
        else { barb_x = y; barb_y = 0; }
    } else if (dirc == 2) { barb_x = size - 1; barb_y = x; }
    else if (dirc == 3) {
        if (wrapped) { barb_x = size - 1 - y; barb_y = size - 1; }
        else { barb_x = size - 1; barb_y = y; }
    } else if (dirc == 4) { barb_x = x; barb_y = size - 1; }
    else if (dirc == 5) {
        if (wrapped) { barb_x = 0; barb_y = size - 1 - y; }
        else { barb_x = size - 1 - y; barb_y = size - 1; }
    } else if (dirc == 6) { barb_x = 0; barb_y = x; }
    else if (dirc == 7) {
        if (wrapped) { barb_x = y; barb_y = 0; }
        else { barb_x = 0; barb_y = size - 1 - y; }
    }
}

// Round-robin scan of army_list looking for a cohort. Walks ``temp_army`` from its last value up
// to 26 candidates, wrapping from 26→1.
// FUNCTION: C2 0x53e8e
// FUNCTION: C2WIN 0x00470607
int get_next_temp_cohort(int strict)
{
    int retries;

    for (retries = 0; retries < 26; retries++) {
        temp_army++;
        if (temp_army >= 26)
            temp_army = 1;

        if (army_list[temp_army].exists == 0) continue;
        if (army_list[temp_army].type   != 1) continue;
        if (strict != 0) {
            if (army_list[temp_army].state_idx    == 10) continue;
            if (army_list[temp_army].target_timer == 0)  continue;
        }
        return 1;
    }
    return 0;
}

// Rebuild the ``cohort_in_action[10]`` bitmap and the ``no_of_cohorts_in_action`` total from the
// live army_list. Each cohort army (type == 1) tags its name slot in the array and bumps the
// total; a stray name >= 10 fires the ``test_beeps`` debug stub.
// FUNCTION: C2 0x53f0c
// FUNCTION: C2WIN 0x004706fe
void get_cohorts_in_action(void)
{
    int i;

    for (no_of_cohorts_in_action = i = 0; i < 10; i++) cohort_in_action[i] = 0;

    for (army_no = 1; army_no < 26; army_no++) {
        if (army_list[army_no].exists != 0 &&
            army_list[army_no].type   == 1) {
            if (army_list[army_no].cohort_id >= 10) test_beeps();
            else {
                cohort_in_action[army_list[army_no].cohort_id] = 1;
                no_of_cohorts_in_action++;
            }
        }
    }

    for (next_cohort_free = i = 0; i < 10; ) { if (cohort_in_action[i] == 0) break; i++; next_cohort_free++; }
}

// Step `forum_viewed_army` to the previous (direction == 0) or next (direction != 0) cohort marked
// active in `cohort_in_action`. Wraps the index into [0..10] after each step; the value 10 is the
// "all cohorts" / "no-match" sentinel and ends the search.
// FUNCTION: C2 0x53f9d
// FUNCTION: C2WIN 0x00470843
void get_next_viewed_cohort(int direction)
{
    int tries;

    get_cohorts_in_action();
    tries = 0;
    for (;;) {
        if (direction == 0) {
            --forum_viewed_army;
        } else {
            ++forum_viewed_army;
        }
        if (forum_viewed_army <  0) forum_viewed_army = 10;
        if (forum_viewed_army > 10) forum_viewed_army = 0;
        if (forum_viewed_army == 10) return;
        if ((cohort_in_action[forum_viewed_army] & 0xff) == 1) return;
        ++tries;
        if (tries >= 11) break;
    }
    forum_viewed_army = 10;
}

// Validate the currently-selected cohort index after external state changes (e.g. battle outcome,
// page navigation).
// FUNCTION: C2 0x54012
// FUNCTION: C2WIN 0x004708f4
void check_viewed_cohort(void)
{
    get_cohorts_in_action();
    if (forum_viewed_army <  0) forum_viewed_army = 10;
    if (forum_viewed_army > 10) forum_viewed_army = 0;
    if (forum_viewed_army != 10 &&
        (cohort_in_action[forum_viewed_army] & 0xff) != 1) {
        get_next_viewed_cohort(1);
    }
}

// Resolve the army record currently selected in the forum view to its army_list[] index. Returns
// `tracking_army` directly if it points at a cohort; otherwise scans army_list[0..26) for the
// first existing cohort whose `cohort_id` matches forum_viewed_army.
// FUNCTION: C2 0x54065
// FUNCTION: C2WIN 0x00470969
int get_actual_viewed_army(void)
{
    if (tracking_army != 0) {
        if (army_list[tracking_army].type == 1)
            return tracking_army;
    }
    for (temp_army = 0; temp_army < 26; ++temp_army) {
        if (army_list[temp_army].exists != 0
            && army_list[temp_army].type == 1
            && army_list[temp_army].cohort_id == forum_viewed_army)
        {
            return temp_army;
        }
    }
    forum_viewed_army = 0xa;
    return 0;
}

// Initialize sea traders for each border using the neighbouring province's primary resource.
// FUNCTION: C2 0x540e4
// FUNCTION: C2WIN 0x00470a6a
void init_traders(void)
{
    int pi;
    int border;

    north_trader_count0 = 2;
    north_trader_count1 = 0xa;
    east_trader_count0  = 4;
    east_trader_count1  = 0xc;
    south_trader_count0 = 6;
    south_trader_count1 = 0xe;
    west_trader_count0  = 8;
    west_trader_count1  = 0x10;

    pi = province_is;
    border = region_borders[pi].u.side.north;
    north_trader_brings = region_sources[border].primary;
    border = region_borders[pi].u.side.east;
    east_trader_brings  = region_sources[border].primary;
    border = region_borders[pi].u.side.south;
    south_trader_brings = region_sources[border].primary;
    border = region_borders[pi].u.side.west;
    west_trader_brings  = region_sources[border].primary;
}

// Monthly trader spawner.
// FUNCTION: C2 0x541c8
// FUNCTION: C2WIN 0x00470b60
void launch_traders(void)
{
    /* ---- North ---- */
    north_trader_count0--;
    if (north_trader_count0 <= 0) {
        if (north_trader_is == 0) {
            do_land_trade(0, north_trader_brings,
                          north_border_x, north_border_y);
            north_trader_count0 = 4;
        } else if (do_sea_trade(0, north_trader_brings,
                                north_border_x, north_border_y, 0)) {
            north_trader_count0 = 0xf423f;
        } else {
            north_trader_count0 = 2;
        }
    }
    north_trader_count1--;
    if (north_trader_count1 <= 0 && north_trader_is != 0) {
        if (do_sea_trade(0, north_trader_brings,
                         north_border_x, north_border_y, 1)) {
            north_trader_count1 = 0xf423f;
        } else {
            north_trader_count1 = 2;
        }
    }

    /* ---- East ---- */
    east_trader_count0--;
    if (east_trader_count0 <= 0) {
        if (east_trader_is == 0) {
            do_land_trade(2, east_trader_brings,
                          east_border_x, east_border_y);
            east_trader_count0 = 4;
        } else if (do_sea_trade(2, east_trader_brings,
                                east_border_x, east_border_y, 0)) {
            east_trader_count0 = 0xf423f;
        } else {
            east_trader_count0 = 2;
        }
    }
    east_trader_count1--;
    if (east_trader_count1 <= 0 && east_trader_is != 0) {
        if (do_sea_trade(2, east_trader_brings,
                         east_border_x, east_border_y, 1)) {
            east_trader_count1 = 0xf423f;
        } else {
            east_trader_count1 = 2;
        }
    }

    /* ---- South ---- */
    south_trader_count0--;
    if (south_trader_count0 <= 0) {
        if (south_trader_is == 0) {
            do_land_trade(4, south_trader_brings,
                          south_border_x, south_border_y);
            south_trader_count0 = 4;
        } else if (do_sea_trade(4, south_trader_brings,
                                south_border_x, south_border_y, 0)) {
            south_trader_count0 = 0xf423f;
        } else {
            south_trader_count0 = 2;
        }
    }
    south_trader_count1--;
    if (south_trader_count1 <= 0 && south_trader_is != 0) {
        if (do_sea_trade(4, south_trader_brings,
                         south_border_x, south_border_y, 1)) {
            south_trader_count1 = 0xf423f;
        } else {
            south_trader_count1 = 2;
        }
    }

    /* ---- West ---- */
    west_trader_count0--;
    if (west_trader_count0 <= 0) {
        if (west_trader_is == 0) {
            do_land_trade(6, west_trader_brings,
                          west_border_x, west_border_y);
            west_trader_count0 = 4;
        } else if (do_sea_trade(6, west_trader_brings,
                                west_border_x, west_border_y, 0)) {
            west_trader_count0 = 0xf423f;
        } else {
            west_trader_count0 = 2;
        }
    }
    west_trader_count1--;
    if (west_trader_count1 <= 0 && west_trader_is != 0) {
        if (do_sea_trade(6, west_trader_brings,
                         west_border_x, west_border_y, 1)) {
            west_trader_count1 = 0xf423f;
        } else {
            west_trader_count1 = 2;
        }
    }
}

// Update a region-map cell's trade-route level after a successful land trade. Gated on bit 0x20 of
// (*(struct region_cell *)((unsigned char *)region_map + (+3))).base_kind; otherwise no-op.
// FUNCTION: C2 0x54503
// FUNCTION: C2WIN 0x00470f23
void do_land_trade(int kind, int p2, int x, int y)
{
    int dist;
    char new_lvl;
    char cur_lvl;
    char q;
    (void)p2;

    q = (*(struct region_cell *)((unsigned char *)region_map + ((x + y * REGION_W) * REGION_CELL_BYTES))).edge_bits & 0x20;

    if (q == 0) return;
    dist = get_closest_trading_post(x, y, 0x10);
    if (dist > 0x10) return;
    cur_lvl = (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).occupant & 0x1c;
    cur_lvl >>= 2;
    if (dist <= 2)       new_lvl = 7;
    else if (dist <= 4)  new_lvl = 6;
    else if (dist <= 6)  new_lvl = 5;
    else if (dist <= 8)  new_lvl = 4;
    else if (dist <= 10) new_lvl = 3;
    else if (dist <= 12) new_lvl = 2;
    else                 new_lvl = 1;
    if (new_lvl > cur_lvl) cur_lvl = new_lvl;
    cur_lvl <<= 2;
    (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).occupant &= 0xe3;
    (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).occupant |= cur_lvl;

    (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).occupant &= 0x9f;
    if (kind == 0) return;
    if (kind == 2) { (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).occupant |= 0x20; return; }
    if (kind == 4) { (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).occupant |= 0x40; return; }
    if (kind == 6) { (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).occupant |= 0x60; return; }
}

// Spawn a sea-trader army. Called once per direction by launch_traders.
// FUNCTION: C2 0x545e8
// FUNCTION: C2WIN 0x0047110f
int do_sea_trade(int compass_side, int cargo,
                 int home_x, int home_y, int army_id)
{
    int idx;

    if (create_army(6, home_x, home_y, 1) == 0) return 0;
    idx = created_army_no;
    army_list[idx].home_x          = home_x;
    army_list[idx].home_y          = home_y;
    army_list[idx].compass_side    = compass_side;
    army_list[idx].trader_brings   = cargo;
    army_list[idx].state_idx       = 0xb;
    army_list[idx].saved_state_idx = 0xb;
    army_list[idx].exists          = 1;
    army_list[idx].departure_year  = year;
    army_list[idx].target_count = 0; army_list[idx].target_kind = 0;
    army_list[idx].return_flag = 0;
    army_list[idx].army_id     = army_id;
    army_list[idx].flags |= 1;
    return 1;
}

// Resume or start an interrupted battle. `pre_loaded == 0` runs the intro path (battle_setup_count
// = 0x64, battle_intro, get_battle_men, battle_state = 5); `pre_loaded != 0` skips the confirm
// prompt and jumps straight into do_fight_battle.
// FUNCTION: C2 0x5468f
// FUNCTION: C2WIN 0x004712b4
void continue_battle(int pre_loaded)
{
    unsigned char mm;

    battle_setup_count = 0;
    if (pre_loaded == 0) {
        battle_setup_count = 0x64;
        battle_intro();
        get_battle_men();
        battle_state = 5;
    } else {
        decision = 1;
    }

    stop_db();
    act_exit_turbo_mode();

    if (decision == 1) {
        do_fight_battle(pre_loaded);
        if (battle_state != 0xa) get_battle_centuries_left();
    }

    if (battle_state == 6) {
        we_retreat();
        battle_victor = 1;
    } else if (battle_state == 8) {
        battle_victor = 0;
    } else if (battle_state == 7) {
        we_surrender();
        battle_victor = 1;
    } else if (battle_state == 9) {
        battle_victor = 0;
    } else if (battle_state == 4) {
        if (our_battle_men <= 0) {
            battle_victor = 1;
        } else if (our_battle_morale <= 0) {
            battle_victor = 1;
        } else {
            battle_victor = 0;
        }
    } else if (battle_state == 5) {
        battle_auto_resolve();
    } else if (battle_state == 0xa) {
        return;
    } else {
        battle_victor = 0;
    }

    if (battle_victor == 0) {
        do_vga_smacked_anim("battwon.smk");
    } else {
        do_vga_smacked_anim("battlost.smk");
    }

    refresh_zoom_mode(zoom_level);
    act_correct_map();
    battle_outtro();
    do_battle_victory();

    mm = map_mode;
    if (mm == 0)      city_map_screen(0);
    else if (mm == 1) region_map_screen(0);

    play_tune("cityprov.xmi", 0);
    city_tune_playing = 1;
    update_map        = 1;
    setup_map_screen_long_refresh(8);
}

// Pre-battle intro: silence music, optionally load the "prebatle.raw" sting, scroll the region map
// to the cohort, and pump the intro game loop until the regular game-loop sets out1.
// FUNCTION: C2 0x547fd
// FUNCTION: C2WIN 0x004716c9
void battle_intro(void)
{
    pointer_mode = 0;
    stop_tune();
    if (c2inf.tunes_on) {
        set_db_sound("prebatle.raw");
    }
    jump_to_regionmap_ptr(army_list[our_battle_army].map_ref + 0x7a0);
    show_regionmap();
    show_battle_intro_screen();
    out1 = 0;
    while (out1 == 0) {
        battle_intro_game_loop();
    }
    clear_mouse();
}

// Pump the idle game loop after a battle ends, displaying the outcome screen, until the player
// right-clicks to dismiss it; then tear down the battle's music/SFX state.
// FUNCTION: C2 0x54864
// FUNCTION: C2WIN 0x00471794
void battle_outtro(void)
{
    pointer_mode = 0;
    show_battle_outtro_screen();
    out1 = 0;
    while (out1 == 0) {
        just_idle_game_loop();
        if (mouse_right_click) {
            out1 = 1;
        }
    }
    stop_db();
}

// Wipe the our-side troop counts after a surrender. All five cohort-strength fields go to zero;
// the num_horse slot is a legacy troop-count field that nothing else reads or writes.
// FUNCTION: C2 0x548a7
// FUNCTION: C2WIN 0x004717e6
void we_surrender(void)
{
    army_list[our_battle_army].num_specials    = 0;
    army_list[our_battle_army].num_horse   = 0;
    army_list[our_battle_army].num_regulars    = 0;
    army_list[our_battle_army].num_irregulars  = 0;
    army_list[our_battle_army].num_auxillaries = 0;
}

// Player retreats: scrap specialist troops entirely, decimate the rest. Specials and the legacy
// num_horse slot go to zero; regulars halve, irregulars drop to a third, auxillaries shrink to a
// quarter.
// FUNCTION: C2 0x548d7
// FUNCTION: C2WIN 0x0047187d
void we_retreat(void)
{
    army_list[our_battle_army].num_specials    = 0;
    army_list[our_battle_army].num_horse   = 0;
    army_list[our_battle_army].num_regulars    /= 2;
    army_list[our_battle_army].num_irregulars  /= 3;
    army_list[our_battle_army].num_auxillaries /= 4;
}

// Off-screen battle resolver invoked when the player picks "auto" from the pre-battle prompt.
// Computes a score for each side, declares battle_victor (0 = us, 1 = them), and scales the
// loser's cohorts by a percentage derived from the strength ratio.
// FUNCTION: C2 0x5493f
// FUNCTION: C2WIN 0x00471967
void battle_auto_resolve(void)
{
    int ratio_band;
    int our_str;
    int their_str;
    int our_score;
    int their_score;
    int lose;
    int pct;
    int aggression;

    aggression = tribe_ai_data[army_list[their_battle_army].tribe_id].aggression;
    random();   /* discarded — only the side-effect on rand128 matters */

    our_str = army_list[our_battle_army].num_regulars + army_list[our_battle_army].num_irregulars
            + army_list[our_battle_army].num_auxillaries + army_list[our_battle_army].num_specials;

    if      (our_str < 50)   our_score = army_list[our_battle_army].morale * 20;
    else if (our_str <= 100) our_score = army_list[our_battle_army].morale * 50;
    else if (our_str <= 200) our_score = army_list[our_battle_army].morale * 80;
    else                     our_score = army_list[our_battle_army].morale * 100;
    our_score += army_list[our_battle_army].num_regulars * 5;
    our_score += army_list[our_battle_army].num_irregulars * 3;
    our_score += army_list[our_battle_army].num_auxillaries * 2;
    our_score += army_list[our_battle_army].num_specials * 3;
    our_score += rand128;

    random();   /* discarded */

    their_str = army_list[their_battle_army].num_regulars + army_list[their_battle_army].num_irregulars
              + army_list[their_battle_army].num_auxillaries + army_list[their_battle_army].num_horse
              + army_list[their_battle_army].num_specials;

    if      (their_str < 50)   their_score = army_list[their_battle_army].morale * 20;
    else if (their_str <= 100) their_score = army_list[their_battle_army].morale * 50;
    else if (their_str <= 200) their_score = army_list[their_battle_army].morale * 80;
    else                       their_score = army_list[their_battle_army].morale * 100;
    their_score += army_list[their_battle_army].num_regulars * 4;
    their_score += army_list[their_battle_army].num_irregulars * 3;
    their_score += army_list[their_battle_army].num_auxillaries;
    their_score += army_list[their_battle_army].num_horse * 4;
    their_score += army_list[their_battle_army].num_specials * 10;
    their_score += rand128;

    if      (their_str < 50)   their_score += (aggression - 1) * 10;
    else if (their_str <= 100) their_score += (aggression - 1) * 20;
    else if (their_str <= 200) their_score += (aggression - 1) * 30;
    else if (their_str <= 400) their_score += (aggression - 1) * 40;
    else if (their_str <= 600) their_score += (aggression - 1) * 50;
    else                       their_score += (aggression - 1) * 60;

    random();   /* discarded */

    if (our_score >= their_score) {
        /* We won. */
        battle_victor = 0;
        tune_mood     = 0x11;

        if      (our_str >= their_str * 10) ratio_band = our_str / 20;
        else if (our_str >= their_str *  5) ratio_band = our_str / 10;
        else if (our_str >= their_str *  3) ratio_band = our_str /  5;
        else if (our_str >= their_str *  2) ratio_band = our_str /  4;
        else if (our_str >= their_str + their_str / 2) ratio_band = our_str /  3;
        else if (our_str >= their_str)      ratio_band = our_str /  2;
        else                                ratio_band = (our_str * 3) / 4;

        if      (our_score > their_score * 5) ratio_band /= 5;
        else if (our_score > their_score * 4) ratio_band /= 4;
        else if (our_score > their_score * 3) ratio_band /= 3;
        else if (our_score > their_score * 2) ratio_band /= 2;

        ratio_band += rand128 & 7;
        lose = valueDIVtotal(ratio_band, our_str);
        lose += aggression;
        if (their_str <= 0) lose = 0;
        if (lose      <  0) lose = 0;
        if (lose      >= 90) lose = 90;
        pct = 100 - lose;

        army_list[our_battle_army].num_regulars = totalXpercent(army_list[our_battle_army].num_regulars, pct);
        army_list[our_battle_army].num_irregulars = totalXpercent(army_list[our_battle_army].num_irregulars, pct);
        army_list[our_battle_army].num_auxillaries = totalXpercent(army_list[our_battle_army].num_auxillaries, pct);
        army_list[our_battle_army].num_specials = totalXpercent(army_list[our_battle_army].num_specials, pct);

        army_list[their_battle_army].num_regulars = 0; army_list[their_battle_army].num_irregulars = 0; army_list[their_battle_army].num_auxillaries = 0; army_list[their_battle_army].num_horse = 0; army_list[their_battle_army].num_specials = 0;
    } else {
        /* We lost. */
        battle_victor = 1;
        tune_mood     = 0x12;

        if      (their_str >= our_str * 10) ratio_band = their_str / 20;
        else if (their_str >= our_str *  5) ratio_band = their_str / 10;
        else if (their_str >= our_str *  3) ratio_band = their_str /  5;
        else if (their_str >= our_str *  2) ratio_band = their_str /  4;
        else if (their_str >= our_str + our_str / 2) ratio_band = their_str /  3;
        else if (their_str >= our_str)      ratio_band = their_str /  2;
        else                                ratio_band = (their_str * 3) / 4;

        if      (their_score > our_score * 5) ratio_band /= 5;
        else if (their_score > our_score * 4) ratio_band /= 4;
        else if (their_score > our_score * 3) ratio_band /= 3;
        else if (their_score > our_score * 2) ratio_band /= 2;

        ratio_band += rand128 & 7;
        lose = valueDIVtotal(ratio_band, their_str);
        if (our_str <= 0) lose = 0;
        if (lose      <  0) lose = 0;
        if (lose      >= 90) lose = 90;
        pct = 100 - lose;

        army_list[their_battle_army].num_regulars = totalXpercent(army_list[their_battle_army].num_regulars, pct);
        army_list[their_battle_army].num_irregulars = totalXpercent(army_list[their_battle_army].num_irregulars, pct);
        army_list[their_battle_army].num_auxillaries = totalXpercent(army_list[their_battle_army].num_auxillaries, pct);
        army_list[their_battle_army].num_horse = totalXpercent(army_list[their_battle_army].num_horse, pct);
        army_list[their_battle_army].num_specials = totalXpercent(army_list[their_battle_army].num_specials, pct);

        army_list[our_battle_army].num_regulars = 0; army_list[our_battle_army].num_irregulars = 0; army_list[our_battle_army].num_auxillaries = 0; army_list[our_battle_army].num_horse = 0; army_list[our_battle_army].num_specials = 0;
    }
}


// Pick the two armies for the upcoming battle: "our" (player-controlled) army and "their" (enemy)
// army. army_no is the cell-target army (the one being attacked or defending the cell); army_a is
// the actor (the army that triggered the encounter).
// FUNCTION: C2 0x54f9e
// FUNCTION: C2WIN 0x004724e7
void get_contenders(void)
{
    if (game_state == 4) return;
    if (army_list[army_no].type == 1) {
        our_battle_army = army_no;
        their_battle_army = army_a;
    } else {
        our_battle_army = army_a;
        their_battle_army = army_no;
    }
}

// Spawn a tribe-flavoured villager-militia in the auto-resolve army slot 0x19 (used during the
// empire/region battle preview when the player attacks an unprotected tribal province).
// FUNCTION: C2 0x54fed
// FUNCTION: C2WIN 0x0047255b
void get_villagers(int x_count)
{
    int   tribe;

    if (game_state == 4) return;

    our_battle_army     = army_no;
    army_a              = 0x19;
    their_battle_army   = 0x19;
    clear_army(&army_list[0x19]);

    army_list[army_a].morale = 3;
    army_list[army_a].source_region = province_is;

    army_list[army_a].total_troops = x_count * 200;

    army_list[army_a].tribe_id = (unsigned char)tribe_type[province_is];
    tribe = army_list[army_a].tribe_id;

    if (tribe_battle_setup[tribe].u.f.middle_kind != 0) {
        army_list[army_a].num_irregulars = x_count * 150;
    } else if (tribe_battle_setup[tribe].u.f.rear_kind != 0) {
        army_list[army_a].num_auxillaries = x_count * 150;
    } else if (tribe_battle_setup[tribe].u.f.front_kind != 0) {
        army_list[army_a].num_regulars = x_count * 150;
    }

    army_list[army_a].battle_disposition = 0xa;
}

// Post-fight bookkeeping for the most recent battle. Branches on battle_victor: Won (0): bump our
// loyalty (clamped to 4); +12 pax_romanum if the loser was the villager slot 0x19, else +24 and
// mark them dispersed (state_idx = 2).
// FUNCTION: C2 0x550d9
// FUNCTION: C2WIN 0x0047274e
void do_battle_victory(void)
{
    struct army_rec *our;
    struct army_rec *their;
    int   aux_loss;
    int   spec_loss;
    int   slot;

    if (battle_victor == 0) {
        /* We won. */
        if (army_list[our_battle_army].morale < 4) army_list[our_battle_army].morale++;

        if (their_battle_army == 0x19) {
            pax_romanum += 12;
            if (pax_romanum > 1000) pax_romanum = 1000;
        } else {
            army_list[their_battle_army].state_idx = 2;
            pax_romanum += 24;
            if (pax_romanum > 1000) pax_romanum = 1000;
        }

        army_list[our_battle_army].total_troops = army_list[our_battle_army].num_auxillaries + army_list[our_battle_army].num_irregulars
                             + army_list[our_battle_army].num_regulars + army_list[our_battle_army].num_horse
                             + army_list[our_battle_army].num_specials;
        army_list[our_battle_army].state_idx = army_list[our_battle_army].saved_state_idx;
    } else {
        /* We lost. */
        if (army_list[their_battle_army].morale < 4) army_list[their_battle_army].morale++;
        army_list[our_battle_army].morale = 0;
        army_list[our_battle_army].readiness_level = 0;
        army_list[our_battle_army].total_troops = army_list[our_battle_army].num_auxillaries + army_list[our_battle_army].num_irregulars
                             + army_list[our_battle_army].num_regulars + army_list[our_battle_army].num_horse
                             + army_list[our_battle_army].num_specials;
        army_list[our_battle_army].morale_timer = 2;
        army_no = our_battle_army;
        sa10_army_demobed();
        army_list[our_battle_army].state_idx = 1;
        army_list[our_battle_army].saved_state_idx = 1;
        pax_romanum -= 12;
        if (pax_romanum < 0) pax_romanum = 0;
        army_list[their_battle_army].total_troops = army_list[their_battle_army].num_auxillaries + army_list[their_battle_army].num_irregulars
                               + army_list[their_battle_army].num_regulars + army_list[their_battle_army].num_horse
                               + army_list[their_battle_army].num_specials;
    }

    /* Shared tail: settle losses against slaves and merc pools. */
    aux_loss  = our_battle_auxs     - army_list[our_battle_army].num_auxillaries;
    spec_loss = our_battle_specials - army_list[our_battle_army].num_specials;

    mercs_in_army -= spec_loss;
    if (mercs_in_army < 0) mercs_in_army = 0;
    max_mercs_allowed -= spec_loss;
    if (max_mercs_allowed < 0) max_mercs_allowed = 0;

    if (aux_loss > slave_requirements[6].current) {
        slaves -= slave_requirements[6].current;
        slave_requirements[6].current = 0;
    } else {
        slaves -= aux_loss;
        slave_requirements[6].current -= aux_loss;
    }
    if (slaves <= 0) slaves = 4;
}
