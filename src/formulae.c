// D:\C2\CODE\formulae.c
//
// Financial and military accounting, promotion logic, slave/army management.
//
// Functions marked FUNCTION have been decompiled and verified byte-identical.
// Functions marked STUB have not yet been reverse engineered.

#include "c2_data.h"
#include "c2_types.h"

char events[5][64] = {
    { 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4, 0, 0, 0 },
    { 0, 0, 0, 0, 4, 0, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 3, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0 },
    { 0, 0, 0, 0, 4, 0, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 3, 0, 0, 4, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 0, 0, 0, 3, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 3, 0, 0, 0, 4, 0, 0, 0 },
    { 0, 0, 0, 0, 4, 0, 0, 0, 0, 0, 2, 0, 0, 0, 0, 3, 0, 0, 3, 0, 0, 0, 0, 0, 3, 0, 0, 4, 0, 0, 0, 0, 0, 0, 4, 0, 0, 0, 0, 0, 0, 2, 0, 0, 0, 3, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 3, 0, 0, 4, 0, 0, 0 },
    { 0, 0, 0, 0, 4, 0, 0, 0, 0, 0, 2, 0, 4, 0, 0, 3, 0, 0, 3, 0, 0, 0, 0, 0, 3, 0, 0, 4, 0, 0, 0, 3, 0, 0, 4, 0, 0, 3, 0, 0, 0, 2, 0, 0, 0, 3, 0, 0, 0, 0, 4, 0, 0, 0, 0, 0, 3, 3, 0, 0, 4, 0, 0, 0 }
};

/* Army sizing / tax parameters live in the main_paras[10] startup table
   (data.c; see datainit.c): [1] = regular-cohort baseline, [2..4] =
   recruit caps (aux/irr/reg), [5] = imperial_tax reset base (= 4). */


// ── Army record ──────────────────────────────────────────────────────────────
// 26 records of 0xAF (175) bytes each starting at linker symbol `army_list`.
// Only the fields needed by formulae.c are declared; the rest are padding.
//
// Cohort `type` encoding (used in centuries[]): 0=empty, 1=regulars,
// 2=irregulars, 3=auxillaries, 4=specials. (Yes, this is the order baked
// into the original game logic; it does not match the offset order of the
// num_* fields below.)
// army_rec and century are defined in c2_types.h.
// ── External functions ────────────────────────────────────────────────────────
void stop_db(void);

// `#pragma aux NAME modify exact [eax]`: PS.EXE's functions all push/pop
// every register they touch, so from the caller's perspective they only
// clobber EAX (and flags). Advertising this via a narrow modify clause
// does two useful things:
//
//   1. Forces the callee's own codegen to preserve ebx/ecx/edx/esi/edi/ebp
//      whenever it uses them (matching PS.EXE's "save everything" prologue).
//   2. Tells caller-side cost heuristics that the call is cheap to cross
//      with live values in the scratch set. This does NOT force the
//      allocator to pick specific registers (Watcom has no GCC-style
//      `register int x asm("ebx")` hint), but it does change which
//      allocation schemes the compiler considers affordable.
//
// NOTE: empirically these pragmas interact poorly with `-os` (the compiler
// picks a size-favouring body layout that no longer fills the forced
// callee-saved slots) so we don't sprinkle them everywhere. If a specific
// function benefits, add a targeted pragma immediately before its
// definition.

// ── Stubs ─────────────────────────────────────────────────────────────────────

// FUNCTION: C2 0x55326
// WIN: 0x00454cb0
// Lines 58–71
// Rule 1 (strong form) applied: every read of months_to_game_over is inline
// (no `x` local). This triggers value-pool allocation into EBX and produces
// `lea ecx,[ebx-1]` for the decrement (keeping the pre-op value live).
void check_game_over(void) {
    if (denarii >= 0) {
        months_to_game_over = 0;
        return;
    }
    if (months_to_game_over == 0) {
        put_message(0x62, 0, 0xe);
        months_to_game_over = 24;
        return;
    }
    months_to_game_over--;
    if (months_to_game_over == 12) {
        put_message(0x63, 0, 0xd);
    }
    if (months_to_game_over <= 0) {
        game_state = 1;
    }
}

// FUNCTION: C2 0x5539D
// WIN: 0x00454d39
// Lines 73–106
// Rule 1 applied: read empire_rating, refused_promotion, c2inf.skill_level,
// and completed_provinces inline instead of via `emp`, `ref`, `lv`,
// `compl` locals so Watcom CSE hoists them into value-pool registers.
void check_for_promotion(void) {
    int level;
    adjust_culture_criteria();
    adjust_proserity_criteria();
    if (c2inf.peace_mode == 0) {
        adjust_empire_criteria();
        adjust_peace_criteria();
        average_rating = (peace_rating + culture_rating + empire_rating + prosperity_rating) / 4;
        if (refused_promotion != 0) refused_promotion--; else {
            if (promotion_cheat != 1) {
                if (peace_rating < promotion_levels[c2inf.skill_level][completed_provinces]) return;
                if (promotion_levels[c2inf.skill_level][completed_provinces] > culture_rating) return;
                if (empire_rating < promotion_levels[c2inf.skill_level][completed_provinces]) return;
                if (promotion_levels[c2inf.skill_level][completed_provinces] > prosperity_rating) return;
                if (average_rating < promotion_av_levels[c2inf.skill_level][completed_provinces]) return;
            }
            promotion_cheat = 0;
            level = province_completion_to_promotion[c2inf.skill_level][completed_provinces];
            empire_won[province_is] = years_elapsed_in_region + 1;
            if (want_promotion(level) != 0) {
                completed_provinces++;
                if (completed_provinces > 19) completed_provinces = 19;
                if (level == 0) assign_to_new_province();
                else do_promotion(level);
            }
        }
    }
}

// FUNCTION: C2 0x554F3
// WIN: 0x00454f27
// Lines 108–120
// Rule 2 applied: pre-load pax_romanum into `t` local before the divide to
// force EDX-first dividend ordering (`mov edx,[m]; mov ebx,10; mov eax,edx;
// sar edx,31; idiv ebx`) matching PS.EXE.
void adjust_peace_criteria(void) {
    int orig;
    int adj;
    int t;
    pax_romanum += 2;
    if (pax_romanum > 1000) pax_romanum = 1000;
    if (pax_romanum < 0)    pax_romanum = 0;
    t = pax_romanum;
    peace_rating = t / 10;                          // store before reg-save
    orig = peace_rating;
    adj = city_pop_limit_10_to_1(orig, 1);
    peace_rating = adj;
    peace_rating_pop_limit = (orig > adj);
    if (population < 10)
        peace_rating_pop_limit = 0;
}

// FUNCTION: C2 0x55573
// WIN: 0x00454fdb
// Lines 122–163
// NOTE: Original uses LEA-chain register pattern and multiple intermediate stores;
// compiler register allocation differs. Logic correct.
// Direct-global-update pattern: apply `+=` directly to each level global
// (no `ent`/`rel`/`util` locals). Watcom emits `mov [m],reg` then
// `add [m],reg` for each subsequent term, matching PS.EXE exactly.
void adjust_culture_criteria(void) {
    int divisor;
    int orig;
    int adj;
    entertainment_level  = theatre_culture_count * 5;
    entertainment_level += odium_culture_count * 8;
    entertainment_level += arena_culture_count * 12;
    entertainment_level += colosseum_culture_count * 16;
    entertainment_level += circus_culture_count * 20;
    entertainment_level += circus_maximus_culture_count * 25;
    entertainment_level *= 100;
    religion_level  = large_temples_culture_count * 12;
    religion_level += med_temples_culture_count * 7;
    religion_level += small_temples_culture_count * 2;
    religion_level *= 100;
    utility_level  = (plaza_culture_count + gardens_culture_count) / 2;
    utility_level += grammaticus_culture_count * 4;
    utility_level += rhetor_culture_count * 7;
    utility_level += accessed_hospitals_count * 10;
    utility_level += accessed_libraries_count * 20;
    utility_level *= 100;
    divisor = population / 16 + 2;
    entertainment_level /= divisor;
    religion_level /= divisor;
    utility_level /= divisor;
    if (entertainment_level > 100) entertainment_level = 100;
    if (religion_level > 100) religion_level = 100;
    if (utility_level > 100) utility_level = 100;
    culture_rating = (entertainment_level + religion_level + utility_level) / 3;
    orig = culture_rating;
    adj = city_pop_limit_10_to_1(culture_rating, 3);
    culture_rating = adj;
    culture_rating_pop_limit = (orig > adj);
    if (population < 10) culture_rating_pop_limit = 0;
}

