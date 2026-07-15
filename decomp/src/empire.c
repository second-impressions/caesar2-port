// D:\C2\CODE\empire.c

#include "c2_data.h"
#include "c2_types.h"     /* struct province_industry / mercs_class */


// FUNCTION: C2 0x57B49
// WIN: 0x00459540
// Lines 12–20
void clear_empire(void)
{
    int i;
    for (i = 0; i < 44; i++) empire[i]     = 0;
    for (i = 0; i < 44; i++) empire_won[i] = 0;
    empire[0]     = 6;
    empire_won[0] = 99998;
}

// FUNCTION: C2 0x57B81
// WIN: 0x004595b3
// Lines 22–45
void get_new_province_options(void)
{
    int i;
    int j;
    int idx;

    provinces_on_offer    = 0;
    auto_conquered        = pompous_conquests[c2inf.skill_level];
    auto_conquered_months = 0;

    for (i = 0; i < 44; i++) {
        if (empire[i] != 6) empire[i] = 0;
    }

    for (i = 0; i < 44; i++) {
        if (empire[i] == 6) continue;
        if (i >= 36 && player_rank < 10) continue;
        for (j = 0; j < 4; j++) {
            idx = region_borders[i].u.dir[j];
            if (idx >= 44) continue;
            if (empire[idx] != 6) continue;
            empire[i] = 2;
            provinces_on_offer++;
        }
    }
}

// FUNCTION: C2 0x57C25
// WIN: 0x004596d5
// Lines 47–58
int known_world(int prov)
{
    int i;
    int idx;
    if (empire[prov] == 6) return 1;
    for (i = 0; i < 4; i++) {
        idx = region_borders[prov].u.dir[i];
        if (idx >= 44) continue;
        if (empire[idx] == 6) return 1;
    }
    return 0;
}

// FUNCTION: C2 0x57C74
// WIN: 0x00459760
// Lines 60–95
void auto_conquer(void)
{
    int i;
    int j;
    int pick;
    int count;
    int idx;

    if (c2inf.peace_mode != 0) return;
    if (player_rank >= 10) return;
    auto_conquered_months++;
    if (auto_conquered_months < 30) return;
    if (auto_conquered <= 0) return;

    pick  = rand128 & 7;
    count = 0;
    for (i = 0; i < 44; i++) {
        if (empire[i] == 6) continue;
        for (j = 0; j < 4; j++) {
            idx = region_borders[i].u.dir[j];
            if (idx >= 44) continue;
            if (empire[idx] != 6) continue;
            if (count == pick) {                          /* Rule 9: action-first */
                put_message(100, 0, 11);
                empire[i]     = 6;
                empire_won[i] = 99999;
                auto_conquered--;
                auto_conquered_months = rand8;
                return;
            }
            count++;
        }
    }
}

// FUNCTION: C2 0x57D45
// WIN: 0x0045989f
// Lines 97–160
void set_new_province(void)
{
    int i;
    int dir;
    int pick;
    int v;

    empire[province_is] = 6;

    /* Clear the prior "on offer" provinces. */
    for (i = 0; i < 44; i++) {
        if (empire[i] == 2) {
            empire[i] = 0;
        }
    }

    if (c2inf.peace_mode != 0) {
        mercs_in_army     = 0;
        max_mercs_allowed = 0;
        return;
    }

    /* Pick four industry kinds for the new province, retrying until
       a valid (<16) kind comes back. */
    pick = 0; i = 0;
    while (i < 4) {
        if      (pick < 3) v = region_sources[province_is].choices[pick % 3];
        else if (pick < 6) v = region_sources[province_is].choices[3 + (pick % 3)];
        else               v = region_sources[province_is].choices[6 + (pick % 3)];
        pick++;
        if (v >= 16) continue;
        province_industries[i].kind      = v;
        province_industries[i].is_trader = 0;
        industry[v].status               = 1;
        i++;
    }

    /* For each of the four neighbours, copy the region's primary
       source into province_industries and trip the trader column to
       1 if the corresponding direction has no trader yet. */
    for (dir = 0; dir < 4; dir++, i++) {
        v = region_sources[region_borders[province_is].u.dir[dir]].primary;
        province_industries[i].kind      = v;
        province_industries[i].is_trader = 2;
        industry[v].status               = 1;

        if (dir == 0 && north_trader_is == 0) province_industries[i].is_trader = 1;
        if (dir == 1 && east_trader_is  == 0) province_industries[i].is_trader = 1;
        if (dir == 2 && south_trader_is == 0) province_industries[i].is_trader = 1;
        if (dir == 3 && west_trader_is  == 0) province_industries[i].is_trader = 1;
    }

    mercs_in_army = 0;
    mercs_from    = mercenary_type[province_is].mercs_from;
    if (mercs_from != 0) {
        mercs_catagory    = mercenary_type[province_is].category;
        max_mercs_allowed = mercenary_type[province_is].max_allowed;
        mercs_cost_per_50 = mercenary_type[province_is].cost_per_50;

        mercs_tribe = (unsigned char)tribe_type[mercs_from];
        mercs_type  = tribe_battle_setup[mercs_tribe].u.raw[mercs_catagory];

        if      (mercs_catagory == 0) mercs_speed = 0;
        else if (mercs_catagory == 1) mercs_speed = 3;
        else                          mercs_speed = 2;

        if      (mercs_catagory == 0) mercs_missile = 1;
        else if (mercs_catagory == 3) mercs_missile = 1;
        else                          mercs_missile = 0;
    }
    else {
        max_mercs_allowed = 0;
    }
}
