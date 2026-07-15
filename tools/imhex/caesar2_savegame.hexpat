#pragma description Caesar II savegame (*.SAV) - 225,745 bytes
#pragma endian little
#pragma pattern_limit 600000

#include <caesar2_common.hexpat>     // HistoryRow

// ---------------------------------------------------------------------------
// Caesar II (Impressions/Sierra, 1995-96) save-game layout.
//
// savegame()/loadgame() (loadsave.c) dump the 500-entry savegame_entries[]
// block table (datainit.c) verbatim, then append the 4000-byte history.dat
// ring buffer.  No header, magic, version or checksum.  Total 225,745 bytes.
//
// All record structs are byte-packed (Watcom pack(1)): multi-byte fields sit
// at non-naturally-aligned offsets (e.g. army_rec.home_ref, an int, at +0xA3),
// so the compiler inserts NO alignment padding.  Every struct is fully
// expanded from decomp/include/entities.h with each field named.  Fields that
// are declared in the source but never read or written anywhere in PS.EXE are
// genuine DEAD/vestigial fields (NOT padding) -- kept as named fields with
// their entities.h names and tagged [[color("707070"), comment(...)]].  Proof:
// whole-binary disasm scan (arrow_rec/province_industry/mercs_class) and the
// two-build Mac cross-check (figure/citizen/unit/army); see
// docs/mac-deadfield-crosscheck.md.
// ---------------------------------------------------------------------------

// ==== cell bitfields (decoded; see docs/cell-bitfields.md) =================

bitfield CityTerrain {            // city_cell.terrain (+0x01) -- each bit = act_* placing_flags
    building       : 1;           // 0x01 building (house/forum/temple/market/...)
    wall           : 1;           // 0x02 wall      (act_wall)
    tower          : 1;           // 0x04 tower     (act_tower; wall-gate)
    water_variant  : 1;           // 0x08 natural water/river variant
    river_bridge   : 1;           // 0x10 river / bridge tile
    road           : 1;           // 0x20 road      (act_road)
    aqueduct       : 1;           // 0x40 aqueduct  (act_aquaduct)
    reservoir      : 1;           // 0x80 reservoir (act_resevoir)
};

bitfield CityEdge {               // city_cell.edge_bits (+0x03)
    on_road     : 1;              // 0x01 on-road/has-citizen/needs-redraw
    drawn       : 1;              // 0x02 drawn (render pass)
    gfx_subkind : 3;              // 0x1c wall/riverbank graphic sub-kind
    on_web      : 1;              // 0x20 on water-network / web path
    gfx_orient  : 1;              // 0x40 graphic orientation
    draw_on_top : 1;              // 0x80 tall structure (wall/tower)
};

bitfield CityFpu {                // city_cell.fpu_flag (+0x0B) = [fire:2][plague:2][unrest:4]
    unrest : 4;                   // 0x0f unrest level 0..15
    plague : 2;                   // 0x30 plague/health (3 = plague)
    fire   : 2;                   // 0xc0 fire level 0..3
};

bitfield RegionTerrain {          // region_cell.terrain (+0x01) -- tile-category bits (put_rm_area)
    block_special : 1;            // 0x01 hut/border/city placement-block (army-occupiable test)
    out_walls     : 1;            // 0x02 out-of-walls
    army_pass     : 1;            // 0x04 army-passable
    land_lo       : 1;            // 0x08 decorative-land low bit (with 0x10 => 0x18 land tile)
    occupied      : 1;            // 0x10 occupied / blocks region placement
    structure     : 1;            // 0x20 structure present
    cat_40        : 1;            // 0x40 terrain category (codes 0x18-0x1b)
    cat_80        : 1;            // 0x80 terrain category (codes 0x1c-0x1f)
};

bitfield RegionEdge {             // region_cell.edge_bits (+0x03)
    has_occupant : 1;             // 0x01 has-army / citizen
    overlay      : 1;             // 0x02 overlay / processed
    unk_1c       : 3;             // 0x1c (not decoded)
    road         : 1;             // 0x20 road
    had_goods    : 1;             // 0x40 had-goods
    marker       : 1;             // 0x80 placement marker
};

// ==== map cells =============================================================

struct CityCell {
    u8 base_kind;             // +0x00
    CityTerrain terrain;      // +0x01  (decoded bitfield)
    u8 road_aqueduct;         // +0x02  wall/aqueduct chain length (int, not bits)
    CityEdge edge_bits;       // +0x03  (decoded bitfield)
    u8 extra_edge;            // +0x04
    u8 activity_a;            // +0x05
    u8 activity_b;            // +0x06
    u8 citizen_a;             // +0x07
    u8 citizen_b;             // +0x08
    u8 building;              // +0x09
    u8 range_flag;            // +0x0A
    CityFpu fpu_flag;         // +0x0B  (decoded bitfield)
    u8 entertainment;         // +0x0C
    u8 education;             // +0x0D
    u8 health;                // +0x0E
    u8 land_value;            // +0x0F
    u8 fire;                  // +0x10
    u8 security;              // +0x11
    u8 industrial;            // +0x12
    u8 business;              // +0x13
};  // 0x14 = 20 bytes

