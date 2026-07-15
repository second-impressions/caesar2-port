// D:\C2\CODE\c2.c

#include <stdlib.h>     /* free() */

#include "c2_data.h"

struct gfx_entry c2_map_gfx[48] = {
    { "ltlmen1b.pl8", 60000 },
    { "cityfixt.pl8", 121978 },
    { "houses1.pl8", 168528 },
    { "build1a.pl8", 147740 },
    { "build1b.pl8", 173728 },
    { "build1c.pl8", 101546 },
    { "build1d.pl8", 109856 },
    { "citytop1.pl8", 43800 },
    { "ltlmen2b.pl8", 18000 },
    { "cityfix2.pl8", 29688 },
    { "houses2.pl8", 37422 },
    { "build2a.pl8", 33836 },
    { "build2b.pl8", 39036 },
    { "build2c.pl8", 23976 },
    { "build2d.pl8", 26000 },
    { "citytop2.pl8", 43800 },
    { "ltlmen3b.pl8", 8000 },
    { "cityfix3.pl8", 7288 },
    { "houses3.pl8", 8272 },
    { "build3a.pl8", 7662 },
    { "build3b.pl8", 8090 },
    { "build3c.pl8", 5250 },
    { "build3d.pl8", 5918 },
    { "citytop3.pl8", 43800 },
    { "my_stds.pl8", 158712 },
    { "provfixt.pl8", 128248 },
    { "prvbld1a.pl8", 108800 },
    { "mountns1.pl8", 110250 },
    { "prvbld1b.pl8", 116684 },
    { "build1c.pl8", 0 },
    { "build1d.pl8", 0 },
    { "citytop1.pl8", 18000 },
    { "my_stds2.pl8", 39194 },
    { "provfix2.pl8", 29688 },
    { "prvbld2a.pl8", 23442 },
    { "mountns2.pl8", 25166 },
    { "prvbld2b.pl8", 27038 },
    { "build2c.pl8", 0 },
    { "build2d.pl8", 0 },
    { "citytop2.pl8", 18000 },
    { "my_stds3.pl8", 9024 },
    { "provfix3.pl8", 7288 },
    { "prvbld3a.pl8", 5700 },
    { "mountns3.pl8", 6502 },
    { "prvbld3b.pl8", 6530 },
    { "build3c.pl8", 0 },
    { "build3d.pl8", 0 },
    { "citytop3.pl8", 18000 }
};

struct gfx_entry c2_overlay_gfx[3] = {
    { "overlay1.pl8", 60000 },
    { "overlay2.pl8", 18000 },
    { "overlay3.pl8", 8000 }
};

struct gfx_entry c2_battle_gfx[68] = {
    { "batlfix2.pl8", 14000 },
    { "RO2SWDA.PL8", 90000 },
    { "RO2SPRB.PL8", 105000 },
    { "RO2SLGC.PL8", 98000 },
    { "AF2SPRA.PL8", 102000 },
    { "AF2KNFB.PL8", 100000 },
    { "AF2BOWC.PL8", 98000 },
    { "AR2SPRA.PL8", 115000 },
    { "AR2SWDB.PL8", 118000 },
    { "AR2BOWC.PL8", 95000 },
    { "GM2SWDA.PL8", 95000 },
    { "GM2SPRB.PL8", 105000 },
    { "GM2BOWC.PL8", 105000 },
    { "GL2SWDA.PL8", 110000 },
    { "GL2SPRB.PL8", 105000 },
    { "GL2BOWC.PL8", 98000 },
    { "BR2SWDA.PL8", 110000 },
    { "BR2SWDB.PL8", 105000 },
    { "BR2JAVC.PL8", 98000 },
    { "HN2CAVA1.PL8", 65000 },
    { "HN2CAVA2.PL8", 120000 },
    { "HN2SWDB.PL8", 100000 },
    { "CA2CAVA1.PL8", 235000 },
    { "CA2CAVA2.PL8", 0 },
    { "CA2SPRB.PL8", 110000 },
    { "GK2SPRA.PL8", 110000 },
    { "GK2SPRB.PL8", 105000 },
    { "GK2SLGC.PL8", 95000 },
    { "EG2SPRA.PL8", 102000 },
    { "EG2SWDB.PL8", 100000 },
    { "EG2BOWC.PL8", 98000 },
    { "PA2CAVA1.PL8", 65000 },
    { "PA2CAVA2.PL8", 120000 },
    { "PA2SWDB.PL8", 100000 },
    { "batlfix3.pl8", 14000 },
    { "RO3SWDA.PL8", 90000 },
    { "RO3SPRB.PL8", 105000 },
    { "RO3SLGC.PL8", 98000 },
    { "AF3SPRA.PL8", 102000 },
    { "AF3KNFB.PL8", 100000 },
    { "AF3BOWC.PL8", 98000 },
    { "AR3SPRA.PL8", 115000 },
    { "AR3SWDB.PL8", 118000 },
    { "AR3BOWC.PL8", 95000 },
    { "GM3SWDA.PL8", 95000 },
    { "GM3SPRB.PL8", 105000 },
    { "GM3BOWC.PL8", 105000 },
    { "GL3SWDA.PL8", 110000 },
    { "GL3SPRB.PL8", 105000 },
    { "GL3BOWC.PL8", 98000 },
    { "BR3SWDA.PL8", 110000 },
    { "BR3SWDB.PL8", 105000 },
    { "BR3JAVC.PL8", 98000 },
    { "HN3CAVA1.PL8", 65000 },
    { "HN3CAVA2.PL8", 120000 },
    { "HN3SWDB.PL8", 100000 },
    { "CA3CAVA1.PL8", 235000 },
    { "CA3CAVA2.PL8", 0 },
    { "CA3SPRB.PL8", 110000 },
    { "GK3SPRA.PL8", 110000 },
    { "GK3SPRB.PL8", 105000 },
    { "GK3SLGC.PL8", 95000 },
    { "EG3SPRA.PL8", 102000 },
    { "EG3SWDB.PL8", 100000 },
    { "EG3BOWC.PL8", 98000 },
    { "PA3CAVA1.PL8", 65000 },
    { "PA3CAVA2.PL8", 120000 },
    { "PA3SWDB.PL8", 100000 }
};

