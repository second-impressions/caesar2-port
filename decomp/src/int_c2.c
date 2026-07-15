// D:\C2\CODE\int_c2.c

#include "c2_data.h"
#include "c2_types.h"

/* ── TU-owned file-scope variables (PS.EXE _BSS, original declaration
   order).  Recovered so the functional rebuild (`c2 rebuild`) links
   self-sustained -- no auto-stubbed storage.  Extern decls: c2_data.h. */
int age_count;

/* ---------------------------------------------------------------------
 * Implicit-int callees made VISIBLE (NOT the original PS source shape).
 *
 * PS's .c did not declare these helpers: the calls below were K&R
 * implicit-int, so wcc386 assumed `int f()`.  Declaring them `extern
 * int f()` here is BYTE-NEUTRAL -- identical codegen to the implicit
 * declaration the compiler already synthesised -- and exists only to
 * surface the real cross-TU contract.  The real definitions return a
 * narrower type (noted per line); the caller intentionally reads EAX
 * as int, exactly as PS.EXE does.  Do NOT "correct" these to the real
 * return type -- a typed (char / enum) decl CHANGES the bytes.
 * ------------------------------------------------------------------- */
extern int get_heading();  /* really heading_t (enum, int-wide) -- common.c */


int city_test_for_road(int x, int y, int map_ref, signed char world_dir);


extern void fill_warehouses_with(int cell_x, int cell_y, int kind,
                                 int cohort_class, int flag);
// FUNCTION: C2 0x45EB5
// WIN: 0x004040b0
// Lines 170–185
//
// Per-tick AI dispatch for all 201 citizen slots.  Bumps the global
// `age_count` (mod 0x40), clamps `no_of_rioters` / `no_of_barbarians`
// to 0/1, and for each existing citizen either calls the type-
// specific handler from `citizen_intelligences[]` or removes it if
// the type has gone out of bounds (type <= 0 or type >= 8).

void citizen_intelligence(void)
{
    age_count++;
    if (age_count >= 0x40) age_count = 0;
    no_of_rioters    = (no_of_rioters    > 1);
    no_of_barbarians = (no_of_barbarians > 1);
    no_of_citizens = 0;
    for (citizen_no = 0; citizen_no < 0xc9; citizen_no++) {
        if (citizen_list[citizen_no].exists != 0) {
            no_of_citizens++;
            if (citizen_list[citizen_no].type <= 0
             || citizen_list[citizen_no].type >= 8)
                remove_citizen(citizen_no);
            else
                citizen_intelligences[citizen_list[citizen_no].type]();
        }
    }
}

// FUNCTION: C2 0x45F5F
// WIN: 0x004041f9
// Lines 187–199
//
// Per-tick AI dispatch for all 26 army slots.  For each existing
// army, zero its per-tick scratch fields (+0x36 / +0x38), bump
// `no_of_armies`, and either call the type-specific handler from
// `army_intelligences[]` or remove the army outright when its type
// has gone out of bounds (type <= 0 or type >= 9).
//
// Returns early without scanning if `c2inf.peace_mode` (combat-paused
// flag) is set.
void army_intelligence(void)
{
    no_of_armies = 0;
    if (c2inf.peace_mode != 0)
        return;
    for (army_no = 0; army_no < 26; army_no++) {
        if (army_list[army_no].exists != 0) {
            no_of_armies++;
            army_list[army_no].map_x = army_list[army_no].map_y = 0;
            if (army_list[army_no].type <= 0
             || army_list[army_no].type >= 9)
                remove_army(army_no);
            else
                army_intelligences[army_list[army_no].type]();
        }
    }
}

// FUNCTION: C2 0x45FE2
// WIN: 0x00404338
//
// Empty citizen-intelligence slot for the null type.
void i00_null(void)
{
}

/* ----------------------------------------------------------------
 *  i##_*_man family — per-citizen-type "intelligence" tick.
 *
 *  All share the same body:
 *    citizen_states[citizen_list[citizen_no].state_idx]();   // dispatch
 *    get_movement_image(IMG);                                // sprite
 *    if (!age_count) {                                       // 1 tick
 *        if (++citizen_list[citizen_no].state_timer >= LIMIT)
 *            citizen_list[citizen_no].state_idx = 2;         // expired
 *    }
 *  i03 + i07 also raise emergency mood and bump a global counter.
 *  i07 picks rioter_image when the active state is 12.
 * ---------------------------------------------------------------- */

// FUNCTION: C2 0x45FE3
// WIN: 0x00404343
// Lines 207–212
//
// Tax-collector tick: sprite base 0x36, 18-tick lifetime.
void i01_tax_man(void)
{
    citizen_states[citizen_list[citizen_no].state_idx]();
    get_movement_image(0x36);
    if (!age_count)
        if (++citizen_list[citizen_no].state_timer >= 0x12)
            citizen_list[citizen_no].state_idx = 2;
}

// FUNCTION: C2 0x46038
// WIN: 0x004043d8
// Lines 214–219
//
// Market-trader tick: sprite base 0x1B, 30-tick lifetime.
void i02_market_man(void)
{
    citizen_states[citizen_list[citizen_no].state_idx]();
    get_movement_image(0x1B);
    if (!age_count)
        if (++citizen_list[citizen_no].state_timer >= 0x1E)
            citizen_list[citizen_no].state_idx = 2;
}

// FUNCTION: C2 0x4608D
// WIN: 0x0040446d
// Lines 221–229
//
// Barbarian citizen tick: sprite base 0xA6, 72-tick lifetime, raises
// emergency_mood and flags `no_of_barbarians`.
void i03_barbarian_man(void)
{
    emergency_mood    = 2;
    no_of_barbarians  = 2;
    citizen_states[citizen_list[citizen_no].state_idx]();
    get_movement_image(0xA6);
    if (!age_count)
        if (++citizen_list[citizen_no].state_timer >= 0x48)
            citizen_list[citizen_no].state_idx = 2;
}

// FUNCTION: C2 0x460F3
// WIN: 0x00404519
// Lines 231–236
//
// Centurian (mounted patrol) tick: sprite base 0x6E, 35-tick lifetime.
void i04_centurian_man(void)
{
    citizen_states[citizen_list[citizen_no].state_idx]();
    get_movement_image(0x6E);
    if (!age_count)
        if (++citizen_list[citizen_no].state_timer >= 0x23)
            citizen_list[citizen_no].state_idx = 2;
}

// FUNCTION: C2 0x46148
// WIN: 0x004045ae
// Lines 238–243
//
// Vigile (firefighter / patrolman) tick: sprite base 0x51, 20-tick
// lifetime.
void i05_vigile_man(void)
{
    citizen_states[citizen_list[citizen_no].state_idx]();
    get_movement_image(0x51);
    if (!age_count)
        if (++citizen_list[citizen_no].state_timer >= 0x14)
            citizen_list[citizen_no].state_idx = 2;
}

// FUNCTION: C2 0x4619D
// WIN: 0x00404643
// Lines 245–250
//
// Businessman tick: sprite base 0, 30-tick lifetime.
void i06_business_man(void)
{
    citizen_states[citizen_list[citizen_no].state_idx]();
    get_movement_image(0);
    if (!age_count)
        if (++citizen_list[citizen_no].state_timer >= 0x1E)
            citizen_list[citizen_no].state_idx = 2;
}

// FUNCTION: C2 0x461EF
// WIN: 0x004046d8
// Lines 252–260
//
// Rioter tick: raises emergency_mood and flags `no_of_rioters`.
// In state 12 (in-riot) uses normal movement sprite 0, otherwise
// uses the rioter-mob sprite at base 0x89.  20-tick lifetime.
void i07_rioter_man(void)
{
    emergency_mood = 2;
    no_of_rioters  = 2;
    citizen_states[citizen_list[citizen_no].state_idx]();
    if (citizen_list[citizen_no].state_idx == 12) get_movement_image(0);
    else                                          get_rioter_image(0x89);
    if (!age_count)
        if (++citizen_list[citizen_no].state_timer >= 0x14)
            citizen_list[citizen_no].state_idx = 2;
}

// FUNCTION: C2 0x46273
// WIN: 0x004047b5
//
// Empty army-intelligence slot for the null type.
void a00_null(void)
{
}

// FUNCTION: C2 0x46274
// WIN: 0x004047c0
// Lines 264–279
//
// Cohort-army intelligence tick: refresh sprite, dispatch the
// per-state handler, and tick the morale / target timers.  On a
// road or settlement tile (terrain & 4) reset morale_timer to 0x30
// and target_timer to 0x320; otherwise decay morale_timer by 2 when
// a target is queued or by 1 otherwise.
void a01_cohort(void)
{
    get_cohort_image();
    army_states[army_list[army_no].state_idx]();
    if ((*(struct region_cell *)((unsigned char *)region_map + (army_list[army_no].map_ref))).terrain & 4) {
        army_list[army_no].morale_timer = 0x30;
        army_list[army_no].target_timer = 0x320;
    } else if (army_list[army_no].morale_timer) {
        if (army_list[army_no].target_flag) army_list[army_no].morale_timer -= 2;
        else                                army_list[army_no].morale_timer -= 1;
    }
    if (army_list[army_no].target_timer) army_list[army_no].target_timer -= 1;
}

// FUNCTION: C2 0x4631E
// WIN: 0x0040493c
// Lines 281–286
//
// Enemy-army intelligence tick: flag a threat mood, refresh the
// sprite frame, and dispatch the per-state handler.
void a02_enemy(void)
{
    threat_mood = 2;
    get_enemy_image();
    army_states[army_list[army_no].state_idx]();
}

// FUNCTION: C2 0x46349
// WIN: 0x004049b0
// Lines 288–291
//
// Raider-army intelligence tick.  Body identical to a03_horde.
void a04_raider(void)
{
    threat_mood = 2;
    get_barbarian_image();
    army_states[army_list[army_no].state_idx]();
}

// FUNCTION: C2 0x4635A
// WIN: 0x004049ea
// Lines 302–309
//
// Revolt-army intelligence tick: raises threat_mood.  Uses the
// hostile-empire sprite (`get_enemy_image`) in the four named
// provinces (6, 0xF, 0x12, 0x22) and the generic barbarian sprite
// everywhere else, then dispatches the per-state handler.
void a05_revolt(void)
{
    threat_mood = 2;
    if (province_is == 6 || province_is == 0xF || province_is == 0x12 || province_is == 0x22)
        get_enemy_image();
    else
        get_barbarian_image();
    army_states[army_list[army_no].state_idx]();
}

// FUNCTION: C2 0x463A8
// WIN: 0x00404a62
// Lines 311–311
//
// Roman-trader-ship intelligence tick: ship sprite base 0x4E, then
// dispatch the per-state handler.
void a06_roman_ship(void)
{
    get_army_ship_image(0x4E);
    army_states[army_list[army_no].state_idx]();
}

// FUNCTION: C2 0x463B7
// WIN: 0x00404aac
// Lines 317–317
//
// Raider-ship intelligence tick: marks the global threat mood as 2
// and lets the caller's sprite update run.  Body identical to
// a07_enemy_ship.
void a08_raider_ship(void)
{
    threat_mood = 2;
}

// FUNCTION: C2 0x463C1
// WIN: 0x00404ac1
// Lines 320–320
//
// Empty citizen-state slot for the null state.
void s00_null(void)
{
}

// FUNCTION: C2 0x463C2
// WIN: 0x00404acc
// Lines 334–342
//
// Citizen state-1 (wait): tick down wait_count, and on expiry reset
// the per-citizen speed phase, clear action_kind, restore the
// saved state_idx, and arm speed = 5.
void s01_wait(void)
{
    if (--citizen_list[citizen_no].wait_count <= 0) {
        citizen_list[citizen_no].speed_phase = 0;
        citizen_list[citizen_no].speed_count = 0;
        citizen_list[citizen_no].action_kind = 0;
        citizen_list[citizen_no].state_idx   = citizen_list[citizen_no].saved_state_idx;
        citizen_list[citizen_no].flag_bits  |= 1;
        citizen_list[citizen_no].speed       = 5;
    }
}

// FUNCTION: C2 0x46411
// WIN: 0x00404bdc
// Lines 344–344
//
// Citizen state-2 (death): remove the citizen from the world.
void s02_death(void)
{
    remove_citizen(citizen_no);
}

// FUNCTION: C2 0x4641D
// WIN: 0x00404bf7
// Lines 349–367
//
// Citizen state-3 (administrator) tick.  Walks toward the queued
// admin target via citizen_go_to_target(0); on arrival, requires
// the citizen to be on a road (flag_bits & 1) and tries to set
// path-find flags + step in the current world direction.  If
// city_test_for_road reports an obstruction (>= 8) the citizen
// drops to state 2 (idle); otherwise commits the new target and
// flips action_kind = 1.
void s03_map_admin(void)
{
    int t;

    if (citizen_go_to_target(0) == 0) return;
    if ((citizen_list[citizen_no].flag_bits & 1) == 0) return;
    flag_range(0, citizen_list[citizen_no].x, citizen_list[citizen_no].y,
               3, 0xa, 0xc);
    t = (unsigned char)city_test_for_road(
            citizen_list[citizen_no].x,
            citizen_list[citizen_no].y,
            citizen_list[citizen_no].map_ref,
            citizen_list[citizen_no].world_dir);
    if (t >= 8) {
        citizen_list[citizen_no].state_idx = 2;
        return;
    }
    target_from_dirc(t);
    citizen_list[citizen_no].action_kind = 1;
}

// FUNCTION: C2 0x464CE
// WIN: 0x00404d45
// Lines 369–400
//
// Citizen state-4 "map markets" tick -- market traders stamp
// per-cell demand bits into the destination cell's `building` byte.
// Walks toward the next market via citizen_go_to_target; on arrival
// paints a 10-row 0xC0-mask flag region around the citizen, refreshes
// the population/industry counters, and, if the target tile is
// residential (base_kind 0xFC..0xFF), writes demand_a into bits
// 0..1 of `building` (2 or 3 by intensity) and demand_b into bits
// 2..3 (8 or 0xC).  Finally consults city_test_for_road for the
// next step: a real direction commits via target_from_dirc, no road
// drops the citizen to state 2.
void s04_map_markets(void)
{
    int ref;
    int t;

    if (citizen_go_to_target(0) == 0) return;
    if ((citizen_list[citizen_no].flag_bits & 1) == 0) return;

    flag_range(0,
               citizen_list[citizen_no].x,
               citizen_list[citizen_no].y,
               3, 0xa, 0xc0);
    get_population_and_industry_count(1, 1);

    ref = citizen_list[citizen_no].target_ref;
    if (((unsigned char *)city_map)[ref] >= 0xfc &&
        ((unsigned char *)city_map)[ref] <= 0xff) {
        if (citizen_list[citizen_no].market_demand_a > 0) {
            ((unsigned char *)city_map)[ref + 9] &= 0xfc;
            if (citizen_list[citizen_no].market_demand_a < 8)
                ((unsigned char *)city_map)[ref + 9] |= 2;
            else
                ((unsigned char *)city_map)[ref + 9] |= 3;
        }
        if (citizen_list[citizen_no].market_demand_b > 0) {
            ((unsigned char *)city_map)[ref + 9] &= 0xf3;
            if (citizen_list[citizen_no].market_demand_b < 8)
                ((unsigned char *)city_map)[ref + 9] |= 8;
            else
                ((unsigned char *)city_map)[ref + 9] |= 0xc;
        }
    }

    t = (unsigned char)city_test_for_road(citizen_list[citizen_no].x,
                                          citizen_list[citizen_no].y,
                                          citizen_list[citizen_no].map_ref,
                                          citizen_list[citizen_no].world_dir);
    if (t >= 8) {
        citizen_list[citizen_no].state_idx = 2;
        return;
    }
    target_from_dirc(t);
    citizen_list[citizen_no].action_kind = 1;
}

// FUNCTION: C2 0x4663A
// WIN: 0x00405005
// Lines 403–424
//
// Citizen state-5 handler: head toward the city's "top spot"
// (visit attraction).  If the path-find can't reach a target, fall
// back to a random nearby tile.  When walking on-road
// (flag_bits & 1), tick a 3-step countdown — every 3 steps the
// citizen re-anchors its destination to the live top_lv_x/y
// coordinates so it tracks moving attraction sprites.
void s05_maraude_to_top_spot(void)
{
    citizen_list[citizen_no].action_kind = 1;
    citizen_list[citizen_no].saved_state_idx = 5;
    if (citizen_maraude_to_target(1) == 0) {
        random_target();
        citizen_list[citizen_no].wait_count = 0;
        citizen_list[citizen_no].state = 3;
        return;
    }
    if ((citizen_list[citizen_no].flag_bits & 1) == 0) return;
    if (citizen_list[citizen_no].state != 0) {
        citizen_list[citizen_no].state--;
        return;
    }
    citizen_list[citizen_no].state = 3;
    citizen_list[citizen_no].dest_x = top_lv_x;
    citizen_list[citizen_no].dest_y = top_lv_y;
}

// FUNCTION: C2 0x466DA
// WIN: 0x00405143
// Lines 426–448
//
// Citizen state-6 (lictor / vigile "quell trouble") tick.
// Walks toward the queued rioter via citizen_maraude_to_target(2);
// on arrival, validates the target slot via the
// (target_kind, target_marker) tuple — `target_marker` is a
// snapshot of the target citizen's evolve_timer, so a recycled
// slot can be detected.  If still valid, refreshes dest_x/dest_y
// from the target's current position and bumps target_count
// (after 4 ticks of failing to engage, drops the target).
//
// If the target is gone or the slot is recycled, runs find_enemy
// in a 10-tile radius for a new target; if found, locks onto it
// (target_kind = idx, target_marker = enemy.evolve_timer, dest_x
// = enemy.x, dest_y = enemy.y, target_count = 0, wf_active = 0);
// if not, drops to state 2 (idle wander).
void s06_quell_trouble(void)
{
    int enemy_no;

    citizen_list[citizen_no].action_kind = 1;
    if (citizen_maraude_to_target(2) == 0) return;
    if ((citizen_list[citizen_no].flag_bits & 1) == 0) return;
    citizen_a = (unsigned char)citizen_list[citizen_no].target_kind;
    if (citizen_list[(unsigned char)citizen_list[citizen_no].target_kind].exists != 0
        && citizen_list[citizen_no].target_marker
            == citizen_list[citizen_a].evolve_timer) {
        citizen_list[citizen_no].dest_x =
            citizen_list[citizen_a].x;
        citizen_list[citizen_no].dest_y =
            citizen_list[citizen_a].y;
        citizen_list[citizen_no].target_count++;
        if (citizen_list[citizen_no].target_count > 4) {
            citizen_list[citizen_no].target_count = 0;
            citizen_list[citizen_no].wf_active    = 0;
        }
        return;
    }
    enemy_no = find_enemy(citizen_list[citizen_no].x,
                          citizen_list[citizen_no].y, 10);
    citizen_a = enemy_no;
    if ((short)enemy_no == 0) {
        citizen_list[citizen_no].state_idx = 2;
        return;
    }
    citizen_list[citizen_no].target_kind  = citizen_a;
    citizen_list[citizen_no].target_marker =
        citizen_list[(short)enemy_no].evolve_timer;
    citizen_list[citizen_no].dest_x =
        citizen_list[(short)enemy_no].x;
    citizen_list[citizen_no].dest_y =
        citizen_list[(short)enemy_no].y;
    citizen_list[citizen_no].target_count = 0;
    citizen_list[citizen_no].wf_active    = 0;
}