// FUNCTION: C2 0x557AF
// WIN: 0x00455201
// Lines 165–192
// Rule 3 applied: `current_gdp = sum; current_gdp /= 4;` (two assignments
// straddling the divide) makes Watcom emit a pre-divide store in addition
// to the post-divide store, matching PS.EXE's triple-store-to-global.
void adjust_proserity_criteria(void) {
    int pop_cap;
    int rating;
    current_gdp = average_pop_tax_denariis * 100 + average_pop_tax_asses;
    current_gdp /= 4;
    if (current_gdp > 60) current_gdp = 60;
    pop_cap = population;
    if (pop_cap > 2000) pop_cap = 2000;
    pop_cap /= 60;
    if (month == 11) rolling_profit += account_total;
    if (rolling_profit < -5000) rolling_profit = -5000;
    if (rolling_profit > 5000) rolling_profit = 5000;
    prosperity_rating = current_gdp + pop_cap + rolling_profit / 200;
    rating = prosperity_rating;
    prosperity_rating = city_pop_limit_10_to_1(rating, 4);
    prosperity_rating_pop_limit = (rating > prosperity_rating);
    if (population < 10) prosperity_rating_pop_limit = 0;
}

// FUNCTION: C2 0x558A0
// WIN: 0x00455342
// Lines 194–212
// Direct-global-update pattern: apply `+=` directly to empire_rating in
// memory (no `rating` local). Watcom emits the full 6-reg push set
// (ebx,ecx,edx,esi,edi,ebp) matching PS.EXE.
void adjust_empire_criteria(void) {
    int orig;
    int adj;
    empire_rating  = (imperial_favour - 80) / 10;
    empire_rating += no_of_empire_connections * 15;
    empire_rating += no_of_connected_towns * 5;
    empire_rating += (no_of_workcamps + no_of_warehouses) / 2;
    empire_rating += no_of_shipyards * 2;
    empire_rating += no_of_farms;
    empire_rating += no_of_mines;
    empire_rating += no_of_quarrys;
    empire_rating += no_of_trading_posts * 2;
    orig = empire_rating;
    adj = city_pop_limit_10_to_1(empire_rating, 1);
    empire_rating = adj;
    empire_rating_pop_limit = (orig > adj);
    if (population < 10) empire_rating_pop_limit = 0;
}

// FUNCTION: C2 0x55992
// WIN: 0x00455432
// Lines 215–230
int city_pop_limit_10_to_1(int value, int factor) {
    int counter;
    if (value < 0) value = 0;
    if (value > 100) value = 100;
    for (counter = 0; counter < 100; counter++) {
        if (counter * 10 * factor >= population) {
            if (value > counter) value = counter;
            break;
        }
    }
    return value;
}

// FUNCTION: C2 0x559D5
// WIN: 0x004554ba
// Lines 232–260
// NOTE: Original pushes EBX/ECX/EDX and zero-extends bytes via xor+mov al;
// compiler uses movzx and drops ECX from the save list. Logic correct.
int want_promotion(int level) {
    int top_rank;
    pointer_mode = 0;
    show_want_promotion_box(player_rank + level);
    clear_mouse();
    out2 = 0;
    decision = 0;
    while (out2 != 1) {
        promotion_game_loop();
    }
    flush_sb_buffer();
    stop_db();
    top_rank = level + player_rank;
    if (top_rank >= 10 && decision == 1) {
        if (c2inf.skill_level < 2) {
            make_emperor();
            return 0;
        }
        confirm(13, 160, 160);
        if (decision == 0) {
            make_emperor();
            return 0;
        }
    }
    if (decision == 1) {
        stop_db();
        return 1;
    }
    load_map_graphics(map_mode, zoom_level);
    if (map_mode == 0) {
        city_map_screen(1);
    } else if (map_mode == 1) {
        region_map_screen(1);
    }
    flush_sb_buffer();
    stop_db();
    return 0;
}

// ── Decompiled functions ──────────────────────────────────────────────────────

// FUNCTION: C2 0x55AC7
// WIN: 0x004556eb
// Lines 262–262
void act_take_promotion(void) {
    decision = 1;
    out2 = 1;
}

// FUNCTION: C2 0x55AD9
// WIN: 0x00455707
// Lines 263–263
// NOTE: PS.EXE emits `xor ah,ah; mov [decision],ah` (10.0-era quirk for
// char = 0) where Watcom 10.0a emits `mov byte [decision],0`. Logic correct.
void act_review_in_10(void) {
    decision = 0;
    out2 = 1;
    refused_promotion = 120;
}

// FUNCTION: C2 0x55AF6
// WIN: 0x0045572d
// Lines 264–264
// NOTE: Same xor ah / mov byte,0 codegen difference as act_review_in_10.
void act_review_in_25(void) {
    decision = 0;
    out2 = 1;
    refused_promotion = 300;
}

// FUNCTION: C2 0x55B13
// WIN: 0x00455753
// Lines 266–269
void assign_to_new_province(void) {
    game_state = 3;
}

// FUNCTION: C2 0x55B1E
// WIN: 0x00455768
// Lines 271–277
// Rule 1 applied: read player_rank inline twice (no `rank` local) so
// Watcom CSE hoists the load into EBX (value-pool) rather than EDX (temp).
void do_promotion(int level) {
    game_state = 3;
    if (player_rank < 10) {
        level += player_rank;
        if (level <= 10) {
            player_rank = level;
        }
    }
}

// FUNCTION: C2 0x55B42
// WIN: 0x004557af
// Lines 279–283
void make_emperor(void) {
    black_out();
    game_state = 2;
}

// FUNCTION: C2 0x55B52
// WIN: 0x004557c9
// Lines 287–307
// NOTE: Original uses xor edx,edx then mov [...],edx for all zero-stores (shorter);
// all available Watcom versions constant-propagate to mov [...],0 (longer). Logic correct.
void init_legion(void) {
    int s;
    army_wage_level = 0;
    conscription_rate = 2;
    mercs_in_army = 0;
    total_no_of_cohorts = 0;
    total_no_of_soldiers = 0;
    total_no_of_auxillaries = 0;
    total_no_of_irregulars = 0;
    total_no_of_regulars = 0;
    current_no_of_soldiers = 0;
    current_no_of_auxillaries = 0;
    current_no_of_irregulars = 0;
    current_no_of_regulars = 0;
    needed_no_of_soldiers = 0;
    needed_no_of_auxillaries = 0;
    needed_no_of_irregulars = 0;
    needed_no_of_regulars = 0;
    s = needed_no_of_specials;
    current_no_of_specials = s;
    total_no_of_specials = s;
    extra_auxillaries = 0;
    lacking_auxillaries = 0;
    extra_irregulars = 0;
    lacking_irregulars = 0;
    extra_regulars = 0;
    lacking_regulars = 0;
    extra_specials = 0;
    lacking_specials = 0;
    average_cohort_readiness = 0;
    average_cohort_morale = 0;
    get_cohorts_in_action();
}