struct gfx_entry c2_battle_aux_gfx[68] = {
    { "batlfix2.pl8", 14000 },
    { "RO2SWDAX.PL8", 90000 },
    { "RO2SPRBX.PL8", 105000 },
    { "RO2SLGCX.PL8", 98000 },
    { "AF2SPRAX.PL8", 102000 },
    { "AF2KNFBX.PL8", 100000 },
    { "AF2BOWCX.PL8", 98000 },
    { "AR2SPRAX.PL8", 115000 },
    { "AR2SWDBX.PL8", 118000 },
    { "AR2BOWCX.PL8", 95000 },
    { "GM2SWDAX.PL8", 95000 },
    { "GM2SPRBX.PL8", 105000 },
    { "GM2BOWCX.PL8", 105000 },
    { "GL2SWDAX.PL8", 110000 },
    { "GL2SPRBX.PL8", 105000 },
    { "GL2BOWCX.PL8", 98000 },
    { "BR2SWDAX.PL8", 110000 },
    { "BR2SWDBX.PL8", 105000 },
    { "BR2JAVCX.PL8", 98000 },
    { "HN2CAVA3.PL8", 65000 },
    { "HN2CAVA4.PL8", 120000 },
    { "HN2SWDBX.PL8", 100000 },
    { "CA2CAVA3.PL8", 235000 },
    { "CA2CAVA4.PL8", 0 },
    { "CA2SPRBX.PL8", 110000 },
    { "GK2SPRAX.PL8", 110000 },
    { "GK2SPRBX.PL8", 105000 },
    { "GK2SLGCX.PL8", 95000 },
    { "EG2SPRAX.PL8", 102000 },
    { "EG2SWDBX.PL8", 100000 },
    { "EG2BOWCX.PL8", 98000 },
    { "PA2CAVA3.PL8", 65000 },
    { "PA2CAVA4.PL8", 120000 },
    { "PA2SWDBX.PL8", 100000 },
    { "batlfix3.pl8", 14000 },
    { "RO3SWDAX.PL8", 90000 },
    { "RO3SPRBX.PL8", 105000 },
    { "RO3SLGCX.PL8", 98000 },
    { "AF3SPRAX.PL8", 102000 },
    { "AF3KNFBX.PL8", 100000 },
    { "AF3BOWCX.PL8", 98000 },
    { "AR3SPRAX.PL8", 115000 },
    { "AR3SWDBX.PL8", 118000 },
    { "AR3BOWCX.PL8", 95000 },
    { "GM3SWDAX.PL8", 95000 },
    { "GM3SPRBX.PL8", 105000 },
    { "GM3BOWCX.PL8", 105000 },
    { "GL3SWDAX.PL8", 110000 },
    { "GL3SPRBX.PL8", 105000 },
    { "GL3BOWCX.PL8", 98000 },
    { "BR3SWDAX.PL8", 110000 },
    { "BR3SWDBX.PL8", 105000 },
    { "BR3JAVCX.PL8", 98000 },
    { "HN3CAVA3.PL8", 65000 },
    { "HN3CAVA4.PL8", 120000 },
    { "HN3SWDBX.PL8", 100000 },
    { "CA3CAVA3.PL8", 235000 },
    { "CA3CAVA4.PL8", 0 },
    { "CA3SPRBX.PL8", 110000 },
    { "GK3SPRAX.PL8", 110000 },
    { "GK3SPRBX.PL8", 105000 },
    { "GK3SLGCX.PL8", 95000 },
    { "EG3SPRAX.PL8", 102000 },
    { "EG3SWDBX.PL8", 100000 },
    { "EG3BOWCX.PL8", 98000 },
    { "PA3CAVA3.PL8", 65000 },
    { "PA3CAVA4.PL8", 120000 },
    { "PA3SWDBX.PL8", 100000 }
};

