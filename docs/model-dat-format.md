# Caesar II `C2MODEL.DAT` Format (game-balance "model" tables)

> ImHex pattern: [`tools/imhex/caesar2_model.hexpat`](../tools/imhex/caesar2_model.hexpat).

## Overview

`C2MODEL.DAT` (4360 bytes) is a flat dump of the game's **balance / difficulty tuning
tables** — the `model_entries[]` blocks in `datainit.c`, written back-to-back in table
order with **no header** (the same block-dump scheme as a `.SAV`). It holds the skill
curves, building costs, population/economy growth data, revolt/unrest tables, troop
numbers, promotion thresholds, and tax/tribute data.

## The fossil

The game **never loads it.** `loadmodel` (the function that would read `C2MODEL.DAT` back
into those globals) has **zero callers anywhere in PS.EXE**, and the string
`"c2model.dat"` appears **nowhere** in the binary. The shipped game uses the values
**baked into the executable** (the `datainit.c` defaults) instead. `C2MODEL.DAT` is a
**shipped-but-unused fossil** — almost certainly the external tuning file an earlier build
(or the design tools) loaded via `loadmodel`, left on the CD after the data was inlined.

It is even a *different* snapshot: of the 30 blocks that can be compared field-for-field,
**19 are identical** to the EXE defaults and **11 differ** — `skill_to_trouble_debar`,
`tax_to_revolt_data`, `conscription_to_revolt_data`, `house_type_to_unrest`,
`unrest_random_data`, `tribe_to_troop_numbers`, `promotion_levels`, `promotion_av_levels`,
`init_slave_data`, `tax_rates`, `tribute_adjust` (e.g. `tax_to_revolt_data` has `-4` where
the EXE has `-6`). So `C2MODEL.DAT` preserves a balance pass that diverged from the final
shipped values.

## Layout

```
Offset  Size   Block                              Notes
------  ----   -----                              -----
+0x000  20     skill_to_imperial_request          int[5]  (per difficulty 0..4)
+0x014  20     skill_to_starting_denarii          int[5]
+0x028  20     skill_to_denarii_reduction         int[5]
+0x03C  80     skill_to_trouble_honeymoons        int[20]
+0x08C  80     skill_to_trouble_frequency         int[20]
+0x0DC  80     skill_to_trouble_debar             int[20]
+0x12C  80     skill_to_city_attacks              int[20]
+0x17C  400    city_costs                         int[100]
+0x30C  80     region_costs                       int[20]
+0x35C  128    houses_to_people                   int[32]
+0x3DC  128    houses_to_income                   int[32]
+0x45C  104    pop_tax_to_growth_data             int[26]
+0x4C4  84     employment_to_pop_growth_factor    int[21]
+0x518  104    ind_tax_to_growth_data             int[26]
+0x580  104    tax_to_revolt_data                 int[26]
+0x5E8  104    conscription_to_revolt_data        int[26]
+0x650  128    house_type_to_unrest               int[32]
+0x6D0  256    unrest_random_data                 int[64]
+0x7D0  256    house_lv_effect                    int[64]
+0x8D0  96     forum_lv_effect                    int[24]
+0x930  96     temple_lv_effect                   int[24]
+0x990  480    tribe_to_troop_numbers             24 x troop_numbers_rec (20 B)
+0xB70  224    buildings_lv_effect                int[56]
+0xC50  8      init_salary                        salary_rec (welfare_bill, slaves)
+0xC58  400    promotion_levels                   int[100]
+0xDE8  400    promotion_av_levels                int[100]
+0xF78  80     init_slave_data                    10 x salary_rec
+0xFC8  40     main_paras                         struct (mixed); see entities.h
+0xFF0  12     tax_triggers                       int[3]
+0xFFC  240    tax_rates                          int[60]
+0x10EC 28     tribute_adjust                     int[7]
                                                  --- ends at 0x1108 = 4360 ---
```

`model_entries[]` actually has 40 slots; entries 31–39 are `{ 0, 0 }` terminators
(`loadmodel` stops at the first zero-size block), so only the 31 blocks above are written.

## Loading (vestigial)

```c
int loadmodel(char *fname) {              // loadsave.c -- never called
    fd = open(fname, O_RDONLY);
    for (i = 0; i < 100; i++) {
        if (model_entries[i].size == 0) break;
        read(fd, model_entries[i].buf, model_entries[i].size);
    }
    close(fd);
    return 1;
}
```

Same block-iteration shape as `loadgame`, but applied to the tuning tables rather than the
live game state.
