// D:\C2\CODE\census.c

#include "c2_data.h"
#include "c2_types.h"

/* ── TU-owned file-scope variables (PS.EXE _BSS, original declaration
   order).  Recovered so the functional rebuild (`c2 rebuild`) links
   self-sustained -- no auto-stubbed storage.  Extern decls: c2_data.h. */
int temp_demand_count[16];

// FUNCTION: C2 0x441C9
// WIN: 0x004304c0
// Lines 36–69
//
// Forum-screen census refresher.  Saves the four "accident"
// timers (fire / wall / road / plague), bumps them to a
// far-future tick (0xf423f ≡ 999_999) so nothing fires
// during this pass, runs the full census pipeline
// (take_census 0x50 → get_census 1 → covers → regroad web
// → region_census → culture/prosperity/empire criteria),
// nudges evolve_clock past the 0xc2..0xca window if it's
// stuck inside, then restores the saved fire/wall/road
// accidents only when the relevant cover is below 100%
// (so a high-coverage city doesn't get penalised on
// reopen).  Plague accident is always restored.
void forum_update_census(void)
{
    int saved_plague;
    int saved_fire;
    int saved_wall;
    int saved_road;

    saved_fire = fire_accident;
    fire_accident = 0xf423f;
    saved_wall = wall_accident;
    wall_accident = 0xf423f;
    saved_road = road_accident;
    road_accident = 0xf423f;
    saved_plague = plague_accident;
    plague_accident = 0xf423f;

    evolve_row = 0;
    take_census(0x50);
    get_census(1);
    slave_warning = 0;
    get_fire_cover();
    get_wall_cover();
    get_road_cover();
    get_water_cover();
    get_regroad_web(reg_city_x, reg_city_y);
    region_census();
    adjust_culture_criteria();
    adjust_proserity_criteria();
    adjust_empire_criteria();

    if (evolve_clock >= 0xc2 && evolve_clock < 0xca) {
        evolve_clock = 0xcb;
    }

    if (fire_cover < 0x64) fire_accident = saved_fire;
    if (wall_cover < 0x64) wall_accident = saved_wall;
    if (road_cover < 0x64) road_accident = saved_road;
    plague_accident = saved_plague;
}

// FUNCTION: C2 0x442B9
// WIN: 0x004305eb
// Lines 71–145
//
// Reset every per-game census counter: accident timers seeded to
// 0xf423f (999_999, "never"), all rate/account/totals fields zeroed,
// last-years stats cleared, this_years_denarii latched from denarii,
// and the 16-slot industry[] table emptied.  In peace mode also seeds
// industry[i].city_supply from city_level_good_supply[i] and stamps
// the alternating-status pattern (0 for even indices, 2 for odd).
void init_census(void)
{
    int i;

    road_accident   = 999999;
    fire_accident   = 999999;
    wall_accident   = 999999;
    region_accident = 999999;
    plague_accident = 999999;
    revolt_accident = 999999;

    pop_tax_last_count         = 0;
    ind_tax_last_count         = 0;
    pop_tax_running_total      = 0;
    pop_tax_counts             = 0;
    ind_tax_running_total      = 0;
    ind_tax_counts             = 0;
    current_construction_cost  = 0;
    current_operating_cost     = 0;
    stolen_denarii             = 0;
    current_gdp                = 0;
    rolling_profit             = 0;
    moving_tribute             = 0;
    average_pop_tax_denariis   = 0;
    average_pop_tax_asses      = 0;
    average_ind_tax_denariis   = 0;
    average_ind_tax_asses      = 0;
    account_total              = 0;
    account_pop_tax            = 0;
    account_ind_tax            = 0;
    account_construction_cost  = 0;
    account_operating_cost     = 0;
    account_tribute            = 0;
    max_population             = 0;
    this_years_population      = 0;
    this_years_denarii         = denarii;
    this_years_pop_tax         = 0;
    this_years_ind_tax         = 0;
    last_years_population      = 0;
    last_years_denarii         = 0;
    last_years_pop_tax         = 0;
    last_years_ind_tax         = 0;

    fire_rate = 0; road_rate = 0; wall_rate = 0;
    water_trouble_rate = 0;

    no_of_ports = 0; no_of_shipyards = 0; no_of_warehouses = 0; no_of_workcamps = 0;
    no_of_quarrys = 0; no_of_mines = 0; no_of_farms = 0; no_of_trading_posts = 0;
    no_of_border_towns = 0; no_of_towns = 0; no_of_villages = 0;

    for (i = 0; i < 16; i++) {
        industry[i].status      = 0;
        industry[i].supply      = 0;
        industry[i].delivered   = 0;
        industry[i].unit_size   = 0;
        industry[i].count       = 0;
        industry[i].has_supply  = 0;
        industry[i].city_supply = 0;
        industry[i].supply_pipeline[0]     = 0;
        industry[i].supply_pipeline[1]     = 0;
        industry[i].supply_pipeline[2]     = 0;

        if (c2inf.peace_mode != 0) {
            industry[i].city_supply = city_level_good_supply[i];
            industry[i].status      = i & 1;
            if (industry[i].status != 0) industry[i].status++;
        }
    }
}