// FUNCTION: C2 0x55C0B
// WIN: 0x004558f1
// Lines 309–322
// NOTE: Original pushes esi+edi and uses EBX as idiv divisor; all Watcom 10.x
// use sub esp,4 stack slot for divisor and EDX/EBX for denarii ops. Logic correct.
void train_soldiers(void) {
    int mercs_cost;
    if (c2inf.peace_mode != 0) return;
    get_cohorts_in_action();
    get_current_cohort_totals();
    get_army_totals();
    set_current_cohort_totals();
    fill_cohort_centuries();
    get_morale_and_readiness();
    current_operating_cost += army_wage_level;
    mercs_cost = (mercs_in_army / 50) * mercs_cost_per_50;
    current_operating_cost += mercs_cost;
    denarii -= army_wage_level;
    denarii -= mercs_cost;
}

// FUNCTION: C2 0x55C82
// WIN: 0x00455983
// Lines 324–349
// BYTE-EXACT 2026-06-12 (was 162 b).  Two levers off the Mac PPC
// oracle: (1) no named `r` — the threshold chain reads
// army_list[temp_army].total_troops inline per compare (Mac reloads
// it every time; x86 Watcom CSEs the loads into EBP itself, which IS
// PS's register — naming it forced EDX + dropped the EBP save);
// (2) Rule 79 zero-init order active_count, readiness_sum,
// morale_sum (PS: xor ecx; xor ebx; xor edx).
void get_morale_and_readiness(void) {
    int active_count = 0;
    int readiness_sum = 0;
    int morale_sum = 0;
    for (temp_army = 1; temp_army < 26; temp_army++) {
        if (army_list[temp_army].exists == 0) continue;
        if (army_list[temp_army].type != 1) continue;
        active_count++;
        morale_sum += army_list[temp_army].morale;
        if (army_list[temp_army].total_troops < 100)
            army_list[temp_army].readiness_level = 0;
        else if (army_list[temp_army].total_troops < 250)
            army_list[temp_army].readiness_level = 1;
        else if (army_list[temp_army].total_troops < 500)
            army_list[temp_army].readiness_level = 2;
        else if (army_list[temp_army].total_troops < 1000)
            army_list[temp_army].readiness_level = 3;
        else
            army_list[temp_army].readiness_level = 4;
        readiness_sum += army_list[temp_army].readiness_level;
    }
    average_cohort_morale = 0;
    average_cohort_readiness = 0;
    if (active_count != 0) {
        average_cohort_morale = morale_sum / active_count;
        average_cohort_readiness = readiness_sum / active_count;
    }
}

// FUNCTION: C2 0x55D79
// WIN: 0x00455b9a
// Lines 351–363
// NOTE: Same pattern as init_legion — original uses `xor edx,edx` + reg stores
// for the four zero-inits (saves 14 bytes); Watcom 10.0a emits immediate-0
// stores instead. Logic correct.
void get_current_cohort_totals(void) {
    current_no_of_specials = 0;
    current_no_of_regulars = 0;
    current_no_of_irregulars = 0;
    current_no_of_auxillaries = 0;
    for (temp_army = 1; temp_army < 26; temp_army++) {
        if (army_list[temp_army].exists == 0) continue;
        if (army_list[temp_army].type != 1) continue;
        current_no_of_auxillaries += army_list[temp_army].num_auxillaries;
        current_no_of_irregulars += army_list[temp_army].num_irregulars;
        current_no_of_regulars   += army_list[temp_army].num_regulars;
        current_no_of_specials   += army_list[temp_army].num_specials;
    }
    current_no_of_soldiers = current_no_of_regulars + current_no_of_irregulars
                           + current_no_of_auxillaries + current_no_of_specials;
}

// FUNCTION: C2 0x55E1D
// WIN: 0x00455cce
// Lines 365–444
//
// Rebalances cohort counts across armies:
//   (1) consume `lacking_*` by decrementing from active armies that still
//       have units of that type,
//   (2) distribute `extra_*` onto active armies, in bursts of 1/2/4 units
//       depending on the army's cohort_size_class,
//   (3) recompute total_troops per army and zero assigned_needs,
//   (4) spread `needed_no_of_*` as reinforcement assignments across armies.
//
// The outer `count` guard (40000) is a runaway-loop safety net inherited
// from the original source; in normal play it is never reached.
void set_current_cohort_totals(void) {
    int count;
    int i;
    int n;
    int needed_spe;
    int needed_reg;
    int needed_aux;
    int needed_irr;

    if (no_of_cohorts_in_action <= 0) {
        current_no_of_soldiers = 0;
        current_no_of_auxillaries = 0;
        current_no_of_irregulars = 0;
        current_no_of_regulars = 0;
        return;
    }

    count = 0;
    temp_army = last_adjusted_cohort;

    // ── auxillaries ─────────────────────────────────────────────────────────
    while (lacking_auxillaries > 0) {
        count++;
        if (count >= 40000) break;
        if (get_next_temp_cohort(0) == 0) break;
        if (army_list[temp_army].num_auxillaries == 0) continue;
        army_list[temp_army].num_auxillaries--;
        lacking_auxillaries--;
    }
    while (extra_auxillaries > 0) {
        count++;
        if (count >= 40000) break;
        if (get_next_temp_cohort(1) == 0) break;
        if (army_list[temp_army].cohort_size_class == 0)      n = 2;
        else if (army_list[temp_army].cohort_size_class == 2) n = 4;
        else                                                  n = 1;
        for (i = 0; i < n; i++) {
            if (extra_auxillaries == 0) break;
            army_list[temp_army].num_auxillaries++;
            extra_auxillaries--;
        }
    }

    // ── irregulars ──────────────────────────────────────────────────────────
    while (lacking_irregulars > 0) {
        count++;
        if (count >= 40000) break;
        if (get_next_temp_cohort(0) == 0) break;
        if (army_list[temp_army].num_irregulars == 0) continue;
        army_list[temp_army].num_irregulars--;
        lacking_irregulars--;
    }
    while (extra_irregulars > 0) {
        count++;
        if (count >= 40000) break;
        if (get_next_temp_cohort(1) == 0) break;
        if (army_list[temp_army].cohort_size_class == 0)      n = 2;
        else if (army_list[temp_army].cohort_size_class == 2) n = 4;
        else                                                  n = 1;
        for (i = 0; i < n; i++) {
            if (extra_irregulars == 0) break;
            army_list[temp_army].num_irregulars++;
            extra_irregulars--;
        }
    }

    // ── regulars ────────────────────────────────────────────────────────────
    while (lacking_regulars > 0) {
        count++;
        if (count >= 40000) break;
        if (get_next_temp_cohort(0) == 0) break;
        if (army_list[temp_army].num_regulars == 0) continue;
        army_list[temp_army].num_regulars--;
        lacking_regulars--;
    }
    while (extra_regulars > 0) {
        count++;
        if (count >= 40000) break;
        if (get_next_temp_cohort(1) == 0) break;
        if (army_list[temp_army].cohort_size_class == 0)      n = 2;
        else if (army_list[temp_army].cohort_size_class == 2) n = 4;
        else                                                  n = 1;
        for (i = 0; i < n; i++) {
            if (extra_regulars == 0) break;
            army_list[temp_army].num_regulars++;
            extra_regulars--;
        }
    }

    // ── specials ────────────────────────────────────────────────────────────
    while (lacking_specials > 0) {
        count++;
        if (count >= 40000) break;
        if (get_next_temp_cohort(0) == 0) break;
        if (army_list[temp_army].num_specials == 0) continue;
        army_list[temp_army].num_specials--;
        lacking_specials--;
    }
    while (extra_specials > 0) {
        count++;
        if (count >= 40000) break;
        if (get_next_temp_cohort(1) == 0) break;
        if (army_list[temp_army].cohort_size_class == 0)      n = 2;
        else if (army_list[temp_army].cohort_size_class == 2) n = 4;
        else                                                  n = 1;
        for (i = 0; i < n; i++) {
            if (extra_specials == 0) break;
            army_list[temp_army].num_specials++;
            extra_specials--;
        }
    }

    last_adjusted_cohort = temp_army;

    // ── recompute total_troops per army, clear assigned_needs ──────────────────
    for (temp_army = 1; temp_army < 26; temp_army++) {
        if (army_list[temp_army].exists == 0) continue;
        if (army_list[temp_army].type != 1) continue;
        army_list[temp_army].total_troops =
              army_list[temp_army].num_auxillaries
            + army_list[temp_army].num_irregulars
            + army_list[temp_army].num_regulars
            + army_list[temp_army].num_specials;
        army_list[temp_army].assigned_needs = 0;
    }

    // ── spread the `needed_no_of_*` requirements as reinforcement tags ──────
    needed_aux = needed_no_of_auxillaries;
    needed_irr = needed_no_of_irregulars;
    needed_reg = needed_no_of_regulars;
    needed_spe = needed_no_of_specials;

    while (needed_aux-- > 0) {
        count++;
        if (count >= 40000) break;
        if (get_next_temp_cohort(1) == 0) break;
        army_list[temp_army].assigned_needs++;
    }
    while (needed_irr-- > 0) {
        count++;
        if (count >= 40000) break;
        if (get_next_temp_cohort(1) == 0) break;
        army_list[temp_army].assigned_needs++;
    }
    while (needed_reg-- > 0) {
        count++;
        if (count >= 40000) break;
        if (get_next_temp_cohort(1) == 0) break;
        army_list[temp_army].assigned_needs++;
    }
    while (needed_spe-- > 0) {
        count++;
        if (count >= 40000) break;
        if (get_next_temp_cohort(1) == 0) break;
        army_list[temp_army].assigned_needs++;
    }
}