struct RegionCell {
    u8 base_kind;             // +0x00  tile/building enum (not bits)
    RegionTerrain terrain;    // +0x01  (decoded bitfield)
    u8 place_state;           // +0x02  flood-fill state (0=unset, 0xff=blocked, else step)
    RegionEdge edge_bits;     // +0x03  (decoded bitfield)
    u8 gfx;                   // +0x04
    u8 _unused05 [[color("707070"), comment("dead field: never read/written in PS.EXE; byte-packed struct, so NOT alignment padding")]];  // +0x05
    u8 outside;               // +0x06  single flag: 0x40 = outside-of-walls
    u8 occupant;              // +0x07  context-dependent packed byte (see docs/cell-bitfields.md)
};  // 0x08 = 8 bytes

struct BattleCell {
    u8 terrain;               // +0x00
    u8 figure;                // +0x01
    u8 dirty;                 // +0x02
    u8 arrow;                 // +0x03
};  // 0x04 = 4 bytes

// ==== nested sub-records ====================================================

struct Century {
    u8 type;                  // +0x00
    u8 damaged;               // +0x01
    u8 _u[2] [[color("707070"), comment("dead field: never read/written in PS.EXE; byte-packed struct, so NOT alignment padding")]];  // +0x02
};  // 0x04 = 4 bytes

struct ArmyRoutePoint {
    u8 x;                     // +0x00
    u8 y;                     // +0x01
};  // 0x02 = 2 bytes

// ==== movement / unit records ===============================================

struct FigureRec {
    u8 exists;                // +0x00
    s8 owner;                 // +0x01
    s8 sprite_anim;           // +0x02
    s8 sprite_dir;            // +0x03
    u8 fight_state;           // +0x04
    s8 sprite_type;           // +0x05
    s8 direction;             // +0x06
    s8 fight_direction;       // +0x07
    s8 grid_x;                // +0x08
    s8 grid_y;                // +0x09
    u32 arrow_data_ptr;       // +0x0A
    u32 sprite_data_ptr;      // +0x0E
    s32 map_ref;              // +0x12
    s8 archer_tick_a;         // +0x16
    s8 archer_tick_b;         // +0x17
    s8 prev_grid_x;           // +0x18
    s8 prev_grid_y;           // +0x19
    s8 next_state_idx;        // +0x1A
    s8 wait_counter;          // +0x1B
    s8 state_idx;             // +0x1C
    s8 wf_searching;          // +0x1D
    s8 wf_orient;             // +0x1E
    s8 wf_dirc;               // +0x1F
    s8 wf_ttl;                // +0x20
    u8 _unk21[1] [[color("707070"), comment("dead field: never read/written in PS.EXE; byte-packed struct, so NOT alignment padding")]];  // +0x21
    u8 wf_step_x;             // +0x22
    u8 wf_step_y;             // +0x23
    s8 is_visible;            // +0x24
    u8 is_routing;            // +0x25
    u8 sprite_kind;           // +0x26
    u8 fight_swing_active;    // +0x27
    s8 death_timer;           // +0x28
    u8 missile_target;        // +0x29
    u8 _unk2A[1] [[color("707070"), comment("dead field: never read/written in PS.EXE; byte-packed struct, so NOT alignment padding")]];  // +0x2A
    u8 unit_ref;              // +0x2B
    u8 unit_type;             // +0x2C
    s8 offset_x;              // +0x2D
    s8 offset_y;              // +0x2E
    u8 is_defending;          // +0x2F
    s8 unit_position;         // +0x30
    s8 kill_counter;          // +0x31
    s8 defense;               // +0x32
    s8 stampede_flag;         // +0x33
    u8 _unk34[1] [[color("707070"), comment("dead field: never read/written in PS.EXE; byte-packed struct, so NOT alignment padding")]];  // +0x34
    u8 opponent;              // +0x35
    s8 attack_count;          // +0x36
    u8 fight_role;            // +0x37
    u8 missile_max;           // +0x38
    u8 selected;              // +0x39
    s8 anim_counter;          // +0x3A
    u8 unit_grid_x;           // +0x3B
    u8 unit_grid_y;           // +0x3C
    u8 shield_class;          // +0x3D
    u8 anim_state;            // +0x3E
    u8 backtrack_flag;        // +0x3F
    u8 missile_timer;         // +0x40
    u8 backtrack_dirc;        // +0x41
    u8 _unk42[2] [[color("707070"), comment("dead field: never read/written in PS.EXE; byte-packed struct, so NOT alignment padding")]];  // +0x42
    u8 stampede_kind;         // +0x44
    u8 anim_kind;             // +0x45
    u8 sub_state;             // +0x46
    u8 figure_rank;           // +0x47
    s8 archer_heading_a;      // +0x48
    s8 archer_heading_b;      // +0x49
    s8 archer_image_a;        // +0x4A
    s8 archer_image_b;        // +0x4B
    s8 archer_target_a;       // +0x4C
    s8 archer_target_b;       // +0x4D
    s8 engaged_count;         // +0x4E
    s8 morale;                // +0x4F
    u8 _reserved50[8] [[color("707070"), comment("dead field: never read/written in PS.EXE; byte-packed struct, so NOT alignment padding")]];  // +0x50
};  // 0x58 = 88 bytes

