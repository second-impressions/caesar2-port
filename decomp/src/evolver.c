// D:\C2\CODE\evolver.c

#include "c2_data.h"
#include "c2_types.h"

#ifndef _MSC_VER   /* MSVC win-oracle build force-includes c2_funcs.h (typed) */
extern int affected_by_cover1(unsigned char *p, int range, char mask);
extern int affected_by_cover2(unsigned char *p, int range, char mask);
#endif
extern unsigned char *get_ptr_to_corner(unsigned char *base_ptr, int size);

/*
 * DO NOT prototype these -- PS's evolver.c does NOT #include c2_funcs.h,
 */

int stretch_ofsets_2x2[4][3] = {
    { 20, 1620, 1600 },
    { -20, 1580, 1600 },
    { -20, -1620, -1600 },
    { 20, -1580, -1600 }
};

int stretch_ofsets_3x3[4][5] = {
    { 40, 1640, 3240, 3220, 3200 },
    { -20, 1580, 3180, 3200, 3220 },
    { -20, 1580, -1620, -1580, -1600 },
    { 40, 1640, -1560, -1580, -1600 }
};

struct int_delta_rec putouts1[4] = {
    { 0, -1 },
    { 1, 0 },
    { 0, 1 },
    { -1, 0 }
};

struct int_delta_rec putouts2[8] = {
    { 0, -1 },
    { 1, -1 },
    { 2, 0 },
    { 2, 1 },
    { 1, 2 },
    { 0, 2 },
    { -1, 1 },
    { -1, 0 }
};

struct int_delta_rec putouts3[12] = {
    { 0, -1 },
    { 1, -1 },
    { 2, -1 },
    { 3, 0 },
    { 3, 1 },
    { 3, 2 },
    { 2, 3 },
    { 1, 3 },
    { 0, 3 },
    { -1, 2 },
    { -1, 1 },
    { -1, 0 }
};

struct int_delta_rec putouts4[16] = {
    { 0, -1 },
    { 1, -1 },
    { 2, -1 },
    { 3, -1 },
    { 4, 0 },
    { 4, 1 },
    { 4, 2 },
    { 4, 3 },
    { 3, 4 },
    { 2, 4 },
    { 1, 4 },
    { 0, 4 },
    { -1, 3 },
    { -1, 2 },
    { -1, 1 },
    { -1, 0 }
};
/*
 * so these callees are declared IMPLICITLY (K&R `int f()`).  For the
 * `void` helpers that means the caller keeps treating EAX as a live
 * return def after the call, which is load-bearing for register
 * allocation.  Adding the real `void` prototype changes the caller's
 * regalloc and REGRESSES byte-exact siblings -- proven: adding
 * `extern void change_sized(int,int,int,int);` breaks the byte-exact
 * evolve_water_table (ir 0 -> 1) while market_image stays exact.  The
 * int-returning ones (get_reg_buildings_in_radius / get_pop_level)
 * happen to match the implicit `int` anyway.  Kept here, commented, so
 * no future session re-adds them:
 *
 *   extern void change_sized(int bk, int color, int size, int sptr);
 *   extern void change_reg_sized(int rm_byte, int color, int size, int rm_offset);
 *   extern void fill_warehouses_with(int x, int y, int amount, int goods, int refresh);
 *   extern int  get_reg_buildings_in_radius(int x, int y, int span, int radius, unsigned char building_kind);
 */

// FUNCTION: C2 0x3FA14
// WIN: 0x00461b10
// Lines 63–71
//
// Reset every per-tick evolution counter to 0 and prime the region-warehouse inventory at game start / load.
void initiate_evolution(void)
{
    evolve_row = 0;
    evolve_clock = 0;
    evolve_count = 0;
    evolve_tick4 = 0;
    evolve_tick3 = 0;
    check_goods_in_region_warehouses();
}

// FUNCTION: C2 0x3FA3C
// WIN: 0x00461b52
// Lines 73–236
//
// Master tick dispatcher driven by `evolve_clock`.  Sets the per-subsystem debar gates, then
// routes the clock value to the appropriate phase: per-row cell evolve at the start,
// then the `evolve_water_supply_baths_industry` / security / amenity / water-table /
// land-value / forum / fort / security / industrial / fire+plague / shell / census
// passes, ending with the region-evolution and yearly housekeeping.
void citymap_evolution(void)
{
    if (evolve_clock <= 0x50) {
        water_debar = lv_debar = security_debar = industry_debar = unrest_debar = entertainment_debar = education_debar = admin_debar = health_debar = 0;
    } else if (evolve_clock < 0x92) {
        water_debar = lv_debar = security_debar = industry_debar = unrest_debar = entertainment_debar = education_debar = admin_debar = health_debar = 1;
    } else {
        water_debar = lv_debar = security_debar = industry_debar = unrest_debar = entertainment_debar = education_debar = admin_debar = health_debar = 0;
    }

    sooth_mood();

    if      (evolve_clock == 0)       { clear_fire_zones(); }
    else if (evolve_clock < 0x51)     { evolve_row = evolve_clock - 1;
                                         evolve_a_cm_row(); }
    else if (evolve_clock == 0x51)    { clear_all_cm(0xd); }
    else if (evolve_clock == 0x52)    { clear_all_cm(0xf); }
    else if (evolve_clock == 0x53)    { clear_all_cm(0xe); }
    else if (evolve_clock == 0x54)    { clear_all_cm(0xc); }
    else if (evolve_clock == 0x55)    { /* nop */ }
    else if (evolve_clock < 0x5e)     { evolve_row = (evolve_clock - 0x56) * 10;
                                         evolve_water_supply_baths_industry(10); }
    else if (evolve_clock < 0x66)     { evolve_row = (evolve_clock - 0x5e) * 10;
                                         evolve_security_cover(10); }
    else if (evolve_clock < 0x6e)     { evolve_row = (evolve_clock - 0x66) * 10;
                                         evolve_amenity_cover(10); }
    else if (evolve_clock < 0x76)     { evolve_row = (evolve_clock - 0x6e) * 10;
                                         evolve_water_table(10); }
    else if (evolve_clock < 0x7e)     { evolve_row = (evolve_clock - 0x76) * 10;
                                         evolve_land_value(10); }
    else if (evolve_clock < 0x8e)     { evolve_row = (evolve_clock - 0x7e) * 5;
                                         cap_land_value(5); }
    else if (evolve_clock < 0x92)     { security_debar = 1;
                                         evolve_row = (evolve_clock - 0x8e) * 0x14;
                                         evolve_forum_activity(0x14); }
    else if (evolve_clock < 0x96)     { security_debar = 1;
                                         evolve_row = (evolve_clock - 0x92) * 0x14;
                                         evolve_fort_activity(0x14); }
    else if (evolve_clock < 0x9a)     { security_debar = 1;
                                         evolve_row = (evolve_clock - 0x96) * 0x14;
                                         evolve_security_activity(0x14); }
    else if (evolve_clock < 0x9e)     { security_debar = 1;
                                         evolve_row = (evolve_clock - 0x9a) * 0x14;
                                         evolve_industrial_activity(0x14); }
    else if (evolve_clock < 0xa2)     { security_debar = 1;
                                         evolve_row = (evolve_clock - 0x9e) * 0x14;
                                         spread_fire_and_plague_and_unrest(0x14); }
    else if (evolve_clock < 0xaa)     { security_debar = 1;
                                         evolve_row = (evolve_clock - 0xa2) * 10;
                                         push_shell(10); }
    else if (evolve_clock < 0xb2)     { security_debar = 1;
                                         evolve_row = (evolve_clock - 0xaa) * 10;
                                         push_shell(10); }
    else if (evolve_clock < 0xba)     { security_debar = 1;
                                         evolve_row = (evolve_clock - 0xb2) * 10;
                                         push_shell(10); }
    else if (evolve_clock < 0xc2)     { security_debar = 1;
                                         evolve_row = (evolve_clock - 0xba) * 10;
                                         push_shell(10); }
    else if (evolve_clock < 0xca)     { security_debar = 1;
                                         evolve_row = (evolve_clock - 0xc2) * 10;
                                         take_census(10); }
    else if (evolve_clock == 0xca)    { get_census(0); }
    else if (evolve_clock == 0xcb)    { launch_traders();
                                         unflag_all_rm(3, 0xdf); }
    else if (evolve_clock == 0xcc)    { get_regroad_web(reg_city_x, reg_city_y); }
    else if (evolve_clock == 0xcd)    { region_census(); }
    else if (evolve_clock == 0xce)    { evolve_row = 0;
                                         evolve_region(0x14); }
    else if (evolve_clock == 0xcf)    { evolve_row = 0x14;
                                         evolve_region(0x14); }
    else if (evolve_clock == 0xd0)    { evolve_row = 0x28;
                                         evolve_region(0x14); }
    else if (evolve_clock == 0xd1)    { check_goods_in_region_warehouses(); }
    else if (evolve_clock == 0xd2)    { check_citizen_list();
                                         check_army_list(); }
    else if (evolve_clock == 0xd3)    { get_landfill(0);
                                         update_landfill = 1; }

    evolve_clock++;
    if (evolve_clock <= 0xd6) return;

    evolve_tick4++; if (evolve_tick4 >= 4) evolve_tick4 = 0;
    evolve_tick3++; if (evolve_tick3 >= 3) evolve_tick3 = 0;
    evolve_clock = 0;
    evolve_count++;
    update_time();
    update_map = 1;
    setup_map_screen_refresh();
}

// FUNCTION: C2 0x3FF68
// WIN: 0x00462296
// Lines 240–261
//
// Run every per-row pass once across the whole 80x80 map so the city's coverage flags reflect
// the current building layout (used after a load or a screen swap).  Restores `evolve_clock`
// to a sensible phase afterwards.
void evolve_to_current_fabric(void)
{
    int t = evolve_clock;
    evolve_row = 0;
    clear_all_cm(0xd);
    clear_all_cm(0xf);
    clear_all_cm(0xe);
    clear_all_cm(0xc);
    evolve_water_supply_baths_industry(0x50);
    evolve_security_cover(0x50);
    evolve_amenity_cover(0x50);
    evolve_water_table(0x50);
    evolve_land_value(0x50);
    cap_land_value(0x50);
    if (t <= 0x50) {
        evolve_clock = t;
    } else if (t >= 0x8e) {
        evolve_clock = t;
    } else {
        evolve_clock = 0x50;
    }
}

// FUNCTION: C2 0x3FFFF
// WIN: 0x00462355
// Lines 264–287
//
// Advance the in-game clock by one tick: bumps week/month/year counters, calls
// `monthly_update` / `yearly_update` / `act_do_year_end` at the appropriate boundaries.
void update_time(void)
{
    get_population_growth_factor();
    get_industry_growth_factor();
    get_insurrection_factor();
    week++;
    if (week < 1) return;
    week = 0;

    if (population < 500) arena_top_count = 0;
    else if (++arena_top_count > 12) arena_top_count = 0;
    if (population < 1000) {
        colosseum_top_count = 0;
    } else {
        colosseum_top_count++;
        if (colosseum_top_count > 18) colosseum_top_count = 0;
    }

    monthly_update();
    month++;
    if (month < 12) {
        check_game_over();
        return;
    }
    month = 0;
    year++;
    years_elapsed++;
    years_elapsed_in_region++;
    yearly_update();
    check_game_over();
    act_do_year_end();
}

// FUNCTION: C2 0x400D0
// WIN: 0x00462456
// Lines 289–313
//
// Once-per-month bookkeeping: random event, slave welfare/costs, salary, region/city trouble,
// auto-conquest, plus the emperor-reply and emperor-warning reminder messages.
void monthly_update(void)
{
    game_state = 0;
    check_for_promotion();
    random_event();
    slave_random = rand8;
    slave_welfare();
    slave_costs();
    adjust_slave_usage();
    train_soldiers();
    pay_salary();
    region_trouble();
    city_trouble();
    auto_conquer();
    if (warned_of_emperor_reply_month == month + 1) {
        warned_of_emperor_reply_month = 0;
        put_message((warned_of_emperor_reply_level) + 0x7d, 0, 0);
    }
    if (month == 6) {
        if (warned_of_emperor == 0) {
            warned_of_emperor = 1;
            put_message(0x78, 0, 0xa);
        }
    }
}

// FUNCTION: C2 0x4016E
// WIN: 0x0046250c
// Lines 315–334
//
// Once-per-year bookkeeping: end-of-year accounts, new tribute target, push the year's
// population/denarii/tax totals into the history graph and roll the "this year" snapshots.
void yearly_update(void)
{
    year_end_accounts();
    get_new_tribute();
    history_entry[0] = population;
    history_entry[1] = denarii;
    history_entry[2] = account_pop_tax;
    history_entry[3] = account_ind_tax;
    history_entry[4] = year;
    save_history();
    last_years_population = this_years_population;
    last_years_denarii = this_years_denarii;
    last_years_pop_tax = this_years_pop_tax;
    last_years_ind_tax = this_years_ind_tax;
    this_years_population = population;
    this_years_denarii = denarii;
    this_years_pop_tax = account_pop_tax;
    this_years_ind_tax = account_ind_tax;
}