// FUNCTION: C2 0x46830
// WIN: 0x0040543e
// Lines 450–477
//
// Citizen state-7 (vigile patrol) tick.  Walks toward queued
// patrol target via citizen_go_to_target(0); on arrival, flags a
// 10×0x30 region around the citizen as patrolled
// (flag_range kind=0, range=4) and, if there's any active
// rioter or barbarian, scans for an enemy via find_enemy in a
// 10-tile radius.  On hit: lock onto the enemy (target_kind /
// target_marker / dest_*) and switch to state 6 (quell-trouble).
// On miss or all-quiet: continue patrol via the standard
// city_test_for_road / target_from_dirc dispatch (drop to state
// 2 with wait_count 40 if blocked).
//
// Despite the "army_patrol" name in the symbol table, this is a
// citizen-tick (vigile) handler — the s06/s07/s08 trio all
// operate on the citizen-grid.  Most of the trailing code-block
// shape is shared with s10_get_business and s06_quell_trouble.
void s07_army_patrol(void)
{
    int enemy_no;
    int t;

    if (citizen_go_to_target(0) == 0) return;
    if ((citizen_list[citizen_no].flag_bits & 1) == 0) return;
    flag_range(0, citizen_list[citizen_no].x,
               citizen_list[citizen_no].y, 4, 0xa, 0x30);
    if (no_of_rioters != 0 || no_of_barbarians != 0) {
        enemy_no = find_enemy(citizen_list[citizen_no].x,
                              citizen_list[citizen_no].y, 10);
        citizen_a = enemy_no;
        if ((short)enemy_no != 0) {
            citizen_list[citizen_no].target_kind  = citizen_a;
            citizen_list[citizen_no].target_marker =
                citizen_list[(short)enemy_no].evolve_timer;
            citizen_list[citizen_no].dest_x =
                citizen_list[(short)enemy_no].x;
            citizen_list[citizen_no].dest_y =
                citizen_list[(short)enemy_no].y;
            citizen_list[citizen_no].target_count = 0;
            citizen_list[citizen_no].wf_active    = 0;
            citizen_list[citizen_no].state_idx    = 6;
            return;
        }
    }
    t = (unsigned char)city_test_for_road(
                citizen_list[citizen_no].x,
                citizen_list[citizen_no].y,
                citizen_list[citizen_no].map_ref,
                citizen_list[citizen_no].world_dir);
    if (t >= 8) {
        citizen_list[citizen_no].state_idx  = 2;
        citizen_list[citizen_no].wait_count = 0x28;
        return;
    }
    target_from_dirc(t);
    citizen_list[citizen_no].action_kind = 1;
}

// FUNCTION: C2 0x46988
// WIN: 0x00405711
// Lines 479–507
//
// Citizen state-8 (vigile patrol) tick.  Walks toward the queued
// patrol target via citizen_go_to_target(0).  On arrival:
//   1. flag_range(0, x, y, 3, 0xa, 0x30) — 10×3 patrol marker.
//   2. test_fire_zones() — any nearby fire? → state 9 (fight),
//      return.
//   3. If any rioter or barbarian active, find_enemy in a 10-
//      tile radius.  On hit, lock onto the enemy and switch to
//      state 6 (quell).
//   4. Otherwise step via city_test_for_road / target_from_dirc.
//      Block (t >= 8) → state 2 with wait_count = 0x28.
void s08_vigile_patrol(void)
{
    int enemy_no;
    int t;

    if (citizen_go_to_target(0) == 0) return;
    if ((citizen_list[citizen_no].flag_bits & 1) == 0) return;
    flag_range(0, citizen_list[citizen_no].x,
               citizen_list[citizen_no].y, 3, 0xa, 0x30);
    if (test_fire_zones() != 0) {
        citizen_list[citizen_no].state_idx = 9;
        return;
    }
    if (no_of_rioters != 0 || no_of_barbarians != 0) {
        enemy_no = find_enemy(citizen_list[citizen_no].x,
                              citizen_list[citizen_no].y, 10);
        citizen_a = enemy_no;
        if ((short)enemy_no != 0) {
            citizen_list[citizen_no].target_kind  = citizen_a;
            citizen_list[citizen_no].target_marker =
                citizen_list[(short)enemy_no].evolve_timer;
            citizen_list[citizen_no].dest_x =
                citizen_list[(short)enemy_no].x;
            citizen_list[citizen_no].dest_y =
                citizen_list[(short)enemy_no].y;
            citizen_list[citizen_no].target_count = 0;
            citizen_list[citizen_no].wf_active    = 0;
            citizen_list[citizen_no].state_idx    = 6;
            return;
        }
    }
    t = (unsigned char)city_test_for_road(
                citizen_list[citizen_no].x,
                citizen_list[citizen_no].y,
                citizen_list[citizen_no].map_ref,
                citizen_list[citizen_no].world_dir);
    if (t >= 8) {
        citizen_list[citizen_no].state_idx  = 2;
        citizen_list[citizen_no].wait_count = 0x28;
        return;
    }
    target_from_dirc(t);
    citizen_list[citizen_no].action_kind = 1;
}

// FUNCTION: C2 0x46AFE
// WIN: 0x00405a0f
// Lines 509–530
//
// Citizen state-9 (fire-fighter) tick.  Walks toward the queued
// fire target; on arrival, either suppresses the fire via
// putting_out_fire and clears the targeting, confirms the fire
// still burns at the recorded tile via confirm_fire_target, or
// re-acquires via test_fire_zones + test_zone_for_closest_fire.
// On no nearby fire, drops to state 2 (idle).  saved_state_idx is
// re-stamped to 9 each tick so any temporary substate (ferret-run
// etc.) returns here afterwards.
void s09_fire_fight(void)
{
    citizen_list[citizen_no].saved_state_idx = 9;
    if (citizen_maraude_to_target(2) == 0) return;
    if ((citizen_list[citizen_no].flag_bits & 2) != 0) {
        citizen_list[citizen_no].state_idx   = 9;
        citizen_list[citizen_no].target_kind = 0;
        citizen_list[citizen_no].flag_bits  &= 0xfd;
    }
    if ((citizen_list[citizen_no].flag_bits & 1) == 0) return;
    if (putting_out_fire() != 0) {
        citizen_list[citizen_no].action_kind = 0;
        citizen_list[citizen_no].target_kind = 0;
        return;
    }
    if (confirm_fire_target() != 0) {
        citizen_list[citizen_no].action_kind = 1;
        return;
    }
    citizen_list[citizen_no].target_kind = 0;
    citizen_list[citizen_no].action_kind = 0;
    citizen_list[citizen_no].target_ref  = 0;
    if (test_fire_zones() != 0) {
        if (test_zone_for_closest_fire() == 0) return;
        citizen_list[citizen_no].dest_x     = z_x;
        citizen_list[citizen_no].dest_y     = z_y;
        citizen_list[citizen_no].target_ref = z_ptr;
        citizen_list[citizen_no].wf_active  = 0;
        citizen_list[citizen_no].target_kind = 1;
        citizen_list[citizen_no].action_kind = 1;
        return;
    }
    citizen_list[citizen_no].state_idx = 2;
}

// FUNCTION: C2 0x46C41
// WIN: 0x00405c88
// Lines 532–562
//
// Citizen state-10 (market trader) tick.  Walks toward the queued
// market target; on arrival, refreshes the population/industry
// counters and, if the cell is a market (base_kind 0xFA), stamps
// the citizen's market_demand_a / market_demand_b into the cell's
// `building` byte as two 2-bit demand levels (bits 0..1 = a, bits
// 2..3 = b, intensity flipped at demand >= 8).  Then consults
// city_test_for_road for the next step: a real direction commits
// via target_from_dirc, obstruction drops to state 2 with a 40-
// tick cool-down.
void s10_get_business(void)
{
    int ref;
    int t;

    if (citizen_go_to_target(0) == 0) return;
    if ((citizen_list[citizen_no].flag_bits & 1) == 0) return;
    get_population_and_industry_count(1, 0);
    ref = citizen_list[citizen_no].target_ref;
    if (((unsigned char *)city_map)[ref] == 0xfa) {
        if (citizen_list[citizen_no].market_demand_a > 0) {
            ((unsigned char *)city_map)[ref + 9] &= 0xfc;
            if (citizen_list[citizen_no].market_demand_a < 8)
                ((unsigned char *)city_map)[ref + 9] |= 2;
            else
                ((unsigned char *)city_map)[ref + 9] |= 3;
        }
        if (citizen_list[citizen_no].market_demand_b > 0) {
            ((unsigned char *)city_map)[ref + 9] &= 0xf3;
            if (citizen_list[citizen_no].market_demand_b < 8)
                ((unsigned char *)city_map)[ref + 9] |= 8;
            else
                ((unsigned char *)city_map)[ref + 9] |= 0xc;
        }
    }
    t = (unsigned char)city_test_for_road(citizen_list[citizen_no].x, citizen_list[citizen_no].y, citizen_list[citizen_no].map_ref, citizen_list[citizen_no].world_dir);
    if (t >= 8) {
        citizen_list[citizen_no].state_idx  = 2;
        citizen_list[citizen_no].wait_count = 0x28;
        return;
    }
    target_from_dirc(t);
    citizen_list[citizen_no].action_kind = 1;
}

// FUNCTION: C2 0x46D86
// WIN: 0x00405f03
// Lines 564–574
//
// Citizen state-11 (rioting in place): tick down wait_count; on
// expiry transition to state 12 (goto_riot), aim the citizen at
// the player's last-viewed tile and reset its walk speed to 5.
void s11_riot(void)
{
    citizen_list[citizen_no].action_kind = 0;
    if (--citizen_list[citizen_no].wait_count <= 0) {
        citizen_list[citizen_no].state_idx   = 12;
        citizen_list[citizen_no].dest_x      = top_lv_x;
        citizen_list[citizen_no].dest_y      = top_lv_y;
        citizen_list[citizen_no].speed_phase = 0;
        citizen_list[citizen_no].speed_count = 0;
        citizen_list[citizen_no].speed       = 5;
    }
}

// FUNCTION: C2 0x46DE3
// WIN: 0x00406003
// Lines 576–586
//
// Citizen state-12 (walking to riot location): step toward the
// queued destination via citizen_maraude_to_target.  On arrival
// re-aim at the player's last-viewed tile and transition to
// state 11 (riot in place) with a 30-tick rest.
void s12_goto_riot(void)
{
    citizen_list[citizen_no].action_kind = 1;
    if (citizen_maraude_to_target(1) && (citizen_list[citizen_no].flag_bits & 1)) {
        citizen_list[citizen_no].dest_x     = top_lv_x;
        citizen_list[citizen_no].dest_y     = top_lv_y;
        citizen_list[citizen_no].state_idx  = 11;
        citizen_list[citizen_no].wait_count = 30;
    }
}

// FUNCTION: C2 0x46E44
// WIN: 0x004060cb
//
// Empty army-state slot for the null state.
void sa00_null(void)
{
}

// FUNCTION: C2 0x46E45
// WIN: 0x004060d6
// Lines 590–602
//
// Army state-1 (wait): unless the global pause counter `cnt4` is
// still ticking, count down wait_count and on expiry restore the
// saved state, clear targeting state, reset heading to 5, and run
// test_for_army_attack to see if the next tick lands on an enemy.
void sa01_wait(void)
{
    if (cnt4) return;
    if (--army_list[army_no].wait_count <= 0) {
        army_list[army_no].wait_count   = 5;
        army_list[army_no].target_count      = 0;
        army_list[army_no].target_kind   = 0;
        army_list[army_no].return_flag  = 0;
        army_list[army_no].state_idx    = army_list[army_no].saved_state_idx;
        army_list[army_no].flags       &= 0xFC;
        army_list[army_no].flags       |= 1;
        army_list[army_no].heading      = 5;
        test_for_army_attack();
    }
}

// FUNCTION: C2 0x46EB9
// WIN: 0x00406249
// Lines 603–603
//
// Army state-2 (death): remove the army from the world.
void sa02_death(void)
{
    remove_army(army_no);
}

// FUNCTION: C2 0x46EC5
// WIN: 0x00406264
// Lines 610–645
//
// Region-map army state-3: walk the patrol route.  Walks the army
// one tick toward (target_x, target_y) via region_go_to_target;
// returns early if path-find fails or the army is off-road.  Sets
// return_flag, then tries test_for_army_attack (which may engage
// an enemy this tick).  Otherwise advances the route waypoint
// cursor (army_routes[cohort_id]): pulls the next waypoint in the
// current row if there is room; on row exhaustion either advances
// to the next row, wraps to (row=1, col=0) for multi-row routes,
// or drops to state 1 (wait) for a single-row route that's done.
void sa03_army_move(void)
{
    if (region_go_to_target(0) == 0) return;
    if ((army_list[army_no].flags & 1) == 0) return;
    army_list[army_no].return_flag = 1;
    if (test_for_army_attack() != 0) return;

    if ((unsigned char)army_list[army_no].dest_x
            < army_routes[army_list[army_no].cohort_id]
                  .row_len[army_list[army_no].dest_y]) {
        new_army_route_point();
        return;
    }
    if (army_list[army_no].dest_y
            < army_routes[army_list[army_no].cohort_id].row_count - 1) {
        army_list[army_no].dest_y++;
        army_list[army_no].dest_x = 0;
        new_army_route_point();
        new_army_route_point();
        return;
    }
    if (army_routes[army_list[army_no].cohort_id].row_count <= 1) {
        army_list[army_no].state_idx       = 1;
        army_list[army_no].saved_state_idx = 1;
        army_list[army_no].wait_count      = 5;
        army_routes[army_list[army_no].cohort_id].chase_row = 0;
        army_routes[army_list[army_no].cohort_id].target_army = 0;
        return;
    }
    army_list[army_no].dest_y = 1;
    army_list[army_no].dest_x = 0;
    new_army_route_point();
}

// FUNCTION: C2 0x46FB4
// WIN: 0x00406517
// Lines 647–669
//
// Pull the next patrol-route waypoint for the current army.  First
// tries to engage a queued enemy via `goto_army_attack` (returns 1
// if it commits).  Otherwise looks up the next (x,y) pair in the
// army's route table, validates that the destination cell is either
// a target building (region_map cell-byte 0x93..0x96 + flags & 1)
// or open ground (no flags & 0x12), and stores the pair in
// prev_x/prev_y.  Returns 1 if the waypoint differs from the army's
// current position (i.e. the army still has to walk), 0 otherwise.
int new_army_route_point(void)
{
    int cell_off;
    int wp_y;
    char tile_flags;
    unsigned char cell_kind;
    int wp_x;

    if (goto_army_attack() != 0) return 1;

    wp_x = army_routes[army_list[army_no].cohort_id]
               .points[army_list[army_no].dest_y][army_list[army_no].dest_x].x;
    wp_y = army_routes[army_list[army_no].cohort_id]
               .points[army_list[army_no].dest_y][army_list[army_no].dest_x].y;
    cell_off = (wp_x + wp_y * REGION_W) * REGION_CELL_BYTES;
    tile_flags = (*(struct region_cell *)((unsigned char *)region_map + (cell_off))).terrain;
    army_list[army_no].dest_x++;

    if ((tile_flags & 1) != 0) {
        cell_kind = (*(struct region_cell *)((unsigned char *)region_map + (cell_off))).base_kind;
        if (cell_kind < 0x93 || cell_kind > 0x96) return 0;
    } else {
        if ((tile_flags & 0x12) != 0) return 0;
    }

    army_list[army_no].target_x = wp_x;
    army_list[army_no].target_y = wp_y;
    if (army_list[army_no].target_x != army_list[army_no].x) return 1;
    if (army_list[army_no].target_y == army_list[army_no].y) return 0;
    return 1;
}

// FUNCTION: C2 0x470A2
// WIN: 0x0040678c
// Lines 671–680
//
// Try to switch the current army into the "attack" state, locking
// onto the queued enemy army from its route slot.  Returns 0 if the
// route's enemy slot is empty or the army has not yet stepped far
// enough; on success commits the chosen `enemy_army`, copies the
// target's image_id (+0x32 word) into the current army's +0x34, sets
// state_idx = 4 (= attack) and returns 1.
int goto_army_attack(void)
{
    if (army_routes[army_list[army_no].cohort_id].target_army == 0)
        return 0;
    if (army_list[army_no].dest_y < army_routes[army_list[army_no].cohort_id].chase_row)
        return 0;
    enemy_army = army_routes[army_list[army_no].cohort_id].target_army;
    army_list[army_no].army_id = enemy_army;
    army_list[army_no].target_marker =
        army_list[enemy_army].evolve_timer;
    army_list[army_no].state_idx = 4;
    return 1;
}

// FUNCTION: C2 0x47120
// WIN: 0x004068ce
// Lines 682–710
//
// Decide whether the current cohort army should commit to an
// attack this tick.  Returns 1 if it engaged (state flipped to 4
// = sa04_army_attack), else 0.  Skips entirely unless army.type
// == 1 (cohort), order_progress == 0, and total_troops > 0.
//
// Two engagement paths: (1) if army_routes[cohort_id].target_army
// has a queued chase target within Chebyshev distance 6, engage
// that; (2) otherwise, if readiness_level != 0, scan for an
// invading army within radius 8 via find_invading_army and engage
// any hit.  Both paths cache the enemy's evolve_timer as
// target_marker so the engagement can detect a slot recycle.
int test_for_army_attack(void)
{
    int d;
    int found;

    if (army_list[army_no].type != 1) goto fail;
    if (army_list[army_no].order_progress != 0) goto fail;
    if (army_list[army_no].total_troops <= 0) goto fail;

    if (army_routes[army_list[army_no].cohort_id].target_army != 0) {
        enemy_army = (short)army_routes[army_list[army_no].cohort_id].target_army;
        d = get_longest_distance(army_list[army_no].x,
                                 army_list[army_no].y,
                                 army_list[enemy_army].x,
                                 army_list[enemy_army].y);
        if (d > 6) goto fail;
        army_list[army_no].army_id = enemy_army;
        army_list[army_no].target_marker  = army_list[enemy_army].evolve_timer;
        army_list[army_no].saved_state_idx = army_list[army_no].state_idx;
        army_list[army_no].state_idx       = 4;
        return 1;
    }
    if (army_list[army_no].readiness_level == 0) goto fail;
    found = find_invading_army(army_list[army_no].x, army_list[army_no].y, 8);
    enemy_army = found;
    if ((short)found == 0) goto fail;
    army_list[army_no].army_id = enemy_army;
    army_list[army_no].target_marker  = army_list[enemy_army].evolve_timer;
    army_list[army_no].saved_state_idx = army_list[army_no].state_idx;
    army_list[army_no].state_idx       = 4;
    return 1;
fail:
    return 0;
}