/* ── TU-owned file-scope variables (PS.EXE _BSS, original declaration
   order).  Recovered so the functional rebuild (`c2 rebuild`) links
   self-sustained -- no auto-stubbed storage.  Extern decls: c2_data.h. */
struct c2inf_rec c2inf;

/* sb_cm_undo_flushed and sb_rm_undo_flushed are byte-wide flags. */

/* Forward declarations of helpers from other Caesar II modules. */

extern void *malloc(unsigned int size);
extern void  printf(const char *fmt, ...);
extern void  exit(int status);

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
#ifndef _MSC_VER   /* MSVC win-oracle build force-includes c2_funcs.h (typed) */
extern int read_config();  /* really char -- lib32.c */
extern int to_upper();     /* really char -- lib32.c */
#endif

/* String constants for circus / building filenames in the data segment. */


extern int   _getdrive(void);
// FUNCTION: C2 0x10010
// WIN: 0x00443733
// Lines 42–215
//
// Caesar II program entry point.  Resolves the CD drive (with an
// interactive retry loop), loads the boot art / palette / fonts,
// initializes the mouse / sound / scratch buffers, plays the
// intro logos and Smacker animation, then runs the outer game
// loop until exit_flag goes high.
//
// On exit: rolls the demo slideshow, saves preferences via
// save_inf, frees the sample / tune buffers, clears the
// map / battle GFX caches, and calls exit_game.
extern int   getch(void);
extern void  demo_lead_in_slideshow(void);
extern void  free_tune_buffer(void);
void *load_a_battle_gfx_file(int n, int idx, int aux);

extern void get_pseudo_map(int n);
extern unsigned _dos_setdrive(unsigned drive, unsigned *total);
extern unsigned _dos_getdrive(unsigned *drive);
extern int      chdir(const char *path);
extern int      open(const char *path, int flags, ...);
extern int      close(int fd);