struct CitizenRec {
    u8 exists;                // +0x00
    s8 xp;                    // +0x01
    s8 type;                  // +0x02
    s8 world_dir;             // +0x03
    s8 x;                     // +0x04
    s8 y;                     // +0x05
    s32 map_ref;              // +0x06
    u8 pixel_x;               // +0x0A
    u8 pixel_y;               // +0x0B
    s8 dest_x;                // +0x0C
    s8 dest_y;                // +0x0D
    u8 saved_state_idx;       // +0x0E
    s8 wait_count;            // +0x0F
    s8 state_idx;             // +0x10
    u8 wf_active;             // +0x11
    s8 wf_step;               // +0x12
    s8 wf_length;             // +0x13
    u8 wf_steps[8];           // +0x14
    u8 _unk1C[2] [[color("707070"), comment("dead field: never read/written in PS.EXE; byte-packed struct, so NOT alignment padding")]];  // +0x1C
    s8 speed;                 // +0x1E
    s8 speed_count;           // +0x1F
    s8 speed_phase;           // +0x20
    s8 flag_bits;             // +0x21
    u8 action_kind;           // +0x22
    u8 is_barbarian;          // +0x23
    s8 state_timer;           // +0x24
    u8 _unk25 [[color("707070"), comment("dead field: never read/written in PS.EXE; byte-packed struct, so NOT alignment padding")]];  // +0x25
    s8 market_demand_a;       // +0x26
    s8 market_demand_b;       // +0x27
    s32 target_ref;           // +0x28
    u8 target_kind;           // +0x2C
    u8 target_count;          // +0x2D
    s16 evolve_timer;         // +0x2E
    s16 target_marker;        // +0x30
    u8 name_id;               // +0x32
    u8 state;                 // +0x33
    s16 image_id;             // +0x34
    u8 wobble_counter;        // +0x36
    u8 _reserved37[3] [[color("707070"), comment("dead field: never read/written in PS.EXE; byte-packed struct, so NOT alignment padding")]];  // +0x37
};  // 0x3A = 58 bytes