// FUNCTION: C2 0x47257
// WIN: 0x00406c08
// Lines 712–727
//
// Region-map army state-4: attack the locked-on enemy.  Aborts to
// state 1 (wait 5 ticks) if the enemy has vanished (exists == 0)
// or its evolve_timer no longer matches the cached `target_marker`
// from `goto_army_attack`.  Otherwise tracks the enemy's tile
// (`prev_x/y = enemy.x/y`) and tail-calls region_go_to_target — on
// success and when on-road (flags & 1), set return_flag.
void sa04_army_attack(void)
{
    if (army_list[army_no].wf_step >= 2) army_list[army_no].wf_active = 0;
    enemy_army = army_list[army_no].army_id;
    if (army_list[army_list[army_no].army_id].exists == 0
     || army_list[enemy_army].evolve_timer
            != army_list[army_no].target_marker) {
        army_list[army_no].state_idx = 1;
        army_list[army_no].wait_count = 5;
        return;
    }
    army_list[army_no].target_x = army_list[enemy_army].x;
    army_list[army_no].target_y = army_list[enemy_army].y;
    if (region_go_to_target(0) != 0
     && (army_list[army_no].flags & 1) != 0)
        army_list[army_no].return_flag = 1;
}

// FUNCTION: C2 0x47332
// WIN: 0x00406db1
// Lines 729–740
//
// Region-map army state-5 (return to home / waypoint): set
// return_flag, walk one tick via region_go_to_target; on arrival
// (flags bit 1 set) drop to state 1 (wait) and clear the pending
// move order.
void sa05_army_return(void)
{
    army_list[army_no].return_flag = 1;
    if (region_go_to_target(0) && (army_list[army_no].flags & 2)) {
        army_list[army_no].state_idx      = 1;
        army_list[army_no].order_progress = 0;
    }
}

// FUNCTION: C2 0x47382
// WIN: 0x00406e42
// Lines 742–751
//
// Region-map army state-6: the raid handler.  Picks a target tile
// (nearest religious-building / city centre) when the army has no
// current target (prev_x/y both zero) or the "force re-pick" flag
// (flags & 2) is set, then sets return_flag and tail-calls
// region_go_to_target(0) to actually walk toward it.
void sa06_army_land_raid(void)
{
    if ((army_list[army_no].target_x == 0 && army_list[army_no].target_y == 0)
     || (army_list[army_no].flags & 2) != 0) {
        if (get_nearest_reg_building() != 0) {
            army_list[army_no].target_x = gmn_x;
            army_list[army_no].target_y = gmn_y;
        } else {
            army_list[army_no].target_x = reg_city_x;
            army_list[army_no].target_y = reg_city_y;
        }
    }
    army_list[army_no].return_flag = 1;
    region_go_to_target(0);
}

// FUNCTION: C2 0x4742A
// WIN: 0x00406f66
// Lines 753–756
//
// Region-map army state-7: barbarian/raider land-invasion handler.
// Always targets the player's city (reg_city_x/reg_city_y), sets
// return_flag, and walks one tick via region_go_to_target.
void sa07_army_land_invade(void)
{
    army_list[army_no].target_x      = reg_city_x;
    army_list[army_no].target_y      = reg_city_y;
    army_list[army_no].return_flag = 1;
    region_go_to_target(0);
}

// FUNCTION: C2 0x47452
// WIN: 0x00406fdb
// Lines 761–779
//
// Army state-8 "stuck" tick -- recovery handler when the straight
// path to target is blocked.  On entering a fresh region cell,
// spirals outward from the desired heading (alternating right /
// left, wrapping 0..7) for up to 3 iterations.  At each step,
// tries try_a_regionmap_square; on a free square, nudges the
// target by the matching gmn_ofsets delta and exits the loop.
// On all-three-fail bumps stuck_timer; once it crosses 4,
// transitions to state 1 (wait 0xA ticks).  Outside the
// recovery branch falls back to region_go_to_target and
// resumes saved_state_idx on arrival.
void sa08_army_stuck(void)
{
    int left_dir;
    int right_dir;
    int i;
    signed char st;

    if (entering_new_square() != 0) {
        left_dir  = get_heading(
                        army_list[army_no].x,
                        army_list[army_no].y,
                        army_list[army_no].target_x,
                        army_list[army_no].target_y,
                        army_list[army_no].world_dir);
        right_dir = left_dir;
        for (i = 0; i < 3; i++) {
            right_dir++;
            if (right_dir >= 8) right_dir = 0;
            left_dir--;
            if (left_dir < 0)   left_dir = 7;
            if (try_a_regionmap_square(right_dir, 0, 0) != 0) {
                army_list[army_no].target_x +=
                    gmn_ofsets[right_dir].dx;
                army_list[army_no].target_y +=
                    gmn_ofsets[right_dir].dy;
                goto post_loop;
            }
            if (try_a_regionmap_square(left_dir, 0, 0) != 0) {
                army_list[army_no].target_x +=
                    gmn_ofsets[left_dir].dx;
                army_list[army_no].target_y +=
                    gmn_ofsets[left_dir].dy;
                goto post_loop;
            }
            if (i == 2) {
                army_list[army_no].saved_state_idx = 1;
                army_list[army_no].wait_count      = 5;
                army_list[army_no].order_progress  = 1;
            }
        }
post_loop:
        st = ++army_list[army_no].stuck_timer;
        if (st > 4) {
            army_list[army_no].state_idx     = 1;
            army_list[army_no].wait_count    = 0xa;
            army_list[army_no].order_progress = 0;
            army_list[army_no].wf_active     = 0;
            return;
        }
    }
    if (region_go_to_target(0) == 0) return;
    if ((army_list[army_no].flags & 1) == 0) return;
    army_list[army_no].state_idx = army_list[army_no].saved_state_idx;
}

// FUNCTION: C2 0x475D2
// WIN: 0x0040735d
// Lines 782–801
//
// Region-map army state-9: army is sieging an enemy stronghold.
// Each tick:
//   * Force sprite_anim = 0x66 (siege-stance frame).
//   * Pick a "period" from total_troops (more troops → faster
//     siege; 8..40 ticks per damage event):
//        ≤  10 → 40    ≤ 200 → 20
//        ≤  50 → 30    ≤ 400 → 15
//        ≤ 100 → 25    ≤ 800 → 12
//        else  → 8
//   * subtimer (+0x13) ++; if < 50, return.
//   * Else reset subtimer = 0; main_timer (wf_phase / +0x14) ++;
//     if < period, return.
//   * Else: clear the 3×3 region area centred on the army (which
//     destroys the besieged building), set state_idx = 7, fire
//     message 0x60 with the army's map_ref as parameter.
void sa09_army_siege(void)
{
    int period;
    unsigned char sub;
    unsigned char mn;

    army_list[army_no].sprite_anim = 0x66;

    if (army_list[army_no].total_troops <= 10)       period = 40;
    else if (army_list[army_no].total_troops <= 50)  period = 30;
    else if (army_list[army_no].total_troops <= 100) period = 25;
    else if (army_list[army_no].total_troops <= 200) period = 20;
    else if (army_list[army_no].total_troops <= 400) period = 15;
    else if (army_list[army_no].total_troops <= 800) period = 12;
    else                                             period = 8;

    sub = ++army_list[army_no].stuck_timer;
    if ((signed char)sub < 50) return;
    army_list[army_no].stuck_timer = 0;
    mn = ++army_list[army_no].wf_phase;
    if ((signed char)mn < period) return;

    clear_a_reg_area(army_list[army_no].x - 1,
                     army_list[army_no].y - 1,
                     army_list[army_no].x + 1,
                     army_list[army_no].y + 1, 1);
    army_list[army_no].state_idx = 7;
    put_message(0x60, army_list[army_no].map_ref, 0x13);
}

// FUNCTION: C2 0x476CF
// WIN: 0x004075e1
// Lines 804–818
//
// Region-map army state-A0 — demobilised: snap the army to its
// home fort tile.  Clears the previous region_map cell's army-
// occupant byte, stamps `army_no` into the fort tile, syncs
// `army.map_ref` to `army.fort_ref`, and rebuilds `army.x` /
// `army.y` from the new map offset (cell stride = 8, region width
// = 60).  Resets walking state (target_kind / target_count /
// pixel_x / pixel_y / world_dir = 0) and forces flags bit 0.
void sa10_army_demobed(void)
{
    army_list[army_no].return_flag = 0;
    (*(struct region_cell *)((unsigned char *)region_map + (army_list[army_no].map_ref))).occupant = 0;
    (*(struct region_cell *)((unsigned char *)region_map + (army_list[army_no].fort_ref))).occupant = army_no;
    army_list[army_no].map_ref = army_list[army_no].fort_ref;
    army_list[army_no].saved_state_idx = 1;
    army_list[army_no].target_count = 0;
    army_list[army_no].target_kind  = 0;
    army_list[army_no].flags |= 1;
    army_list[army_no].pixel_x = 0;
    army_list[army_no].pixel_y = 0;
    army_list[army_no].world_dir = 0;
    army_list[army_no].x = (char)((army_list[army_no].fort_ref / 8) % 60);
    army_list[army_no].y = (char)((army_list[army_no].fort_ref / 8) / 60);
}

// FUNCTION: C2 0x4777F
// WIN: 0x004077c2
// Lines 821–837
//
// Army state-11 (sail to player's port): target the city tile and
// walk via sail_to_target.  On arrival (flags bit 3 set) reset
// wf_phase, transition to state 0xD (sail-round-coast), and stash
// the city as the new dest.
void sa11_army_sail_to_port(void)
{
    army_list[army_no].target_x      = reg_city_x;
    army_list[army_no].target_y      = reg_city_y;
    army_list[army_no].return_flag = 1;
    if (sail_to_target(0) && (army_list[army_no].flags & 8)) {
        army_list[army_no].wf_phase  = 0;
        army_list[army_no].state_idx = 0xD;
        army_list[army_no].dest_x    = reg_city_x;
        army_list[army_no].dest_y    = reg_city_y;
    }
}

// FUNCTION: C2 0x477FD
// WIN: 0x004078e5
// Lines 839–865
//
// Army state-12 (sail home) tick: moves a sea-borne army back to
// its launch port (home_x/home_y).  Re-anchors the target to the
// home cell and, when more than one tile away, nudges target_x/y
// inward one tile per axis if home is at the map edge (push from
// x == 0, pull from x >= 0x3B, same for y).  Sets return_flag and
// sails one tick via sail_to_target.  On success, transitions to
// state 0xF (sa15_sink hand-off) if any of flags bits 8 / 2 / 4 is
// set (tested as three separate ifs).
void sa12_army_sail_home(void)
{
    int dist;

    army_list[army_no].target_x = army_list[army_no].home_x;
    army_list[army_no].target_y = army_list[army_no].home_y;
    dist = get_longest_distance(army_list[army_no].x,
                                army_list[army_no].y,
                                army_list[army_no].home_x,
                                army_list[army_no].home_y);
    if (dist > 1) {
        if (army_list[army_no].x != army_list[army_no].target_x) {
            if (army_list[army_no].home_x <= 0)
                army_list[army_no].target_x++;
            else if (army_list[army_no].home_x >= 0x3b)
                army_list[army_no].target_x--;
        }
        if (army_list[army_no].y != army_list[army_no].target_y) {
            if (army_list[army_no].home_y <= 0)
                army_list[army_no].target_y++;
            else if (army_list[army_no].home_y >= 0x3b)
                army_list[army_no].target_y--;
        }
    }
    army_list[army_no].return_flag = 1;
    if (sail_to_target(0) == 0) return;
    if ((army_list[army_no].flags & 8) != 0)
        army_list[army_no].state_idx = 0xf;
    if ((army_list[army_no].flags & 2) != 0)
        army_list[army_no].state_idx = 0xf;
    if ((army_list[army_no].flags & 4) != 0)
        army_list[army_no].state_idx = 0xf;
}

// FUNCTION: C2 0x47967
// WIN: 0x00407c18
// Lines 867–903
//
// Sea-army state-13 (sail round coast): sister of
// sa16_army_lurk_round_coast for traders/invaders that want to
// find a beaching cell rather than a port.  `wf_phase` doubles as
// a circumnavigation timeout counter; once it crosses 0x14 ticks
// the army gives up and transitions to state 0xC (sail_home).
// try_a_seamap_square return == 3 (good docking candidate, even
// heading only) triggers dock_the_ship_in_good_port: success
// parks the ship 10 ticks at the docks, failure parks it 100
// ticks before retry, and either way sets quick_respawn so the
// eventual sa15_sink hand-off uses the 2-tick fast respawn.
void sa13_army_sail_round_coast(void)
{
    int heading;
    int attempts;
    int r;
    signed char ph;

    army_list[army_no].return_flag = 1;
    if (sail_to_target(0) == 0) return;
    if ((army_list[army_no].flags & 0xa) == 0) return;
    army_list[army_no].flags &= 0xfd;
    ph = ++army_list[army_no].wf_phase;
    if (ph > 0x14) {
        army_list[army_no].state_idx = 0xc;
        return;
    }
    army_list[army_no].target_x = army_list[army_no].dest_x;
    army_list[army_no].target_y = army_list[army_no].dest_y;
    heading = get_heading(army_list[army_no].x,
                          army_list[army_no].y,
                          army_list[army_no].target_x,
                          army_list[army_no].target_y,
                          army_list[army_no].world_dir);
    for (attempts = 0; attempts < 8; attempts++) {
        r = try_a_seamap_square(heading, 0, 0);
        if (r == 1) {
            army_list[army_no].target_x =
                army_list[army_no].x +
                gmn_ofsets[heading].dx;
            army_list[army_no].target_y =
                army_list[army_no].y +
                gmn_ofsets[heading].dy;
            return;
        }
        if (r == 2) {
            army_list[army_no].state_idx = 0xf;
            return;
        }
        if (r == 3 && (heading & 1) == 0) {
            army_list[army_no].state_idx       = 1;
            army_list[army_no].saved_state_idx = 0xc;
            if (dock_the_ship_in_good_port(heading) != 0)
                army_list[army_no].wait_count = 0xa;
            else
                army_list[army_no].wait_count = 0x64;
            army_list[army_no].quick_respawn = 1;
        } else {
            army_list[army_no].dest_x =
                army_list[army_no].x +
                gmn_ofsets[heading].dx;
            army_list[army_no].dest_y =
                army_list[army_no].y +
                gmn_ofsets[heading].dy;
        }
        if (army_list[army_no].army_id != 0) {
            heading--;
            if (heading < 0) heading = 7;
        } else {
            heading++;
            if (heading >= 8) heading = 0;
        }
        if (attempts >= 7)
            army_list[army_no].state_idx = 0xf;
    }
}

// FUNCTION: C2 0x47B80
// WIN: 0x00408076
// Lines 905–920
//
// Army state-14 (sail to shore for an invasion): target the city,
// sail one tick; on landfall (landed_flag set) transition to
// state 0x10 (sa16_lurk) with the city as dest, or otherwise fall
// back to the saved state on a successful waypoint.
void sa14_army_sail_to_shore(void)
{
    army_list[army_no].target_x      = reg_city_x;
    army_list[army_no].target_y      = reg_city_y;
    army_list[army_no].return_flag = 1;
    sail_to_target(0);
    if (army_list[army_no].landed_flag) {
        army_list[army_no].state_idx = 0x10;
        army_list[army_no].flags    &= 0xFD;
        army_list[army_no].dest_x    = reg_city_x;
        army_list[army_no].dest_y    = reg_city_y;
        return;
    }
    if (army_list[army_no].flags & 0xA)
        army_list[army_no].state_idx = army_list[army_no].saved_state_idx;
}

// FUNCTION: C2 0x47C10
// WIN: 0x004081dc
// Lines 922–949
//
// Naval trader sink handler.  Schedules respawn of the appropriate
// trader (via the corresponding compass-side `*_trader_count*`
// global) and removes the army.  Respawn delay is 2 ticks if
// `quick_respawn` is set (e.g. by sa13_army_sail_round_coast when
// the ship has run aground) or 15 ticks otherwise.  Each compass
// side has two trader slots (count0 / count1) selected by the
// army's `army_id` field (0 = first slot, non-zero = second).
void sa15_sink(void)
{
    int delay;

    delay = (army_list[army_no].quick_respawn != 0) ? 2 : 15;
    if (army_list[army_no].compass_side == 0) {            /* north */
        if (army_list[army_no].army_id == 0)
            north_trader_count0 = delay;
        else
            north_trader_count1 = delay;
    } else if (army_list[army_no].compass_side == 2) {     /* east  */
        if (army_list[army_no].army_id == 0)
            east_trader_count0 = delay;
        else
            east_trader_count1 = delay;
    } else if (army_list[army_no].compass_side == 4) {     /* south */
        if (army_list[army_no].army_id == 0)
            south_trader_count0 = delay;
        else
            south_trader_count1 = delay;
    } else if (army_list[army_no].compass_side == 6) {     /* west  */
        if (army_list[army_no].army_id == 0)
            west_trader_count0 = delay;
        else
            west_trader_count1 = delay;
    }
    remove_army(army_no);
}

// FUNCTION: C2 0x47CD8
// WIN: 0x004083a5
// Lines 951–979
//
// Sea-army state-16 (lurk round coast): a sailing army that's
// blocked from its current target tries up to 8 alternate headings
// around the coastline before giving up.  Only runs when
// sail_to_target reports progress with the "stuck" or
// "land/grounded" flag bits set.  Sweeps headings CCW (army_id
// != 0) or CW (army_id == 0) probing each with try_a_seamap_square:
// 1 = sea-walkable -> commit and exit; 2 = give-up sentinel ->
// state 0xf (sink); 0 = stash the candidate into dest and keep
// trying; 0 without landed_flag = resume the saved state.  On the
// 8th failed attempt forces state 0xf as a fallback sink.
void sa16_army_lurk_round_coast(void)
{
    int heading;
    int attempts;
    int r;

    army_list[army_no].return_flag = 1;
    if (sail_to_target(0) == 0) return;
    if ((army_list[army_no].flags & 0xa) == 0) return;
    army_list[army_no].flags &= 0xfd;
    army_list[army_no].target_x = army_list[army_no].dest_x;
    army_list[army_no].target_y = army_list[army_no].dest_y;
    heading = get_heading(army_list[army_no].x,
                          army_list[army_no].y,
                          army_list[army_no].target_x,
                          army_list[army_no].target_y,
                          army_list[army_no].world_dir);
    for (attempts = 0; attempts < 8; attempts++) {
        r = try_a_seamap_square(heading, 0, 0);
        if (r == 1) {
            army_list[army_no].target_x =
                army_list[army_no].x +
                gmn_ofsets[heading].dx;
            army_list[army_no].target_y =
                army_list[army_no].y +
                gmn_ofsets[heading].dy;
            return;
        }
        if (r == 2) {
            army_list[army_no].state_idx = 0xf;
            return;
        }
        if (r == 0 && army_list[army_no].landed_flag == 0) {
            army_list[army_no].state_idx =
                army_list[army_no].saved_state_idx;
            return;
        }
        army_list[army_no].dest_x =
            army_list[army_no].x +
            gmn_ofsets[heading].dx;
        army_list[army_no].dest_y =
            army_list[army_no].y +
            gmn_ofsets[heading].dy;
        if (army_list[army_no].army_id != 0) {
            heading--;
            if (heading < 0) heading = 7;
        } else {
            heading++;
            if (heading >= 8) heading = 0;
        }
        if (attempts >= 7)
            army_list[army_no].state_idx = 0xf;
    }
}