void main(int argc, char *argv[])
{
    unsigned int e;
    int cd_err;
    int err;
    int init_err;

    demo_mode = 1;
    demo_mode = 0;

    drive_name = _getdrive() + 0x40;

    if (getcwd(path_name, 0x50) == NULL) goto end;

    c2inf.cd_letter  = 0;
    c2inf.drive_init = 1;

    e = (unsigned char)read_config("resource.cfg", misc);
    c2inf.cd_letter = to_upper(e);
    if (e == 1) {
        high_beep();
        c2inf.drive_init = 0;
    } else {
        cd_err = 1;
        while (cd_err != 0) {
            cd_err = test_cd_drive();
            if (cd_err == 1) {
                printf("\nNo CD information found.\n");
            } else if (cd_err == 2) {
                printf("\nThe drive entered is not a valid drive.\n");
            } else if (cd_err == 3) {
                printf("\nThe drive could not be accessed.\n");
            } else if (cd_err == 4) {
                printf("\nNo CD check info found..\n");
            } else if (cd_err == 5) {
                printf("\nCould not reset to current drive.\n");
            } else if (cd_err == 6) {
                printf("\nCould not reset to current path.\n");
            } else {
                printf("\nCD version installed OK.\n");
                break;
            }
            printf("    1) Enter a valid drive letter.\n");
            printf("    2) Enter SPACE to play from hard-drive only.\n");
            printf("    3) Enter ESC to exit to DOS.\n");
            c2inf.cd_letter = to_upper(getch() & 0xff);
            if (c2inf.cd_letter == 0x1b) {
                printf("\nCAESAR 2 aborted.\n");
                exit(0);
            }
            if (c2inf.cd_letter >= 'A' && c2inf.cd_letter <= 'Z') continue;
            c2inf.drive_init = 0;
            break;
        }
    }

    map_mode   = 0;
    zoom_level = 0;
    init_map_gfx_buffers();
    init_battle_gfx_buffers();
    err = load_start_graphics();
    if (err != 0) {
        printf("File not found - code%d.\n", err);
        exit(0);
    }
    load_map_graphics(0, 0);
    screen_mode = 2;

    if (init_mouse() == 0) {
        printf("No mouse driver found.\n");
        exit(0);
    }

    scratch_buffer_size = 0x27100;
    init_err = 0;
    if (start_system() == 0) init_err = 1;
    if (internal_screen == 0) init_err = 2;
    if (scratch_buffer == 0)  init_err = 3;
    if (init_sample_buffer(0xa) == 0) init_err = 4;
    if (init_tune_buffer() == 0)      init_err = 5;

    if (init_err != 0) {
        no_high_beeps(init_err);
        stop_system();
        printf("Not enough free memory to run Caesar2.\n");
        exit(100);
    }

    flush_sb_buffer();
    init_queery_panel();
    refresh_zoom_mode(0);
    setup_svga_refresh_data();
    load_inf();
    lead_in_logos();
    do_svga_smacked_anim("intro.smk");
    play_tune("forum1.xmi", 1);
    demo_lead_in_slideshow();

    hold_hot_keys = 1;
    background_screen();
    click_warning(0, 0xa0, 0x100);

    turbo_mode = 0;
    exit_flag  = 0;

    while (exit_flag == 0) {
        if (game_state == 3) {
            start_a_promotion();
        } else if (pre_loaded_status == 0) {
            start_a_new_game();
        }

        if (exit_flag != 0) break;

        city_tune_playing = 0;
        hold_hot_keys     = 0;

        if (pre_loaded_status == 0) clear_landfill();
        act_correct_map();
        last_icon_used   = 0;
        placing_type     = 0;
        placing_cost     = 0;
        total_build_cost = 0;
        update_map       = 1;
        restart_flag     = 0;

        if (pre_loaded_status == 0) clear_landfill();

        turbo_mode = 0;
        while (1) {
            if (restart_flag != 0 || exit_flag != 0) break;
            if (pre_loaded_status == 0) {
                main_game_loop();
                if (restart_flag != 0) break;
            }
            deal_with_battles();
            if (restart_flag != 0) break;
            pre_loaded_status = 0;
            if (game_state != 0) {
                restart_flag = 1;
            }
        }

        if (game_state == 1) do_lose_game();
        if (exit_flag == 0) play_tune("forum1.xmi", 1);
    }

    demo_lead_in_slideshow();
    save_inf();
    free_tune_buffer();
    free_sample_buffer(10);
    clear_map_gfx_buffers();
    clear_battle_gfx_buffers();
    exit_game();

end:;
}

// FUNCTION: C2 0x10409
// WIN: 0x00443c91
// Lines 217–234
//
// Per-tick battle bookkeeping.  Only fires when the game is in
// the BATTLE state (game_state == 4).  For battle_type 2 (cohort
// fight), continues the battle and -- if the player won --
// stamps two marker bytes (0x97, 0x32) into region_map at the
// battle2_ptr offset.  For other battle types, continues only
// when neither army's state_idx is 2 (state 2 == "wait/stuck").
//
// After processing, clears game_state unless restart_flag is set
// (some path needs to keep the BATTLE state alive across the next
// tick).

void deal_with_battles(void)
{
    if (game_state != 4) return;

    if (battle_type == 2) {
        continue_battle(pre_loaded_status);
        if (battle_victor == 0) {
            RM_CELL(battle2_ptr).base_kind     = 0x97;
            RM_CELL(battle2_ptr).gfx = 0x32;
        }
    } else if (army_list[our_battle_army].state_idx != 2 &&
               army_list[their_battle_army].state_idx != 2) {
        continue_battle(pre_loaded_status);
    }

    if (restart_flag == 0) {
        game_state = 0;
    }
}

// FUNCTION: C2 0x1049B
// WIN: 0x00443d62
// Lines 236–254
void start_a_new_game(void)
{
    setup_game();
    if (!develop_mode) act_set_skill_levels();
    if (exit_flag)     exit_game();
    if (pre_loaded_status)        return;
    if (continue_tutorial_status) return;
    start_year = year = -300;          /* 0xFFFFFED4 = -300 BC */
    week = month = 0;
    years_elapsed = 0;
    completed_provinces = 0;
    province_is = 0;
    player_rank = 0;
    players_denarii = 0;
    players_salary = init_salary[0].welfare_bill;
    init_tribute();
    clear_empire();
    new_province();
}

// FUNCTION: C2 0x10529
// WIN: 0x00443e35
// Lines 257–264
void start_a_promotion(void)
{
    setup_game();
    if (month) {
        month = 0;
        year++;
    }
    imperial_tax = 0;
    new_province();
    if (restart_flag) start_a_new_game();
}