struct UnitRec {
    u8 x;                     // +0x00
    u8 y;                     // +0x01
    s32 current_men;          // +0x02
    s32 start_men;            // +0x06
    u8 _unk0A[3] [[color("707070"), comment("dead field: never read/written in PS.EXE; byte-packed struct, so NOT alignment padding")]];  // +0x0A
    u8 withdraw_flag;         // +0x0D
    s32 target_lock;          // +0x0E
    s32 prev_attack_off;      // +0x12
    u8 type;                  // +0x16
    u8 loss_tier;             // +0x17
    u8 state;                 // +0x18
    u8 _unk19[1] [[color("707070"), comment("dead field: never read/written in PS.EXE; byte-packed struct, so NOT alignment padding")]];  // +0x19
    u8 unit_rank;             // +0x1A
    u8 exists;                // +0x1B
    u8 owner;                 // +0x1C
    s8 morale_a;              // +0x1D
    s8 morale_b;              // +0x1E
    u8 fatigue;               // +0x1F
    u8 combat_order;          // +0x20
    u8 _unk21[1] [[color("707070"), comment("dead field: never read/written in PS.EXE; byte-packed struct, so NOT alignment padding")]];  // +0x21
    u8 prev_x;                // +0x22
    u8 prev_y;                // +0x23
    u8 _unk24 [[color("707070"), comment("dead field: never read/written in PS.EXE; byte-packed struct, so NOT alignment padding")]];  // +0x24
    u8 fatigue_alert;         // +0x25
    u8 has_selected_figs;     // +0x26
    u8 is_target;             // +0x27
    u8 _unk28[2] [[color("707070"), comment("dead field: never read/written in PS.EXE; byte-packed struct, so NOT alignment padding")]];  // +0x28
    u8 regen_tick;            // +0x2A
    u8 _unk2B[1] [[color("707070"), comment("dead field: never read/written in PS.EXE; byte-packed struct, so NOT alignment padding")]];  // +0x2B
    u8 first_figure;          // +0x2C
    u8 last_figure;           // +0x2D
    u8 fig_count;             // +0x2E
    u8 _unk2F [[color("707070"), comment("dead field: never read/written in PS.EXE; byte-packed struct, so NOT alignment padding")]];  // +0x2F
    u8 formation_width;       // +0x30
    u8 formation_cols;        // +0x31
    u8 _init32;               // +0x32
    u8 _unk33 [[color("707070"), comment("dead field: never read/written in PS.EXE; byte-packed struct, so NOT alignment padding")]];  // +0x33
    s8 heading;               // +0x34
    u8 stage_slot;            // +0x35
    u8 formation_mode;        // +0x36
    u8 _unk37[2] [[color("707070"), comment("dead field: never read/written in PS.EXE; byte-packed struct, so NOT alignment padding")]];  // +0x37
    u8 unit_sub_kind;         // +0x39
    u8 attack_marker_x;       // +0x3A
    u8 attack_marker_y;       // +0x3B
    u8 _unk3C [[color("707070"), comment("dead field: never read/written in PS.EXE; byte-packed struct, so NOT alignment padding")]];  // +0x3C
    u8 flank_pending;         // +0x3D
    s16 ai_period;            // +0x3E
    s16 ai_tick;              // +0x40
    u8 manoeuvre_done;        // +0x42
    u8 _reserved43[11] [[color("707070"), comment("dead field: never read/written in PS.EXE; byte-packed struct, so NOT alignment padding")]];  // +0x43
};  // 0x4E = 78 bytes

struct ArrowRec {
    s16 start_x;              // +0x00
    s16 start_y;              // +0x02
    s16 end_x;                // +0x04
    s16 end_y;                // +0x06
    u32 arrow_data_ptr;       // +0x08
    s8 grid_x;                // +0x0C
    s8 grid_y;                // +0x0D
    s32 step_x;               // +0x0E
    s32 step_y;               // +0x12
    s32 step_error;           // +0x16
    u8 sprite_anim;           // +0x1A
    u8 sprite_kind;           // +0x1B
    u8 sprite_base;           // +0x1C
    u8 anim_count;            // +0x1D
    u8 anim_delta;            // +0x1E
    u8 _unk1F[1] [[color("707070"), comment("dead field: never read/written in PS.EXE; byte-packed struct, so NOT alignment padding")]];  // +0x1F
    s8 fire_range;            // +0x20
    u8 flight_done;           // +0x21
    u8 axis_dominant;         // +0x22
    u8 exists;                // +0x23
    u8 flight_age;            // +0x24
    u8 fire_speed;            // +0x25
    u8 weapon_kind;           // +0x26
    u8 heading;               // +0x27
    u8 owner;                 // +0x28
    s32 map_ref;              // +0x29
};  // 0x2D = 45 bytes