// FUNCTION: C2 0x47E9D
// WIN: 0x0040875d
// Lines 987–1030
//
// Compute the current citizen's sprite image_id from a base image,
// the citizen's facing direction relative to map_direction (one of 8),
// and the walk-phase (`speed_count & 3`).  Direction adds 0/3/6/.../21
// (a row per 3-frame walk cycle); phase adds 0/1/2/1 (alternating
// foot-forward poses).  Stores result into citizen.image_id.
void get_movement_image(int img_base)
{
    int d;

    d = citizen_list[citizen_no].world_dir - map_direction;
    if (d < 0) d += 8;
    switch (d) {
    case 0: break;
    case 1: img_base += 3; break;
    case 2: img_base += 6; break;
    case 3: img_base += 9; break;
    case 4: img_base += 12; break;
    case 5: img_base += 15; break;
    case 6: img_base += 18; break;
    case 7: img_base += 21; break;
    }
    switch (citizen_list[citizen_no].speed_count & 3) {
    case 1:
    case 3: img_base += 1; break;
    case 2: img_base += 2; break;
    }
    citizen_list[citizen_no].image_id = img_base;
}

// FUNCTION: C2 0x47F29
// WIN: 0x0040889c
// Lines 1032–1040
//
// Compute screen-direction sprite frame for the current army's ship.
// Rotates the army's absolute world heading by `map_direction`, wraps
// to the [0..7] range, and stores `img_base + dir` into the army's
// sprite_image slot.
void get_army_ship_image(int img_base)
{
    int dir;
    dir = army_list[army_no].world_dir - map_direction + 1;
    if (dir < 0)  dir += 8;
    if (dir >= 8) dir %= 8;
    img_base += dir;
    army_list[army_no].sprite_image = img_base;
}

// FUNCTION: C2 0x47F7A
// WIN: 0x00408918
// Lines 1042–1050
//
// Pick the rioter sprite based on the current wait_count: chunked
// into 5-tick bands, even bands use img + 0x1B and odd bands use
// img + 0x1C.  Used by i07_rioter_man for the mob-walking sprite.
void get_rioter_image(int img)
{
    if (citizen_list[citizen_no].wait_count < 5) {
        citizen_list[citizen_no].image_id = (img + 0x1B);
        return;
    }
    if (citizen_list[citizen_no].wait_count < 10) {
        citizen_list[citizen_no].image_id = (img + 0x1C);
        return;
    }
    if (citizen_list[citizen_no].wait_count < 15) {
        citizen_list[citizen_no].image_id = (img + 0x1B);
        return;
    }
    if (citizen_list[citizen_no].wait_count < 20) {
        citizen_list[citizen_no].image_id = (img + 0x1C);
        return;
    }
    if (citizen_list[citizen_no].wait_count < 25) {
        citizen_list[citizen_no].image_id = (img + 0x1B);
        return;
    }
    citizen_list[citizen_no].image_id = (img + 0x1C);
}

// FUNCTION: C2 0x47FC7
// WIN: 0x00408aa0
// Lines 1052–1069
//
// Sprite-frame helper for a barbarian army.  Sister of get_enemy_image
// / get_cohort_image.  At state_idx >= 14 the barbarian is in
// advanced combat / death animation, signalled by a fixed
// `dir + 0x56` direction-only image with no animation cycle.
void get_barbarian_image(void)
{
    int dir;

    army_list[army_no].sprite_dir = 0;
    dir = army_list[army_no].world_dir - map_direction + 1;
    if (dir < 0)  dir += 8;
    if (dir >= 8) dir %= 8;

    if (army_list[army_no].state_idx >= 14) {
        army_list[army_no].sprite_image = (char)(dir + 0x56);
        army_list[army_no].sprite_anim = 0;
    } else {
        army_list[army_no].sprite_image = tribe_to_standard[
            army_list[army_no].tribe_id];
        army_list[army_no].sprite_anim = (get_army_walk_dirc(dir,
            army_list[army_no].target_kind) + 0x2a);
    }
}

// FUNCTION: C2 0x48079
// WIN: 0x00408beb
// Lines 1071–1088
//
// Compute the sprite frame for an enemy (barbarian / brigand) army.
// At advanced state (state_idx >= 14, charging/dead) the frame is a
// fixed `dir + 0x5e` direction-only image with no animation cycle.
// Otherwise pick a tribe-banner image and combine the cnt8 animation
// counter with the walk-direction sub-frame.
void get_enemy_image(void)
{
    int dir;

    dir = army_list[army_no].world_dir - map_direction + 1;
    if (dir < 0)  dir += 8;
    if (dir >= 8) dir %= 8;

    if (army_list[army_no].state_idx >= 14) {
        army_list[army_no].sprite_image = (char)(dir + 0x5e);
        army_list[army_no].sprite_anim = 0;
        army_list[army_no].sprite_dir  = 0;
    } else {
        army_list[army_no].sprite_image = tribe_to_standard[
            army_list[army_no].tribe_id];
        army_list[army_no].sprite_anim = (cnt8 + 0x1a);
        army_list[army_no].sprite_dir  = (get_army_walk_dirc(dir,
            army_list[army_no].target_kind) + 0x42);
    }
}

// FUNCTION: C2 0x48130
// WIN: 0x00408d56
// Lines 1090–1102
//
// Sprite-frame helper for a cohort army.  Computes the walk-direction
// (mod 8 with sign-extension), copies army.cohort_id (+0x28) into
// sprite_image, and picks the per-tick animation: a fixed `+0x12`
// frame when state_idx == 10 (resting?) or `cnt8 + 0x12` otherwise.
void get_cohort_image(void)
{
    int dir;

    dir = army_list[army_no].world_dir - map_direction + 1;
    if (dir < 0)  dir += 8;
    if (dir >= 8) dir %= 8;

    army_list[army_no].sprite_image = army_list[army_no].cohort_id;
    if (army_list[army_no].state_idx == 10)
        army_list[army_no].sprite_anim = 0x12;
    else
        army_list[army_no].sprite_anim = (cnt8 + 0x12);
    army_list[army_no].sprite_dir = (get_army_walk_dirc(dir,
        army_list[army_no].target_kind) + 0x36);
}

// FUNCTION: C2 0x481CE
// WIN: 0x00408e82
// Lines 1105–1119
//
// Map a base heading (`dir`, 0..7) and a rotation hint (`rot`, low
// 2 bits used) to a sprite-frame direction code.
//
//   dir == 0          -> base 6     (south)
//   dir == 4          -> base 0     (north)
//   dir < 4 (1..3)    -> base 9
//   dir > 4 (5..7)    -> base 3
//
// Then `rot &= 3`; if rot == 0 the base is returned unchanged,
// rot == 2 returns base + 2, any other rot (1 or 3) returns base + 1.
int get_army_walk_dirc(int dir, int rot)
{
    int r;
    if (dir == 0)      r = 6;
    else if (dir == 4) r = 0;
    else if (dir < 4)  r = 9;
    else               r = 3;
    rot &= 3;
    if (rot != 0) {
        if (rot == 2) r += rot;
        else          r++;
    }
    return r;
}

// FUNCTION: C2 0x481FF
// WIN: 0x00408f06
// Lines 1121–1141
//
// Scan the citizen list for the nearest enemy citizen (type 3 or 7)
// within a Chebyshev radius of (cx, cy).  Returns the citizen
// index of the best (closest) match, or 0 if none.
//
// Walks indices 0..0xC8 (200 citizens) using the global
// `enemy_citizen` as the loop counter so calls to
// get_longest_distance can re-read the candidate's tile from
// citizen_list[enemy_citizen].x/.y.  Bounding box is clipped to
// [0, 0x4f] (citizen-map width 80).
int find_enemy(int cx, int cy, int r)
{
    int x_lo;
    int x_hi;
    int y_hi;
    int best_idx;
    int best_dist;
    int y_lo;
    int d;

    x_lo = cx - r;        if (x_lo < 0)    x_lo = 0;
    x_hi = cx + r;        if (x_hi >= 0x50) x_hi = 0x4f;
    y_lo = cy - r;        if (y_lo < 0)    y_lo = 0;
    y_hi = cy + r;        if (y_hi >= 0x50) y_hi = 0x4f;
    best_dist = r + 1;
    best_idx = 0;
    for (enemy_citizen = 0; enemy_citizen < 0xc9; enemy_citizen++) {
        if (citizen_list[enemy_citizen].exists == 0) continue; if (citizen_list[enemy_citizen].type != 3 && citizen_list[enemy_citizen].type != 7) continue;
        if (citizen_list[enemy_citizen].x < x_lo || citizen_list[enemy_citizen].x >= x_hi) continue; if (citizen_list[enemy_citizen].y < y_lo || citizen_list[enemy_citizen].y >= y_hi) continue;
        d = get_longest_distance(cx, cy, citizen_list[enemy_citizen].x, citizen_list[enemy_citizen].y);
        if (d < best_dist) { best_dist = d; best_idx = enemy_citizen; }
    }
    return best_idx;
}

// FUNCTION: C2 0x482F1
// WIN: 0x0040910e
// Lines 1144–1163
//
// Region-map twin of find_enemy — scan armies (indices 0..0x19,
// 25 slots) for the nearest invading army within Chebyshev radius
// of (cx, cy).  Filter: army.exists != 0 AND type in [2..5] AND
// state_idx < 14.  Bounding box clipped to [0, 0x3b] (region-map
// width 60).
//
// Returns the army index of the best (closest) match, or 0 if
// none.
int find_invading_army(int cx, int cy, int r)
{
    int x_lo;
    int y_lo;
    int y_hi;
    int x_hi;
    int best_idx;
    int best_dist;
    int xx;
    int yy;
    int d;
    int kind;

    x_lo = cx - r;        if (x_lo < 0)    x_lo = 0;
    x_hi = cx + r;        if (x_hi >= 0x3c) x_hi = 0x3b;
    y_lo = cy - r;        if (y_lo < 0)    y_lo = 0;
    y_hi = cy + r;        if (y_hi >= 0x3c) y_hi = 0x3b;
    best_dist = r + 1;
    best_idx = 0;
    for (enemy_army = 0; enemy_army < 0x1a; enemy_army++) {
        if (army_list[enemy_army].exists == 0) continue;
        kind = army_list[enemy_army].type;
        if (kind < 2 || kind > 5) continue;
        if (army_list[enemy_army].state_idx >= 14) continue;
        xx = army_list[enemy_army].x;
        if (xx < x_lo || xx >= x_hi) continue;
        yy = army_list[enemy_army].y;
        if (yy < y_lo || yy >= y_hi) continue;
        d = get_longest_distance(cx, cy, xx, yy);
        if (d < best_dist) {
            best_dist = d;
            best_idx = enemy_army;
        }
    }
    return best_idx;
}

// FUNCTION: C2 0x483DF
// WIN: 0x00409336
// Lines 1169–1198
//
// Citizen "advance toward target" tick.  Sister of
// citizen_maraude_to_target but for straight-line walks with no
// ferret-run fallback.
//
//   A) flag_bits bit 0 clear: tick the per-type speed gate.
//      After 15 cumulative speed_counts the bit is set so the
//      next call enters B.  Returns 0 in this not-yet-moving case.
//   B) flag_bits bit 0 set: get_heading + try_a_citymap_square.
//      At-target (w_dirc >= 8) clears action_kind and flags arrival;
//      blocked (t > 2, t == 0, or kind == 0 with t == 2) reverses
//      the heading 180 degrees and drops to state 1 with a 0x14-tick
//      wait; otherwise commits the heading and calls move_citizen.
int citizen_go_to_target(int kind)
{
    int t;

    if ((citizen_list[citizen_no].flag_bits & 1) == 0) {
        if (citizen_list[citizen_no].is_barbarian) t = citizen_speed_on_road[citizen_list[citizen_no].type];
        else t = citizen_speed_off_road[citizen_list[citizen_no].type];
        citizen_list[citizen_no].speed_phase = citizen_list[citizen_no].speed_phase + 1;
        if (citizen_list[citizen_no].speed_phase > t) {
            citizen_list[citizen_no].speed_phase = 0; citizen_list[citizen_no].speed_count++; if (citizen_list[citizen_no].speed_count > 0xf) citizen_list[citizen_no].flag_bits |= 1;
        }
        return 0;
    }

    citizen_list[citizen_no].speed_count = 0; citizen_list[citizen_no].speed_phase = 0;
    if (citizen_list[citizen_no].action_kind == 0) return 1;

    w_dirc = (char)get_heading(citizen_list[citizen_no].x,
                               citizen_list[citizen_no].y,
                               citizen_list[citizen_no].dest_x,
                               citizen_list[citizen_no].dest_y,
                               citizen_list[citizen_no].world_dir);
    if (w_dirc >= 8) { citizen_list[citizen_no].action_kind = 0; citizen_list[citizen_no].flag_bits |= 2; return 1; }
    t = try_a_citymap_square(w_dirc, 0, 0);
    if (t > 2) {
        citizen_list[citizen_no].state_idx = 1; citizen_list[citizen_no].wait_count = 0x14; citizen_list[citizen_no].world_dir = (citizen_list[citizen_no].world_dir + 4) & 7;
        return 1;
    }
    if (kind == 0 && t == 2) {
        citizen_list[citizen_no].state_idx = 1; citizen_list[citizen_no].wait_count = 0x14; citizen_list[citizen_no].world_dir = (citizen_list[citizen_no].world_dir + 4) & 7;
        return 1;
    }
    if (t == 0) {
        citizen_list[citizen_no].state_idx = 1; citizen_list[citizen_no].wait_count = 0x14; citizen_list[citizen_no].world_dir = (citizen_list[citizen_no].world_dir + 4) & 7;
        return 1;
    }
    citizen_list[citizen_no].is_barbarian = 1;
    citizen_list[citizen_no].flag_bits &= 0xfe;
    citizen_list[citizen_no].world_dir = w_dirc;
    citizen_list[citizen_no].speed_count = 1;
    move_citizen();
    return 1;
}

// FUNCTION: C2 0x48569
// WIN: 0x00409815
// Lines 1200–1244
//
// Citizen state-handler tail used by s05_maraude_to_top_spot,
// s06_quell_trouble, s09_fire_fight, s12_goto_riot.  Drives a
// citizen toward (dest_x, dest_y) one tile at a time, with a
// per-class speed gate and an optional ferret-run path.
//
//   A) flag_bits bit 0 clear -- speed/phase tick: accumulates
//      speed_phase against citizen_speed_on_road[type] (when
//      on path) or citizen_speed_off_road[type] (when not),
//      rolling into speed_count, and once speed_count exceeds
//      0xF sets the bit so the next call enters B.  Always 1.
//   B) flag_bits bit 0 set -- move step: get_heading + try_a_citymap_square:
//      on arrival, drop to s01_wait; on a 0x3E7 blocked sentinel,
//      rotate world_dir and bounce; on terrain blocked, kick off
//      a fresh clear_ferret_map / run_2_map_ferrets pair against
//      city_map (returning 0 on failure so the caller retries);
//      otherwise commit the heading and call move_citizen.
int citizen_maraude_to_target(int kind)
{
    int result;

    if ((citizen_list[citizen_no].flag_bits & 1) == 0) {
        /* Branch A — speed gate. */
        if (citizen_list[citizen_no].is_barbarian) result = citizen_speed_on_road[citizen_list[citizen_no].type];
        else result = citizen_speed_off_road[citizen_list[citizen_no].type];
        citizen_list[citizen_no].speed_phase = citizen_list[citizen_no].speed_phase + 1;
        if (citizen_list[citizen_no].speed_phase > result) {
            citizen_list[citizen_no].speed_phase = 0; citizen_list[citizen_no].speed_count++; if (citizen_list[citizen_no].speed_count > 0xf) citizen_list[citizen_no].flag_bits |= 1;
        }
        return 1;
    }

    /* Branch B — move step. */
    citizen_list[citizen_no].speed_count = 0; citizen_list[citizen_no].speed_phase = 0;

    if (citizen_list[citizen_no].action_kind == 0) return 1;

    w_dirc = (char)get_heading(
        citizen_list[citizen_no].x,
        citizen_list[citizen_no].y,
        citizen_list[citizen_no].dest_x,
        citizen_list[citizen_no].dest_y,
        citizen_list[citizen_no].world_dir);

    if (w_dirc >= 8) { citizen_list[citizen_no].state_idx = 1; citizen_list[citizen_no].wait_count = 0x78; citizen_list[citizen_no].flag_bits |= 2; return 1; }

    if (citizen_list[citizen_no].wf_active) get_dirc_from_citizen_wf_run();

    result = try_a_citymap_square(w_dirc, kind, 0);

    if (result == 0x3e7 || (result == 0 && citizen_list[citizen_no].wf_active)) {
        /* Blocked or in-wf-run sentinel. */
        citizen_list[citizen_no].world_dir = (char)((citizen_list[citizen_no].world_dir + 1) & 7);
        if (citizen_list[citizen_no].wf_active) citizen_list[citizen_no].wf_active = 0;
        else { citizen_list[citizen_no].state_idx = 1; citizen_list[citizen_no].wait_count = 0x10; }
        return 1;
    }

    if (result == 0) {
        /* Open square, no wf_run yet — kick off a fresh ferret run. */
        citizen_list[citizen_no].wf_active = 0; citizen_list[citizen_no].speed = 0x14;
        clear_ferret_map(citizen_list[citizen_no].speed,
                         (unsigned char *)city_map,
                         0x50, 0x50,
                         0x14,
                         citizen_list[citizen_no].x,
                         citizen_list[citizen_no].y,
                         citizen_list[citizen_no].dest_x,
                         citizen_list[citizen_no].dest_y);
        if (run_2_map_ferrets(citizen_list[citizen_no].speed,
                              (unsigned char *)city_map,
                              0x50, 0x50,
                              0x14,
                              citizen_list[citizen_no].x,
                              citizen_list[citizen_no].y,
                              citizen_list[citizen_no].dest_x,
                              citizen_list[citizen_no].dest_y)
            == 0) {
            /* Run failed — re-target and bail. */
            change_citizen_targs(0x12);
            citizen_list[citizen_no].state_idx = 1; citizen_list[citizen_no].wait_count = 0x14; citizen_list[citizen_no].world_dir = (char)((citizen_list[citizen_no].world_dir + 1) & 7);
            return 0;
        }
        copy_ferret_run_to_citizen();
        return 1;
    }

    /* result != 0 and != 0x3E7 — heading good. */
    if (result == 1) citizen_list[citizen_no].is_barbarian = 1;
    else citizen_list[citizen_no].is_barbarian = 0;
    citizen_list[citizen_no].flag_bits &= 0xfe;
    citizen_list[citizen_no].world_dir = w_dirc;
    citizen_list[citizen_no].speed_count = 1;
    move_citizen();
    return 1;
}