// FUNCTION: C2 0x56322
// WIN: 0x00456551
// Lines 447–502
void fill_cohort_centuries(void) {
    int aux;
    int irr;
    int reg;
    int i;
    int spe;

    for (temp_army = 1; temp_army < 26; temp_army++) {
        if (army_list[temp_army].exists == 0) continue;
        if (army_list[temp_army].type != 1) continue;

        army_list[temp_army].num_centuries = 0;
        aux = army_list[temp_army].num_auxillaries;
        irr = army_list[temp_army].num_irregulars;
        reg = army_list[temp_army].num_regulars;
        spe = army_list[temp_army].num_specials;
        army_list[temp_army].total_troops = aux + irr + reg + spe;

        // Pass 1: re-stock existing centuries by type.
        for (i = 0; i < 14; i++) {
            if (army_list[temp_army].centuries[i].type == 1) {                       // regulars
                if (reg <= 0) {
                    army_list[temp_army].centuries[i].type = 0;
                } else if (reg >= 60) {
                    reg -= 60;
                    if (army_list[temp_army].centuries[i].damaged == 0)
                        army_list[temp_army].centuries[i].damaged = 1;
                } else {
                    army_list[temp_army].centuries[i].damaged = 0;
                    reg = 0;
                }
            } else if (army_list[temp_army].centuries[i].type == 2) {                // irregulars
                if (irr <= 0) {
                    army_list[temp_army].centuries[i].type = 0;
                } else if (irr >= 60) {
                    irr -= 60;
                    if (army_list[temp_army].centuries[i].damaged == 0)
                        army_list[temp_army].centuries[i].damaged = 1;
                } else {
                    army_list[temp_army].centuries[i].damaged = 0;
                    irr = 0;
                }
            } else if (army_list[temp_army].centuries[i].type == 3) {                // auxillaries
                if (aux <= 0) {
                    army_list[temp_army].centuries[i].type = 0;
                } else if (aux >= 60) {
                    aux -= 60;
                    if (army_list[temp_army].centuries[i].damaged == 0)
                        army_list[temp_army].centuries[i].damaged = 1;
                } else {
                    army_list[temp_army].centuries[i].damaged = 0;
                    aux = 0;
                }
            } else if (army_list[temp_army].centuries[i].type == 4) {                // specials
                if (spe <= 0) {
                    army_list[temp_army].centuries[i].type = 0;
                } else if (spe >= 60) {
                    spe -= 60;
                    if (army_list[temp_army].centuries[i].damaged == 0)
                        army_list[temp_army].centuries[i].damaged = 1;
                } else {
                    army_list[temp_army].centuries[i].damaged = 0;
                    spe = 0;
                }
            }
        }

        // Pass 2: fill empty centuries from leftovers.
        for (i = 0; i < 14; i++) {
            if (army_list[temp_army].centuries[i].type != 0) continue;
            if (reg >= 60) {
                reg -= 60;
                army_list[temp_army].centuries[i].type = 1;
                army_list[temp_army].centuries[i].damaged = 1;
            } else if (irr >= 60) {
                irr -= 60;
                army_list[temp_army].centuries[i].type = 2;
                army_list[temp_army].centuries[i].damaged = 1;
            } else if (aux >= 60) {
                aux -= 60;
                army_list[temp_army].centuries[i].type = 3;
                army_list[temp_army].centuries[i].damaged = 1;
            } else if (spe >= 60) {
                spe -= 60;
                army_list[temp_army].centuries[i].type = 4;
                army_list[temp_army].centuries[i].damaged = 1;
            } else if (reg != 0) {
                reg = 0;
                army_list[temp_army].centuries[i].type = 1;
                army_list[temp_army].centuries[i].damaged = 0;
            } else if (irr != 0) {
                irr = 0;
                army_list[temp_army].centuries[i].type = 2;
                army_list[temp_army].centuries[i].damaged = 0;
            } else if (aux != 0) {
                aux = 0;
                army_list[temp_army].centuries[i].type = 3;
                army_list[temp_army].centuries[i].damaged = 0;
            } else if (spe != 0) {
                spe = 0;
                army_list[temp_army].centuries[i].type = 4;
                army_list[temp_army].centuries[i].damaged = 0;
            }
        }

        // Pass 3: count non-empty centuries.
        for (i = 0; i < 14; i++) {
            if (army_list[temp_army].centuries[i].type != 0)
                army_list[temp_army].num_centuries++;
        }
    }
}