struct ArmyRec {
    s8 exists;                // +0x00
    s8 sprite_image;          // +0x01
    u8 sprite_anim;           // +0x02
    u8 sprite_dir;            // +0x03
    s8 type;                  // +0x04
    s8 world_dir;             // +0x05
    s8 x;                     // +0x06
    s8 y;                     // +0x07
    s32 map_ref;              // +0x08
    u8 pixel_x;               // +0x0C
    u8 pixel_y;               // +0x0D
    s8 target_x;              // +0x0E
    s8 target_y;              // +0x0F
    u8 saved_state_idx;       // +0x10
    s8 wait_count;            // +0x11
    s8 state_idx;             // +0x12
    s8 stuck_timer;           // +0x13
    u8 wf_phase;              // +0x14
    u8 wf_active;             // +0x15
    s8 wf_step;               // +0x16
    s8 wf_length;             // +0x17
    u8 wf_steps[8];           // +0x18
    u8 _unk20[2] [[color("707070"), comment("dead field: never read/written in PS.EXE; byte-packed struct, so NOT alignment padding")]];  // +0x20
    u8 heading;               // +0x22
    s8 target_kind;           // +0x23
    s8 target_count;          // +0x24
    s8 flags;                 // +0x25
    u8 return_flag;           // +0x26
    u8 target_flag;           // +0x27
    s8 cohort_id;             // +0x28
    u8 dest_y;                // +0x29
    u8 dest_x;                // +0x2A
    u8 _unk2B[1] [[color("707070"), comment("dead field: never read/written in PS.EXE; byte-packed struct, so NOT alignment padding")]];  // +0x2B
    s32 fort_ref;             // +0x2C
    u8 army_id;               // +0x30
    u8 _unk31 [[color("707070"), comment("dead field: never read/written in PS.EXE; byte-packed struct, so NOT alignment padding")]];  // +0x31
    s16 evolve_timer;         // +0x32
    s16 target_marker;        // +0x34
    s16 map_x;                // +0x36
    s16 map_y;                // +0x38
    s32 departure_year;       // +0x3A
    Century centuries[14];    // +0x3E
    s32 num_horse;            // +0x76
    s32 num_auxillaries;      // +0x7A
    s32 num_irregulars;       // +0x7E
    s32 num_regulars;         // +0x82
    s32 num_specials;         // +0x86
    s32 total_troops;         // +0x8A
    s32 assigned_needs;       // +0x8E
    u8 num_centuries;         // +0x92
    u8 morale_timer;          // +0x93
    u8 morale;                // +0x94
    u8 readiness_level;       // +0x95
    u8 home_x;                // +0x96
    u8 home_y;                // +0x97
    u8 compass_side;          // +0x98
    u8 trader_brings;         // +0x99
    u8 battle_disposition;    // +0x9A
    u8 source_region;         // +0x9B
    u8 landed_flag;           // +0x9C
    u8 tribe_id;              // +0x9D
    u8 quick_respawn;         // +0x9E
    u8 order_progress;        // +0x9F
    u8 cohort_size_class;     // +0xA0
    s16 target_timer;         // +0xA1
    s32 home_ref;             // +0xA3
    u8 _reservedA7[8] [[color("707070"), comment("dead field: never read/written in PS.EXE; byte-packed struct, so NOT alignment padding")]];  // +0xA7
};  // 0xAF = 175 bytes

struct ArmyRouteRec {
    s32 row_count;            // +0x00
    s32 chase_row;            // +0x04
    s32 target_army;          // +0x08
    u8 army_x;                // +0x0C
    u8 army_y;                // +0x0D
    u8 over_x;                // +0x0E
    u8 over_y;                // +0x0F
    u8 row_len[10];           // +0x10
    ArmyRoutePoint points[10][16];// +0x1A
};  // 0x15A = 346 bytes

// ==== misc records ==========================================================

struct ProvinceIndustry {
    s32 kind;                 // +0x00
    s32 is_trader;            // +0x04
    s32 _unk08 [[color("707070"), comment("dead field: never read/written in PS.EXE; byte-packed struct, so NOT alignment padding")]];  // +0x08
    s32 _unk0C [[color("707070"), comment("dead field: never read/written in PS.EXE; byte-packed struct, so NOT alignment padding")]];  // +0x0C
};  // 0x10 = 16 bytes

struct IndustryRec {
    s32 status;               // +0x00
    s32 supply;               // +0x04
    s32 delivered;            // +0x08
    s32 unit_size;            // +0x0C
    s32 count;                // +0x10
    s32 has_supply;           // +0x14
    s32 city_supply;          // +0x18
    s32 supply_pipeline[5];   // +0x1C
};  // 0x30 = 48 bytes

struct SlaveReq {
    s32 current;              // +0x00
    s32 max;                  // +0x04
};  // 0x08 = 8 bytes

struct MsgSlot {
    s32 msg;                  // +0x00
    s32 param;                // +0x04
};  // 0x08 = 8 bytes

struct HutRec {
    u8 x;                     // +0x00
    u8 y;                     // +0x01
    u8 kind;                  // +0x02
};  // 0x03 = 3 bytes

// ==== history-graph row (HistoryRow from caesar2_common.hexpat) =============

// ==== master block layout (savegame_entries[] order) ========================