// FUNCTION: C2 0x4446D
// WIN: 0x00430923
// Lines 147–265
//
// Roll the freshly-accumulated *_pass_count tallies (built up
// during the monthly map sweep) into their published _count /
// _running_count counterparts that the rest of the engine reads.
// Also fires the population-milestone warning chain, recomputes
// slave_requirements and per-industry supply/demand, and — only
// when called with quiet=0 — runs the trouble checks and tax
// updates.
//
//   quiet (eax)
//     0 = full monthly pass: bump no_of_census_passes, run
//         warnings, run trouble + tax.
//     1 = silent refresh (used by forum_update_census): copy the
//         counts but skip trouble + tax.
void get_census(int quiet)
{
    int i;

    if (quiet == 0) no_of_census_passes++;

    /* --- Bulk pass_count → _count / _running_count copy ------------ */
    population_running_count       = population_pass_count;
    structure_running_count        = structure_pass_count;
    road_running_count             = road_pass_count;
    fire_running_count             = fire_pass_count;
    plague_running_count           = plague_pass_count;
    fountains_count                = fountains_pass_count;
    baths_count                    = baths_pass_count;
    supplied_fountains_count       = supplied_fountains_pass_count;
    supplied_baths_count           = supplied_baths_pass_count;
    large_forums_count             = large_forums_pass_count;
    medium_forums_count            = medium_forums_pass_count;
    small_forums_count             = small_forums_pass_count;
    forts_count                    = forts_pass_count;
    prefectures_count              = prefectures_pass_count;
    barracks_count                 = barracks_pass_count;
    large_temples_count            = large_temples_pass_count;
    med_temples_count              = med_temples_pass_count;
    small_temples_count            = small_temples_pass_count;
    large_temples_culture_count    = large_temples_culture_pass_count;
    med_temples_culture_count      = med_temples_culture_pass_count;
    small_temples_culture_count    = small_temples_culture_pass_count;
    large_robbery_count            = large_robbery_pass_count;
    med_robbery_count              = med_robbery_pass_count;
    small_robbery_count            = small_robbery_pass_count;
    hospitals_count                = hospitals_pass_count;
    accessed_hospitals_count       = accessed_hospitals_pass_count;
    libraries_count                = libraries_pass_count;
    accessed_libraries_count       = accessed_libraries_pass_count;
    grammaticus_count              = grammaticus_pass_count;
    rhetor_count                   = rhetor_pass_count;
    grammaticus_culture_count      = grammaticus_culture_pass_count;
    rhetor_culture_count           = rhetor_culture_pass_count;
    theatre_count                  = theatre_pass_count;
    odium_count                    = odium_pass_count;
    arena_count                    = arena_pass_count;
    colosseum_count                = colosseum_pass_count;
    circus_count                   = circus_pass_count;
    circus_maximus_count           = circus_maximus_pass_count;
    theatre_culture_count          = theatre_culture_pass_count;
    odium_culture_count            = odium_culture_pass_count;
    arena_culture_count            = arena_culture_pass_count;
    colosseum_culture_count        = colosseum_culture_pass_count;
    circus_culture_count           = circus_culture_pass_count;
    circus_maximus_culture_count   = circus_maximus_culture_pass_count;
    business_count                 = business_pass_count;
    market_count                   = market_pass_count;
    plaza_culture_count            = plaza_culture_pass_count;
    gardens_culture_count          = gardens_culture_pass_count;

    /* Derived totals */
    water_running_count = supplied_fountains_count + supplied_baths_count;
    temples_count       = large_temples_count + med_temples_count + small_temples_count;
    robbery_count       = large_robbery_count  + med_robbery_count  + small_robbery_count;

    /* --- Publish population + maintain high-water + warnings ------- */
    population = population_running_count;
    if (population > max_population) max_population = population;

    if      (population >= 200   && warned_city_size == 0)  { put_message(0x68, 0, 10); warned_city_size++; }
    else if (population >= 500   && warned_city_size == 1)  { put_message(0x69, 0, 10); warned_city_size++; }
    else if (population >= 1000  && warned_city_size == 2)  { put_message(0x6a, 0, 10); warned_city_size++; }
    else if (population >= 2000  && warned_city_size == 3)  { put_message(0x6b, 0, 10); warned_city_size++; }
    else if (population >= 5000  && warned_city_size == 4)  { put_message(0x6c, 0, 10); warned_city_size++; }
    else if (population >= 10000 && warned_city_size == 5)  { put_message(0x6d, 0, 10); warned_city_size++; }
    else if (population >= 20000 && warned_city_size == 6)  { put_message(0x6e, 0, 10); warned_city_size++; }
    else if (population >= 30000 && warned_city_size == 7)  { put_message(0x6f, 0, 10); warned_city_size++; }
    else if (population >= 40000 && warned_city_size == 8)  { put_message(0x70, 0, 10); warned_city_size++; }
    /* New-structure-available chain */
    if      (population >= 400   && warned_new_struct == 0) { put_message(0x73, 0, 10); new_structure_is = 0xb2; warned_new_struct++; }
    else if (population >= 800   && warned_new_struct == 1) { put_message(0x73, 0, 10); new_structure_is = 0xe6; warned_new_struct++; }
    else if (population >= 1200  && warned_new_struct == 2) { put_message(0x73, 0, 10); new_structure_is = 0xf5; warned_new_struct++; }
    else if (population >= 1800  && warned_new_struct == 3) { put_message(0x73, 0, 10); new_structure_is = 0xb6; warned_new_struct++; }
    else if (population >= 2400  && warned_new_struct == 4) { put_message(0x73, 0, 10); new_structure_is = 0xe8; warned_new_struct++; }
    else if (population >= 4800  && warned_new_struct == 5) { put_message(0x73, 0, 10); new_structure_is = 0xed; warned_new_struct++; }

    /* --- slave_requirements demand --------------------------------- */
    slave_requirements[1].max = fire_running_count      / 8;
    slave_requirements[2].max = road_running_count      / 8;
    slave_requirements[3].max = water_running_count     * 2;
    slave_requirements[4].max = structure_running_count / 8;
    slave_requirements[5].max = no_of_workcamps         * 30;
    slave_requirements[6].max = 0;

    /* --- Pre-loop: industry[i].has_supply = temp_demand_count[i] --- */
    for (i = 0; i < 16; i++) {
        industry[i].has_supply = temp_demand_count[i];
    }

    if (quiet == 0) {
        /* Full per-industry refresh + shift the supply window. */
        for (i = 0; i < 16; i++) {
            industry[i].has_supply = temp_demand_count[i];
            industry[i].unit_size  = temp_demand_count[i];
            if (temp_demand_count[i] != 0) industry[i].supply_pipeline[0] = population / temp_demand_count[i];
            else                           industry[i].supply_pipeline[0] = 0;
            industry[i].supply_pipeline[2] = industry[i].supply_pipeline[1];
            industry[i].supply_pipeline[1] = 0;
        }
    }

    hospital_coverage();
    library_coverage();
    employment();

    if (quiet != 0) return;

    slave_warning = 0;
    fire_trouble();
    road_trouble();
    water_trouble();
    wall_trouble();
    running_pop_tax();
    running_ind_tax();
}