// FUNCTION: C2 0x10565
// WIN: 0x00443eca
// Lines 266–319
//
// Initialize a fresh province for play: clear figures and armies,
// reset growth counters, set starting denarii (skill-tier scaled
// minus a per-completed-province reduction), and call the
// province-setup helpers.  When restart_flag goes high (player
// chose Quit / Restart from the choose-region screen), exits
// before re-running the long initialization tail.

void new_province(void)
{
    int skill;
    int r;

    setup_game();
    restart_flag = 0;
    setup_history_data();
    clear_citizen_list();
    clear_army_list();

    skill = c2inf.skill_level;
    auto_conquered = pompous_conquests[skill];
    auto_conquered_months = 0;
    if (skill <= 4) {
        pop_growth_future = 0x1c;
    }
    pop_growth_factor = pop_growth_future / 8;

    ind_growth_future   = 0;
    ind_growth_factor   = 0;
    insurrection_future = 0;
    insurrection_factor = 0;
    employment_rate     = 0;
    population          = 0;

    skill = c2inf.skill_level;
    denarii  = skill_to_starting_denarii[skill];
    r = skill_to_denarii_reduction[skill];
    denarii -= r * completed_provinces;

    income_multiple = 0x258;
    pop_tax_rate    = 5;
    ind_tax_rate    = 5;

    init_messages();
    init_flag_markers();
    act_choose_init_region();

    if (restart_flag != 0) return;

    clear_region_map();
    load_region_map(province_is);
    adjust_sailable_area();
    generate_city_map_geography();
    initiate_evolution();
    init_traders();
    init_region_trouble();
    set_new_province();
    init_slaves();
    init_legion();
    init_census();
    monthly_update();
    init_census();
    set_new_province();

    years_elapsed_in_region = 0;
    culture_rating          = 0;
    prosperity_rating       = 0;
    peace_rating            = 0;
    empire_rating           = 0;
    pax_romanum             = 0;
}

// FUNCTION: C2 0x106BB
// WIN: 0x004440a8
// Lines 321–356
//
// One-shot reset of the per-game runtime state: panel-map cursor,
// city/province camera, zoom and rotation, command-window pixel
// rect, ambient map dimensions, and the placing/cheat/highlight
// scratchpads.  Loads the pseudo-map and the per-zoom map graphics
// for the freshly-zoomed view.

void setup_game(void)
{
    pm_y       = 0x50;
    pm_x       = 0x28;
    city_pm_x  = 0x28;
    city_pm_y  = 0x50;
    zoom_level = 0;

    city_rotation   = 0;
    city_zoom_level = 0;
    prov_rotation   = 0;
    prov_zoom_level = 0;
    map_mode        = 0;
    in_the_forum    = 0;

    com_x = 0x1e0;
    com_y = 0x30;
    com_w = 0xa0;
    com_h = 0xa0;

    map_actual_width     = 0x50;
    map_actual_height    = 0x50;
    map_actual_atom      = 0x14;
    map_height_reduction = 0;
    map_width_reduction  = 0;

    get_pseudo_map(0);
    refresh_zoom_mode(zoom_level);
    load_map_graphics(map_mode,
                      zoom_level);

    ov_map_mode      = 0;
    ov2_map_mode     = 1;
    last_icon_used   = 4;
    promotion_cheat  = 0;
    housing_cheat    = 0;
    slave_warning    = 0;
    clear_highlight_goods_list();
    reg_placing_type  = 0;
    reg_placing_flags = 0;
    placing_type      = 0;
    placing_flags     = 0;
    pm_build_shape    = 0;
}