// FUNCTION: C2 0x40200
// WIN: 0x004625a8
// Lines 338–366
//
// Per-row coverage pass for reservoirs (kind 0xbe), industries (0xfc..0xff) and businesses
// (0xfa): write the appropriate water-supply / industry / baths flag bits via `flag_range`.
void evolve_water_supply_baths_industry(int rows)
{
    int yi;
    int xi;
    unsigned char kind;
    unsigned char t;

    cm_sptr = evolve_row * 1600;
    for (yi = 0; yi < rows; yi++) {
        for (xi = 0; xi < 80; xi++, cm_sptr += 20) {
            kind = (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).base_kind;
            if (kind == 0xbe) {
                t = (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).range_flag & 3;
                if      (t == 3) flag_range(0, xi, evolve_row + yi, 6, 0x0d, 4);
                else if (t == 2) flag_range(0, xi, evolve_row + yi, 5, 0x0d, 4);
                else if (t == 1) flag_range(0, xi, evolve_row + yi, 4, 0x0d, 4);
            } else if (kind >= 0xfc && kind <= 0xff) {
                flag_range(0, xi, evolve_row + yi, 2, 0x0d, 0x40);
            } else if (kind == 0xfa) {
                flag_range(0, xi, evolve_row + yi, 4, 0x0e, 0x20);
                flag_range(0, xi, evolve_row + yi, 2, 0x0e, 0x10);
                flag_range(0, xi, evolve_row + yi, 1, 0x0d, 0x80);
            }
        }
    }
}

// FUNCTION: C2 0x40327
// WIN: 0x0046277b
// Lines 371–442
//
// Per-row water-table pass: stamp water-coverage flags around reservoirs / wells / fountains
// and tick the supply cooldown on baths/fountains, swapping their sprites between
// supplied and unsupplied variants as the trouble rate dictates.
void evolve_water_table(int rows)
{
    unsigned char supplied;
    int row;
    int col;
    unsigned char counter_sum;
    unsigned char variant;
    unsigned char activity;
    unsigned char sprite_count;
    int depth;
    unsigned char kind;

    cm_sptr = evolve_row * 1600;

    for (row = 0; row < rows; row++)
        for (col = 0; col < 80; col++, cm_sptr += 20)
        {
            kind = (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).base_kind;
            if ((kind >= 0x1e) && (kind <= 0x51))
            {
                flag_range(0, col, row + evolve_row, 3, 0xd, 2);
            }
            else if ((kind >= 0xd7) && (kind <= 0xda))
            {
                flag_range(0, col, row + evolve_row, 2, 0xd, 2);
            }
            else if (kind == 0xbe)
            {
                supplied = (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).range_flag & 3;
                if (supplied == 3) flag_range(0, col, row + evolve_row, 3, 0xd, 1);
                else if (supplied == 2) flag_range(0, col, row + evolve_row, 2, 0xd, 1);
                else if (supplied == 1) flag_range(0, col, row + evolve_row, 1, 0xd, 1);
            }
            else if ((kind >= 0xdb) && (kind <= 0xde))
            {
                supplied = (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).education & 4;

                if (water_trouble_rate == 0) supplied = 0;
                else if (water_trouble_rate < 0x10)
                {
                    counter_sum = (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).building + water_trouble_rate;
                    if (counter_sum < 0x10) supplied = 0; else counter_sum = counter_sum & 0xf;
                    (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).building = counter_sum;
                }

                if (supplied)
                {
                    flag_range(0, col, row + evolve_row, 6, 0xd, 1);
                    (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).extra_edge = house_gfxdat[kind + 0x2d] + 1;
                }
                else (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).extra_edge = house_gfxdat[kind + 0x2d];
                (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).edge_bits |= 1;
            }
            else if ((kind >= 0xdf) && (kind <= 0xe2))
            {
                activity = (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).activity_a & 0xf;
                if (activity != 0) continue;
                variant = kind - 0xdf;
                supplied = affected_by_cover1((*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).b, 2, 4);
                if (supplied)
                {
                    depth = kind - 0xda;
                    flag_range(1, col, row + evolve_row, depth, 0xd, 8);
                }

                if (water_trouble_rate == 0) supplied = 0;
                else if (water_trouble_rate < 0x10)
                {
                    counter_sum = (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).building + water_trouble_rate;
                    if (counter_sum < 0x10) supplied = 0; else counter_sum = counter_sum & 0xf;
                    (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).building = counter_sum;
                }

                sprite_count = (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).extra_edge;
                if (supplied && (sprite_count >= 0x63)) change_sized(kind, (variant * 4) + 0x20, 2, cm_sptr);
                if ((!supplied) && (sprite_count < 0x63)) change_sized(kind, (variant * 4) + 0x63, 2, cm_sptr);
            }
        }
}

// FUNCTION: C2 0x40617
// WIN: 0x00462bda
// Lines 446–472
//
// Per-row security-coverage pass: stamp prefecture / fort / wall / forum coverage flag bits
// around their source buildings via `flag_range`.
void evolve_security_cover(int rows)
{
    int row;
    int col;
    unsigned char kind;

    cm_sptr = evolve_row * 1600;

    for (row = 0; row < rows; row++) {
        for (col = 0; col < 80; col++, cm_sptr += 20) {
            kind = (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).base_kind;

            if (kind == 0xe4) {
                flag_range(0, col, evolve_row + row, 3, 0xe, 0x01);
                flag_range(0, col, evolve_row + row, 3, 0xa, 0x30);
            } else if (kind == 0xe3) {
                flag_range(0, col, evolve_row + row, 2, 0xe, 0x02);
                flag_range(0, col, evolve_row + row, 3, 0xa, 0x30);
            } else if (kind == 0xc0) {
                flag_range(0, col, evolve_row + row, 2, 0xe, 0x04);
            } else if (kind >= 0xbf && kind <= 0xca) {
                flag_range(0, col, evolve_row + row, 2, 0xe, 0x08);
            } else if (kind >= 0xae && kind <= 0xb1) {
                flag_range(0, col, evolve_row + row, 3, 0xa, 0x0c);
            } else if (kind >= 0xb2 && kind <= 0xb5) {
                flag_range(0, col, evolve_row + row, 4, 0xa, 0x0c);
            } else if (kind >= 0xb6 && kind <= 0xb9) {
                flag_range(0, col, evolve_row + row, 5, 0xa, 0x0c);
            } else if (kind >= 0xfc && kind <= 0xff) {
                flag_range(0, col, evolve_row + row, 3, 0xa, 0xc0);
            }

        }
    }
}

// FUNCTION: C2 0x4077B
// WIN: 0x00462e70
// Lines 475–525
//
// Per-row amenity-coverage pass: stamp temple / school / hospital / theatre / arena radius
// flags via `flag_range3` (the variant that also writes the per-tier rank bits).
void evolve_amenity_cover(int rows)
{
    int row;
    int col;
    unsigned char kind;
    unsigned char act;

    cm_sptr = evolve_row * 1600;

    for (row = 0; row < rows; row++) {
        for (col = 0; col < 80; col++, cm_sptr += 20) {
            kind = (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).base_kind;
            act = (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).activity_a & 0x0f;
            if (act != 0) continue;

            if (kind == 0xf3) {
                flag_range(1, col, evolve_row + row, 6, 0xd, 0x10);
            } else if (kind == 0xf4) {
                flag_range(2, col, evolve_row + row, 8, 0xd, 0x20);
            } else if (kind == 0xe5) {
                flag_range3(1, col, evolve_row + row, 9, 0xc, 1, 3, 0xfc);
                flag_range3(1, col, evolve_row + row, 7, 0xc, 2, 3, 0xfc);
                flag_range3(1, col, evolve_row + row, 5, 0xc, 3, 3, 0xfc);
            } else if (kind == 0xe6) {
                flag_range3(1, col, evolve_row + row, 11, 0xc, 1, 3, 0xfc);
                flag_range3(1, col, evolve_row + row,  9, 0xc, 2, 3, 0xfc);
                flag_range3(1, col, evolve_row + row,  7, 0xc, 3, 3, 0xfc);
            } else if (kind == 0xe7) {
                flag_range3(2, col, evolve_row + row, 9, 0xc, 4, 0xc, 0xf3);
                flag_range3(2, col, evolve_row + row, 7, 0xc, 8, 0xc, 0xf3);
                flag_range3(2, col, evolve_row + row, 5, 0xc, 0xc, 0xc, 0xf3);
            } else if (kind == 0xe8) {
                flag_range3(2, col, evolve_row + row, 11, 0xc, 4, 0xc, 0xf3);
                flag_range3(2, col, evolve_row + row,  9, 0xc, 8, 0xc, 0xf3);
                flag_range3(2, col, evolve_row + row,  7, 0xc, 0xc, 0xc, 0xf3);
            } else if (kind == 0xe9 || kind == 0xea || kind == 0xeb || kind == 0xec) {
                flag_range3(2, col, evolve_row + row, 10, 0xc, 0x10, 0x30, 0xcf);
                flag_range3(2, col, evolve_row + row,  8, 0xc, 0x20, 0x30, 0xcf);
                flag_range3(2, col, evolve_row + row,  6, 0xc, 0x30, 0x30, 0xcf);
            } else if (kind == 0xed || kind == 0xee || kind == 0xef || kind == 0xf0) {
                flag_range3(3, col, evolve_row + row, 12, 0xc, 0x10, 0x30, 0xcf);
                flag_range3(3, col, evolve_row + row, 10, 0xc, 0x20, 0x30, 0xcf);
                flag_range3(3, col, evolve_row + row,  8, 0xc, 0x30, 0x30, 0xcf);
            }
        }
    }
}