// FUNCTION: C2 0x44A94
// WIN: 0x0043107a
// Lines 269–528
//
// Monthly map sweep that builds up the *_pass_count tally for the
// get_census follow-up; `rows` is the number of 20-byte-per-cell
// rows to scan this slice.  When evolve_row == 0 (first slice of
// the month) also zeroes temp_demand_count[] and every
// *_pass_count global before sweeping.  For each cell, dispatches
// on the kind byte: plaza/garden tiles bump the culture pass count;
// event-trigger flags (road wear-out, wall collapse, fire) tick
// their pass count until it hits the per-cell accident threshold,
// at which point the event fires and the threshold is pushed to
// ~1 million; housing tiles feed population + income; forums,
// temples, and entertainment buildings tally their per-tier count
// plus a culture count via test_for_any_admin; service tiles
// (baths, fountains, prefectures, barracks, hospitals, libraries,
// business, market) bump their own counters and business cells
// also drive the temp_demand_count[] industry-supply vector.
// NOTE: fire ticks for kinds OUTSIDE 0xbc..0xe2 (PS L386 jl/jle
// polarity + WIN oracle both confirm the inverted range).
//

// BYTE-EXACT (2026-07-10): the Windows local census recovered the
// original C89 local inventory hidden by Watcom's optimiser: `row` is
// reused by the reset loop, wall terrain has its own byte local, and
// the business range check reuses `cul` rather than `rob`.  Those fixes
// make the 13 local widths/use counts agree exactly with MSVC /Od.
// Rule 115/28a declaration order is codegen-load-bearing here: `cul`
// precedes `kind`, while `terrain` follows `rob`.  That ConfBefore order
// gives PS's EDX/EBX/EAX seats throughout; all 175 line transitions are
// clean.  The remaining seven Windows structural rows are the known
// loop-compare port drift plus unlinked-relocation artefacts.
void take_census(int rows)
{
    int row;
    int col;
    unsigned char cul;
    int tier;
    unsigned char kind;
    unsigned char rob;
    unsigned char terrain;
    unsigned char sick;
    unsigned char busy;
    unsigned char edu;
    unsigned char dem;
    int saved_sptr;
    unsigned char flags;

    if (evolve_row == 0) {
        for (row = 0; row < 16; row++) temp_demand_count[row] = 0;
        population_pass_count                = 0;
        pop_income_pass_count                = 0;
        ind_income_pass_count                = 0;
        structure_pass_count                 = 0;
        road_pass_count                      = 0;
        fire_pass_count                      = 0;
        plague_pass_count                    = 0;
        fountains_pass_count                 = 0;
        baths_pass_count                     = 0;
        supplied_fountains_pass_count        = 0;
        supplied_baths_pass_count            = 0;
        large_forums_pass_count              = 0;
        medium_forums_pass_count             = 0;
        small_forums_pass_count              = 0;
        forts_pass_count                     = 0;
        prefectures_pass_count               = 0;
        barracks_pass_count                  = 0;
        large_temples_pass_count             = 0;
        med_temples_pass_count               = 0;
        small_temples_pass_count             = 0;
        large_temples_culture_pass_count     = 0;
        med_temples_culture_pass_count       = 0;
        small_temples_culture_pass_count     = 0;
        large_robbery_pass_count             = 0;
        med_robbery_pass_count               = 0;
        small_robbery_pass_count             = 0;
        hospitals_pass_count                 = 0;
        accessed_hospitals_pass_count        = 0;
        libraries_pass_count                 = 0;
        accessed_libraries_pass_count        = 0;
        grammaticus_pass_count               = 0;
        rhetor_pass_count                    = 0;
        grammaticus_culture_pass_count       = 0;
        rhetor_culture_pass_count            = 0;
        theatre_pass_count                   = 0;
        odium_pass_count                     = 0;
        arena_pass_count                     = 0;
        colosseum_pass_count                 = 0;
        circus_pass_count                    = 0;
        circus_maximus_pass_count            = 0;
        theatre_culture_pass_count           = 0;
        odium_culture_pass_count             = 0;
        arena_culture_pass_count             = 0;
        colosseum_culture_pass_count         = 0;
        circus_culture_pass_count            = 0;
        circus_maximus_culture_pass_count    = 0;
        business_pass_count                  = 0;
        market_pass_count                    = 0;
        plaza_culture_pass_count             = 0;
        gardens_culture_pass_count           = 0;
    }

    cm_sptr = evolve_row * 1600;  /* 80 cols × 20 bytes per cell */

    for (row = 0; rows > row; row++) {
        for (col = 0; col < 80; col++, cm_sptr += 20) {
            flags = (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).terrain & 0x27;
            kind  = (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).base_kind;

            /* Plaza / gardens overlay -------------------------- */
            if (kind >= 0x7c && kind <= 0x7e) {
                cul = (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).range_flag & 0x0c;
                if (cul) plaza_culture_pass_count++;
            } else if (kind >= 0x78 && kind <= 0x7b) {
                cul = (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).range_flag & 0x0c;
                if (cul) gardens_culture_pass_count++;
            }

            if (flags == 0) continue;

            /* Event-trigger branches --------------------------- */
            if (flags & 0x20) {
                /* Road wear-out trigger */
                if (road_pass_count != road_accident) road_pass_count++;
                else {
                    destroy_an_atom(cm_sptr, 0); road_accident = 0xf423f;
                }
            }
            else if (flags & 0x02) {
                /* Wall collapse trigger */
                if (structure_pass_count != wall_accident) structure_pass_count++;
                else {
                    saved_sptr = cm_sptr;
                    terrain = (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).terrain;
                    if (terrain & 0xc0) unflag_all_cm(3, 0xdf);
                    clear_an_area(col, evolve_row + row,
                                  col, evolve_row + row);
                    cm_sptr           = saved_sptr;
                    wall_accident     = 0xf423f;
                    particles_cleared = 0;
                }
            }
            else if (flags & 0x04) {
                kind = (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).base_kind;
                if (kind == 0xbf) forts_pass_count++;
            }
            else {

            /* Fire (anything OUTSIDE kind 0xBC..0xE2) ---------- */
            if (kind < 0xbc || kind > 0xe2) {
                if (fire_pass_count != fire_accident) fire_pass_count++;
                else {
                    destroy_an_atom(cm_sptr, 1);
                    put_message(0x52, cm_sptr, 20);
                    fire_accident = 0xf423f;
                    continue;
                }
            }

            /* Plague (housing kinds only) ---------------------- */
            if (kind >= 0x82 && kind <= 0xa1) {
                if (plague_accident == plague_pass_count) {
                    plague_an_atom(cm_sptr);
                    put_message(0x51, cm_sptr, 22);
                    plague_accident = 0xf423f;
                    continue;
                }
                sick = (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).fpu_flag & 0x30;
                if (sick == 0x30) plague_pass_count++;
            }

            /* If the cell is busy / under construction, skip the
             * service-side bookkeeping. */
            busy = (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).activity_a & 0x0f;
            if (busy != 0) continue;

            /* ---------------- Per-kind dispatch ---------------- */
            if (kind >= 0x82 && kind <= 0xa1) {
                kind -= 0x82;
                population_pass_count += houses_to_people[kind];
                cul = (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).range_flag & 0x0c;
                if (cul) pop_income_pass_count += houses_to_income[kind];
            } else if (kind >= 0xae && kind <= 0xb9) {
                kind -= 0xae;
                if      (kind < 4) small_forums_pass_count++;
                else if (kind < 8) medium_forums_pass_count++;
                else               large_forums_pass_count++;
            } else if (kind >= 0xa2 && kind <= 0xa5) {
                small_temples_pass_count++;
                rob = (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).range_flag & 0x30;
                cul = (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).range_flag & 0x0c;
                if (cul) small_temples_culture_pass_count++;
                if (rob == 0) small_robbery_pass_count++;
            } else if (kind >= 0xa6 && kind <= 0xa9) {
                med_temples_pass_count++;
                rob = (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).range_flag & 0x30;
                if (test_for_any_admin(cm_sptr, 2)) med_temples_culture_pass_count++;
                if (rob == 0) med_robbery_pass_count++;
            } else if (kind >= 0xaa && kind <= 0xad) {
                large_temples_pass_count++;
                rob = (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).range_flag & 0x30;
                if (test_for_any_admin(cm_sptr, 3)) large_temples_culture_pass_count++;
                if (rob == 0) large_robbery_pass_count++;
            } else if (kind >= 0xdf && kind <= 0xe2) {
                baths_pass_count++;
                edu = (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).education & 4;
                if (edu) supplied_baths_pass_count++;
            } else if (kind >= 0xdb && kind <= 0xde) {
                fountains_pass_count++;
                edu = (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).education & 4;
                if (edu) supplied_fountains_pass_count++;
            } else if (kind == 0xe3) prefectures_pass_count++;
              else if (kind == 0xe4) barracks_pass_count++;
              else if (kind == 0xf3) {
                grammaticus_pass_count++;
                if (test_for_any_admin(cm_sptr, 2)) grammaticus_culture_pass_count++;
            } else if (kind == 0xf4) {
                rhetor_pass_count++;
                if (test_for_any_admin(cm_sptr, 3)) rhetor_culture_pass_count++;
            } else if (kind == 0xe5) {
                theatre_pass_count++;
                if (test_for_any_admin(cm_sptr, 2)) theatre_culture_pass_count++;
            } else if (kind == 0xe6) {
                odium_pass_count++;
                if (test_for_any_admin(cm_sptr, 2)) odium_culture_pass_count++;
            } else if (kind == 0xe7) {
                arena_pass_count++;
                if (test_for_any_admin(cm_sptr, 3)) arena_culture_pass_count++;
            } else if (kind == 0xe8) {
                colosseum_pass_count++;
                if (test_for_any_admin(cm_sptr, 3)) colosseum_culture_pass_count++;
            } else if (kind == 0xe9 || kind == 0xeb) {
                circus_pass_count++;
                if (test_for_any_admin(cm_sptr, 3)) circus_culture_pass_count++;
            } else if (kind == 0xed || kind == 0xef) {
                circus_maximus_pass_count++;
                if (test_for_any_admin(cm_sptr, 4)) circus_maximus_culture_pass_count++;
            } else if (kind >= 0xfc && kind <= 0xff) { market_pass_count++;
            } else if (kind == 0xfb) {
                hospitals_pass_count++;
                if (test_perimeter_for_road_and_forum(col, evolve_row + row, 3, 0)) accessed_hospitals_pass_count++;
            } else if (kind == 0xf5) {
                libraries_pass_count++;
                if (test_perimeter_for_road_and_forum(col, evolve_row + row, 3, 0)) accessed_libraries_pass_count++;
            } else if (kind == 0xfa) {
                business_pass_count++;
                dem = (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).business & 0x0f;
                temp_demand_count[dem]++;
                cul = (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).range_flag & 0x0c;
                if (cul) {
                    tier = (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).building & 0xf0;
                    tier >>= 4;
                    ind_income_pass_count += tier * 0x46;
                }
            }
            } /* event-trigger else (fire/plague/dispatch) */
        } }
}