// FUNCTION: C2 0x107DB
// WIN: 0x0044421c
// Lines 358–434
//
// Reload the eight per-zoom map-graphics buffers (people, fixtures,
// houses, four building tiers, and tops) from c2_map_gfx.
// Mode and level select an 8-entry block in the table:
//   block_idx = mode * 24 + level * 8
// (mode is clamped to 0 if > 1 -- only modes 0 and 1 are valid.)
//
// Each iteration: read the entry's size; if zero, skip.  Otherwise
// malloc the slot, readfile the named asset, and continue.  On any
// malloc or readfile failure, stop_system + printf + exit(100).
int load_map_graphics(int mode, int level)
{
    int   base_idx;
    int   i;
    int   size;
    char *fname;
    int   ret;

    clear_map_gfx_buffers();
    init_map_gfx_buffers();
    clear_battle_gfx_buffers();
    init_battle_gfx_buffers();

    if (mode > 1) mode = 0;
    base_idx = mode * 24 + level * 8;

    for (i = 0; i < 8; i++) {
        size  = c2_map_gfx[i + base_idx].size;
        fname = c2_map_gfx[i + base_idx].filename;

        if (size == 0) continue;

        if (i == 0) {
            people_data = malloc((unsigned)size);
            if (people_data == NULL) goto alloc_fail;
            if (!readfile(fname, people_data, size, 0)) goto file_fail;
        }
        else if (i == 1) {
            fixt_data = malloc((unsigned)size);
            if (fixt_data == NULL) goto alloc_fail;
            if (!readfile(fname, fixt_data, size, 0)) goto file_fail;
        }
        else if (i == 2) {
            house_data = malloc((unsigned)size);
            if (house_data == NULL) goto alloc_fail;
            if (!readfile(fname, house_data, size, 0)) goto file_fail;
        }
        else if (i == 3) {
            building_data1 = malloc((unsigned)size);
            if (building_data1 == NULL) goto alloc_fail;
            if (!readfile(fname, building_data1, size, 0)) goto file_fail;
        }
        else if (i == 4) {
            building_data2 = malloc((unsigned)size);
            if (building_data2 == NULL) goto alloc_fail;
            if (!readfile(fname, building_data2, size, 0)) goto file_fail;
        }
        else if (i == 5) {
            building_data3 = malloc((unsigned)size);
            if (building_data3 == NULL) goto alloc_fail;
            if (!readfile(fname, building_data3, size, 0)) goto file_fail;
        }
        else if (i == 6) {
            building_data4 = malloc((unsigned)size);
            if (building_data4 == NULL) goto alloc_fail;
            if (!readfile(fname, building_data4, size, 0)) goto file_fail;
        }
        else if (i == 7) {
            tops_data = malloc((unsigned)size);
            if (tops_data == NULL) goto alloc_fail;
            if (!readfile(fname, tops_data, size, 0)) goto file_fail;
        }
    }

    ret = 1;
    goto done;

file_fail:
    stop_system();
    printf("\nError loading graphics data - code %d - file not found.\n",
           i + base_idx);
    exit(100);

alloc_fail:
    stop_system();
    printf("\nError loading graphics data - code %d  - cannot allocate memory.\n",
           i + base_idx);
    exit(100);

done:
    return ret;
}

// FUNCTION: C2 0x10944
// WIN: 0x0044474a
// Lines 436–460
void swap_circus_gfx(void)
{
    if (population < 2000) return;
    if (map_mode != 0)     return;
    if (game_state == 3)   return;
    if (game_state == 1)   return;
    if (game_state == 2)   return;

    if (zoom_level == 0) {
        if (year & 1)
            readfile("build1f.pl8", building_data4, 0x1ad20, 0);
        else
            readfile("build1d.pl8", building_data4, 0x1ad20, 0);
    } else if (zoom_level == 1) {
        if (year & 1)
            readfile("build2f.pl8", building_data4, 0x6590, 0);
        else
            readfile("build2d.pl8", building_data4, 0x6590, 0);
    } else if (zoom_level == 2) {
        if (year & 1)
            readfile("build3f.pl8", building_data4, 0x171e, 0);
        else
            readfile("build3d.pl8", building_data4, 0x171e, 0);
    }
}

// FUNCTION: C2 0x10A40
// WIN: 0x004448fb
// Lines 462–485
//
// Read one zoom-keyed graphics-table entry into the people_data
// buffer.  The 0-arg path uses c2_map_gfx (8 entries per zoom),
// the non-zero arg path uses c2_overlay_gfx (1 entry per zoom);
// each entry is 20 bytes (16-byte filename + 4-byte size).
//
// On read failure, stops the game and exit(100)s.
// Tail-merges into init_battle_gfx_buffers' 5-pop epilogue at
// 0x10D7A.
int load_overlay_graphics(int param)
{
    int   size;
    char *fname;
    int   slot;
    int   ok;

    if (param == 0) {
        slot = zoom_level * 8;
        size  = c2_map_gfx[slot].size;
        fname = c2_map_gfx[slot].filename;
    } else {
        slot = zoom_level;
        size  = c2_overlay_gfx[slot].size;
        fname = c2_overlay_gfx[slot].filename;
    }

    if (readfile(fname, people_data, size, 0)) {
        ok = 1;
    } else {
        stop_system();
        printf("\nError loading overlay data - file not found.\n");
        exit(100);
    }
    return ok;
}

// FUNCTION: C2 0x10AC9
// WIN: 0x004449df
// Lines 487–520
//
// Reset and reload all of the per-battle graphics: city/region map
// fixtures, the four base figure sets, and (when the player army
// has mercenaries) the mercenary figure set.  Sub-tables 4..6 are
// keyed by the defending army's tribe, sub-tables 7/8 by the
// player's mercenary tribe and category.
//
// Tail-merge into init_battle_gfx_buffers' 5-pop epilogue at 0x10D7A.