// FUNCTION: C2 0x48847
// WIN: 0x00409ec7
// Lines 1246–1253
//
// Pull the next walking-ferret-run direction for the current citizen.
// `wf_steps[]` packs two 4-bit headings per byte: low nibble for even
// steps, high nibble for odd steps.  When wf_step reaches wf_length,
// clear wf_active and return without advancing.
void get_dirc_from_citizen_wf_run(void)
{
    if (citizen_list[citizen_no].wf_step
        >= citizen_list[citizen_no].wf_length) {
        citizen_list[citizen_no].wf_active = 0;
        return;
    }
    w_dirc = citizen_list[citizen_no].wf_steps[
        citizen_list[citizen_no].wf_step >> 1];
    if ((citizen_list[citizen_no].wf_step & 1) != 0)
        w_dirc >>= 4;
    else
        w_dirc &= 0xf;
    citizen_list[citizen_no].wf_step++;
}

// FUNCTION: C2 0x488BB
// WIN: 0x00409fb6
// Lines 1255–1268
//
// Re-pack `ferret_run[]` (one direction per byte) into the current
// citizen's `wf_steps[]` (4-bit packed: low nibble for even steps,
// high nibble for odd steps).  Activates the run by setting
// wf_active=1 / wf_step=0 / wf_length=ferret_run_length and seeds
// `w_dirc` with the first direction.
void copy_ferret_run_to_citizen(void)
{
    int i, j;
    char step;

    citizen_list[citizen_no].wf_active = 1; citizen_list[citizen_no].wf_step = 0; citizen_list[citizen_no].wf_length = ferret_run_length;
    w_dirc = ferret_run[0];
    i = 0; j = 0;
    for (; i < ferret_run_length; i++) {
        step = ferret_run[i];
        if ((i & 1) == 0) citizen_list[citizen_no].wf_steps[j] = step;
        else { step <<= 4; citizen_list[citizen_no].wf_steps[j] += step; j++; }
    }
}

// FUNCTION: C2 0x48955
// WIN: 0x0040a0c4
// Lines 1270–1314
//
// Per-direction adjacency dispatcher used by the citizen path-
// stepper.  Given a compass `dir` (0..7) and a `kind` flag,
// computes the candidate destination cell's byte-offset from the
// citizen's current map_ref (cell stride 20 bytes, row stride
// 0x640 = 80*20) and forwards to try_this_citymap_square.  Each
// case bails (return 0) when the citizen is at the appropriate
// edge or when dir > 7.  Zeros enemy_figure on every entry.
int try_a_citymap_square(int dir, int kind, int unused)
{
    int r;

    r = 0;
    enemy_figure = 0;

    switch ((unsigned int)dir) {
    case 0:
        if (citizen_list[citizen_no].y <= 0)
            r = 0;
        else
            r = try_this_citymap_square(citizen_list[citizen_no].map_ref - 0x640, kind, unused);
        break;
    case 1:
        if (citizen_list[citizen_no].x < 0x4f) {
            if (citizen_list[citizen_no].y <= 0)
                r = 0;
            else
                r = try_this_citymap_square(citizen_list[citizen_no].map_ref - 0x62c, kind, unused);
        } else {
            r = 0;
        }
        break;
    case 2:
        if (citizen_list[citizen_no].x < 0x4f)
            r = try_this_citymap_square(citizen_list[citizen_no].map_ref + 0x14, kind, unused);
        else
            r = 0;
        break;
    case 3:
        if (citizen_list[citizen_no].x < 0x4f) {
            if (citizen_list[citizen_no].y < 0x4f)
                r = try_this_citymap_square(citizen_list[citizen_no].map_ref + 0x654, kind, unused);
            else
                r = 0;
        } else {
            r = 0;
        }
        break;
    case 4:
        if (citizen_list[citizen_no].y < 0x4f)
            r = try_this_citymap_square(citizen_list[citizen_no].map_ref + 0x640, kind, unused);
        else
            r = 0;
        break;
    case 5:
        if (citizen_list[citizen_no].x <= 0)
            r = 0;
        else if (citizen_list[citizen_no].y < 0x4f)
            r = try_this_citymap_square(citizen_list[citizen_no].map_ref + 0x62c, kind, unused);
        else
            r = 0;
        break;
    case 6:
        if (citizen_list[citizen_no].x <= 0)
            r = 0;
        else
            r = try_this_citymap_square(citizen_list[citizen_no].map_ref - 0x14, kind, unused);
        break;
    case 7:
        if (citizen_list[citizen_no].x <= 0)
            r = 0;
        else if (citizen_list[citizen_no].y <= 0)
            r = 0;
        else
            r = try_this_citymap_square(citizen_list[citizen_no].map_ref - 0x654, kind, unused);
        break;
    }
    return r;
}

// FUNCTION: C2 0x48AEB
// WIN: 0x0040a4c0
// Lines 1317–1365
//
// Per-cell adjacency test used by try_a_citymap_square's path-
// stepper.  `cm_ptr` is the candidate destination cell's byte-
// offset; `kind` is 0 for a standard step or 1 for force-trample.
//
// Returns 0 (OK to step), 1 (impassable terrain), 2 (destroyed
// something), or 0x3E7 (both citizen slots full).  Also runs
// handle_collision on any citizen already in the cell.
//
// In trample mode, ticks the cell's industrial counter and on
// overflow (>12) destroys the atom; cells with terrain bit 0x40 /
// 0x80 set wipe a flag class; otherwise clears the 1x1 area and
// transitions the citizen to s01_wait with a 0x20-tick ferret-run.
int try_this_citymap_square(int cm_ptr, int kind, int third)
{
    unsigned char terrain;
    unsigned char ind;
    int x;
    int y;
    int cell_idx;

    (void)third;
    citizen_a = (short)(unsigned char)(*(struct city_cell *)((unsigned char *)city_map + (cm_ptr))).citizen_a;
    citizen_b = (short)(unsigned char)(*(struct city_cell *)((unsigned char *)city_map + (cm_ptr))).citizen_b;
    terrain   = (*(struct city_cell *)((unsigned char *)city_map + (cm_ptr))).terrain;

    if (citizen_a != 0) handle_collision(citizen_a);
    if (citizen_b != 0) handle_collision(citizen_b);

    if (citizen_a != 0 && citizen_b != 0) return 0x3e7;

    if ((terrain & 0x20) != 0) return 1;

    if (kind != 1) {
        if (terrain == 0) goto ret2;
        return 0;
    }

    /* kind == 1: trample mode.  The return-2 arms funnel to a shared
       tail; the return-0 arms are written self-contained. */
    if ((terrain & 4) != 0) return 0;
    if ((terrain & 0x18) != 0) return 0;

    if ((terrain & 2) != 0) {
        ind = (*(struct city_cell *)((unsigned char *)city_map + (cm_ptr))).industrial;
        ind++;
        if (ind > 0xc) {
            destroy_an_atom(cm_ptr, 0);
            goto ret2;
        }
        (*(struct city_cell *)((unsigned char *)city_map + (cm_ptr))).industrial = ind;
        return 0;
    }

    if (terrain != 0) {
        if ((terrain & 0xc0) != 0) {
            unflag_all_cm(3, 0xdf);
        }

        /* cm_ptr (byte offset) / 20 = cell_idx; / 80 = y, %% 80 = x */
        cell_idx = cm_ptr / 20;
        x = cell_idx % 80;
        y = cell_idx / 80;
        clear_an_area(x, y, x, y);
        setup_map_screen_refresh();
        particles_cleared = 0;
        citizen_list[citizen_no].state_idx = 1;
        citizen_list[citizen_no].wait_count = 0x20;
        citizen_list[citizen_no].wf_active = 1;
        return 0;
    }
    destroy_an_atom(cm_ptr, 0);
    return 2;
ret2:
    return 2;
}

// FUNCTION: C2 0x48C6A
// WIN: 0x0040a702
// Lines 1368–1400
//
// Two citizens have ended up on the same map cell.  Decides what
// happens between the current `citizen_no` (me) and the citizen at
// `other_idx` based on each side's type:
//
//   me            other          action
//   --            -----          ------
//   4/5 (vigile)  3 (barbarian)  → fight_barbarian(other)
//   4/5 (vigile)  7 (cohort)     → other.state_idx = 2 (back off)
//   7 (cohort)    3/4/5          → me.state_idx = 2 (cohort yields)
//   7 (cohort)    != me.type     → other.state_idx = 2 (push aside)
//   3 (barbarian) 4/5 (vigile)   → fight_centurian(other)
//   3 (barbarian) anything-else  → other.state_idx = 2
//   other         3 or 7         → me.state_idx = 2 (yield)
//
// Returns early if me is already in state 2.  No-op for type
// equality of dual cohorts (both 7).
void handle_collision(int other_idx)
{
    int t;

    if (citizen_list[citizen_no].state_idx == 2) return;
    t = citizen_list[citizen_no].type;
    if (t == 4 || t == 5) {
        if (citizen_list[other_idx].type == 3) {
            fight_barbarian(other_idx);
            return;
        }
        if (citizen_list[other_idx].type == 7) {
            citizen_list[other_idx].state_idx = 2;
            return;
        }
        return;
    }
    if (t == 7) {
        if (citizen_list[other_idx].type == 3) {
            citizen_list[citizen_no].state_idx = 2;
            return;
        }
        if (citizen_list[other_idx].type == 4) {
            citizen_list[citizen_no].state_idx = 2;
            return;
        }
        if (citizen_list[other_idx].type == 5) {
            citizen_list[citizen_no].state_idx = 2;
            return;
        }
        if (citizen_list[other_idx].type != t)
            citizen_list[other_idx].state_idx = 2;
        return;
    }
    if (t == 3) {
        if (citizen_list[other_idx].type == t) return;
        if (citizen_list[other_idx].type == 4) {
            fight_centurian(other_idx);
            return;
        }
        if (citizen_list[other_idx].type == 5) {
            fight_centurian(other_idx);
            return;
        }
        citizen_list[other_idx].state_idx = 2;
        return;
    }
    if (citizen_list[other_idx].type == 3) {
        citizen_list[citizen_no].state_idx = 2;
        return;
    }
    if (citizen_list[other_idx].type == 7) {
        citizen_list[citizen_no].state_idx = 2;
        return;
    }
}

// FUNCTION: C2 0x48D32
// WIN: 0x0040aa40
// Lines 1403–1410
//
// Resolve a vigile/centurian vs barbarian skirmish: a coin-flip
// against rand8 decides whether we lose (state_idx = 2) or the
// barbarian loses; either way our XP counter ticks up by 1.
void fight_centurian(int idx)
{
    if (citizen_list[citizen_no].xp + 2 < rand8) citizen_list[idx].state_idx        = 2;
    else                                          citizen_list[citizen_no].state_idx = 2;
    citizen_list[citizen_no].xp += 1;
}

// FUNCTION: C2 0x48D6F
// WIN: 0x0040aac6
// Lines 1412–1419
//
// Mirror of fight_centurian from the barbarian side: the coin-flip
// against rand8 decides whether the centurian (we lose) or the
// barbarian dies, and the barbarian's XP ticks up either way.
void fight_barbarian(int idx)
{
    if (citizen_list[idx].xp + 2 < rand8) citizen_list[citizen_no].state_idx = 2;
    else                                  citizen_list[idx].state_idx        = 2;
    citizen_list[idx].xp += 1;
}

// FUNCTION: C2 0x48DC1
// WIN: 0x0040ab44
// Lines 1421–1474
//
// Move citizen one cell in citizen.world_dir (0..7).  Vacates the
// source cell's slot (citizen_a or citizen_b, whichever holds
// citizen_no), updates citizen.x / y / map_ref via the 8-way
// direction table (cell stride 20 bytes, row stride 0x640 = 80*20),
// then claims a slot in the new cell.  If both slots in the new
// cell are occupied the citizen is despawned (high_beep +
// remove_citizen).
void move_citizen(void)
{
    int cm;

    cm = citizen_list[citizen_no].map_ref;
    if ((*(struct city_cell *)((unsigned char *)city_map + (cm))).citizen_a == citizen_no) {
        (*(struct city_cell *)((unsigned char *)city_map + (cm))).citizen_a = 0;
    } else if ((*(struct city_cell *)((unsigned char *)city_map + (cm))).citizen_b == citizen_no) {
        (*(struct city_cell *)((unsigned char *)city_map + (cm))).citizen_b = 0;
    }

    switch ((unsigned char)citizen_list[citizen_no].world_dir) {
    case 0:
        citizen_list[citizen_no].y--;
        citizen_list[citizen_no].map_ref -= 0x640;
        break;
    case 1:
        citizen_list[citizen_no].y--;
        citizen_list[citizen_no].x++;
        citizen_list[citizen_no].map_ref -= 0x62c;
        break;
    case 2:
        citizen_list[citizen_no].x++;
        citizen_list[citizen_no].map_ref += 0x14;
        break;
    case 3:
        citizen_list[citizen_no].y++;
        citizen_list[citizen_no].x++;
        citizen_list[citizen_no].map_ref += 0x654;
        break;
    case 4:
        citizen_list[citizen_no].y++;
        citizen_list[citizen_no].map_ref += 0x640;
        break;
    case 5:
        citizen_list[citizen_no].y++;
        citizen_list[citizen_no].x--;
        citizen_list[citizen_no].map_ref += 0x62c;
        break;
    case 6:
        citizen_list[citizen_no].x--;
        citizen_list[citizen_no].map_ref -= 0x14;
        break;
    case 7:
        citizen_list[citizen_no].y--;
        citizen_list[citizen_no].x--;
        citizen_list[citizen_no].map_ref -= 0x654;
        break;
    default:
        return;
    }

    cm = citizen_list[citizen_no].map_ref;
    if ((*(struct city_cell *)((unsigned char *)city_map + (cm))).citizen_a == 0) {
        (*(struct city_cell *)((unsigned char *)city_map + (cm))).citizen_a = citizen_no;
        return;
    }
    if ((*(struct city_cell *)((unsigned char *)city_map + (cm))).citizen_b == 0) {
        (*(struct city_cell *)((unsigned char *)city_map + (cm))).citizen_b = citizen_no;
        return;
    }
    high_beep();
    remove_citizen(citizen_no);
}

// FUNCTION: C2 0x48F2E
// WIN: 0x0040af92
// Lines 1476–1505
//
// Re-bound the current citizen's wander target so it sits within
// `delta` cells of the citizen on each axis.  Algorithm:
//
//   1.  X axis: if dest_x > x + delta clamp east; else if
//       dest_x < x - delta clamp west; else mark the X axis
//       "in range".
//   2.  Y axis: same shape, marking Y axis "in range".
//   3.  If BOTH axes were already in range:
//          - peek at the city_map cell at (dest_x, dest_y).
//            Field +1 (after &0xDF) holds occupancy bits.
//          - if the cell is empty → call random_target() to
//            pick a fresh wander destination.
//          - else nudge dest one step toward home (so we don't
//            stand on whatever's blocking the cell).
//   4.  Finally clamp dest_{x,y} to [0, 0x4F] (city is 80×80).
//
void change_citizen_targs(int delta)
{
    int unclamped = 2;            /* hits 0 only when both axes are within delta */
    int cell_idx;

    /* ---- X axis ---- */
    if (citizen_list[citizen_no].dest_x >
        citizen_list[citizen_no].x + delta) {
        citizen_list[citizen_no].dest_x =
            citizen_list[citizen_no].x + delta;
    } else if (citizen_list[citizen_no].dest_x <
               citizen_list[citizen_no].x - delta) {
        citizen_list[citizen_no].dest_x =
            citizen_list[citizen_no].x - delta;
    } else {
        unclamped = 1;
    }

    /* ---- Y axis ---- */
    if (citizen_list[citizen_no].dest_y >
        citizen_list[citizen_no].y + delta) {
        citizen_list[citizen_no].dest_y =
            citizen_list[citizen_no].y + delta;
    } else if (citizen_list[citizen_no].dest_y <
               citizen_list[citizen_no].y - delta) {
        citizen_list[citizen_no].dest_y =
            citizen_list[citizen_no].y - delta;
    } else {
        unclamped--;
    }

    /* ---- Cell occupancy nudge / random retarget ---- */
    if (unclamped == 0) {
        cell_idx = citizen_list[citizen_no].dest_x
                 + citizen_list[citizen_no].dest_y * 80;
        if (((*(struct city_cell *)((unsigned char *)city_map + ((cell_idx * CITY_CELL_BYTES)))).terrain & 0xDF) != 0) {
            /* Cell is non-empty — step target back one tile
             * toward home on whichever axis still differs. */
            if (citizen_list[citizen_no].dest_x >
                citizen_list[citizen_no].x)
                citizen_list[citizen_no].dest_x--;
            if (citizen_list[citizen_no].dest_x <
                citizen_list[citizen_no].x)
                citizen_list[citizen_no].dest_x++;
            if (citizen_list[citizen_no].dest_y >
                citizen_list[citizen_no].y)
                citizen_list[citizen_no].dest_y--;
            if (citizen_list[citizen_no].dest_y <
                citizen_list[citizen_no].y)
                citizen_list[citizen_no].dest_y++;
        } else {
            random_target();
        }
    }

    /* ---- Final 0..0x4F clamp ---- */
    if (citizen_list[citizen_no].dest_x < 0)
        citizen_list[citizen_no].dest_x = 0;
    if (citizen_list[citizen_no].dest_x > 0x4f)
        citizen_list[citizen_no].dest_x = 0x4f;
    if (citizen_list[citizen_no].dest_y < 0)
        citizen_list[citizen_no].dest_y = 0;
    if (citizen_list[citizen_no].dest_y > 0x4f)
        citizen_list[citizen_no].dest_y = 0x4f;
}

// FUNCTION: C2 0x4910B
// WIN: 0x0040b422
// Lines 1508–1514
//
// Pull the current citizen's wander target a few steps closer to home,
// with a small per-axis random jitter.  Independently per X/Y:
//   * if dest > home, set dest = home + rand8 - 3 (or -2 for Y);
//   * else                  set dest = home + rand8 - 5 (or -6 for Y).
// The `else if (dest <= home)` form (rather than a plain `else`)
// is the original source shape.
void random_target(void)
{
    if (citizen_list[citizen_no].dest_x > citizen_list[citizen_no].x)
        citizen_list[citizen_no].dest_x =
            citizen_list[citizen_no].x + rand8 - 3;
    else if (citizen_list[citizen_no].dest_x <= citizen_list[citizen_no].x)
        citizen_list[citizen_no].dest_x =
            citizen_list[citizen_no].x + rand8 - 5;
    if (citizen_list[citizen_no].dest_y > citizen_list[citizen_no].y)
        citizen_list[citizen_no].dest_y =
            citizen_list[citizen_no].y + rand8 - 2;
    else if (citizen_list[citizen_no].dest_y <= citizen_list[citizen_no].y)
        citizen_list[citizen_no].dest_y =
            citizen_list[citizen_no].y + rand8 - 6;
}