// FUNCTION: C2 0x40AC5
// WIN: 0x004632ce
// Lines 530–790
//
//
// Per-row land-value pass.  Walks each cell, looks up its base land-value delta + radius
// from `house_lv_effect` / `buildings_lv_effect` / `forum_lv_effect` / `temple_lv_effect`,
// stamps the contribution via `change_lv`, and remembers the city-wide top spot.
void evolve_land_value(int rows)
{
    int row;
    int col;
    unsigned char kind;
    unsigned char flags;
    unsigned char bkind;
    unsigned char idx;
    unsigned char cooldown;
    int radius;
    int delta;
    int growth;
    int size;
    signed char curr_lv;

    if (evolve_row == 0) top_lv = 0;
    cm_sptr = evolve_row * 1600;

    for (row = 0; row < rows; row++) {
        for (col = 0; col < 80; col++, cm_sptr += 20) {
            flags = ((unsigned char *)city_map)[cm_sptr + 1];
            kind  = ((unsigned char *)city_map)[cm_sptr];

            if ((flags & 0x20) != 0) {
                if ((flags & 0x04) != 0) {
                    change_lv(col, row + evolve_row, 1, 1, 2);
                } else if ((flags & 0x10) != 0) {
                    change_lv(col, row + evolve_row, 2, 1, 1);
                } else if (kind == 0x5c) {
                    change_lv(col, row + evolve_row, 1, 1, 2);
                } else if (kind >= 0x58 && kind <= 0x5b) {
                    change_lv(col, row + evolve_row, 1, 1, 1);
                }
            } else {
                if ((flags & 0x01) != 0) {
                bkind = (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).base_kind;
                cooldown = (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).activity_a & 0xf;
                if (cooldown != 0) continue;
                if (bkind >= 0x82 && bkind <= 0xa1) {
                        bkind -= 0x82;
                        radius = house_lv_effect[bkind].radius;
                        delta  = house_lv_effect[bkind].delta;
                        size   = house_gfxdat[bkind*4 + 1];
                        delta += pop_growth_factor;
                        if      (bkind < 0x1a) growth = 0;
                        else if (bkind < 0x1e) growth = pop_growth_factor * 2;
                        else                 growth = pop_growth_factor * 4;
                        if (growth < 0) growth = 0;
                        (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).land_value += growth;
                        change_lv(col, row + evolve_row, radius, size, delta);
                    } else if (bkind >= 0xdb && bkind <= 0xde) {
                        delta  = buildings_lv_effect[0];
                        radius = buildings_lv_effect[1];
                        if (((*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).education & 4) != 0)
                            change_lv(col, row + evolve_row, radius, 1, delta);
                    } else if (bkind == 0xe3) {
                        delta  = buildings_lv_effect[2];
                        radius = buildings_lv_effect[3];
                        change_lv(col, row + evolve_row, radius, 1, delta);
                    } else if (bkind == 0xe4) {
                        delta  = buildings_lv_effect[4];
                        radius = buildings_lv_effect[5];
                        change_lv(col, row + evolve_row, radius, 3, delta);
                    } else if (bkind >= 0xae && bkind <= 0xb9) {
                        bkind -= 0xae;
                        radius = forum_lv_effect[bkind].radius;
                        delta  = forum_lv_effect[bkind].delta;
                        size   = forum_gfxdat[bkind*4 + 1];
                        change_lv(col, row + evolve_row, radius, size, delta);
                    } else if (bkind == 0xe5) {
                        delta  = buildings_lv_effect[6];
                        radius = buildings_lv_effect[7];
                        change_lv(col, row + evolve_row, radius, 2, delta);
                    } else if (bkind == 0xe6) {
                        delta  = buildings_lv_effect[8];
                        radius = buildings_lv_effect[9];
                        change_lv(col, row + evolve_row, radius, 2, delta);
                    } else if (bkind == 0xe7) {
                        delta  = buildings_lv_effect[10];
                        radius = buildings_lv_effect[11];
                        change_lv(col, row + evolve_row, radius, 3, delta);
                    } else if (bkind == 0xe8) {
                        delta  = buildings_lv_effect[12];
                        radius = buildings_lv_effect[13];
                        change_lv(col, row + evolve_row, radius, 3, delta);
                    } else if (bkind >= 0xe9 && bkind <= 0xec) {
                        delta  = buildings_lv_effect[14];
                        radius = buildings_lv_effect[15];
                        change_lv(col, row + evolve_row, radius, 3, delta);
                    } else if (bkind >= 0xed && bkind <= 0xf0) {
                        delta  = buildings_lv_effect[16];
                        radius = buildings_lv_effect[17];
                        change_lv(col, row + evolve_row, radius, 4, delta);
                    } else if (bkind == 0xf3) {
                        delta  = buildings_lv_effect[18];
                        radius = buildings_lv_effect[19];
                        change_lv(col, row + evolve_row, radius, 2, delta);
                    } else if (bkind == 0xf4) {
                        delta  = buildings_lv_effect[20];
                        radius = buildings_lv_effect[21];
                        change_lv(col, row + evolve_row, radius, 3, delta);
                    } else if (bkind == 0xf5) {
                        delta  = buildings_lv_effect[22];
                        radius = buildings_lv_effect[23];
                        change_lv(col, row + evolve_row, radius, 3, delta);
                    } else if (bkind >= 0xa2 && bkind <= 0xad) {
                        bkind -= 0xa2;
                        radius = temple_lv_effect[bkind].radius;
                        delta  = temple_lv_effect[bkind].delta;
                        if      (bkind < 4) size = 1;
                        else if (bkind < 8) size = 2;
                        else              size = 3;
                        change_lv(col, row + evolve_row, radius, size, delta);
                    } else if (bkind == 0xfa) {
                        idx = (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).building & 0xf0;
                        idx >>= 4;
                        if (idx <= 4) {
                            delta  = buildings_lv_effect[24];
                            radius = buildings_lv_effect[25];
                        } else {
                            delta  = buildings_lv_effect[26];
                            radius = buildings_lv_effect[27];
                        }
                        change_lv(col, row + evolve_row, radius, 3, delta);
                    } else if (bkind == 0xfc) {
                        delta  = buildings_lv_effect[28];
                        radius = buildings_lv_effect[29];
                        change_lv(col, row + evolve_row, radius, 2, delta);
                    } else if (bkind == 0xfd) {
                        delta  = buildings_lv_effect[30];
                        radius = buildings_lv_effect[31];
                        change_lv(col, row + evolve_row, radius, 2, delta);
                    } else if (bkind == 0xfe) {
                        delta  = buildings_lv_effect[32];
                        radius = buildings_lv_effect[33];
                        change_lv(col, row + evolve_row, radius, 2, delta);
                    } else if (bkind == 0xff) {
                        delta  = buildings_lv_effect[34];
                        radius = buildings_lv_effect[35];
                        change_lv(col, row + evolve_row, radius, 2, delta);
                    } else if (bkind == 0xdf) {
                        if (((*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).education & 4) != 0) {
                            delta  = buildings_lv_effect[36];
                            radius = buildings_lv_effect[37];
                            change_lv(col, row + evolve_row, radius, 2, delta);
                        }
                    } else if (bkind == 0xe0) {
                        if (((*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).education & 4) != 0) {
                            delta  = buildings_lv_effect[38];
                            radius = buildings_lv_effect[39];
                            change_lv(col, row + evolve_row, radius, 2, delta);
                        }
                    } else if (bkind == 0xe1) {
                        if (((*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).education & 4) != 0) {
                            delta  = buildings_lv_effect[40];
                            radius = buildings_lv_effect[41];
                            change_lv(col, row + evolve_row, radius, 2, delta);
                        }
                    } else if (bkind == 0xe2) {
                        if (((*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).education & 4) != 0) {
                            delta  = buildings_lv_effect[42];
                            radius = buildings_lv_effect[43];
                            change_lv(col, row + evolve_row, radius, 2, delta);
                        }
                } else if (bkind == 0xfb) {
                    delta  = buildings_lv_effect[44];
                    radius = buildings_lv_effect[45];
                    change_lv(col, row + evolve_row, radius, 3, delta);
                }
                } else if ((flags & 0x18) != 0) {
                    (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).land_value = 0;
                }
            }

            if (kind >= 0 && kind < 8) {
                if ((((unsigned char *)city_map)[cm_sptr + 3] & 0x80) != 0) {
                    delta  = buildings_lv_effect[46];
                    radius = buildings_lv_effect[47];
                    change_lv(col, row + evolve_row, radius, 1, delta);
                } else {
                    delta  = buildings_lv_effect[48];
                    radius = buildings_lv_effect[49];
                    change_lv(col, row + evolve_row, radius, 1, delta);
                }
                delta  = buildings_lv_effect[50];
                radius = buildings_lv_effect[51];
                change_lv(col, row + evolve_row, radius, 1, delta);
            } else if (kind >= 0x7c && kind <= 0x7e) {
                delta  = buildings_lv_effect[52];
                radius = buildings_lv_effect[53];
                change_lv(col, row + evolve_row, radius, 1, delta);
            } else if (kind >= 0x78 && kind <= 0x7b) {
                delta  = buildings_lv_effect[54];
                radius = buildings_lv_effect[55];
                change_lv(col, row + evolve_row, radius, 1, delta);
            }

            curr_lv = (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).land_value;
            if (curr_lv > top_lv) {
                top_lv      = curr_lv;
                top_lv_spot = cm_sptr;
            }
        }
    }

    if (row + evolve_row >= 0x50) {
        top_lv_ptr = top_lv_spot / 20;
        top_lv_x   = top_lv_ptr  % 80;
        top_lv_y   = top_lv_ptr  / 80;
    }
}

// FUNCTION: C2 0x41138
// WIN: 0x00463f66
// Lines 793–969
//
// Per-row land-value cap: for every cell, derive an upper-bound rank `cl` from the surrounding
// amenity / water / security / hospital / library coverage and clamp the cell's `+0xf`
// land-value rank to it.
//
// Byte-exact (2026-07-11): PS L868 keeps `mov bh,al; inc bh; mov [slot],bh`.
// A plain conditional increment reaches the same pre-compression IL, but Watcom's
// final LdStCompress sees the move adjacent in chain order and folds it to `inc al`.
// The explicit in-place byte normalization below leaves another move on the far
// side of the increment in chain order (compress `prevkind=3`, `nextkind=3`, no
// fuse verdict), while layout keeps the three instructions byte-adjacent.  Packing
// the two source statements onto one line also matches PS's single L868 mark.
// `line-compare` has no direction divergence; its only RC-only mark is the unrelated
// outer-loop increment at +0x46a.
void cap_land_value(int rows)
{
    unsigned char hit;
    int col;
    signed char cl;
    int row;
    unsigned char kind;
    int a;
    unsigned char act;
    unsigned int size;
    unsigned char boosted;
    signed char security;
    char range3_top;
    char range3_shifted;
    unsigned char *p;
    int raw;
    char range3_tmp;
    unsigned char rank_sum;
    signed char rank;
    signed char b;

    cm_sptr = evolve_row * 1600;
    for (row = 0; row < rows; row++)
    {
        for (col = 0; col < 80; col++, cm_sptr += 20)
        {
            kind = ((unsigned char *)city_map)[cm_sptr];
            if (kind >= 0x82) size = reg_aquaduct_gfxdat[kind + 8];
            else size = 1;

            act = (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).activity_a & 0xf;

            p = (unsigned char *)city_map + cm_sptr;
            if (act) p = get_ptr_to_corner(p, size);

            if ((kind < 0x82) || (kind > 0xa1))
                goto non_housing;

            a = affected_by_cover1(p, size, 2);
            b = affected_by_cover1(p, size, 1);
            if (b == 0 && (char)a == 0) { cl = 0x02; goto emit; }

            hit = get_range1(p, size, 0x0c);
            if (hit == 0) { cl = 0x06; goto emit; }

            hit = affected_by_cover1(p, size, 0x80);
            if (hit != 0) { cl = 0x0a; goto emit; }

            hit = get_range1(p, size, 0xc0);
            if (hit == 0) { cl = 0x0c; goto emit; }

            if (b == 0) { cl = 0x0e; goto emit; }

            hit = affected_by_cover2(p, size, 0x10);
            if (hit != 0) { cl = 0x10; goto emit; }

            hit = affected_by_cover1(p, size, 0x08);
            if (hit == 0) { cl = 0x12; goto emit; }

            range3_tmp = get_range3(p, size, 0x03);
            raw = get_range3(p, size, 0x0c);
            range3_shifted = (raw & 0xff) >> 2;
            raw = get_range3(p, size, 0x30);
            range3_top = (raw & 0xff) >> 4;
            rank_sum = range3_tmp + range3_shifted + range3_top;
            if (rank_sum == 0) { cl = 0x14; goto emit; }

            hit = affected_by_cover2(p, size, 0x01);
            if (hit != 0) { cl = 0x18; goto emit; }

            security = ((unsigned char *)city_map)[cm_sptr + 0x11];
            hit = get_range1(p, size, 0x30);
            boosted = (security >= 0x10);

            if (hit) { boosted &= 0xff; boosted++; }
            if (boosted == 0) { cl = 0x18; goto emit; }

            hit = affected_by_cover2(p, size, 0x20);
            if (hit != 0) { cl = 0x1a; goto emit; }

            if (rank_sum <= 1) { cl = 0x1a; goto emit; }

            hit = affected_by_cover2(p, size, 0x08);
            if (hit != 0) { cl = 0x1a; goto emit; }

            if (rank_sum <= 2) { cl = 0x1c; goto emit; }

            hit = affected_by_cover2(p, size, 0x04);
            if (hit != 0) { cl = 0x1e; goto emit; }

            if (hospital_cover < 0x14) { cl = 0x1e; goto emit; }

            if (rank_sum <= 3) { cl = 0x20; goto emit; }

            hit = affected_by_cover1(p, size, 0x10);
            if (hit == 0) { cl = 0x22; goto emit; }

            hit = affected_by_cover2(p, size, 0x02);
            if (hit != 0) { cl = 0x22; goto emit; }

            if (hospital_cover < 0x28) { cl = 0x24; goto emit; }

            if (rank_sum <= 4) { cl = 0x26; goto emit; }

            hit = affected_by_cover1(p, size, 0x40);
            if (hit != 0) { cl = 0x28; goto emit; }

            if (boosted <= 1) { cl = 0x2a; goto emit; }

            if (hospital_cover < 0x3c) { cl = 0x2c; goto emit; }

            if (rank_sum <= 5) { cl = 0x2c; goto emit; }

            hit = affected_by_cover1(p, size, 0x20);
            if (hit == 0) { cl = 0x2e; goto emit; }

            if (library_cover < 0x14) { cl = 0x2e; goto emit; }

            if (rank_sum <= 6) { cl = 0x30; goto emit; }

            if (library_cover < 0x28) { cl = 0x32; goto emit; }

            if (hospital_cover < 0x50) { cl = 0x34; goto emit; }

            if (library_cover < 0x3c) { cl = 0x36; goto emit; }

            if (rank_sum <= 7) { cl = 0x38; goto emit; }

            if (hospital_cover < 0x64) { cl = 0x3a; goto emit; }

            if (library_cover < 0x50) { cl = 0x3a; goto emit; }

            if (rank_sum <= 8) { cl = 0x3c; goto emit; }

            if (library_cover < 0x64) { cl = 0x3e; goto emit; }

            cl = 0x40;
            goto emit;

        non_housing:
            hit = affected_by_cover1(p, size, 0x80);
            if (hit != 0) { cl = 0x0a; goto emit; }

            hit = affected_by_cover2(p, size, 0x10);
            if (hit != 0) { cl = 0x10; goto emit; }

            hit = affected_by_cover2(p, size, 0x01);
            if (hit != 0) { cl = 0x18; goto emit; }

            hit = affected_by_cover2(p, size, 0x20);
            if (hit != 0) { cl = 0x1a; goto emit; }

            hit = affected_by_cover2(p, size, 0x08);
            if (hit != 0) { cl = 0x1a; goto emit; }

            hit = affected_by_cover2(p, size, 0x04);
            if (hit != 0) { cl = 0x1e; goto emit; }

            hit = affected_by_cover2(p, size, 0x02);
            if (hit != 0) { cl = 0x22; goto emit; }

            hit = affected_by_cover1(p, size, 0x40);
            if (hit != 0) { cl = 0x28; goto emit; }

            cl = 0x40;
        emit:
            rank = ((signed char *)city_map)[cm_sptr + 0xf];
            if (cl < rank) ((unsigned char *)city_map)[cm_sptr + 0xf] = cl;
        }
    }
}