int load_battle_graphics(int n)
{
    int idx_base;
    int merc_offset;

    clear_map_gfx_buffers();
    init_map_gfx_buffers();
    clear_battle_gfx_buffers();
    init_battle_gfx_buffers();

    idx_base = tribe_to_troops[
        army_list[their_battle_army].tribe_id];

    fixt_data    = load_a_battle_gfx_file(n, 0, 0);
    figure1_data = load_a_battle_gfx_file(n, 1, 0);
    figure2_data = load_a_battle_gfx_file(n, 2, 0);
    figure3_data = load_a_battle_gfx_file(n, 3, 0);
    figure4_data = load_a_battle_gfx_file(n, idx_base, 0);
    figure5_data = load_a_battle_gfx_file(n, idx_base + 1, 0);
    figure6_data = load_a_battle_gfx_file(n, idx_base + 2, 0);

    if (max_mercs_allowed != 0) {
        idx_base    = tribe_to_troops[mercs_tribe];
        merc_offset = idx_base + 1;

        if (mercs_catagory == 0) {
            figure7_data = load_a_battle_gfx_file(n, idx_base, 1);
            figure8_data = load_a_battle_gfx_file(n, merc_offset, 1);
        } else if (mercs_catagory == 1) {
            figure7_data = load_a_battle_gfx_file(n, idx_base, 1);
        } else if (mercs_catagory == 2) {
            figure7_data = load_a_battle_gfx_file(n, merc_offset, 1);
        } else if (mercs_catagory == 3) {
            figure7_data = load_a_battle_gfx_file(n, idx_base + 2, 1);
        }
    }

    return 1;
}

// FUNCTION: C2 0x10C03
// WIN: 0x00444cf6
// Lines 523–557
//
// Read one slot of a 2D graphics-file table and load the named
// file into a freshly malloc'd buffer.  Each table entry is 20
// bytes: 16-byte filename followed by a 4-byte size field.  The
// table is indexed as [(n-1)*34 + idx] and selected between
// the main (`c2_battle_gfx`) or auxiliary (`c2_battle_aux_gfx`)
// table by `aux`.
//
// Returns NULL when the entry's size field is 0 (slot unused),
// otherwise the malloc'd buffer.  On allocation or read failure
// the game stops and prints an error before exit(100).

void *load_a_battle_gfx_file(int n, int idx, int aux)
{
    int    slot;
    int    size;
    char  *fname;
    void  *buf;

    n--;
    slot = n * 34 + idx;
    if (aux) {
        size  = c2_battle_aux_gfx[slot].size;
        fname = c2_battle_aux_gfx[slot].filename;
    } else {
        size  = c2_battle_gfx[slot].size;
        fname = c2_battle_gfx[slot].filename;
    }

    if (size == 0) return NULL;

    buf = malloc((unsigned)size);
    if (!buf) {
        stop_system();
        printf("\nError loading battle data - code %d - cannot allocate memory.\n",
               idx);
        exit(100);
    }

    if (!readfile(fname, buf, size, 0)) {
        stop_system();
        if (size == 0) {
            printf("\nError loading battle data - 0 sized file.\n");
        } else {
            printf("\nError loading battle data - %s not found.\n", fname);
        }
        exit(100);
    }

    return buf;
}

// FUNCTION: C2 0x10CB9
// WIN: 0x00444e27
// Lines 559–569
void init_map_gfx_buffers(void)
{
    people_data    = 0;
    fixt_data      = 0;
    house_data     = 0;
    building_data1 = 0;
    building_data2 = 0;
    building_data3 = 0;
    building_data4 = 0;
    tops_data      = 0;
}

// FUNCTION: C2 0x10CEE
// WIN: 0x00444fd3
// Lines 571–581
void clear_map_gfx_buffers(void)
{
    if (people_data)    free(people_data);
    if (fixt_data)      free(fixt_data);
    if (house_data)     free(house_data);
    if (building_data1) free(building_data1);
    if (building_data2) free(building_data2);
    if (building_data3) free(building_data3);
    if (building_data4) free(building_data4);
    if (tops_data)      free(tops_data);
}

// FUNCTION: C2 0x10D80
// WIN: 0x004451bf
// Lines 583–596
void init_battle_gfx_buffers(void)
{
    fixt_data     = 0;
    figure1_data  = 0;
    figure2_data  = 0;
    figure3_data  = 0;
    figure4_data  = 0;
    figure5_data  = 0;
    figure6_data  = 0;
    figure7_data  = 0;
    figure8_data  = 0;
    figure9_data  = 0;
    figure10_data = 0;
}

