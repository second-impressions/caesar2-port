#pragma description Caesar II C2MODEL.DAT (game-balance "model" tuning tables)
#pragma endian little

// ---------------------------------------------------------------------------
// Caesar II C2MODEL.DAT -- a flat dump of the 31 game-balance / difficulty
// tuning tables registered in model_entries[] (datainit.c), in table order,
// NO header (same block-dump scheme as a *.SAV).  4360 bytes total.
//
// loadmodel() would read this back into those globals, BUT it has ZERO callers
// anywhere in PS.EXE and the name "c2model.dat" appears nowhere in the binary,
// so the shipped game NEVER loads it -- it uses the baked-in datainit.c
// defaults instead.  C2MODEL.DAT is a shipped-but-unused fossil; 11 of its 30
// comparable blocks even differ from the final EXE values (a different tuning
// snapshot).  See docs/model-dat-format.md.
// ---------------------------------------------------------------------------

struct Model {
    s32 skill_to_imperial_request[5];         // 20 B
    s32 skill_to_starting_denarii[5];         // 20 B
    s32 skill_to_denarii_reduction[5];        // 20 B
    s32 skill_to_trouble_honeymoons[20];      // 80 B
    s32 skill_to_trouble_frequency[20];       // 80 B
    s32 skill_to_trouble_debar[20];           // 80 B
    s32 skill_to_city_attacks[20];            // 80 B
    s32 city_costs[100];                      // 400 B
    s32 region_costs[20];                     // 80 B
    s32 houses_to_people[32];                 // 128 B
    s32 houses_to_income[32];                 // 128 B
    s32 pop_tax_to_growth_data[26];           // 104 B
    s32 employment_to_pop_growth_factor[21];  // 84 B
    s32 ind_tax_to_growth_data[26];           // 104 B
    s32 tax_to_revolt_data[26];               // 104 B
    s32 conscription_to_revolt_data[26];      // 104 B
    s32 house_type_to_unrest[32];             // 128 B
    s32 unrest_random_data[64];               // 256 B
    s32 house_lv_effect[64];                  // 256 B
    s32 forum_lv_effect[24];                  // 96 B
    s32 temple_lv_effect[24];                 // 96 B
    s32 tribe_to_troop_numbers[120];          // 24 x troop_numbers_rec (20B); see entities.h
    s32 buildings_lv_effect[56];              // 224 B
    s32 init_salary[2];                       // salary_rec (welfare_bill,slaves)
    s32 promotion_levels[100];                // 400 B
    s32 promotion_av_levels[100];             // 400 B
    s32 init_slave_data[20];                  // 10 x salary_rec
    s32 main_paras[10];                       // struct (mixed); see entities.h
    s32 tax_triggers[3];                      // 12 B
    s32 tax_rates[60];                        // 240 B
    s32 tribute_adjust[7];                    // 28 B
};

Model file @ 0x00;