// FUNCTION: C2 0x415BB
// WIN: 0x004647a0
// Lines 974–1020
//
// Per-row pass for forum cells (0xae..0xb9): tick the shopper-spawn cooldown and emit
// citizens via `put_out_a` once the population allows it.
void evolve_forum_activity(int rows)
{
    unsigned char flags;
    int row;
    unsigned char kind;
    unsigned char occ;
    int col;
    unsigned char gfx_template;
    unsigned char cooldown;
    unsigned char shoppers;
    int result;

    cm_sptr = evolve_row * 1600;

    for (row = 0; row < rows; row++) {
        for (col = 0; col < 80; col++, cm_sptr += 20) {
            kind = ((unsigned char *)city_map)[cm_sptr];
            if (kind < 0xae) continue; if (kind > 0xb9) continue;

            gfx_template = forum_gfxdat[kind + 0x26];
            if (gfx_template == 0) continue;
            occ = ((unsigned char *)city_map)[cm_sptr + 5] & 0x0f;
            if (occ != 0) continue;

            cooldown = ((unsigned char *)city_map)[cm_sptr + 6] & 0x0f;
            flags = ((unsigned char *)city_map)[cm_sptr + 6] & 0x10;
            shoppers = (((unsigned char *)city_map)[cm_sptr + 5] & 0xf0) >> 4;

            if (cooldown == 0) {
                if (population < 2) continue;
                result = put_out_a(1, (unsigned char)col, (unsigned char)(evolve_row + row), flags,
                                   shoppers, gfx_template, 0x20);
                if (result != 0) {
                    shoppers = result & 0xff;
                    cooldown = 3;
                    if (gfx_template == 9) cooldown -= 1;
                    else if (gfx_template == 0x10) cooldown -= 2;
                    citizen_list[created_citizen_no].state_idx = 1; citizen_list[created_citizen_no].wait_count = 0x14;
                    citizen_list[created_citizen_no].saved_state_idx = 3;
                }
                if (shoppers >= gfx_template) shoppers = 0;
            } else {
                cooldown--;
            }

            ((unsigned char *)city_map)[cm_sptr + 6] &= 0xf0;
            ((unsigned char *)city_map)[cm_sptr + 6] |= cooldown;
            ((unsigned char *)city_map)[cm_sptr + 5] &= 0x0f;
            ((unsigned char *)city_map)[cm_sptr + 5] |= shoppers << 4;
        }
    }
}

// FUNCTION: C2 0x4176E
// WIN: 0x00464a1f
// Lines 1024–1063
//
// Per-row pass for fort cells (0xbf): tick the soldier-spawn cooldown, find a nearby enemy
// citizen and dispatch a soldier to engage it.
void evolve_fort_activity(int rows)
{
    int row;
    int col;
    unsigned char kind;
    unsigned char counter;
    short enemy_idx;
    int res;

    cm_sptr = evolve_row * 1600;

    for (row = 0; row < rows; row++) {
        for (col = 0; col < 80; col++, cm_sptr += 20) {
            kind = ((unsigned char *)city_map)[cm_sptr];
            if (kind == 0xbf) {
                counter = ((unsigned char *)city_map)[cm_sptr + 6] & 0x0f;
                if (counter == 0) {
                    if (population < 2) continue;
                    enemy_idx = find_enemy(col, evolve_row + row, 6);
                    if (enemy_idx == 0) continue;
                    counter = 3;
                    res = put_out_a(4, (unsigned char)col, (unsigned char)(evolve_row + row), 0, 0, 1, 0);
                    if (res != 0) {
                        citizen_a = enemy_idx;
                        citizen_list[created_citizen_no].target_kind = citizen_a;
                        citizen_list[created_citizen_no].target_marker = citizen_list[enemy_idx].evolve_timer;
                        citizen_list[created_citizen_no].dest_x = citizen_list[enemy_idx].x; citizen_list[created_citizen_no].dest_y = citizen_list[enemy_idx].y;
                        citizen_list[created_citizen_no].state_idx = 1;
                        citizen_list[created_citizen_no].saved_state_idx = 6;
                        citizen_list[created_citizen_no].wait_count = 0x14;
                    }
                } else {
                    counter--;
                }
                ((unsigned char *)city_map)[cm_sptr + 6] &= 0xf0;
                ((unsigned char *)city_map)[cm_sptr + 6] |= counter;
            }
        }
    }
}

// FUNCTION: C2 0x418D9
// WIN: 0x00464c75
// Lines 1068–1133
//
// Per-row pass for prefecture (0xe3) and watch-tower (0xe4) cells: tick the patrol cooldown
// and spawn the next patrol citizen via `put_out_a`.
void evolve_security_activity(int rows)
{
    int row;
    unsigned char occ;
    unsigned char kind;
    int col;
    unsigned char flags;
    unsigned char cooldown;
    unsigned char patrol_count;
    int result;

    cm_sptr = evolve_row * 1600;

    for (row = 0; row < rows; row++) {
        for (col = 0; col < 80; col++, cm_sptr += 20) {
            kind = (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).base_kind;
            if (kind == 0xe3) {
                occ = (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).activity_a & 0x0f;
                if (occ != 0) continue;
                cooldown     = (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).activity_b & 0x0f;
                flags        = (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).activity_b & 0x10;
                patrol_count = ((*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).activity_a & 0xf0) >> 4;
                if (cooldown == 0) {
                    if (population < 2) continue;
                    result = put_out_a(5, (unsigned char)col, (unsigned char)(evolve_row + row), flags,
                                       patrol_count, 1, 0x20);
                    if (result != 0) {
                        patrol_count = (unsigned char)result;
                        cooldown = 3;
                        citizen_list[created_citizen_no].state_idx = 1; citizen_list[created_citizen_no].wait_count = 0x14;
                        citizen_list[created_citizen_no].saved_state_idx = 8;
                    }
                    patrol_count++; if (patrol_count >= 4) patrol_count = 0;
                } else {
                    cooldown--;
                }
                (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).activity_b &= 0xf0;
                (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).activity_b |= cooldown;
                (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).activity_a &= 0x0f;
                (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).activity_a |= patrol_count << 4;
            } else if (kind == 0xe4) {
                occ = (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).activity_a & 0x0f;
                if (occ != 0) continue;
                cooldown     = (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).activity_b & 0x0f;
                flags        = (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).activity_b & 0x10;
                patrol_count = ((*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).activity_a & 0xf0) >> 4;
                if (cooldown == 0) {
                    if (population < 2) continue;
                    result = put_out_a(4, (unsigned char)col, (unsigned char)(evolve_row + row), flags,
                                       patrol_count, 9, 0x20);
                    if (result != 0) {
                        patrol_count = (unsigned char)result;
                        cooldown = 3;
                        citizen_list[created_citizen_no].state_idx = 1; citizen_list[created_citizen_no].wait_count = 0x14;
                        citizen_list[created_citizen_no].saved_state_idx = 7;
                    }
                    patrol_count++; if (patrol_count >= 9) patrol_count = 0;
                } else {
                    cooldown--;
                }
                (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).activity_b &= 0xf0;
                (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).activity_b |= cooldown;
                (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).activity_a &= 0x0f;
                (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).activity_a |= patrol_count << 4;
            }
        }
    }
}


// FUNCTION: C2 0x41B49
// WIN: 0x0046503e
// Lines 1137–1215
//
// Per-row pass for markets (0xfc..0xff) and businesses (0xfa): refresh the market sprite via
// `market_image`, recompute business supply via `business_output`, then spawn the next
// shopper / trader citizen and record its envoy slot in the cell.
//
// EXACT (2026-07-11): Rule 121 duplicated-tail rover advance.  The old recovery routed
// both activity arms through an invented `writeback` label and used inverted `occ` guards;
// WIN /Od showed one loop-increment funnel, nested `occ == 0` arms, and four source-level
// writeback statements duplicated in each arm.  Restoring that shape lets Watcom ComTail
// merge the identical suffixes back to the SAME emitted CFG, but their pre-merge block
// births move the first market cooldown spill-reload from RC AL to PS CL.  That one scratch
// pick self-heals the full 11-byte byte-register cascade: 192/192 register-blind -> exact.
// `line-compare` has no direction divergence (two harmless RC-only marks at +0x16a/+0x2dd);
// WIN struct-diff also drops 44 -> 21.
void evolve_industrial_activity(int rows)
{
    unsigned char kind;
    int row;
    unsigned char occ;
    unsigned char flags;
    unsigned char patrons;
    unsigned char cooldown;
    int col;
    int result;

    cm_sptr = evolve_row * 1600;

    for (row = 0; rows > row; row++) {
        for (col = 0; col < 80; col++, cm_sptr += 20) {
            kind = ((unsigned char *)city_map)[cm_sptr];
            if (kind >= 0xfc && kind <= 0xff) {
                occ = ((unsigned char *)city_map)[cm_sptr + 5] & 0xf;
                if (occ == 0) {
                    market_image();

                    cooldown = ((unsigned char *)city_map)[cm_sptr + 6] & 0xf;
                    flags = ((unsigned char *)city_map)[cm_sptr + 6] & 0x10;
                    patrons  = (((unsigned char *)city_map)[cm_sptr + 5] & 0xf0) >> 4;
                    if (cooldown == 0) {
                        if (population < 2) goto next;
                        result = put_out_a(2, (char)col, (char)(evolve_row + row), flags,
                                           (char)patrons, 4, 0x20);
                        if (result != 0) {
                            patrons = (unsigned char)result;
                            cooldown = 3;
                            citizen_list[created_citizen_no].state_idx = 1; citizen_list[created_citizen_no].wait_count = 0x14;
                            citizen_list[created_citizen_no].saved_state_idx = 4;
                            citizen_list[created_citizen_no].target_ref = cm_sptr;
                            remove_envoy();
                            ((unsigned char *)city_map)[cm_sptr + 0x12] = (unsigned char)created_citizen_no;
                        }
                        patrons++; if (patrons >= 4) patrons = 0;
                    } else {
                        cooldown--;
                    }
                    ((unsigned char *)city_map)[cm_sptr + 6] &= 0xf0;
                    ((unsigned char *)city_map)[cm_sptr + 6] |= cooldown;
                    ((unsigned char *)city_map)[cm_sptr + 5] &= 0x0f;
                    ((unsigned char *)city_map)[cm_sptr + 5] |= patrons << 4;
                }
            } else if (kind == 0xfa) {
                occ = ((unsigned char *)city_map)[cm_sptr + 5] & 0xf;
                ((unsigned char *)city_map)[cm_sptr + 3] |= 1;
                if (occ == 0) {
                    business_output(col, evolve_row + row);

                    cooldown = ((unsigned char *)city_map)[cm_sptr + 6] & 0xf;
                    flags = ((unsigned char *)city_map)[cm_sptr + 6] & 0x10;
                    patrons  = (((unsigned char *)city_map)[cm_sptr + 5] & 0xf0) >> 4;
                    if (cooldown == 0) {
                        if (population < 2) goto next;
                        result = put_out_a(6, (char)col, (char)(evolve_row + row), flags,
                                           (char)patrons, 9, 0x20);
                        if (result != 0) {
                            patrons = (unsigned char)result;
                            cooldown = 3;
                            citizen_list[created_citizen_no].state_idx = 1; citizen_list[created_citizen_no].wait_count = 0x14;
                            citizen_list[created_citizen_no].saved_state_idx = 0xa;
                            citizen_list[created_citizen_no].target_ref = cm_sptr;
                            remove_envoy();
                            ((unsigned char *)city_map)[cm_sptr + 0x12] = (unsigned char)created_citizen_no;
                        }
                        patrons++; if (patrons >= 9) patrons = 0;
                    } else {
                        cooldown--;
                    }
                    ((unsigned char *)city_map)[cm_sptr + 6] &= 0xf0;
                    ((unsigned char *)city_map)[cm_sptr + 6] |= cooldown;
                    ((unsigned char *)city_map)[cm_sptr + 5] &= 0x0f;
                    ((unsigned char *)city_map)[cm_sptr + 5] |= patrons << 4;
                }
            }
        next:
            ;
        }
    }
}

// FUNCTION: C2 0x41E3A
// WIN: 0x004654b5
// Lines 1217–1223
//
// Detach the previous envoy citizen from the cell at `cm_sptr` so a new one can take its
// slot: drives the old envoy's state to 2 (go-home) if it is still pointing back here.
void remove_envoy(void)
{
    citizen_a = (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).industrial;
    if (citizen_list[(*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).industrial].exists) {
        if (citizen_list[citizen_a].target_ref == cm_sptr)
            citizen_list[citizen_a].state_idx = 2;
    }
}