// FUNCTION: C2 0x49184
// WIN: 0x0040b607
// Lines 1516–1593
//
// Citizen path-finder helper: pick a road direction off the current
// city_map cell, biased toward roads with no other citizens.
// `map_ref` is the byte-offset form of the cell index.
//
// Walks the four cardinal neighbours (N/E/S/W), stashing each road
// tile's (present, citizen_a, citizen_b) into a per-direction slot.
// (The south neighbour reads citizen_a into both bytes, an original
// source quirk preserved here.)  Picks a random even direction as
// the scan seed and a `forbidden` direction = world_dir + 4 (don't
// turn back).  No roads available returns 8; exactly one road
// returns it; multiple roads with an empty one available scans for
// an empty + non-forbidden hit; otherwise falls back to any non-
// forbidden road.  Final fallthrough returns 8.
int city_test_for_road(int x, int y, int map_ref, signed char world_dir)
{
    unsigned char slots[8][3];
    signed char forbidden;
    signed char rand_dir;
    int i;
    int n_present;
    int n_empty;

    for (i = 0; i < 8; i += 2) slots[i][0] = slots[i][1] = slots[i][2] = 0;
    forbidden = ((char)world_dir + 4) & 7;

    if (y > 0) {
        if ((*(struct city_cell *)((unsigned char *)city_map + ((map_ref - 1600)))).terrain & 0x20) {
            slots[0][0] = 1;
            slots[0][1] = (*(struct city_cell *)((unsigned char *)city_map + ((map_ref - 1600)))).citizen_a;
            slots[0][2] = (*(struct city_cell *)((unsigned char *)city_map + ((map_ref - 1600)))).citizen_b;
        }
    }
    if (x < 0x4f) {
        if ((*(struct city_cell *)((unsigned char *)city_map + ((map_ref + 20)))).terrain & 0x20) {
            slots[2][0] = 1;
            slots[2][1] = (*(struct city_cell *)((unsigned char *)city_map + ((map_ref + 20)))).citizen_a;
            slots[2][2] = (*(struct city_cell *)((unsigned char *)city_map + ((map_ref + 20)))).citizen_b;
        }
    }
    if (y < 0x4f) {
        if ((*(struct city_cell *)((unsigned char *)city_map + ((map_ref + 1600)))).terrain & 0x20) {
            slots[4][0] = 1;
            /* South cell reads citizen_a into both bytes (original source quirk). */
            slots[4][1] = (*(struct city_cell *)((unsigned char *)city_map + ((map_ref + 1600)))).citizen_a;
            slots[4][2] = (*(struct city_cell *)((unsigned char *)city_map + ((map_ref + 1600)))).citizen_a;
        }
    }
    if (x > 0) {
        if ((*(struct city_cell *)((unsigned char *)city_map + ((map_ref - 20)))).terrain & 0x20) {
            slots[6][0] = 1;
            slots[6][1] = (*(struct city_cell *)((unsigned char *)city_map + ((map_ref - 20)))).citizen_a;
            slots[6][2] = (*(struct city_cell *)((unsigned char *)city_map + ((map_ref - 20)))).citizen_b;
        }
    }

    n_present = 0; n_empty = 0;
    for (i = 0; i < 8; i += 2) {
        if (slots[i][0] == 0) continue;
        n_present++; if (slots[i][1] != 0) continue; if (slots[i][2] != 0) continue; n_empty++;
    }

    rand_dir = (unsigned char)rand8 & 6;
    if (n_present != 0) {
        if (n_present == 1) {
            for (i = 0; i < 8; i += 2) if (slots[i][0] != 0) return i;
        }
        if (n_empty != 0) {
            for (i = 0; i < 4; i++) {
                if (slots[rand_dir][0] != 0) {
                    if (slots[rand_dir][1] == 0 && slots[rand_dir][2] == 0) {
                        if (rand_dir != forbidden) return rand_dir;
                    }
                }
                rand_dir += 2;
                if (rand_dir > 6) rand_dir = 0;
            }
        }
        for (i = 0; i < 4; i++) {
            if (slots[rand_dir][0] != 0) {
                if (rand_dir != forbidden) return rand_dir;
            }
            rand_dir += 2;
            if (rand_dir > 6) rand_dir = 0;
        }
    }
    return 8;
}

// FUNCTION: C2 0x4933E
// WIN: 0x0040b930
// Lines 1596–1606
//
// Set citizen.dest_x / dest_y to the city-map tile adjacent to the
// current citizen in the given direction.  Compass mapping (game-
// world; 0=N, 1=NE, 2=E, … clockwise; rotated 45° for "diagonal"
// 1/3/5/7):
//
//   0  N  → ( x  , y-1)        4  S  → ( x  , y+1)
//   1  NE → (x+1 , y-1)        5  SW → (x-1 , y+1)
//   2  E  → (x+1 , y  )        6  W  → (x-1 , y  )
//   3  SE → (x+1 , y+1)        7  NW → (x-1 , y-1)
//
// PS lays this out as an if-else chain in dir order 0,2,4,6,1,3,5,7
// (cardinals first, then diagonals).
void target_from_dirc(int dir)
{
    if (dir == 0) {
        citizen_list[citizen_no].dest_x = citizen_list[citizen_no].x;
        citizen_list[citizen_no].dest_y = citizen_list[citizen_no].y - 1;
    } else if (dir == 2) {
        citizen_list[citizen_no].dest_x = citizen_list[citizen_no].x + 1;
        citizen_list[citizen_no].dest_y = citizen_list[citizen_no].y;
    } else if (dir == 4) {
        citizen_list[citizen_no].dest_x = citizen_list[citizen_no].x;
        citizen_list[citizen_no].dest_y = citizen_list[citizen_no].y + 1;
    } else if (dir == 6) {
        citizen_list[citizen_no].dest_x = citizen_list[citizen_no].x - 1;
        citizen_list[citizen_no].dest_y = citizen_list[citizen_no].y;
    } else if (dir == 1) {
        citizen_list[citizen_no].dest_x = citizen_list[citizen_no].x + 1;
        citizen_list[citizen_no].dest_y = citizen_list[citizen_no].y - 1;
    } else if (dir == 3) {
        citizen_list[citizen_no].dest_x = citizen_list[citizen_no].x + 1;
        citizen_list[citizen_no].dest_y = citizen_list[citizen_no].y + 1;
    } else if (dir == 5) {
        citizen_list[citizen_no].dest_x = citizen_list[citizen_no].x - 1;
        citizen_list[citizen_no].dest_y = citizen_list[citizen_no].y + 1;
    } else if (dir == 7) {
        citizen_list[citizen_no].dest_x = citizen_list[citizen_no].x - 1;
        citizen_list[citizen_no].dest_y = citizen_list[citizen_no].y - 1;
    }
}

// FUNCTION: C2 0x4944A
// WIN: 0x0040bcc6
// Lines 1611–1618
//
// Test whether the current army has just entered a new square that
// should trigger a path-find/walk-state event.  Returns 1 if either:
//   * the army's flag bit 0 is set (always-trigger flag), or
//   * its target_count is at least the threshold (2 when target_flag
//     is clear, 1 otherwise) AND target_kind is at saturation (>= 15).
// Otherwise returns 0.
int entering_new_square(void)
{
    int threshold;
    if ((army_list[army_no].flags & 1) != 0) return 1;
    if (army_list[army_no].target_flag) threshold = 1;
    else threshold = 2;
    if (army_list[army_no].target_count >= threshold
     && army_list[army_no].target_kind >= 15)
        return 1;
    return 0;
}


// FUNCTION: C2 0x494AC
// WIN: 0x0040bd88
// Lines 1620–1691
//
// Army analogue of citizen_maraude_to_target.  Drives the current
// army one tile toward `(target_x, target_y)` per call, gated by a
// per-type speed counter and with an optional region-ferret pathing
// pass when the straight step is blocked.  Two halves:
//
//   A) `flags & 1 == 0` -- speed gate (speed = 2 for cohorts with
//      a target, 3 for non-cohorts).  Bumps target_count; on
//      overflow rolls into target_kind, on saturation (>0xF) sets
//      `flags & 1` so the next call enters branch B.  Always 0.
//   B) `flags & 1 == 1` -- move step.  get_heading + try_a_regionmap_square:
//      0x3E7 blocked -> wait + rotate world_dir; 0 (terrain blocks)
//      kicks off a ferret-run path, with cohort failure handing off
//      to sa08_army_stuck and non-cohort failure either firing a
//      siege message (state 9) or dropping to state 2; any other
//      result commits the move via move_army().
int region_go_to_target(int kind)
{
    int speed;
    int result;
    signed char gate;
    (void)kind;

    gate = army_list[army_no].flags & 1;
    army_list[army_no].flags &= 0xf7;
    speed = gate;
    if (speed != 0) {
        /* Branch B initial — clear the gate counters. */
        army_list[army_no].target_kind = 0;
        army_list[army_no].target_count = 0;
    } else {
        /* Branch A — speed gate. */
        if (army_list[army_no].target_flag == 0) {
            if (army_list[army_no].type == 1)
                speed = 2;
            else
                speed = 3;
        }
        army_list[army_no].target_count++;
        if (army_list[army_no].target_count > speed) {
            army_list[army_no].target_count = 0;
            army_list[army_no].target_kind++;
            if (army_list[army_no].target_kind > 0xf) {
                army_list[army_no].flags |= 1;
                army_list[army_no].target_kind = 0;
                goto branch_b;
            }
        }
        return 0;
    branch_b: ;
        /* fall through to branch B */
    }

    /* Branch B body. */
    if (army_list[army_no].return_flag == 0) {
        return 1;
    }

    w_dirc = (char)get_heading(
        army_list[army_no].x,
        army_list[army_no].y,
        army_list[army_no].target_x,
        army_list[army_no].target_y,
        army_list[army_no].world_dir);

    if (w_dirc >= 8) {
        army_list[army_no].return_flag = 0;
        army_list[army_no].flags |= 2;
        return 1;
    }

    if (army_list[army_no].wf_active) {
        get_dirc_from_army_wf_run();
    }

    result = try_a_regionmap_square(w_dirc, 0, 0);

    if (result == 0x3e7) {
        if (army_list[army_no].state_idx == 2) return 0;
        army_list[army_no].saved_state_idx =
            army_list[army_no].state_idx;
        army_list[army_no].state_idx = 1;
        army_list[army_no].wait_count = 5;
        army_list[army_no].world_dir =
            (army_list[army_no].world_dir + 1) & 7;
        return 0;
    }

    if (result == 0) {
        army_list[army_no].wf_active = 0;
        if (army_list[army_no].state_idx == 8) return 1;

        clear_region_ferret_map(0, 0x3c,
                                (unsigned char *)region_map,
                                0x3c, 0x3c, 8,
                                army_list[army_no].x,
                                army_list[army_no].y,
                                army_list[army_no].target_x,
                                army_list[army_no].target_y);
        if (run_2_map_ferrets(0x3c,
                              (unsigned char *)region_map,
                              0x3c, 0x3c, 8,
                              army_list[army_no].x,
                              army_list[army_no].y,
                              army_list[army_no].target_x,
                              army_list[army_no].target_y)
            == 0) {
            /* Pathfind failed. */
            if (army_list[army_no].type == 1) {
                /* Cohort: hand off to sa08_army_stuck. */
                army_list[army_no].saved_state_idx =
                    army_list[army_no].state_idx;
                army_list[army_no].state_idx = 8;
                army_list[army_no].stuck_timer = 0;
                return 0;
            }
            if (army_list[army_no].flags & 8) {
                army_list[army_no].state_idx = 9;
                army_list[army_no].stuck_timer = 0;
                army_list[army_no].wf_phase = 0;
                put_message(0x5f, army_list[army_no].map_ref, 0x12);
                return 0;
            }
            /* Retry with mode=1. */
            clear_region_ferret_map(1, 0x3c,
                                    (unsigned char *)region_map,
                                    0x3c, 0x3c, 8,
                                    army_list[army_no].x,
                                    army_list[army_no].y,
                                    army_list[army_no].target_x,
                                    army_list[army_no].target_y);
            if (run_2_map_ferrets(0x3c,
                                  (unsigned char *)region_map,
                                  0x3c, 0x3c, 8,
                                  army_list[army_no].x,
                                  army_list[army_no].y,
                                  army_list[army_no].target_x,
                                  army_list[army_no].target_y)
                == 0) {
                army_list[army_no].state_idx = 2;
                return 0;
            }
            copy_ferret_run_to_army();
            return 0;
        }
        copy_ferret_run_to_army();
        return 0;
    }

    /* result != 0 and != 0x3E7 — heading good. */
    if (result == 1)
        army_list[army_no].target_flag = 1;
    else
        army_list[army_no].target_flag = 0;

    /* Move tail. */
    army_list[army_no].flags &= 0xfe;
    army_list[army_no].world_dir = w_dirc;
    army_list[army_no].target_kind = 1;
    move_army();
    return 1;
}

// FUNCTION: C2 0x4987B
// WIN: 0x0040c603
// Lines 1694–1740
//
// Sea-army analogue of region_go_to_target.  Drives the current
// sailing army one tile toward (target_x, target_y) per call.
// Same flag-gated speed/phase counter (threshold hard-coded to 2,
// no per-type branch).  The arg `kind` is unused.
//
// Branch A (flags bit 0 clear): tick the speed gate; on overflow
// roll into target_kind and on saturation flip the bit and fall
// through to branch B.
// Branch B (flags bit 0 set): get_heading + try_a_seamap_square.
// On arrival drop return_flag and flag flags bit 1.  0x3E7 (deep
// sea blocked) or any non-1 result kicks off a ferret-run path on
// region_map: failure returns 1 (army is done), success calls
// copy_ferret_run_to_army and returns 0.  result == 1 commits the
// move via move_army().
int sail_to_target(int kind)
{
    int result;
    (void)kind;

    /* Mask: clear flags & {2, 3} on every entry. */
    army_list[army_no].flags &= 0xf3;

    if ((army_list[army_no].flags & 1) != 0) {
        /* Branch B initial — reset gate counters. */
        army_list[army_no].target_kind = 0;
        army_list[army_no].target_count = 0;
    } else {
        /* Branch A — speed gate (threshold = 2). */
        army_list[army_no].target_count++;
        if (army_list[army_no].target_count > 2) {
            army_list[army_no].target_count = 0;
            army_list[army_no].target_kind++;
            if (army_list[army_no].target_kind <= 0xf) {
                return 0;
            }
            army_list[army_no].flags |= 1;
            army_list[army_no].target_kind = 0;
            /* fall through */
        } else {
            return 0;
        }
    }

    /* Branch B body. */
    if (army_list[army_no].return_flag == 0) {
        return 1;
    }

    w_dirc = (char)get_heading(
        army_list[army_no].x,
        army_list[army_no].y,
        army_list[army_no].target_x,
        army_list[army_no].target_y,
        army_list[army_no].world_dir);

    if (w_dirc >= 8) {
        army_list[army_no].return_flag = 0;
        army_list[army_no].flags |= 2;
        return 1;
    }

    if (army_list[army_no].wf_active) {
        get_dirc_from_army_wf_run();
    }

    result = try_a_seamap_square(w_dirc, 0, 0);

    if (result == 0x3e7) {
        army_list[army_no].flags |= 4;
        /* fall through to ferret-run */
    }

    if (result != 1) {
        /* result == 0 or 0x3E7 or other → ferret-run path. */
        army_list[army_no].wf_active = 0;
        clear_sea_ferret_map(0, 0x3c,
                             (unsigned char *)region_map,
                             0x3c, 0x3c, 8,
                             army_list[army_no].x,
                             army_list[army_no].y,
                             army_list[army_no].target_x,
                             army_list[army_no].target_y);
        if (run_2_map_ferrets(0x3c,
                              (unsigned char *)region_map,
                              0x3c, 0x3c, 8,
                              army_list[army_no].x,
                              army_list[army_no].y,
                              army_list[army_no].target_x,
                              army_list[army_no].target_y)
            == 0) {
            return 1;
        }
        copy_ferret_run_to_army();
        return 0;
    }

    /* Move tail (result == 1). */
    army_list[army_no].target_flag = 0;
    army_list[army_no].flags &= 0xfe;
    army_list[army_no].world_dir = w_dirc;
    army_list[army_no].target_kind = 1;
    move_army();
    return 1;
}

// FUNCTION: C2 0x49A96
// WIN: 0x0040cb2d
// Lines 1743–1750
//
// Pull the next walking-ferret-run direction for the current army.
// Identical structure to `get_dirc_from_citizen_wf_run`: `wf_steps[]`
// packs two 4-bit headings per byte; when wf_step reaches wf_length,
// clear wf_active and return without advancing.
void get_dirc_from_army_wf_run(void)
{
    if (army_list[army_no].wf_step
        >= army_list[army_no].wf_length) {
        army_list[army_no].wf_active = 0;
        return;
    }
    w_dirc = army_list[army_no].wf_steps[
        army_list[army_no].wf_step >> 1];
    if ((army_list[army_no].wf_step & 1) != 0)
        w_dirc >>= 4;
    else
        w_dirc &= 0xf;
    army_list[army_no].wf_step++;
}

// FUNCTION: C2 0x49B10
// WIN: 0x0040cc1f
// Lines 1752–1765
//
// Re-pack `ferret_run[]` (one direction per byte) into the current
// army's `wf_steps[]` (4-bit packed: low nibble for even steps, high
// nibble for odd steps).  Twin of `copy_ferret_run_to_citizen`.
void copy_ferret_run_to_army(void)
{
    int i, j;
    char step;

    army_list[army_no].wf_active = 1; army_list[army_no].wf_step = 0; army_list[army_no].wf_length = ferret_run_length;
    w_dirc = ferret_run[0];
    i = 0; j = 0;
    for (; i < ferret_run_length; i++) {
        step = ferret_run[i];
        if ((i & 1) == 0) army_list[army_no].wf_steps[j] = step;
        else { step <<= 4; army_list[army_no].wf_steps[j] += step; j++; }
    }
}