struct State {
    u8  map_mode;
    u8  ov_map_mode;
    u8  zoom_level;
    u8  zoom_level_2;
    s32 map_direction;
    s32 pm_x;
    s32 pm_y;
    ArmyRec army_list[26];
    CitizenRec citizen_list[201];
    UnitRec unit_list[51];
    FigureRec figure_list[201];
    ArrowRec arrow_list[201];
    ArmyRouteRec army_routes[10];
    CityCell city_map[6400];
    RegionCell region_map[3600];
    s8 fire_zones[100];
    u8  c2inf_byte52;             // single c2inf options byte
    s32 randseed;
    s32 top_lv_spot;
    s32 top_lv;
    s32 top_lv_x;
    s32 top_lv_y;
    s32 evolve_tick4;
    s32 evolve_row;
    s32 evolve_clock;
    s32 year;
    s32 month;
    s32 week;
    s32 denarii;
    s32 pop_tax_rate;
    s32 ind_tax_rate;
    s32 employment_rate;
    s32 population;
    s32 account_total;
    s32 account_pop_tax;
    s32 account_ind_tax;
    s32 account_construction_cost;
    s32 account_operating_cost;
    s32 estimate_total;
    s32 estimate_pop_tax;
    s32 estimate_ind_tax;
    s32 estimate_construction_cost;
    s32 estimate_operating_cost;
    s32 no_of_census_passes;
    s32 population_running_count;
    s32 employment_running_count;
    s32 structure_running_count;
    s32 road_running_count;
    s32 fire_running_count;
    s32 plague_running_count;
    s32 water_running_count;
    s32 region_running_count;
    s32 slaves;
    s32 slave_population_change;
    s32 slave_welfare_bill;
    s32 slave_population_estimate;
    SlaveReq slave_requirements[8];
    s32 slave_random;
    s32 population_pass_count;
    s32 employment_pass_count;
    s32 structure_pass_count;
    s32 road_pass_count;
    s32 fire_pass_count;
    s32 plague_pass_count;
    s32 region_pass_count;
    s32 fountains_pass_count;
    s32 fountains_count;
    s32 supplied_fountains_pass_count;
    s32 supplied_fountains_count;
    s32 baths_pass_count;
    s32 baths_count;
    s32 supplied_baths_pass_count;
    s32 supplied_baths_count;
    s32 large_forums_pass_count;
    s32 large_forums_count;
    s32 medium_forums_pass_count;
    s32 medium_forums_count;
    s32 small_forums_pass_count;
    s32 small_forums_count;
    s32 forts_pass_count;
    s32 forts_count;
    s32 prefectures_pass_count;
    s32 prefectures_count;
    s32 barracks_pass_count;
    s32 barracks_count;
    s32 large_temples_pass_count;
    s32 large_temples_count;
    s32 med_temples_pass_count;
    s32 med_temples_count;
    s32 small_temples_pass_count;
    s32 small_temples_count;
    s32 hospitals_pass_count;
    s32 hospitals_count;
    s32 accessed_hospitals_pass_count;
    s32 accessed_hospitals_count;
    s32 libraries_pass_count;
    s32 libraries_count;
    s32 accessed_libraries_pass_count;
    s32 accessed_libraries_count;
    s32 grammaticus_pass_count;
    s32 grammaticus_count;
    s32 rhetor_pass_count;
    s32 rhetor_count;
    s32 theatre_pass_count;
    s32 theatre_count;
    s32 odium_pass_count;
    s32 odium_count;
    s32 arena_pass_count;
    s32 arena_count;
    s32 colosseum_pass_count;
    s32 colosseum_count;
    s32 circus_pass_count;
    s32 circus_count;
    s32 circus_maximus_pass_count;
    s32 circus_maximus_count;
    s32 business_pass_count;
    s32 business_count;
    s32 market_pass_count;
    s32 market_count;
    s32 water_trouble_rate;
    s32 road_rate;
    s32 road_accident;
    s32 fire_rate;
    s32 fire_accident;
    s32 wall_rate;
    s32 wall_accident;
    s32 region_rate;
    s32 region_accident;
    s32 fire_spread_direction;
    s32 fire_spread_count;
    s32 fire_spread_target;
    s32 plague_spread_direction;
    s32 plague_spread_count;
    s32 plague_spread_target;
    s32 hospital_cover;
    s32 library_cover;
    s32 plague_accident;
    s32 revolt_accident;
    s32 shell_push_direction;
    s32 pop_growth_factor;
    s32 ind_growth_factor;
    s32 insurrection_factor;
    s32 pop_growth_future;
    s32 ind_growth_future;
    s32 insurrection_future;
    s32 conscription_rate;
    s32 employees;
    s32 pop_income_pass_count;
    s32 pop_tax_running_total;
    s32 pop_tax_last_count;
    s32 pop_tax_counts;
    s32 ind_income_pass_count;
    s32 ind_tax_running_total;
    s32 ind_tax_last_count;
    s32 ind_tax_counts;
    s32 current_construction_cost;
    s32 current_operating_cost;
    s32 account_tribute;
    s32 estimate_tribute;
    s32 income_multiple;
    s32 average_pop_tax_denariis;
    s32 average_pop_tax_asses;
    s32 average_ind_tax_denariis;
    s32 average_ind_tax_asses;
    s32 tribute;
    s32 last_tribute;
    s32 unrest_random_count;
    s32 no_of_rioters;
    s32 no_of_barbarians;
    s32 free_message_ptr;
    s32 show_message_ptr;
    MsgSlot message_list[8];
    u8  warned_of_fire;
    u8  warned_of_cutbacks;
    u8  warned_of_robbery;
    u8  warned_of_emperor;
    u8  warned_of_emperor_reply_month;
    u8  warned_of_emperor_reply_level;
    u8  warned_of_free4;
    u8  warned_of_free5;
    s32 large_robbery_pass_count;
    s32 large_robbery_count;
    s32 med_robbery_pass_count;
    s32 med_robbery_count;
    s32 small_robbery_pass_count;
    s32 small_robbery_count;
    s32 temples_count;
    s32 robbery_count;
    s32 stolen_denarii;
    s32 reg_city_x;
    s32 reg_city_y;
    s32 our_battle_army;
    s32 their_battle_army;
    s32 forum_viewed_army;
    s32 army_wage_level;
    s32 conscription_rate_2;
    s32 total_no_of_cohorts;
    s32 total_no_of_centuries;
    s32 total_no_of_soldiers;
    s32 total_no_of_regulars;
    s32 total_no_of_irregulars;
    s32 total_no_of_auxillaries;
    s32 current_no_of_centuries;
    s32 current_no_of_soldiers;
    s32 current_no_of_regulars;
    s32 current_no_of_irregulars;
    s32 current_no_of_auxillaries;
    s32 needed_no_of_centuries;
    s32 needed_no_of_soldiers;
    s32 needed_no_of_regulars;
    s32 needed_no_of_irregulars;
    s32 needed_no_of_auxillaries;
    s32 average_cohort_morale;
    s32 average_cohort_readiness;
    s32 last_adjusted_cohort;
    s32 west_border_x;
    s32 west_border_y;
    s32 east_border_x;
    s32 east_border_y;
    s32 north_border_x;
    s32 north_border_y;
    s32 south_border_x;
    s32 south_border_y;
    s32 province_is;
    s32 north_trader_count0;
    s32 east_trader_count0;
    s32 south_trader_count0;
    s32 west_trader_count0;
    s32 north_trader_brings;
    s32 east_trader_brings;
    s32 south_trader_brings;
    s32 west_trader_brings;
    s32 north_trader_is;
    s32 east_trader_is;
    s32 south_trader_is;
    s32 west_trader_is;
    s32 north_trader_count1;
    s32 east_trader_count1;
    s32 south_trader_count1;
    s32 west_trader_count1;
    s32 no_of_workcamps;
    s32 no_of_warehouses;
    s32 no_of_shipyards;
    s32 no_of_ports;
    s32 no_of_trading_posts;
    s32 no_of_farms;
    s32 no_of_mines;
    s32 no_of_quarrys;
    s32 no_of_villages;
    s32 no_of_towns;
    s32 no_of_border_towns;
    s32 months_to_game_over;
    u8  old_map_mode;
    u8  old_zoom_level;
    s32 battle_state;
    BattleCell battle_map[2704];
    s32 city_pm_x;
    s32 city_pm_y;
    s32 region_pm_x;
    s32 region_pm_y;
    s32 battle_pm_x;
    s32 battle_pm_y;
    s32 city_direction;
    s32 region_direction;
    s32 battle_direction;
    s32 battle_scale;
    s32 our_battle_men;
    s32 our_battle_start_men;
    s32 their_battle_men;
    s32 their_battle_start_men;
    s32 our_battle_routs;
    s32 their_battle_routs;
    s32 our_battle_stance;
    s32 their_battle_stance;
    s32 battle_npc_retreat_count;
    s32 retreat_flag;
    s32 no_of_empire_connections;
    s32 empire_connections;
    s32 battle_over_count;
    s32 our_battle_morale;
    s32 their_battle_morale;
    s32 our_battle_units;
    s32 their_battle_units;
    u8 empire[50];
    s32 completed_provinces;
    s32 auto_conquered;
    s32 empire_rating;
    s32 peace_rating;
    s32 prosperity_rating;
    s32 culture_rating;
    s32 pax_romanum;
    s32 player_rank;
    s32 large_temples_culture_pass_count;
    s32 large_temples_culture_count;
    s32 med_temples_culture_pass_count;
    s32 med_temples_culture_count;
    s32 small_temples_culture_pass_count;
    s32 small_temples_culture_count;
    s32 theatre_culture_pass_count;
    s32 theatre_culture_count;
    s32 odium_culture_pass_count;
    s32 odium_culture_count;
    s32 arena_culture_pass_count;
    s32 arena_culture_count;
    s32 colosseum_culture_pass_count;
    s32 colosseum_culture_count;
    s32 circus_culture_pass_count;
    s32 circus_culture_count;
    s32 circus_maximus_culture_pass_count;
    s32 circus_maximus_culture_count;
    s32 grammaticus_culture_pass_count;
    s32 grammaticus_culture_count;
    s32 plaza_culture_count;
    s32 plaza_culture_pass_count;
    s32 gardens_culture_count;
    s32 gardens_culture_pass_count;
    s32 rhetor_culture_pass_count;
    s32 rhetor_culture_count;
    s32 refused_promotion;
    s32 entertainment_level;
    s32 religion_level;
    s32 utility_level;
    s32 rolling_profit;
    s32 current_gdp;
    s32 no_of_connected_towns;
    s32 start_year;
    s32 years_elapsed;
    s32 months_since_last_war;
    s32 months_since_last_horde;
    s32 months_since_last_raider;
    s32 months_since_last_revolt;
    s32 years_elapsed_in_region;
    HutRec hut_list[4];
    s32 roman_name_count;
    s32 barbarian_name_count;
    ProvinceIndustry province_industries[8];// 128B symbol (8 records)
    u8  _industry_overshoot[128] [[color("707070"), comment("{ province_industries, 256 } over-reads 128B into industry[]; re-saved by the next block (message_list-style double store)")]];
    s32 history_end_ptr;
    s32 history_start_ptr;
    s32 history_entries;
    IndustryRec industry[16];
    s32 imperial_favour;
    s32 imperial_request;
    s32 imperial_review;
    s32 imperial_req_goods;
    s32 imperial_req_amount;
    s32 av_imperial_gift_level;
    s32 our_battle_specials;
    s32 our_battle_horse;
    s32 our_battle_regs;
    s32 our_battle_irregs;
    s32 our_battle_auxs;
    s32 their_battle_specials;
    s32 their_battle_horse;
    s32 their_battle_regs;
    s32 their_battle_irregs;
    s32 their_battle_auxs;
    s32 mercs_in_army;
    s32 max_mercs_allowed;
    s32 mercs_type;
    s32 mercs_from;
    s32 mercs_cost_per_50;
    s32 current_no_of_specials;
    s32 needed_no_of_specials;
    s32 total_no_of_specials;
    s32 mercs_catagory;
    s32 mercs_tribe;
    s32 mercs_speed;
    s32 mercs_missile;
    s32 battle_type;
    s32 battle2_ptr;
    s32 game_state;
    s32 return_zoom_level;
    s32 return_map_mode;
    s32 shell_wall_flag;
    s32 shell_last_value;
    MsgSlot message_list_2[16];
    s32 average_rating;
    s32 empire_rating_pop_limit;
    s32 peace_rating_pop_limit;
    s32 prosperity_rating_pop_limit;
    s32 culture_rating_pop_limit;
    s32 no_of_city_flags;
    s32 no_of_prov_flags;
    s32 no_of_danger_flags;
    s32 last_city_flag;
    s32 last_prov_flag;
    s32 last_danger_flag;
    s32 city_flag_list[20];
    s32 prov_flag_list[20];
    s32 danger_flag_list[20];
    s32 danger_flag_map_mode;
    s32 flag_mode_decay_count;
    s32 last_years_population;
    s32 this_years_population;
    s32 last_years_denarii;
    s32 this_years_denarii;
    s32 last_years_pop_tax;
    s32 this_years_pop_tax;
    s32 last_years_ind_tax;
    s32 this_years_ind_tax;
    s32 pop_growth_extra;
    s32 pop_growth_extra_count;
    s32 players_denarii;
    s32 players_salary;
    s32 donation_level;
    s32 evolve_tick3;
    u8  c2inf_byte53;             // single c2inf options byte
    s32 months_since_last_city_attack;
    s32 auto_conquered_months;
    s32 max_population;
    s32 warned_city_size;
    s32 warned_new_struct;
    s32 last_city_mood;
    s32 last_battle_mood;
    s32 empire_won[50];
    s32 final_bribe;
    s32 province_difficulty;
    s32 total_amount_of_bribes;
    s32 total_no_of_bribes;
    s32 bat_tribe;
    s32 battle_ai_count;
    s32 moving_tribute;
    s32 imperial_tax;
    s32 last_imperial_tax_amount;
    s32 total_imperial_taxes;
    s32 last_imperial_tax_percent;
    s32 city_rotation;
    s32 city_zoom_level;
    s32 prov_rotation;
    s32 prov_zoom_level;
    s32 arena_top_count;
    s32 colosseum_top_count;
    s32 reserved_expansion[68] [[color("707070"), comment("68x reserved { &dummy_sav, 4 } expansion slots; not used state")]];
};

struct Savegame {
    State       state;          // 221,745 b  (500 registered blocks)
    HistoryRow  history[200];   //   4,000 b  (history.dat ring buffer tail)
};

Savegame file @ 0x00;