// FUNCTION: C2 0x41E7E
// WIN: 0x0046553b
// Lines 1225–1257
//
// Pick the market-tier sprite for the cell at `cm_sptr` based on its current shopper-count
// state, and slowly drain the two state nibbles toward 0 on every second tick.
void market_image(void)
{
    unsigned char shape = (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).base_kind;
    unsigned char state = (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).building;
    unsigned char halfA = state & 0x03;
    unsigned char halfB = state & 0x0c;
    unsigned char target = halfA;
    if (halfB == 0) target = 1;

    if (shape != 0xfc + target) {
        change_sized(target + 0xfc, target * 4 + 0x30, 2, cm_sptr);
    }

    if (halfA != 0 && (evolve_tick4 & 1)) {
        (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).building &= 0xfc;
        if (halfA == 2) {
            (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).building |= 1;
        } else if (halfA == 3) {
            (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).building |= 2;
        }
    }

    if (halfB != 0 && (evolve_tick4 & 1)) {
        (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).building &= 0xf3;
        if (halfB == 8) {
            (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).building |= 4;
        } else if (halfB == 0xc) {
            (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).building |= 8;
        }
    }
}

// FUNCTION: C2 0x41F63
// WIN: 0x004656e6
// Lines 1259–1336
//
// Recompute a business cell's production tier for the current month from the surrounding
// population, supply pipeline, empire connections and city stockpile.  Writes the new tier
// back into the cell's `building` byte.
void business_output(int col, int y)
{
  unsigned char flags9 = (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).building;
  unsigned char good = (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).business & 0xf;
  unsigned char level = flags9 & 3;
  unsigned char staged = flags9 & 0xc;
  int city_sup = industry[good].city_supply;
  int pipeline = industry[good].supply_pipeline[0];
  int growth = ind_growth_factor;
  int pop = test_area_for_population(2, col, y, 2);
  int supply;
  if (pop > 0x82)
    level += 4;
  else if (pop > 0x5a)
    level += 3;
  else if (pop > 0x32)
    level += 2;
  else if (pop > 10)
    level += 1;
  if (level <= 0)
    supply = 0;
  else
    if (level <= 1)
    supply = 3;
  else
    if (level <= 2)
    supply = 5;
  else
    if (level <= 3)
    supply = 7;
  else
    supply = 7;
  if (staged == 0)
  {
    growth -= 2;
    if (supply > 4)
      supply = 4;
  }
  if (pipeline <= 0)
    supply = 0;
  else
    if (pipeline <= 0x32)
  {
    growth -= 3;
    if (supply > 1)
      supply = 1;
  }
  else
    if (pipeline <= 0xc8)
  {
    growth -= 2;
    if (supply > 3)
      supply = 3;
  }
  else
    if (pipeline <= 0x190)
  {
    growth -= 1;
    if (supply > 5)
      supply = 5;
  }
  else
    if (pipeline > 600)
  {
    if (pipeline <= 0x320)
      growth += 1;
    else
      if (pipeline <= 0x3e8)
      growth += 2;
    else
      if (pipeline > 1000)
      growth += 3;
  }
  if (no_of_empire_connections <= 0)
  {
    if (supply > 4)
      supply = 4;
  }
  else
    if (no_of_empire_connections <= 1)
    growth += 1;
  else
    if (no_of_empire_connections > 1)
    growth += 2;
  if (city_sup <= 0)
    supply = 0;
  else
    if (city_sup <= 0x14)
  {
    if (supply > 1)
      supply = 1;
  }
  else
    if (city_sup <= 0x22)
  {
    if (supply > 2)
      supply = 2;
  }
  else
    if (city_sup <= 0x32)
  {
    if (supply > 3)
      supply = 3;
  }
  else
    if (city_sup <= 0x43)
  {
    if (supply > 4)
      supply = 4;
  }
  else
    if (city_sup <= 0x4b)
  {
    if (supply > 5)
      supply = 5;
  }
  else
    if ((city_sup <= 99) && (supply > 6))
    supply = 6;
  if (supply < growth)
    growth = supply;
  if (growth < 0)
    growth = 0;
  if (growth > 7)
    growth = 7;
  (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).building &= 0xf;
  growth <<= 4;
  (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).building |= growth;
  if (level != 0)
  {
    (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).building &= 0xfc;
    if (level == 2)
      (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).building |= 1;
    else
      if (level == 3)
      (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).building |= 2;
  }
  if (staged != 0)
  {
    (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).building &= 0xf3;
    if (staged == 8)
      (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).building |= 4;
    else
      if (staged == 0xc)
      (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).building |= 8;
  }
}

// FUNCTION: C2 0x42204
// WIN: 0x00465bbb
// Lines 1340–1446
//
// Per-row pass that ticks down fire / plague timers, spreads them to a neighbour in the
// rolling random direction, and re-evaluates unrest on housing cells (spawning a riot
// citizen and destroying the house once unrest tips over 0xf).
void spread_fire_and_plague_and_unrest(int rows)
{
    int row;
    int col;
    unsigned char kind;
    unsigned char n;
    signed char unrest;
    unsigned char rf;
    unsigned char hb;
    unsigned char r;

    cm_sptr = evolve_row * 1600;

    if (evolve_row == 0) {
        if (rand8 > 4) {
            stone_random_count++;
            if (stone_random_count >= 0x40) stone_random_count = 0;
            fire_spread_direction =
                stone_random_data[stone_random_count] & 6;
        }
        stone_random_count++;
        if (stone_random_count >= 0x40) stone_random_count = 0;
        plague_spread_direction =
            stone_random_data[stone_random_count] & 6;
        fire_spread_count    = 0;
        fire_spread_target   = rand8 & 1;
        plague_spread_count  = 0;
        plague_spread_target = rand8 & 1;
        unrest_random_count += rand8;
        if (unrest_random_count >= 0x40) unrest_random_count -= 0x40;
    }

    for (row = 0; row < rows; row++) {
        for (col = 0; col < 80; col++, cm_sptr += 20) {

            if ((*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).edge_bits & 0x80) {
                kind = (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).base_kind;
                if (kind < 8) {
                    n = (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).fire - 1;
                    (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).fire = n;
                    if (n == 0) {
                        (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).edge_bits &= 0x7f;
                    } else {
                        if (fire_spread_count++ < fire_spread_target) goto next;
                        fire_spread_target += 2;
                        if (fire_spread_direction == 0 && row + evolve_row <= 0)
                            goto next;
                        if (fire_spread_direction == 4 && row + evolve_row >= 0x4f)
                            goto next;
                        if (fire_spread_direction == 6 && col <= 0)
                            goto next;
                        if (fire_spread_direction == 2 && col >= 0x4f)
                            goto next;
                        spread_fire_atom(cm_sptr, fire_spread_direction);
                    }
                } else if (kind >= 0x82 && kind <= 0xa1) {
                    (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).fpu_flag &= 0xcf;
                    n = (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).fire;
                    n--; (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).fire = n;
                    if (n == 0) {
                        destroy_an_atom(cm_sptr, 0);
                    } else {
                        if (plague_spread_count++ < plague_spread_target) goto next;
                        plague_spread_target++;
                        if (plague_spread_direction == 0 && row + evolve_row <= 0)
                            goto next;
                        if (plague_spread_direction == 4 && row + evolve_row >= 0x4f)
                            goto next;
                        if (plague_spread_direction == 6 && col <= 0)
                            goto next;
                        if (plague_spread_direction == 2 && col >= 0x4f)
                            goto next;
                        if (n == 9)
                            goto next;
                        spread_plague_atom(cm_sptr, plague_spread_direction);
                    }
                }
            } else {
                kind = (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).base_kind;
                if (kind < 0x82 || kind > 0x9b) goto next;
                unrest = (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).activity_a & 0xf;
                if (unrest != 0) goto next;

                unrest = (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).fpu_flag & 0xf;
                rf = (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).range_flag;
                hb = (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).health;
                if ((rf & 0x0c) == 0) unrest--;
                if ((rf & 0x30) != 0) unrest--;
                if ((hb & 0x03) != 0) unrest--;
                unrest += insurrection_factor;

                unrest_random_count++;
                if (unrest_random_count >= 0x40) unrest_random_count = 0;
                r = unrest_random_data[unrest_random_count];
                if (r == 9)
                    unrest += house_type_to_unrest[kind - 0x82].unrest_delta;
                else
                    unrest += r;
                if (unrest < 0) unrest = 0;
                else if (unrest > 0xf) {
                    if (insurrection_factor > 6)
                        insurrection_factor = 6;
                    else if (insurrection_factor > 2)
                        insurrection_factor = 2;
                    destroy_an_atom(cm_sptr, 0);
                    if (put_out_a(7, (unsigned char)col, (unsigned char)(evolve_row + row), 0, 0, 0, 0) != 0) {
                        citizen_list[created_citizen_no].speed_phase = 0;
                        citizen_list[created_citizen_no].speed_count = 0;
                        citizen_list[created_citizen_no].state_idx = 1;
                        citizen_list[created_citizen_no].wait_count = 0x14;
                        citizen_list[created_citizen_no].saved_state_idx = 0xb;
                        if (put_a_message == 0)
                            put_message(0x57, cm_sptr, 0x15);
                    }
                    goto next;
                }
                (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).fpu_flag &= 0xf0;
                (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).fpu_flag |= unrest;
            }
next:
            ;
        }
    }
}

// FUNCTION: C2 0x42666
// WIN: 0x00466232
// Lines 1465–1491
//
// Helper used by every "spawn a citizen" call site: pick a starting offset from one of the
// `putoutsN[]` slot tables, find the first free direction that succeeds, and create the
// citizen there.  Returns the next-free slot index (so the caller can resume next tick)
// or 0 if no slot is available.
int put_out_a(char type, char x, char y, int unused, char start_idx,
              char mask, char is_barb)
{
  int counter;
  int count;
  int idx;
  int offx;
  int offy;
  (void) unused;
  idx = start_idx;
  if (mask == 1)
    count = 4;
  else
    if (mask == 4)
    count = 8;
  else
    if (mask == 9)
    count = 12;
  else
    if (mask == 0x10)
    count = 0x10;
  else
  {
    if (create_citizen(type, x, y, 0) == 0)
      return 0;
    return 1;
  }
  for (counter = 0; counter < count; counter++)
  {
    if (count <= idx)
      idx = 0;
    if (mask == 1)
    {
      offx = putouts1[idx].dx;
      offy = putouts1[idx].dy;
    }
    else
      if (mask == 4)
    {
      offx = putouts2[idx].dx;
      offy = putouts2[idx].dy;
    }
    else
      if (mask == 9)
    {
      offx = putouts3[idx].dx;
      offy = putouts3[idx].dy;
    }
    else
      if (mask == 0x10)
    {
      offx = putouts4[idx].dx;
      offy = putouts4[idx].dy;
    }
    if (create_citizen(type, x + offx, y + offy, is_barb) != 0)
      return idx + 1;
    idx++;
  }

  return 0;
}