// FUNCTION: C2 0x5654E
// WIN: 0x00456d85
// Lines 505–545
void get_army_totals(void) {
    lacking_specials = 0;
    lacking_regulars = 0;
    lacking_irregulars = 0;
    lacking_auxillaries = 0;
    extra_specials = 0;
    extra_regulars = 0;
    extra_irregulars = 0;
    extra_auxillaries = 0;

    total_no_of_auxillaries = slave_requirements[6].current;
    total_no_of_irregulars = totalXpercent(population, conscription_rate);
    total_no_of_regulars = army_wage_level * (main_paras[1] + 1 - province_difficulty);
    total_no_of_specials = mercs_in_army;

    if (total_no_of_auxillaries < current_no_of_auxillaries) {
        lacking_auxillaries = current_no_of_auxillaries - total_no_of_auxillaries;
    } else {
        if (current_no_of_auxillaries + main_paras[2] <= total_no_of_auxillaries) extra_auxillaries = main_paras[2];
        else extra_auxillaries = total_no_of_auxillaries - current_no_of_auxillaries;
    }
    current_no_of_auxillaries = current_no_of_auxillaries - lacking_auxillaries;
    current_no_of_auxillaries = current_no_of_auxillaries + extra_auxillaries;

    if (total_no_of_irregulars < current_no_of_irregulars) {
        lacking_irregulars = current_no_of_irregulars - total_no_of_irregulars;
    } else {
        if (current_no_of_irregulars + main_paras[3] <= total_no_of_irregulars) extra_irregulars = main_paras[3];
        else extra_irregulars = total_no_of_irregulars - current_no_of_irregulars;
    }
    current_no_of_irregulars = current_no_of_irregulars - lacking_irregulars;
    current_no_of_irregulars = current_no_of_irregulars + extra_irregulars;

    if (total_no_of_regulars < current_no_of_regulars) {
        lacking_regulars = current_no_of_regulars - total_no_of_regulars;
    } else {
        if (current_no_of_regulars + main_paras[4] <= total_no_of_regulars) extra_regulars = main_paras[4];
        else extra_regulars = total_no_of_regulars - current_no_of_regulars;
    }
    current_no_of_regulars = current_no_of_regulars - lacking_regulars;
    current_no_of_regulars = current_no_of_regulars + extra_regulars;

    if (total_no_of_specials < current_no_of_specials) {
        lacking_specials = current_no_of_specials - total_no_of_specials;
    } else {
        if (current_no_of_specials + 1000 <= total_no_of_specials) extra_specials = 1000;
        else extra_specials = total_no_of_specials - current_no_of_specials;
    }
    current_no_of_specials = current_no_of_specials - lacking_specials;
    current_no_of_specials = current_no_of_specials + extra_specials;

    needed_no_of_auxillaries = total_no_of_auxillaries - current_no_of_auxillaries;
    needed_no_of_irregulars = total_no_of_irregulars - current_no_of_irregulars;
    needed_no_of_regulars = total_no_of_regulars - current_no_of_regulars;
    needed_no_of_specials = total_no_of_specials - current_no_of_specials;

    total_no_of_soldiers = total_no_of_regulars + total_no_of_irregulars + total_no_of_auxillaries + total_no_of_specials;
    needed_no_of_soldiers = needed_no_of_regulars + needed_no_of_irregulars + needed_no_of_auxillaries + needed_no_of_specials;
    current_no_of_soldiers = current_no_of_regulars + current_no_of_irregulars + current_no_of_auxillaries + current_no_of_specials;
}

// FUNCTION: C2 0x567FC
// WIN: 0x00457094
// Lines 548–568
// ----------------------------------------------------------------------------
// Speculative version of `set_current_cohort_totals`: recomputes the per-type
// totals from province parameters, calls `get_current_cohort_totals` for the
// current snapshot, then derives `needed_no_of_*` = total - current,
// clamping negatives to zero (and pinning total = current in that case).
// Finally computes the summary `total_no_of_soldiers` / `needed_no_of_soldiers`.
//
// NOTE: tail-call to a far address inside `adjust_proserity_criteria`'s
// epilogue at 0x457a8 (shared `pop ebp/edi/esi/edx/ecx/ebx ret`). The
// compiler emits its own per-function epilogue instead; diff is cosmetic.
void predict_army_totals(void) {
    get_current_cohort_totals();

    total_no_of_auxillaries = slave_requirements[6].current;
    total_no_of_irregulars  = totalXpercent(population, conscription_rate);
    total_no_of_regulars    = army_wage_level * (main_paras[1] + 1 - province_difficulty);
    total_no_of_specials    = mercs_in_army;

    needed_no_of_auxillaries = total_no_of_auxillaries - current_no_of_auxillaries;
    needed_no_of_irregulars  = total_no_of_irregulars  - current_no_of_irregulars;
    needed_no_of_regulars    = total_no_of_regulars    - current_no_of_regulars;
    needed_no_of_specials    = total_no_of_specials    - current_no_of_specials;

    if (needed_no_of_auxillaries < 0) {
        needed_no_of_auxillaries = 0;
        total_no_of_auxillaries  = current_no_of_auxillaries;
    }
    if (needed_no_of_irregulars < 0) {
        needed_no_of_irregulars = 0;
        total_no_of_irregulars  = current_no_of_irregulars;
    }
    if (needed_no_of_regulars < 0) {
        needed_no_of_regulars = 0;
        total_no_of_regulars  = current_no_of_regulars;
    }
    if (needed_no_of_specials < 0) {
        needed_no_of_specials = 0;
        total_no_of_specials  = current_no_of_specials;
    }

    total_no_of_soldiers  = total_no_of_regulars + total_no_of_irregulars
                          + total_no_of_auxillaries + total_no_of_specials;
    needed_no_of_soldiers = needed_no_of_regulars + needed_no_of_irregulars
                          + needed_no_of_auxillaries + needed_no_of_specials;
}

// FUNCTION: C2 0x56943
// WIN: 0x004571e5
// Lines 573–584
// ----------------------------------------------------------------------------
// One-shot initialisation of the slave economy + zeroing of the
// slave_requirements table. Called once per new province.
//
// `init_salary` is a per-difficulty welfare/slave record table.
void init_slaves(void) {
    slave_welfare_bill = init_salary[province_difficulty].welfare_bill;
    slaves             = init_salary[province_difficulty].slaves;

    slave_requirements[0].max     = 0x14;
    slave_requirements[1].current = 0x0C;
    slave_requirements[2].current = 4;
    slave_requirements[3].current = 4;
    slave_requirements[4].current = 0;
    slave_requirements[5].current = 0;
    slave_requirements[6].current = 0;
}

// FUNCTION: C2 0x569A1
// WIN: 0x00457258
// Lines 586–627
// ----------------------------------------------------------------------------
// Runs one slave-economy tick. Computes a "welfare quality" index from the
// province's welfare bill, then picks a (growth %, mortality %) pair from a
// 16-way range table and updates `slaves` / `slave_population_change`.
//
// NOTE: the "bored happiness" band (95..=105) short-circuits with
// `slave_population_change = 0` and a tail-jmp to `0x457a8` (shared epilogue).
// All other bands also tail-jmp after updating `slaves` + `change`; our
// emit will be per-function epilogues instead, the cascade diff is cosmetic.
//
void slave_welfare(void) {
    int orig_slaves = slaves;
    int standard    = main_paras[0] - province_difficulty / 3;
    int quality     = valueDIVtotal(standard * slave_welfare_bill, orig_slaves);
    int growth_pct;
    int mortality_pct;
    int growth_amt;
    int mortality_amt;

    if      (quality <   10) { mortality_pct = 50; growth_pct =   1; }
    else if (quality <   25) { mortality_pct = 30; growth_pct =   2; }
    else if (quality <   50) { mortality_pct = 20; growth_pct =   3; }
    else if (quality <   75) { mortality_pct = 15; growth_pct =   4; }
    else if (quality <   95) { mortality_pct =  9; growth_pct =   5; }
    else if (quality > 2000) { mortality_pct =    2; growth_pct = 200; }
    else if (quality > 1500) { mortality_pct =    2; growth_pct = 150; }
    else if (quality > 1000) { mortality_pct =    2; growth_pct = 100; }
    else if (quality >  750) { mortality_pct =    2; growth_pct =  60; }
    else if (quality >  500) { mortality_pct =    2; growth_pct =  40; }
    else if (quality >  300) { mortality_pct =    2; growth_pct =  20; }
    else if (quality >  200) { /* mortality stays 3 (==ebx from idiv) */
                               mortality_pct =    3; growth_pct =  15; }
    else if (quality >  150) { mortality_pct =    4; growth_pct =  11; }
    else if (quality >  125) { mortality_pct =    5; growth_pct =   9; }
    else if (quality >  105) { mortality_pct =    6; growth_pct =   8; }
    else {
        // 95..=105: sustainable equilibrium, no change
        slave_population_change = 0;
        return;
    }

    // Both percent calls read the *original* `slaves` in the asm (the two
    // writes below only happen after both calls), so stage the computation
    // via locals rather than letting the second call see an updated value.
    growth_amt    = totalXpercent(slaves, growth_pct);
    mortality_amt = totalXpercent(slaves, mortality_pct);
    growth_amt++;                              /* PS: inc esi */
    slaves += growth_amt;                      /* RMW pattern */
    slaves -= mortality_amt;
    if (slaves < 1) slaves = 1;
    slave_population_change = slaves - orig_slaves;
}