// FUNCTION: C2 0x452D0
// WIN: 0x00431c26
// Lines 533–577
//
// Test the perimeter around the current cm_sptr square footprint for a
// road/forum access tile.  `x`,`y` are the footprint's top-left city-map
// coordinates and `size` is its width/height.  If `road_only` is nonzero,
// any neighbouring road bit (city_map+1 bit 0x20) succeeds; otherwise
// the neighbouring road must also carry forum bits in city_map+0x0a
// mask 0x0c.  Returns 1 on first qualifying perimeter cell, else 0.
int test_perimeter_for_road_and_forum(int x, int y, int size, int road_only)
{
    int i;
    int p;

    if (y > 0) {
        p = cm_sptr - 1600;
        for (i = 0; i < size; i++, p += 20) {
            if (((*(struct city_cell *)((unsigned char *)city_map + (p))).terrain & 0x20) != 0) {
                if (road_only != 0) return 1;
                if (((*(struct city_cell *)((unsigned char *)city_map + (p))).range_flag & 0x0c) != 0) return 1;
            }
        }
    }
    if (80 - size > y) {
        p = cm_sptr + size * 1600;
        for (i = 0; i < size; i++, p += 20) {
            if (((*(struct city_cell *)((unsigned char *)city_map + (p))).terrain & 0x20) != 0) {
                if (road_only != 0) return 1;
                if (((*(struct city_cell *)((unsigned char *)city_map + (p))).range_flag & 0x0c) != 0) return 1;
            }
        }
    }
    if (x > 0) {
        p = cm_sptr - 20;
        for (i = 0; i < size; i++, p += 1600) {
            if (((*(struct city_cell *)((unsigned char *)city_map + (p))).terrain & 0x20) != 0) {
                if (road_only != 0) return 1;
                if (((*(struct city_cell *)((unsigned char *)city_map + (p))).range_flag & 0x0c) != 0) return 1;
            }
        }
    }
    if (x < 80 - size) {
        p = cm_sptr + size * 20;
        for (i = 0; i < size; i++, p += 1600) {
            if (((*(struct city_cell *)((unsigned char *)city_map + (p))).terrain & 0x20) != 0) {
                if (road_only != 0) return 1;
                if (((*(struct city_cell *)((unsigned char *)city_map + (p))).range_flag & 0x0c) != 0) return 1;
            }
        }
    }
    return 0;
}