// FUNCTION: C2 0x42790
// WIN: 0x0046640d
// Lines 1495–1662
//
// Once-per-row pass driven by `evolve_clock`: ticks down the amenity-decay nibbles, computes
// the per-house water-supply / hospital tier, accumulates fire-zone heat, and — when the
// cell's evolve cooldown is 0 — dispatches to the per-kind evolve/devolve helpers (house,
// well, fountain, baths, forum, temple, plaza).
//
// BYTE-EXACT 2026-07-10 (was ir 1/116 "ComTail residue", 1150bd).  The fix was the
// win-oracle shape (Hard Rule #7), NOT the t1/t2 ternary the 2026-07-07/09 sessions
// probed: CAESAR2.EXE shows compound `water_ok -= 1/-= 2` arms with a nested
// if/else in the >= 0x4b arm and NO t1/t2 temps -- the "speculative pre-compute"
// (`mov dl,al; sub dl,2` before `cmp 0x64`) is Watcom's OWN cross-arm CSE hoist of
// the compound forms, not evidence of source temps.  Also win-witnessed: the `b`
// temp for city_qptr[0xb], `e2 = extra & 2` (not `extra &= 2`), and a chained
// `odd = tick3 = tick4 = rand_ok = 0;` init with a dead `odd` flag from
// `evolve_tick4 & 1` (Watcom eliminates it; byte-neutral but win-faithful).
// All decls are C89 top-of-function; the decl ORDER is load-bearing (Rule 107/115:
// m0c/b_state placement decides the m0c-vs-amenity_c0 spill pick and the
// tick4/rand_ok slot order) -- found by `c2 sweep` composed decl perms.
void evolve_a_cm_row(void)
{
    unsigned char fire_row_off;
    signed char idx;
    int odd;
    signed char rank;
    int tick4;
    unsigned char m0c;
    unsigned char b_state;
    unsigned char amenity_c0;
    int rand_ok;
    int tick3;
    unsigned char amenity;
    unsigned char m30;
    unsigned char kind;
    signed char water_ok;
    unsigned char extra;
    unsigned char b;
    unsigned char e8;
    unsigned char e1;
    unsigned char e2;
    unsigned char colq;

    odd = tick3 = tick4 = rand_ok = 0;
    if (evolve_tick4 & 1) odd = 1;
    if (evolve_tick3 == 0) tick3 = 1;
    if (evolve_tick4 == 0) tick4 = 1;
    if (rand8 >= 6) rand_ok = 1;
    fire_row_off = evolve_row / 8;

    city_qptr = (unsigned char *)city_map;
    city_qptr += evolve_row * 1600;
    city_ptr  = evolve_row * 1600;

    for (evolve_col = 0; evolve_col < 80; evolve_col++, city_qptr += 20) {
        b_state = city_qptr[5] & 0xf;
        kind = city_qptr[0];
        rank = city_qptr[0xf];

        if (tick3) {
            amenity = city_qptr[0xa];
            m0c = amenity & 0xc;
            m30 = amenity & 0x30;
            amenity_c0 = amenity & 0xc0;
            if (m30) {
                city_qptr[0xa] &= 0xcf;
                if (m30 == 0x30) city_qptr[0xa] |= 0x20;
                else if (m30 == 0x20) city_qptr[0xa] |= 0x10;
            }
            if (amenity_c0) {
                city_qptr[0xa] &= 0x3f;
                if (amenity_c0 == 0xc0) city_qptr[0xa] |= 0x80;
                else if (amenity_c0 == 0x80) city_qptr[0xa] |= 0x40;
            }
            if (m0c) {
                city_qptr[0xa] &= 0xf3;
                if (m0c == 0xc) city_qptr[0xa] |= 8;
                else if (m0c == 8) city_qptr[0xa] |= 4;
            }
        }

        if (tick4) {
            if (kind >= 0x82 && kind <= 0xa1) {
                extra  = city_qptr[0xd];
                b = city_qptr[0xb];
                water_ok = b & 0x30;
                water_ok >>= 4;
                e8 = extra & 8;
                e1 = extra & 1;
                e2 = extra & 2;
                water_ok += rand_ok;
                if (e8 && e1) water_ok -= 3;
                else if (e8 && e2) water_ok -= 2;
                else if (e1 || e8) water_ok -= 1;
                else if (!e2) water_ok += 1;
                if (hospital_cover <= 0) water_ok += 1;
                else if (hospital_cover >= 0x64) water_ok -= 2;
                else if (hospital_cover >= 0x4b) { if (evolve_count & 1) water_ok -= 2; else water_ok -= 1; }
                else if (hospital_cover >= 0x32) water_ok -= 1;
                else if (hospital_cover >= 0x19 && (evolve_count & 1)) water_ok -= 1;
                if (water_ok <= 0) water_ok = 0;
                else if (water_ok == 1) water_ok = 0x10;
                else if (water_ok == 2) water_ok = 0x20;
                else water_ok = 0x30;
                city_qptr[0xb] &= 0xcf;
                city_qptr[0xb] |= water_ok;
            }
        }

        if (kind < 8) {
            if (city_qptr[3] & 0x80) {
                colq = evolve_col / 8;
                fire_zones[fire_row_off * 10 + colq] += 2;
            }
        }

        if (b_state == 0) {
            if (kind >= 0x82 && kind <= 0xa1) {
                idx  = kind - 0x82;
                if (idx >= 0x1e) rank = get_best_lv(city_qptr, 3);
                else if (idx >= 0x1a) rank = get_best_lv(city_qptr, 2);
                if      (rank <  house_evolution[idx].devolve_below) devolve_a_house(idx);
                else if (rank >  house_evolution[idx].evolve_above)  evolve_a_house(idx);
            } else if (kind >= 0xd7 && kind <= 0xda) {
                idx  = kind - 0xd7;
                if      (rank <  well_evolution[idx].devolve_below) devolve_a_building(idx, 1, 0xd7, 0x10, 1);
                else if (rank >  well_evolution[idx].evolve_above)  evolve_a_building(idx, 1, 0xd7, 0x10, 1);
            } else if (kind >= 0xdb && kind <= 0xde) {
                idx  = kind - 0xdb;
                if      (rank <  fountain_evolution[idx].devolve_below) devolve_a_building(idx, 1, 0xdb, 0, 0);
                else if (rank >  fountain_evolution[idx].evolve_above)  evolve_a_building(idx, 1, 0xdb, 0, 0);
            } else if (kind >= 0xdf && kind <= 0xe2) {
                idx  = kind - 0xdf;
                rank = get_best_lv(city_qptr, 2);
                if      (rank <  baths_evolution[idx].devolve_below) devolve_a_building(idx, 2, 0xdf, 0, 0);
                else if (rank >  baths_evolution[idx].evolve_above)  evolve_a_building(idx, 2, 0xdf, 0, 0);
            } else if (kind >= 0xae && kind <= 0xb1) {
                idx  = kind - 0xae;
                rank = get_best_lv(city_qptr, 2);
                if      (rank <  forum_evolution[idx].devolve_below) devolve_a_building(idx, 2, 0xae, forum_gfxdat[0], 4);
                else if (rank >  forum_evolution[idx].evolve_above)  evolve_a_building(idx, 2, 0xae, forum_gfxdat[0], 4);
            } else if (kind >= 0xb2 && kind <= 0xb5) {
                idx  = kind - 0xb2;
                rank = get_best_lv(city_qptr, 3);
                if      (rank <  forum_evolution[idx].devolve_below) devolve_a_building(idx, 3, 0xb2, forum_gfxdat[0x10], 9);
                else if (rank >  forum_evolution[idx].evolve_above)  evolve_a_building(idx, 3, 0xb2, forum_gfxdat[0x10], 9);
            } else if (kind >= 0xb6 && kind <= 0xb9) {
                idx  = kind - 0xb6;
                rank = get_best_lv(city_qptr, 4);
                if      (rank <  forum_evolution[idx].devolve_below) devolve_a_building(idx, 4, 0xb6, forum_gfxdat[0x20], 0x10);
                else if (rank >  forum_evolution[idx].evolve_above)  evolve_a_building(idx, 4, 0xb6, forum_gfxdat[0x20], 0x10);
            } else if (kind >= 0xa2 && kind <= 0xa5) {
                idx  = kind - 0xa2;
                if (rank <  temple_evolution[idx].devolve_below ||
                    population <  temple_populations1[idx].devolve_below) {
                    devolve_a_building(idx, 1, 0xa2, 0x3c, 1);
                } else if (rank >  temple_evolution[idx].evolve_above &&
                           population > temple_populations1[idx].evolve_above) {
                    evolve_a_building(idx, 1, 0xa2, 0x3c, 1);
                }
            } else if (kind >= 0xa6 && kind <= 0xa9) {
                idx  = kind - 0xa6;
                rank = get_best_lv(city_qptr, 2);
                if (rank <  temple_evolution[idx].devolve_below ||
                    population <  temple_populations2[idx].devolve_below) {
                    devolve_a_building(idx, 2, 0xa6, 0x40, 4);
                } else if (rank >  temple_evolution[idx].evolve_above &&
                           population > temple_populations2[idx].evolve_above) {
                    evolve_a_building(idx, 2, 0xa6, 0x40, 4);
                }
            } else if (kind >= 0xaa && kind <= 0xad) {
                idx  = kind - 0xaa;
                rank = get_best_lv(city_qptr, 3);
                if ((temple_evolution[idx].devolve_below) > (rank) ||
                    population <  temple_populations3[idx].devolve_below) {
                    devolve_a_building(idx, 3, 0xaa, 0, 9);
                } else if ((temple_evolution[idx].evolve_above) < (rank) &&
                           population > temple_populations3[idx].evolve_above) {
                    evolve_a_building(idx, 3, 0xaa, 0, 9);
                }
            } else if (kind >= 0x7c && kind <= 0x7e) evolve_a_plaza(rank, kind, evolve_col);
        }

    }
}

// FUNCTION: C2 0x42EAC
// WIN: 0x0046707d
// Lines 1667–1688
//
// Step a multi-tier building (well / fountain / baths / forum / temple) down one tier and
// re-stamp its sprite via `change_sized`.
void devolve_a_building(
    int count, int size, unsigned char kind, unsigned char color_base,
    unsigned char color_step)
{
    unsigned char offs;
    unsigned char fflag;

    if (count <= 0)
        return;
    --count;
    if (kind == 0xDB) {
        fflag = city_qptr[0xD] & 4;
        offs = fountain_gfxdat[count];
        if (fflag) ++offs;
    } else if (kind == 0xDF) {
        fflag = city_qptr[0xD] & 4;
        if (fflag) offs = count * 4 + 0x20;
        else offs = count * 4 + 0x63;
    } else {
        offs = color_base + count * color_step;
    }
    change_sized(kind + count, offs, size,
                 city_ptr + evolve_col * 20);
}

// FUNCTION: C2 0x42F46
// WIN: 0x0046716d
// Lines 1693–1703
//
// Step a multi-tier building (well / fountain / baths / forum / temple) up one tier and
// re-stamp its sprite via `change_sized`.
void evolve_a_building(
    int count, int size, unsigned char kind, unsigned char color_base,
    unsigned char color_step)
{
    unsigned char offs;
    unsigned char fflag;

    if (count >= 3)
        return;
    ++count;
    if (kind == 0xDB) {
        fflag = city_qptr[0xD] & 4;
        offs = fountain_gfxdat[count];
        if (fflag)
            ++offs;
    } else if (kind == 0xDF) {
        fflag = city_qptr[0xD] & 4;
        if (fflag)
            offs = count * 4 + 0x20;
        else
            offs = count * 4 + 0x63;
    } else {
        offs = color_base + count * color_step;
    }
    change_sized(kind + count, offs, size,
                 city_ptr + evolve_col * 20);
    return;
}

// FUNCTION: C2 0x42F5D
// WIN: 0x0046725d
// Lines 1725–1736
//
// Drop a house from tier `n` to tier `n-1`, pulling the size down to the previous tier's
// footprint (and padding the freed cells with domus stubs) or removing the house entirely
// at tier 0.
int devolve_a_house(int n)
{
    unsigned int curr;
    unsigned int prev;

    curr = house_gfxdat[n*4 + 1];
    --n;
    if (n < 0) {
        remove_house();
        return 0;
    }
    prev = house_gfxdat[n*4 + 1] & 0xff;
    change_house(n, prev, 0);
    if (curr != prev) {
        pad_house_with_domus(prev);
    }
    return 1;
}

// FUNCTION: C2 0x42FA5
// WIN: 0x004672d2
// Lines 1738–1754
//
// Promote a house from tier `n` to tier `n+1`.  If the next tier is larger, first checks
// `stretch_house` can grow into the neighbouring cells; bails out otherwise.
int evolve_a_house(int n)
{
    unsigned int curr;
    unsigned int next;
    int delta;

    curr = house_gfxdat[n*4 + 1];
    ++n;
    if (n >= 0x20) return 0;
    next = house_gfxdat[n*4 + 1];
    delta = 0;
    if (curr != next) {
        delta = stretch_house(n, next);
        if (delta == 0) return 0;
        delta--;
    }
    change_house(n, next, delta);
    return 1;
}

// FUNCTION: C2 0x42FF4
// WIN: 0x0046736a
// Lines 1758–1775
//
// Look for a free 2x2 or 3x3 footprint adjacent to the current cell so a house can grow into
// the larger tier.  Returns the winning orientation (1..4) or 0 if no footprint fits.
int stretch_house(int n, int variant)
{
    if (variant == 2) {
        if (stretch_to_2x2_house(n, variant, 0)) return 1;
        if (stretch_to_2x2_house(n, variant, 1)) return variant;
        if (stretch_to_2x2_house(n, variant, variant)) return 3;
        if (stretch_to_2x2_house(n, variant, 3)) return 4;
    } else if (variant == 3) {
        if (stretch_to_3x3_house(n, variant, 0)) return 1;
        if (stretch_to_3x3_house(n, variant, 1)) return 2;
        if (stretch_to_3x3_house(n, variant, 2)) return variant;
        if (stretch_to_3x3_house(n, variant, variant)) return 4;
    }
    return 0;
}

// FUNCTION: C2 0x430AF
// WIN: 0x004674b5
// Lines 1777–1798
//
// Test whether the current house can grow into a specific 2x2 orientation: every neighbour
// in `stretch_ofsets_2x2[orient]` must be empty or a same-tier house belonging to us.
int stretch_to_2x2_house(int p1, int unused, int orient)
{
    unsigned char *cell;
    int i;
    int toff;
    unsigned char cb1;
    unsigned char cb0;
    unsigned char cb7;
    unsigned char cb8;

    (void)unused;
    if (evolve_col == 0x4f) { fail: return 0; }
    if (evolve_row == 0x4f) goto fail;
    if (evolve_col == 0) goto fail;
    if (evolve_row == 0) goto fail;
    for (i = 0; i < 3; i++) {
        toff = stretch_ofsets_2x2[orient][i];
        cell = city_qptr + toff;
        cb1 = (unsigned char)cell[1];
        cb0 = (unsigned char)cell[0];
        cb7 = (unsigned char)cell[7];
        cb8 = (unsigned char)cell[8];
        if (cb7 != 0 || cb8 != 0) goto fail;
        if ((cb1 & 0xfe) != 0) goto fail;
        if ((cb1 & 1) != 0 && cb0 >= p1 + 0x82) goto fail;
    }
    return 1;
}