// FUNCTION: C2 0x56B5A
// WIN: 0x004574e1
// Lines 629–633
void slave_costs(void) {
    int bill = slave_welfare_bill;
    denarii -= bill;
    current_operating_cost += bill;
}

// FUNCTION: C2 0x56B6C
// WIN: 0x00457507
// Lines 635–646
// ----------------------------------------------------------------------------
// Runs the slave-welfare simulation forward one tick to get a short-term
// estimate, then 99 more ticks to get a long-term one, finally restoring
// the real `slaves` / `slave_population_change` state so this function has
// no net side effects.
void slave_estimate(void) {
    int saved_slaves = slaves;
    int saved_change = slave_population_change;
    int i;

    slave_welfare();
    slave_population_estimate = slaves;

    for (i = 0; i < 100; i++) {
        slave_welfare();
    }
    slave_population_final_estimate = slaves;

    slaves = saved_slaves;
    slave_population_change = saved_change;
}

// FUNCTION: C2 0x56BB5
// WIN: 0x00457571
// Lines 650–666
// ----------------------------------------------------------------------------
// Walks the 7 priority buckets in `slave_requirements` and distributes the
// province's `slaves` pool across them. Each bucket's `current` field gets
// set to min(remaining pool, bucket.max). Any unspent slaves go into
// record 7 (the overflow bucket).
//
// Record 0's `current` is reset from `slave_requirements[0].max` at the
// top of the function so the allocation starts from a clean state.
//
// NOTE: Watcom 10.0a -os inverts the register roles (we get `eax = pool,
// edx = scratch` where PS.EXE has `edx = pool, eax = scratch`) and flips
// the `pool < quota` branch polarity to `jge` fall-through. Logic is
// identical; byte diff is cosmetic.
void adjust_slave_usage(void) {
    int pool = slaves;
    int i;

    slave_requirements[0].current = slave_requirements[0].max;

    for (i = 0; i < 7; i++) {
        if (pool >= slave_requirements[i].current) {
            pool -= slave_requirements[i].current;
        } else {
            slave_requirements[i].current = pool;
            pool = 0;
        }
    }
    slave_requirements[i].current = pool;              /* i == 7, indexed store */
}

// FUNCTION: C2 0x56BF6
// WIN: 0x004575f9
// Lines 699–771
// ----------------------------------------------------------------------------
// Draws a random event for this turn from a [c2inf.skill_level][64] lookup table,
// then executes the event logic:
//
//   0  — "good fortune" check: possibly trigger robbery based on
//         denarii/temple ratio vs a random threshold.
//   2  — revolt warning / quarter-denarii penalty (no temples guard).
//   3  — temple-protected robbery: percentage of denarii stolen based on
//         weighted temple coverage vs weighted robbery exposure.
//   4  — plague: get_rand_max(plague_running_count) -> plague_accident.
//
// NOTE: the `cmp eax, 0x4e20` before `cmp eax, 0x2710` in the good-fortune
// path is dead (no conditional jump follows the first cmp; the second cmp
// immediately overwrites the flags).  It is the redundant
// `if (denarii_per_temple >= 20000) bonus = 20;` line: bonus=20 duplicates the
// >=10000 arm so Watcom DCEs the store+branch but leaves the cmp behind.
//
// BYTE-EXACT.  Three load-bearing shape facts, all confirmed against PS's -d1
// marks (L758 temple_w, L759 rob_w, L760 valueDIVtotal) and the Mac decompile:
//   1. temple_w-FIRST: event-3 computes temple_w (L758) before rob_w (L759).
//   2. ONE reused int (temple_score) holds BOTH the event-0 temple ratio and
//      the event-3 robbery percentage — PS's iVar7 reuse.  Sharing the name
//      seats both in EBX; two separate locals split the conflict and the
//      percentage lands in ECX (the dead event hole), diverging.
//   3. The rob_w divisor is the global `robbery_count` INLINED, not a
//      `rob_count` local.  The inline seats robbery_count in ECX, freeing EBX
//      for temple_w; a named rob_count steals EBX and swaps the pair (14b).
void random_event(void) {
    int event;
    int temple_score;   /* also reused for the event-3 robbery % (PS iVar7) */
    int denarii_per_temple;
    int bonus;
    int temple_w;
    int rob_w;

    // Draw event from the skill-level event row.
    event = (unsigned char)events[c2inf.skill_level][rand128 & 63];

    plague_accident = 999999;
    revolt_accident = 999999;

    if (event == 0) {
        // ── event 0: good fortune / robbery check ───────────────────────────
        if (denarii < 1000) return;
        if (population < 100) return;
        temple_score = large_temples_count * 4
                     + med_temples_count   * 3
                     + small_temples_count;
        if (temple_score == 0) temple_score = 1;
        denarii_per_temple = denarii / temple_score;
        if (denarii_per_temple >= 20000) bonus = 20;
        if      (denarii_per_temple >= 10000) bonus =  20;
        else if (denarii_per_temple >=  4000) bonus =  14;
        else if (denarii_per_temple >=  2000) bonus =   8;
        else if (denarii_per_temple >=  1000) bonus =   4;
        else if (denarii_per_temple >=   500) bonus =   0;
        else                                  bonus =  -4;
        if (c2inf.skill_level + bonus <= rand128) return;
        robbery_count = 1;
        event = 3;
    }

    // ── event 4: plague ───────────────────────────────────────────────────
    if (event == 4) {
        if (plague_running_count < 4) return;
        plague_accident = get_rand_max(plague_running_count);
    }

    // ── event 2: revolt warning / fine ───────────────────────────────────
    if (event == 2) {
        if (denarii < 1000)   return;
        if (population < 100) return;
        if (temples_count == 0) {
            if (!warned_of_robbery) {
                warned_of_robbery = 1;
                put_message(88, 0, 14);
            } else {
                put_message(89, 0, 16);
                stolen_denarii = denarii / 4;  // sar-shl-sbb idiom
                denarii -= stolen_denarii;
            }
        }
        // temples_count != 0: fall through to event==3 check below
    }

    // ── event 3: temple-protected robbery ─────────────────────────────────
    // Reached directly (event==3) or via fall-through from event-2 when temples
    // are present (event still 2 → this block is skipped, which is correct:
    // Ghidra shows `if (uVar2 != 3) return` before the robbery code).
    if (event != 3) return;
    if (denarii < 1000)   return;
    if (population < 100) return;
    if (temples_count == 0) {
        if (!warned_of_robbery) {
            warned_of_robbery = 1;
            put_message(88, 0, 14);
        } else {
            put_message(89, 0, 16);
            stolen_denarii = denarii / 4;  // sar-shl-sbb idiom
            denarii -= stolen_denarii;
        }
        return;
    }
    if (robbery_count == 0) return;
    temple_w = large_temples_count * 4
             + med_temples_count   * 2
             + small_temples_count;
    rob_w = (large_robbery_count * 4
           + med_robbery_count   * 2
           + small_robbery_count) / robbery_count;
    temple_score = valueDIVtotal(rob_w, temple_w);
    if (temple_score < 10)  temple_score = 10;
    if (temple_score > 80)  temple_score = 80;
    stolen_denarii = totalXpercent(denarii / 4, temple_score);
    if (stolen_denarii <= 0) return;               // Rule 4 (enables `test eax,eax`)
    denarii -= stolen_denarii;
    put_message(86, 0, 16);
}