// FUNCTION: C2 0x45422
// WIN: 0x00431e5e
// Lines 579–592
//
// Tests an n×n cell square starting at byte-offset `cm_ptr` into
// city_map for any cell whose `range_flag` (+0x0A) has bits 2 or 3
// set (mask 0x0C — "any admin building present").  Returns 1 on
// the first hit, 0 if none.  Used by census passes to detect e.g.
// any temple / forum within a building's footprint.
int test_for_any_admin(int cm_ptr, int n)
{
    int i;
    int j;
    int eax = cm_ptr;
    int stride = 1600 - n * 20;
    for (i = 0; i < n; i++, eax += stride) {
        for (j = 0; j < n; j++, eax += 20) {
            char b = (*(struct city_cell *)((unsigned char *)city_map + (eax))).range_flag & 0x0C;
            if (b) {
                return 1;
            }
        }
    }
    return 0;
}

// FUNCTION: C2 0x4546C
// WIN: 0x00431ef8
// Lines 596–609
//
// Per-tick fire-trouble accumulator: fire_accident defaults to
// 999_999 (effectively never).  When the city has any
// fire-fighter requirement, increment fire_rate by
// (100 - fire_cover); cap below at 0; once it overflows 100,
// pull a fresh fire_accident slot via get_rand_max(fire_pass_count)
// and reset fire_rate to (rate % 100).
void fire_trouble(void)
{
    fire_accident = 0xf423f;
    if (slave_requirements[1].max == 0) return;
    get_fire_cover();
    fire_rate += 0x64 - fire_cover;
    if (fire_rate <= 0) fire_rate = 0;
    if (fire_rate < 0x64) return;
    fire_rate = fire_rate % 0x64;
    fire_accident = get_rand_max(fire_pass_count);
}