// FUNCTION: C2 0x4313D
// WIN: 0x004675ef
// Lines 1800–1836
//
// Test whether the current house can grow into a specific 3x3 orientation, and reduce any
// villa cells found in that footprint back to domus stubs.
//
// BYTE-EXACT 2026-07-11.  The first loop deliberately uses the flat pointer form with
// `(orient * 5) + i`; the second uses the 2D subscript.  Those associations reproduce
// PS's two distinct index trees.  The corrected temp map plus WIN's nine stack slots
// exposed the real final-loop locals: the masked value starts in `dy`, is copied to `dx`,
// and both are updated in place; the ninth local is `cell`, not an invented `off`.  That
// keeps `dy` in EBX through the *1600 chain and removes RC's final `mov eax,ebx`.
// Replacing `off` changed the temp-birth order, so commuting the flat index terms was also
// required to restore PS L1813.  `line-compare` reports no direction divergence.  Keep all
// declarations at function scope in strict-C89 form.
int stretch_to_3x3_house(int p1, int unused, int orient)
{
    int toff;
    unsigned char cb8;
    unsigned char cb1;
    unsigned char cb7;
    int dy;
    int dx;
    int i;
    unsigned char cb0;
    unsigned char *cell;

    if (evolve_col >= 0x4e) return 0;
    if (evolve_row >= 0x4e) return 0;
    if (evolve_col <= 0) return 0;
    if (evolve_row <= 0) return 0;
    for (i = 0; i < 5; i++) {
        toff = *((int *)stretch_ofsets_3x3 + (unsigned int)(orient * 5) + i);
        cb1 = city_qptr[toff + 1];
        cb0 = city_qptr[toff];
        cb7 = city_qptr[toff + 7];
        cb8 = city_qptr[toff + 8];
        if (cb7 != 0 || cb8 != 0) return 0;
        if ((cb1 & 0xfe) != 0) return 0;
        if ((cb1 & 1) != 0 && cb0 >= p1 + 0x82) return 0;
    }
    for (i = 0; i < 5; i++) {
        toff = stretch_ofsets_3x3[orient][i];
        cb0 = city_qptr[toff];
        if (cb0 >= 0x9c && cb0 <= 0x9f) {
            dy = city_qptr[toff + 5] & 0xf;
            dx = dy;
            dx %= 2;
            dy /= 2;
            cell = city_qptr + toff;
            cell -= dx * 20;
            cell -= dy * 1600;
            reduce_villa_to_domus(cell);
        }
    }
    return 1;
}

// FUNCTION: C2 0x43255
// WIN: 0x00467804
// Lines 1838–1866
//
// Stamp a `size`x`size` house of tier `n` onto the map starting from a chosen corner cell.
// Writes the kind / edge / index / sprite bytes for every cell in the footprint.
void change_house(int n, int size, int variant)
{
    int base = (unsigned char)house_gfxdat[n * 4];
    int row_skip = (80 - size) * 20;
    unsigned char *cell = city_qptr;
    int row;
    int col;
    int idx;
    unsigned char off;

    if (variant != 0) {
        if (variant == 1) cell -= 20;
        else if (variant == 2) cell -= 0x654;
        else if (variant == 3) cell -= 0x640;
    }

    for (row = 0, idx = 0; row < size; row++, cell += row_skip) {
        for (col = 0; col < size; col++, cell += 20, idx++) {
            if ((unsigned char)cell[0] < 0x82) cell[3] &= 0x7f;
            cell[0] = (char)(n + 0x82);
            cell[1] |= 1;
            cell[3] |= 1;
            cell[3] &= 0xc3;
            cell[5] = idx;
            if (size == 1) {
                cell[4] = base;
            } else if (size == 2) {
                off = diamond_ofsets_2x[idx];
                cell[4] = (char)(base + off);
            } else if (size == 3) {
                off = diamond_ofsets_3x[idx];
                cell[4] = (char)(base + off);
            }
        }
    }
}

// FUNCTION: C2 0x4332A
// WIN: 0x004679ae
// Lines 1868–1891
//
// After shrinking a house from a `prev`x`prev` footprint, fill the freed L-shaped strip with
// domus (kind 0x9b) stubs so the cells aren't left empty.
void pad_house_with_domus(int prev)
{
    int gfx;
    int stride;
    unsigned char *p;
    int row;
    int col;

    gfx    = house_gfxdat[0x64];
    stride = (80 - prev) * 20;
    p      = city_qptr;

    for (row = 0; row < prev; row++) {
        col = 0;
        for ( ; col < prev; col++, p += 20)
            ;
        p[0]  = 0x9b;
        p[3] |= 1;
        p[4]  = gfx;
        p[5]  = 0;
        p    += stride;
    }

    for (col = 0; col <= prev; col++, p += 20) {
        p[0]  = 0x9b;
        p[3] |= 1;
        p[4]  = gfx;
        p[5]  = 0;
    }
}

// FUNCTION: C2 0x433A1
// WIN: 0x00467a9b
// Lines 1893–1905
//
// Convert a 2x2 villa rooted at `cm` into four 1x1 domus cells.
void reduce_villa_to_domus(unsigned char *cm)
{
    int cy;
    int cx;

    for (cy = 0; cy < 2; cy++, cm += CITY_ROW - 2 * CITY_CELL_BYTES) {
        for (cx = 0; cx < 2; cx++, cm += CITY_CELL_BYTES) {
            ((cm)[0])        = 0x9b;
            ((cm)[3])  |= 1;
            ((cm)[4])  = house_gfxdat[0x64];
            ((cm)[5])  = 0;
        }
    }
}

// FUNCTION: C2 0x433D4
// WIN: 0x00467b19
// Lines 1907–1920
//
// Demolish the house at `city_qptr` back to dirt: clears all per-house flag bytes and resets
// the cell's kind to plain ground (0x1a).
void remove_house(void)
{
    city_qptr[0x00] = 0x1a;
    city_qptr[0x09] = 0;
    city_qptr[0x01] &= 0x18;
    city_qptr[0x03] &= 0xe3;
    city_qptr[0x03] &= 0xdf;
    city_qptr[0x03] &= 0x7f;
    city_qptr[0x0a] &= 0xfc;
    city_qptr[0x0b] &= 0xcf;
    city_qptr[0x0b] &= 0xf0;
    city_qptr[0x03] |= 1;
    city_qptr[0x05] = 0;
}

// FUNCTION: C2 0x43437
// WIN: 0x00467be6
// Lines 1923–1935
//
// Promote a plaza cell (kinds 0x7c..0x7e) to a higher tier based on its land-value rank `value`,
// only on the even cells of the diamond pattern.
void evolve_a_plaza(signed char value, signed char old_kind, int x)
{
    if ((evolve_row & 1) != 0) return;
    if ((x & 1) != 0) return;
    if (city_qptr[7] != 0) return;
    if (city_qptr[8] != 0) return;
    if ((signed char)value > 0x28) {
        city_qptr[0] = 0x7e;
        city_qptr[4] = 0x76;
    } else if ((signed char)value > 0x14) {
        city_qptr[0] = 0x7d;
        city_qptr[4] = 0x75;
    } else {
        city_qptr[0] = 0x7c;
        city_qptr[4] = 0x74;
    }
    if ((unsigned char)old_kind != city_qptr[0]) {
        flag_range(0, x, evolve_row, 1, 3, 1);
    }
}

// FUNCTION: C2 0x434BB
// WIN: 0x00467cc7
// Lines 1941–1951
//
// Decay every entry in the 10x10 `fire_zones` heatmap one step toward 0 (capped at 2).
void clear_fire_zones(void)
{
    int x;
    int y;
    int idx;

    for (x = 0; x < 10; x++) {
        for (y = 0; y < 10; y++) {
            idx = x * 10 + y;
            if (fire_zones[idx] > 2)        fire_zones[idx] = 2;
            else if (fire_zones[idx] > 1)   fire_zones[idx] = 1;
            else if (fire_zones[idx] <= 1)  fire_zones[idx] = 0;
        }
    }
}

// FUNCTION: C2 0x4350A
// WIN: 0x00467d9c
// Lines 1957–2002
//
// Per-row pass that propagates the wall-shadow / security value outward from walls
// (terrain & 0x1e) in the rolling `shell_push_direction`.  Re-evaluates every cell's
// `security` byte as it sweeps a single axis per call.
//
// The neighbour wall-test value is a SEPARATE local (neighbour_w), not a reuse of
// max_local: splitting it drops max_local's savings (1210 -> 610) below inner's
// (710), which flips the allocation order so inner takes EDX and max_local BL,
// exactly PS's seats (the wall-branch phase and the loop-carried max_local are
// disjoint, so neighbour_w shares BL).  This was the whole 41b EBX<->EDX residue.
void push_shell(int rows)
{
    int xstride;
    unsigned char has_neighbour;
    int d;
    int row;
    int ymul;
    int inner;
    unsigned char neighbour_b;
    unsigned char neighbour_w;
    int start_offset;
    char new_val;
    unsigned char max_local;
    unsigned char wall;

    if (evolve_row == 0) {
        shell_push_direction++;
        if (shell_push_direction >= 4) shell_push_direction = 0;
    }
    if (shell_push_direction == 0)      { ymul = 20;   xstride =  1600; start_offset = 0;       }
    else if (shell_push_direction == 1) { ymul = 1600; xstride =   -20; start_offset = 0x62c;   }
    else if (shell_push_direction == 2) { ymul = 20;   xstride = -1600; start_offset = 0x1edc0; }
    else if (shell_push_direction == 3) { ymul = 1600; xstride =    20; start_offset = 0;       }

    for (row = 0; row < rows; row++) {
        cm_sptr = start_offset + (evolve_row + row) * ymul;
        max_local      = 0xf8;
        has_neighbour  = 0;
        for (inner = 0; inner < 80; inner++, cm_sptr += xstride) {
            wall = (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).terrain & 0x1e;
            if (wall != 0) {
                neighbour_w   = 1;
                (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).security    = 100;
                d = shell_push_direction;
                if (d == 0) {
                    if (inner > 0) {
                        neighbour_w = (*(struct city_cell *)((unsigned char *)city_map + ((cm_sptr) - 20))).terrain & 0x1e;
                        neighbour_b = (*(struct city_cell *)((unsigned char *)city_map + ((cm_sptr) - 20))).security;
                    }
                } else if (d == 1) {
                    if (inner > 0) {
                        neighbour_w = (*(struct city_cell *)((unsigned char *)city_map + ((cm_sptr) - 1600))).terrain & 0x1e;
                        neighbour_b = (*(struct city_cell *)((unsigned char *)city_map + ((cm_sptr) - 1600))).security;
                    }
                } else if (d == 2) {
                    if (inner < 0x4f) {
                        neighbour_w = (*(struct city_cell *)((unsigned char *)city_map + ((cm_sptr) + 20))).terrain & 0x1e;
                        neighbour_b = (*(struct city_cell *)((unsigned char *)city_map + ((cm_sptr) + 20))).security;
                    }
                } else if (d == 3) {
                    if (inner < 0x4f) {
                        neighbour_w = (*(struct city_cell *)((unsigned char *)city_map + ((cm_sptr) + 1600))).terrain & 0x1e;
                        neighbour_b = (*(struct city_cell *)((unsigned char *)city_map + ((cm_sptr) + 1600))).security;
                    }
                }
                if (neighbour_w == 0) {
                    max_local = neighbour_b;
                } else {
                    has_neighbour = 1;
                    max_local = 100;
                }
            } else if (has_neighbour) {
                new_val = (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).security;
                if ((signed char)new_val < 100) new_val++;
                if ((signed char)new_val > (signed char)max_local) new_val = max_local;
                (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).security = new_val;
                max_local  = new_val;
            } else {
                (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).security = max_local;
            }
        }
    }
}