// FUNCTION: C2 0x56EB8
// WIN: 0x00457984
// Lines 776–781
void pay_salary(void) {
    int sal = players_salary;
    current_operating_cost += sal;
    players_denarii += sal;
    denarii -= sal;
}

// FUNCTION: C2 0x56ED0
// WIN: 0x004579b5
// Lines 783–793
void get_population_growth_factor(void) {
    pop_growth_future += pop_tax_to_growth_data[pop_tax_rate];
    pop_growth_future += employment_to_pop_growth_factor[employment_rate / 5];
    pop_growth_future -= province_difficulty / 3;
    if (pop_growth_future >  36) pop_growth_future =  36;
    if (pop_growth_future < -36) pop_growth_future = -36;
    if (tutorial_mode != 0) pop_growth_future = 36;
    pop_growth_factor = pop_growth_future / 8;          // sar-shl-sbb idiom
}

// FUNCTION: C2 0x56F74
// WIN: 0x00457a5d
// Lines 795–802
void get_industry_growth_factor(void) {
    ind_growth_future += ind_tax_to_growth_data[ind_tax_rate];
    if (ind_growth_future >  36) ind_growth_future =  36;
    if (ind_growth_future < -36) ind_growth_future = -36;
    if (business_count == 0) ind_growth_future = business_count;
    ind_growth_factor = ind_growth_future / 8;    // sar-shl-sbb idiom (signed /8)
}

// FUNCTION: C2 0x56FDD
// WIN: 0x00457ad2
// Lines 804–823
// NOTE: recomp is 6 bytes short. PS.EXE emits a 2-byte short `je` for the
// tutorial_mode tail and uses 5 callee-saved registers (ebx/ecx/edx/esi/edi);
// Watcom 10.0a -os only allocates 3-4, leaving fewer push/pop bytes and
// forcing a 6-byte near `je`. Cosmetic; logic is identical.
void get_insurrection_factor(void) {
    insurrection_future += tax_to_revolt_data[pop_tax_rate];
    insurrection_future += (province_difficulty - 4) / 2;
    if (province_difficulty <= 2) insurrection_future -= 1;
    insurrection_future += conscription_to_revolt_data[conscription_rate / 2];
    if      (insurrection_future >= 100) { insurrection_factor = 10; insurrection_future -= 100; }
    else if (insurrection_future >=  90) { insurrection_factor =  9; insurrection_future -=  90; }
    else if (insurrection_future >=  80) { insurrection_factor =  8; insurrection_future -=  80; }
    else if (insurrection_future >=  70) { insurrection_factor =  7; insurrection_future -=  70; }
    else if (insurrection_future >=  60) { insurrection_factor =  6; insurrection_future -=  60; }
    else if (insurrection_future >=  50) { insurrection_factor =  5; insurrection_future -=  50; }
    else if (insurrection_future >=  40) { insurrection_factor =  4; insurrection_future -=  40; }
    else if (insurrection_future >=  30) { insurrection_factor =  3; insurrection_future -=  30; }
    else if (insurrection_future >   20) { insurrection_factor =  2; insurrection_future -=  20; }
    else if (insurrection_future <  -10) { insurrection_factor = -2; insurrection_future +=  10; }
    else                                 { insurrection_factor =  0; }
    if (tutorial_mode != 0) insurrection_factor = -2;
}

// FUNCTION: C2 0x5717D
// WIN: 0x00457cad
// Lines 827–840
void year_end_accounts(void) {
    collect_pop_tax();
    collect_ind_tax();
    account_construction_cost = current_construction_cost;
    account_operating_cost    = current_operating_cost + stolen_denarii;
    denarii      -= tribute;
    account_tribute = tribute;
    current_construction_cost = 0;
    current_operating_cost    = 0;
    stolen_denarii            = 0;
    account_total = (account_pop_tax + account_ind_tax)
                  - account_construction_cost
                  - account_operating_cost
                  - account_tribute;
    if (account_total > 0) months_to_game_over = 0;
}

// FUNCTION: C2 0x57200
// WIN: 0x00457d4d
// Lines 842–850
void collect_pop_tax(void) {
    if (pop_tax_counts != 0) {
        account_pop_tax       = pop_tax_running_total / pop_tax_counts;  // two-step
        account_pop_tax      /= 100;
        denarii              += account_pop_tax;
        pop_tax_running_total = 0;
        pop_tax_counts        = 0;
    }
}

// FUNCTION: C2 0x5724D
// WIN: 0x00457dac
// Lines 852–860
void collect_ind_tax(void) {
    if (ind_tax_counts != 0) {
        account_ind_tax       = ind_tax_running_total / ind_tax_counts;  // two-step
        account_ind_tax      /= 100;
        denarii              += account_ind_tax;
        ind_tax_running_total = 0;
        ind_tax_counts        = 0;
    }
}

// FUNCTION: C2 0x5729A
// WIN: 0x00457e0b
// Lines 862–878
// NOTE: operating_cost is accumulated via 5 separate assignments so the
// compiler generates the same incremental store pattern as the original.
void get_estimates(void) {
    int months_left;
    get_pop_tax_estimate();
    get_ind_tax_estimate();
    estimate_construction_cost  = current_construction_cost;
    months_left = 12 - month;
    estimate_operating_cost     = current_operating_cost + stolen_denarii;
    estimate_operating_cost    += slave_welfare_bill * months_left;
    estimate_operating_cost    += army_wage_level    * months_left;
    estimate_operating_cost    += (mercs_in_army / 50) * mercs_cost_per_50 * months_left;
    estimate_operating_cost    += players_salary     * months_left;
    estimate_tribute            = tribute;
    estimate_total              = (estimate_pop_tax + estimate_ind_tax)
                                - estimate_construction_cost
                                - estimate_operating_cost
                                - tribute;
}

// FUNCTION: C2 0x57356
// WIN: 0x00457ec2
// Lines 882–896
// Projects pop tax for remaining months and divides by 12 to get monthly avg.
void get_pop_tax_estimate(void) {
    int projected = 0;
    if (pop_tax_counts < 12) {
        int months_left = 12 - pop_tax_counts;
        projected = totalXpercent(pop_tax_last_count * income_multiple, pop_tax_rate);
        projected *= months_left;
    }
    projected += pop_tax_running_total;
    estimate_pop_tax  = projected / 12;            // two-step: PS stores intermediate
    estimate_pop_tax /= 100;
}

// FUNCTION: C2 0x573B5
// WIN: 0x00457f44
// Lines 898–912
void get_ind_tax_estimate(void) {
    int projected = 0;
    if (ind_tax_counts < 12) {
        int months_left = 12 - ind_tax_counts;
        projected = totalXpercent(ind_tax_last_count * income_multiple, ind_tax_rate);
        projected *= months_left;
    }
    projected += ind_tax_running_total;
    estimate_ind_tax  = projected / 12;            // two-step: PS stores intermediate
    estimate_ind_tax /= 100;
}