// FUNCTION: C2 0x454DD
// WIN: 0x00431f7f
// Lines 611–623
//
// Sister of fire_trouble for the road network.  Reads
// slave_requirements[2].max as the gate, road_cover/road_rate
// as the per-tick deltas, and pulls road_accident from
// get_rand_max(road_pass_count) when rate overflows 100.
void road_trouble(void)
{
    road_accident = 0xf423f;
    if (slave_requirements[2].max == 0) return;
    get_road_cover();
    road_rate += 0x64 - road_cover;
    if (road_rate <= 0) road_rate = 0;
    if (road_rate < 0x64) return;
    road_rate = road_rate % 0x64;
    road_accident = get_rand_max(road_pass_count);
}

// FUNCTION: C2 0x4554E
// WIN: 0x00432006
// Lines 626–645
//
// Map water_cover (per get_water_cover) onto a 0..0x10 water_trouble
// rating using a 14-band ladder.  The 0 → 2 jump (band 1 skipped)
// matches PS.EXE: a band rating of 1 is never produced.
void water_trouble(void)
{
    get_water_cover();
    if (water_cover <= 0x0a) { water_trouble_rate = 0;    return; }
    if (water_cover <= 0x16) { water_trouble_rate = 2;    return; }
    if (water_cover <= 0x1c) { water_trouble_rate = 3;    return; }
    if (water_cover <= 0x22) { water_trouble_rate = 4;    return; }
    if (water_cover <= 0x28) { water_trouble_rate = 5;    return; }
    if (water_cover <= 0x2e) { water_trouble_rate = 6;    return; }
    if (water_cover <= 0x34) { water_trouble_rate = 7;    return; }
    if (water_cover <= 0x3a) { water_trouble_rate = 8;    return; }
    if (water_cover <= 0x40) { water_trouble_rate = 9;    return; }
    if (water_cover <= 0x46) { water_trouble_rate = 0xa;  return; }
    if (water_cover <= 0x4c) { water_trouble_rate = 0xb;  return; }
    if (water_cover <= 0x52) { water_trouble_rate = 0xc;  return; }
    if (water_cover <= 0x58) { water_trouble_rate = 0xd;  return; }
    if (water_cover <= 0x5e) { water_trouble_rate = 0xe;  return; }
    if (water_cover <  0x64) { water_trouble_rate = 0xf;  return; }
    water_trouble_rate = 0x10;
}

// FUNCTION: C2 0x45674
// WIN: 0x004321c4
// Lines 647–659
//
// Sister of fire_trouble for walls.  Reads
// slave_requirements[4].max as the gate, wall_cover/wall_rate
// as the per-tick deltas, and pulls wall_accident from
// get_rand_max(structure_pass_count) when rate overflows 100.
void wall_trouble(void)
{
    wall_accident = 0xf423f;
    if (slave_requirements[4].max == 0) return;
    get_wall_cover();
    wall_rate += 0x64 - wall_cover;
    if (wall_rate <= 0) wall_rate = 0;
    if (wall_rate < 0x64) return;
    wall_rate = wall_rate % 0x64;
    wall_accident = get_rand_max(structure_pass_count);
}

// FUNCTION: C2 0x456E5
// WIN: 0x0043224b
// Lines 661–669
//
// Compute fire-fighter coverage from slave_requirements[1].
// Sets fire_cover to:
//
//   100 if slave_requirements[1].max == 0   (no need)
//   100 if (tutorial_mode != 0 && tutorial_page < 22)
//   else clamp(valueDIVtotal(.current, .max), 0, 100)
//
// When the percentage is < 100, slave_warning is
// incremented (the player needs more workers).
//
// Same shape as get_road_cover / get_wall_cover /
// get_water_cover.
void get_fire_cover(void)
{
    int pct;

    if (slave_requirements[1].max == 0) {
        fire_cover = 100;
        return;
    }
    if (tutorial_mode != 0 && tutorial_page < 22) {
        fire_cover = 100;
        return;
    }
    pct = valueDIVtotal(slave_requirements[1].current,
                        slave_requirements[1].max);
    fire_cover = pct;
    if (pct >= 100) {
        fire_cover = 100;
    } else {
        ++slave_warning;
    }
    if (fire_cover < 0) fire_cover = 0;
}