// FUNCTION: C2 0x436AB
// WIN: 0x00468079
// Lines 2008–2214
//
// Per-row pass over the region map: evolves city tier sprites (kind 0x92, 0x97, 0x98..0x9b,
// 0xd3), ticks down warehouse delivery flags, and pushes new goods deliveries into the
// industry pipelines based on trader source and difficulty.
//
// Shape notes (2026-07-09, 1746bd -> 56bd): the inner for's increment clause carries
// `cm_sptr += 8` (skip path is `continue`, NOT a trailing label stmt -- WIN funnel witness);
// the difficulty pre-calc uses its own temp `t` (v owning it made v's whole-loop web spill,
// wrecking every seat: PS has v=ESI, col=EDI, row=EBP, difficulty spilled); the e8-eb/ec-ef
// map update is `x = v; x <<= 2;` (int x, WIN in-place-shl witness) + TWO compound RMWs on
// the map byte (Rule 143 store-forwards them to one load / copy chain / one store); the
// e0-e3/e4-e7 trader refill RMWs `trader` itself (no wkind intermediate, PS L2126-2129);
// the ec-ef 0xd5 radius result lands in `t` (PS -d1 L2191/L2192 two marks + WIN iVar3).
// SOLVED (2026-07-09, 56bd -> 0bd): the kind<->tier slot transposition (Rule 107,
// shellsort-instability) fell to pure DECL ORDER after all -- but only a COMPOSED
// two-swap permutation reaches it: t first / trader second-to-last (swap trader<->t)
// PLUS skip before e3 / wkind late (swap wkind<->skip).  The earlier "decl-order is
// inert" note held only for SINGLE swaps of the spilled pair; a full 503-variant
// byte-oracle sweep (ForgeBuilder LE, docs/codegen-experiments/spell-verdict-audit.py
// harness) found 9 single swaps reaching 6bd, and a second sweep on that baseline
// found wkind<->skip closing the residual `mov dl,bh`-vs-`or` order flip at the e4-e7
// trader refill.  Line-compare witness: the outer for is BRACELESS (both loop tails
// attribute their -d1 mark to the inner `}` line -- Watcom marks for-increment/cond
// insns with the closing-brace line); `if (...) stmt; else stmt;` packs at the
// workcamps and 0xd5-radius sites; `cmu_count[4] = 0` sits on its own line.
void evolve_region(int rows)
{
    int t;
    int col;
    unsigned char skip;
    unsigned char e3;
    int pop_level;
    unsigned char o6;
    unsigned char gfx;
    unsigned char wkind;
    unsigned char tier;
    int row;
    int pop_target;
    int v;
    int difficulty;
    unsigned char kind;
    unsigned char trader;
    int x;

    if (c2inf.peace_mode != 0) {
        return;
    }

    pop_level = get_pop_level();
    pop_target = slave_requirements[5].current;
    if (no_of_workcamps != 0) pop_target /= no_of_workcamps;
    else pop_target = 0;
    pop_target /= 10;
    if (pop_target > 3) pop_target = 3;
    if (pop_target < 0) pop_target = 0;

    if (evolve_row == 0)
        cmu_count[4] = 0;

    t = (province_difficulty + rand8) * 4;
    if      (t > 0x3c) difficulty = 3;
    else if (t > 0x30) difficulty = 2;
    else if (t > 0x20) difficulty = 1;
    else               difficulty = 0;

    cm_sptr = evolve_row * 480;

    for (row = 0; row < rows; row++)
        for (col = 0; col < 60; col++, cm_sptr += 8) {
            skip = ((unsigned char *)region_map)[cm_sptr + 7] & 3;
            kind = ((unsigned char *)region_map)[cm_sptr];
            if (kind == 0xd4) skip = 0;
            if (skip != 0) continue;

            gfx = ((unsigned char *)region_map)[cm_sptr + 4];
            e3  = ((unsigned char *)region_map)[cm_sptr + 3] & 0x20;
            o6  = ((unsigned char *)region_map)[cm_sptr + 6] & 0x40;

            if (kind == 0x92 && cmu_count[4] == 0) {
                v = pop_level;
                cmu_count[4] = 1;
                tier = gfx / 4;
                if (tier < v) change_reg_sized(kind, gfx + 4, 2, cm_sptr);
                if (v < tier) change_reg_sized(kind, gfx - 4, 2, cm_sptr);
            } else if (kind >= 0x98 && kind <= 0x9b) {
                v = (pop_level - 1) / 2;
                if (e3 && o6) v += 2;
                else if (e3)   v += 4;
                tier = gfx - 0x50;
                if (v > tier) change_reg_sized(kind, gfx + 1, 1, cm_sptr);
                if (v < tier) change_reg_sized(kind, gfx - 1, 1, cm_sptr);
            } else if (kind == 0x97) {
                v = (pop_level - 1) / 2;
                if (e3 && o6) v += 2;
                else if (e3)   v += 4;
                tier = gfx - 0x32;
                if (v > tier) change_reg_sized(kind, gfx + 1, 1, cm_sptr);
                if (v < tier) change_reg_sized(kind, gfx - 1, 1, cm_sptr);
            } else if (kind == 0xd3) {
                v = pop_target;
                tier = gfx - 0x3c;
                if (tier < v) change_reg_sized(kind, gfx + 1, 1, cm_sptr);
                if (v < tier) change_reg_sized(kind, gfx - 1, 1, cm_sptr);
            } else if (kind == 0xd4) {
                ;
            } else if (kind >= 0xdc && kind <= 0xdf) {
                v = get_reg_buildings_in_radius(col, evolve_row + row, 2, 1, 0xd3);
                v = pop_target * v;
                if (e3 && o6) v--;
                else if (!e3) v = 0;
                if (v > 3) v = 3; else if (v < 0) v = 0;
                tier = kind - 0xdc;
                if (v > tier) change_reg_sized(kind + 1, gfx + 4, 2, cm_sptr);
                if (v < tier) change_reg_sized(kind - 1, gfx - 4, 2, cm_sptr);
                trader = ((unsigned char *)region_map)[cm_sptr + 7] & 0xf0;
                trader >>= 4;
                if (v > difficulty) {
                    v -= difficulty;
                    fill_warehouses_with(col, evolve_row + row, v, trader, 0);
                    industry[trader].supply_pipeline[1] += v;
                }
            } else if (kind >= 0xe0 && kind <= 0xe3) {
                v = get_reg_buildings_in_radius(col, evolve_row + row, 2, 1, 0xd3);
                v = pop_target * v;
                if (e3 && o6) v--;
                else if (!e3) v = 0;
                if (v > 3) v = 3; else if (v < 0) v = 0;
                tier = kind - 0xe0;
                if (v > tier) change_reg_sized(kind + 1, gfx + 4, 2, cm_sptr);
                if (v < tier) change_reg_sized(kind - 1, gfx - 4, 2, cm_sptr);
                trader = ((unsigned char *)region_map)[cm_sptr + 7] & 0xf0;
                trader >>= 4;
                if (trader == 0) {
                    trader = region_sources[province_is].choices[3];
                    trader <<= 4;
                    ((unsigned char *)region_map)[cm_sptr + 7] |= trader;
                    trader >>= 4;
                }
                if (v > difficulty) {
                    v -= difficulty;
                    fill_warehouses_with(col, evolve_row + row, v, trader, 0);
                    industry[trader].supply_pipeline[1] += v;
                }
            } else if (kind >= 0xe4 && kind <= 0xe7) {
                v = get_reg_buildings_in_radius(col, evolve_row + row, 2, 1, 0xd3);
                v = pop_target * v;
                if (e3 && o6) v--;
                else if (!e3) v = 0;
                if (v > 3) v = 3; else if (v < 0) v = 0;
                tier = kind - 0xe4;
                if (v > tier) change_reg_sized(kind + 1, gfx + 4, 2, cm_sptr);
                if (v < tier) change_reg_sized(kind - 1, gfx - 4, 2, cm_sptr);
                trader = ((unsigned char *)region_map)[cm_sptr + 7] & 0xf0;
                trader >>= 4;
                if (trader == 0) {
                    trader = region_sources[province_is].choices[6];
                    trader <<= 4;
                    ((unsigned char *)region_map)[cm_sptr + 7] |= trader;
                    trader >>= 4;
                }
                if (v > difficulty) {
                    v -= difficulty;
                    fill_warehouses_with(col, evolve_row + row, v, trader, 0);
                    industry[trader].supply_pipeline[1] += v;
                }
            } else if (kind >= 0xe8 && kind <= 0xeb) {
                v = ((unsigned char *)region_map)[cm_sptr + 7] & 0x1c;
                v >>= 2;
                if (v != 0) v--;
                x = v; x <<= 2;
                ((unsigned char *)region_map)[cm_sptr + 7] &= 0xe3;
                ((unsigned char *)region_map)[cm_sptr + 7] |= x;
                if (e3 && o6) v--;
                else if (!e3) v = 0;
                if (v > 3) v = 3; else if (v < 0) v = 0;
                tier = kind - 0xe8;
                if (v > tier) change_reg_sized(kind + 1, gfx + 4, 2, cm_sptr);
                if (v < tier) change_reg_sized(kind - 1, gfx - 4, 2, cm_sptr);
                wkind = ((unsigned char *)region_map)[cm_sptr + 7] & 0x60;
                if      (wkind == 0)    trader = north_trader_brings;
                else if (wkind == 0x20) trader = east_trader_brings;
                else if (wkind == 0x40) trader = south_trader_brings;
                else if (wkind == 0x60) trader = west_trader_brings;
                fill_warehouses_with(col, evolve_row + row, v, trader, 0);
            } else if (kind >= 0xec && kind <= 0xef) {
                t = get_reg_buildings_in_radius(col, evolve_row + row, 2, 1, 0xd5);
                if (t != 0) ((unsigned char *)region_map)[cm_sptr + 7] |= 0x80;
                else ((unsigned char *)region_map)[cm_sptr + 7] &= 0x7f;
                v = ((unsigned char *)region_map)[cm_sptr + 7] & 0x1c;
                v >>= 2;
                if (v != 0 && (evolve_tick4 & 1)) v--;
                x = v; x <<= 2;
                ((unsigned char *)region_map)[cm_sptr + 7] &= 0xe3;
                ((unsigned char *)region_map)[cm_sptr + 7] |= x;
                if (e3 && o6) v--;
                else if (!e3) v = 0;
                if (v > 3) v = 3; else if (v < 0) v = 0;
                tier = kind - 0xec;
                if (v > tier) change_reg_sized(kind + 1, gfx + 4, 2, cm_sptr);
                if (v < tier) change_reg_sized(kind - 1, gfx - 4, 2, cm_sptr);
            }
        }
}

// FUNCTION: C2 0x43F9F
// WIN: 0x00468d77
// Lines 2216–2226
//
// Return the city population bracket (0..7) used to gate region-map growth.
int get_pop_level(void)
{
    if (population > 12000) return 7;
    if (population >  8000) return 6;
    if (population >  4000) return 5;
    if (population >  2000) return 4;
    if (population >  1000) return 3;
    if (population >   500) return 2;
    if (population >   250) return 1;
    return 0;
}

// FUNCTION: C2 0x44013
// WIN: 0x00468e5d
// Lines 2228–2296
//
// Walk the whole region map once and sum each industry's warehouse counts/supplies/deliveries.
// Refreshes per-good sprites for warehouses still being unloaded.  In peace mode just
// copies the static city-supply table.
//
// BYTE-EXACT (2026-07-12): the WIN /Od frame witnesses one `i` across all
// three 16-loops and the outer 60-loop, an inner `sx`, and no early use of
// the final-loop `t`.  The original peace branch writes the field directly
// (`status = 0; status = i & 1; if (status) status++`), and the map walk is
// two nested C89 `for` loops with `sx++, cm_sptr += 8` in the inner header.
// Once those source identities were restored, Rule 115 made the function's
// front-of-function declaration order load-bearing: i, sx, delivered_now,
// t, idx, kind, unit, unit2, d seats kind in CL and closes the former 19/147b
// allocator plateaus.  `line-compare` also proves the compact one-line
// conditionals and shared `} } }` loop tail: 47/47 transitions, clean.
void check_goods_in_region_warehouses(void)
{
    int i;
    int sx;
    unsigned char delivered_now;
    int t;
    unsigned char idx;
    unsigned char kind;
    unsigned char unit;
    unsigned char unit2;
    int d;

    if (c2inf.peace_mode) {
        for (i = 0; i < 16; i++) {
            industry[i].city_supply = city_level_good_supply[i];
            industry[i].status = 0;
            industry[i].status = i & 1;
            if (industry[i].status) industry[i].status++;
        }
        return;
    }

    for (i = 0; i < 16; i++) {
        industry[i].count     = 0;
        industry[i].supply    = 0;
        industry[i].delivered = 0;
    }

    i = 0; cm_sptr = 0;
    for (; i < 60; i++) {
        for (sx = 0; sx < 60; sx++, cm_sptr += 8) {
            kind = ((unsigned char *)region_map)[cm_sptr];
            if (kind == 0xd4) {
                delivered_now = ((unsigned char *)region_map)[cm_sptr + 7] & 0x0f;
                idx = ((unsigned char *)region_map)[cm_sptr + 7] & 0xf0;
                idx >>= 4;
                idx &= 0xf;
                industry[idx].count++;
                if (delivered_now != 0) {
                    industry[idx].status = 2;
                    unit = industry[idx].unit_size;
                    if (delivered_now <= unit) {
                        unit -= delivered_now;
                        industry[idx].delivered += delivered_now;
                        delivered_now = 0;
                    } else {
                        delivered_now -= unit;
                        industry[idx].delivered += unit;
                        industry[idx].supply += delivered_now;
                        unit = 0;
                    }
                    industry[idx].unit_size = unit;
                    ((unsigned char *)region_map)[cm_sptr + 7] &= 0xf0;
                    ((unsigned char *)region_map)[cm_sptr + 7] |= delivered_now;
                    if (delivered_now < 0xf) unit2 = delivered_now + 11;
                    else unit2 = 0x24;
                    change_reg_sized(kind, unit2, 1, cm_sptr);
                }
            } } }

    for (i = 0; i < 16; i++) {
        d = industry[i].delivered;
        t = industry[i].has_supply;
        if (t) industry[i].city_supply = valueDIVtotal(d, t);
        else industry[i].city_supply = 0;
    }
}