// FUNCTION: C2 0x57414
// WIN: 0x00457fc6
// Lines 915–925
// Computes average pop tax per person in denarii and asses (100 asses = 1 denarius).
void get_average_pop_tax(void) {
    int per_person;
    int denarii_part;
    if (population == 0) {
        average_pop_tax_asses    = 0;
        average_pop_tax_denariis = 0;
        return;
    }
    per_person       = totalXpercent(pop_tax_last_count * income_multiple, pop_tax_rate)
                       / population;
    denarii_part              = per_person / 100;
    average_pop_tax_denariis  = denarii_part;
    average_pop_tax_asses     = per_person % 100;
}

// FUNCTION: C2 0x5747E
// WIN: 0x00458046
// Lines 927–937
void get_average_ind_tax(void) {
    int per_business;
    int denarii_part;
    if (business_count == 0) {
        average_ind_tax_asses    = 0;
        average_ind_tax_denariis = 0;
        return;
    }
    per_business     = totalXpercent(ind_tax_last_count * income_multiple, ind_tax_rate)
                       / business_count;
    denarii_part              = per_business / 100;
    average_ind_tax_denariis  = denarii_part;
    average_ind_tax_asses     = per_business % 100;
}

// FUNCTION: C2 0x574E8
// WIN: 0x004580c6
// Lines 939–1041
// Updates imperial tribute demand, processes requests and reviews.
void get_new_tribute(void) {
    int delta;
    int cp;
    int amount;
    last_tribute = tribute;

    delta = rand128 & 7;
    delta -= 3;
    delta -= c2inf.skill_level;
    if      (imperial_favour <  25) delta += 2;
    else if (imperial_favour <  70) delta += 1;
    else if (imperial_favour > 175) delta -= 2;
    else if (imperial_favour > 120) delta -= 1;

    if (population < 50) delta = 0;
    imperial_favour += delta;
    if (imperial_favour <   0) imperial_favour =   0;
    if (imperial_favour > 200) imperial_favour = 200;

    if (player_rank >= 10) {                     // Rule 4
        imperial_favour  = 200;
        tribute          =   0;
        imperial_request = 100;
        imperial_review  = 100;
        return;
    }

    imperial_request -= 1; if (imperial_request <= 0) {
        if (c2inf.peace_mode != 0) { imperial_request = 100; return; }
        if (max_population < 2000) { imperial_request = 2;
        } else if (imperial_request == 0) {
                imperial_req_goods  = province_industries[rand128 & 3].kind;
                amount = c2inf.skill_level + 1 + completed_provinces / 2; amount += years_elapsed_in_region / 10; amount += rand128 & 1; imperial_req_amount = amount;
                put_message(135, 0, 10);
            } else if (imperial_request == -1) { put_message(136, 0, 11);
            } else if (imperial_request == -2) { put_message(137, 0, 14);
            } else {
                put_message(138, 0, 13);
            }
    }

    imperial_review -= 1; if (imperial_review <= 0) {
        imperial_review = (rand8 & 3) + 2;
        tribute = (220 - imperial_favour) / 2;
        if      (rolling_profit >=  4000) moving_tribute += tribute_adjust[0];
        else if (rolling_profit >=  2000) moving_tribute += tribute_adjust[1];
        else if (rolling_profit <= -4000) moving_tribute += tribute_adjust[2];
        else if (rolling_profit <= -2000) moving_tribute += tribute_adjust[3];
        if      (denarii >= 40000) moving_tribute += tribute_adjust[4];
        else if (denarii >= 20000) moving_tribute += tribute_adjust[5];
        else if (denarii <  1000) moving_tribute += tribute_adjust[6];
        if (moving_tribute <    0) moving_tribute =    0;
        if (moving_tribute > 2000) moving_tribute = 2000;
        tribute += moving_tribute;
        if (tribute <    0) tribute =    0;
        if (tribute > 2000) tribute = 2000;
        if (last_tribute > tribute) {
            if      (rolling_profit <= -4000) put_message(143, 0, 11);
            else if (denarii        <  1000) put_message(142, 0, 11);
            else if (imperial_favour <   80) put_message(124, 0, 11);
            else                             put_message(123, 0, 11);
        } else if (last_tribute < tribute) {
            if      (denarii >= 50000)        put_message(141, 0, 14);
            else if (rolling_profit >= 4000) put_message(140, 0, 14);
            else if (imperial_favour > 130)  put_message(122, 0, 14);
            else                             put_message(121, 0, 14);
        }
    }

    imperial_tax -= 1; if (imperial_tax <= 0) {
        imperial_tax = main_paras[5] + (rand8 & 3); cp = completed_provinces;
        /* tax_rates is laid out as int[3][20]: row 0 = greedy band,
           row 1 = 5-citizen band, row 2 = poor band. */
        if (players_denarii >= tax_triggers[0]) {
            last_imperial_tax_percent = tax_rates[cp];
            last_imperial_tax_amount = totalXpercent(players_denarii, last_imperial_tax_percent);
            total_imperial_taxes += last_imperial_tax_amount;
            put_message(146, 0, 14);
        } else if (players_denarii >= tax_triggers[1]) {
            last_imperial_tax_percent = tax_rates[20 + cp];
            last_imperial_tax_amount = totalXpercent(players_denarii, last_imperial_tax_percent);
            total_imperial_taxes += last_imperial_tax_amount;
            put_message(145, 0, 14);
        } else if (players_denarii >= tax_triggers[2]) {
            last_imperial_tax_percent = tax_rates[40 + cp];
            last_imperial_tax_amount = totalXpercent(players_denarii, last_imperial_tax_percent);
            total_imperial_taxes += last_imperial_tax_amount;
            put_message(144, 0, 14);
        }
    }
}

// FUNCTION: C2 0x57958
// WIN: 0x004586ae
// Lines 1044–1058
void init_tribute(void) {
    imperial_favour         = 110;
    tribute                 = 45;
    moving_tribute          = 0;
    last_tribute            = 0;
    total_amount_of_bribes  = 0;
    total_no_of_bribes      = 0;
    imperial_gift_level     = 0;
    av_imperial_gift_level  = 0;
    imperial_tax            = 1;
    last_imperial_tax_amount  = 0;
    last_imperial_tax_percent = 0;
    total_imperial_taxes      = 0;
}

// FUNCTION: C2 0x579B1
// WIN: 0x0045873d
// Lines 1062–1091
void get_temple_tip(int param_1) {
    if (param_1 == 0) {
        if (empire_rating_pop_limit != 0) { current_temple_tip = 1; play_speech(31); return; }
        if (imperial_favour < 80)         { current_temple_tip = 2; play_speech(32); return; }
        if (no_of_empire_connections == 0){ current_temple_tip = 3; play_speech(33); return; }
                                            current_temple_tip = 4; play_speech(34); return;
    }
    if (param_1 == 1) {
        if (peace_rating_pop_limit != 0)  { current_temple_tip = 5; play_speech(35); return; }
                                            current_temple_tip = 6; play_speech(36); return;
    }
    if (param_1 == 2) {
        if (prosperity_rating_pop_limit != 0) { current_temple_tip =  9; play_speech(37); return; }
        if (rolling_profit < 0)               { current_temple_tip = 10; play_speech(38); return; }
        if (current_gdp < 10)                 { current_temple_tip = 11; play_speech(39); return; }
                                                current_temple_tip = 12; play_speech(40); return;
    }
    // param_1 == 3: culture
    if (culture_rating_pop_limit != 0) { current_temple_tip = 13; play_speech(41); return; }
    if (entertainment_level <= religion_level && entertainment_level <= utility_level)
                                       { current_temple_tip = 14; play_speech(42); return; }
    if (religion_level <= entertainment_level && religion_level <= utility_level)
                                       { current_temple_tip = 15; play_speech(43); return; }
                                         current_temple_tip = 16; play_speech(44); return;
}