// FUNCTION: C2 0x49BB1
// WIN: 0x0040cd36
// Lines 1767–1811
//
// Region-map move primitive: given an absolute compass `dir`
// (0..7), check whether the army can step into that neighbour of
// its current cell, and if so call try_this_regionmap_square with
// the candidate cell offset.  Region cells are 8 bytes wide on a
// 60x60 grid (row stride 0x1E0).  Each case bails (return 0) when
// the army is at the appropriate edge.  Clears `enemy_figure` on
// every entry; `kind` and `third` are passed through unchanged.
int try_a_regionmap_square(int dir, int kind, int third)
{
    int r;

    r = 0;
    enemy_figure = 0;
    switch ((unsigned int)dir) {
    case 0:                                /* N */
        if (army_list[army_no].y <= 0)
            r = 0;
        else
            r = try_this_regionmap_square(army_list[army_no].map_ref - 0x1e0, kind, third);
        break;
    case 1:                                /* NE */
        if (army_list[army_no].x < 0x3b) {
            if (army_list[army_no].y <= 0)
                r = 0;
            else
                r = try_this_regionmap_square(army_list[army_no].map_ref - 0x1d8, kind, third);
        } else {
            r = 0;
        }
        break;
    case 2:                                /* E */
        if (army_list[army_no].x < 0x3b)
            r = try_this_regionmap_square(army_list[army_no].map_ref + 8, kind, third);
        else
            r = 0;
        break;
    case 3:                                /* SE */
        if (army_list[army_no].x < 0x3b) {
            if (army_list[army_no].y < 0x3b)
                r = try_this_regionmap_square(army_list[army_no].map_ref + 0x1e8, kind, third);
            else
                r = 0;
        } else {
            r = 0;
        }
        break;
    case 4:                                /* S */
        if (army_list[army_no].y < 0x3b)
            r = try_this_regionmap_square(army_list[army_no].map_ref + 0x1e0, kind, third);
        else
            r = 0;
        break;
    case 5:                                /* SW */
        if (army_list[army_no].x <= 0)
            r = 0;
        else if (army_list[army_no].y < 0x3b)
            r = try_this_regionmap_square(army_list[army_no].map_ref + 0x1d8, kind, third);
        else
            r = 0;
        break;
    case 6:                                /* W */
        if (army_list[army_no].x <= 0)
            r = 0;
        else
            r = try_this_regionmap_square(army_list[army_no].map_ref - 8, kind, third);
        break;
    case 7:                                /* NW */
        if (army_list[army_no].x <= 0)
            r = 0;
        else if (army_list[army_no].y <= 0)
            r = 0;
        else
            r = try_this_regionmap_square(army_list[army_no].map_ref - 0x1e8, kind, third);
        break;
    }
    return r;
}

// FUNCTION: C2 0x49D62
// WIN: 0x0040d132
// Lines 1814–1927
//
// Per-cell admission test for a region-map step.  Decides what
// happens if the current army moves into the cell at byte-offset
// `target` in region_map; `kind` and `third` are unused.
//
// Returns 0 when the step is handled (battle setup, message,
// passive type) or the cell is open and benign; 1 when the cell
// is open with the warehouse/landfall bit; 2 when the cell is
// blocked; 0x3E7 as a combat-blocking sentinel.
//
// Outer dispatch is on `army.type`:
//   - type == 1 (Roman cohort): occupied cells either trigger a
//     battle vs the occupant or refuse (vs ally).  Impassable
//     settlement tiles (base_kind 0x93..0x96) prompt the player
//     for an assault.
//   - 2..5 (barbarian / raider): occupied cells just return 0;
//     settlement tiles trigger barbarian_invades_city, upgrade
//     tile 0x97 to 0x93, or destroy the tile; pax_romanum is
//     deducted per event class.
//   - otherwise: passive (return 0).
//
// OPEN: 6 bytes at +0x167..+0x186 (evidence as of 2026-07-04; only
// byte-exact closes this) -- the
// L1847 `target_y = .y` copy's two anon army_no*0xaf index temps get
// EAX(src)/EDX(dest) in PS but EDX(src)/EAX(dest) here.  regtrace
// verdict CLEAN (294 reg-operands: named seats/types/frame all agree);
// the pair sits in the 42-member anon ConfBefore tie group whose order
// is the FE name-POINTER (allocation address) -- no named-local handle.
// Exhaustively probed via forge (docs/codegen-experiments/ttrs-*.py:
// retmix 695 plans, mixmask 260 name/inline/decl variants, slotperm
// 143, packing/targpair/nameheap/splitcopy 53): no source form flips
// the pair without regressing slots.  MECHANICAL PROOF (offline
// ShellSort replay, byte-exact vs the traced postsort): the two
// stmt2 index temps sit at adjacent creation slots (LHS-addr temp
// first, RHS second -- the FE's fixed assignment processing order);
// the flip needs that order swapped, and every syntactic form of the
// statement (casts, *(&...) derefs on either side, +0, split into
// `t = .y; target_y = t;`) normalizes to the IDENTICAL conflict
// list (traced: same node at the same presort slot), while a named
// byte temp spills (764bd).  Note stmt1 has the SAME queue pattern
// yet PS-matching seats -- the divergence is below the conflict
// queue.  CRM-chain chase (2026-07-04, probed): the pair's seats are
// CountRegMoves-driven -- each movsx temp scores EDX=2/EAX=2 from its
// OP_MUL (*0xaf) result temp's already-assigned seat, and those
// mul-temps inherit through the 42-member anon tie group in QUEUE
// order (reverse parse order: the DECLINE-path and blocked-tail
// sibling pairs' temps allocate BEFORE the accept pair and seed its
// EDX preference; the chain's root, the route-loop base temp
// sav=110->EDX, matches PS).  12 manual swap probes on the seeding
// statements (dest_x/dest_y order, chained zeros, pair swaps in all
// three sites, cast/paren forms of every upstream byte op) are ALL
// IL-invariant (identical bytes at identical offsets -- Watcom
// canonicalizes them) or catastrophic (chain-assign 766bd).  The
// divergence enters mid-chain with no reachable source handle found
// yet.  Run-ledger 244/252
// register-blind; the
// only ledger island is try_a_seamap_square's switch table decode
// (data, zero diff bytes).  Everything else in this 1107b function is
// byte-exact, incl. the corpus-unique framed mid-function epilogue at
// +0x217 (see ~watcom10.0a/probes/framed-epilogue/) which lands from
// `ret0: return 0;` inside the &1-arm + `goto ret999;` as the final
// statement.  The (int) casts on the mask tests are load-bearing:
// they keep the spilled byte temps' zext-reload test form (mov al,
// [esp+N]; test eax,eax) that inline/plain-uchar forms lose.
int try_this_regionmap_square(int target, int kind, int third)
{
    unsigned char terr_bit_1;
    unsigned char terrain;
    unsigned char terr_bit_4;
    unsigned char terr_bit_2;
    unsigned char base_kind;
    int type;
    unsigned char terr_bit_20;
    int i;

    (void)kind; (void)third;

    army_a      = (short)(*(struct region_cell *)((unsigned char *)region_map + (target))).occupant;
    terrain     = (*(struct region_cell *)((unsigned char *)region_map + (target))).terrain;
    type        = army_list[army_no].type;

    terr_bit_2  = terrain & 2;
    terr_bit_20 = terrain & 0x20;
    terr_bit_4  = terrain & 4;
    terr_bit_1  = terrain & 1;

    if (type == 1) {
        /* --- Branch A: Roman main army. --- */
        if ((terrain & 0x10) != 0) {
            if (army_a == 0) goto ret0;
            if (army_list[army_a].state_idx == 2) goto ret0;
            if (army_list[army_a].type != type) { get_contenders(); game_state = 4; battle_type = type; }
            goto ret999;
        }
        if ((int)terr_bit_1) {
            base_kind = (*(struct region_cell *)((unsigned char *)region_map + (target))).base_kind;
            if (base_kind >= 0x93 && base_kind <= 0x96) {
                /* Inline confirm() prompt for settlement battle. */
                confirm(9, 0xa0, 0xa0);
                if (decision == 1) {
                    battle_type   = 2;
                    battle2_ptr   = target;
                    get_villagers(base_kind - 0x92);
                    game_state    = 4;
                    army_list[army_no].target_x = army_list[army_no].x;
                    army_list[army_no].target_y = army_list[army_no].y;
                }
                else {
                    /* Decline: reset army's per-route walk cursor (but keep
                       cohort_id so the loop below clears the right route). */
                    army_list[army_no].dest_y = 0;
                    army_list[army_no].dest_x = 0;
                    for (i = 0; i < 10; i++) {
                        army_routes[army_list[army_no].cohort_id].row_len[i] = 0;
                    }
                    army_routes[army_list[army_no].cohort_id].row_count = 0;
                    army_routes[army_list[army_no].cohort_id].chase_row = 0;
                    army_routes[army_list[army_no].cohort_id].target_army = 0;
                    army_list[army_no].target_x = army_list[army_no].x;
                    army_list[army_no].target_y = army_list[army_no].y;
                    army_list[army_no].order_progress = 0;
                }
            }
ret0:
            return 0;
        }
        if ((int)terr_bit_4) return 2;
        if (army_a == 0) {
            if ((int)terr_bit_20) return 1;
            if ((int)terr_bit_2) return 0;
            return 2;
        }
        /* army_a != 0: battle/contender check. */
        if (army_list[army_a].type != 1) {
            if (army_list[army_a].state_idx == 2) return 0;
            get_contenders(); game_state = 4; battle_type = 1;
        }
ret999:
        return 0x3e7;
    }

    if (type < 2 || type > 5) return 0;

    /* --- Branch B: barbarian / raider (type 2..5). --- */
    if ((terrain & 0x10) != 0) return 0;
    if ((int)terr_bit_2) {
        army_list[army_no].flags |= 8;
        return 0;
    }
    if ((int)terr_bit_1) {
        base_kind = (*(struct region_cell *)((unsigned char *)region_map + (target))).base_kind;
        if (base_kind >= 0x93 && base_kind <= 0x96) return 0;
        if (base_kind == 0x92) {
            barbarian_invades_city(army_no);
            army_list[army_no].state_idx = 2;
            return 0;
        }
        if (base_kind == 0x97) {
            (*(struct region_cell *)((unsigned char *)region_map + (target))).base_kind = 0x93;
            (*(struct region_cell *)((unsigned char *)region_map + (target))).gfx = 0x2e;
            army_list[army_no].state_idx = 2;
            put_message(0x71, target, 0x13);
            pax_romanum -= 0xc;
            if (pax_romanum < 0) pax_romanum = 0;
            return 0;
        }
        destroy_reg_atom(target);
        army_list[army_no].target_x = army_list[army_no].x;
        army_list[army_no].target_y = army_list[army_no].y;
        pax_romanum -= 6;
        if (pax_romanum < 0) pax_romanum = 0;
        put_message(0x72, target, 0x13);
        return 0;
    }
    if ((int)terr_bit_4) return 0;
    if (army_a == 0) {
        destroy_reg_atom(target);
        if ((int)terr_bit_20) return 1;
        return 2;
    }
    if (army_list[army_a].type == 1) {
        if (army_list[army_a].state_idx == 2) return 0;
        get_contenders();
        game_state  = 4;
        battle_type = 1;
    }
    goto ret999;
}

// FUNCTION: C2 0x4A1B5
// WIN: 0x0040d869
// Lines 1930–1974
//
// Sea-army move primitive: identical structure to
// try_a_regionmap_square but for a sailing army.  Differences:
//
//   * Out-of-bounds → return 2 (sentinel meaning "blocked /
//     give up"), not 0.
//   * `default` (dir > 7) → return 0.
//   * Tail call goes to try_this_seamap_square (which only uses
//     `cell_off`; `kind` and `third` are ignored).
//
// 60×60 region grid; cell stride 8 bytes (so direction deltas
// match try_a_regionmap_square: ±0x1E0 for N/S, ±8 for E/W,
// ±0x1D8 / ±0x1E8 for diagonals).
int try_a_seamap_square(int dir, int kind, int third)
{
    int r;

    r = 0;
    enemy_figure = 0;
    switch (dir) {
    case 0:                                /* N */
        if (army_list[army_no].y <= 0)
            r = 2;
        else
            r = try_this_seamap_square(army_list[army_no].map_ref - 0x1e0, kind, third);
        break;
    case 1:                                /* NE */
        if (army_list[army_no].x < 0x3b) {
            if (army_list[army_no].y <= 0)
                r = 2;
            else
                r = try_this_seamap_square(army_list[army_no].map_ref - 0x1d8, kind, third);
        } else {
            r = 2;
        }
        break;
    case 2:                                /* E */
        if (army_list[army_no].x < 0x3b)
            r = try_this_seamap_square(army_list[army_no].map_ref + 8, kind, third);
        else
            r = 2;
        break;
    case 3:                                /* SE */
        if (army_list[army_no].x < 0x3b) {
            if (army_list[army_no].y < 0x3b)
                r = try_this_seamap_square(army_list[army_no].map_ref + 0x1e8, kind, third);
            else
                r = 2;
        } else {
            r = 2;
        }
        break;
    case 4:                                /* S */
        if (army_list[army_no].y < 0x3b)
            r = try_this_seamap_square(army_list[army_no].map_ref + 0x1e0, kind, third);
        else
            r = 2;
        break;
    case 5:                                /* SW */
        if (army_list[army_no].x <= 0)
            r = 2;
        else if (army_list[army_no].y < 0x3b)
            r = try_this_seamap_square(army_list[army_no].map_ref + 0x1d8, kind, third);
        else
            r = 2;
        break;
    case 6:                                /* W */
        if (army_list[army_no].x <= 0)
            r = 2;
        else
            r = try_this_seamap_square(army_list[army_no].map_ref - 8, kind, third);
        break;
    case 7:                                /* NW */
        if (army_list[army_no].x <= 0)
            r = 2;
        else if (army_list[army_no].y <= 0)
            r = 2;
        else
            r = try_this_seamap_square(army_list[army_no].map_ref - 0x1e8, kind, third);
        break;
    }
    return r;
}

// FUNCTION: C2 0x4A369
// WIN: 0x0040dc89
// Lines 1977–2000
//
// Inspect a region_map cell at `cell` from the perspective of the
// current army's sail-target search.  Returns:
//   * 1 — cell is a target army's tile (bits 8 and 0x10 set);
//   * 3 — cell is impassable (bit 0 set) and the army is too small
//         to land (state_idx >= 6) → mark as landed and bail;
//   * 0 (with destroy_reg_atom side-effect) — bit 0 set but the
//         army is too small (state_idx < 6);
//   * 0 — open sea / non-target tile; record cell flags & 0x17 in
//         landed_flag and return.
//
// Always sets `army_a` to the cell's army-occupant byte (+0x7).
int try_this_seamap_square(int cell_off, int kind, int third)
{
    char tile_flags;
    (void)kind; (void)third;

    army_a = (*(struct region_cell *)((unsigned char *)region_map + (cell_off))).occupant;
    tile_flags = (*(struct region_cell *)((unsigned char *)region_map + (cell_off))).terrain;
    if ((tile_flags & 8) != 0) {
        if ((tile_flags & 0x10) != 0)
            return 1;
        if ((tile_flags & 1) != 0) {
            if (army_list[army_no].type < 6) {
                destroy_reg_atom(cell_off);
                return 0;
            }
            army_list[army_no].flags |= 8;
            return 3;
        }
    }
    army_list[army_no].landed_flag = tile_flags & 0x17;
    army_list[army_no].flags |= 8;
    return 0;
}

// FUNCTION: C2 0x4A3F5
// WIN: 0x0040ddb0
// Lines 2002–2045
//
// Land a sailing army at the chosen port-adjacent shore tile.
// `heading` (0..7) selects the neighbour cell to dock against; two
// occupant flag bits on the candidate slide the dock one cell west
// (& 1) or north (& 2) so the trader unloads onto the actual port
// tile.  Stamps the three port flags into the cell's occupant byte
// (set bits 2/3/4, clear bits 5/6), then OR-in the compass-side
// quadrant (0x20/0x40/0x60) so the dock faces correctly.  If the
// cell carries the warehouse edge bit (0x20 of edge_bits), tops up
// the warehouses via fill_warehouses_with.  Returns 1 iff the
// original (pre-stamp) occupant byte had bit 0x80 set (a sentinel
// callers use as "made landfall?").

int dock_the_ship_in_good_port(int heading)
{
    unsigned char occ;
    unsigned char adj;
    unsigned char was_sea_flag;
    unsigned char edge_flag;
    int cell_x;
    int cell_y;
    int target;
    int idx;
    int size;

    if (heading == 0)      target = army_list[army_no].map_ref - 0x1e0;
    else if (heading == 1) target = army_list[army_no].map_ref - 0x1d8;
    else if (heading == 2) target = army_list[army_no].map_ref + 8;
    else if (heading == 3) target = army_list[army_no].map_ref + 0x1e8;
    else if (heading == 4) target = army_list[army_no].map_ref + 0x1e0;
    else if (heading == 5) target = army_list[army_no].map_ref + 0x1d8;
    else if (heading == 6) target = army_list[army_no].map_ref - 8;
    else if (heading == 7) target = army_list[army_no].map_ref - 0x1e8;

    /* Both adjustments test the ORIGINAL cell's occupant. */
    occ = (*(struct region_cell *)((unsigned char *)region_map + (target))).occupant;
    adj = occ & 3;
    if (adj & 1) target -= 8;
    if (adj & 2) target -= 0x1e0;

    /* Decode cell coords (signed div-by-8, then divmod 60). */
    idx = target / 8;
    cell_x = idx % 60;
    cell_y = idx / 60;

    occ = (*(struct region_cell *)((unsigned char *)region_map + (target))).occupant;
    edge_flag = (*(struct region_cell *)((unsigned char *)region_map + (target))).edge_bits & 0x20;
    was_sea_flag = occ & 0x80;

    (*(struct region_cell *)((unsigned char *)region_map + (target))).occupant |= 0x1c;
    (*(struct region_cell *)((unsigned char *)region_map + (target))).occupant &= 0x9f;

    if (army_list[army_no].compass_side != 0) {
        if (army_list[army_no].compass_side == 2)      (*(struct region_cell *)((unsigned char *)region_map + (target))).occupant |= 0x20;
        else if (army_list[army_no].compass_side == 4) (*(struct region_cell *)((unsigned char *)region_map + (target))).occupant |= 0x40;
        else                                           (*(struct region_cell *)((unsigned char *)region_map + (target))).occupant |= 0x60;
    }

    size = army_list[army_no].trader_brings;
    if (edge_flag != 0) {
        fill_warehouses_with(cell_x, cell_y, 0xf, size, 1);
    }

    return was_sea_flag != 0;
}