// FUNCTION: C2 0x4574B
// WIN: 0x004322ed
// Lines 671–679
//
// Sister of get_fire_cover indexed at slave_requirements[2]: sets
// road_cover to the current/max permille (clamped to [0, 100]),
// pinned at 100 while tutorial_page < 22.
void get_road_cover(void)
{
    int pct;

    if (slave_requirements[2].max == 0) {
        road_cover = 100;
        return;
    }
    if (tutorial_mode != 0 && tutorial_page < 22) {
        road_cover = 100;
        return;
    }
    pct = valueDIVtotal(slave_requirements[2].current,
                        slave_requirements[2].max);
    road_cover = pct;
    if (pct >= 100) {
        road_cover = 100;
    } else {
        ++slave_warning;
    }
    if (road_cover < 0) road_cover = 0;
}

// FUNCTION: C2 0x457B1
// WIN: 0x0043238f
// Lines 681–689
//
// Sister of get_fire_cover indexed at slave_requirements[4]: sets
// wall_cover to the current/max permille (clamped to [0, 100]),
// pinned at 100 while tutorial_page < 22.
void get_wall_cover(void)
{
    int pct;

    if (slave_requirements[4].max == 0) {
        wall_cover = 100;
        return;
    }
    if (tutorial_mode != 0 && tutorial_page < 22) {
        wall_cover = 100;
        return;
    }
    pct = valueDIVtotal(slave_requirements[4].current,
                        slave_requirements[4].max);
    wall_cover = pct;
    if (pct >= 100) {
        wall_cover = 100;
    } else {
        ++slave_warning;
    }
    if (wall_cover < 0) wall_cover = 0;
}

// FUNCTION: C2 0x45817
// WIN: 0x00432431
// Lines 691–699
//
// Sister of get_fire_cover indexed at slave_requirements[3]: sets
// water_cover to the current/max permille (clamped to [0, 100]),
// pinned at 100 while tutorial_page < 22.
void get_water_cover(void)
{
    int pct;

    if (slave_requirements[3].max == 0) {
        water_cover = 100;
        return;
    }
    if (tutorial_mode != 0 && tutorial_page < 22) {
        water_cover = 100;
        return;
    }
    pct = valueDIVtotal(slave_requirements[3].current,
                        slave_requirements[3].max);
    water_cover = pct;
    if (pct >= 100) {
        water_cover = 100;
    } else {
        ++slave_warning;
    }
    if (water_cover < 0) water_cover = 0;
}

// FUNCTION: C2 0x4587D
// WIN: 0x004324d3
// Lines 701–707
//
// Hospital-coverage indicator.  Computes:
//
//   hospital_cover = (accessed_hospitals_count * 1000) / population
//
// (a permille “how many hospital-slots per resident”
// metric).  If `population < 100` the divide is skipped
// and coverage is pinned at 100 to avoid a low-population
// false alarm.  When `accessed_hospitals_count == 0` the
// indicator stays at 0.
void hospital_coverage(void)
{
    hospital_cover = 0;
    if (accessed_hospitals_count > 0) {
        if (population < 100) {
            hospital_cover = 100;
            return;
        }
        hospital_cover = valueDIVtotal(accessed_hospitals_count * 1000,
                                       population);
    }
}

// FUNCTION: C2 0x458CA
// WIN: 0x0043253b
// Lines 709–715
//
// Library-coverage indicator.  Same shape as
// hospital_coverage but with multiplier 1200 (one library
// per 1200 residents is the target).
void library_coverage(void)
{
    library_cover = 0;
    if (accessed_libraries_count > 0) {
        if (population < 100) {
            library_cover = 100;
            return;
        }
        library_cover = valueDIVtotal(accessed_libraries_count * 1200,
                                      population);
    }
}

// FUNCTION: C2 0x45919
// WIN: 0x004325a3
// Lines 718–746
//
// Recompute the city's employment rate from the per-building pass
// counters that take_census populated.  Each building type
// contributes a fixed number of jobs per active instance (10..120,
// see the body); the totals are summed into `employees`.
// employment_rate = (employees * 100) / population +
// conscription_rate, clamped to 100.  Tiny colonies (population
// < 50) are pinned to 100% so the per-capita figure isn't dominated
// by setup-period noise.
void employment(void)
{
    employees = 0;
    employees += small_forums_pass_count          *  40;
    employees += medium_forums_pass_count         *  80;
    employees += large_forums_pass_count          * 120;
    employees += small_temples_pass_count         *  10;
    employees += med_temples_pass_count           *  20;
    employees += large_temples_pass_count         *  30;
    employees += supplied_baths_pass_count        *  20;
    employees += prefectures_pass_count           *  25;
    employees += barracks_pass_count              *  30;
    employees += grammaticus_pass_count           *  30;
    employees += rhetor_pass_count                *  80;
    employees += accessed_libraries_pass_count    *  60;
    employees += theatre_pass_count               *  25;
    employees += odium_pass_count                 *  30;
    employees += arena_pass_count                 *  50;
    employees += colosseum_pass_count             *  60;
    employees += circus_pass_count                *  80;
    employees += circus_maximus_pass_count        * 100;
    employees += accessed_hospitals_pass_count    *  80;
    employees += market_pass_count                *  20;
    employees += business_pass_count              *  60;

    employment_rate  = valueDIVtotal(employees, population);
    employment_rate += conscription_rate;

    if (population < 50) employment_rate = 100;
    if (employment_rate > 100) employment_rate = 100;
}