// FUNCTION: C2 0x10DC7
// WIN: 0x0044536f
// Lines 598–610
void clear_battle_gfx_buffers(void)
{
    if (fixt_data)     free(fixt_data);
    if (figure1_data)  free(figure1_data);
    if (figure2_data)  free(figure2_data);
    if (figure3_data)  free(figure3_data);
    if (figure4_data)  free(figure4_data);
    if (figure5_data)  free(figure5_data);
    if (figure6_data)  free(figure6_data);
    if (figure7_data)  free(figure7_data);
    if (figure8_data)  free(figure8_data);
    if (figure9_data)  free(figure9_data);
    if (figure10_data) free(figure10_data);
}

// FUNCTION: C2 0x10E89
// WIN: 0x0044551f
// Lines 614–633
//
// Read the 14 boot-time art / data blobs into their fixed
// destination buffers.  Returns 0 on success or a 1-based code
// identifying the first file that failed to load.
int load_start_graphics(void)
{
    if (!readfile("cityfixt.256", city_palette,        0x300,  0)) return 1;
    if (!readfile("landfill.pl8", landfill,            0x1540, 0)) return 2;
    if (!readfile("font_c2.pl8", font1,                0x24f4, 0)) return 3;
    if (!readfile("font3c2.pl8", font2,                0x6e58, 0)) return 4;
    if (!readfile("mouse.pl8", mice,                   0x21b6, 0)) return 5;
    if (!readfile("system.pl8", system_panel,                  0xa2c8, 0)) return 6;
    if (!readfile("panels.pl8", game_panels,           0x5b91, 0)) return 7;
    if (!readfile("smacker.pl8", logos,                0x14e0, 0)) return 8;
    if (!readfile("misc.pl8", misc,                    0xe00,  0)) return 9;
    if (!readfile("c2.eng", text_buffer,               0x9c40, 0)) return 10;
    if (!readfile("int_city.pl8", int_city_header,     0x1c8,  0)) return 11;
    if (!readfile("provfixt.256", region_palette,      0x300,  0)) return 12;
    if (!readfile("int_prov.pl8", int_region_header,   0x1c8,  0)) return 13;
    if (!readfile("int_batl.pl8", int_battle_header,   0x1c8,  0)) return 14;
    return 0;
}

// FUNCTION: C2 0x1107C
// WIN: 0x0044578b
// Lines 635–639
void flush_sb_buffer(void)
{
    sb_cm_undo_flushed = 1;
    sb_rm_undo_flushed = 1;
}

// FUNCTION: C2 0x1108B
// WIN: 0x004457a4
// Lines 641–641
void do_pos(void)
{
    pos_sound();
}

// FUNCTION: C2 0x11090
// WIN: 0x004457b4
// Lines 642–642
void do_neg(void)
{
    neg_sound();
}

// FUNCTION: C2 0x11095
// WIN: 0x004457c4
// Lines 646–684
//
// Verify that the configured CD-ROM drive contains "cd.dat".
// Returns 0 when everything checks out, otherwise a numbered
// error code:
//   1 - c2inf.cd_letter not set (< 'A')
//   2 - couldn't switch to CD drive
//   3 - chdir to CD root failed
//   4 - "cd.dat" missing on the CD
//   5 - couldn't restore previous drive
//   6 - couldn't restore previous working directory
//
// Cases 3..6 don't early-exit: the function continues so that the
// previous working directory and drive get restored even when one
// of the CD checks failed.


int test_cd_drive(void)
{
    int            ret;
    int            drv;
    int            max_drv;
    int            curr_drv;
    int            fd;
    char          *cd_root = "c:\\";

    ret = 0;

    if (c2inf.cd_letter < 'A') {
        return 1;
    }

    drv = c2inf.cd_letter - 0x40;
    _dos_setdrive((unsigned)drv, (unsigned *)&max_drv);
    _dos_getdrive((unsigned *)&curr_drv);
    if (drv != curr_drv) {
        return 2;
    }

    cd_root[0] = c2inf.cd_letter;
    if (chdir(cd_root) != 0) {
        ret = 3;
    }

    getcwd(path_name, 0x50);

    fd = open("cd.dat", 0x200);
    if (fd >= 0) {
        close(fd);
    } else {
        ret = 4;
    }

    drv = drive_name - 0x40;
    _dos_setdrive((unsigned)drv, (unsigned *)&max_drv);
    _dos_getdrive((unsigned *)&curr_drv);
    if (drv != curr_drv) {
        ret = 5;
    }

    if (chdir(path_name) != 0) {
        ret = 6;
    }

    return ret;
}