// FUNCTION: C2 0x4A621
// WIN: 0x0040e131
// Lines 2049–2101
//
// Step the current army one tile in its `world_dir` heading on the
// region map.  Vacates the army-occupant byte in the old cell (if
// still ours), saves the old map_ref into army.home_ref (used by
// the sail-home logic), updates x/y/map_ref via the 8-way direction
// table (cell stride 8 bytes, row stride 0x1E0 = 60*8), and finally
// stamps `army_no` into the new cell's occupant byte unless
// somebody else is already there (collisions handled elsewhere).
void move_army(void)
{
    if ((*(struct region_cell *)((unsigned char *)region_map + (army_list[army_no].map_ref))).occupant == army_no)
        (*(struct region_cell *)((unsigned char *)region_map + (army_list[army_no].map_ref))).occupant = 0;
    army_list[army_no].home_ref = army_list[army_no].map_ref;

    switch ((unsigned char)army_list[army_no].world_dir) {
    default: return;
    case 0:
        army_list[army_no].y--;
        army_list[army_no].map_ref -= 0x1e0;
        break;
    case 1:
        army_list[army_no].y--;
        army_list[army_no].x++;
        army_list[army_no].map_ref -= 0x1d8;
        break;
    case 2:
        army_list[army_no].x++;
        army_list[army_no].map_ref += 8;
        break;
    case 3:
        army_list[army_no].y++;
        army_list[army_no].x++;
        army_list[army_no].map_ref += 0x1e8;
        break;
    case 4:
        army_list[army_no].y++;
        army_list[army_no].map_ref += 0x1e0;
        break;
    case 5:
        army_list[army_no].y++;
        army_list[army_no].x--;
        army_list[army_no].map_ref += 0x1d8;
        break;
    case 6:
        army_list[army_no].x--;
        army_list[army_no].map_ref -= 8;
        break;
    case 7:
        army_list[army_no].y--;
        army_list[army_no].x--;
        army_list[army_no].map_ref -= 0x1e8;
        break;
    }
    if ((*(struct region_cell *)((unsigned char *)region_map + (army_list[army_no].map_ref))).occupant == 0)
        (*(struct region_cell *)((unsigned char *)region_map + (army_list[army_no].map_ref))).occupant = army_no;
}

// FUNCTION: C2 0x4A759
// WIN: 0x0040e4f2
// Lines 2103–2113
//
// Region-map twin of target_from_dirc — sets army.target_x /
// target_y to the cell adjacent to (army.x, army.y) in compass
// direction `dir`.  Same 0..7 mapping (0=N, 2=E, 4=S, 6=W and
// the four diagonals).  Laid out as an if-else chain with cardinals
// first then diagonals.
void target_from_army_dirc(int dir)
{
    if (dir == 0) {
        army_list[army_no].target_x = army_list[army_no].x;
        army_list[army_no].target_y = army_list[army_no].y - 1;
    } else if (dir == 2) {
        army_list[army_no].target_x = army_list[army_no].x + 1;
        army_list[army_no].target_y = army_list[army_no].y;
    } else if (dir == 4) {
        army_list[army_no].target_x = army_list[army_no].x;
        army_list[army_no].target_y = army_list[army_no].y + 1;
    } else if (dir == 6) {
        army_list[army_no].target_x = army_list[army_no].x - 1;
        army_list[army_no].target_y = army_list[army_no].y;
    } else if (dir == 1) {
        army_list[army_no].target_x = army_list[army_no].x + 1;
        army_list[army_no].target_y = army_list[army_no].y - 1;
    } else if (dir == 3) {
        army_list[army_no].target_x = army_list[army_no].x + 1;
        army_list[army_no].target_y = army_list[army_no].y + 1;
    } else if (dir == 5) {
        army_list[army_no].target_x = army_list[army_no].x - 1;
        army_list[army_no].target_y = army_list[army_no].y + 1;
    } else if (dir == 7) {
        army_list[army_no].target_x = army_list[army_no].x - 1;
        army_list[army_no].target_y = army_list[army_no].y - 1;
    }
}

// FUNCTION: C2 0x4A880
// WIN: 0x0040e888
// Lines 2118–2137
//
// Find a fire-zone bit set in the 3×3 neighbourhood of the
// current citizen's zone (zone = 8×8 cells).  Sets the global
// (zone_x, zone_y) to the chosen zone and returns 1, or
// returns 0 if no neighbour zone has a fire.
//
// Layout: fire_zones is a 10×10 byte map, one bit per zone.
// The vigile (citizen) lives in a city_map cell (.x, .y) which
// maps to the zone (x/8, y/8).
//
// Search order:
//   1. self            (zone_y, zone_x)
//   2. north row       (y-1, x), (y-1, x-1), (y-1, x+1)
//   3. south row       (y+1, x), (y+1, x-1), (y+1, x+1)
//   4. west            (y, x-1)
//   5. east            (y, x+1)
//
// First non-zero hit wins; updates (zone_x, zone_y) to the hit
// cell and returns 1.
int test_fire_zones(void)
{
    zone_x = citizen_list[citizen_no].x / 8;
    zone_y = citizen_list[citizen_no].y / 8;

    if (fire_zones[zone_x + zone_y * 10] != 0) {
        return 1;
    }

    if (zone_y > 0) {
        if (fire_zones[zone_x + (zone_y - 1) * 10] != 0) {
            zone_y = zone_y - 1;
            return 1;
        }
        if (zone_x > 0) {
            if (fire_zones[(zone_x - 1) + (zone_y - 1) * 10] != 0) {
                zone_x = zone_x - 1;
                zone_y = zone_y - 1;
                return 1;
            }
        }
        if (zone_x < 9) {
            if (fire_zones[(zone_x + 1) + (zone_y - 1) * 10] != 0) {
                zone_x = zone_x + 1;
                zone_y = zone_y - 1;
                return 1;
            }
        }
    }

    if (zone_y < 9) {
        if (fire_zones[zone_x + (zone_y + 1) * 10] != 0) {
            zone_y = zone_y + 1;
            return 1;
        }
        if (zone_x > 0) {
            if (fire_zones[(zone_x - 1) + (zone_y + 1) * 10] != 0) {
                zone_x = zone_x - 1;
                zone_y = zone_y + 1;
                return 1;
            }
        }
        if (zone_x < 9) {
            if (fire_zones[(zone_x + 1) + (zone_y + 1) * 10] != 0) {
                zone_x = zone_x + 1;
                zone_y = zone_y + 1;
                return 1;
            }
        }
    }

    if (zone_x > 0) {
        if (fire_zones[zone_y * 10 + (zone_x - 1)] != 0) {
            zone_x = zone_x - 1;
            return 1;
        }
    }
    if (zone_x < 9) {
        if (fire_zones[zone_y * 10 + (zone_x + 1)] != 0) {
            zone_x = zone_x + 1;
            return 1;
        }
    }

    return 0;
}

// FUNCTION: C2 0x4AA68
// WIN: 0x0040eb06
// Lines 2140–2180
//
// Find the most appealing fire in the 8×8 zone centred at
// (zone_x*8, zone_y*8) for the current vigile (citizen).  Two
// candidates are tracked:
//
//   * uncovered fire — closest cell where bit 0x80 of edge_bits
//     is set AND is_fire_covered(cm_ptr) returns 0.
//   * covered fire   — same scan, is_fire_covered != 0.
//
// Decision tree (after the scan):
//
//   if   uncov >  40 AND cov <  36 → pick covered
//   else if uncov >  12 AND cov <   6 → pick covered
//   else if uncov >   8 AND cov <   4 → pick covered
//   else if uncov < 100               → pick uncovered
//   else if cov   < 100               → return 0 (don't clear)
//   else  fire_zones[zone_y*10+zone_x] = 0; return 0;
//
// "Pick" stores the chosen cell into the global trio
// (z_x, z_y, z_ptr) and returns 1.
//
// Walks the 8x8 zone row-major and tracks the closest covered fire
// (a fire whose tile is currently being attended by another vigile)
// and the closest uncovered one.  Distance is Chebyshev from the
// vigile's grid position.
int test_zone_for_closest_fire(void)
{
  int cov_ptr;
  int uncov_x;
  int uncov_y;
  int ptr;
  int min_cov;
  int uncov_ptr;
  int min_uncov;
  int y;
  int x;
  int cov_x;
  int cov_y;
  int zp;
  ptr = (zone_y * ((8 * CITY_W) * CITY_CELL_BYTES));
  ptr += (zone_x * (8 * CITY_CELL_BYTES));
  min_uncov = 100;
  min_cov = 100;
  for (y = zone_y * 8; y < ((zone_y * 8) + 8); y++, ptr += 1440)
  {
    for (x = zone_x * 8; x < ((zone_x * 8) + 8); x++, ptr += 20)
    {
      unsigned char b;
      b = (*(struct city_cell *)((unsigned char *)city_map + (ptr))).base_kind;
      if (b < 8)
      {
        b = (*(struct city_cell *)((unsigned char *)city_map + (ptr))).edge_bits;
        if ((b & 0x80) != 0)
        {
          int dist;
          dist = get_distance(x, y, citizen_list[citizen_no].x, citizen_list[citizen_no].y);
          if (dist < min_uncov)
          {
            if (is_fire_covered(ptr) != 0)
            {
              min_cov = dist;
              cov_x = x;
              cov_y = y;
              cov_ptr = ptr;
              continue;
            }
            min_uncov = dist;
            uncov_x = x;
            uncov_y = y;
            uncov_ptr = ptr;
          }
        }
      }
    }
  }

  if ((min_uncov > 0x28) && (min_cov < 0x24))
  {
    z_x = cov_x;
    z_y = cov_y;
    z_ptr = cov_ptr;
    return 1;
  }
  if ((min_uncov > 0xc) && (min_cov < 6))
  {
    z_x = cov_x;
    z_y = cov_y;
    z_ptr = cov_ptr;
    return 1;
  }
  if ((min_uncov > 8) && (min_cov < 4))
  {
    z_x = cov_x;
    z_y = cov_y;
    z_ptr = cov_ptr;
    return 1;
  }
  if (min_uncov < 100)
  {
    z_x = uncov_x;
    z_y = uncov_y;
    z_ptr = uncov_ptr;
    return 1;
  }
  if (min_cov >= 100)
  {
    zp = (zone_y * 10) + zone_x;
    fire_zones[zp] = 0;
  }
  return 0;
}





// FUNCTION: C2 0x4ABFF
// WIN: 0x0040ed63
// Lines 2182–2196
//
// One fire-fight tick at the citizen's current cell:
//   * return 0 if the cell is solid terrain (base_kind >= 8) or no
//     longer has the active-fire bit set (edge_bits & 0x80 == 0);
//   * if the cell's fire counter is at 1, clear the active-fire bit;
//     otherwise decrement the counter in place;
//   * return 1.
int putting_out_fire(void)
{
    int ref;
    unsigned char x;

    ref = citizen_list[citizen_no].map_ref;
    x = (*(struct city_cell *)((unsigned char *)city_map + ((ref)))).base_kind;
    if (x < 8) {
        x = (*(struct city_cell *)((unsigned char *)city_map + ((ref)))).edge_bits;
        if ((x & 0x80) != 0) {
            x = (*(struct city_cell *)((unsigned char *)city_map + ((ref)))).fire;
            if (--x != 0)
                (*(struct city_cell *)((unsigned char *)city_map + ((ref)))).fire--;
            else
                (*(struct city_cell *)((unsigned char *)city_map + ((ref)))).edge_bits &= 0x7f;
            return 1;
        }
    }
    return 0;
}

// FUNCTION: C2 0x4AC56
// WIN: 0x0040ee6f
// Lines 2198–2206
//
// Re-validate the current citizen's fire target.  Returns:
//   0 — no target set, or the target tile is now solid terrain
//       (base_kind >= 8), or the target tile no longer has the
//       active-fire bit (edge_bits & 0x80) set;
//   1 — fire is still burning at the recorded target tile.
//
// The two `return 0` paths share a single epilogue (PS jumps
// *backwards* from the base_kind check to the first return 0).
int confirm_fire_target(void)
{
    int ref;

    if (citizen_list[citizen_no].target_kind == 0) return 0;
    ref = citizen_list[citizen_no].target_ref;
    if ((*(struct city_cell *)((unsigned char *)city_map + ((ref)))).base_kind >= 8)
        return 0;
    if (((*(struct city_cell *)((unsigned char *)city_map + ((ref)))).edge_bits & 0x80) == 0)
        return 0;
    return 1;
}

// FUNCTION: C2 0x4AC97
// WIN: 0x0040ef01
// Lines 2208–2216
//
// Walk citizens 1..200 and return 1 if any active citizen is in the
// fire-fight state (state_idx == 9 == s09_fire_fight) with target_ref
// matching the supplied cm_ptr.  Otherwise return 0.  Leaves
// `temp_citizen` at the last index tested so the caller's neighbour
// search can pick up where this scan left off.
int is_fire_covered(int ref)
{
    for (temp_citizen = 1; temp_citizen < 0xc9; temp_citizen++) {
        if (citizen_list[temp_citizen].exists != 0
         && citizen_list[temp_citizen].state_idx == 9
         && citizen_list[temp_citizen].target_ref == ref) {
            return 1;
        }
    }
    return 0;
}

// FUNCTION: C2 0x4ACE8
// WIN: 0x0040efad
// Lines 2220–2260
//
// Sweep a (radius+1)x(radius+1) bounding box around the current
// citizen on city_map and update the citizen's two market-demand
// fields.  Three counters: count_industry (base_kind 0x82..0xA1),
// count_pop (education & 0x80, +2 per hit), count_other (education
// & 0x40, +3 per hit).  market_demand_a is bumped by
// count_industry and decayed by 1 (or 2 when > 4), capped at 100.
// market_demand_b is bumped by count_pop when mode != 0 (or
// count_other otherwise), decayed by 1, capped at 100.  Uses
// (gmn_x, gmn_y, gmn_sptr) as live walk pointers.
void get_population_and_industry_count(int radius, int mode)
{
    int y_start;
    int x_start;
    int diameter;
    int width;
    int height;
    int row_inc;
    unsigned char count_pop;
    unsigned char count_industry;
    unsigned char count_other;
    unsigned char base;
    unsigned char edu;

    x_start = citizen_list[citizen_no].x - radius;
    y_start = citizen_list[citizen_no].y - radius;
    diameter = 2 * radius;
    height = diameter + 1;
    width  = diameter + 1;

    if (x_start < 0) {
        width += x_start;
        x_start = 0;
    } else if (x_start + width > 0x50) {
        width -= (x_start + width) - 0x50;
    }
    if (y_start < 0) {
        height += y_start;
        y_start = 0;
    } else if (y_start + height > 0x50) {
        height -= (y_start + height) - 0x50;
    }

    gmn_sptr = 20 * (x_start + y_start * 0x50);
    row_inc  = 20 * (0x50 - width);

    count_other    = 0;
    count_pop      = 0;
    count_industry = 0;

    for (gmn_y = y_start; gmn_y < y_start + height; gmn_y++, gmn_sptr += row_inc) {
        for (gmn_x = x_start; gmn_x < x_start + width; gmn_x++, gmn_sptr += 20) {
            base = ((struct city_cell *)((unsigned char *)city_map + gmn_sptr))->base_kind;
            edu  = ((struct city_cell *)((unsigned char *)city_map + gmn_sptr))->education;
            if (base >= 0x82 && base <= 0xa1) count_industry++;
            if (edu & 0x80) count_pop   += 2;
            if (edu & 0x40) count_other += 3;
        }
    }

    /* Saturating bump for market_demand_a. */
    citizen_list[citizen_no].market_demand_a += count_industry;
    if (citizen_list[citizen_no].market_demand_a > 4) {
        citizen_list[citizen_no].market_demand_a -= 2;
    } else if (citizen_list[citizen_no].market_demand_a > 0) {
        citizen_list[citizen_no].market_demand_a--;
    }
    if (citizen_list[citizen_no].market_demand_a > 0x64) {
        citizen_list[citizen_no].market_demand_a = 0x64;
    }

    /* Bump for market_demand_b. */
    if (mode != 0) {
        citizen_list[citizen_no].market_demand_b += count_pop;
    } else {
        citizen_list[citizen_no].market_demand_b += count_other;
    }
    if (citizen_list[citizen_no].market_demand_b > 0) {
        citizen_list[citizen_no].market_demand_b--;
    }
    if (citizen_list[citizen_no].market_demand_b > 0x64) {
        citizen_list[citizen_no].market_demand_b = 0x64;
    }
}

// FUNCTION: C2 0x4AEDB
// WIN: 0x0040f3c1
// Lines 2267–2290
//
// Scan the 60×60 region_map for the nearest "regional
// building" cell (per the type test t == 0x97 || t > 0xd2,
// gated by flags1 bit 0 and flags2 bits 0..1 clear), where
// distance is get_longest_distance from the army's current
// position.  Region cells are 8 bytes wide.
//
// On match: leaves gmn_x / gmn_y pointing at the best cell,
// returns 1.  On miss: returns 0.
int get_nearest_reg_building(void)
{
    int min_dist;
    int best_x;
    int best_y;
    int t;
    int d;
    unsigned char terrain;
    unsigned char flags1;
    unsigned char flags2;

    min_dist = 0x3e8; best_x = best_y = 0;
    gmn_sptr = gmn_y = 0;
    for ( ; gmn_y < 0x3c; gmn_y++) {
    for (gmn_x = 0; gmn_x < 0x3c; gmn_x++, gmn_sptr += 8) {
    terrain = (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).base_kind;
    flags1  = (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).terrain;
    flags2  = (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).occupant & 3;
    if ((flags1 & 1) != 0) {
        if (flags2 == 0) {
            if ((t = terrain) >= 0x97) {
                if (t < 0x98 || t > 0xd2) {
                    d = get_longest_distance(army_list[army_no].x, army_list[army_no].y, gmn_x, gmn_y);
                    if (d < min_dist) { min_dist = d; best_x = gmn_x; best_y = gmn_y; }
                }
            }
        }
    }
    }
    }
    if (min_dist < 0x3e8) { gmn_x = best_x; gmn_y = best_y; return 1; }
    return 0;
}

void (*citizen_intelligences[8])(void) = {
    i00_null,
    i01_tax_man,
    i02_market_man,
    i03_barbarian_man,
    i04_centurian_man,
    i05_vigile_man,
    i06_business_man,
    i07_rioter_man
};

void (*army_intelligences[9])(void) = {
    a00_null,
    a01_cohort,
    a02_enemy,
    a04_raider,
    a04_raider,
    a05_revolt,
    a06_roman_ship,
    a08_raider_ship,
    a08_raider_ship
};

void (*citizen_states[13])(void) = {
    s00_null,
    s01_wait,
    s02_death,
    s03_map_admin,
    s04_map_markets,
    s05_maraude_to_top_spot,
    s06_quell_trouble,
    s07_army_patrol,
    s08_vigile_patrol,
    s09_fire_fight,
    s10_get_business,
    s11_riot,
    s12_goto_riot
};

void (*army_states[17])(void) = {
    sa00_null,
    sa01_wait,
    sa02_death,
    sa03_army_move,
    sa04_army_attack,
    sa05_army_return,
    sa06_army_land_raid,
    sa07_army_land_invade,
    sa08_army_stuck,
    sa09_army_siege,
    sa10_army_demobed,
    sa11_army_sail_to_port,
    sa12_army_sail_home,
    sa13_army_sail_round_coast,
    sa14_army_sail_to_shore,
    sa15_sink,
    sa16_army_lurk_round_coast
};