// FUNCTION: C2 0x45B7B
// WIN: 0x00432787
// Lines 749–757
//
// Accumulate this turn's pop tax into the running total.
// Multiplies the per-cohort income by the income multiple,
// scales by the tax rate, and bumps the cohort count.
void running_pop_tax(void)
{
    pop_tax_running_total += totalXpercent(
        pop_income_pass_count * income_multiple, pop_tax_rate);
    pop_tax_last_count = pop_income_pass_count;
    pop_tax_counts++;
}

// FUNCTION: C2 0x45BAB
// WIN: 0x004327cc
// Lines 759–767
//
// Mirror of running_pop_tax for industry tax: accumulates this
// turn's industry tax into ind_tax_running_total and bumps the
// cohort count.
void running_ind_tax(void)
{
    ind_tax_running_total += totalXpercent(
        ind_income_pass_count * income_multiple, ind_tax_rate);
    ind_tax_last_count = ind_income_pass_count;
    ind_tax_counts++;
}

// FUNCTION: C2 0x45BDB
// WIN: 0x00432811
// Lines 773–837
//
// Walk the 60×60 region map once per month and tally building
// counts per category (workcamps, mines, ports, etc.) plus the
// four cardinal empire connections.  (*(struct region_cell *)((unsigned char *)region_map + ())).base_kind cells are
// 8 bytes apiece; port tiles encode connection slots in flag byte +7,
// while border-town tiles encode the same four slots directly as kind
// 0x98..0x9B.  Reads each cell's kind byte, edge flag (bit 0x20 =
// empire-connection / city-edge), and the low-bit ignore mask /
// connection-slot id from the secondary flag byte.  Peace mode
// (c2inf.peace_mode = 1) short-circuits the scan and pre-fills all
// four empire_connections[] slots so the diplomacy UI shows the
// player as fully linked.
void region_census(void)
{
    int i;
    int sy;
    int sx;
    unsigned char kind;
    unsigned char flag7;
    unsigned char flag3;
    unsigned char slot;

    no_of_ports               = 0;
    no_of_shipyards           = 0;
    no_of_warehouses          = 0;
    no_of_workcamps           = 0;
    no_of_quarrys             = 0;
    no_of_mines               = 0;
    no_of_farms               = 0;
    no_of_trading_posts       = 0;
    no_of_border_towns        = 0;
    no_of_towns               = 0;
    no_of_villages            = 0;
    no_of_connected_towns     = 0;
    no_of_empire_connections  = 0;

    for (i = 0; i < 4; i++)
        empire_connections[i] = 0;

    if (c2inf.peace_mode) {
        no_of_empire_connections = 4;
        for (i = 0; i < 4; i++)
            empire_connections[i] = 1;
        return;
    }

    sy = 0;
    cm_sptr = 0;
    for ( ; sy < 0x3c; sy++) {
    for (sx = 0; sx < 0x3c; sx++, cm_sptr += 8) {
    flag7 = (*(struct region_cell *)((unsigned char *)region_map + (cm_sptr))).occupant & 3;
    /* Warehouses (kind 0xD4) ignore the low-bit ignore mask. */
    if ((*(struct region_cell *)((unsigned char *)region_map + (cm_sptr))).base_kind == 0xd4) flag7 = 0;
    if (flag7 != 0) continue;

    kind = (*(struct region_cell *)((unsigned char *)region_map + (cm_sptr))).base_kind;
    if      (kind == 0xd3) { no_of_workcamps++; }
    else if (kind == 0xd4) { no_of_warehouses++; }
    else if (kind == 0xd5) { no_of_shipyards++; }
    else if (kind >= 0xdc && kind <= 0xdf) { no_of_farms++; }
    else if (kind >= 0xe0 && kind <= 0xe3) { no_of_mines++; }
    else if (kind >= 0xe4 && kind <= 0xe7) { no_of_quarrys++; }
    else if (kind >= 0xe8 && kind <= 0xeb) { no_of_trading_posts++; }
    else if (kind >= 0xec && kind <= 0xef) {
        no_of_ports++;
        flag3 = (*(struct region_cell *)((unsigned char *)region_map + (cm_sptr))).edge_bits & 0x20;
        if (flag3) {
            slot = (*(struct region_cell *)((unsigned char *)region_map + (cm_sptr))).occupant & 0x60;
            if (slot == 0 && empire_connections[0] == 0) {
                empire_connections[0] = 1;
                no_of_empire_connections++;
            } else if (slot == 0x20 && empire_connections[1] == 0) {
                empire_connections[1] = 1;
                no_of_empire_connections++;
            } else if (slot == 0x40 && empire_connections[2] == 0) {
                empire_connections[2] = 1;
                no_of_empire_connections++;
            } else if (slot == 0x60 && empire_connections[3] == 0) {
                empire_connections[3] = 1;
                no_of_empire_connections++;
            }
        }
    }
    else if (kind >= 0x93 && kind <= 0x96) { no_of_villages++; }
    else if (kind >= 0x98 && kind <= 0x9b) {
        no_of_border_towns++;
        flag3 = (*(struct region_cell *)((unsigned char *)region_map + (cm_sptr))).edge_bits & 0x20;
        if (flag3) {
            empire_connections[kind - 0x98] = 1;
            no_of_empire_connections++;
        }
    }
    else if (kind == 0x97) {
        flag7 = (*(struct region_cell *)((unsigned char *)region_map + (cm_sptr))).edge_bits & 0x20;
        if (flag7) no_of_connected_towns++;
        no_of_towns++;
    }
    }
    }
}
