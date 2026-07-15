// D:\C2\CODE\map.c

#include "c2_data.h"

/* ── TU-owned file-scope variables (PS.EXE _BSS, original declaration
   order).  Recovered so the functional rebuild (`c2 rebuild`) links
   self-sustained -- no auto-stubbed storage.  Extern decls: c2_data.h. */
struct byte_point_rec temp_route[16];

extern void copy(unsigned char *src, unsigned char *dst, int n);

// FUNCTION: C2 0x65F4C
// WIN: 0x0049f830
// Lines 165–193
//
// Initial city-map geography clear + scrub/river generation.
// Clears every per-cell layer in a specific order (matching PS's
// `mov eax, K; call clear_all_cm` sequence), then seeds scrub on
// top.  Up to six attempts are made to lay a river: if
// generate_cm_river succeeds (non-zero return) the routine
// commits; otherwise the scrub is re-rolled and another attempt
// is made.
void generate_city_map_geography(void)
{
    int tries;

    tries = 5;
    clear_all_cm(2);
    clear_all_cm(1);
    clear_all_cm(3);
    clear_all_cm(9);
    clear_all_cm(0x10);
    clear_all_cm(tries);
    clear_all_cm(6);
    clear_all_cm(7);
    clear_all_cm(8);
    clear_all_cm(0xf);
    clear_all_cm(0xd);
    clear_all_cm(0xe);
    clear_all_cm(0xa);
    clear_all_cm(0xb);
    clear_all_cm(0xc);
    clear_all_cm(4);
    clear_all_cm(0x11);
    generate_cm_scrub();
    while (generate_cm_river() == 0) {
        generate_cm_scrub();
        tries--;
        if (tries == -1) break;
    }
}

// FUNCTION: C2 0x66014
// WIN: 0x0049f923
// Lines 195–268
//
// Trace one river path across the 80×80 city_map.  The path
// is a random walk biased to flow southward; each visited
// cell is flagged as a "river atom" (city_map[+1] |= 0x10
// and city_map[+0] = 4) for the flesh_river_atoms pass to
// turn into concrete tiles.
//
// State:
//   x, y, cm_sptr     — current grid position + byte offset.
//   gmn_*              — mirror of (x, y, cm_sptr) used by
//                       test_citymap_neighbours_negedge to
//                       look one step ahead.
//   esi (east_count)   — consecutive south-step counter
//                       (named for the asm convention; the
//                       counter actually tracks dir==4 steps).
//   ebx (cur_dir)      — next-step direction (0/2/4/6), 8 =
//                       "skip step this iteration".
//   edx (prev_dir)     — last accepted direction (used to
//                       reject 180° reverses).
//   edi (budget)       — step budget (initial 0x3C0 = 960).
//
// Algorithm:
//   1. Pick a start at (x = 24 + rand128 & 0x1F, y = 0);
//      cm_sptr = (x + y * 80) * 20.  Mark the cell as a river atom.
//   2. Start direction = 4 (south); reset prev_dir, east_count.
//   3. Each iteration decrements budget; if it drops below 0,
//      finish.  cur_dir of 0/2/4/6 steps north/east/south/west
//      respectively and re-marks the new cell.  cur_dir == 8
//      is the "skip" token — leaves position unchanged.
//   4. After stepping, re-sync gmn_* from x/y/cm_sptr.  If
//      x or y hits a map edge (0 or 79), end the walk.
//   5. Roll a new candidate direction: rand128 & 3, then
//      multiplied by 2 → 0/2/4/6.
//      - Candidate 0 (north): only allowed when east_count >= 4
//        (i.e. we've gone south enough to balance back up).
//      - Reject 180° reverses (candidate == prev_dir).
//      - Pre-step gmn_x/y/sptr to the candidate cell and call
//        test_citymap_neighbours_negedge(0x10).  If the
//        candidate cell touches more than two existing river
//        atoms, reject (would form a loop).
//      - On acceptance: prev_dir = (candidate + 4) & 7;
//        cur_dir = candidate.  If candidate == 4 (south),
//        east_count++; if 0 (north), reset east_count.
//   6. After loop end, if budget > 0 (didn't dead-end), call
//      flesh_river_atoms() to materialise the tiles.
//   7. Return budget remaining.
int generate_cm_river(void)
{
    int cur_dir;
    int prev_dir;
    int east_count;
    int budget;
    int cand;

    budget = 0x3c0;
    random();

    y = 0;
    x = 24;
    x += rand128 & 0x1f;
    cm_sptr = (x + y * 80) * 20;

    gmn_x    = x;
    gmn_y    = y;
    gmn_sptr = cm_sptr;

    (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).terrain |= 0x10;
    (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).base_kind  = 4;

    east_count = 0;
    prev_dir   = 0;
    cur_dir    = 4;

    for (;;) {
        if (--budget == -1) break;

        if (cur_dir == 0) {
            y--;  cm_sptr -= 0x640;
            (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).terrain |= 0x10;
            (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).base_kind  = cur_dir;
        } else if (cur_dir == 2) {
            x++;  cm_sptr += 0x14;
            (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).terrain |= 0x10;
            (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).base_kind  = cur_dir;
        } else if (cur_dir == 4) {
            y++;  cm_sptr += 0x640;
            (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).terrain |= 0x10;
            (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).base_kind  = cur_dir;
        } else if (cur_dir == 6) {
            x--;  cm_sptr -= 0x14;
            (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).terrain |= 0x10;
            (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).base_kind  = cur_dir;
        }

        gmn_x    = x;
        gmn_y    = y;
        gmn_sptr = cm_sptr;

        if (x == 0 || y == 0 || x >= 0x4f || y >= 0x4f) break;

        random();
        cand = (rand128 & 3) * 2;

        if (cand == 0 && east_count < 4) {
            cur_dir = 8;
            continue;
        }
        if (cand == prev_dir) {
            cur_dir = 8;
            continue;
        }

        if (cand == 0) {
            gmn_y--; gmn_sptr -= 0x640;
        } else if (cand == 2) {
            gmn_x++; gmn_sptr += 0x14;
        } else if (cand == 4) {
            gmn_y++; gmn_sptr += 0x640;
        } else if (cand == 6) {
            gmn_x--; gmn_sptr -= 0x14;
        }

        test_citymap_neighbours_negedge(0x10);
        if (gmn_count > 2) {
            cur_dir = 8;
            continue;
        }

        cur_dir  = cand;
        prev_dir = (cand + 4) % 8;
        if (cand == 4) east_count++;
        if (cand == 0) east_count = 0;
    }

    if (budget != 0) {
        flesh_river_atoms();
    }
    return budget;
}

// FUNCTION: C2 0x6623D
// WIN: 0x0049fc8b
// Lines 270–281
//
// Initial-state generator for the city map's scrub layer.
// Sets every cell's `base_kind` (byte 0) to a random scrub
// tile in 8..23 (8 + (rand128 & 0xf)).  Calls random() once
// per cell to advance the PRNG state, then reads the resulting
// rand128 byte.  Advances cm_sptr by 20 (cell stride) per
// iteration; full sweep is 80×80 = 6400 cells.
void generate_cm_scrub(void)
{
    int xi;
    int yi;

    cm_sptr = 0;
    for (yi = 0; yi < 80; yi++) {
        for (xi = 0; xi < 80; xi++, cm_sptr += 20) {
            int v;
            random();
            v = rand128 & 0xf;
            (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).base_kind = (v + 8);
        }
    }
}

// FUNCTION: C2 0x66281
// WIN: 0x0049fd08
// Lines 284–309
//
// Second pass of river generation: walk every city_cell on
// the 80×80 map, and for cells flagged with the river-atom
// bit ((*(struct city_cell *)((unsigned char *)city_map + (cell))).terrain & 0x10) substitute a concrete river
// tile id chosen from river_data based on the cell's current
// terrain id and its neighbour mask.
//
//   1. test_citymap_neighbours_posedge(0x10) populates the
//      choice_info/first_choice/choice_count globals from the
//      mask of neighbours that also carry the 0x10 bit.
//
//   2. choose_from(river_data, 6) picks one of 6 river
//      variants; bail if choose_from returns 0.
//
//   3. If the running first_choice doesn't already match the
//      cell's terrain (choice_info), rewrite first_choice via
//      a 6-way remap so subsequent neighbour stamps land on
//      the variant that matches the running edge orientation:
//          0x26 → 0x2A,  0x1E → 0x22,  0x36 → 0x2E,
//          0x46 → 0x42,  0x3A → 0x32,  0x4A → 0x3E.
//
//   4. (*(struct city_cell *)((unsigned char *)city_map + (cell))).base_kind = first_choice + choice_count
//      (tile id picked from the row indexed by first_choice).
//
//   5. If the picked variant id > 2 (mid-stream tiles), set
//      the 0x08 flag in (*(struct city_cell *)((unsigned char *)city_map + (cell))).terrain to mark it for the
//      downstream stamp pass.
void flesh_river_atoms(void)
{
    unsigned char terrain;
    unsigned char variant;

    gmn_y    = 0;
    gmn_sptr = 0;

    for ( ; gmn_y < 0x50; gmn_y++) {
        gmn_x = 0;
        do {
            if ((*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).terrain & 0x10) {
                test_citymap_neighbours_posedge(0x10);
                terrain = (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).base_kind;
                variant = (unsigned char)choose_from(river_data, 6);

                if (variant != 0) {
                    if (terrain != choice_info) {
                        if (first_choice == 0x26) first_choice = 0x2a;
                        else if (first_choice == 0x1e) first_choice = 0x22;
                        else if (first_choice == 0x36) first_choice = 0x2e;
                        else if (first_choice == 0x46) first_choice = 0x42;
                        else if (first_choice == 0x3a) first_choice = 0x32;
                        else if (first_choice == 0x4a) first_choice = 0x3e;
                    }
                    (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).base_kind = first_choice + choice_count;
                    if (variant > 2) (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).terrain |= 8;
                }
            }

            gmn_x++;
            gmn_sptr += 0x14;
        } while (gmn_x < 0x50);
    }
}

// FUNCTION: C2 0x663AB
// WIN: 0x0049febf
// Lines 319–383
//
// BFS layer pass for the city-map elastic preview.  Called
// from get_road_elastic, get_wall_elastic and
// get_aquaduct_elastic with r = 1, 2, 3, … to expand the
// candidate-slot stamp (city_map[+2]) outward from
// (act_start_x, act_start_y) one ring at a time.
//
// Visits cells in the clipped 80×80 bounding box of side
// 2*r+1 around (act_start_x, act_start_y).  Per cell:
//   * If cm[+1] & reject_mask          → cm[+2] = 0xFF
//   * Else if cm[+7] != 0 || cm[+8] != 0 → cm[+2] = 0xFF
//   * Else if cm[+2] != 0              → leave alone
//   * Else: read the four neighbour [+2] slot bytes; if any
//     neighbour slot is non-zero AND < r+1, stamp
//     cm[+2] = r+1.
//
// Two emission paths, chosen by whether any clipping was
// required:
//   * Bbox fits entirely inside [0..0x50) on both axes
//     → fast path with unchecked neighbour reads
//       (cells on the iteration border are already > 0 in
//       on the relevant axis, so unchecked reads stay on
//       city_map).
//   * Any edge clipped → bounds-checked path that gates
//     each neighbour read on its respective edge test.
//
// Neighbour slot byte offsets from cm:
//   N → -0x63E,  E → +0x16,  S → +0x642,  W → -0x12.
void test_elastic_range(int r, unsigned char reject_mask)
{
    int x_min;
    int y_min;
    int needs_bounds;
    int x_span;
    int stride;
    int side;
    unsigned char neigh;

    needs_bounds = 0;
    x_min = act_start_x - r;
    y_min = act_start_y - r;
    side = 2 * r + 1;
    x_span = side;
    if (x_min <= 0) {
        x_span += x_min;
        x_min = 0;
        needs_bounds = 1;
    } else if (x_span + x_min > 0x50) {
        x_span -= x_span + x_min - 0x50;
        needs_bounds = 1;
    }
    if (y_min <= 0) {
        side += y_min;
        y_min = 0;
        needs_bounds = 1;
    } else if (side + y_min >= 0x50) {
        side -= side + y_min - 0x50;
        needs_bounds = 1;
    }

    gmn_sptr = ((x_min) + (y_min) * 80) * 20;
    stride = (0x50 - x_span) * 20;

    if (!needs_bounds) {
        gmn_y = y_min;
        for ( ; gmn_y < y_min + side; gmn_y++, gmn_sptr += stride) {
            gmn_x = x_min;
            for ( ; gmn_x < x_min + x_span; gmn_x++, gmn_sptr += 20) {
                if ((*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).terrain & reject_mask) {
                    (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).road_aqueduct = 0xff;
                    continue;
                }
                if ((*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).citizen_a != 0) {
                    (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).road_aqueduct = 0xff;
                    continue;
                }
                if ((*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).citizen_b != 0) {
                    (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).road_aqueduct = 0xff;
                    continue;
                }
                if ((*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).road_aqueduct != 0)
                    continue;
                neigh = (*(struct city_cell *)((unsigned char *)city_map + ((gmn_sptr) - CITY_ROW))).road_aqueduct;
                if (neigh != 0 && neigh < r + 1) {
                    (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).road_aqueduct = (unsigned char)(r + 1);
                    continue;
                }
                neigh = (*(struct city_cell *)((unsigned char *)city_map + ((gmn_sptr) + CITY_CELL_BYTES))).road_aqueduct;
                if (neigh != 0 && neigh < r + 1) {
                    (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).road_aqueduct = (unsigned char)(r + 1);
                    continue;
                }
                neigh = (*(struct city_cell *)((unsigned char *)city_map + ((gmn_sptr) + CITY_ROW))).road_aqueduct;
                if (neigh != 0 && neigh < r + 1) {
                    (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).road_aqueduct = (unsigned char)(r + 1);
                    continue;
                }
                neigh = (*(struct city_cell *)((unsigned char *)city_map + ((gmn_sptr) - CITY_CELL_BYTES))).road_aqueduct;
                if (neigh != 0 && neigh < r + 1) {
                    (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).road_aqueduct = (unsigned char)(r + 1);
                }
            }
        }
    } else {
        gmn_y = y_min;
        for ( ; gmn_y < y_min + side; gmn_y++, gmn_sptr += stride) {
            gmn_x = x_min;
            for ( ; gmn_x < x_min + x_span; gmn_x++, gmn_sptr += 20) {
                if ((*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).road_aqueduct != 0)
                    continue;
                if ((*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).terrain & reject_mask) {
                    (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).road_aqueduct = 0xff;
                    continue;
                }
                if (gmn_y > 0)
                    neigh = (*(struct city_cell *)((unsigned char *)city_map + ((gmn_sptr) - CITY_ROW))).road_aqueduct;
                else
                    neigh = 0;
                if (neigh != 0 && neigh < r + 1) {
                    (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).road_aqueduct = (unsigned char)(r + 1);
                    continue;
                }
                if (gmn_x < 0x4f)
                    neigh = (*(struct city_cell *)((unsigned char *)city_map + ((gmn_sptr) + CITY_CELL_BYTES))).road_aqueduct;
                else
                    neigh = 0;
                if (neigh != 0 && neigh < r + 1) {
                    (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).road_aqueduct = (unsigned char)(r + 1);
                    continue;
                }
                if (gmn_y < 0x4f)
                    neigh = (*(struct city_cell *)((unsigned char *)city_map + ((gmn_sptr) + CITY_ROW))).road_aqueduct;
                else
                    neigh = 0;
                if (neigh != 0 && neigh < r + 1) {
                    (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).road_aqueduct = (unsigned char)(r + 1);
                    continue;
                }
                if (gmn_x > 0)
                    neigh = (*(struct city_cell *)((unsigned char *)city_map + ((gmn_sptr) - CITY_CELL_BYTES))).road_aqueduct;
                else
                    neigh = 0;
                if (neigh != 0 && neigh < r + 1) {
                    (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).road_aqueduct = (unsigned char)(r + 1);
                }
            }
        }
    }
}

// FUNCTION: C2 0x666A4
// WIN: 0x004a03c4
// Lines 386–432
//
// Among the four neighbouring city-map cells around byte offset `ptr`,
// pick the non-zero elastic byte (+2) with the lowest value, respecting
// map bounds.  Search starts at `dirc` and wraps through all directions;
// results are published in best_elastic_value/best_elastic_dirc.
void get_best_elastic_value(int x, int y, int ptr, int dirc)
{
    int i;
    int dir = dirc;
    unsigned char v;

    best_elastic_value = 100;
    best_elastic_dirc = 0;
    i = 0;
    while (i++ < 4) {
        if (dir == 0) {
            if (y > 0) {
                v = (*(struct city_cell *)((unsigned char *)city_map + ((ptr) - CITY_ROW))).road_aqueduct;
                if (v != 0 && v < best_elastic_value) {
                    best_elastic_value = v;
                    best_elastic_dirc = 0;
                }
            }
        } else if (dir == 1) {
            if (x < 79) {
                v = (*(struct city_cell *)((unsigned char *)city_map + ((ptr) + CITY_CELL_BYTES))).road_aqueduct;
                if (v != 0 && v < best_elastic_value) {
                    best_elastic_value = v;
                    best_elastic_dirc = 1;
                }
            }
        } else if (dir == 2) {
            if (y < 79) {
                v = (*(struct city_cell *)((unsigned char *)city_map + ((ptr) + CITY_ROW))).road_aqueduct;
                if (v != 0 && v < best_elastic_value) {
                    best_elastic_value = v;
                    best_elastic_dirc = 2;
                }
            }
        } else if (dir == 3) {
            if (x > 0) {
                v = (*(struct city_cell *)((unsigned char *)city_map + ((ptr) - CITY_CELL_BYTES))).road_aqueduct;
                if (v != 0 && v < best_elastic_value) {
                    best_elastic_value = v;
                    best_elastic_dirc = 3;
                }
            }
        }
        dir++;
        if (dir > 3) dir = 0;
    }
}

// FUNCTION: C2 0x6675A
// WIN: 0x004a0576
// Lines 434–501
//
// BFS layer pass for the region-map elastic preview;
// region-map twin of test_elastic_range.  Called from
// get_reg_road_elastic with strict=0 and from
// get_reg_wall_elastic with strict=1, both with reject_mask
// = 0xD9.
//
// Visits cells in the clipped 60×60 bbox of side 2*r+1
// around (act_start_x, act_start_y).  Per cell:
//   * cm[+1] & reject_mask                  → cm[+2] = 0xFF
//   * cm[+7] != 0 AND (strict == 0 OR
//       cm[+1] & 0x17 != 0)                 → cm[+2] = 0xFF
//   * cm[+2] != 0                           → leave alone
//   * else: read four neighbour [+2] slot bytes (offsets
//     N=-0x1DE, E=+0xA, S=+0x1E2, W=-6).  If any is
//     non-zero AND < r+1, stamp cm[+2] = r+1.
//
// Two emission paths chosen by whether any axis required
// clipping (left/top ≤ 0 or right/bottom > 0x3C); the alt
// path gates each neighbour read on the corresponding edge
// test.
void test_rm_elastic_range(int strict, int r, unsigned char reject_mask)
{
    int x_min;
    int y_min;
    int needs_bounds;
    int x_span;
    int stride;
    int side;
    unsigned char neigh;

    needs_bounds = 0;
    x_min = act_start_x - r;
    y_min = act_start_y - r;
    side  = 2 * r + 1;
    x_span = side;
    if (x_min <= 0) {
        x_span += x_min;
        x_min = 0;
        needs_bounds = 1;
    } else if (x_min + side > 0x3c) {
        x_span -= x_min + side - 0x3c;
        needs_bounds = 1;
    }
    if (y_min <= 0) {
        side += y_min;
        y_min = 0;
        needs_bounds = 1;
    } else if (y_min + side >= 0x3c) {
        side -= y_min + side - 0x3c;
        needs_bounds = 1;
    }

    gmn_sptr = ((x_min) + (y_min) * 60) * 8;
    stride   = (0x3c - x_span) * 8;

    if (!needs_bounds) {
        gmn_y = y_min;
        for ( ; gmn_y < y_min + side; gmn_y++, gmn_sptr += stride) {
            gmn_x = x_min;
            for ( ; gmn_x < x_min + x_span; gmn_x++, gmn_sptr += 8) {
                if ((*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).terrain & reject_mask) {
                    (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).place_state = 0xff;
                    continue;
                }
                if ((*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).occupant != 0) {
                    if (strict == 0) {
                        (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).place_state = 0xff;
                        continue;
                    }
                    if ((*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).terrain & 0x17) {
                        (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).place_state = 0xff;
                        continue;
                    }
                }
                if ((*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).place_state != 0)
                    continue;
                neigh = (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr - 480))).place_state;
                if (neigh != 0 && neigh < r + 1) {
                    (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).place_state = (unsigned char)(r + 1);
                    continue;
                }
                neigh = (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr + 8))).place_state;
                if (neigh != 0 && neigh < r + 1) {
                    (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).place_state = (unsigned char)(r + 1);
                    continue;
                }
                neigh = (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr + 480))).place_state;
                if (neigh != 0 && neigh < r + 1) {
                    (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).place_state = (unsigned char)(r + 1);
                    continue;
                }
                neigh = (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr - 8))).place_state;
                if (neigh != 0 && neigh < r + 1) {
                    (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).place_state = (unsigned char)(r + 1);
                }
            }
        }
    } else {
        gmn_y = y_min;
        for ( ; gmn_y < y_min + side; gmn_y++, gmn_sptr += stride) {
            gmn_x = x_min;
            for ( ; gmn_x < x_min + x_span; gmn_x++, gmn_sptr += 8) {
                if ((*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).terrain & reject_mask) {
                    (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).place_state = 0xff;
                    continue;
                }
                if ((*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).place_state != 0)
                    continue;
                if (gmn_y > 0)
                    neigh = (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr - 480))).place_state;
                else
                    neigh = 0;
                if (neigh != 0 && neigh < r + 1) {
                    (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).place_state = (unsigned char)(r + 1);
                    continue;
                }
                if (gmn_x < 0x3b)
                    neigh = (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr + 8))).place_state;
                else
                    neigh = 0;
                if (neigh != 0 && neigh < r + 1) {
                    (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).place_state = (unsigned char)(r + 1);
                    continue;
                }
                if (gmn_y < 0x3b)
                    neigh = (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr + 480))).place_state;
                else
                    neigh = 0;
                if (neigh != 0 && neigh < r + 1) {
                    (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).place_state = (unsigned char)(r + 1);
                    continue;
                }
                if (gmn_x > 0)
                    neigh = (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr - 8))).place_state;
                else
                    neigh = 0;
                if (neigh != 0 && neigh < r + 1) {
                    (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).place_state = (unsigned char)(r + 1);
                }
            }
        }
    }
}

// FUNCTION: C2 0x66A53
// WIN: 0x004a0a83
// Lines 504–548
//
// Pick the cheapest non-wall, non-blocking neighbour (slot byte +2)
// in the four cardinal directions starting from `dirc` and rotating
// through all four.  Region-map sister of get_best_elastic_value;
// publishes best_elastic_value / best_elastic_dirc.
void get_best_rm_elastic_value(int x, int y, int ptr, int dirc)
{
    int i;
    int dir = dirc;
    unsigned char v;

    best_elastic_value = 100;
    best_elastic_dirc = 0;
    i = 0;
    while (i++ < 4) {
        if (dir == 0) {
            if (y > 0) {
                v = (*(struct region_cell *)((unsigned char *)region_map + (ptr - 480))).place_state;
                if (v != 0 && v < best_elastic_value) {
                    best_elastic_value = v;
                    best_elastic_dirc = 0;
                }
            }
        } else if (dir == 1) {
            if (x < 59) {
                v = (*(struct region_cell *)((unsigned char *)region_map + (ptr + 8))).place_state;
                if (v != 0 && v < best_elastic_value) {
                    best_elastic_value = v;
                    best_elastic_dirc = 1;
                }
            }
        } else if (dir == 2) {
            if (y < 59) {
                v = (*(struct region_cell *)((unsigned char *)region_map + (ptr + 480))).place_state;
                if (v != 0 && v < best_elastic_value) {
                    best_elastic_value = v;
                    best_elastic_dirc = 2;
                }
            }
        } else if (dir == 3) {
            if (x > 0) {
                v = (*(struct region_cell *)((unsigned char *)region_map + (ptr - 8))).place_state;
                if (v != 0 && v < best_elastic_value) {
                    best_elastic_value = v;
                    best_elastic_dirc = 3;
                }
            }
        }
        dir++;
        if (dir > 3) dir = 0;
    }
}

// FUNCTION: C2 0x66B05
// WIN: 0x004a0c35
// Lines 554–561
//
// Pre-grow elastic for road-style construction at
// (act_start_x, act_start_y).  Initialises a 21×2 elastic
// region (set_range with width=21, height=2, last arg=0),
// stamps elastic=1 on the start cell, then walks indices 1..20
// calling test_elastic_range(idx, 9) for each, and finally
// calls transform_road_elastic(20) to finish the road growth.
//
// The 21-cell width matches the maximum road segment length
// the elastic algorithm will consider in a single act.
void get_road_elastic(void)
{
    int i;

    set_range(act_start_x, act_start_y, 0x15, 2, 0);
    (*(struct city_cell *)((unsigned char *)city_map + (act_start_pm_ptr))).road_aqueduct = 1;
    for (i = 1; i <= 20; i++)
        test_elastic_range(i, 9);
    transform_road_elastic(20);
}

// FUNCTION: C2 0x66B56
// WIN: 0x004a0c9f
// Lines 563–613
//
// City-map twin of transform_reg_road_elastic.  Marks cells
// of city_map inside a radius-r square around
// (act_start_x, act_start_y) as candidate road tiles
// (city_map[+2] = 0xFF) when their terrain + edge mask
// match the city-road criteria.
//
// city_map cells are 20 bytes each on an 80×80 grid;
// gmn_sptr advances by 20 per column, +(80-cols)*20 per row.
//
// Per cell (skip if city_map[+2] is already 0xFF):
//   * mask & 0x02 AND 0xC2 < terrain < 0xC7: mark    (scrub)
//   * mask & 0x04 AND !(mask & 0x20):        mark    (open)
//   * mask & 0x80:                             mark    (vacant)
//   * mask & 0x40 AND terrain >= 0xD1:        mark    (hill)
//   * terrain < 8 AND (cell[+3] & 0x80):     mark    (deep water /
//                                                     bridge ramp)
//
// Bounding box is clipped to [0..80) on each axis.  Returns y_max
// for caller bookkeeping.
void transform_road_elastic(int r)
{
    int x_min;
    int y_min;
    int x_max;
    int y_max;
    int side;
    int x_span;
    int stride;

    x_min = act_start_x - r;
    y_min = act_start_y - r;
    side  = 2 * r + 1;
    x_span = side;
    x_max = side + x_min;
    if (x_min <= 0)       { x_span = x_max; x_min = 0; }
    else if (x_max > 80)  { x_span -= x_max - 80; }
    y_max = side + y_min;
    if (y_min <= 0)       { side = y_max; y_min = 0; }
    else if (y_max >= 80) { side -= y_max - 80; }

    gmn_sptr = (x_min + y_min * 80) * 20;
    stride   = (80 - x_span) * 20;

    gmn_y = y_min;
    for ( ; gmn_y < y_min + side; gmn_y++, gmn_sptr += stride) {
        gmn_x = x_min;
        for ( ; gmn_x < x_min + x_span; gmn_x++, gmn_sptr += 20) {
            if ((*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).road_aqueduct != 0xff) {
                if ((*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).terrain & 0x02) {
                    if ((*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).base_kind <= 0xc2
                        || (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).base_kind >= 0xc7) continue;
                    (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).road_aqueduct = 0xff;
                }
                if ((*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).terrain & 0x04) {
                    if ((*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).terrain & 0x20) continue;
                    (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).road_aqueduct = 0xff;
                }
                if ((*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).terrain & 0x80) {
                    (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).road_aqueduct = 0xff;
                }
                if ((*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).terrain & 0x40) {
                    if ((*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).base_kind < 0xd1) continue;
                    (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).road_aqueduct = 0xff;
                }
                if ((*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).base_kind < 8
                    && ((*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).edge_bits & 0x80)) {
                    (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).road_aqueduct = 0xff;
                }
            }
        }
    }
}

// FUNCTION: C2 0x66D22
// WIN: 0x004a0f4e
// Lines 615–729
//
// Commit the player-drawn city road.  City-map twin of
// build_reg_road_from_elastic; operates on the elastic
// preview marks left by transform_road_elastic on the
// 80×80 city_map (20-byte cells).
//
// pm_over_cm_ptr is the cell byte offset into city_map for
// the active cell.  Neighbour slot bytes (each at +2 of the
// neighbour cell):
//   north → -0x63E,  east  → +0x16
//   south → +0x642,  west  → -0x12
// Cell pointer steps by ±0x640 (north/south) or ±0x14 (east/west).
//
// Per cell visited (both phases share this prologue):
//   1. If (cm[+1] & 0x02):
//        cm[+1] = (cm[+1] & ~0x06) | 0x04   (replace
//        wall-eligible bit with the "road on wall" bit)
//   2. !(cm[+1] & 0x20) → particles_built++
//   3. count-- (cm[+2] running slot)
//   4. cm[+0] < 0x1A → particles_cleared++
//   5. cm[+1] |= 0x20
//   6. cm[+3] |= 1
//   7. saved_slot = cm[+2]
//
// Find next neighbour (rotating dir 0..3, starts one past
// previously accepted dir).  For each:
//   - if (cm[+1] & 0x10) bridge_count = 1; else bridge_count = 0
//   - if on-map, neighbour_slot = neighbour[+2]
//   - if neighbour edge_mask & 0x10: bridge_count++
//   - if bridge_count > 1: reject this dir (can’t chain
//     two existing bridge tiles)
//   - else if neighbour_slot != 0 AND < saved_slot: accept
//     and step.
//
// If no dir matches in 4 attempts: phase ends.
// status = 1 (phase 1) or 3 (phase 2) if saved_slot > 1.
//
// Phase 2 restarts at pm_over_cm_ptr and walks forward with
// road_ramifications(x, y) preceding each step; if it returns
// 0, abort with status = 2.
//
// Final: status == 0 → success (jmp 0x678b4 shared 6-pop
// epilogue).  status != 0 → illegal_build = 1;
// restore_city_from_undo_buffer().
//
// Byte-exact source-shape note (2026-07-12): both bridge-count seeds are
// explicit constant-store if/else statements.  Watcom folds each diamond
// to the same setne sequence as `bridge_count = (mask != 0)`, but the
// expression form creates an extra FlowOut temp.  Removing both temps
// restores PS's count/over_y_l ShellSort slot order (Rule 107).  The old
// `(int)neighbour` cast was only a slot crutch and is not PS source; all
// eight accept tests are the direct byte form (`test cl,cl`).
void build_road_from_elastic(void)
{
    int over_y_l;
    int over_x_l;
    int cell_ptr;
    int count;
    unsigned char saved_slot;
    unsigned char status;
    int attempt;
    int dir;
    unsigned char neighbour;
    int bridge_count;

    count = (*(struct city_cell *)((unsigned char *)city_map + (pm_over_cm_ptr))).road_aqueduct;
    if (count == 0) { illegal_build = 1; return; }
    if (count == 0xff) { illegal_build = 1; return; }

    over_x_l = over_x;
    over_y_l = over_y;
    cell_ptr = pm_over_cm_ptr;
    dir      = 0;
    bridge_count = 0;
    status   = 0;

    while (count > 0) {
        count--;
        if ((*(struct city_cell *)((unsigned char *)city_map + (cell_ptr))).terrain & 0x02) {
            (*(struct city_cell *)((unsigned char *)city_map + (cell_ptr))).terrain &= 0xf9;
            (*(struct city_cell *)((unsigned char *)city_map + (cell_ptr))).terrain |= 0x04;
        }
        if (!((*(struct city_cell *)((unsigned char *)city_map + (cell_ptr))).terrain & 0x20)) particles_built++;
        if ((*(struct city_cell *)((unsigned char *)city_map + (cell_ptr))).base_kind < 0x1a) particles_cleared++;
        (*(struct city_cell *)((unsigned char *)city_map + (cell_ptr))).terrain |= 0x20;
        (*(struct city_cell *)((unsigned char *)city_map + (cell_ptr))).edge_bits |= 1;

        saved_slot = (*(struct city_cell *)((unsigned char *)city_map + (cell_ptr))).road_aqueduct;
        attempt = 4; dir = 0;
        while (attempt-- > 0) {
            neighbour    = 0;
            if ((*(struct city_cell *)((unsigned char *)city_map + (cell_ptr))).terrain & 0x10) bridge_count = 1; else bridge_count = 0;
            if (++dir > 3) dir = 0;
            if (dir == 0) {
                if (over_y_l > 0) neighbour = (*(struct city_cell *)((unsigned char *)city_map + ((cell_ptr) - 0x640))).road_aqueduct;
                if ((*(struct city_cell *)((unsigned char *)city_map + ((cell_ptr) - 0x640))).terrain & 0x10) bridge_count++;
                if (bridge_count > 1) neighbour = 0;
                if (neighbour != 0 && neighbour < saved_slot) { cell_ptr -= 0x640; over_y_l--; break; }
            } else if (dir == 1) {
                if (over_x_l < 0x4f) neighbour = (*(struct city_cell *)((unsigned char *)city_map + ((cell_ptr) + 0x14))).road_aqueduct;
                if ((*(struct city_cell *)((unsigned char *)city_map + ((cell_ptr) + 0x14))).terrain & 0x10) bridge_count++;
                if (bridge_count > 1) neighbour = 0;
                if (neighbour != 0 && neighbour < saved_slot) { cell_ptr += 0x14; over_x_l++; break; }
            } else if (dir == 2) {
                if (over_y_l < 0x4f) neighbour = (*(struct city_cell *)((unsigned char *)city_map + ((cell_ptr) + 0x640))).road_aqueduct;
                if ((*(struct city_cell *)((unsigned char *)city_map + ((cell_ptr) + 0x640))).terrain & 0x10) bridge_count++;
                if (bridge_count > 1) neighbour = 0;
                if (neighbour != 0 && neighbour < saved_slot) { cell_ptr += 0x640; over_y_l++; break; }
            } else if (dir == 3) {
                if (over_x_l > 0) neighbour = (*(struct city_cell *)((unsigned char *)city_map + ((cell_ptr) - 0x14))).road_aqueduct;
                if ((*(struct city_cell *)((unsigned char *)city_map + ((cell_ptr) - 0x14))).terrain & 0x10) bridge_count++;
                if (bridge_count > 1) neighbour = 0;
                if (neighbour != 0 && neighbour < saved_slot) { cell_ptr -= 0x14; over_x_l--; break; }
            }
        }
        if (neighbour != 0 && neighbour < saved_slot)
            continue;
        if (saved_slot > 1) { status = 1; goto finish; }
        goto phase2;
    }

phase2:
    count    = (*(struct city_cell *)((unsigned char *)city_map + (pm_over_cm_ptr))).road_aqueduct;
    over_x_l = over_x;
    over_y_l = over_y;
    cell_ptr = pm_over_cm_ptr;
    dir      = 0;
    bridge_count = 0;

    while (count > 0) {
        count--;
        if (road_ramifications(over_x_l, over_y_l) == 0) {
            status = 2; goto finish;
        }
        saved_slot = (*(struct city_cell *)((unsigned char *)city_map + (cell_ptr))).road_aqueduct;
        attempt = 4; dir = 0;
        while (attempt-- > 0) {
            neighbour    = 0;
            if ((*(struct city_cell *)((unsigned char *)city_map + (cell_ptr))).terrain & 0x10) bridge_count = 1; else bridge_count = 0;
            if (++dir > 3) dir = 0;
            if (dir == 0) {
                if (over_y_l > 0) neighbour = (*(struct city_cell *)((unsigned char *)city_map + ((cell_ptr) - 0x640))).road_aqueduct;
                if ((*(struct city_cell *)((unsigned char *)city_map + ((cell_ptr) - 0x640))).terrain & 0x10) bridge_count++;
                if (bridge_count > 1) neighbour = 0;
                if (neighbour != 0 && neighbour < saved_slot) { cell_ptr -= 0x640; over_y_l--; break; }
            } else if (dir == 1) {
                if (over_x_l < 0x4f) neighbour = (*(struct city_cell *)((unsigned char *)city_map + ((cell_ptr) + 0x14))).road_aqueduct;
                if ((*(struct city_cell *)((unsigned char *)city_map + ((cell_ptr) + 0x14))).terrain & 0x10) bridge_count++;
                if (bridge_count > 1) neighbour = 0;
                if (neighbour != 0 && neighbour < saved_slot) { cell_ptr += 0x14; over_x_l++; break; }
            } else if (dir == 2) {
                if (over_y_l < 0x4f) neighbour = (*(struct city_cell *)((unsigned char *)city_map + ((cell_ptr) + 0x640))).road_aqueduct;
                if ((*(struct city_cell *)((unsigned char *)city_map + ((cell_ptr) + 0x640))).terrain & 0x10) bridge_count++;
                if (bridge_count > 1) neighbour = 0;
                if (neighbour != 0 && neighbour < saved_slot) { cell_ptr += 0x640; over_y_l++; break; }
            } else if (dir == 3) {
                if (over_x_l > 0) neighbour = (*(struct city_cell *)((unsigned char *)city_map + ((cell_ptr) - 0x14))).road_aqueduct;
                if ((*(struct city_cell *)((unsigned char *)city_map + ((cell_ptr) - 0x14))).terrain & 0x10) bridge_count++;
                if (bridge_count > 1) neighbour = 0;
                if (neighbour != 0 && neighbour < saved_slot) { cell_ptr -= 0x14; over_x_l--; break; }
            }
        }
        if (neighbour != 0 && neighbour < saved_slot)
            continue;
        if (saved_slot > 1) { status = 3; goto finish; }
        break;
    }

finish:
    if (status != 0) {
        illegal_build = 1;
        restore_city_from_undo_buffer();
    }
}

// FUNCTION: C2 0x67109
// WIN: 0x004a1612
//
// Recompute road sprites in the clamped 3x3 neighbourhood around
// (x,y).  Per cell: skip non-road/road-already-stamped tiles; for
// fortified roads (bit 0x10), promote the underlying scrub tile to
// a road sprite; for walls/aqueducts delegate to the corresponding
// ramification helper; otherwise pick a road sprite from the
// city-map road-data table via choose_from.  Mirrors
// reg_road_ramifications on the 80×80 city map.
// Lines 731–795
int road_ramifications(int x, int y)
{
    int x_min;
    char kind;
    int x_max;
    int y_max;
    int y_min;

    x_min = (x == 0) ? 0 : x - 1;
    y_min = (y == 0) ? 0 : y - 1;
    x_max = (x == 79) ? 79 : x + 1;
    y_max = (y == 79) ? 79 : y + 1;

    for (gmn_y = y_min; y_max >= gmn_y; gmn_y++) {
        for (gmn_x = x_min; x_max >= gmn_x; gmn_x++) {
            gmn_sptr = ((gmn_x) + (gmn_y) * 80) * 20;
            if (((*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).terrain & 0x20) == 0) continue;
            if (((*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).terrain & 8) != 0) continue;
            (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).edge_bits |= 1;
            if (((*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).terrain & 0x10) != 0) {
                if ((*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).building != 0) continue;
                kind = (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).base_kind;
                (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).building = kind;
                if (kind >= 0x1e && kind < 0x22)
                    (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).base_kind = 0x4e;
                else if (kind >= 0x22 && kind < 0x26)
                    (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).base_kind = 0x4f;
                else if (kind >= 0x26 && kind < 0x2a)
                    (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).base_kind = 0x50;
                else if (kind >= 0x2a && kind < 0x2e)
                    (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).base_kind = 0x51;
                continue;
            }
            if (((*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).terrain & 4) != 0) {
                if (one_wall_ramification() != 0) continue;
                (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).terrain &= 0xf9;
                (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).terrain |= 2;
                return 0;
            }
            if (((*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).terrain & 0x40) != 0) {
                if (one_aquaduct_ramification() == 0) {
                    (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).terrain &= 0xdf;
                    return 0;
                }
                (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).edge_bits |= 0x80;
                continue;
            }
            if (((*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).base_kind & 0xff) >= 0x7c) continue;
            test_citymap_neighbours_posedge(0x20);
            if (choose_from(road_data, 0x10) == 0) {
                (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).terrain &= 0xdf;
                return 0;
            }
            (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).base_kind = first_choice;
        }
    }
    return 1;
}

// FUNCTION: C2 0x67333
// WIN: 0x004a1998
// Lines 799–808
//
// Wall sister of get_road_elastic / get_aquaduct_elastic.
// Pre-grow elastic for wall construction at
// (act_start_x, act_start_y).  Initialises a 21×2 elastic
// region, stamps elastic=1 on the start cell, walks
// indices 1..20 calling test_elastic_range(i, 0x99)
// for each, then calls transform_wall_elastic(20) to
// finish.  After the transform, clamps the start cell's
// elastic byte: if it didn't reach 0xff (saturated), set
// it back to 1.  Resets elastic_start_dirc.
//
void get_wall_elastic(void)
{
    int i;

    set_range(act_start_x, act_start_y, 0x15, 2, 0);
    (*(struct city_cell *)((unsigned char *)city_map + (act_start_pm_ptr))).road_aqueduct = 1;
    for (i = 1; i <= 20; i++)
        test_elastic_range(i, 0x99);
    transform_wall_elastic(0x14);
    if ((*(struct city_cell *)((unsigned char *)city_map + (act_start_pm_ptr))).road_aqueduct != 0xff)
        (*(struct city_cell *)((unsigned char *)city_map + (act_start_pm_ptr))).road_aqueduct = 1;
    elastic_start_dirc = 0;
}

// FUNCTION: C2 0x673A8
// WIN: 0x004a1a34
// Lines 810–888
//
// City-map wall preview pass (twin of
// transform_aquaduct_elastic and
// transform_reg_wall_elastic).  Walks the clipped 80×80
// bounding box of radius r around
// (act_start_x, act_start_y) and stamps the candidate-wall
// byte (city_map[+2]) based on terrain + edge mask.
//
// Skip cells where [+2] is already 0xFF.  Per cell:
//
//  A) (mask & 0x02) AND !(mask & 0x40) (wall-eligible,
//                                        not on a hill):
//       terrain == 0xC1:
//           set_2_neighbours_if_not_wallortower(
//               x, y, sptr, 2, 0xff, 0)
//           cell[+2] = 0xff
//       terrain == 0xC2:
//           set_2_neighbours_if_not_wallortower(
//               x, y, sptr, 2, 0xff, 1)
//           cell[+2] = 0xff
//       terrain < 0xC7  (low ground):
//           set_4_neighbours_if_not_wallortower(
//               x, y, sptr, 2, 0xff)
//           cell[+2] = 0xff
//       0xC7 <= terrain <= 0xCA (slope / wall foot):
//           if (x, y) != (act_start_x, act_start_y):
//               inc_elastic_by2(x, y, sptr)
//               cell[+2] += 2
//       terrain > 0xCA: no action.
//
//  B) Else (mask & 0x02 not set):
//       if (mask & 0x04) AND cell[+2] > 1 AND cell[+2] != 0xff:
//           cell[+2]--
//
//  C) If mask & 0x20:
//       if mask & 0x04: continue (skip D/E this cell)
//       elif terrain == 0x52/0x53: cell[+2]++
//       else                        cell[+2] = 0xff
//
//  D) If mask & 0x40 (hill tile):
//       if terrain <= 0xD0: cell[+2]++
//       else                 cell[+2] = 0xff
//
//  E) If terrain < 8 AND (cell[+3] & 0x80): cell[+2] = 0xff
//
// Bounding box clipped to [0..80) on each axis.
void transform_wall_elastic(int r)
{
    int x_min;
    int y_min;
    unsigned char kind;
    int stride;
    int x_span;
    int side;
    int needs_bounds;

    needs_bounds = 0;
    x_min = act_start_x - r;
    y_min = act_start_y - r;
    side = 2 * r + 1;
    x_span = side;
    if (x_min <= 0)                  { x_span += x_min; x_min = 0; needs_bounds = 1; }
    else if (x_min + side > 80)      { x_span -= x_min + side - 80; needs_bounds = 1; }
    if (y_min <= 0)                  { side += y_min; y_min = 0; needs_bounds = 1; }
    else if (y_min + side >= 80)     { side -= y_min + side - 80; needs_bounds = 1; }

    gmn_sptr = (x_min + y_min * 80) * 20;
    stride   = (80 - x_span) * 20;

    for (gmn_y = y_min; y_min + side > gmn_y; gmn_y++, gmn_sptr += stride) {
        for (gmn_x = x_min; x_min + x_span > gmn_x; gmn_x++, gmn_sptr += 20) {
            if ((*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).road_aqueduct != 0xff) {
                if ((*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).terrain & 0x02) {
                    kind = (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).base_kind;
                    if (!((*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).terrain & 0x40)) {
                        if ((*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).base_kind == 0xc1) {
                            set_2_neighbours_if_not_wallortower(gmn_x, gmn_y, gmn_sptr, 2, 0xff, 0);
                            (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).road_aqueduct = 0xff;
                        } else if ((*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).base_kind == 0xc2) {
                            set_2_neighbours_if_not_wallortower(gmn_x, gmn_y, gmn_sptr, 2, 0xff, 1);
                            (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).road_aqueduct = 0xff;
                        } else if ((*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).base_kind < 0xc7) {
                            set_4_neighbours_if_not_wallortower(gmn_x, gmn_y, gmn_sptr, 2, 0xff);
                            (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).road_aqueduct = 0xff;
                        } else if ((*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).base_kind <= 0xca) {
                            if (gmn_x == act_start_x && gmn_y == act_start_y) continue;
                            inc_elastic_by2(gmn_x, gmn_y, gmn_sptr);
                            (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).road_aqueduct += 2;
                        }
                    }
                } else if (((*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).terrain & 0x04) && (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).road_aqueduct > 1 && (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).road_aqueduct != 0xff) {
                    (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).road_aqueduct -= 1;
                }

                if ((*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).terrain & 0x20) {
                    if ((*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).terrain & 0x04) continue;
                    if ((*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).base_kind == 0x52) (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).road_aqueduct += 1;
                    else if ((*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).base_kind == 0x53) (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).road_aqueduct += 1;
                    else (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).road_aqueduct = 0xff;
                }
                if ((*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).terrain & 0x40) {
                    if ((*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).base_kind <= 0xd0) (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).road_aqueduct += 1;
                    else                                   (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).road_aqueduct = 0xff;
                }
                if ((*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).base_kind < 8 && ((*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).edge_bits & 0x80)) {
                    (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).road_aqueduct = 0xff;
                }
            }
        }
    }
}

// FUNCTION: C2 0x67653
// WIN: 0x004a1ee0
// Lines 890–977
//
// Walks an elastic-wall placement preview to its final cells.
// Two-pass: first pass marks each preview cell, second pass calls
// wall_ramifications() at each step.  If either pass fails (byte+2
// reaches `best_elastic_value` cutoff or `wall_ramifications` returns
// 0), restore the city from the undo buffer and rotate
// elastic_start_dirc.
//
void build_wall_from_elastic(void)
{
    int counter;
    int y;
    int x;
    int ptr;
    unsigned char outer_state;
    unsigned char saved_byte2;

    counter = (unsigned char)(*(struct city_cell *)((unsigned char *)city_map + (pm_over_cm_ptr))).road_aqueduct;
    if ((*(struct city_cell *)((unsigned char *)city_map + (pm_over_cm_ptr))).terrain & 4)
        counter++;
    if (counter == 0) {
        illegal_build = 1;
    } else if (counter == 0xff) {
        illegal_build = 1;
    } else {

        outer_state = 0;
        x = over_x;
        y = over_y;
        ptr = pm_over_cm_ptr;
        while (counter > 0) {
            counter--;
            if (((*(struct city_cell *)((unsigned char *)city_map + (ptr))).terrain & 6) == 0)
                particles_built++;
            if ((unsigned char)(*(struct city_cell *)((unsigned char *)city_map + (ptr))).base_kind < 0x1a)
                particles_cleared++;
            (*(struct city_cell *)((unsigned char *)city_map + (ptr))).edge_bits |= 1;
            if (!((*(struct city_cell *)((unsigned char *)city_map + (ptr))).terrain & 4)) {
                if ((*(struct city_cell *)((unsigned char *)city_map + (ptr))).terrain & 0x20)
                    (*(struct city_cell *)((unsigned char *)city_map + (ptr))).terrain |= 4;
                else
                    (*(struct city_cell *)((unsigned char *)city_map + (ptr))).terrain |= 2;
            }
            saved_byte2 = (*(struct city_cell *)((unsigned char *)city_map + (ptr))).road_aqueduct;
            get_best_elastic_value(x, y, ptr, elastic_start_dirc);
            if (saved_byte2 >= best_elastic_value) {
                if (best_elastic_dirc == 0) { ptr -= 0x640; y--; }
                else if (best_elastic_dirc == 1) { ptr += 0x14;  x++; }
                else if (best_elastic_dirc == 2) { ptr += 0x640; y++; }
                else if (best_elastic_dirc == 3) { ptr -= 0x14;  x--; }
                continue;
            }
            if (saved_byte2 > 1) {
                outer_state = 1;
                goto check_outer_state;
            }
            break;
        }

        counter = (unsigned char)(*(struct city_cell *)((unsigned char *)city_map + (pm_over_cm_ptr))).road_aqueduct;
        if ((*(struct city_cell *)((unsigned char *)city_map + (pm_over_cm_ptr))).terrain & 4)
            counter++;
        x = over_x;
        y = over_y;
        ptr = pm_over_cm_ptr;
        while (counter > 0) {
            counter--;
            if (!wall_ramifications(x, y)) {
                outer_state = 2;
                goto check_outer_state;
            }
            (*(struct city_cell *)((unsigned char *)city_map + (ptr))).industrial = 0;
            saved_byte2 = (*(struct city_cell *)((unsigned char *)city_map + (ptr))).road_aqueduct;
            get_best_elastic_value(x, y, ptr, elastic_start_dirc);
            if (saved_byte2 >= best_elastic_value) {
                if (best_elastic_dirc == 0) { ptr -= 0x640; y--; }
                else if (best_elastic_dirc == 1) { ptr += 0x14;  x++; }
                else if (best_elastic_dirc == 2) { ptr += 0x640; y++; }
                else if (best_elastic_dirc == 3) { ptr -= 0x14;  x--; }
                continue;
            }
            if (saved_byte2 > 1) {
                outer_state = 3;
                goto check_outer_state;
            }
            break;
        }

    check_outer_state:
        if (outer_state != 0) {
            illegal_build = 1;
            restore_city_from_undo_buffer();
            elastic_start_dirc++;
            if (elastic_start_dirc > 3)
                elastic_start_dirc = 0;
        }
    }
}

// FUNCTION: C2 0x678BB
// WIN: 0x004a2251
// Lines 979–995
//
// Validate wall connections at (x, y) and across the 3×3 (or
// smaller, if at edges) neighbourhood.  Sister of
// aquaduct_ramifications: same control flow but uses equality
// tests (==) for the bound clamps instead of inequality (>),
// matching PS's `jne`-based codegen.
int wall_ramifications(int x, int y)
{
    int x_min;
    int y_min;
    int x_max;
    int y_max;

    if (x == 0) x_min = 0; else x_min = x - 1;
    if (y == 0) y_min = 0; else y_min = y - 1;
    if (x == 79) x_max = x; else x_max = x + 1;
    if (y == 79) y_max = y; else y_max = y + 1;

    gmn_x = x;
    gmn_y = y;
    if (one_wall_ramification() == 0)
        return 0;

    for (gmn_y = y_min; y_max >= gmn_y; gmn_y++) {
        for (gmn_x = x_min; x_max >= gmn_x; gmn_x++) {
            if (one_wall_ramification() == 0)
                return 0;
        }
    }

    return 1;
}

// FUNCTION: C2 0x67944
// WIN: 0x004a2362
// Lines 997–1080
//
// Re-evaluate the wall sprite for a single city-map cell at
// (gmn_x, gmn_y).  Tests the cell's neighbour mask (via
// test_citymap_neighbours_negedge) and picks a sprite id from the
// wall-data table; returns 0 when no valid wall sprite is available.
int one_wall_ramification(void)
{
    unsigned char sprite;

    gmn_sptr = ((gmn_x) + (gmn_y) * 80) * 20;
    (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).edge_bits |= 1;

    if (((*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).terrain & 2) != 0) {
        test_citymap_neighbours_negedge(6);
        if (((*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).terrain & 0x40) != 0) {
            if (gmn_polar_count == 0) {
                if ((*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).base_kind == 0xcf) first_choice = 0xbc;
                else if ((*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).base_kind == 0xd0) first_choice = 0xbd;
                else return 0;
                (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).base_kind = first_choice;
                (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).edge_bits &= 0xe3;
                (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).edge_bits |= 8;
                if (first_choice == 0xbc) sprite = 3;
                else sprite = 7;
                (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).extra_edge = sprite;
                (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).building = sprite;
                return 1;
            } else {
                if (choose_from(wallaqua_data, 2) != 0) {
                    (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).base_kind = first_choice;
                    (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).edge_bits &= 0xe3;
                    (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).edge_bits |= 8;
                    if (first_choice == 0xbc) sprite = 3;
                    else sprite = 7;
                    (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).extra_edge = sprite;
                    (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).building = sprite;
                    return 1;
                }
                gmn_err_sptr = gmn_sptr;
                gmn_err_x = gmn_x;
                gmn_err_y = gmn_y;
                return 0;
            }
        }
        if (choose_from(wall_data, 0xe) == 0) {
            gmn_err_sptr = gmn_sptr;
            gmn_err_x = gmn_x;
            gmn_err_y = gmn_y;
            return 0;
        }
        (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).base_kind = first_choice;
        (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).edge_bits &= 0xe3;
        (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).edge_bits |= wall_gfxdat[first_choice - WALL_GFX_FIRST_TILE].edge_bits;
        (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).extra_edge = wall_gfxdat[first_choice - WALL_GFX_FIRST_TILE].sprite;
        return 1;
    }

    if (((*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).terrain & 4) != 0) {
        if (((*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).terrain & 0x20) != 0) {
            test_type_citymap_neighbours_negedge(0xc0);
            if (gmn_polar_count != 0) {
                gmn_err_sptr = gmn_sptr;
                gmn_err_x = gmn_x;
                gmn_err_y = gmn_y;
                return 0;
            }
            test_citymap_neighbours_negedge(6);
            if (choose_from(gateway_data, 6) != 0) {
                (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).extra_edge = first_choice;
                (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).base_kind = 0xc0;
                (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).edge_bits &= 0x63;
                (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).edge_bits |= 0x88;
                return 1;
            }
            test_citymap_neighbours_negedge(0x20);
            if (choose_from(gateway2_data, 2) == 0) {
                gmn_err_sptr = gmn_sptr;
                gmn_err_x = gmn_x;
                gmn_err_y = gmn_y;
                return 0;
            }
            (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).extra_edge = first_choice;
            (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).base_kind = 0xc0;
            (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).edge_bits &= 0x63;
            (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).edge_bits |= 0x88;
            return 1;
        }

        test_citymap_neighbours_negedge(6);
        if (choose_from(tower_data, 0x10) == 0) {
            gmn_err_sptr = gmn_sptr;
            gmn_err_x = gmn_x;
            gmn_err_y = gmn_y;
            return 0;
        }
        (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).extra_edge = first_choice;
        (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).base_kind = 0xbf;
        (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).edge_bits &= 0xe3;
        (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).edge_bits |= 8;
        return 1;
    }
    return 1;
}

// FUNCTION: C2 0x67C23
// WIN: 0x004a2894
// Lines 1094–1101
//
// Aqueduct sister of get_road_elastic.  Pre-grow elastic for
// aqueduct construction at (act_start_x, act_start_y).
// Initialises a 21×2 elastic region, stamps elastic=1 on the
// start cell, walks indices 1..20 calling test_elastic_range
// (with constant 0x1d instead of 9 for road), then calls
// transform_aquaduct_elastic(20) to finish.
//
// If the start cell's elastic byte didn't saturate to 0xff, reset
// it to 1, then clear elastic_start_dirc.  Functionally identical
// for all three elastic-grow primitives.
void get_aquaduct_elastic(void)
{
    int i;

    set_range(act_start_x, act_start_y, 0x15, 2, 0);
    (*(struct city_cell *)((unsigned char *)city_map + (act_start_pm_ptr))).road_aqueduct = 1;
    for (i = 1; i <= 20; i++)
        test_elastic_range(i, 0x1d);
    transform_aquaduct_elastic(20);
    if ((*(struct city_cell *)((unsigned char *)city_map + (act_start_pm_ptr))).road_aqueduct != 0xff)
        (*(struct city_cell *)((unsigned char *)city_map + (act_start_pm_ptr))).road_aqueduct = 1;
    elastic_start_dirc = 0;
}

// FUNCTION: C2 0x67C75
// WIN: 0x004a292d
// Lines 1105–1179
//
// City-map aqueduct twin of transform_road_elastic.  Walks
// the clipped 80×80 bounding box of radius r around
// (act_start_x, act_start_y) and marks each cell's
// candidate-aquaduct byte (city_map[+2]) based on terrain +
// edge mask.
//
// Skip cells where [+2] is already 0xFF.  Per cell:
//
//  A) Mountain edge (mask & 0x40):
//       terrain == 0xCF or 0xD5:
//           set_2_neighbours_if_not_aquaductorresevoir(
//               x, y, sptr, 2, 0xff, 0);
//           cell[+2] = 0xff
//       terrain == 0xD0 or 0xD6:
//           set_2_neighbours_if_not_aquaductorresevoir(
//               x, y, sptr, 2, 0xff, 1);
//           cell[+2] = 0xff
//       terrain <= 0xCE  (raw mountain):
//           if (x, y) != (act_start_x, act_start_y):
//               inc_elastic_by2(x, y, sptr);
//               cell[+2] += 2  (slot bump for tunnel exit)
//       terrain > 0xCE  (high peak):
//           set_4_neighbours_if_not_aquaductorresevoir(
//               x, y, sptr, 2, 0xff);
//           cell[+2] = 0xff
//
//  B) Else if (mask & 0x80) cliff/aquaduct-end:
//       if (cell[+2] > 1 && cell[+2] != 0xff)
//           cell[+2]--    (decay slot toward 0)
//
//  C) (always) Reservoir tile group (mask & 0x20):
//       if terrain == 0x52 or 0x53: cell[+2]++
//       else                        cell[+2] = 0xff
//
//  D) Scrub group (mask & 0x02):
//       if terrain > 0xC2: cell[+2] = 0xff
//       else                cell[+2]++
//
//  E) Deep water / bridge ramp
//     (terrain < 8 && (cell[+3] & 0x80)): cell[+2] = 0xff
//
// Bounding box clipped to [0..80) on each axis.
void transform_aquaduct_elastic(int r)
{
    int x_min;
    int y_min;
    int x_max;
    int y_max;
    int side;
    int x_span;
    int stride;
    char kind;

    x_min = act_start_x - r;
    y_min = act_start_y - r;
    side  = 2 * r + 1;
    x_span = side;
    x_max = x_min + side;
    if (x_min <= 0)       { x_span = x_max; x_min = 0; }
    else if (x_max > 80)  { x_span -= x_max - 80; }
    y_max = y_min + side;
    if (y_min <= 0)       { side = y_max; y_min = 0; }
    else if (y_max >= 80) { side -= y_max - 80; }

    gmn_sptr = (x_min + y_min * 80) * 20;
    stride   = (80 - x_span) * 20;

    gmn_y = y_min;
    for ( ; gmn_y < y_min + side; gmn_y++, gmn_sptr += stride) {
        gmn_x = x_min;
        for ( ; gmn_x < x_min + x_span; gmn_x++, gmn_sptr += 20) {
            if ((*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).road_aqueduct != 0xff) {
                if ((*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).terrain & 0x40) {
                    kind = (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).base_kind;
                    if (kind == 0xcf || kind == 0xd5) {
                        set_2_neighbours_if_not_aquaductorresevoir(gmn_x, gmn_y, gmn_sptr, 2, 0xff, 0);
                        (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).road_aqueduct = 0xff;
                    } else if (kind == 0xd0 || kind == 0xd6) {
                        set_2_neighbours_if_not_aquaductorresevoir(gmn_x, gmn_y, gmn_sptr, 2, 0xff, 1);
                        (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).road_aqueduct = 0xff;
                    } else if (kind <= 0xce) {
                        if (gmn_x == act_start_x && gmn_y == act_start_y) continue;
                        inc_elastic_by2(gmn_x, gmn_y, gmn_sptr);
                        (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).road_aqueduct += 2;
                    } else if (kind > 0xce) {
                        set_4_neighbours_if_not_aquaductorresevoir(gmn_x, gmn_y, gmn_sptr, 2, 0xff);
                        (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).road_aqueduct = 0xff;
                    }
                } else if ((*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).terrain & 0x80) {
                    if ((*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).road_aqueduct > 1 && (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).road_aqueduct != 0xff) {
                        (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).road_aqueduct -= 1;
                    }
                }
                if ((*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).terrain & 0x20) {
                    if ((*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).base_kind == 0x52)
                        (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).road_aqueduct++;
                    else if ((*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).base_kind == 0x53)
                        (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).road_aqueduct++;
                    else
                        (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).road_aqueduct = 0xff;
                }
                if ((*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).terrain & 0x02) {
                    if ((*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).base_kind <= 0xc2)
                        (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).road_aqueduct++;
                    else
                        (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).road_aqueduct = 0xff;
                }
                if ((*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).base_kind < 8 && ((*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).edge_bits & 0x80)) {
                    (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).road_aqueduct = 0xff;
                }
            }
        }
    }
}

// FUNCTION: C2 0x67F13
// WIN: 0x004a2d9f
// Lines 1182–1265
//
// Commit the player-drawn aqueduct: walks the elastic
// preview marks left by transform_aquaduct_elastic outward
// from the drag-end (over_x, over_y, pm_over_cm_ptr) in two
// phases.  Phase 1 follows the elastic value back along the
// preview chain; phase 2 walks forward from the same start
// expanding aquaduct_ramifications (junctions / bridges).
//
// Per step on either phase:
//   1. Decrement the candidate-slot counter (the cell's
//      city_map[+2] value, plus 1 if mask & 0x80 was set
//      meaning the cell already carries a wall-end stamp).
//   2. If neither bit 0x40 nor 0x80 of city_map[+1] is set,
//      bump particles_built (a new aqueduct tile).
//   3. If terrain < 0x1A (cleared / placeholder), bump
//      particles_cleared.
//   4. Set city_map[+3] |= 1 (aquaduct-built marker).
//   5. If mask & 0x80 was NOT set, OR in mask |= 0x40.
//   6. Call get_best_elastic_value(over_x, over_y, pm_ptr,
//      elastic_start_dirc) which writes
//      best_elastic_value + best_elastic_dirc.
//   7. If saved cell[+2] < best_elastic_value, break phase
//      (status = 1 in phase 1, 3 in phase 2).  Else step
//      pm_over_cm_ptr / over_x / over_y by best_elastic_dirc:
//         0 → -1600 / y--      (north)
//         1 → +20  / x++       (east)
//         2 → +1600 / y++      (south)
//         3 → -20  / x--       (west)
//   In phase 2 step 1 is preceded by aquaduct_ramifications:
//   if it returns 0, abort phase 2 with status = 2.
//
// Status byte at function exit:
//   0    -> success.
//   != 0 -> illegal_build = 1; restore_city_from_undo_buffer;
//           rotate elastic_start_dirc (++ with wrap 0..3).
void build_aquaduct_from_elastic(void)
{
    int over_y_l;
    int over_x_l;
    int pm_ptr;
    int count;
    unsigned char saved_slot;
    unsigned char status;

    over_x_l = over_x;
    over_y_l = over_y;
    pm_ptr = pm_over_cm_ptr;

    count = CM_CELL(pm_over_cm_ptr).road_aqueduct;
    if (CM_CELL(pm_over_cm_ptr).terrain & 0x80)
        count++;
    if (count == 0) {
        illegal_build = 1;
    } else if (count == 0xff) {
        illegal_build = 1;
    } else {

        status = 0;

        while (count > 0) {
            count--;
            if ((CM_CELL(pm_ptr).terrain & 0xc0) == 0)
                particles_built++;
            if (CM_CELL(pm_ptr).base_kind < 0x1a)
                particles_cleared++;
            CM_CELL(pm_ptr).edge_bits |= 1;
            if (!(CM_CELL(pm_ptr).terrain & 0x80))
                CM_CELL(pm_ptr).terrain |= 0x40;

            saved_slot = CM_CELL(pm_ptr).road_aqueduct;
            get_best_elastic_value(over_x_l, over_y_l, pm_ptr, elastic_start_dirc);
            if (saved_slot >= best_elastic_value) {
                if (best_elastic_dirc == 0) { pm_ptr -= 0x640; over_y_l--; }
                else if (best_elastic_dirc == 1) { pm_ptr += 0x14;  over_x_l++; }
                else if (best_elastic_dirc == 2) { pm_ptr += 0x640; over_y_l++; }
                else if (best_elastic_dirc == 3) { pm_ptr -= 0x14;  over_x_l--; }
                continue;
            }
            if (saved_slot > 1) {
                status = 1;
                goto check_outer_state;
            }
            break;
        }

        count = CM_CELL(pm_over_cm_ptr).road_aqueduct;
        if (CM_CELL(pm_over_cm_ptr).terrain & 0x80)
            count++;

        over_x_l = over_x;
        over_y_l = over_y;
        pm_ptr = pm_over_cm_ptr;

        while (count > 0) {
            count--;
            if (!aquaduct_ramifications(over_x_l, over_y_l)) {
                status = 2;
                goto check_outer_state;
            }
            saved_slot = CM_CELL(pm_ptr).road_aqueduct;
            get_best_elastic_value(over_x_l, over_y_l, pm_ptr, elastic_start_dirc);
            if (saved_slot >= best_elastic_value) {
                if (best_elastic_dirc == 0) { pm_ptr -= 0x640; over_y_l--; }
                else if (best_elastic_dirc == 1) { pm_ptr += 0x14;  over_x_l++; }
                else if (best_elastic_dirc == 2) { pm_ptr += 0x640; over_y_l++; }
                else if (best_elastic_dirc == 3) { pm_ptr -= 0x14;  over_x_l--; }
                continue;
            }
            if (saved_slot > 1) {
                status = 3;
                goto check_outer_state;
            }
            break;
        }

    check_outer_state:
        if (status != 0) {
            illegal_build = 1;
            restore_city_from_undo_buffer();
            elastic_start_dirc++;
            if (elastic_start_dirc > 3)
                elastic_start_dirc = 0;
        }
    }
}

// FUNCTION: C2 0x6811E
// WIN: 0x004a30d6
// Lines 1267–1287
//
// Validate aqueduct connections at (x, y) and across the
// 3×3 (or smaller, if at edges) neighbourhood.  Calls
// `one_aquaduct_ramification()` (which reads gmn_x/gmn_y
// globals) for the center cell first; returns 0 immediately
// if the center cell is not a valid aqueduct connection.
// Then walks the clamped neighbourhood (x_min..x_max,
// y_min..y_max) calling the same helper.  Returns 1 if all
// pass, 0 if any fail.
//
int aquaduct_ramifications(int x, int y)
{
    int x_min;
    int y_min;
    int x_max;
    int y_max;

    if (x <= 0) x_min = 0; else x_min = x - 1;
    if (y <= 0) y_min = 0; else y_min = y - 1;
    if (x >= 79) x_max = 79; else x_max = x + 1;
    if (y >= 79) y_max = 79; else y_max = y + 1;

    gmn_x = x;
    gmn_y = y;
    if (one_aquaduct_ramification() == 0)
        return 0;

    for (gmn_y = y_min; y_max >= gmn_y; gmn_y++) {
        for (gmn_x = x_min; x_max >= gmn_x; gmn_x++) {
            if (one_aquaduct_ramification() == 0)
                return 0;
        }
    }

    return 1;
}

// FUNCTION: C2 0x681AD
// WIN: 0x004a31e8
// Lines 1289–1370
//
// Re-evaluate one cell of an aquaduct preview: re-anchors via
// get_aqua_web when the cell isn't on an existing aquaduct, then
// reads the surrounding neighbour mask and writes a matching sprite
// id.  Returns 0 when no valid choice is available.
int one_aquaduct_ramification(void)
{
    unsigned char polar;
    int sel;
    unsigned char sprite;

    gmn_sptr = ((gmn_x) + (gmn_y) * 80) * 20;
    (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).edge_bits |= 1;
    if (((*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).edge_bits & 0x20) == 0)
        get_aqua_web(gmn_x, gmn_y);

    polar = (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).range_flag & 3;
    if (((*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).terrain & 0x40) != 0) {
        test_citymap_neighbours_negedge(0xc0);
        if (((*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).terrain & 2) != 0) {
            if (gmn_polar_count == 0) {
                if ((*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).base_kind == 0xc1) first_choice = 0xbd;
                else if ((*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).base_kind != 0xc2) return 0;
                else first_choice = 0xbc;
                (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).base_kind = first_choice;
                (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).edge_bits &= 0xe3;
                (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).edge_bits |= 8;
                if (first_choice == 0xbc) sprite = 3;
                else sprite = 7;
                (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).extra_edge = sprite;
                (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).building = sprite;
                return 1;
            } else {
                if (choose_from(aquawall_data, 2) != 0) {
                    (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).base_kind = first_choice;
                    (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).edge_bits &= 0xe3;
                    (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).edge_bits |= 8;
                    if (first_choice == 0xbc) sprite = 3;
                    else sprite = 7;
                    (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).extra_edge = sprite;
                    (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).building = sprite;
                    return 1;
                }
                err:
                gmn_err_sptr = gmn_sptr;
                gmn_err_x = gmn_x;
                gmn_err_y = gmn_y;
                return 0;
            }
        }
        if (((*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).terrain & 0x20) != 0) {
            sel = choose_from(aquaroad_data, 2);
            (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).edge_bits |= 0x80;
        } else {
            sel = choose_from(aquaduct_data, 0xe);
        }
        if (sel == 0) {
            goto err;
        }
        (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).base_kind = first_choice;
        (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).edge_bits &= 0xe3;
        (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).edge_bits |= wall_gfxdat[first_choice - WALL_GFX_FIRST_TILE].edge_bits;
        (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).extra_edge = wall_gfxdat[first_choice - WALL_GFX_FIRST_TILE].sprite;
        (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).building = wall_gfxdat[first_choice - WALL_GFX_FIRST_TILE].sprite;
        if (polar == 3) (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).extra_edge += 2;
        else if (polar >= 1) (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).extra_edge += 1;
        return 1;
    }

    if (((*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).terrain & 0x80) == 0)
        return 1;
    test_citymap_neighbours_negedge(0xc0);
    if (choose_from(resevoir_data, 0x10) == 0) {
        goto err;
    }
    (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).extra_edge = first_choice;
    (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).building = first_choice;
    if (polar == 3) (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).extra_edge += 3;
    if (polar == 2) (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).extra_edge += 2;
    if (polar == 1) (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).extra_edge++;
    return 1;
}

// FUNCTION: C2 0x68472
// WIN: 0x004a36d5
// Lines 1376–1385
//
// Region-map sister of get_road_elastic.  Pre-grow elastic for
// inter-province road construction at
// (act_start_x, act_start_y).  Initialises a 21×2 elastic
// region on the region_map (set_rm_range), stamps elastic=1
// on the start cell, walks indices 1..20 calling
// test_rm_elastic_range(1, i, 0xd9), then calls
// transform_reg_road_elastic(20) to finish.
void get_reg_road_elastic(void)
{
    int i;

    set_rm_range(act_start_x, act_start_y, 0x15, 2, 0);
    (*(struct region_cell *)((unsigned char *)region_map + (act_start_pm_ptr))).place_state = 1;
    for (i = 1; i <= 20; i++)
        test_rm_elastic_range(1, i, 0xd9);
    transform_reg_road_elastic(20);
}

// FUNCTION: C2 0x684C8
// WIN: 0x004a3744
// Lines 1387–1431
//
// Mark the cells of region_map inside a radius-r square
// around (act_start_x, act_start_y) as candidate road tiles
// (region_cell[+2] = 0xFF) when their terrain + edge mask
// match the regional-road criteria.  Used during the
// elastic-mode preview of a multi-cell road placement on
// the empire map.
//
// region_map cells are 8 bytes each on a 60×60 grid;
// gmn_sptr advances by 8 per column, +(60-cols)*8 per row.
//
// Per cell (skip if region_cell[+2] is already 0xFF):
//   * If edge-mask bit 0x02 set AND terrain is in the scrub
//     range 0xB8 < t < 0xBD: mark as road.
//   * If edge-mask bit 0x04 set AND bit 0x20 NOT set: mark.
//   * If edge-mask bit 0x08 set: mark.
//   * If edge-mask bit 0x40 set AND terrain >= 0xC7: mark.
//
// Bounding box is clipped to [0..60) on each axis.  Returns y_max
// for caller bookkeeping.
int transform_reg_road_elastic(int r)
{
    int x_min;
    int y_min;
    int x_max;
    int y_max;
    int side;
    int x_span;
    int stride;

    x_min = act_start_x - r;
    y_min = act_start_y - r;
    side  = 2 * r + 1;
    x_span = side;
    x_max = side + x_min;
    if (x_min <= 0)       { x_span = x_max; x_min = 0; }
    else if (x_max > 60)  { x_span -= x_max - 60; }
    y_max = side + y_min;
    if (y_min <= 0)       { side = y_max; y_min = 0; }
    else if (y_max >= 60) { side -= y_max - 60; }

    gmn_sptr = ((x_min) + (y_min) * 60) * 8;
    stride   = (60 - x_span) * 8;

    gmn_y = y_min;
    for ( ; gmn_y < y_min + side; gmn_y++, gmn_sptr += stride) {
        gmn_x = x_min;
        for ( ; gmn_x < x_min + x_span; gmn_x++, gmn_sptr += 8) {
            if ((*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).place_state != 0xff) {
                if ((*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).terrain & 0x02) {
                    if ((*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).base_kind <= 0xb8
                        || (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).base_kind >= 0xbd) continue;
                    (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).place_state = 0xff;
                }
                if ((*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).terrain & 0x04) {
                    if ((*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).terrain & 0x20) continue;
                    (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).place_state = 0xff;
                }
                if ((*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).terrain & 0x08) {
                    (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).place_state = 0xff;
                }
                if ((*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).terrain & 0x40) {
                    if ((*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).base_kind < 0xc7) continue;
                    (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).place_state = 0xff;
                }
            }
        }
    }

    return y_min + side;
}

// FUNCTION: C2 0x68654
// WIN: 0x004a39b8
// Lines 1434–1522
//
// Commit the player-drawn region road.  Operates on the
// elastic preview marks left by transform_reg_road_elastic
// on region_map; runs a two-phase neighbour-pick walker that
// follows decreasing-slot values from the drag-end
// (over_x, over_y, pm_over_cm_ptr) toward 0.
//
// region_map is a 60×60 grid of 8-byte cells; pm_over_cm_ptr
// is the cell offset into region_map for the active cell.
// Neighbour slot bytes (each at +2 of the neighbour cell):
//   north → +(-0x1DE),  east  → +0xA
//   south → +0x1E2,    west  → -6
// Cell pointer steps by ±0x1E0 (north/south) or ±8 (east/west).
//
// Per cell visited (both phases share this prologue):
//   1. count-- (cell[+2] running slot value).
//   2. !(cell[+1] & 0x20) → particles_built++.
//   3. terrain < 0x10 → particles_cleared++.
//   4. cell[+1] |= 0x20  (mark region road built).
//   5. cell[+3] |= 1.
//   6. Find next neighbour: cycle through dir 0..3 starting
//      one past the previously-accepted dir; for each that
//      stays on-map fetch the neighbour's slot byte.  Accept
//      the first dir whose neighbour slot is non-zero AND
//      strictly less than saved_slot.  Step pointer + x/y in
//      that direction.  If no dir matches in 4 attempts the
//      chain has dead-ended.
//
// Phase split:
//   * Phase 1 starts at pm_over_cm_ptr and walks the
//     elastic chain back toward the elastic origin.  Sets
//     status=1 if the walker stops with saved_slot > 1
//     (meaning the chain wasn't fully exhausted).
//   * Phase 2 restarts at pm_over_cm_ptr and walks forward
//     using reg_road_ramifications(x, y) before each step.
//     If reg_road_ramifications returns 0 — fails to expand
//     the bridge/junction — abort with status=2.  Sets
//     status=3 if the walker stops with saved_slot > 1.
//
// status == 0 -> success.  status != 0 ->
// restore_region_from_undo_buffer; illegal_build = 1.
void build_reg_road_from_elastic(void)
{
    int over_y_l;
    int over_x_l;
    int cell_ptr;
    int count;
    unsigned char saved_slot;
    unsigned char status;
    unsigned char neighbour;
    int attempt;
    int dir;

    count = (*(struct region_cell *)((unsigned char *)region_map + (pm_over_cm_ptr))).place_state;
    if (count == 0) {
        illegal_build = 1;
        return;
    }
    if (count == 0xff) {
        illegal_build = 1;
        return;
    }

    over_x_l = over_x;
    over_y_l = over_y;
    cell_ptr = pm_over_cm_ptr;
    dir      = 0;
    status   = 0;

    while (count > 0) {
        count--;
        if (!((*(struct region_cell *)((unsigned char *)region_map + (cell_ptr))).terrain & 0x20)) particles_built++;
        if ((*(struct region_cell *)((unsigned char *)region_map + (cell_ptr))).base_kind < 0x10) particles_cleared++;
        (*(struct region_cell *)((unsigned char *)region_map + (cell_ptr))).terrain |= 0x20;
        (*(struct region_cell *)((unsigned char *)region_map + (cell_ptr))).edge_bits |= 1;

        saved_slot = (*(struct region_cell *)((unsigned char *)region_map + (cell_ptr))).place_state;
        attempt = 4;
        dir = 0;
        while (attempt-- > 0) {
            neighbour = 0;
            if (++dir > 3) dir = 0;
            if (dir == 0) {
                if (over_y_l > 0) neighbour = (*(struct region_cell *)((unsigned char *)region_map + (cell_ptr - 480))).place_state;
                if (neighbour != 0 && neighbour < saved_slot) { cell_ptr -= 0x1e0; over_y_l--; break; }
            } else if (dir == 1) {
                if (over_x_l < 0x3b) neighbour = (*(struct region_cell *)((unsigned char *)region_map + (cell_ptr + 8))).place_state;
                if (neighbour != 0 && neighbour < saved_slot) { cell_ptr += 8; over_x_l++; break; }
            } else if (dir == 2) {
                if (over_y_l < 0x3b) neighbour = (*(struct region_cell *)((unsigned char *)region_map + (cell_ptr + 480))).place_state;
                if (neighbour != 0 && neighbour < saved_slot) { cell_ptr += 0x1e0; over_y_l++; break; }
            } else if (dir == 3) {
                if (over_x_l > 0) neighbour = (*(struct region_cell *)((unsigned char *)region_map + (cell_ptr - 8))).place_state;
                if (neighbour != 0 && neighbour < saved_slot) { cell_ptr -= 8; over_x_l--; break; }
            }
        }
        if (neighbour != 0 && neighbour < saved_slot)
            continue;
        if (saved_slot > 1) {
            status = 1;
            goto finish;
        }
        break;
    }

    count    = (*(struct region_cell *)((unsigned char *)region_map + (pm_over_cm_ptr))).place_state;
    over_x_l = over_x;
    over_y_l = over_y;
    cell_ptr = pm_over_cm_ptr;
    dir      = 0;

    while (count > 0) {
        count--;
        if (reg_road_ramifications(over_x_l, over_y_l) == 0) { status = 2; goto finish; }

        saved_slot = (*(struct region_cell *)((unsigned char *)region_map + (cell_ptr))).place_state;
        attempt = 4;
        dir = 0;
        while (attempt-- > 0) {
            neighbour = 0;
            if (++dir > 3) dir = 0;
            if (dir == 0) {
                if (over_y_l > 0) neighbour = (*(struct region_cell *)((unsigned char *)region_map + (cell_ptr - 480))).place_state;
                if (neighbour != 0 && neighbour < saved_slot) { cell_ptr -= 0x1e0; over_y_l--; break; }
            } else if (dir == 1) {
                if (over_x_l < 0x3b) neighbour = (*(struct region_cell *)((unsigned char *)region_map + (cell_ptr + 8))).place_state;
                if (neighbour != 0 && neighbour < saved_slot) { cell_ptr += 8; over_x_l++; break; }
            } else if (dir == 2) {
                if (over_y_l < 0x3b) neighbour = (*(struct region_cell *)((unsigned char *)region_map + (cell_ptr + 480))).place_state;
                if (neighbour != 0 && neighbour < saved_slot) { cell_ptr += 0x1e0; over_y_l++; break; }
            } else if (dir == 3) {
                if (over_x_l > 0) neighbour = (*(struct region_cell *)((unsigned char *)region_map + (cell_ptr - 8))).place_state;
                if (neighbour != 0 && neighbour < saved_slot) { cell_ptr -= 8; over_x_l--; break; }
            }
        }
        if (neighbour != 0 && neighbour < saved_slot)
            continue;
        if (saved_slot > 1) {
            status = 3;
            goto finish;
        }
        break;
    }

finish:
    if (status != 0) {
        restore_region_from_undo_buffer();
        illegal_build = 1;
    }
}

// FUNCTION: C2 0x688BB
// WIN: 0x004a3eb6
// Lines 1524–1568
//
// Recompute regional road sprites in the clamped 3×3 neighbourhood
// around (x,y).  Wall/road crossings are delegated to
// one_reg_wall_ramification; plain road cells choose a road sprite from
// their positive-edge neighbours.
int reg_road_ramifications(int x, int y)
{
    int x_min;
    int y_max;
    int x_max;
    int y_min;

    if (x == 0) x_min = 0; else x_min = x - 1;
    if (y == 0) y_min = 0; else y_min = y - 1;
    if (x == 59) x_max = 59; else x_max = x + 1;
    if (y == 59) y_max = 59; else y_max = y + 1;

    for (gmn_y = y_min; y_max >= gmn_y; gmn_y++) {
        for (gmn_x = x_min; x_max >= gmn_x; gmn_x++) {
            gmn_sptr = (gmn_x + gmn_y * 60) * 8;
            if (((*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).terrain & 0x20) != 0) {
                (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).edge_bits |= 1;
                if (((*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).terrain & 2) != 0) {
                    if (one_reg_wall_ramification() == 0) {
                        (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).terrain &= 0xf9;
                        (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).terrain |= 2;
                        return 0;
                    }
                } else {
                    test_regionmap_neighbours_posedge(0xe5);
                    if (choose_from(road_data, 0x10) != 0) {
                        (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).base_kind = first_choice + 0x4e;
                        (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).edge_bits &= 0xe3;
                        (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).gfx = first_choice - 0x52;
                    } else {
                        (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).terrain &= 0xdf;
                        return 0;
                    }
                }
            }
        }
    }
    return 1;
}

// FUNCTION: C2 0x689F6
// WIN: 0x004a40d4
// Lines 1572–1579
//
// Region-map sister of get_wall_elastic.  Same shape: prime
// the elastic preview range via set_rm_range, mark the start
// cell, sweep test_rm_elastic_range over 20 segments, transform
// to final wall, then de-saturate the start cell.
void get_reg_wall_elastic(void)
{
    int i;

    set_rm_range(act_start_x, act_start_y, 0x15, 2, 0);
    (*(struct region_cell *)((unsigned char *)region_map + (act_start_pm_ptr))).place_state = 1;
    for (i = 1; i <= 0x14; i++)
        test_rm_elastic_range(0, i, 0xd9);
    transform_reg_wall_elastic(0x14);
    if ((*(struct region_cell *)((unsigned char *)region_map + (act_start_pm_ptr))).place_state != 0xff)
        (*(struct region_cell *)((unsigned char *)region_map + (act_start_pm_ptr))).place_state = 1;
    elastic_start_dirc = 0;
}

// FUNCTION: C2 0x68A6A
// WIN: 0x004a4172
// Lines 1583–1641
//
// Region-map wall preview pass (twin of
// transform_aquaduct_elastic but on the 60×60 region grid
// with 8-byte cells).  Walks the clipped bounding box of
// radius r around (act_start_x, act_start_y) and stamps the
// candidate-wall byte (region_cell[+2]) based on terrain +
// edge mask.
//
// Skip cells where [+2] is already 0xFF.  Per cell:
//
//  A) mask & 0x02 (wall-eligible terrain ring):
//       terrain < 0xBD (low ground):
//         if mask & 0x20: leave for the always-pass below.
//         else: set_4_rm_neighbours_if_not_wallortower(
//                   x, y, sptr, 2, 0xff)
//               cell[+2] = 0xff   (gateway clear)
//       terrain >= 0xBD and <= 0xC0  (slope/hill):
//         if (x, y) != (act_start_x, act_start_y):
//             inc_elastic_by2(x, y, sptr)
//             cell[+2] += 2
//       terrain > 0xC0 (peak): no action.
//
//  B) Else (mask & 0x02 not set):
//       if mask & 0x04 AND cell[+2] > 1 AND cell[+2] != 0xff:
//           cell[+2]--  (decay slot toward 0)
//
//  C) Always (mask & 0x20):
//       if terrain == 0xA0 or 0xA1: cell[+2]++
//       elif mask & 0x02:            cell[+2]++
//       else:                          cell[+2] = 0xff
//
// Bounding box clipped to [0..60) on each axis.  Tail-merges
// into the shared 6-pop epilogue at 0x6764b / 0x678b4.
void transform_reg_wall_elastic(int r)
{
    int x_min;
    int y_min;
    int x_max;
    int y_max;
    int side;
    int x_span;
    int stride;
    int ps;
    int bk;
    int bk2;

    x_min = act_start_x - r;
    y_min = act_start_y - r;
    side  = 2 * r + 1;
    x_span = side;
    x_max = x_min + side;
    if (x_min <= 0)        { x_span = x_max; x_min = 0; }
    else if (x_max > 60)   { x_span -= x_max - 60; }
    y_max = side + y_min;
    if (y_min <= 0)        { side = y_max; y_min = 0; }
    else if (y_max >= 60)  { side -= y_max - 60; }

    gmn_sptr = (x_min + y_min * 60) * 8;
    stride   = (60 - x_span) * 8;

    gmn_y = y_min;
    for ( ; gmn_y < y_min + side; gmn_y++, gmn_sptr += stride) {
        gmn_x = x_min;
        for ( ; gmn_x < x_min + x_span; gmn_x++, gmn_sptr += 8) {
            ps = ((unsigned char *)region_map)[(gmn_sptr + 2)];
            if (ps == 0xff) continue;

            if (((unsigned char *)region_map)[(gmn_sptr + 1)] & 0x02) {
                bk = ((unsigned char *)region_map)[(gmn_sptr)];
                if (bk < 0xbd) {
                    if (!(((unsigned char *)region_map)[(gmn_sptr + 1)] & 0x20)) {
                        set_4_rm_neighbours_if_not_wallortower(
                            gmn_x, gmn_y, gmn_sptr, 2, 0xff);
                        ((unsigned char *)region_map)[(gmn_sptr + 2)] = 0xff;
                    }
                } else if (bk <= 0xc0) {
                    if (gmn_x == act_start_x && gmn_y == act_start_y)
                        continue;
                    inc_elastic_by2(gmn_x, gmn_y, gmn_sptr);
                    ((unsigned char *)region_map)[(gmn_sptr + 2)] += 2;
                }
            } else if ((((unsigned char *)region_map)[(gmn_sptr + 1)] & 0x04)
                       && ps > 1 && ps != 0xff) {
                ((unsigned char *)region_map)[(gmn_sptr + 2)]--;
            }

            if (((unsigned char *)region_map)[(gmn_sptr + 1)] & 0x20) {
                bk2 = ((unsigned char *)region_map)[(gmn_sptr)];
                if (bk2 == 0xa0) {
                    ((unsigned char *)region_map)[(gmn_sptr + 2)]++;
                } else if (bk2 == 0xa1) {
                    ((unsigned char *)region_map)[(gmn_sptr + 2)]++;
                } else if (((unsigned char *)region_map)[(gmn_sptr + 1)] & 0x02) {
                    ((unsigned char *)region_map)[(gmn_sptr + 2)]++;
                } else {
                    ((unsigned char *)region_map)[(gmn_sptr + 2)] = 0xff;
                }
            }
        }
    }
}

// FUNCTION: C2 0x68C7C
// WIN: 0x004a450a
// Lines 1644–1728
//
// Commit the player-drawn region wall.  Same get_best_rm_
// elastic_value-driven walker shape as
// build_aquaduct_from_elastic but on the 60×60 region_map
// (8-byte cells) and with the wall mask bits.
//
// Per step, both phases share this prologue (cm is the cell
// at cell_ptr):
//   1. !(cm[+1] & 0x02) → particles_built++
//   2. count--
//   3. cm[+0] < 0x10 → particles_cleared++
//   4. cm[+3] |= 1
//   5. !(cm[+1] & 0x04) → cm[+1] |= 0x02
//   6. saved_slot = cm[+2]
//   7. get_best_rm_elastic_value(over_x, over_y, cell_ptr,
//                                elastic_start_dirc)
//   8. saved_slot < best_elastic_value → break (status=1
//      in P1, 3 in P2 if saved_slot > 1).  Else step:
//         0 → -0x1E0 / y--  (north)
//         1 → +8     / x++  (east)
//         2 → +0x1E0 / y++  (south)
//         3 → -8     / x--  (west)
//
// Phase 2 prefixes step 1 with reg_wall_ramifications(x, y);
// if 0 returned, abort with status=2.
//
// count is initialised to cm[+2] + (cm[+1] & 0x04 ? 1 : 0).
// If count == 0 or 0xff: illegal_build = 1; jmp epilogue.
//
// Final: status == 0 -> success.  status != 0 -> illegal_build = 1;
// restore_region_from_undo_buffer; rotate elastic_start_dirc
// (++ with wrap 0..3).
void build_reg_wall_from_elastic(void)
{
    int over_y_l;
    int over_x_l;
    int cell_ptr;
    int count;
    unsigned char saved_slot;
    unsigned char status;

    count = RM_CELL(pm_over_cm_ptr).place_state;
    if (RM_CELL(pm_over_cm_ptr).terrain & 0x04) count++;

    if (count == 0) { illegal_build = 1; return; }
    if (count == 0xff) { illegal_build = 1; return; }

    status = 0;
    over_x_l = over_x;
    over_y_l = over_y;
    cell_ptr = pm_over_cm_ptr;

    while (count > 0) {
        count--;
        if (!(RM_CELL(cell_ptr).terrain & 0x02)) particles_built++;
        if (RM_CELL(cell_ptr).base_kind < 0x10) particles_cleared++;
        RM_CELL(cell_ptr).edge_bits |= 1;
        if (!(RM_CELL(cell_ptr).terrain & 0x04)) RM_CELL(cell_ptr).terrain |= 0x02;
        saved_slot = RM_CELL(cell_ptr).place_state;
        get_best_rm_elastic_value(over_x_l, over_y_l, cell_ptr, elastic_start_dirc);
        if (saved_slot >= best_elastic_value) {
            if (best_elastic_dirc == 0) { cell_ptr -= 0x1e0; over_y_l--; }
            else if (best_elastic_dirc == 1) { cell_ptr += 8; over_x_l++; }
            else if (best_elastic_dirc == 2) { cell_ptr += 0x1e0; over_y_l++; }
            else if (best_elastic_dirc == 3) { cell_ptr -= 8; over_x_l--; }
            continue;
        }
        if (saved_slot > 1) {
            status = 1;
            goto finish;
        }
        break;
    }

    count = RM_CELL(pm_over_cm_ptr).place_state;
    if (RM_CELL(pm_over_cm_ptr).terrain & 0x04) count++;

    over_x_l = over_x;
    over_y_l = over_y;
    cell_ptr = pm_over_cm_ptr;

    while (count > 0) {
        count--;
        if (!reg_wall_ramifications(over_x_l, over_y_l)) { status = 2; goto finish; }
        saved_slot = RM_CELL(cell_ptr).place_state;
        get_best_rm_elastic_value(over_x_l, over_y_l, cell_ptr, elastic_start_dirc);
        if (saved_slot >= best_elastic_value) {
            if (best_elastic_dirc == 0) { cell_ptr -= 0x1e0; over_y_l--; }
            else if (best_elastic_dirc == 1) { cell_ptr += 8; over_x_l++; }
            else if (best_elastic_dirc == 2) { cell_ptr += 0x1e0; over_y_l++; }
            else if (best_elastic_dirc == 3) { cell_ptr -= 8; over_x_l--; }
            continue;
        }
        if (saved_slot > 1) {
            status = 3;
            goto finish;
        }
        break;
    }

finish:
    if (status != 0) {
        illegal_build = 1;
        restore_region_from_undo_buffer();
        elastic_start_dirc++;
        if (elastic_start_dirc > 3) elastic_start_dirc = 0;
    }
}

// FUNCTION: C2 0x68EA5
// WIN: 0x004a4841
// Lines 1730–1746
//
// Region-map sister of wall_ramifications: validate wall
// connections at (x, y) and across the 3×3 (or smaller, if at
// edges) neighbourhood.  Region map is 60×60, so edge clamp is
// against 59 (=0x3b) instead of 79 (=0x4f).
int reg_wall_ramifications(int x, int y)
{
    int x_min;
    int y_min;
    int x_max;
    int y_max;

    if (x == 0) x_min = 0; else x_min = x - 1;
    if (y == 0) y_min = 0; else y_min = y - 1;
    if (x == 59) x_max = x; else x_max = x + 1;
    if (y == 59) y_max = y; else y_max = y + 1;

    gmn_x = x;
    gmn_y = y;
    if (one_reg_wall_ramification() == 0)
        return 0;

    for (gmn_y = y_min; y_max >= gmn_y; gmn_y++) {
        for (gmn_x = x_min; x_max >= gmn_x; gmn_x++) {
            if (one_reg_wall_ramification() == 0)
                return 0;
        }
    }

    return 1;
}

// FUNCTION: C2 0x68F2E
// WIN: 0x004a4953
// Lines 1748–1787
//
// Region-map twin of one_wall_ramification: re-evaluate one wall
// sprite at (gmn_x, gmn_y) on the 60x60 region grid.  Returns 0 if
// no valid sprite, caching (gmn_err_x/y/sptr) for the caller.
int one_reg_wall_ramification(void)
{
    gmn_sptr = ((gmn_x) + (gmn_y) * 60) * 8;
    (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).edge_bits |= 1;

    if (((*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).terrain & 2) != 0) {
        if (((*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).terrain & 0x20) != 0) {
            test_type_regionmap_neighbours_negedge(0xb6);
            if (gmn_polar_count != 0) {
                gmn_err_sptr = gmn_sptr;
                gmn_err_x = gmn_x;
                gmn_err_y = gmn_y;
                return 0;
            }
            test_regionmap_neighbours_negedge(6);
            if (choose_from(regwallroad_data, 2) == 0) {
                gmn_err_sptr = gmn_sptr;
                gmn_err_x = gmn_x;
                gmn_err_y = gmn_y;
                return 0;
            }
            (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).gfx = first_choice;
            (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).base_kind = 0xb6;
            (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).edge_bits &= 0xe3;
            return 1;
        }
        test_regionmap_neighbours_negedge(6);
        if (choose_from(wall_data, 0xe) == 0) {
            gmn_err_sptr = gmn_sptr;
            gmn_err_x = gmn_x;
            gmn_err_y = gmn_y;
            return 0;
        }
        (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).base_kind = first_choice - 0xa;
        (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).edge_bits &= 0xe3;
        (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).gfx = house_gfxdat[first_choice + 0x51];
        return 1;
    }

    if (((*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).terrain & 4) != 0) {
        test_regionmap_neighbours_negedge(6);
        if (choose_from(tower_data, 0x10) == 0) {
            gmn_err_sptr = gmn_sptr;
            gmn_err_x = gmn_x;
            gmn_err_y = gmn_y;
            return 0;
        }
        (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).gfx = first_choice;
        (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).base_kind = 0xd2;
        (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).edge_bits &= 0xe3;
        return 1;
    }
    return 1;
}

// FUNCTION: C2 0x69093
// WIN: 0x004a4bca
// Lines 1803–1836
//
// Plant garden tiles across the rectangle (x1,y1)–(x2,y2) on
// the city map.  Sorts the corners, walks the rectangle by
// `cm_sptr` byte-stride, and replaces every non-stone /
// non-flagged tile with a random garden ground sprite (low
// nibble) plus a matching upper sprite (offset 0x4) chosen
// from `stone_random_data`.  Bumps `particles_built` per
// tile placed and `particles_cleared` per tile that wasn't
// already a hard stone (< 0x1a).  Saves `stone_random_count`
// at entry and restores it at exit so the global RNG cursor
// is unaffected.  Sets `illegal_build = 1` if no tile in the
// rectangle was actually placed.
//
// `stone_random_count` is signed-char (movsx everywhere); the
// in-loop saved copy is kept as `int`.
void garden_an_area(int x1, int y1, int x2, int y2)
{
    int saved_count = stone_random_count;
    int row_stride;
    int tmp;
    int y;
    int x;

    if (x1 > x2) {
        tmp = x2;
        x2 = x1;
        x1 = tmp;
    }
    if (y1 > y2) {
        tmp = y2;
        y2 = y1;
        y1 = tmp;
    }

    cm_sptr = (x1 + y1 * 80) * 20;
    row_stride = (80 - (x2 - x1) - 1) * 20;

    for (y = y1; y <= y2;) {
        for (x = x1; x <= x2;) {
            if ((*(struct city_cell *)((unsigned char *)city_map + ((cm_sptr)))).base_kind < 0x1e) {
                if ((*(struct city_cell *)((unsigned char *)city_map + ((cm_sptr)))).base_kind >= 8 || !((*(struct city_cell *)((unsigned char *)city_map + ((cm_sptr)))).edge_bits & 0x80)) {
                    stone_random_count++;
                    if (stone_random_count >= 0x40)
                        stone_random_count = 0;
                    if ((*(struct city_cell *)((unsigned char *)city_map + ((cm_sptr)))).base_kind < 0x1a)
                        particles_cleared++;
                    particles_built++;
                    (*(struct city_cell *)((unsigned char *)city_map + ((cm_sptr)))).base_kind = (unsigned char)((stone_random_data[stone_random_count] >> 2) + 0x78);
                    clear_basic(cm_sptr);
                    (*(struct city_cell *)((unsigned char *)city_map + ((cm_sptr)))).extra_edge = (unsigned char)((stone_random_data[stone_random_count] >> 2) + 0x77);
                    (*(struct city_cell *)((unsigned char *)city_map + ((cm_sptr)))).edge_bits &= 0xe3;
                    (*(struct city_cell *)((unsigned char *)city_map + ((cm_sptr)))).edge_bits |= 4;
                    (*(struct city_cell *)((unsigned char *)city_map + ((cm_sptr)))).activity_a = 0;
                }
            }
            x++;
            cm_sptr += 20;
        }
        y++;
        cm_sptr += row_stride;
    }
    stone_random_count = (signed char)saved_count;
    if (particles_built == 0)
        illegal_build = 1;
}

// FUNCTION: C2 0x6921C
// WIN: 0x004a4dd7
// Lines 1838–1868
//
// Convert every clearable city-map cell in the inclusive rectangle
// bounded by (x1,y1) and (x2,y2) to plaza paving.  Existing occupied
// structures (base_kind >= 0x1e), blocked terrain, and hard edges are
// left alone; if nothing was paved, mark the attempted build illegal.
void plaza_an_area(int x1, int y1, int x2, int y2)
{
    int row_skip;
    int tmp;
    int y;
    int x;

    if (x1 > x2) {
        tmp = x2;
        x2 = x1;
        x1 = tmp;
    }
    if (y1 > y2) {
        tmp = y2;
        y2 = y1;
        y1 = tmp;
    }

    cm_sptr = (x1 + y1 * 80) * 20;
    row_skip = (80 - (x2 - x1) - 1) * 20;

    for (y = y1; y <= y2;) {
        for (x = x1; x <= x2;) {
            if ((*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).base_kind < 0x1e
                && ((*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).base_kind >= 8
                    || ((*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).edge_bits & 0x80) == 0)) {
                if ((*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).base_kind < 0x1a) particles_cleared++;
                particles_built++;
                (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).base_kind = 0x7c;
                clear_basic(cm_sptr);
                (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).extra_edge = 0x74;
                (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).edge_bits &= 0xe3;
                (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).edge_bits |= 4;
                (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).activity_a = 0;
                (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).terrain |= 0x20;
            }
            x++;
            cm_sptr += 20;
        }
        y++;
        cm_sptr += row_skip;
    }
    if (particles_built == 0) illegal_build = 1;
}

// FUNCTION: C2 0x69344
// WIN: 0x004a4fa8
// Lines 1871–1932
//
// Clear/demolish every city-map cell in an inclusive rectangle.  The
// first pass removes selection bit 0x40; the second pass restores
// temporary protected cells, clears buildings to rubble/empty according
// to forum_gfxdat footprint size, and the final pass recalculates road,
// wall, and aqueduct ramifications for every coordinate in the range.
//
// SHAPE 2026-07-09: recovered PS's structure from the Win/Mac oracles.
// (1) Bounds sorting swaps the PARAMS in place (x1<->x2, y1<->y2 via one
//     reused temp) -- NOT via invented xmin/xmax/ymin/ymax locals
//     (win-census Delta=-3 named them).  The DOS diff is now instruction-
//     identical through the sort.
// (2) The base_kind<0x82 arm is a NESTED if (base_kind<8) {...} else,
//     not an ||-chain; size = forum_gfxdat[kind+0x26] has NO & 0xff
//     (the operand is already unsigned char).
// These two changes were the TEMP-SET lever that flipped the Rule 107
// AssignTemps ShellSort slot-swap {row_skip,saved_random,y1,y2} to PS's
// order (proven with c2.regalloc.shellsort_sim: statement reorder + decl
// order are INERT here; only the temp-set change moves it -- target nt_pre
// order [saved_random,y2,row_skip,y1]).  Bytes 463->454, ir-cascade 17->7.
// Residual: a layer-3 edx<->ebx seat tie (PS holds kind + the terrain/
// edge_bits byte scratch in EDX; RC in EBX) -- Rule 44 spurious `and
// edx,0xff`; the 3 [ops] islands (kind dispatch jge/jl, Rule 9) are its
// downstream branch-encoding.  decl-order proven inert (savings-based tie).
void clear_an_area(int x1, int y1, int x2, int y2)
{
    char size;
    int swap_temp;
    int row_skip;
    int x;
    int y;
    int saved_random;
    unsigned char kind;

    saved_random = stone_random_count;
    if (x1 > x2) { swap_temp = x2; x2 = x1; x1 = swap_temp; }
    if (y1 > y2) { swap_temp = y2; y2 = y1; y1 = swap_temp; }

    cm_sptr = (x1 + y1 * 80) * 20;
    row_skip = (80 - (x2 - x1) - 1) * 20;

    for (y = y1; y <= y2; ) {
        for (x = x1; x <= x2; ) {
            (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).edge_bits &= 0xbf; x++; cm_sptr += 20; } y++; cm_sptr += row_skip; }

    cm_sptr = (x1 + y1 * 80) * 20;
    for (y = y1; y <= y2; ) {
        for (x = x1; x <= x2; ) {

            if (((*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).terrain & 0x10) != 0) {

                if (((*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).terrain & 0x20) != 0) {

                    (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).base_kind = (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).building;
                    (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).terrain &= 0xdf;
                    (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).building = 0;
                }
            } else {

                if ((*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).base_kind >= 0x82) {

                    kind = (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).base_kind;
                    size = forum_gfxdat[kind + 0x26];
                    if (size == 0) clear_to_empty(cm_sptr);
                    if (size == 4) clear_sized_to_rubble(cm_sptr, 2, 0);
                    else if (size == 9) clear_sized_to_rubble(cm_sptr, 3, 0);
                    else if (size == 0x10) clear_sized_to_rubble(cm_sptr, 4, 0);
                    else if (kind < 0x82) clear_to_empty(cm_sptr);
                    else clear_to_rubble(cm_sptr, 0);

                } else if ((*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).base_kind < 8) {
                    if (((*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).edge_bits & 0x80) == 0)
                        if (((*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).edge_bits & 0x40) == 0)

                            clear_to_empty(cm_sptr);
                } else {
                    clear_to_empty(cm_sptr);
                }
            }
            x++; cm_sptr += 20; } y++; cm_sptr += row_skip; }

    cm_sptr = (x1 + y1 * 80) * 20;
    for (y = y1; y <= y2; ) {
        for (x = x1; x <= x2; ) {
            road_ramifications(x, y);
            wall_ramifications(x, y);
            aquaduct_ramifications(x, y);
            x++; cm_sptr += 20; } y++; cm_sptr += row_skip; }
    stone_random_count = (signed char)saved_random;
}

// FUNCTION: C2 0x695B9
// WIN: 0x004a536b
// Lines 1934–1984
//
// Clear/demolish an inclusive rectangle on the 60×60 region map.
// Fortresses (0xd2) can be protected by keep_fortress, cohort/army
// ranges are skipped, sized industries/ports are cleared through the
// sized helper, and every affected coordinate has regional road/wall
// ramifications recomputed afterwards.
void clear_a_reg_area(int x0, int y0, int x1, int y1, int keep_fortress)
{
    int saved_random;
    int row_skip;
    unsigned char kind;
    int x;
    int y;
    int t;

    saved_random = stone_random_count;

    if (x1 < x0) { t = x1; x1 = x0; x0 = t; }
    if (y0 > y1) { t = y1; y1 = y0; y0 = t; }

    cm_sptr = (x0 + y0 * 60) * 8;
    row_skip = (60 - (x1 - x0)) * 8 - 8;

    for (y = y0; y <= y1; y++, cm_sptr += row_skip) {
        for (x = x0; x <= x1; x++, cm_sptr += 8) {
            if ((RM_CELL(cm_sptr).terrain & 0x10) != 0) continue;
            stone_random_count++;
            if (stone_random_count >= 0x40) stone_random_count = 0;
            kind = RM_CELL(cm_sptr).base_kind;
            if (kind >= 0x92 && kind <= 0x9b) continue;
            if (keep_fortress != 0 && kind == 0xd2) continue;
            if (kind < 0x10) particles_cleared++;
            if (kind >= 0x20 && kind < 0x7c) {
                /* nothing */
            } else if (kind >= 0xd5 && kind <= 0xeb) {
                clear_sized_to_reg_basic(cm_sptr, 2);
            } else if (kind >= 0xec && kind <= 0xef) {
                clear_sized_to_reg_basic(cm_sptr, 2);
                unflag_rm_area(x - ofset_x, y - ofset_y, 2, 0xf7);
                adjust_regions_coastline(x - ofset_x - 1,
                                         y - ofset_y - 1, 4, 4);
            } else {
                clear_reg_basic(cm_sptr);
            }
            if (kind == 0xd2) clear_army_from_fort_ref(cm_sptr);
        }
    }

    for (y = y0; y <= y1; y++, cm_sptr += row_skip) {
        for (x = x0; x <= x1; x++, cm_sptr += 8) {
            reg_road_ramifications(x, y);
            reg_wall_ramifications(x, y);
        }
    }
    stone_random_count = saved_random;
}

// FUNCTION: C2 0x697E7
// WIN: 0x004a564b
// Lines 1986–2013
//
// Clear one region-map atom at byte offset `sptr`, handling sized
// industry/port footprints and recalculating coast/road/wall side
// effects.  This is the single-cell companion to clear_a_reg_area.
void destroy_reg_atom(int sptr)
{
    int cell = sptr / 8;
    int y;
    int x = cell % 60;
    int saved_random;
    unsigned char kind;
    y = cell / 60;
    saved_random = stone_random_count;
    kind = (*(struct region_cell *)((unsigned char *)region_map + (sptr))).base_kind;

    if (!((kind >= 0x20 && kind < 0x7c) ||
          (kind >= 0x92 && kind <= 0x9b))) {
        if (kind >= 0xd5 && kind <= 0xeb) {
            clear_sized_to_reg_basic(sptr, 2);
        } else if (kind >= 0xec && kind <= 0xef) {
            clear_sized_to_reg_basic(sptr, 2);
            unflag_rm_area(x - ofset_x, y - ofset_y, 2, 0xf7);
            adjust_regions_coastline(x - ofset_x - 1, y - ofset_y - 1, 4, 4);
        } else if (((*(struct region_cell *)((unsigned char *)region_map + (sptr))).terrain & 0x28) == 0) {
            clear_reg_basic(sptr);
        }
    }
    stone_random_count = (signed char)saved_random;
    particles_cleared = 0;
}

// FUNCTION: C2 0x69907
// WIN: 0x004a57bd
// Lines 2015–2039
//
// Destroy one city-map atom at byte offset `sptr`, selecting the
// correct rubble/empty clear path from the base kind and forum_gfxdat
// footprint size.  Afterwards recompute map coordinates for aqueduct
// ramifications and restore stone_random_count/particles_cleared so
// the caller's drag/destroy loop remains deterministic.
void destroy_an_atom(int sptr, int rubble_kind)
{
    int saved_random;
    int kind;
    int size;
    int cell_index;
    int x;
    int y;

    saved_random = stone_random_count;
    kind = (*(struct city_cell *)((unsigned char *)city_map + (sptr))).base_kind & 0xff;
    if (kind >= 0x82) {
        size = forum_gfxdat[kind + 0x26] & 0xff;
        if (size == 4)
            clear_sized_to_rubble(sptr, 2, rubble_kind);
        else if (size == 9)
            clear_sized_to_rubble(sptr, 3, rubble_kind);
        else if (size == 0x10)
            clear_sized_to_rubble(sptr, 4, rubble_kind);
        else if (kind >= 0x82)
            clear_to_rubble(sptr, rubble_kind);
        else
            clear_to_empty(sptr);
    } else if (kind >= 8) {
        clear_to_empty(sptr);
    }

    cell_index = sptr / 20;
    x = cell_index % 80;
    y = cell_index / 80;
    aquaduct_ramifications(x, y);
    stone_random_count = (signed char)saved_random;
    particles_cleared = 0;
}

// FUNCTION: C2 0x699D7
// WIN: 0x004a590a
// Lines 2041–2060
//
// Directional fire-spread wrapper.  Adjust the city_map byte offset
// by dir (0 north, 4 south, 6 west, 2 east), skip protected ids
// 0xbc..0xe2, then dispatch by forum_gfxdat size class:
// 4 -> 2x2 rubble, 9 -> 3x3, 0x10 -> 4x4, otherwise one cell.
void spread_fire_atom(int sptr, int dir)
{
    char kind_byte;
    int kind;
    int size;

    if (dir == 0)
        sptr -= 0x640;
    else if (dir == 4)
        sptr += 0x640;
    else if (dir == 6)
        sptr -= 0x14;
    else if (dir == 2)
        sptr += 0x14;

    kind_byte = (*(struct city_cell *)((unsigned char *)city_map + (sptr))).base_kind;
    kind = (unsigned char)kind_byte;
    if (kind >= 0xbc && kind <= 0xe2) return;
    kind = (unsigned char)kind_byte;
    if (kind < 0x82) return;

    size = forum_gfxdat[kind + 0x26] & 0xff;
    if (size == 4)
        clear_sized_to_rubble(sptr, 2, 1);
    else if (size == 9)
        clear_sized_to_rubble(sptr, 3, 1);
    else if (size == 0x10)
        clear_sized_to_rubble(sptr, 4, 1);
    else
        clear_to_rubble(sptr, 1);
}

// FUNCTION: C2 0x69A77
// WIN: 0x004a5a2b
// Lines 2062–2079
//
// Directional wrapper around plague_an_atom: move the supplied
// city_map byte offset one cell north/south/west/east depending
// on dir (0,4,6,2 respectively), then plague the target building
// unless its edge_bits high bit is set.  Same size-class logic as
// plague_an_atom, inlined here so spread can skip blocked edges.
void spread_plague_atom(int sptr, int dir)
{
    int kind;
    int tile_size;

    if (dir == 0)
        sptr -= 0x640;
    else if (dir == 4)
        sptr += 0x640;
    else if (dir == 6)
        sptr -= 0x14;
    else if (dir == 2)
        sptr += 0x14;

    kind = (*(struct city_cell *)((unsigned char *)city_map + (sptr))).base_kind & 0xff;
    if (kind < 0x82) return;
    if (kind > 0xa1) return;
    if (((*(struct city_cell *)((unsigned char *)city_map + (sptr))).edge_bits & 0x80) != 0) return;

    tile_size = forum_gfxdat[kind + 0x26] & 0xff;
    if (tile_size == 4)
        plague_sized(sptr, 2);
    else if (tile_size == 9)
        plague_sized(sptr, 3);
    else
        plague_it(sptr);
}

// FUNCTION: C2 0x69AFE
// WIN: 0x004a5b27
// Lines 2081–2092
//
// Plague-mark a building footprint based on the cell at
// byte-offset `sptr`.  Reads cell.base_kind and looks up the
// building's tile-size class via forum_gfxdat[+0x26 + kind]:
//
//   * kind ∈ [0x82, 0xa1]: examine size-class:
//       - size == 4 → plague_sized(sptr, 2)  (2×2 footprint)
//       - size == 9 → plague_sized(sptr, 3)  (3×3 footprint)
//       - else      → plague_it(sptr)        (1×1 footprint)
//   * kind otherwise: no-op (not a plague-able building).
//
// Lever: explicit `& 0xff` for the byte zero-extension (not
// `(unsigned char)` cast).  Watcom emits the 2-step Watcom-
// traditional `mov dl, [m]; and edx, 0xff` zext idiom for the
// `& 0xff` form; the `(unsigned char)` cast triggers the
// 1-step `xor edx, edx; mov dl, [m]` modern idiom that PS
// doesn't use here.
void plague_an_atom(int sptr)
{
    int kind = (*(struct city_cell *)((unsigned char *)city_map + (sptr))).base_kind & 0xff;
    int tile_size;

    if (kind < 0x82) return;
    if (kind > 0xa1) return;

    tile_size = forum_gfxdat[kind + 0x26] & 0xff;
    if (tile_size == 4)
        plague_sized(sptr, 2);
    else if (tile_size == 9)
        plague_sized(sptr, 3);
    else
        plague_it(sptr);
}

// FUNCTION: C2 0x69B4B
// WIN: 0x004a5bc7
// Lines 2094–2107
//
// Spread plague (call plague_it on every cell) over a
// `size`×`size` building footprint anchored on cm_ptr
// (123 b, L2094–2107).
//
// (*(struct city_cell *)((unsigned char *)city_map + (cm_ptr))).base_kind.activity_a (byte +0x05) low nibble
// holds the cell's position within the footprint as a
// raw index n in [0, size*size).  We back-walk to the
// footprint's top-left:
//
//   rem  = n % size      (column offset within the row)
//   quot = n / size      (row offset)
//   start = cm_ptr - rem*20 - quot*1600
//
// Then plague_it is called on every cell of the
// size×size grid, advancing 20 b per column and
// (80 - size)*20 b at row end (city_map row stride 1600).
//
// `n % size` and `n / size` must be spelled as two distinct
// expressions: Watcom 10.0a does not CSE compound division here, so
// PS emits two idiv instructions.
void plague_sized(int sptr, int size)
{
    int x;
    int y;

    x = (*(struct city_cell *)((unsigned char *)city_map + (sptr))).activity_a & 0xf;
    y = x % size;
    x /= size;
    sptr = sptr - y * 20 - x * 80 * 20;
    for (y = 0; y < size; y++, sptr += (80 - size) * 20)
        for (x = 0; x < size; x++, sptr += 20)
            plague_it(sptr);
}

// FUNCTION: C2 0x69BC6
// WIN: 0x004a5c9a
// Lines 2109–2145
//
// Rubble-clear a size×size city building.  The sub-tile index in
// activity_a (+5) identifies the clicked cell within the footprint;
// walk back to the top-left, rubble every cell, then handle linked
// 2×2 gatehouse halves (base kinds 0xe9..0xf0) by clearing the paired
// footprint as well.  Ends by playing the medium/large rubble sound
// and scheduling a map refresh.
void clear_sized_to_rubble(int sptr, int size, int rubble_kind)
{
    int n;
    int yoff;
    int xoff;
    unsigned char old_kind;
    int start;
    int x;
    int y;

    n = CM_CELL(sptr).activity_a & 0xf;
    old_kind = CM_CELL(sptr).base_kind;
    xoff = n % size; yoff = n / size;   /* one line: PS's single L2115 mark */

    sptr -= xoff * 20;
    sptr -= yoff * 1600;
    start = sptr;

    for (y = 0; y < size; y++, sptr += (80 - size) * 20)
        for (x = 0; x < size; x++, sptr += 20)
            clear_to_rubble(sptr, rubble_kind);

    /* Out-of-range kinds return HERE: PS's jl/jg land on the merged
       epilogue (get_range1+0x70), so the paired-half fixup, the second
       clear loop, the rubble sound AND setup_map_screen_refresh are all
       in-range-only. */
    if (old_kind < 0xe9) return;
    if (old_kind > 0xf0) return;

    /* PS's -d1 stream marks ONE line per kind block (L2126..L2133). */
    sptr = start;
    if (old_kind == 0xe9) { if (CM_CELL(sptr + 0x12c0).base_kind == 0xea) sptr += 0x12c0; else sptr -= 0x12c0; }
    if (old_kind == 0xea) { if (CM_CELL(sptr - 0x12c0).base_kind == 0xe9) sptr -= 0x12c0; else sptr += 0x12c0; }
    if (old_kind == 0xeb) { if (CM_CELL(sptr + 0x3c).base_kind == 0xec) sptr += 0x3c; else sptr -= 0x3c; }
    if (old_kind == 0xec) { if (CM_CELL(sptr - 0x3c).base_kind == 0xeb) sptr -= 0x3c; else sptr += 0x3c; }
    if (old_kind == 0xed) { if (CM_CELL(sptr + 0x1900).base_kind == 0xee) sptr += 0x1900; else sptr -= 0x1900; }
    if (old_kind == 0xee) { if (CM_CELL(sptr - 0x1900).base_kind == 0xed) sptr -= 0x1900; else sptr += 0x1900; }
    if (old_kind == 0xef) { if (CM_CELL(sptr + 0x50).base_kind == 0xf0) sptr += 0x50; else sptr -= 0x50; }
    if (old_kind == 0xf0) { if (CM_CELL(sptr - 0x50).base_kind == 0xef) sptr -= 0x50; else sptr += 0x50; }
    for (y = 0; y < size; y++, sptr += (80 - size) * 20)
        for (x = 0; x < size; x++, sptr += 20)
            clear_to_rubble(sptr, rubble_kind);

    if (had_clear_sound == 0 || mouse_left_button == 0) {
        if (size <= 2) set_sound("medrub.wav", 1);
        else set_sound("lrgrub.wav", 1);
        if (mouse_left_button != 0) had_clear_sound = 1;
        else had_clear_sound = 0;
    }
    setup_map_screen_refresh();
}

// FUNCTION: C2 0x69E2B
// WIN: 0x004a602f
// Lines 2148–2171
//
// Turn one city cell into rubble/smoke.  rubble_kind selects fire
// rubble: set the high edge bit, seed smoke animation bytes, and play
// fire.wav.  Otherwise play the ordinary small-rubble sound, throttled
// while the mouse is held down.
void clear_to_rubble(int sptr, int rubble_kind)
{
    short r;

    stone_random_count++;
    if (stone_random_count >= 0x40) stone_random_count = 0;
    r = stone_random_data[stone_random_count];
    (*(struct city_cell *)((unsigned char *)city_map + (sptr))).base_kind = (r / 2);
    clear_basic(sptr);
    (*(struct city_cell *)((unsigned char *)city_map + (sptr))).edge_bits |= 0x40;

    if (rubble_kind != 0) {
        (*(struct city_cell *)((unsigned char *)city_map + (sptr))).edge_bits |= 0x80;
        stone_random_count += rand8;
        if (stone_random_count >= 0x40) stone_random_count = 0;
        r = stone_random_data[stone_random_count];
        (*(struct city_cell *)((unsigned char *)city_map + (sptr))).building = r;
        (*(struct city_cell *)((unsigned char *)city_map + (sptr))).fire = (r / 4 + 8);
        set_sound("fire.wav", 1);
    } else if (had_clear_sound == 0 || mouse_left_button == 0) {
        set_sound("smrub.wav", 1);
        if (mouse_left_button != 0) had_clear_sound = 1;
        else had_clear_sound = 0;
    }
    particles_cleared++;
}

// FUNCTION: C2 0x69F41
// WIN: 0x004a6183
// Lines 2173–2179
//
// Clear a single cell at byte-offset `sptr` to an "empty"
// scrub tile.  Bumps the global stone_random_count (with wrap
// at 0x40); if the cell's old base_kind was outside the scrub
// range [0x1a, 0x1d], increments particles_cleared.  Picks a
// new scrub tile id `0x1a + (random>>2)` from stone_random_data
// and writes it to base_kind.  Then tail-calls clear_basic to
// scrub the rest of the cell flags.
//
void clear_to_empty(int sptr)
{
    stone_random_count++;
    if (stone_random_count >= 0x40)
        stone_random_count = 0;
    if ((*(struct city_cell *)((unsigned char *)city_map + (sptr))).base_kind < 0x1a
            || (*(struct city_cell *)((unsigned char *)city_map + (sptr))).base_kind > 0x1d)
        particles_cleared++;
    (*(struct city_cell *)((unsigned char *)city_map + (sptr))).base_kind = ((stone_random_data[stone_random_count] >> 2) + 0x1a);
    clear_basic(sptr);
}

// FUNCTION: C2 0x69F9E
// WIN: 0x004a6203
// Lines 2181–2202
//
// Reset a city-map cell to a clean "basic" terrain state.
// Receives the cell byte-offset in eax («__watcall first arg»).
// If the cell is currently both reserved (terrain & 0x10) and
// in-use (terrain & 0x20), preserves the active building byte
// by promoting it back to base_kind.  Then unconditionally
// clears the building / fire / activity / business overlays,
// strips most terrain bits, and re-asserts the on-road bit
// (edge_bits & 1).
//
// `building` is written zero twice on purpose — PS source has
// a redundant store that survives optimisation (matches L2188
// and L2200 in the debug line table).
void clear_basic(int sptr)
{
    if (((*(struct city_cell *)((unsigned char *)city_map + ((sptr)))).terrain & 0x10) && ((*(struct city_cell *)((unsigned char *)city_map + ((sptr)))).terrain & 0x20)) {
        (*(struct city_cell *)((unsigned char *)city_map + ((sptr)))).base_kind = (*(struct city_cell *)((unsigned char *)city_map + ((sptr)))).building;
    }
    (*(struct city_cell *)((unsigned char *)city_map + ((sptr)))).building = 0;
    (*(struct city_cell *)((unsigned char *)city_map + ((sptr)))).fire = 0;
    (*(struct city_cell *)((unsigned char *)city_map + ((sptr)))).terrain &= 0x18;
    (*(struct city_cell *)((unsigned char *)city_map + ((sptr)))).edge_bits &= 2;
    (*(struct city_cell *)((unsigned char *)city_map + ((sptr)))).range_flag &= 0xfc;
    (*(struct city_cell *)((unsigned char *)city_map + ((sptr)))).fpu_flag &= 0xc0;
    (*(struct city_cell *)((unsigned char *)city_map + ((sptr)))).activity_a = 0;
    (*(struct city_cell *)((unsigned char *)city_map + ((sptr)))).activity_b = 0;
    (*(struct city_cell *)((unsigned char *)city_map + ((sptr)))).edge_bits |= 1;
    (*(struct city_cell *)((unsigned char *)city_map + ((sptr)))).building = 0;
    (*(struct city_cell *)((unsigned char *)city_map + ((sptr)))).business = 0;
}

// FUNCTION: C2 0x6A018
// WIN: 0x004a633c
// Lines 2205–2218
//
// Find the top-left of a sized (size×size) building anchored
// at `rm_offset` and call clear_reg_basic on every cell of the
// block.  The cell's `+7` byte stores a packed sub-position
// `packed = ofset_y * size + ofset_x`; we walk back ofset_x
// columns (×8 b) and ofset_y rows (×480 b = 60×8) to reach
// the top-left.  Special-cases tile == 0xd4 (warehouse marker)
// as already-top-left (ofset_x = ofset_y = 0).
//
// Globals `ofset_x`, `ofset_y` are written as a side effect.
//
void clear_sized_to_reg_basic(int rm_offset, int size)
{
    int x;
    int y;

    if (((*(struct region_cell *)((unsigned char *)region_map + (rm_offset))).base_kind) == 0xd4)
        y = x = 0;
    else
        y = x = (*(struct region_cell *)((unsigned char *)region_map + (rm_offset))).occupant & 3;
    y = y % size;
    x = x / size;
    ofset_x = y; ofset_y = x;
    rm_offset -= y * 8;
    rm_offset -= x * 60 * 8;
    for (y = 0; y < size; y++, rm_offset += (60 - size) * 8)
        for (x = 0; x < size; x++, rm_offset += 8)
            clear_reg_basic(rm_offset);
}

// FUNCTION: C2 0x6A0A6
// WIN: 0x004a6430
// Lines 2220–2233
//
// Reset a region-map cell to a clean basic state, choosing a
// stone tile id based on terrain bits at byte +1:
//   bit 0x40 set: tile = 0x18 + (random>>2)   /* mountain    */
//   bit 0x80 set: tile = 0x1c + (random>>2)   /* mountain alt*/
//   else:         tile = 0x10 + (random>>2)   /* normal      */
// Where `random = stone_random_data[stone_random_count]` (note:
// stone_random_count is *not* advanced — just sampled).
//
// Then if bit 1 of byte +1 is set, zero byte +7 (warehouse-like
// link).  Strip terrain bits to (& 0xd8), normalize edge bits to
// just bit 1, then re-assert bit 1 (so the cell is marked basic).
// Used by clear_sized_to_reg_basic to clear sized buildings.
void clear_reg_basic(int rm_offset)
{
    if ((*(struct region_cell *)((unsigned char *)region_map + (rm_offset))).terrain & 0x40) {
        (*(struct region_cell *)((unsigned char *)region_map + (rm_offset))).base_kind = (char)((stone_random_data[stone_random_count]) / 4 + 0x18);
    } else if ((*(struct region_cell *)((unsigned char *)region_map + (rm_offset))).terrain & 0x80) {
        (*(struct region_cell *)((unsigned char *)region_map + (rm_offset))).base_kind = (char)((stone_random_data[stone_random_count]) / 4 + 0x1c);
    } else {
        (*(struct region_cell *)((unsigned char *)region_map + (rm_offset))).base_kind = (char)((stone_random_data[stone_random_count]) / 4 + 0x10);
    }
    if ((*(struct region_cell *)((unsigned char *)region_map + (rm_offset))).terrain & 1) {
        (*(struct region_cell *)((unsigned char *)region_map + (rm_offset))).occupant = 0;
    }
    (*(struct region_cell *)((unsigned char *)region_map + (rm_offset))).terrain   &= 0xd8;
    (*(struct region_cell *)((unsigned char *)region_map + (rm_offset))).edge_bits &= 2;
    (*(struct region_cell *)((unsigned char *)region_map + (rm_offset)))._unused05  = 0;
    (*(struct region_cell *)((unsigned char *)region_map + (rm_offset))).outside    = 0;
    (*(struct region_cell *)((unsigned char *)region_map + (rm_offset))).edge_bits |= 1;
}

// FUNCTION: C2 0x6A17A
// WIN: 0x004a6555
// Lines 2235–2246
//
// Mark cell at byte-offset `sptr` as plague-stricken.  Strips
// fpu_flag low bits (& 0xc0), sets edge_bits 0x81 (on-road +
// extra), advances stone_random_count by rand8 (with wrap at
// 0x40), copies one byte of stone_random_data to extra_edge,
// and sets activity_b to plague-marker 0x0a.
void plague_it(int sptr)
{
    (*(struct city_cell *)((unsigned char *)city_map + (sptr))).fpu_flag &= 0xc0;
    (*(struct city_cell *)((unsigned char *)city_map + (sptr))).edge_bits |= 0x81;
    stone_random_count = stone_random_count + (char)rand8;
    if (stone_random_count >= 0x40)
        stone_random_count = 0;
    (*(struct city_cell *)((unsigned char *)city_map + (sptr))).building = stone_random_data[stone_random_count];
    (*(struct city_cell *)((unsigned char *)city_map + (sptr))).fire = 0x0a;
}

// FUNCTION: C2 0x6A1CB
// WIN: 0x004a6605
// Lines 2248–2281
//
// Build/fill every legal city-map cell in the inclusive rectangle
// bounded by (x1,y1) and (x2,y2).  Illegal cells are skipped rather
// than aborting the whole fill.  If no cell was placed, sets
// illegal_build.  Used by the drag-to-build area tool.
void build_an_area(int x1, int y1, int x2, int y2,
                   int base_kind, int edge_bits, int color)
{
    int row_skip;
    int x;
    int y;
    int t;
    unsigned char old_kind;
    unsigned char bk;

    bk = (unsigned char)base_kind;
    if (x1 > x2) { t = x2; x2 = x1; x1 = t; }
    if (y1 > y2) { t = y2; y2 = y1; y1 = t; }

    cm_sptr = (x1 + y1 * CITY_W) * CITY_CELL_BYTES;
    row_skip = (CITY_W - (x2 - x1) - 1) * CITY_CELL_BYTES;
    for (y = y1; y <= y2; y++, cm_sptr += row_skip) {
        for (x = x1; x <= x2; x++, cm_sptr += CITY_CELL_BYTES) {
            CM_CELL(cm_sptr).edge_bits |= 1;
            if ((CM_CELL(cm_sptr).terrain & 0x10) == 0 &&
                (CM_CELL(cm_sptr).terrain & 0xe7) == 0 &&
                (CM_CELL(cm_sptr).base_kind >= 8 ||
                 (CM_CELL(cm_sptr).edge_bits & 0x80) == 0) &&
                CM_CELL(cm_sptr).citizen_a == 0 &&
                CM_CELL(cm_sptr).citizen_b == 0) {
                old_kind = CM_CELL(cm_sptr).base_kind;
                particles_built++;
                if (old_kind < 0x1a) particles_cleared++;
                CM_CELL(cm_sptr).base_kind = bk;
                CM_CELL(cm_sptr).terrain |= placing_flags;
                CM_CELL(cm_sptr).extra_edge = color;
                CM_CELL(cm_sptr).edge_bits &= 0xe3;
                CM_CELL(cm_sptr).edge_bits |= edge_bits;
                CM_CELL(cm_sptr).activity_a = 0;
            }
        }
    }
    if (particles_built == 0) illegal_build = 1;
}

// FUNCTION: C2 0x6A341
// WIN: 0x004a683b
// Lines 2284–2307
//
// Place a 1×1 city-map atom at (x,y).  Rejects blocked / occupied
// cells, records the placement origin globals, counts built/cleared
// particles, stamps base_kind/placing_flags/color/edge bits, and
// clears the secondary image byte.  Returns 1 on success, 0 on illegal
// placement (setting illegal_build).
int put_x1_area(int x, int y, char base_kind, int edge_bits, int color)
{

    start_sptr = (x + y * 80) * 20;
    start_x_pos = x;
    start_y_pos = y;
    cm_sptr = start_sptr;

    if (((*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).terrain & 0x10) != 0) {
    illegal:
        illegal_build = 1;
        return 0;
    }
    if (((*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).terrain & 0xe7) != 0) goto illegal;
    if ((unsigned char)(*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).base_kind < 8 && ((*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).edge_bits & 0x80) != 0) goto illegal;
    if ((*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).citizen_a != 0) goto illegal;
    if ((*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).citizen_b != 0) goto illegal;

    particles_built++;
    if ((unsigned char)(*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).base_kind < 0x1a) particles_cleared++;
    (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).edge_bits |= 1;
    (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).base_kind = base_kind;
    (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).terrain |= placing_flags;
    (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).extra_edge = (char)color;
    (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).edge_bits &= 0xe3;
    (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).edge_bits |= (char)edge_bits;
    (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).activity_a = 0;
    return 1;
}

// FUNCTION: C2 0x6A43F
// WIN: 0x004a6a13
// Lines 2309–2357
//
// Stamp a 2x2 square on city_map starting at the placement anchor.
// Rotates the anchor by map_direction, validates the 4 cells are
// empty, then writes base_kind / edge_bits / color +
// diamond_ofsets_2x[n].  Returns 1 on success, 0 on any blocked cell.
int put_x2_area(int x, int y, char base_kind, int edge_bits, int color)
{
    int row_skip;
    int xi;
    int yi;
    int n;
    int bad = 0;
    row_skip = (80 - 2) * 20;

    if (map_direction == 2) x -= 1;
    if (map_direction == 6) y -= 1;
    if (map_direction == 4) {
        x -= 1;
        y -= 1;
    }
    if (x < 0) {
    illegal:
        illegal_build = 1;
        return 0;
    }
    if (y < 0) goto illegal;
    if (x + 1 >= 80) goto illegal;
    if (y + 1 >= 80) goto illegal;

    start_x_pos = x;
    start_y_pos = y;
    start_sptr = (x + y * 80) * 20;
    cm_sptr = start_sptr;

    for (yi = y; yi < y + 2; ) {
        for (xi = x; xi < x + 2; ) {
            if (((*(struct city_cell *)((unsigned char *)city_map + ((cm_sptr)))).terrain   & 0x10) != 0) bad = 1;
            if (((*(struct city_cell *)((unsigned char *)city_map + ((cm_sptr)))).terrain   & 0xe7) != 0) bad = 1;
            if ((unsigned char)(*(struct city_cell *)((unsigned char *)city_map + ((cm_sptr)))).base_kind < 8 &&
                ((*(struct city_cell *)((unsigned char *)city_map + ((cm_sptr)))).edge_bits & 0x80) != 0) bad = 1;
            if ((*(struct city_cell *)((unsigned char *)city_map + ((cm_sptr)))).citizen_a != 0) bad = 1;
            if ((*(struct city_cell *)((unsigned char *)city_map + ((cm_sptr)))).citizen_b != 0) bad = 1;
            (*(struct city_cell *)((unsigned char *)city_map + ((cm_sptr)))).edge_bits |= 1;
            xi++;
            cm_sptr += 20;
        }
        yi++;
        cm_sptr += row_skip;
    }
    if (bad) goto illegal;

    cm_sptr = start_sptr;
    n = 0;
    for (yi = y; yi < y + 2; ) {
        for (xi = x; xi < x + 2; ) {
            if ((unsigned char)(*(struct city_cell *)((unsigned char *)city_map + ((cm_sptr)))).base_kind < 0x1a)
                particles_cleared++;
            (*(struct city_cell *)((unsigned char *)city_map + ((cm_sptr)))).base_kind        = base_kind;
            (*(struct city_cell *)((unsigned char *)city_map + ((cm_sptr)))).terrain    |= placing_flags;
            (*(struct city_cell *)((unsigned char *)city_map + ((cm_sptr)))).extra_edge  = (char)(color + diamond_ofsets_2x[n]);
            (*(struct city_cell *)((unsigned char *)city_map + ((cm_sptr)))).edge_bits  &= 0xe3;
            (*(struct city_cell *)((unsigned char *)city_map + ((cm_sptr)))).edge_bits  |= (char)edge_bits;
            (*(struct city_cell *)((unsigned char *)city_map + ((cm_sptr)))).activity_a  = n;
            if (map_direction == 2 || map_direction == 4)
                (*(struct city_cell *)((unsigned char *)city_map + ((cm_sptr)))).activity_b = 0x20;
            xi++;
            cm_sptr += 20;
            n++;
        }
        yi++;
        cm_sptr += row_skip;
    }
    particles_built++;
    return 1;
}

// FUNCTION: C2 0x6A669
// WIN: 0x004a6d79
// Lines 2359–2408
//
// BYTE-EXACT.  Mirrors put_x4_area exactly: params modified in
// place (no x0/y0 copies -- parm homing emits copies-then-spills
// like PS) AND the direction subtract is the CONSTANT `x -= 2`
// (matching x4's `x -= 3`), not `x -= map_direction`.  The constant
// removes one dword rover advance, which is what kept the 2nd-loop
// map_direction compare in ECX (the earlier x-direct attempt used
// the variable subtract and shifted the rover, landing it in EAX).
int put_x3_area(int x, int y, char base_kind, int edge_bits, int color)
{
    int row_skip;
    int xi;
    int yi;
    int n;
    int bad = 0;
    row_skip = (80 - 3) * 20;

    if (map_direction == 2) x -= 2;
    if (map_direction == 6) y -= 2;
    if (map_direction == 4) {
        x -= 2;
        y -= 2;
    }
    if (x < 0) {
    illegal:
        illegal_build = 1;
        return 0;
    }
    if (y < 0) goto illegal;
    if (x + 2 >= 80) goto illegal;
    if (y + 2 >= 80) goto illegal;

    start_x_pos = x;
    start_y_pos = y;
    start_sptr = (x + y * 80) * 20;
    cm_sptr = start_sptr;

    for (yi = y; yi < y + 3; ) {
        for (xi = x; xi < x + 3; ) {
            if (((*(struct city_cell *)((unsigned char *)city_map + ((cm_sptr)))).terrain   & 0x10) != 0) bad = 1;
            if (((*(struct city_cell *)((unsigned char *)city_map + ((cm_sptr)))).terrain   & 0xe7) != 0) bad = 1;
            if ((unsigned char)(*(struct city_cell *)((unsigned char *)city_map + ((cm_sptr)))).base_kind < 8 &&
                ((*(struct city_cell *)((unsigned char *)city_map + ((cm_sptr)))).edge_bits & 0x80) != 0) bad = 1;
            if ((*(struct city_cell *)((unsigned char *)city_map + ((cm_sptr)))).citizen_a != 0) bad = 1;
            if ((*(struct city_cell *)((unsigned char *)city_map + ((cm_sptr)))).citizen_b != 0) bad = 1;
            (*(struct city_cell *)((unsigned char *)city_map + ((cm_sptr)))).edge_bits |= 1;
            xi++;
            cm_sptr += 20;
        }
        yi++;
        cm_sptr += row_skip;
    }
    if (bad) goto illegal;

    cm_sptr = start_sptr;
    n = 0;
    for (yi = y; yi < y + 3; ) {
        for (xi = x; xi < x + 3; ) {
            if ((unsigned char)(*(struct city_cell *)((unsigned char *)city_map + ((cm_sptr)))).base_kind < 0x1a)
                particles_cleared++;
            (*(struct city_cell *)((unsigned char *)city_map + ((cm_sptr)))).base_kind        = base_kind;
            (*(struct city_cell *)((unsigned char *)city_map + ((cm_sptr)))).terrain    |= placing_flags;
            (*(struct city_cell *)((unsigned char *)city_map + ((cm_sptr)))).extra_edge  = (char)(color + diamond_ofsets_3x[n]);
            (*(struct city_cell *)((unsigned char *)city_map + ((cm_sptr)))).edge_bits  &= 0xe3;
            (*(struct city_cell *)((unsigned char *)city_map + ((cm_sptr)))).edge_bits  |= (char)edge_bits;
            (*(struct city_cell *)((unsigned char *)city_map + ((cm_sptr)))).activity_a  = n;
            if (map_direction == 2 || map_direction == 4)
                (*(struct city_cell *)((unsigned char *)city_map + ((cm_sptr)))).activity_b = 0x20;
            xi++;
            cm_sptr += 20;
            n++;
        }
        yi++;
        cm_sptr += row_skip;
    }
    particles_built++;
    return 1;
}

// FUNCTION: C2 0x6A889
// WIN: 0x004a70e7
// Lines 2410–2458
//
// Sister of put_x2_area for a 4x4 square; uses diamond_ofsets_4x[n]
// for the per-cell color offset.
int put_x4_area(int x, int y, char base_kind, int edge_bits, int color)
{
    int row_skip;
    int xi;
    int yi;
    int n;
    int bad = 0;
    row_skip = (80 - 4) * 20;

    if (map_direction == 2) x -= 3;
    if (map_direction == 6) y -= 3;
    if (map_direction == 4) {
        x -= 3;
        y -= 3;
    }
    if (x < 0) {
    illegal:
        illegal_build = 1;
        return 0;
    }
    if (y < 0) goto illegal;
    if (x + 3 >= 80) goto illegal;
    if (y + 3 >= 80) goto illegal;

    start_x_pos = x;
    start_y_pos = y;
    start_sptr = (x + y * 80) * 20;
    cm_sptr = start_sptr;

    for (yi = y; yi < y + 4; ) {
        for (xi = x; xi < x + 4; ) {
            if (((*(struct city_cell *)((unsigned char *)city_map + ((cm_sptr)))).terrain   & 0x10) != 0) bad = 1;
            if (((*(struct city_cell *)((unsigned char *)city_map + ((cm_sptr)))).terrain   & 0xe7) != 0) bad = 1;
            if ((unsigned char)(*(struct city_cell *)((unsigned char *)city_map + ((cm_sptr)))).base_kind < 8 &&
                ((*(struct city_cell *)((unsigned char *)city_map + ((cm_sptr)))).edge_bits & 0x80) != 0) bad = 1;
            if ((*(struct city_cell *)((unsigned char *)city_map + ((cm_sptr)))).citizen_a != 0) bad = 1;
            if ((*(struct city_cell *)((unsigned char *)city_map + ((cm_sptr)))).citizen_b != 0) bad = 1;
            (*(struct city_cell *)((unsigned char *)city_map + ((cm_sptr)))).edge_bits |= 1;
            xi++;
            cm_sptr += 20;
        }
        yi++;
        cm_sptr += row_skip;
    }
    if (bad) goto illegal;

    cm_sptr = start_sptr;
    n = 0;
    for (yi = y; yi < y + 4; ) {
        for (xi = x; xi < x + 4; ) {
            if ((unsigned char)(*(struct city_cell *)((unsigned char *)city_map + ((cm_sptr)))).base_kind < 0x1a)
                particles_cleared++;
            (*(struct city_cell *)((unsigned char *)city_map + ((cm_sptr)))).base_kind        = base_kind;
            (*(struct city_cell *)((unsigned char *)city_map + ((cm_sptr)))).terrain    |= placing_flags;
            (*(struct city_cell *)((unsigned char *)city_map + ((cm_sptr)))).extra_edge  = (char)(color + diamond_ofsets_4x[n]);
            (*(struct city_cell *)((unsigned char *)city_map + ((cm_sptr)))).edge_bits  &= 0xe3;
            (*(struct city_cell *)((unsigned char *)city_map + ((cm_sptr)))).edge_bits  |= (char)edge_bits;
            (*(struct city_cell *)((unsigned char *)city_map + ((cm_sptr)))).activity_a  = n;
            if (map_direction == 2 || map_direction == 4)
                (*(struct city_cell *)((unsigned char *)city_map + ((cm_sptr)))).activity_b = 0x20;
            xi++;
            cm_sptr += 20;
            n++;
        }
        yi++;
        cm_sptr += row_skip;
    }
    particles_built++;
    return 1;
}

// FUNCTION: C2 0x6AAAB
// WIN: 0x004a7455
// Lines 2460–2474
//
// Stamp a square (1×1, 2×2, 3×3, or 4×4) on the city map
// starting at byte-offset `sptr`, writing `bk` to base_kind
// and computing the upper sprite (extra_edge) from `color`
// plus the size-specific diamond offset table
// (`diamond_ofsets_Nx[n]`).  Sets the on-road bit (edge_bits & 1)
// on every cell.
void change_sized(int bk, int color, int size, int sptr)
{
    int xi;
    int yi;
    int n;
    int row_step = (80 - size) * 20;

    for (yi = 0, n = 0; yi < size; ) {
        for (xi = 0; xi < size; ) {
            (*(struct city_cell *)((unsigned char *)city_map + (sptr))).base_kind = bk;
            (*(struct city_cell *)((unsigned char *)city_map + (sptr))).edge_bits |= 1;
            if (size == 1) {
                (*(struct city_cell *)((unsigned char *)city_map + (sptr))).extra_edge = color;
            } else if (size == 2) {
                (*(struct city_cell *)((unsigned char *)city_map + (sptr))).extra_edge =
                    color + diamond_ofsets_2x[n];
            } else if (size == 3) {
                (*(struct city_cell *)((unsigned char *)city_map + (sptr))).extra_edge =
                    color + diamond_ofsets_3x[n];
            } else if (size == 4) {
                (*(struct city_cell *)((unsigned char *)city_map + (sptr))).extra_edge =
                    color + diamond_ofsets_4x[n];
            }
            xi++;
            sptr += 20;
            n++;
        }
        yi++;
        sptr += row_step;
    }
}

// FUNCTION: C2 0x6AB34
// WIN: 0x004a7573
// Lines 2477–2498
//
// Mark a directed size×size placement footprint on city_map.  The
// visible anchor (x,y) is shifted according to map_direction so the
// footprint extends in the direction the cursor/building preview faces,
// then every covered city cell has edge_bits bit0 set.  Also stamps
// start_x_pos/start_y_pos/start_sptr/cm_sptr for later placement code.
void set_map_ref(int x, int y, int size)
{
    int row_skip;
    int sptr;
    int xi;
    int yi;
    int sm1;

    row_skip = (80 - size) * 20;
    if (map_direction == 2)
        x -= size - 1;
    if (map_direction == 6)
        y -= size - 1;
    if (map_direction == 4) {
        x -= size - 1;
        y -= size - 1;
    }
    if (x < 0) return;
    if (y < 0) return;
    sm1 = size - 1;
    if (x + sm1 >= 80) return;
    if (y + sm1 >= 80) return;

    start_x_pos = x;
    start_y_pos = y;
    sptr = (x + y * 80) * 20;
    start_sptr = sptr;
    cm_sptr = sptr;
    for (yi = y; yi < y + size; yi++, cm_sptr += row_skip) {
        for (xi = x; xi < x + size; xi++, cm_sptr += 20) {
            (*(struct city_cell *)((unsigned char *)city_map + (cm_sptr))).edge_bits |= 1;
        }
    }
}

// FUNCTION: C2 0x6AC09
// WIN: 0x004a76d5
// Lines 2501–2522
//
// Region-map 1×1 placement.  `strict_flags` selects the occupancy
// check used by region industry placement: when true, only the low
// six flag bits block; otherwise any flag byte blocks.  Returns 1 on
// success, 0 on blocked.
int put_reg_x1_area(int x, int y, unsigned char base_kind, int edge_bits,
                    int color, int strict_flags)
{
    start_x_pos = x; start_y_pos = y;
    x = x + y * 60; start_sptr = x * 8;
    cm_sptr = start_sptr;

    if (strict_flags == 1) { if (((*(struct region_cell *)((unsigned char *)region_map + (cm_sptr))).terrain & 0x3f) != 0) return 0; }
    else { if (((*(struct region_cell *)((unsigned char *)region_map + (cm_sptr))).terrain & 0xff) != 0) return 0; }
    if ((*(struct region_cell *)((unsigned char *)region_map + (cm_sptr))).occupant != 0) return 0;

    particles_built++;
    if ((*(struct region_cell *)((unsigned char *)region_map + (cm_sptr))).base_kind < 0x10) particles_cleared++;
    (*(struct region_cell *)((unsigned char *)region_map + (cm_sptr))).edge_bits |= 1;
    (*(struct region_cell *)((unsigned char *)region_map + (cm_sptr))).base_kind = (unsigned char)base_kind;
    (*(struct region_cell *)((unsigned char *)region_map + (cm_sptr))).terrain |= reg_placing_flags;
    (*(struct region_cell *)((unsigned char *)region_map + (cm_sptr))).gfx = (unsigned char)color;
    (*(struct region_cell *)((unsigned char *)region_map + (cm_sptr))).edge_bits &= 0xe3;
    (*(struct region_cell *)((unsigned char *)region_map + (cm_sptr))).edge_bits |= (unsigned char)edge_bits;
    (*(struct region_cell *)((unsigned char *)region_map + (cm_sptr))).edge_bits &= 0xbf;
    (*(struct region_cell *)((unsigned char *)region_map + (cm_sptr))).occupant = 0;
    return 1;
}

// FUNCTION: C2 0x6ACD1
// WIN: 0x004a7852
// Lines 2524–2569
//
// Region-map sister of put_x2_area: stamp a 2x2 square of
// region_map cells.  `strict_flags` selects the occupancy check
// (when true, only low 6 flag bits block; otherwise any flag
// blocks).  Returns 1 on success, 0 on blocked.
int put_reg_x2_area(int x, int y, unsigned char base_kind, int edge_bits,
                    int color, int strict_flags)
{
    int xi;
    int yi;
    int n;
    int off;
    int bad;
    int row_skip;

    bad = 0;
    row_skip = (60 - 2) * 8;

    if (map_direction == 2) x--;
    if (map_direction == 6) y--;
    if (map_direction == 4) { x--; y--; }
    if (x < 0) return 0;
    if (y < 0) return 0;
    if (x + 1 >= 60) return 0;
    if (y + 1 >= 60) return 0;

    start_x_pos = x;
    start_y_pos = y;
    off = ((x) + (y) * 60) * 8;
    start_sptr = off;
    cm_sptr = off;

    for (yi = y; yi < y + 2; yi++, cm_sptr += row_skip) {
        for (xi = x; xi < x + 2; xi++, cm_sptr += 8) {
            if (strict_flags == 1) {
                if (((*(struct region_cell *)((unsigned char *)region_map + (cm_sptr))).terrain & 0x3f) != 0) bad = 1;
            } else {
                if ((int)(*(struct region_cell *)((unsigned char *)region_map + (cm_sptr))).terrain != 0) bad = 1;
            }
            if ((*(struct region_cell *)((unsigned char *)region_map + (cm_sptr))).occupant != 0) bad = 1;
            (*(struct region_cell *)((unsigned char *)region_map + (cm_sptr))).edge_bits |= 1;
        }
    }
    if (bad) return 0;

    cm_sptr = start_sptr;
    n = 0;
    for (yi = y; yi < y + 2; yi++, cm_sptr += row_skip) {
        for (xi = x; xi < x + 2; xi++, cm_sptr += 8, n++) {
            if ((*(struct region_cell *)((unsigned char *)region_map + (cm_sptr))).base_kind < 0x10) particles_cleared++;
            (*(struct region_cell *)((unsigned char *)region_map + (cm_sptr))).base_kind = (unsigned char)base_kind;
            (*(struct region_cell *)((unsigned char *)region_map + (cm_sptr))).terrain |= reg_placing_flags;
            (*(struct region_cell *)((unsigned char *)region_map + (cm_sptr))).gfx = color + diamond_ofsets_2x[n];
            (*(struct region_cell *)((unsigned char *)region_map + (cm_sptr))).edge_bits &= 0xe3;
            (*(struct region_cell *)((unsigned char *)region_map + (cm_sptr))).edge_bits |= (unsigned char)edge_bits;
            (*(struct region_cell *)((unsigned char *)region_map + (cm_sptr))).edge_bits &= 0xbf;
            (*(struct region_cell *)((unsigned char *)region_map + (cm_sptr))).occupant = (unsigned char)n;
        }
    }
    particles_built++;
    return 1;
}

// FUNCTION: C2 0x6AEAC
// WIN: 0x004a7b37
// Lines 2571–2583
//
// Stamp a `size × size` square (size ∈ {1, 2, 3, …}) of region-map
// cells starting at byte-offset `rm_offset` from `region_map`.  Every
// cell gets:
//   +0   = (char)rm_byte           // base value (e.g. terrain id)
//   +3  |= 1                        // mark cell as "modified"
//   +4   = color (size==1) or       // for 1×1 just the color
//          diamond_ofsets_2x[n] + color  (size==2)
//                                   // for 2×2, +0..+3 stamp variants
// Cells are 8 bytes wide; the region-map row stride is 60 cells
// (60×8 = 480 bytes).  For size>2 the +4 byte is left untouched.
//
void change_reg_sized(int rm_byte, int color, int size, int rm_offset)
{
    int xi;
    int yi;
    int n;
    int row_step = (60 - size) * 8;

    for (yi = 0, n = 0; yi < size; ) {
        for (xi = 0; xi < size; ) {
            (*(struct region_cell *)((unsigned char *)region_map + (rm_offset))).base_kind = rm_byte;
            (*(struct region_cell *)((unsigned char *)region_map + (rm_offset))).edge_bits |= 1;
            if (size == 1) {
                (*(struct region_cell *)((unsigned char *)region_map + (rm_offset))).gfx = color;
            } else if (size == 2) {
                (*(struct region_cell *)((unsigned char *)region_map + (rm_offset))).gfx =
                    color + diamond_ofsets_2x[n];
            }
            xi++;
            rm_offset += 8;
            n++;
        }
        yi++;
        rm_offset += row_step;
    }
}

// FUNCTION: C2 0x6AF11
// WIN: 0x004a7c06
// Lines 2586–2625
//
// Stamp an arbitrary size×size region-map square.  Rejects cells with
// an occupant at +7, blocked bit 0x10, or low flag bit set; on success
// writes base_kind, placing flags, edge bits, and a size-dependent
// diamond/color byte.  Returns 1 on success, 0 on any early reject.
int put_rm_area(int x, int y, int size, unsigned char base_kind,
                int edge_bits, int color, int flags)
{
    int row_skip;
    int off, xi, yi, n;
    unsigned char c = color;


    row_skip = (60 - size) * 8;

    if (map_direction == 2) x -= size - 1;
    if (map_direction == 6) y -= size - 1;
    if (map_direction == 4) { x -= size - 1; y -= size - 1; }
    if (x < 0) return 0;
    if (y < 0) return 0;

    off = (x + y * 60) * 8;
    for (yi = y; yi < y + size; yi++, off += row_skip) {
        for (xi = x; xi < x + size; xi++, off += 8) {

            if ((*(struct region_cell *)((unsigned char *)region_map + (off))).occupant != 0) return 0;
            if (((*(struct region_cell *)((unsigned char *)region_map + (off))).terrain & 0x10) != 0) return 0;
            if (((*(struct region_cell *)((unsigned char *)region_map + (off))).terrain & 1) != 0) return 0;
            (*(struct region_cell *)((unsigned char *)region_map + (off))).edge_bits |= 1;
        }
    }
    off = (x + y * 60) * 8;
    for (yi = y, n = 0; yi < y + size; yi++, off += row_skip) {
        for (xi = x; xi < x + size; xi++, off += 8, n++) {

            (*(struct region_cell *)((unsigned char *)region_map + (off))).base_kind = base_kind;
            (*(struct region_cell *)((unsigned char *)region_map + (off))).terrain |= flags;
            (*(struct region_cell *)((unsigned char *)region_map + (off))).edge_bits &= 0xe3;
            (*(struct region_cell *)((unsigned char *)region_map + (off))).edge_bits |= edge_bits;
            if (size == 1) (*(struct region_cell *)((unsigned char *)region_map + (off))).gfx = c;
            else if (size == 2) (*(struct region_cell *)((unsigned char *)region_map + (off))).gfx = c + diamond_ofsets_2x[n];
            else if (size == 3) (*(struct region_cell *)((unsigned char *)region_map + (off))).gfx = c + diamond_ofsets_3x[n];
            else if (size == 4) (*(struct region_cell *)((unsigned char *)region_map + (off))).gfx = c + diamond_ofsets_4x[n];
        }
    }
    return 1;
}

// FUNCTION: C2 0x6B08C
// WIN: 0x004a7ec5
// Lines 2627–2645
//
// OR mask_byte into the +1 terrain/flag byte of every region_map cell
// in a size×size square.  The x/y origin is adjusted for map_direction
// so the square is anchored around the user-facing placement direction.
// No-op when the adjusted origin falls off the top/left edge.  Sister of
// unflag_rm_area (which ANDs instead of ORs).
void flag_rm_area(int x, int y, int size, char mask_byte)
{
    int row_skip = (60 - size) * 8;
    int rm_offset;
    int xi;
    int yi;

    if (map_direction == 2)
        x -= size - 1;
    if (map_direction == 6)
        y -= size - 1;
    if (map_direction == 4) {
        x -= size - 1;
        y -= size - 1;
    }
    if (x < 0) return;
    if (y < 0) return;

    rm_offset = ((x) + (y) * 60) * 8;
    for (yi = y; yi < y + size; yi++, rm_offset += row_skip) {
        for (xi = x; xi < x + size; xi++, rm_offset += 8) {
            (*(struct region_cell *)((unsigned char *)region_map + (rm_offset))).terrain |= mask_byte;
        }
    }
}

// FUNCTION: C2 0x6B126
// WIN: 0x004a7fd4
// Lines 2647–2665
//
// AND mask_byte into the +1 (terrain bits) byte of every region_map
// cell in the size x size square at (x, y).  No-op if (x < 0) or
// (y < 0).  Sister of flag_rm_area which ORs instead.
void unflag_rm_area(int x, int y, int size, char mask_byte)
{
    int row_skip = (60 - size) * 8;
    int rm_offset;
    int xi;
    int yi;

    if (x < 0) return;
    if (y < 0) return;

    rm_offset = ((x) + (y) * 60) * 8;

    for (yi = y; yi < y + size; yi++, rm_offset += row_skip) {
        for (xi = x; xi < x + size; xi++, rm_offset += 8) {
            (*(struct region_cell *)((unsigned char *)region_map + (rm_offset))).terrain &= mask_byte;
        }
    }
}

// FUNCTION: C2 0x6B18C
// WIN: 0x004a808c
// Lines 2669–2692
//
// Validate that a 2×2 region industry footprint overlaps exactly four
// cells with the requested terrain flag (farm/mine/quarry masks).  The
// footprint anchor is rotated like other 2×2 region placements.
void check_region_map_for_farm_square(int x, int y, char mask)
{
    int count;
    int xi;
    int yi;
    int row_skip;

    industry_build_ok = 1;
    count = 0;
    row_skip = (60 - 2) * 8;
    if (map_direction == 2) x--;
    if (map_direction == 6) y--;
    if (map_direction == 4) { x--; y--; }
    if (x < 0 || y < 0 || x + 1 >= 60 || y + 1 >= 60) return;

    cm_sptr = ((x) + (y) * 60) * 8;
    for (yi = y; yi < y + 2; yi++, cm_sptr += row_skip) {
        for (xi = x; xi < x + 2; xi++, cm_sptr += 8) {
            if (((*(struct region_cell *)((unsigned char *)region_map + (cm_sptr))).terrain & mask) != 0) count++;
        }
    }
    if (count == 4) industry_build_ok = 0;
    else illegal_build = 1;
}

// FUNCTION: C2 0x6B26D
// WIN: 0x004a81d2
// Lines 2695–2719
//
// Validate a 2×2 port footprint: at least one covered tile must have a
// coast neighbour on its negative edge.  On success, industry_build_ok
// is cleared; otherwise illegal_build is set.
void check_region_map_for_port_square(int x, int y)
{
    int row_skip;

    industry_build_ok = 1;
    row_skip = (60 - 2) * 8;
    if (map_direction == 2) x--;
    if (map_direction == 6) y--;
    if (map_direction == 4) { x--; y--; }
    if (x < 0 || y < 0 || x + 1 >= 60 || y + 1 >= 60) return;

    gmn_sptr = ((x) + (y) * 60) * 8;
    for (gmn_y = y; gmn_y < y + 2; gmn_y++, gmn_sptr += row_skip) {
        for (gmn_x = x; gmn_x < x + 2; gmn_x++, gmn_sptr += 8) {
            test_regionmap_neighbours_negedge(8);
            if (gmn_polar_count != 0) {
                industry_build_ok = 0;
                return;
            }
        }
    }
    illegal_build = 1;
}

// FUNCTION: C2 0x6B347
// WIN: 0x004a8311
// Lines 2722–2759
//
// Re-evaluate coast tiles in a clipped region rectangle.  For every
// water/coast candidate, compute neighbour bits, choose a matching coast
// sprite, and update the impassable/coast flag from coast_data.
void adjust_regions_coastline(int x, int y, int width, int height)
{
    int x0 = x;
    int y0 = y;
    int x1 = x + width;
    int y1 = y + height;
    int kind;

    if (x0 < 0) x0 = 0;
    if (y0 < 0) y0 = 0;
    if (x1 > 60) x1 = 60;
    if (y1 > 60) y1 = 60;

    init_choices(coast_data, 0x30);
    for (gmn_y = y0; gmn_y < y1; gmn_y++) {
        for (gmn_x = x0; gmn_x < x1; gmn_x++) {
            gmn_sptr = ((gmn_x) + (gmn_y) * 60) * 8;
            if (((*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).terrain & 8) != 0 &&
                ((*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).terrain & 1) == 0) {
                test_regionmap_neighbours_posedge(8);
                invert_gmn();
                if (choose_from(coast_data, 0x30) == 0)
                    high_beep();
                (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).base_kind = first_choice + choice_count - 0x10;
                (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).edge_bits |= 1;
                kind = (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).base_kind & 0xff;
                if (kind < 0x7c) {
                    unsigned char sea = sailable_sea[kind - SAILABLE_SEA_FIRST_TILE];
                    if (sea)
                        (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).terrain &= 0xef;
                    else
                        (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).terrain |= 0x10;
                }
            }
        }
    }
}

// FUNCTION: C2 0x6B474
// WIN: 0x004a84fc
// Lines 2761–2775
//
// Sweep the 60x60 region_map grid.  For cells whose +1 flag has
// bit 0x08 set, check the base tile byte against coast_data+0x220;
// if that coast-data byte is non-zero (and base < 0x7c), clear
// bit 0x10 in the same +1 flag.  gmn_sptr is the running byte
// offset into region_map (8 bytes per region cell).
void adjust_sailable_area(void)
{
    unsigned char tile;
    unsigned char coast;

    gmn_y = 0;
    gmn_sptr = 0;
    for ( ; gmn_y < 0x3c; gmn_y++) {
    for (gmn_x = 0; gmn_x < 0x3c; gmn_x++, gmn_sptr += 8) {
    if (((*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).terrain & 8) != 0) {
        tile = (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).base_kind;
        if (tile < 0x7c) {
            coast = sailable_sea[tile - SAILABLE_SEA_FIRST_TILE];
            if (coast != 0)
                (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).terrain &= 0xef;
        }
    }
    }
    }
}

// FUNCTION: C2 0x6B4F3
// WIN: 0x004a85d6
// Lines 2783–2828
//
// Read the 8-neighbour mask of (gmn_x, gmn_y) on city_map into the
// gmn[0..7] array plus the various counters (gmn_count / polar /
// ns / ew / nesw / nwse / density / max_run).  Edge cells off the
// grid count as `1` (positive edge: "present" outside the map).
void test_citymap_neighbours_posedge(char mask)
{
    int i;

    gmn_count = gmn_polar_count = gmn_density = 0;
    gmn_ns_count = gmn_ew_count = gmn_nesw_count = gmn_nwse_count = 0;
    gmn_run = gmn_max_run = 0;

    if (gmn_y == 0) { gmn[0] = 1; gmn_density = -1; }
    else gmn[0] = (*(struct city_cell *)((unsigned char *)city_map + ((gmn_sptr) - CITY_ROW))).terrain & mask;
    if (gmn[0]) { gmn_count++; gmn_polar_count++; gmn_ns_count++; gmn_density++; }

    if (gmn_y == 0 || gmn_x == 79) { gmn[1] = 1; gmn_nesw_count--; }
    else gmn[1] = (*(struct city_cell *)((unsigned char *)city_map + ((gmn_sptr) - CITY_ROW + CITY_CELL_BYTES))).terrain & mask;
    if (gmn[1]) { gmn_count++; gmn_nesw_count++; }

    if (gmn_x == 79) { gmn[2] = 1; gmn_density--; }
    else gmn[2] = (*(struct city_cell *)((unsigned char *)city_map + ((gmn_sptr) + CITY_CELL_BYTES))).terrain & mask;
    if (gmn[2]) { gmn_count++; gmn_polar_count++; gmn_ew_count++; gmn_density++; }

    if (gmn_x == 79 || gmn_y == 79) { gmn[3] = 1; gmn_nwse_count--; }
    else gmn[3] = (*(struct city_cell *)((unsigned char *)city_map + ((gmn_sptr) + CITY_ROW + CITY_CELL_BYTES))).terrain & mask;
    if (gmn[3]) { gmn_count++; gmn_nwse_count++; }

    if (gmn_y == 79) { gmn[4] = 1; gmn_density--; }
    else gmn[4] = (*(struct city_cell *)((unsigned char *)city_map + ((gmn_sptr) + CITY_ROW))).terrain & mask;
    if (gmn[4]) { gmn_count++; gmn_polar_count++; gmn_ns_count++; gmn_density++; }

    if (gmn_x == 0 || gmn_y == 79) { gmn[5] = 1; gmn_nesw_count--; }
    else gmn[5] = (*(struct city_cell *)((unsigned char *)city_map + ((gmn_sptr) + CITY_ROW - CITY_CELL_BYTES))).terrain & mask;
    if (gmn[5]) { gmn_count++; gmn_nesw_count++; }

    if (gmn_x == 0) { gmn[6] = 1; gmn_density--; }
    else gmn[6] = (*(struct city_cell *)((unsigned char *)city_map + ((gmn_sptr) - CITY_CELL_BYTES))).terrain & mask;
    if (gmn[6]) { gmn_count++; gmn_polar_count++; gmn_ew_count++; gmn_density++; }

    if (gmn_x == 0 || gmn_y == 0) { gmn[7] = 1; gmn_nwse_count--; }
    else gmn[7] = mask & (*(struct city_cell *)((unsigned char *)city_map + ((gmn_sptr) - CITY_ROW - CITY_CELL_BYTES))).terrain;
    if (gmn[7]) { gmn_count++; gmn_nwse_count++; }

    gmn[8] = gmn[0];
    gmn[9] = gmn[1];
    gmn[10] = gmn[2];
    gmn[11] = gmn[3];
    gmn[12] = gmn[4];
    gmn[13] = gmn[5];
    gmn[14] = gmn[6];
    gmn[15] = gmn[7];
    for (i = 0; i < 16; i++) {
        if (gmn[i]) gmn_run++;
        else gmn_run = 0;
        if (gmn_run > gmn_max_run) gmn_max_run = gmn_run;
    }
}

// FUNCTION: C2 0x6B814
// WIN: 0x004a89f2
// Lines 2831–2876
//
// Sister of test_citymap_neighbours_posedge with the opposite
// off-map convention: cells off the grid count as `0` (negative
// edge: "absent" outside the map).
void test_citymap_neighbours_negedge(char mask)
{
    int i;

    gmn_count = gmn_polar_count = gmn_density = 0;
    gmn_ns_count = gmn_ew_count = gmn_nesw_count = gmn_nwse_count = 0;
    gmn_run = gmn_max_run = 0;

    if (gmn_y == 0) gmn[0] = 0;
    else gmn[0] = (*(struct city_cell *)((unsigned char *)city_map + ((gmn_sptr) - CITY_ROW))).terrain & mask;
    if (gmn[0]) { gmn_count++; gmn_polar_count++; gmn_ns_count++; gmn_density++; }

    if (gmn_y == 0 || gmn_x == 79) gmn[1] = 0;
    else gmn[1] = (*(struct city_cell *)((unsigned char *)city_map + ((gmn_sptr) - CITY_ROW + CITY_CELL_BYTES))).terrain & mask;
    if (gmn[1]) { gmn_count++; gmn_nesw_count++; }

    if (gmn_x == 79) gmn[2] = 0;
    else gmn[2] = (*(struct city_cell *)((unsigned char *)city_map + ((gmn_sptr) + CITY_CELL_BYTES))).terrain & mask;
    if (gmn[2]) { gmn_count++; gmn_polar_count++; gmn_ew_count++; gmn_density++; }

    if (gmn_x == 79 || gmn_y == 79) gmn[3] = 0;
    else gmn[3] = (*(struct city_cell *)((unsigned char *)city_map + ((gmn_sptr) + CITY_ROW + CITY_CELL_BYTES))).terrain & mask;
    if (gmn[3]) { gmn_count++; gmn_nwse_count++; }

    if (gmn_y == 79) gmn[4] = 0;
    else gmn[4] = (*(struct city_cell *)((unsigned char *)city_map + ((gmn_sptr) + CITY_ROW))).terrain & mask;
    if (gmn[4]) { gmn_count++; gmn_polar_count++; gmn_ns_count++; gmn_density++; }

    if (gmn_x == 0 || gmn_y == 79) gmn[5] = 0;
    else gmn[5] = (*(struct city_cell *)((unsigned char *)city_map + ((gmn_sptr) + CITY_ROW - CITY_CELL_BYTES))).terrain & mask;
    if (gmn[5]) { gmn_count++; gmn_nesw_count++; }

    if (gmn_x == 0) gmn[6] = 0;
    else gmn[6] = (*(struct city_cell *)((unsigned char *)city_map + ((gmn_sptr) - CITY_CELL_BYTES))).terrain & mask;
    if (gmn[6]) { gmn_count++; gmn_polar_count++; gmn_ew_count++; gmn_density++; }

    if (gmn_x == 0 || gmn_y == 0) gmn[7] = 0;
    else gmn[7] = mask & (*(struct city_cell *)((unsigned char *)city_map + ((gmn_sptr) - CITY_ROW - CITY_CELL_BYTES))).terrain;
    if (gmn[7]) { gmn_count++; gmn_nwse_count++; }

    gmn[8] = gmn[0];
    gmn[9] = gmn[1];
    gmn[10] = gmn[2];
    gmn[11] = gmn[3];
    gmn[12] = gmn[4];
    gmn[13] = gmn[5];
    gmn[14] = gmn[6];
    gmn[15] = gmn[7];
    for (i = 0; i < 16; i++) {
        if (gmn[i]) gmn_run++;
        else gmn_run = 0;
        if (gmn_run > gmn_max_run) gmn_max_run = gmn_run;
    }
}

// FUNCTION: C2 0x6BB01
// WIN: 0x004a8dde
// Lines 2878–2931
//
// Type-variant: edge sets gmn[i]=0 + decrements counter; non-edge
// computes byte^type (0 = match).  Second pass: if (gmn[i] == 0)
// promote to 1 and increment counters; else gmn[i] = 0.  Net effect
// for edge: gmn[i] ends at 1 and dec/inc cancel out (counter net 0)
// but count++ fires.
void test_type_citymap_neighbours_posedge(unsigned char type)
{
    int i;

    gmn_count = gmn_polar_count = gmn_density = 0;
    gmn_ns_count = gmn_ew_count = gmn_nesw_count = gmn_nwse_count = 0;
    gmn_run = gmn_max_run = 0;

    if (gmn_y == 0) { gmn[0] = 0; gmn_density = -1; }
    else gmn[0] = (*(struct city_cell *)((unsigned char *)city_map + ((gmn_sptr) - CITY_ROW))).base_kind ^ (unsigned char)type;
    if (gmn[0] == 0) { gmn[0] = 1; gmn_count++; gmn_polar_count++; gmn_ns_count++; gmn_density++; }
    else gmn[0] = 0;

    if (gmn_y == 0 || gmn_x == 79) { gmn[1] = 0; gmn_nesw_count--; }
    else gmn[1] = (*(struct city_cell *)((unsigned char *)city_map + ((gmn_sptr) - CITY_ROW + CITY_CELL_BYTES))).base_kind ^ (unsigned char)type;
    if (gmn[1] == 0) { gmn[1] = 1; gmn_count++; gmn_nesw_count++; }
    else gmn[1] = 0;

    if (gmn_x == 79) { gmn[2] = 0; gmn_density--; }
    else gmn[2] = (*(struct city_cell *)((unsigned char *)city_map + ((gmn_sptr) + CITY_CELL_BYTES))).base_kind ^ (unsigned char)type;
    if (gmn[2] == 0) { gmn[2] = 1; gmn_count++; gmn_polar_count++; gmn_ew_count++; gmn_density++; }
    else gmn[2] = 0;

    if (gmn_x == 79 || gmn_y == 79) { gmn[3] = 0; gmn_nwse_count--; }
    else gmn[3] = (*(struct city_cell *)((unsigned char *)city_map + ((gmn_sptr) + CITY_ROW + CITY_CELL_BYTES))).base_kind ^ (unsigned char)type;
    if (gmn[3] == 0) { gmn[3] = 1; gmn_count++; gmn_nwse_count++; }
    else gmn[3] = 0;

    if (gmn_y == 79) { gmn[4] = 0; gmn_density--; }
    else gmn[4] = (*(struct city_cell *)((unsigned char *)city_map + ((gmn_sptr) + CITY_ROW))).base_kind ^ (unsigned char)type;
    if (gmn[4] == 0) { gmn[4] = 1; gmn_count++; gmn_polar_count++; gmn_ns_count++; gmn_density++; }
    else gmn[4] = 0;

    if (gmn_x == 0 || gmn_y == 79) { gmn[5] = 0; gmn_nesw_count--; }
    else gmn[5] = (*(struct city_cell *)((unsigned char *)city_map + ((gmn_sptr) + CITY_ROW - CITY_CELL_BYTES))).base_kind ^ (unsigned char)type;
    if (gmn[5] == 0) { gmn[5] = 1; gmn_count++; gmn_nesw_count++; }
    else gmn[5] = 0;

    if (gmn_x == 0) { gmn[6] = 0; gmn_density--; }
    else gmn[6] = (*(struct city_cell *)((unsigned char *)city_map + ((gmn_sptr) - CITY_CELL_BYTES))).base_kind ^ (unsigned char)type;
    if (gmn[6] == 0) { gmn[6] = 1; gmn_count++; gmn_polar_count++; gmn_ew_count++; gmn_density++; }
    else gmn[6] = 0;

    if (gmn_x == 0 || gmn_y == 0) { gmn[7] = 0; gmn_nwse_count--; }
    else gmn[7] = (unsigned char)type ^ (*(struct city_cell *)((unsigned char *)city_map + ((gmn_sptr) - CITY_ROW - CITY_CELL_BYTES))).base_kind;
    if (gmn[7] == 0) { gmn[7] = 1; gmn_count++; gmn_nwse_count++; }
    else gmn[7] = 0;

    gmn[8] = gmn[0];
    gmn[9] = gmn[1];
    gmn[10] = gmn[2];
    gmn[11] = gmn[3];
    gmn[12] = gmn[4];
    gmn[13] = gmn[5];
    gmn[14] = gmn[6];
    gmn[15] = gmn[7];
    for (i = 0; i < 16; i++) { if (gmn[i]) gmn_run++; else gmn_run = 0; if (gmn_run > gmn_max_run) gmn_max_run = gmn_run; }
}

// FUNCTION: C2 0x6BEB5
// WIN: 0x004a9272
// Lines 2934–2987
//
// Type-variant negedge: edge sets gmn[i]=1 (sentinel that fails the
// match-test below); non-edge computes byte^type.  Second pass
// gates on `gmn[i] == 0`: match → promote to 1 + inc; else →
// gmn[i] = 0.  Edge case ends with gmn[i]=0 and no inc (since
// gmn[i]=1 fails the `==0` test).
void test_type_citymap_neighbours_negedge(unsigned char type)
{
    int i;

    gmn_count = gmn_polar_count = gmn_density = 0;
    gmn_ns_count = gmn_ew_count = gmn_nesw_count = gmn_nwse_count = 0;
    gmn_run = gmn_max_run = 0;

    if (gmn_y == 0) gmn[0] = 1;
    else gmn[0] = (*(struct city_cell *)((unsigned char *)city_map + ((gmn_sptr) - CITY_ROW))).base_kind ^ (unsigned char)type;
    if (gmn[0] == 0) { gmn[0] = 1; gmn_count++; gmn_polar_count++; gmn_ns_count++; gmn_density++; }
    else gmn[0] = 0;

    if (gmn_y == 0 || gmn_x == 79) gmn[1] = 1;
    else gmn[1] = (*(struct city_cell *)((unsigned char *)city_map + ((gmn_sptr) - CITY_ROW + CITY_CELL_BYTES))).base_kind ^ (unsigned char)type;
    if (gmn[1] == 0) { gmn[1] = 1; gmn_count++; gmn_nesw_count++; }
    else gmn[1] = 0;

    if (gmn_x == 79) gmn[2] = 1;
    else gmn[2] = (*(struct city_cell *)((unsigned char *)city_map + ((gmn_sptr) + CITY_CELL_BYTES))).base_kind ^ (unsigned char)type;
    if (gmn[2] == 0) { gmn[2] = 1; gmn_count++; gmn_polar_count++; gmn_ew_count++; gmn_density++; }
    else gmn[2] = 0;

    if (gmn_x == 79 || gmn_y == 79) gmn[3] = 1;
    else gmn[3] = (*(struct city_cell *)((unsigned char *)city_map + ((gmn_sptr) + CITY_ROW + CITY_CELL_BYTES))).base_kind ^ (unsigned char)type;
    if (gmn[3] == 0) { gmn[3] = 1; gmn_count++; gmn_nwse_count++; }
    else gmn[3] = 0;

    if (gmn_y == 79) gmn[4] = 1;
    else gmn[4] = (*(struct city_cell *)((unsigned char *)city_map + ((gmn_sptr) + CITY_ROW))).base_kind ^ (unsigned char)type;
    if (gmn[4] == 0) { gmn[4] = 1; gmn_count++; gmn_polar_count++; gmn_ns_count++; gmn_density++; }
    else gmn[4] = 0;

    if (gmn_x == 0 || gmn_y == 79) gmn[5] = 1;
    else gmn[5] = (*(struct city_cell *)((unsigned char *)city_map + ((gmn_sptr) + CITY_ROW - CITY_CELL_BYTES))).base_kind ^ (unsigned char)type;
    if (gmn[5] == 0) { gmn[5] = 1; gmn_count++; gmn_nesw_count++; }
    else gmn[5] = 0;

    if (gmn_x == 0) gmn[6] = 1;
    else gmn[6] = (*(struct city_cell *)((unsigned char *)city_map + ((gmn_sptr) - CITY_CELL_BYTES))).base_kind ^ (unsigned char)type;
    if (gmn[6] == 0) { gmn[6] = 1; gmn_count++; gmn_polar_count++; gmn_ew_count++; gmn_density++; }
    else gmn[6] = 0;

    if (gmn_x == 0 || gmn_y == 0) gmn[7] = 1;
    else gmn[7] = (unsigned char)type ^ (*(struct city_cell *)((unsigned char *)city_map + ((gmn_sptr) - CITY_ROW - CITY_CELL_BYTES))).base_kind;
    if (gmn[7] == 0) { gmn[7] = 1; gmn_count++; gmn_nwse_count++; }
    else gmn[7] = 0;

    gmn[8] = gmn[0];
    gmn[9] = gmn[1];
    gmn[10] = gmn[2];
    gmn[11] = gmn[3];
    gmn[12] = gmn[4];
    gmn[13] = gmn[5];
    gmn[14] = gmn[6];
    gmn[15] = gmn[7];
    for (i = 0; i < 16; i++) { if (gmn[i]) gmn_run++; else gmn_run = 0; if (gmn_run > gmn_max_run) gmn_max_run = gmn_run; }
}

// FUNCTION: C2 0x6C22E
// WIN: 0x004a96d6
// Lines 2994–3039
//
// Region-map sister of test_citymap_neighbours_posedge on the
// 60x60 region grid.  Off-map cells count as `1`.
void test_regionmap_neighbours_posedge(char mask)
{
    int i;

    gmn_count = gmn_polar_count = gmn_density = 0;
    gmn_ns_count = gmn_ew_count = gmn_nesw_count = gmn_nwse_count = 0;
    gmn_run = gmn_max_run = 0;

    if (gmn_y == 0) { gmn[0] = 1; gmn_density = -1; }
    else gmn[0] = (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr - 480))).terrain & mask;
    if (gmn[0]) { gmn_count++; gmn_polar_count++; gmn_ns_count++; gmn_density++; }

    if (gmn_y == 0 || gmn_x == 59) { gmn[1] = 1; gmn_nesw_count--; }
    else gmn[1] = (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr - 472))).terrain & mask;
    if (gmn[1]) { gmn_count++; gmn_nesw_count++; }

    if (gmn_x == 59) { gmn[2] = 1; gmn_density--; }
    else gmn[2] = (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr + 8))).terrain & mask;
    if (gmn[2]) { gmn_count++; gmn_polar_count++; gmn_ew_count++; gmn_density++; }

    if (gmn_x == 59 || gmn_y == 59) { gmn[3] = 1; gmn_nwse_count--; }
    else gmn[3] = (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr + 488))).terrain & mask;
    if (gmn[3]) { gmn_count++; gmn_nwse_count++; }

    if (gmn_y == 59) { gmn[4] = 1; gmn_density--; }
    else gmn[4] = (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr + 480))).terrain & mask;
    if (gmn[4]) { gmn_count++; gmn_polar_count++; gmn_ns_count++; gmn_density++; }

    if (gmn_x == 0 || gmn_y == 59) { gmn[5] = 1; gmn_nesw_count--; }
    else gmn[5] = (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr + 472))).terrain & mask;
    if (gmn[5]) { gmn_count++; gmn_nesw_count++; }

    if (gmn_x == 0) { gmn[6] = 1; gmn_density--; }
    else gmn[6] = (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr - 8))).terrain & mask;
    if (gmn[6]) { gmn_count++; gmn_polar_count++; gmn_ew_count++; gmn_density++; }

    if (gmn_x == 0 || gmn_y == 0) { gmn[7] = 1; gmn_nwse_count--; }
    else gmn[7] = mask & (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr - 488))).terrain;
    if (gmn[7]) { gmn_count++; gmn_nwse_count++; }

    gmn[8] = gmn[0];
    gmn[9] = gmn[1];
    gmn[10] = gmn[2];
    gmn[11] = gmn[3];
    gmn[12] = gmn[4];
    gmn[13] = gmn[5];
    gmn[14] = gmn[6];
    gmn[15] = gmn[7];
    for (i = 0; i < 16; i++) {
        if (gmn[i]) gmn_run++;
        else gmn_run = 0;
        if (gmn_run > gmn_max_run) gmn_max_run = gmn_run;
    }
}

// FUNCTION: C2 0x6C54F
// WIN: 0x004a9af2
// Lines 3042–3087
//
// Region-map sister of test_citymap_neighbours_negedge on the
// 60x60 region grid.  Off-map cells count as `0`.
void test_regionmap_neighbours_negedge(char mask)
{
    int i;

    gmn_count = gmn_polar_count = gmn_density = 0;
    gmn_ns_count = gmn_ew_count = gmn_nesw_count = gmn_nwse_count = 0;
    gmn_run = gmn_max_run = 0;

    if (gmn_y == 0) gmn[0] = 0;
    else gmn[0] = (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr - 480))).terrain & mask;
    if (gmn[0]) { gmn_count++; gmn_polar_count++; gmn_ns_count++; gmn_density++; }

    if (gmn_y == 0 || gmn_x == 59) gmn[1] = 0;
    else gmn[1] = (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr - 472))).terrain & mask;
    if (gmn[1]) { gmn_count++; gmn_nesw_count++; }

    if (gmn_x == 59) gmn[2] = 0;
    else gmn[2] = (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr + 8))).terrain & mask;
    if (gmn[2]) { gmn_count++; gmn_polar_count++; gmn_ew_count++; gmn_density++; }

    if (gmn_x == 59 || gmn_y == 59) gmn[3] = 0;
    else gmn[3] = (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr + 488))).terrain & mask;
    if (gmn[3]) { gmn_count++; gmn_nwse_count++; }

    if (gmn_y == 59) gmn[4] = 0;
    else gmn[4] = (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr + 480))).terrain & mask;
    if (gmn[4]) { gmn_count++; gmn_polar_count++; gmn_ns_count++; gmn_density++; }

    if (gmn_x == 0 || gmn_y == 59) gmn[5] = 0;
    else gmn[5] = (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr + 472))).terrain & mask;
    if (gmn[5]) { gmn_count++; gmn_nesw_count++; }

    if (gmn_x == 0) gmn[6] = 0;
    else gmn[6] = (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr - 8))).terrain & mask;
    if (gmn[6]) { gmn_count++; gmn_polar_count++; gmn_ew_count++; gmn_density++; }

    if (gmn_x == 0 || gmn_y == 0) gmn[7] = 0;
    else gmn[7] = mask & (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr - 488))).terrain;
    if (gmn[7]) { gmn_count++; gmn_nwse_count++; }

    gmn[8] = gmn[0];
    gmn[9] = gmn[1];
    gmn[10] = gmn[2];
    gmn[11] = gmn[3];
    gmn[12] = gmn[4];
    gmn[13] = gmn[5];
    gmn[14] = gmn[6];
    gmn[15] = gmn[7];
    for (i = 0; i < 16; i++) {
        if (gmn[i]) gmn_run++;
        else gmn_run = 0;
        if (gmn_run > gmn_max_run) gmn_max_run = gmn_run;
    }
}

// FUNCTION: C2 0x6C83C
// WIN: 0x004a9ede
// Lines 3089–3142
//
// Like test_regionmap_neighbours_posedge but matches an EXACT
// base_kind byte against `type` rather than a terrain bitmask
// (XOR + zero-test).  Used by adjusting passes that want "is this
// neighbour the same kind?".  Off-map cells count as 0.
void test_type_regionmap_neighbours_posedge(unsigned char type)
{
    int i;

    gmn_count = gmn_polar_count = gmn_density = 0;
    gmn_ns_count = gmn_ew_count = gmn_nesw_count = gmn_nwse_count = 0;
    gmn_run = gmn_max_run = 0;

    if (gmn_y == 0) { gmn[0] = 0; gmn_density = -1; }
    else gmn[0] = (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr - 480))).base_kind ^ (unsigned char)type;
    if (gmn[0] == 0) { gmn[0] = 1; gmn_count++; gmn_polar_count++; gmn_ns_count++; gmn_density++; }
    else gmn[0] = 0;

    if (gmn_y == 0 || gmn_x == 59) { gmn[1] = 0; gmn_nesw_count--; }
    else gmn[1] = (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr - 472))).base_kind ^ (unsigned char)type;
    if (gmn[1] == 0) { gmn[1] = 1; gmn_count++; gmn_nesw_count++; }
    else gmn[1] = 0;

    if (gmn_x == 59) { gmn[2] = 0; gmn_density--; }
    else gmn[2] = (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr + 8))).base_kind ^ (unsigned char)type;
    if (gmn[2] == 0) { gmn[2] = 1; gmn_count++; gmn_polar_count++; gmn_ew_count++; gmn_density++; }
    else gmn[2] = 0;

    if (gmn_x == 59 || gmn_y == 59) { gmn[3] = 0; gmn_nwse_count--; }
    else gmn[3] = (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr + 488))).base_kind ^ (unsigned char)type;
    if (gmn[3] == 0) { gmn[3] = 1; gmn_count++; gmn_nwse_count++; }
    else gmn[3] = 0;

    if (gmn_y == 59) { gmn[4] = 0; gmn_density--; }
    else gmn[4] = (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr + 480))).base_kind ^ (unsigned char)type;
    if (gmn[4] == 0) { gmn[4] = 1; gmn_count++; gmn_polar_count++; gmn_ns_count++; gmn_density++; }
    else gmn[4] = 0;

    if (gmn_x == 0 || gmn_y == 59) { gmn[5] = 0; gmn_nesw_count--; }
    else gmn[5] = (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr + 472))).base_kind ^ (unsigned char)type;
    if (gmn[5] == 0) { gmn[5] = 1; gmn_count++; gmn_nesw_count++; }
    else gmn[5] = 0;

    if (gmn_x == 0) { gmn[6] = 0; gmn_density--; }
    else gmn[6] = (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr - 8))).base_kind ^ (unsigned char)type;
    if (gmn[6] == 0) { gmn[6] = 1; gmn_count++; gmn_polar_count++; gmn_ew_count++; gmn_density++; }
    else gmn[6] = 0;

    if (gmn_x == 0 || gmn_y == 0) { gmn[7] = 0; gmn_nwse_count--; }
    else gmn[7] = (unsigned char)type ^ (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr - 488))).base_kind;
    if (gmn[7] == 0) { gmn[7] = 1; gmn_count++; gmn_nwse_count++; }
    else gmn[7] = 0;

    gmn[8] = gmn[0];
    gmn[9] = gmn[1];
    gmn[10] = gmn[2];
    gmn[11] = gmn[3];
    gmn[12] = gmn[4];
    gmn[13] = gmn[5];
    gmn[14] = gmn[6];
    gmn[15] = gmn[7];
    for (i = 0; i < 16; i++) { if (gmn[i]) gmn_run++; else gmn_run = 0; if (gmn_run > gmn_max_run) gmn_max_run = gmn_run; }
}

// FUNCTION: C2 0x6CBF0
// WIN: 0x004aa372
// Lines 3145–3198
//
// Sister of test_type_regionmap_neighbours_posedge: off-map cells
// count as `1` (treated as "matching").
void test_type_regionmap_neighbours_negedge(unsigned char type)
{
    int i;

    gmn_count = gmn_polar_count = gmn_density = 0;
    gmn_ns_count = gmn_ew_count = gmn_nesw_count = gmn_nwse_count = 0;
    gmn_run = gmn_max_run = 0;

    if (gmn_y == 0) gmn[0] = 1;
    else gmn[0] = (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr - 480))).base_kind ^ (unsigned char)type;
    if (gmn[0] == 0) { gmn[0] = 1; gmn_count++; gmn_polar_count++; gmn_ns_count++; gmn_density++; }
    else gmn[0] = 0;

    if (gmn_y == 0 || gmn_x == 59) gmn[1] = 1;
    else gmn[1] = (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr - 472))).base_kind ^ (unsigned char)type;
    if (gmn[1] == 0) { gmn[1] = 1; gmn_count++; gmn_nesw_count++; }
    else gmn[1] = 0;

    if (gmn_x == 59) gmn[2] = 1;
    else gmn[2] = (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr + 8))).base_kind ^ (unsigned char)type;
    if (gmn[2] == 0) { gmn[2] = 1; gmn_count++; gmn_polar_count++; gmn_ew_count++; gmn_density++; }
    else gmn[2] = 0;

    if (gmn_x == 59 || gmn_y == 59) gmn[3] = 1;
    else gmn[3] = (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr + 488))).base_kind ^ (unsigned char)type;
    if (gmn[3] == 0) { gmn[3] = 1; gmn_count++; gmn_nwse_count++; }
    else gmn[3] = 0;

    if (gmn_y == 59) gmn[4] = 1;
    else gmn[4] = (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr + 480))).base_kind ^ (unsigned char)type;
    if (gmn[4] == 0) { gmn[4] = 1; gmn_count++; gmn_polar_count++; gmn_ns_count++; gmn_density++; }
    else gmn[4] = 0;

    if (gmn_x == 0 || gmn_y == 59) gmn[5] = 1;
    else gmn[5] = (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr + 472))).base_kind ^ (unsigned char)type;
    if (gmn[5] == 0) { gmn[5] = 1; gmn_count++; gmn_nesw_count++; }
    else gmn[5] = 0;

    if (gmn_x == 0) gmn[6] = 1;
    else gmn[6] = (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr - 8))).base_kind ^ (unsigned char)type;
    if (gmn[6] == 0) { gmn[6] = 1; gmn_count++; gmn_polar_count++; gmn_ew_count++; gmn_density++; }
    else gmn[6] = 0;

    if (gmn_x == 0 || gmn_y == 0) gmn[7] = 1;
    else gmn[7] = (unsigned char)type ^ (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr - 488))).base_kind;
    if (gmn[7] == 0) { gmn[7] = 1; gmn_count++; gmn_nwse_count++; }
    else gmn[7] = 0;

    gmn[8] = gmn[0];
    gmn[9] = gmn[1];
    gmn[10] = gmn[2];
    gmn[11] = gmn[3];
    gmn[12] = gmn[4];
    gmn[13] = gmn[5];
    gmn[14] = gmn[6];
    gmn[15] = gmn[7];
    for (i = 0; i < 16; i++) { if (gmn[i]) gmn_run++; else gmn_run = 0; if (gmn_run > gmn_max_run) gmn_max_run = gmn_run; }
}

// FUNCTION: C2 0x6CF69
// WIN: 0x004aa7d6
// Lines 3204–3227
//
// Walk `records` (8-slot match arrays + value + counter) and find
// the first record whose 8 match bits agree with the global gmn[]
// (skip-2 slots are wildcards, 1 needs gmn[i] != 0, 0 needs gmn[i]
// == 0).  On a hit, publish first_choice / choice_info /
// choice_count and return the 1-based record index; 0 on no match.
int choose_from(struct choice_rec *records, int count)
{
    int rec_idx;
    int byte_idx;
    for (rec_idx = 0; rec_idx < count; records++, rec_idx++) {
        for (byte_idx = 0; byte_idx < 8; byte_idx++) {
            if (records->match[byte_idx] == 2) continue;
            if (records->match[byte_idx] != 0 && gmn[byte_idx] != 0) continue;
            if (records->match[byte_idx] != 0) break;
            if (gmn[byte_idx] != 0) break;
        }
        if (byte_idx >= 8) {
            first_choice = records->value;
            choice_info  = records->info;
            records->counter++;
            if (records->counter >= records->max_count) {
                records->counter = 0;
            }
            choice_count = records->counter;
            return rec_idx + 1;
        }
    }
    return 0;
}

// FUNCTION: C2 0x6CFED
// WIN: 0x004aa8fd
// Lines 3229–3233
//
// Clear the "selected" byte (offset 11) of every entry in a
// 12-byte-strided choice array.  Used to reset selection
// state on UI panels with a chooser list.
void init_choices(struct choice_rec *arr, int count)
{
    int i;
    for (i = 0; i < count; i++, arr++)
        arr->counter = 0;
}

// FUNCTION: C2 0x6D002
// Lines 3236–3240
//
// Toggle every byte in gmn[0..16): 0 ↔ 1.
void invert_gmn(void)
{
    int i;
    for (i = 0; i < 16; i++) {
        gmn[i] = (gmn[i] == 0);
    }
}

// FUNCTION: C2 0x6D01E
// WIN: 0x004aaa92
// Lines 3261–3277
//
// Region-map sibling of ``clear_all_cm``.  Region cells are
// 8 bytes each and the grid is 60×60.  Each inner iteration
// clears 10 adjacent cells' ``layer``-th byte (the offset is
// passed as the 8-bit ``al``/``dl`` parameter, zero-extended
// to int before adding to ``cm_sptr``).  Outer ``gmn_y`` runs
// 0..59, inner ``gmn_x`` runs 0..5 (× 10 unroll = 60 cells per
// row), with ``cm_sptr`` advancing by 80 bytes per inner step.
//
void clear_all_rm(char layer)
{
    cm_sptr = 0;
    for (gmn_y = 0; gmn_y < 60; gmn_y++) {
        for (gmn_x = 0; gmn_x < 6; gmn_x++, cm_sptr += 0x50) {
            int idx = cm_sptr + (unsigned char)layer;
            ((unsigned char *)region_map)[(idx + 0x00)] = 0;
            ((unsigned char *)region_map)[(idx + 0x08)] = 0;
            ((unsigned char *)region_map)[(idx + 0x10)] = 0;
            ((unsigned char *)region_map)[(idx + 0x18)] = 0;
            ((unsigned char *)region_map)[(idx + 0x20)] = 0;
            ((unsigned char *)region_map)[(idx + 0x28)] = 0;
            ((unsigned char *)region_map)[(idx + 0x30)] = 0;
            ((unsigned char *)region_map)[(idx + 0x38)] = 0;
            ((unsigned char *)region_map)[(idx + 0x40)] = 0;
            ((unsigned char *)region_map)[(idx + 0x48)] = 0;
        }
    }
}

// FUNCTION: C2 0x6D0B7
// WIN: 0x004aabba
// Lines 3280–3290
//
// Battle-map sister of clear_all_cm: zero the byte at offset
// `layer` inside every cell of the 52×52 battle_map (cell
// stride 4 bytes, not 20).  4 byte-stores per inner iter × 13
// inner iters × 52 outer iters = 2704 cells = full battle_map.
// Globals cm_sptr / gmn_x / gmn_y are clobbered as side
// effects (same as clear_all_cm).
//
void clear_all_bm(char layer)
{
    cm_sptr = 0;
    for (gmn_y = 0; gmn_y < 52; gmn_y++) {
        for (gmn_x = 0; gmn_x < 13; gmn_x++, cm_sptr += 0x10) {
            int idx = cm_sptr + (unsigned char)layer;
            (*(struct battle_cell *)((unsigned char *)battle_map + (idx))).terrain = 0;
            (*(struct battle_cell *)((unsigned char *)battle_map + (idx + 0x4))).terrain = 0;
            (*(struct battle_cell *)((unsigned char *)battle_map + (idx + 0x8))).terrain = 0;
            (*(struct battle_cell *)((unsigned char *)battle_map + (idx + 0xc))).terrain = 0;
        }
    }
}

// FUNCTION: C2 0x6D12C
// WIN: 0x004aac70
// Lines 3293–3308
//
// Walk the entire 80×80 city map and AND `mask` into a single
// byte field (at byte-offset `field_off` within each cell).
// Used to clear flag bits across the whole map (e.g. "recompute
// land value" passes).  Inner loop is unrolled 8 cells wide.
//
// Globals cm_sptr / gmn_x / gmn_y serve as the loop counters.
void unflag_all_cm(char field_off, int mask)
{
    cm_sptr = 0;
    gmn_y = 0;
    do {
        gmn_x = 0;
        do {
            ((unsigned char *)city_map)[cm_sptr + field_off + 0x00] &= mask;
            ((unsigned char *)city_map)[cm_sptr + field_off + 0x14] &= mask;
            ((unsigned char *)city_map)[cm_sptr + field_off + 0x28] &= mask;
            ((unsigned char *)city_map)[cm_sptr + field_off + 0x3c] &= mask;
            ((unsigned char *)city_map)[cm_sptr + field_off + 0x50] &= mask;
            ((unsigned char *)city_map)[cm_sptr + field_off + 0x64] &= mask;
            ((unsigned char *)city_map)[cm_sptr + field_off + 0x78] &= mask;
            ((unsigned char *)city_map)[cm_sptr + field_off + 0x8c] &= mask;
            gmn_x++;
            cm_sptr += 0xa0;
        } while (gmn_x < 10);
        gmn_y++;
    } while (gmn_y < 80);
}

// FUNCTION: C2 0x6D1B7
// WIN: 0x004aae45
// Lines 3310–3327
//
// Sister of \`unflag_all_cm\` for the 60×60 region map.
// Cells are 8 bytes wide; inner loop unrolled 10 cells
// wide (gmn_x < 6 × 10 = 60 cells per row).
void unflag_all_rm(char field_off, int mask)
{
    cm_sptr = 0;
    gmn_y = 0;
    do {
        gmn_x = 0;
        do {
            ((unsigned char *)region_map)[(cm_sptr + field_off + 0x00)] &= (char)mask;
            ((unsigned char *)region_map)[(cm_sptr + field_off + 0x08)] &= (char)mask;
            ((unsigned char *)region_map)[(cm_sptr + field_off + 0x10)] &= (char)mask;
            ((unsigned char *)region_map)[(cm_sptr + field_off + 0x18)] &= (char)mask;
            ((unsigned char *)region_map)[(cm_sptr + field_off + 0x20)] &= (char)mask;
            ((unsigned char *)region_map)[(cm_sptr + field_off + 0x28)] &= (char)mask;
            ((unsigned char *)region_map)[(cm_sptr + field_off + 0x30)] &= (char)mask;
            ((unsigned char *)region_map)[(cm_sptr + field_off + 0x38)] &= (char)mask;
            ((unsigned char *)region_map)[(cm_sptr + field_off + 0x40)] &= (char)mask;
            ((unsigned char *)region_map)[(cm_sptr + field_off + 0x48)] &= (char)mask;
            gmn_x++;
            cm_sptr += 0x50;
        } while (gmn_x < 6);
        gmn_y++;
    } while (gmn_y < 60);
}

// FUNCTION: C2 0x6D24B
// WIN: 0x004ab0be
// Lines 3329–3344
//
// 60×60 region-map sweep that strips the upper 2 bits of the
// `+3` flags byte on every cell whose `+0` rm_byte is *not*
// 0xd4 (warehouse marker).  Inner loop unrolled 4 cells wide
// (gmn_x < 15 × 4 = 60 cells per row).
void unflag_all_rm_xwarehouse(void)
{
    cm_sptr = 0;
    gmn_y = 0;
    do {
        gmn_x = 0;
        do {
            if ((*(struct region_cell *)((unsigned char *)region_map + (cm_sptr))).base_kind != 0xd4)
                (*(struct region_cell *)((unsigned char *)region_map + (cm_sptr))).edge_bits &= 0x3f;
            if ((*(struct region_cell *)((unsigned char *)region_map + (cm_sptr + 8))).base_kind != 0xd4)
                (*(struct region_cell *)((unsigned char *)region_map + (cm_sptr + 8))).edge_bits &= 0x3f;
            if ((*(struct region_cell *)((unsigned char *)region_map + (cm_sptr + 16))).base_kind != 0xd4)
                (*(struct region_cell *)((unsigned char *)region_map + (cm_sptr + 16))).edge_bits &= 0x3f;
            if ((*(struct region_cell *)((unsigned char *)region_map + (cm_sptr + 24))).base_kind != 0xd4)
                (*(struct region_cell *)((unsigned char *)region_map + (cm_sptr + 24))).edge_bits &= 0x3f;
            gmn_x++;
            cm_sptr += 0x20;
        } while (gmn_x < 15);
        gmn_y++;
    } while (gmn_y < 60);
}

// FUNCTION: C2 0x6D309
// WIN: 0x004ab1f8
// Lines 3348–3367
//
// Fill a clipped city-map square centered at (x,y), writing `value` to
// byte field `field_off` for every covered cell.  The side length is
// 2*range+1.
void set_range(int x, int y, int range, unsigned char field_off, unsigned char value)
{
    int width;
    int height;
    int xend;
    int yend;
    int row_skip;

    x -= range;
    y -= range;
    width = height = range * 2 + 1;

    xend = width + x;
    if (x < 0) {
        width = xend;
        x = 0;
    } else if (xend > 80) {
        width -= xend - 80;
    }
    yend = height + y;
    if (y < 0) {
        height = yend;
        y = 0;
    } else if (yend > 80) {
        height -= yend - 80;
    }

    gmn_sptr = ((x) + (y) * 80) * 20;
    row_skip  = (80 - width) * 20;
    for (gmn_y = y; gmn_y < y + height; gmn_y++, gmn_sptr += row_skip) {
        for (gmn_x = x; gmn_x < x + width; gmn_x++, gmn_sptr += 20) {
            ((unsigned char *)city_map)[gmn_sptr + field_off] = value;
        }
    }
}

// FUNCTION: C2 0x6D3ED
// WIN: 0x004ab344
// Lines 3370–3390
//
// Region-map sister of set_range.  Writes ``kind_byte`` to byte
// offset ``field_offset`` within every region_map cell of a
// (2*half_width+1)×(2*half_width+1) square centred on (x, y),
// clamped to the 60×60 region grid.
//
// Parameters (4 register args + 1 stack):
//   eax = x  (centre column)
//   edx = y  (centre row)
//   ebx = half_width  (half-extent of the square; full diameter
//                       is 2*half_width + 1)
//   ecx = field_offset (byte index inside an 8-byte rmcell)
//   stack[+0] = kind_byte (low byte stored at every visited cell)
//
// Side-effects: gmn_x, gmn_y, gmn_sptr are left pointing at the
// end-of-rectangle position so callers (e.g. get_reg_road_elastic)
// can pick up from there.
void set_rm_range(int x, int y, int half_width, char field_offset,
                  char kind_byte)
{
    int width;
    int height;
    int row_skip;

    x -= half_width;
    y -= half_width;
    height = 2 * half_width + 1;
    width = height;

    if (x < 0) {
        width = x + height;
        x = 0;
    } else if (x + height > 60) {
        width -= (x + height - 60);
    }

    if (y < 0) {
        height = y + height;
        y = 0;
    } else if (y + height > 60) {
        height -= (y + height - 60);
    }

    gmn_sptr = ((x) + (y) * 60) * 8;
    row_skip = (60 - width) * 8;

    for (gmn_y = y; gmn_y < y + height; gmn_y++, gmn_sptr += row_skip) {
        for (gmn_x = x; gmn_x < x + width; gmn_x++, gmn_sptr += 8) {
            ((unsigned char *)region_map)[(gmn_sptr + field_offset)] = kind_byte;
        }
    }
}

// FUNCTION: C2 0x6D4C1
// WIN: 0x004ab48d
// Lines 3392–3416
//
// OR `mask` into (*(struct city_cell *)((unsigned char *)city_map + (field_off))).base_kind for the square centered on (x,y)
// with radius `range`, optionally extending the side length by `extra`.
// Publishes gmn_x/gmn_y/gmn_sptr while scanning, matching the shared
// range-walker convention used by neighbouring helpers.
//
void flag_range(int extra, int x, int y, int range, unsigned char field_off, unsigned char mask)
{
    int width;
    int height;
    int xend;
    int yend;
    int row_stride;
    unsigned char fo;

    fo = field_off;
    x -= range;
    y -= range;
    width = height = 2 * range + 1;
    if (extra != 0)
        height = width = height + extra;

    xend = width + x;
    if (x < 0) {
        width = xend;
        x = 0;
    } else if (xend > 80) {
        width -= xend - 80;
    }
    yend = height + y;
    if (y < 0) {
        height = yend;
        y = 0;
    } else if (yend > 80) {
        height -= yend - 80;
    }

    gmn_sptr   = ((x) + (y) * 80) * 20;
    row_stride = (80 - width) * 20;
    for (gmn_y = y; gmn_y < y + height; gmn_y++, gmn_sptr += row_stride) {
        for (gmn_x = x; gmn_x < x + width; gmn_x++, gmn_sptr += 20) {
            ((unsigned char *)city_map)[gmn_sptr + fo] |= mask;
        }
    }
}

// FUNCTION: C2 0x6D5AA
// WIN: 0x004ab603
// Lines 3418–3450
//
// Stamp a (2*range+1)+extra-side square of city_map cells'
// entertainment byte (+0x0C) with `threshold` if the cell's
// current value, masked by `query_mask`, falls strictly below
// `threshold`.  When stored, the existing byte is first masked
// by `clear_mask` (clearing the bits the new value will own)
// and OR'd with `threshold`.
//
// Each step of the inner loop publishes the running cell
// pointer in globals ``gmn_sptr / gmn_x / gmn_y`` so callees
// (none here, but the convention is shared with flag_range)
// can read the current cell.
//
// The 5th arg is dead — every caller passes 0xC and the body
// hard-codes the entertainment field offset.  PS most likely
// took a `field_offset` param historically and inlined the
// constant after a refactor; we keep the slot to match the
// 4-stack-arg ABI (callee ``ret 0x10`` pops 16 bytes).
//
// Stamping threshold/query_mask/clear_mask are unsigned char (PS's
// inner compare is a byte-level unsigned `cmp dh,dl; jbe`).
void flag_range3(int extra, int x, int y, int range, int unused_field_off,
                 unsigned char threshold, unsigned char query_mask,
                 unsigned char clear_mask)
{
    int height;
    int width;
    int row_stride;
    int xend;
    int yend;

    (void)unused_field_off;

    x -= range;
    y -= range;
    width = height = 2 * range + 1;
    if (extra != 0) {
        width = height = (2 * range + 1) + extra;
    }

    xend = width + x;
    if (x < 0) {
        width = xend;
        x = 0;
    } else if (xend > 80) {
        width -= xend - 80;
    }

    yend = height + y;
    if (y < 0) {
        height = yend;
        y = 0;
    } else if (yend > 80) {
        height -= yend - 80;
    }

    gmn_sptr   = (x + y * 80) * 20;
    row_stride = (80 - width) * 20;

    for (gmn_y = y; gmn_y < y + height; gmn_y++, gmn_sptr += row_stride) {
        for (gmn_x = x; gmn_x < x + width; gmn_x++, gmn_sptr += 20) {
            if (threshold > (unsigned char)((*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).entertainment & query_mask)) {
                (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).entertainment &= clear_mask;
                (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).entertainment |= threshold;
            }
        }
    }
}

// FUNCTION: C2 0x6D6B5
// WIN: 0x004ab7b3
// Lines 3453–3459
//
// Set a byte field (`field_off`) on all four city-map neighbours that
// exist around (x,y).  `sptr` is the current cell byte offset.
void set_4_neighbours(int x, int y, int sptr, unsigned char field_off, unsigned char value)
{
    if (x > 0)  ((unsigned char *)city_map)[sptr - 20 + field_off] = value;
    if (x < 79) ((unsigned char *)city_map)[sptr + 20 + field_off] = value;
    if (y > 0)  ((unsigned char *)city_map)[sptr - 1600 + field_off] = value;
    if (y < 79) ((unsigned char *)city_map)[sptr + 1600 + field_off] = value;
}

// FUNCTION: C2 0x6D6FB
// WIN: 0x004ab82e
// Lines 3460–3474
//
// Same as set_4_neighbours, but do not overwrite neighbours whose
// terrain byte has wall/tower bits (0x06) set.
void set_4_neighbours_if_not_wallortower(int x, int y, int sptr,
                                         unsigned char field_off, unsigned char value)
{
    if (x > 0 && (((*(struct city_cell *)((unsigned char *)city_map + ((sptr) - CITY_CELL_BYTES))).terrain & 6) == 0))
        ((unsigned char *)city_map)[sptr - 20 + field_off] = value;
    if (x < 79 && (((*(struct city_cell *)((unsigned char *)city_map + ((sptr) + CITY_CELL_BYTES))).terrain & 6) == 0))
        ((unsigned char *)city_map)[sptr + 20 + field_off] = value;
    if (y > 0 && (((*(struct city_cell *)((unsigned char *)city_map + ((sptr) - CITY_ROW))).terrain & 6) == 0))
        ((unsigned char *)city_map)[sptr - 1600 + field_off] = value;
    if (y < 79 && (((*(struct city_cell *)((unsigned char *)city_map + ((sptr) + CITY_ROW))).terrain & 6) == 0))
        ((unsigned char *)city_map)[sptr + 1600 + field_off] = value;
}

// FUNCTION: C2 0x6D785
// WIN: 0x004ab8f9
// Lines 3476–3496
//
// Set either east/west (`north_south == 0`) or north/south neighbours,
// skipping wall/tower cells.
void set_2_neighbours_if_not_wallortower(int x, int y, int sptr,
                                         unsigned char field_off, unsigned char value,
                                         int north_south)
{
    if (north_south == 0) {
        if (x > 0 && (((*(struct city_cell *)((unsigned char *)city_map + ((sptr) - CITY_CELL_BYTES))).terrain & 6) == 0))
            ((unsigned char *)city_map)[sptr - 20 + field_off] = value;
        if (x < 79 && (((*(struct city_cell *)((unsigned char *)city_map + ((sptr) + CITY_CELL_BYTES))).terrain & 6) == 0))
            ((unsigned char *)city_map)[sptr + 20 + field_off] = value;
    } else {
        if (y > 0 && (((*(struct city_cell *)((unsigned char *)city_map + ((sptr) - CITY_ROW))).terrain & 6) == 0))
            ((unsigned char *)city_map)[sptr - 1600 + field_off] = value;
        if (y < 79 && (((*(struct city_cell *)((unsigned char *)city_map + ((sptr) + CITY_ROW))).terrain & 6) == 0))
            ((unsigned char *)city_map)[sptr + 1600 + field_off] = value;
    }
}

// FUNCTION: C2 0x6D80A
// WIN: 0x004ab9d3
// Lines 3498–3512
//
// Stamp `value` at byte field_off on every cardinal neighbour
// (city_map) whose terrain bits 0x40 / 0x80 (aquaduct / reservoir)
// are clear.
void set_4_neighbours_if_not_aquaductorresevoir(int x, int y, int sptr,
                                                unsigned char field_off, unsigned char value)
{
    if (x > 0 && (((*(struct city_cell *)((unsigned char *)city_map + ((sptr) - CITY_CELL_BYTES))).terrain & 0xc0) == 0))
        ((unsigned char *)city_map)[sptr - 20 + field_off] = value;
    if (x < 79 && (((*(struct city_cell *)((unsigned char *)city_map + ((sptr) + CITY_CELL_BYTES))).terrain & 0xc0) == 0))
        ((unsigned char *)city_map)[sptr + 20 + field_off] = value;
    if (y > 0 && (((*(struct city_cell *)((unsigned char *)city_map + ((sptr) - CITY_ROW))).terrain & 0xc0) == 0))
        ((unsigned char *)city_map)[sptr - 1600 + field_off] = value;
    if (y < 79 && (((*(struct city_cell *)((unsigned char *)city_map + ((sptr) + CITY_ROW))).terrain & 0xc0) == 0))
        ((unsigned char *)city_map)[sptr + 1600 + field_off] = value;
}

// FUNCTION: C2 0x6D894
// WIN: 0x004aba9e
// Lines 3514–3534
//
// Half-sister of set_4_neighbours_if_not_aquaductorresevoir: stamps
// only the E/W pair when north_south == 0, only the N/S pair when
// north_south != 0.
void set_2_neighbours_if_not_aquaductorresevoir(int x, int y, int sptr,
                                                unsigned char field_off, unsigned char value,
                                                int north_south)
{
    if (north_south == 0) {
        if (x > 0 && ((*(struct city_cell *)((unsigned char *)city_map + ((sptr) - CITY_CELL_BYTES))).terrain & 0xc0) == 0)
            ((unsigned char *)city_map)[sptr - 20 + field_off] = value;
        if (x < 79 && ((*(struct city_cell *)((unsigned char *)city_map + ((sptr) + CITY_CELL_BYTES))).terrain & 0xc0) == 0)
            ((unsigned char *)city_map)[sptr + 20 + field_off] = value;
    } else {
        if (y > 0 && ((*(struct city_cell *)((unsigned char *)city_map + ((sptr) - CITY_ROW))).terrain & 0xc0) == 0)
            ((unsigned char *)city_map)[sptr - 1600 + field_off] = value;
        if (y < 79 && ((*(struct city_cell *)((unsigned char *)city_map + ((sptr) + CITY_ROW))).terrain & 0xc0) == 0)
            ((unsigned char *)city_map)[sptr + 1600 + field_off] = value;
    }
}

// FUNCTION: C2 0x6D919
// WIN: 0x004abb78
// Lines 3536–3550
//
// Region-map sister of set_4_neighbours: stamps `value` at field_off
// on every cardinal region-map neighbour whose terrain bits 0x02 /
// 0x04 (wall / tower) are clear.
void set_4_rm_neighbours_if_not_wallortower(int x, int y, int sptr,
                                            unsigned char field_off, unsigned char value)
{
    if (x > 0 && (((*(struct region_cell *)((unsigned char *)region_map + (sptr - 8))).terrain & 6) == 0))
        ((unsigned char *)region_map)[(sptr - 8 + field_off)] = (unsigned char)value;
    if (x < 59 && (((*(struct region_cell *)((unsigned char *)region_map + (sptr + 8))).terrain & 6) == 0))
        ((unsigned char *)region_map)[(sptr + 8 + field_off)] = (unsigned char)value;
    if (y > 0 && (((*(struct region_cell *)((unsigned char *)region_map + (sptr - 480))).terrain & 6) == 0))
        ((unsigned char *)region_map)[(sptr - 480 + field_off)] = (unsigned char)value;
    if (y < 59 && (((*(struct region_cell *)((unsigned char *)region_map + (sptr + 480))).terrain & 6) == 0))
        ((unsigned char *)region_map)[(sptr + 480 + field_off)] = (unsigned char)value;
}

// FUNCTION: C2 0x6D9A3
// WIN: 0x004abc43
// Lines 3551–3565
//
// Sister of set_4_rm_neighbours_if_not_wallortower with a different
// mask (0x40 = aquaduct/reservoir bit).
void set_4_rm_neighbours_if_not_aquaductorresevoir(int x, int y, int sptr,
                                                   unsigned char field_off, unsigned char value)
{
    if (x > 0 && ((*(struct region_cell *)((unsigned char *)region_map + (sptr - 8))).terrain & 0x40) == 0)
        ((unsigned char *)region_map)[(sptr - 8 + field_off)] = value;
    if (x < 59 && ((*(struct region_cell *)((unsigned char *)region_map + (sptr + 8))).terrain & 0x40) == 0)
        ((unsigned char *)region_map)[(sptr + 8 + field_off)] = value;
    if (y > 0 && ((*(struct region_cell *)((unsigned char *)region_map + (sptr - 480))).terrain & 0x40) == 0)
        ((unsigned char *)region_map)[(sptr - 480 + field_off)] = value;
    if (y < 59 && ((*(struct region_cell *)((unsigned char *)region_map + (sptr + 480))).terrain & 0x40) == 0)
        ((unsigned char *)region_map)[(sptr + 480 + field_off)] = value;
}

// FUNCTION: C2 0x6DA2D
// WIN: 0x004abd0e
// Lines 3566–3580
//
// Increment the "elastic" field (byte +2 of city_cell) by 2 at
// each of the 4 cardinal neighbours of cell (x, y) at byte-
// offset `sptr`.  Saturates at 0xff: a neighbour cell whose
// elastic value is already 0xff is left untouched.  Skips any
// neighbour that would fall off the 80×80 grid (x==0 left
// edge, x==79 right edge, etc.).
//
// Used by transform_*_elastic() to spread elasticity to the
// neighbours of a cell that just received a wall/aqueduct.
//
// Note: source uses the natural `if (m != 0xff) m += 2;`
// idiom (no temp variable).  Watcom compiles this to the
// in-place RMW: `xor reg, reg; mov reg_lo, [m]; cmp; je
// skip; add reg_lo, 2; mov [m], reg_lo`.  Hoisting the read
// to a local (`int v = ...; if (v != 0xff) [m] = v + 2;`)
// triggers stack spilling instead.
void inc_elastic_by2(int x, int y, int sptr)
{
    if (x > 0) {
        if ((*(struct city_cell *)((unsigned char *)city_map + ((sptr) - CITY_CELL_BYTES))).road_aqueduct != 0xff)
            (*(struct city_cell *)((unsigned char *)city_map + ((sptr) - CITY_CELL_BYTES))).road_aqueduct += 2;
    }
    if (x < 79) {
        if ((*(struct city_cell *)((unsigned char *)city_map + ((sptr) + CITY_CELL_BYTES))).road_aqueduct != 0xff)
            (*(struct city_cell *)((unsigned char *)city_map + ((sptr) + CITY_CELL_BYTES))).road_aqueduct += 2;
    }
    if (y > 0) {
        if ((*(struct city_cell *)((unsigned char *)city_map + ((sptr) - CITY_ROW))).road_aqueduct != 0xff)
            (*(struct city_cell *)((unsigned char *)city_map + ((sptr) - CITY_ROW))).road_aqueduct += 2;
    }
    if (y < 79) {
        if ((*(struct city_cell *)((unsigned char *)city_map + ((sptr) + CITY_ROW))).road_aqueduct != 0xff)
            (*(struct city_cell *)((unsigned char *)city_map + ((sptr) + CITY_ROW))).road_aqueduct += 2;
    }
}

// FUNCTION: C2 0x6DAA6
// WIN: 0x004abdf9
// Lines 3582–3591
//
// Probe whether the cell at (sptr, y) on city_map has a
// city wall (mask byte bit 0x02) or wall-foot (bit 0x04)
// neighbour to the north or south.  Returns 1 if so, else 0.
/* PS signature: y in EDX, sptr in EBX (no EAX param).
 * Inferred-sig: (edx, ebx).  Dummy EAX param matches PS calling
 * convention and direct city_map[sptr+...] indexing (no cm cache)
 * triggers fold-base-into-disp. */
int test_for_ns_polar_walls(int _eax_unused, int y, int sptr)
{
    (void)_eax_unused;
    if (y > 0     && ((*(struct city_cell *)((unsigned char *)city_map + ((sptr) - CITY_ROW))).terrain & 0x06)) return 1;
    if (y < 0x4f  && ((*(struct city_cell *)((unsigned char *)city_map + ((sptr) + CITY_ROW))).terrain & 0x06)) return 1;
    return 0;
}

// FUNCTION: C2 0x6DAD6
// WIN: 0x004abe5b
// Lines 3592–3601
//
// Probe whether the cell at (sptr, x) on city_map has a
// city wall (mask byte bit 0x02) or wall-foot (bit 0x04)
// neighbour to the east or west.  Returns 1 if so, else 0.
/* PS signature: sptr is passed in EBX (3rd watcall reg), with an
 * unused EDX slot.  Inferred-sig: (eax, ebx).  Adding the dummy
 * `int _edx_unused` parameter matches the PS calling convention so
 * sptr lands directly in EBX without an extra cache move. */
int test_for_ew_polar_walls(int x, int _edx_unused, int sptr)
{
    (void)_edx_unused;
    if (x > 0     && ((*(struct city_cell *)((unsigned char *)city_map + ((sptr) - CITY_CELL_BYTES))).terrain & 0x06)) return 1;
    if (x < 0x4f  && ((*(struct city_cell *)((unsigned char *)city_map + ((sptr) + CITY_CELL_BYTES))).terrain & 0x06)) return 1;
    return 0;
}

// FUNCTION: C2 0x6DB08
// WIN: 0x004abebd
// Lines 3603–3622
//
// Probe whether any of the 8 region_map neighbours of
// (x, y) carries a wall mark (region_map[(+1)] & 0x02).
// Returns 1 on the first hit, else 0.
int test_for_next_to_region_wall(int x, int y)
{
    int sptr = ((x) + (y) * 60) * 8;

    if (y > 0) {
        if ((*(struct region_cell *)((unsigned char *)region_map + (sptr - 480))).terrain & 0x02) return 1;
        if (x > 0    && ((*(struct region_cell *)((unsigned char *)region_map + (sptr - 488))).terrain & 0x02)) return 1;
        if (x < 0x3b && ((*(struct region_cell *)((unsigned char *)region_map + (sptr - 472))).terrain & 0x02)) return 1;
    }
    if (y < 0x3b) {
        if ((*(struct region_cell *)((unsigned char *)region_map + (sptr + 480))).terrain & 0x02) return 1;
        if (x > 0    && ((*(struct region_cell *)((unsigned char *)region_map + (sptr + 472))).terrain & 0x02)) return 1;
        if (x < 0x3b && ((*(struct region_cell *)((unsigned char *)region_map + (sptr + 488))).terrain & 0x02)) return 1;
    }
    if (x > 0    && ((*(struct region_cell *)((unsigned char *)region_map + (sptr - 8))).terrain & 0x02)) return 1;
    if (x < 0x3b && ((*(struct region_cell *)((unsigned char *)region_map + (sptr + 8))).terrain & 0x02)) return 1;
    return 0;
}

// FUNCTION: C2 0x6DBDA
// WIN: 0x004ac027
// Lines 3624–3653
//
// Count region-map cells of `building_kind` in a clipped rectangular
// search area.  PS callers pass the centre/radius in registers and a
// span/kind pair; this helper preserves the original broad signature
// for future evolve/query callers.
int get_reg_buildings_in_radius(int x, int y, int span, int radius,
                                unsigned char building_kind)
{
    int width;
    int height;
    int row_skip;
    int count;
    unsigned char kind;

    x = x - radius;
    y = y - radius;
    height = radius * 2 + 1;
    span--;
    width = height + span;
    height = width;
    if (x < 0) { width += x; x = 0; }
    else if (x + width > 60) width -= x + width - 60;
    if (y < 0) { height += y; y = 0; }
    else if (y + height > 60) height -= y + height - 60;

    gmn_sptr = (x + y * 60) * 8;
    row_skip = (60 - width) * 8;

    count = 0;
    for (gmn_y = y; gmn_y < y + height; gmn_y++, gmn_sptr += row_skip) {
        for (gmn_x = x; gmn_x < x + width; gmn_x++, gmn_sptr += 8) {
            kind = (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).base_kind;
            if (kind == building_kind) count++;
        }
    }
    return count;
}

// FUNCTION: C2 0x6DCB4
// WIN: 0x004ac19b
// Lines 3655–3681
//
// Count 3×3-neighbourhood regional industry/port tiles (0xdc..0xef)
// around (x,y), clipping at the 60×60 map edges.
int get_reg_industries_in_radius(int x, int y)
{
    int width;
    int height;
    int row_skip;
    int count;
    unsigned char kind;

    x = x - 1; y = y - 1;
    height = 3; width = height;

    if (x < 0) { width += x; x = 0; }
    else if (x + width > 60) width -= x + width - 60;
    if (y < 0) { height += y; y = 0; }
    else if (y + height > 60) height -= y + height - 60;

    gmn_sptr = (x + y * 60) * 8;
    row_skip = (60 - width) * 8;

    count = 0;
    for (gmn_y = y; gmn_y < y + height; gmn_y++, gmn_sptr += row_skip) {
        for (gmn_x = x; gmn_x < x + width; gmn_x++, gmn_sptr += 8) {
            kind = (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).base_kind;
            if (kind >= 0xdc && kind <= 0xef) count++;
        }
    }
    return count;
}

// FUNCTION: C2 0x6DD8C
// WIN: 0x004ac2ff
// Lines 3683–3726
//
// Search a clipped radius around (x,y) for the nearest top-left tile
// of a logging-camp/trading-post style 2×2 building (0xe8..0xeb).
// The best cell offset is published in gmn_sptr; the return value is
// the longest-axis distance to that cell, or radius+1 if none found.
int get_closest_trading_post(int x, int y, int radius)
{
    unsigned char kind;
    unsigned char occ;
    int y2;
    int x2;
    int width;
    int height;
    int row_skip;
    int best;
    int best_sptr;
    int dist;

    best_sptr = 0;
    best = radius + 1;
    x2 = x;
    y2 = y;
    x -= radius;
    y -= radius;
    width = height = radius * 2 + 1;
    if (x < 0) {
        width += x;
        x = 0;
    } else if (x + width > 60) {
        width -= x + width - 60;
    }
    if (y < 0) {
        height += y;
        y = 0;
    } else if (y + height > 60) {
        height -= y + height - 60;
    }
    gmn_sptr = (y * 60 + x) * 8;
    row_skip = (60 - width) * 8;

    for (gmn_y = y; gmn_y < y + height; gmn_y++, gmn_sptr += row_skip) {
        for (gmn_x = x; gmn_x < x + width; gmn_x++, gmn_sptr += 8) {
            kind = ((unsigned char *)region_map)[gmn_sptr];
            occ  = ((unsigned char *)region_map)[gmn_sptr + 7] & 3;
            if (occ != 0) continue;
            if (kind >= 0xe8 && kind <= 0xeb) {
                dist = get_longest_distance(gmn_x, gmn_y, x2, y2);
                if (dist < best) {
                    best = dist;
                    best_sptr = gmn_sptr;
                }
            }
        }
    }
    gmn_sptr = best_sptr;
    return best;
}

// FUNCTION: C2 0x6DEDF
// WIN: 0x004ac4e9
// Lines 3728–3794
//
// Add `amount` goods of type `goods` to warehouses in the 4×4 area
// around (x,y).  Warehouse cells store goods in region_map[(+7)]: high
// nibble = goods type, low nibble = amount.  Optional `refresh` updates
// the warehouse sprite state after filling.
//
// RESIDUE (2026-07-07): ir 1/42 (isl 2), 221bd -- was ir 8/42 (isl 11,
// 330bd) before the fixes below (Hard Rule #3: shape dropped hugely even
// though bytes rose from the rewritten loop shape).  Two generalizable
// levers applied (see AGENTS.md session-lever survey, ~2026-07-07 17:00-
// 19:05 commits):
//   1. loop-rotation (the PS-only `loop_rotation_entry`/`loop_rotation_
//      test_back` hint / clear_an_area's Rule 134): all three nested
//      `while (cond) {...; cnt++;}` loops rewritten as the bottom-tested
//      `for ( ; cond; cnt++)` form (empty init clause, init done as a
//      separate prior statement) -- PS jumps PAST the body to the
//      bottom compare on loop entry; `while` funnels the test to the top.
//   2. dropped an un-PS `(unsigned short)qty == 0` cast (qty is already
//      `unsigned char`; PS just tests the byte, no widen) -- ir 3->1.
// Remaining island: `gmn_y = y;` seats in RC EAX vs PS EDX, a compiler-
// temp ConfBefore tie against `goods`/anon EAX competitors at L5421/5484
// (regtrace: "EAX<->ECX ... best-guess taken").  Swept all 24 decl-order
// permutations of the 4 top-scope int locals (row_skip/i/height/width,
// the Rule 115 lever regtrace names) -- best is the current order
// (221bd); every other permutation regresses to 287bd.  Not source-decl
// reachable; document, do not grind further (Hard Rule #6).
void fill_warehouses_with(int x, int y, int amount, int goods, int refresh)
{
    unsigned char stored_goods;
    unsigned char qty;
    unsigned char cell_kind;
    unsigned char refresh_qty;
    int row_skip;
    int i;
    int height;
    int width;

    if (amount == 0) return;
    x -= 1; y--;
    width = height = 4;
    if (x < 0)             { width = x + 4; x = 0; }
    else if (x + 4 > 0x3c) width = 4 - (x - 0x38);
    if (y < 0)             { height += y; y = 0; }
    else if (y + height > 0x3c) height -= y + height - 0x3c;

    row_skip = (60 - width) * 8;
    i = 0;
    for ( ; i < amount; i++) {
        gmn_sptr = ((x) + (y) * 60) * 8;
        gmn_y = y;
        for ( ; gmn_y < y + height; gmn_y++, gmn_sptr += row_skip) {
            gmn_x = x;
            for ( ; gmn_x < x + width; gmn_x++, gmn_sptr += 8) {
                cell_kind = (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).base_kind;
                if (cell_kind == 0xd4) {
                    stored_goods = (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).occupant & 0xf0;
                    stored_goods >>= 4;
                    qty = (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).occupant & 0xf;
                    if (qty == 0) {
                        (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).edge_bits |= 0x40;
                        (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).occupant &= 0xf;
                        (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).occupant |= (goods << 4);
                    } else if (stored_goods != goods) continue;
                    else if (qty >= 0xf) continue;
                    qty++;
                    (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).occupant &= 0xf0;
                    (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).occupant |= qty;
                    goto next_unit;
                }
            }
        }
next_unit:
        ;
    }

    if (refresh == 1) {
        gmn_sptr = ((x) + (y) * 60) * 8;
        gmn_y = y;
        for ( ; gmn_y < y + height; ) {
            gmn_x = x;
            for ( ; gmn_x < x + width; ) {
                cell_kind = (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).base_kind;
                if (cell_kind == 0xd4) {
                    qty = (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).occupant & 0xf;
                    if (qty < 0xf) refresh_qty = qty + 0xb;
                    else refresh_qty = 0x24;
                    change_reg_sized(cell_kind, refresh_qty, 1, gmn_sptr);
                }
                gmn_x++; gmn_sptr += 8; } gmn_y++; gmn_sptr += row_skip; }
    }
}

// FUNCTION: C2 0x6E10D
// WIN: 0x004ac84e
// Lines 3796–3821
//
// Remove up to `amount` goods of type `goods` from warehouses, scanning
// the whole region map.  Stops once the request is satisfied.
void take_from_warehouses(int amount, int goods)
{
    unsigned char qty;
    unsigned char stored_goods;

    if (amount <= 0) return;
    gmn_y = 0;
    gmn_sptr = 0;
    for ( ; gmn_y < 60; gmn_y++) {
    gmn_x = 0;
    do {
        if (((*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).base_kind & 0xff) == 0xd4) {
                stored_goods = (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).occupant & 0xf0;
                stored_goods >>= 4;
                qty = (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).occupant & 0xf;
                if (stored_goods == goods && qty != 0) {
                    if (amount >= qty) {
                        amount -= qty;
                        qty = 0;
                    } else {
                        qty -= amount;
                        amount = 0;
                    }
                    (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).occupant &= 0xf0;
                    (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).occupant |= qty;
                    if (amount <= 0) return;
                }
            }
        gmn_x++;
        gmn_sptr += 8;
    } while (gmn_x < 60);
    }
}

// FUNCTION: C2 0x6E1CB
// WIN: 0x004ac9b3
// Lines 3823–3827
//
// Stamp `value` at field_off on the north + south city_map
// neighbours of `sptr` (skips the E/W pair).  Used by polar
// neighbour passes.
void set_ns_polar(int x, int y, int sptr, unsigned char field_off, unsigned char value)
{
    (void)x;
    if (y > 0)  ((unsigned char *)city_map)[sptr - 1600 + field_off] = value;
    if (y < 79) ((unsigned char *)city_map)[sptr + 1600 + field_off] = value;
}

// FUNCTION: C2 0x6E1F6
// WIN: 0x004ac9f6
// Lines 3828–3832
//
// Sister of set_ns_polar: stamps `value` on the E/W neighbours only.
void set_ew_polar(int x, int y, int sptr, unsigned char field_off, unsigned char value)
{
    (void)y;
    if (x > 0)  ((unsigned char *)city_map)[sptr - 20 + field_off] = value;
    if (x < 79) ((unsigned char *)city_map)[sptr + 20 + field_off] = value;
}

// FUNCTION: C2 0x6E221
// WIN: 0x004aca39
// Lines 3835–3863
//
// Add signed `delta` to land_value (+0x0f) over a clipped city-map
// rectangle centered at (x,y).  Radius plus extra width determines the
// side length; values are clamped to [-64, 64].
/* NOTE: 86b residual, single root: the DELTA stack-parm's register home.
   PS homes delta->ECX (extra evicted to EBP at the prologue); recomp
   homes delta->EBX (radius evicted to EAX).  PROVEN from PS asm and kept
   here: the guard-first order and ALL params modified in place (sub
   esi/edi,ebx; add ebx,ebx; add ebp,ebx -- x,y,radius,extra ARE x0,y0,
   r2,width).  Also proven but REVERTED (head reshuffle nets worse until
   the home issue is fixed): the clamp region byte-matches PS as
   `signed char nv = map[..]+(char)delta; v = nv; if (v>0x40) nv=0x40;
   else if (v<-0x40) nv=-0x40; map[..]=nv;` (clamps write the BYTE copy,
   compare the int -- movsx edx,al / mov al,0x40 2-byte forms).  Tried:
   decl orders, char delta param (worse), v-first.  Same blocked family
   as put_reg_x1_area (treegen home/coalesce choice). */
void change_lv(int x, int y, int radius, int extra, int delta)
{
    int width;
    int height;
    int row_skip;
    int v;

    if (extra == 0) return;
    x -= radius;
    y -= radius;
    height = extra + radius * 2;
    width = height;
    if (x < 0) { width += x; x = 0; }
    else if (x + width > 80) width -= x + width - 80;
    if (y < 0) { height += y; y = 0; }
    else if (y + height > 80) height -= y + height - 80;

    gmn_sptr = ((x) + (y) * 80) * 20;
    row_skip = (80 - width) * 20;
    for (gmn_y = y; gmn_y < y + height;) {
        for (gmn_x = x; gmn_x < x + width;) {
            signed char nv = (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).land_value;
            nv += (char)delta;
            v = nv;
            if (v > 0x40) nv = 0x40;
            else if (v < -0x40) nv = -0x40;
            (*(struct city_cell *)((unsigned char *)city_map + (gmn_sptr))).land_value = nv;
            gmn_x++;
            gmn_sptr += 20;
        }
        gmn_y++;
        gmn_sptr += row_skip;
    }
}

// FUNCTION: C2 0x6E31B
// WIN: 0x004acbcf
// Lines 3865–3878
//
// Return the maximum ``land_value`` (cell field +0x0F) over a
// ``bp × bp`` square of city_map cells starting at ``base``.
// Used by evolve_* paths to score zone-suitable land before stamping
// new buildings.
int get_best_lv(unsigned char *base, int bp)
{
    int best;
    int i;
    int j;

    best = 0;
    for (i = 0; i < bp; i++) {
        for (j = 0; j < bp; j++) {
            int val = (base + j * CITY_CELL_BYTES + i * CITY_ROW)[15];
            if (val > best) best = val;
        }
    }
    return best;
}

// FUNCTION: C2 0x6E36A
// WIN: 0x004acc61
// Lines 3880–3886
//
// Given a city-map byte pointer into a multi-cell building, return
// a pointer to the building's top-left corner cell.  The cell's
// byte +5 (activity_a field) low nibble holds a packed sub-
// position `packed = ofset_y * size + ofset_x`; we subtract
// ofset_x × 20 (cell stride) and ofset_y × 1600 (row stride)
// from the input pointer to walk back to the top-left.
//
// Caller computes `base_ptr = city_map + cm_sptr`
// before passing in (cap_land_value).  The result is the
// canonical building anchor.
//
unsigned char *get_ptr_to_corner(unsigned char *base_ptr, int size)
{
    int packed;
    int x_off;

    packed = base_ptr[5] & 0xf;
    x_off = packed % size; packed /= size;
    base_ptr -= x_off * 20;
    packed *= 1600; return base_ptr - packed;
}

// FUNCTION: C2 0x6E3B5
// WIN: 0x004accc6
// Lines 3890–3899
//
// Returns 1 if any cell in a range×range square starting at `p`
// has `cell.education` (+0x0D) sharing any bit with `mask`.
// Special-cased range==1 path returns the bitwise AND directly
// (used for single-cell footprints like simple housing).
char affected_by_cover1(unsigned char *p, int range, char mask)
{
    int xi;
    int yi;

    if (range == 1)
        return (p)[13] & mask;
    for (yi = 0; yi < range; yi++) {
        for (xi = 0; xi < range; xi++) {
            if ((p + xi * CITY_CELL_BYTES + yi * CITY_ROW)[13] & mask)
                return 1;
        }
    }
    return 0;
}

// FUNCTION: C2 0x6E41C
// WIN: 0x004acd6f
// Lines 3901–3908
//
// Sibling of affected_by_cover1; same shape but reads
// `cell.health` (+0x0E) instead of `cell.education` (+0x0D).
//
char affected_by_cover2(unsigned char *p, int range, char mask)
{
    int xi;
    int yi;

    if (range == 1)
        return (p)[14] & mask;
    for (yi = 0; yi < range; yi++) {
        for (xi = 0; xi < range; xi++) {
            if ((p + xi * CITY_CELL_BYTES + yi * CITY_ROW)[14] & mask)
                return 1;
        }
    }
    return 0;
}

// FUNCTION: C2 0x6E47B
// WIN: 0x004ace18
// Lines 3912–3926
//
// Scan a `range × range` block of city-map cells starting at
// `start` and return the maximum value of `cell->range_flag
// & mask` found in the block.  Used by `cap_land_value` and
// `get_query_info` to find the highest range marker in a
// neighbourhood.  Special-cased range==1 returns just the
// single cell's masked value.
//
int get_range1(unsigned char *start, int range, char mask)
{
    int best;
    int row;
    int col;
    int val;
    unsigned char *c;

    if (range == 1) {
        val = (start)[10];
        val &= mask;
        return val;
    }
    best = 0;
    for (row = 0; row < range; row++) {
        for (col = 0; col < range; col++) {
            c = start + col * CITY_CELL_BYTES + row * CITY_ROW;
            val = (c)[10];
            val &= mask;
            if (val > best)
                best = val;
        }
    }
    return best;
}

// FUNCTION: C2 0x6E4F3
// WIN: 0x004aced1
// Lines 3928–3940
//
// Sister of `get_range1` for `cell->entertain` (+0xc) instead
// of `cell->range_flag` (+0xa).  Callers pass entertainment
// masks 0x3/0xc/0x30 (theatre/colosseum/circus 2-bit slots),
// confirming the field is CC_ENTERTAIN, not CC_FPU_FLAG.
int get_range3(unsigned char *start, int range, char mask)
{
    int best;
    int row;
    int col;
    int val;
    unsigned char *c;

    if (range == 1) {
        val = (start)[12];
        val &= mask;
        return val;
    }
    best = 0;
    for (row = 0; row < range; row++) {
        for (col = 0; col < range; col++) {
            c = start + col * CITY_CELL_BYTES + row * CITY_ROW;
            val = (c)[12];
            val &= mask;
            if (val > best)
                best = val;
        }
    }
    return best;
}

// FUNCTION: C2 0x6E563
// WIN: 0x004acf8a
// Lines 3944–3990
//
// Scan a clipped square around (x, y) for housing cells (0x82..0xa1)
// that are top-left footprint cells.  `mode` selects which service
// byte contributes to the four global test_result counters:
//   0 -> range_flag & 0xc (theatre/colosseum); split into the
//        "no entertainment" counter test_result2 and the "summed
//        entertainment level" counter test_result3.
//   1 -> range_flag & 0x30 (circus) -> test_result2 ("no").
//   2 -> fpu_flag & 0xf       (forum coverage) -> sum.
// test_result1 counts the total housing tiles visited.
void test_range_for(int x, int y, int radius, int mode)
{
    unsigned char kind_byte;
    int kind;
    int height;
    int yend;
    int row_skip;
    int sptr;
    char val;
    int width;
    int xend;
    char sub;
    int diff;

    x -= radius;
    y -= radius;
    width = height = radius * 2 + 1;

    xend = width + x;
    if (x < 0) {
        width = xend;
        x = 0;
    } else if (xend > 80) {
        width -= xend - 80;
    }
    yend = height + y;
    if (y < 0) {
        height = yend;
        y = 0;
    } else if (yend > 80) {
        height -= yend - 80;
    }

    sptr = ((x) + (y) * 80) * 20;
    diff = (80 - width) * 4;
    diff += (80 - width);
    row_skip = diff * 4;
    test_result1 = 0;
    test_result2 = 0;
    test_result3 = 0;
    test_result4 = 0;
    for (gmn_y = y; gmn_y < y + height; gmn_y++, sptr += row_skip) {
        for (gmn_x = x; gmn_x < x + width; gmn_x++, sptr += 20) {
            sub = (*(struct city_cell *)((unsigned char *)city_map + (sptr))).activity_a & 0xf;
            kind_byte = (*(struct city_cell *)((unsigned char *)city_map + (sptr))).base_kind;
            kind = kind_byte;
            if (kind >= 0x82 && kind <= 0xa1)
                if (sub == 0) {
                    test_result1++;
                    if (mode == 0) {
                        val = (*(struct city_cell *)((unsigned char *)city_map + (sptr))).range_flag & 0xc;
                        val >>= 2;
                        if (val == 0)
                            test_result2++;
                        else
                            test_result3 += val;
                    } else if (mode == 1) {
                        val = (*(struct city_cell *)((unsigned char *)city_map + (sptr))).range_flag & 0x30;
                        if (val == 0)
                            test_result2++;
                    } else if (mode == 2) {
                        val = (*(struct city_cell *)((unsigned char *)city_map + (sptr))).fpu_flag & 0xf;
                        test_result2 += val;
                    }
                }
        }
    }
}

// FUNCTION: C2 0x6E6D6
// WIN: 0x004ad1db
// Lines 3992–4017
//
// Return true if any cell in a clipped city-map square has the road /
// plaza terrain bit 0x20 set.
int test_range_for_road(int x, int y, int radius)
{
    int side;
    int width;
    int sptr;
    int row_skip;
    unsigned char t;
    x -= radius;
    y -= radius;
    side = radius * 2 + 1;
    width = side;

    if (x < 0) { width = side + x; x = 0; }
    else if (x + side > 80) { width -= (x + side) - 80; }
    if (y < 0) { side = side + y; y = 0; }
    else if (y + side > 80) { side -= (y + side) - 80; }

    sptr = ((x) + (y) * 80) * 20;
    row_skip = (80 - width) * 20;

    for (gmn_y = y; gmn_y < y + side; gmn_y++, sptr += row_skip) {
        for (gmn_x = x; gmn_x < x + width; gmn_x++, sptr += 20) {

            t = (*(struct city_cell *)((unsigned char *)city_map + (sptr))).terrain & 0x20;
            if (t != 0) return 1;
        }
    }
    return 0;
}

// FUNCTION: C2 0x6E7A2
// WIN: 0x004ad339
// Lines 4019–4051
//
// Sum houses_to_people for top-left housing cells in a clipped area around
// (x,y).  The optional extra parameter widens the square beyond radius.
int test_area_for_population(int extra, int x, int y, int radius)
{
    int width;
    int height;
    int xend;
    int yend;
    int row_skip;
    int sptr;
    int total;
    int kind;
    char kind_byte;
    char flag;

    x -= radius;
    y -= radius;
    width = height = radius * 2 + 1;
    if (extra != 0)
        height = width = height + extra;

    xend = width + x;
    if (x < 0) {
        width = xend;
        x = 0;
    } else if (xend > 80) {
        width -= xend - 80;
    }
    yend = height + y;
    if (y < 0) {
        height = yend;
        y = 0;
    } else if (yend > 80) {
        height -= yend - 80;
    }

    sptr = ((x) + (y) * 80) * 20;
    row_skip = (80 - width) * 20;
    total = 0;
    for (gmn_y = y; gmn_y < y + height; gmn_y++, sptr += row_skip) {
        for (gmn_x = x; gmn_x < x + width; gmn_x++, sptr += 20) {
            flag = (*(struct city_cell *)((unsigned char *)city_map + (sptr))).activity_a & 0xf;
            kind_byte = (*(struct city_cell *)((unsigned char *)city_map + (sptr))).base_kind;
            kind = kind_byte & 0xff;
            if (kind >= 0x82 && kind <= 0xa1 && flag == 0)
                total += houses_to_people[kind - 0x82];
        }
    }
    return total;
}

// FUNCTION: C2 0x6E898
// WIN: 0x004ad4f0
// Lines 4055–4067
//
// Snapshot the active map (city_map @ 80×80×20, or region_map
// @ 60×60×8) into the undo scratch buffer.  City snapshot lives
// at scratch_buffer + 0..0x1F3FF; region snapshot at
// +0x1F400..+0x2647F.  Clears the corresponding `_undo_flushed`
// flag so the matching restore_*_from_undo_buffer() can later
// roll back.  Other map_mode values are ignored.
void save_undo_info(void)
{
    if (map_mode == 0) {
        sb_cm_undo_flushed = 0;
        copy((unsigned char *)city_map, scratch_buffer, 0x1f400);
    } else if (map_mode == 1) {
        sb_rm_undo_flushed = 0;
        copy((unsigned char *)region_map, scratch_buffer + 0x1f400, 0x7080);
    }
}


// FUNCTION: C2 0x6E8EB
// WIN: 0x004ad562
// Lines 4069–4074
//
// Roll back the city map (80×80×20 = 0x1F400 bytes) from
// the undo scratch buffer.  Skip if the undo region was
// already flushed.  Particle counters are zeroed alongside
// because they tracked the now-discarded user actions.
void restore_city_from_undo_buffer(void)
{
    if (sb_cm_undo_flushed != 0) return;
    copy(scratch_buffer, (unsigned char *)city_map, 0x1f400);
    particles_built = 0;
    particles_cleared = 0;
}

// FUNCTION: C2 0x6E91B
// WIN: 0x004ad5ad
// Lines 4076–4082
//
// Region-map equivalent: city undo lives at scratch_buffer
// +0..0x1F3FF, region undo at +0x1F400..+0x2647F (28 800
// bytes).  After the rollback, replays army-position
// adjustments invalidated by the undo.
void restore_region_from_undo_buffer(void)
{
    if (sb_rm_undo_flushed != 0) return;
    copy(scratch_buffer + 0x1f400, (unsigned char *)region_map, 0x7080);
    particles_built = 0;
    particles_cleared = 0;
    army_restoring_adjusts();
}

// FUNCTION: C2 0x6E955
// WIN: 0x004ad602
// Lines 4084–4093
//
// Reset every layer of the region map and the relevant
// city-map layers.  PS folds the trailing call to
// clear_all_cm(4) into a fallthrough — the function ends
// with `mov eax, 4` and runs straight into clear_all_cm at
// +0x48.  Source order (clear_region_map immediately before
// clear_all_cm) is what coaxes Watcom into emitting that.
void clear_region_map(void)
{
    clear_all_rm(2);
    clear_all_rm(0);
    clear_all_rm(1);
    clear_all_rm(3);
    clear_all_cm(5);
    clear_all_cm(6);
    clear_all_rm(7);
    clear_all_cm(4);
}

// FUNCTION: C2 0x6E99D
//
// Zero the byte at offset `layer` (0..19) inside every
// cell of the 80x80 city_map.  8 byte-stores per inner
// iter × 10 inner iters × 80 outer iters = 6400 cells =
// full city_map.  Globals `cm_sptr` (running byte offset
// from city_map base) and `gmn_x` / `gmn_y` (cell column
// / row counters) are clobbered as side effects.
//
void clear_all_cm(char layer)
{
    cm_sptr = 0;
    for (gmn_y = 0; gmn_y < 80; gmn_y++) {
        for (gmn_x = 0; gmn_x < 10; gmn_x++, cm_sptr += 0xa0) {
            int idx = cm_sptr + (unsigned char)layer;
            (*(struct city_cell *)((unsigned char *)city_map + (idx))).base_kind = 0;
            (*(struct city_cell *)((unsigned char *)city_map + ((idx) + CITY_CELL_BYTES))).base_kind = 0;
            (*(struct city_cell *)((unsigned char *)city_map + (idx + 0x28))).base_kind = 0;
            (*(struct city_cell *)((unsigned char *)city_map + (idx + 0x3c))).base_kind = 0;
            (*(struct city_cell *)((unsigned char *)city_map + (idx + 0x50))).base_kind = 0;
            (*(struct city_cell *)((unsigned char *)city_map + (idx + 0x64))).base_kind = 0;
            (*(struct city_cell *)((unsigned char *)city_map + (idx + 0x78))).base_kind = 0;
            (*(struct city_cell *)((unsigned char *)city_map + (idx + 0x8c))).base_kind = 0;
        }
    }
}

// FUNCTION: C2 0x6EA2D
// Lines 4096–4100
//
// Strip the edge-info bit (mask 0xfd) from byte +3 on every cell of
// the active map (city or region, picked by map_mode).
void clear_edge_info(void)
{
    if (map_mode == 0) {
        unflag_all_cm(3, 0xfd);
    } else if (map_mode == 1) {
        unflag_all_rm(3, 0xfd);
    }
}

// FUNCTION: C2 0x6EA65
// WIN: 0x004ad6aa
// Lines 4106–4111
//
// Reset the route elastic-band overlay: clear region-map
// layer 2 then call set_route_elastic_range for each band
// 1..15.
void set_route_elastic(void)
{
    int i;
    clear_all_rm(2);
    for (i = 1; i <= 0xf; i++)
        set_route_elastic_range(i);
}

// FUNCTION: C2 0x6EA84
// WIN: 0x004ad6ec
// Lines 4114–4184
//
// BFS step for army route-finding on region_map.  Called
// from set_route_elastic with r = 1, 2, 3, … to expand the
// movement-cost slot stamp (region_map[(+2)]) outward from
// (over_x, over_y) one ring at a time, taking the cheaper
// of (best 8-neighbour slot + step cost) and the existing
// stamp.
//
// Seeds cm[+2] = 1 at (over_x, over_y) on entry.
//
// Visits cells in the clipped 60×60 bbox of side 2*r+1
// around (over_x, over_y).  Per cell:
//   * cm[+2] == 0xFF                 → skip
//   * cm[+1] & 0x11 (impassable) AND
//     terrain not in 0x93..0x96      → cm[+2] = 0xFF
//   * cm[+1] & 0x04 (owned region):
//        cm[+7] != 0 AND
//        cm[+7] != tracking_army     → cm[+2] = 0xFF
//        otherwise                    → cost = 2
//   * else if cm[+1] & 0x20 (road)   → cost = 1
//   * else if cm[+1] & 0x02 (wall)   → cm[+2] = 0xFF
//   * else                            → cost = 2
//
// Read the 8 neighbour [+2] slots (gating each on the
// appropriate edge test).  Track the smallest non-zero,
// non-0xFF slot starting from a sentinel of 0xC7 in `best`.
// new_slot = best + cost.  Write cm[+2] = new_slot when:
//   * new_slot < current cm[+2], OR
//   * cm[+2] == 0 AND best != 0  (first stamp).
//
// Neighbour byte offsets in region_map (8-byte cells,
// 60-wide grid):
//   N  -0x1DE   NE -0x1D6
//   E  +0x0A   SE +0x1EA
//   S  +0x1E2  SW +0x1DA
//   W  -6       NW -0x1E6
//
// SHAPE 2026-07-09: the header block now matches PS's -d1 order:
// x_min(L4126), y_min(L4127), side/x_span(L4128); then
// gmn_sptr(L4135), stride(L4136), gmn_y(L4138) -- the prior order
// (side before y_min; stride/gmn_y before gmn_sptr) added RC-only
// [ops] statements PS lacked (ir 8->4 by the dossier judge metric).
// Remaining residue is Rule 107: the -d1-faithful int-temp order
// (y_min/side/stride) tips the AssignTemps size-sort ShellSort into
// an unstable arm, swapping the {cost,saved,n_se,n_n,side,y_min,stride}
// spill slots (bytes 627->707 -- pure slot displacement, no reg or
// op change).
//
// SIM 2026-07-09 (c2.regalloc.shellsort_sim, driven directly): the
// simulator reproduces this function's live nt_post exactly; PS's
// target 7-order is [saved,n_se,cost,n_n,stride,side,y_min] (derived
// from the DOS slot offsets).  UNLIKE clear_an_area (win-census
// Delta=-3 invented locals -> a nested-if/de-invent structural fix WAS
// the temp-set lever that flipped its swap), set_route's local set
// already MATCHES PS (win-census Delta=0).  So no faithful lever exists:
// header statement-reorder (within the -d1 order) and decl-order are
// INERT (temp ranks don't move); the only perturbations that flip the
// sort ADD/REMOVE a temp or flip byte<->int types -- which make the set
// WRONG (Delta!=0) and break the proven byte codegen (cost/saved are
// byte-stored in PS: mov byte[esp+N],K).  Documented shellsort-
// instability / sort-stable-other open frontier: correct temp set, no
// source lever isolated.  Destabilising size=1 temps: L6248,6247,6224,6283.
//
// SEAT FIX 2026-07-09: the sav=600 n_* ConfBefore tie order IS
// decl-order-driven, via a FIXED position permutation p=[7,5,1,8,2,4,3,6]
// (tie[i] = decl[p[i]] over the 8 n_* decl slots).  Inverting p for PS's
// tie order [n_ne,n_s,n_w,n_sw,n_nw,n_e,n_n,n_se] gave the current decl
// order; seats now match PS exactly (regtrace verdict clean, binir 5->1
// semantic lines).  The older "decl-order is INERT" claim above applies
// only to the AssignTemps slot RANKS (nt list), which are decl-blind --
// verified again after the seat fix (slot commit order unchanged).
//
// SLOT SIM UPDATE 2026-07-09 (post-seat-fix single-perturbation sweep of
// nt_pre, sim==live validated): NO removal flips to PS's order; the only
// single perturbations that do are (a) swapping n_e's nt slot with an
// anon dword (L6234/L6259 CSE temps) or r's, (b) INSERTING a fresh dead
// sz1 name at nt[85] (creation point ~L6226-6229, a region with no byte
// objects), (c) INSERTING a fresh dead sz4 name at nt[3]/nt[5] (creation
// between L6263 and L6296's dead temps).  All act on anonymous-name
// CREATION ORDER, which no tested source spelling reaches (decl order,
// statement order inert).  Residue class: Rule 107 shellsort-instability,
// anon-temp-birth-order arm -- open frontier, NOT a proven floor.
//
// ⚠ -d1 CONFLICT (2026-07-09, second session): the CURRENT header order
// (side/x_span before y_min, from 0f45d13b's shape win ir17->9) CONTRADICTS
// the -d1 witness -- PS marks are L4126 x_min, L4127 y_min (mov eax,esi;
// sub; mov [esp],eax), L4128 side+x_span PACKED ON ONE LINE (add ecx,ecx;
// inc; store; mov ebp,ecx), all in ascending address order = source order.
// The shape drop is a COMPENSATED PAIR: swapping the y_min/side statements
// while their spill slots are also swapped reproduces nearly the same
// bytes (like the side+y_min operand-order trap at the guard/loop-bound
// sites, which is byte-compensated by the same slot swap -- do NOT
// "fix" the operand orders alone; probed, +1 isl).  The TRUE target is
// the -d1 order (y_min first, side;x_span packed) WITH PS's slots
// [y_min->esp, side->esp+4, stride->esp+8]; from that baseline `c2 sweep`
// exhausts the decl space FLAT at shape 11 and every descent chains
// through anti-d1 stmt swaps.  Also exhausted: forge solve (48k-variant
// class sibling trace_back was fully neutral), spell --suggest (no safe
// folds).  Still the anon-temp-birth-order frontier.
//
// 2026-07-10 THE TRUE-SHAPE COMPOSITION (three edits that only work
// TOGETHER, on the -d1-true frame -- each alone/mixed with the
// committed form regresses):
//   (1) header in -d1 order: x_min; y_min; side; x_span  (L4126-28),
//   (2) the || condition spelled `best + cost < saved` (RC then emits
//       PS's movzx-of-cost mirror -- the zext-idiom island closes),
//   (3) `t = cost + best;` on its own line before the if, store `= t;`
//       (materializes PS's `mov ah,[cost]; add ah,al` byte sum, SAME
//       AH seat, and LOCKS the byte-slot triple cost->0x10 n_se->0x14
//       saved->0x18 to PS).
// Result: ALL 266 insns match register-blind except the ah-pair's
// SCHEDULE (PS mid-condition after the saved load, RC at block top --
// the -d1 marks put PS's t-assign inside L4180's span, position is
// sub-source) -- but the metric reads ir 13 / 703bd because the
// (side,y_min,stride) dword-slot triple ROTATES ([esp],[esp+4],[esp+8])
// and cascades displacements.  Sim (single-perturbation, on that
// baseline): flip = REMOVE any ONE of nt[41..48] = r(SAllocUserTemp) /
// ArithExpand L6286,L6292 / CheckMul pairs L6279,L6298 / InsToAddr --
// all attributed, none source-removable found (`*8`->`<<3` INERT@TREE;
// spell --suggest's 5 LIVE candidates all regress; sweep descends only
// via anti-d1 compensations).  APPLIED: the composition IS the current
// body -- it is byte-closer than the old compensated form (703bd vs
// 730bd) besides being witness-true; the metric's ir 13 (vs the old
// form's ir 9) is slot-cascade attribution, not shape.  Remaining:
// the (side,y_min,stride) rotation (one temp-removal in nt[41..48])
// and the sub-source ah-pair schedule.
//
// 2026-07-11 (nf-instrumented session): the removal lever space is now
// PROVABLY closed at every observable level -- (a) arithmetic/address
// respellings of the window lines (assoc, *8<-><<3, flat-array) are
// canonicalized at tree->IL emission (spell INERT@BURN, identical ni
// births); (b) dead stores and coalesced `t = x;` copies birth a name
// that the pre-RegAlloc useless-name sweep @0x5862f culls (nf records;
// `c2 tempbirths` prints the cull list); (c) a fresh NAMED local is
// blocked by the win-census Δ=0 local-set witness.  The window's
// surviving anons are all emission-determined (InsToAddr/CheckMul/
// ArithExpand of the existing exprs).  If PS's input differs it is by
// a MULTI-entry compensation outside the single-perturbation space.
// Certified Rule 107 anon-birth-order residue; open, not a floor.
//
// 2026-07-11 ORACLE SHAPE FIX: Mac and MSVC /Od both expose the final
// update as explicit `if (...) store; else if (...) store;`, with no
// second assignment to the base-kind scratch `t`.  Restoring that form
// drops DOS 703bd -> 297bd and ir 13 -> 9; WIN struct diff drops 23 -> 9.
// The same oracles nest the wall test and fallback `cost = 2` inside the
// final terrain `else`; that rewrite is DOS-neutral but removes WIN's
// extra-goto source-shape mismatch.  Mac's `y_min + side` loop bound
// operand order then closes the last dword-slot island (297bd -> 292bd,
// ir 9 -> 8).  Rule 152 / Rule 28a / Hard Rule 7.
// 2026-07-11 BYTE-EXACT: the apparent final AH/DL residue was a two-part
// source composition.  Reusing dead n_sw as the result carrier in BOTH
// explicit update arms makes Watcom hoist the byte sum into PS's AH and
// use ESI for the final address.  That extends n_sw's live range, so the
// declaration permutation below is required to retain every PS neighbor
// seat and spill slot.  The deferred block local `int value; value = best;`
// plus the load-bearing `cost + value` operand order then emits PS's exact
// promoted condition sequence (`mov cl,al` followed by `movzx esi,[cost]`).
// Direct best+cost, init-in-decl, and precomputed-sum forms choose the other
// temp order.  Result: 903/903 bytes exact; line-compare has no direction
// divergence.  Rules 28a / 107 / 115 and observed-source-style §0.
void set_route_elastic_range(int r)
{
    int x_span;
    int y_min;
    unsigned char n_nw;
    unsigned char best;
    unsigned char n_sw;
    unsigned char saved;
    unsigned char n_w;
    int stride;
    unsigned char n_e;
    unsigned char t;
    unsigned char n_n;
    unsigned char n_ne;
    unsigned char cost;
    unsigned char n_se;
    int side;
    int x_min;
    unsigned char n_s;

    gmn_sptr = ((over_x) + (over_y) * 60) * 8;
    (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).place_state = 1;

    x_min = over_x - r;
    y_min = over_y - r;
    side  = 2 * r + 1;
    x_span = side;
    if (x_min <= 0) {
        x_span += x_min;
        x_min = 0;
    } else if (x_min + side > 0x3c) {
        x_span -= x_min + side - 0x3c;
    }
    if (y_min <= 0) {
        side += y_min; y_min = 0;
    } else if (y_min + side >= 0x3c) {
        side -= y_min + side - 0x3c;
    }

    gmn_sptr = ((x_min) + (y_min) * 60) * 8;
    stride   = (0x3c - x_span) * 8;
    gmn_y = y_min;
    for ( ; gmn_y < y_min + side; gmn_y++, gmn_sptr += stride) {
        gmn_x = x_min;
        for ( ; gmn_x < x_min + x_span; gmn_x++, gmn_sptr += 8) {
            if ((*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).place_state == 0xff)
                continue;
            if ((*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).terrain & 0x11) {
                t = (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).base_kind;
                if (t < 0x93 || t > 0x96) {
                    (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).place_state = 0xff;
                    continue;
                }
            }
            if ((*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).terrain & 0x04) {
                if ((*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).occupant != 0 &&
                    (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).occupant != tracking_army) {
                    (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).place_state = 0xff;
                    continue;
                }
                cost = 2;
            } else if ((*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).terrain & 0x20) {
                cost = 1;
            } else {
                if ((*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).terrain & 0x02) {
                    (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).place_state = 0xff;
                    continue;
                }
                cost = 2;
            }

            saved = (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).place_state;
            n_n = n_e = n_s = n_w = n_ne = n_se = n_sw = n_nw = 0;
            best = 0xc7;
            if (gmn_y > 0)
                n_n = (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr - 480))).place_state;
            if (gmn_x < 0x3b)
                n_e = (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr + 8))).place_state;
            if (gmn_y < 0x3b)
                n_s = (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr + 480))).place_state;
            if (gmn_x > 0)
                n_w = (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr - 8))).place_state;
            if (gmn_y > 0 && gmn_x < 0x3b)
                n_ne = (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr - 472))).place_state;
            if (gmn_x < 0x3b && gmn_y < 0x3b)
                n_se = (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr + 488))).place_state;
            if (gmn_y < 0x3b && gmn_x > 0)
                n_sw = (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr + 472))).place_state;
            if (gmn_x > 0 && gmn_y > 0)
                n_nw = (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr - 488))).place_state;
            if (n_n != 0 && n_n != 0xff && n_n < best)
                best = n_n;
            if (n_e != 0 && n_e != 0xff && n_e < best)
                best = n_e;
            if (n_s != 0 && n_s != 0xff && n_s < best)
                best = n_s;
            if (n_w != 0 && n_w != 0xff && n_w < best)
                best = n_w;
            if (n_ne != 0 && n_ne != 0xff && n_ne < best)
                best = n_ne;
            if (n_se != 0 && n_se != 0xff && n_se < best)
                best = n_se;
            if (n_sw != 0 && n_sw != 0xff && n_sw < best)
                best = n_sw;
            if (n_nw != 0 && n_nw != 0xff && n_nw < best)
                best = n_nw;
            {
                int value;
                value = best;
                if (cost + value < saved) {
                    n_sw = best + cost;
                    (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).place_state = n_sw;
                } else if (saved == 0 && best != 0) {
                    n_sw = best + cost;
                    (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).place_state = n_sw;
                }
            }
        }
    }
}

// FUNCTION: C2 0x6EE0B
// WIN: 0x004adcc4
// Lines 4187–4241
//
// Steepest-descent route reconstruction on region_map.
// Called from show_latest_route after
// set_route_elastic_range has filled cm[+2] of each
// region-map cell with the BFS distance from the chosen
// start.  Walks back from (over_x, over_y) by repeatedly
// stepping into the 8-neighbour with the smallest non-zero
// slot < the current cell's slot, accumulating the visited
// (x, y) into temp_route.  Stops when the best neighbour
// reaches slot 1 (= the start), or after 1000 iterations
// without progress (safety).
//
// Neighbour read order — cardinals first, diagonals after
// — with ties broken by visit order: N, E, S, W, NE, SE,
// SW, NW.  The chosen direction’s (dx, dy) is read from
// gmn_ofsets[dir*2] / [dir*2+1] (signed bytes).  Each
// visited cell gets region_map[(+3)] |= 0x40 to mark it on
// the path.
//
// The accumulated path is reversed into
// army_routes[player*0x15A + this_route*0x20 + 0x1A + i*2]
// (x at +0x1A, y at +0x1B per step) and the step count
// stored at army_routes[player*0x15A + this_route + 0x10].
// player = army_list[tracking_army*0xAF + 0x28] (signed).
//
// BYTE-EXACT 2026-07-12 (57bd -> 0; line-compare clean 43/43).
// POSTMORTEM -- three load-bearing recoveries, in order:
// (1) The memset init is the CHAINED `temp_route[i].x =
//     temp_route[i].y = 0;` (the CAESAR2.EXE /Od witness: store .y,
//     re-read .y, store .x).  It births a sav=70 i-index temp that
//     conflicts with idx and takes EBX first, which is the ONLY thing
//     that seats idx in ECX (idx is a list-order tie over {EBX,ECX};
//     with the split init nothing masks EBX and NO savings/credit/
//     order edit can -- certified exhaustively via c2 savings --flip
//     both directions).  Earlier sessions dismissed this form on the
//     raw island count ('ir 1->12') and missed that first-diff moved
//     +0xa -> +0x8c (Hard Rule #3).
// (2) The decl order (n_se/dir/n_w/n_s/n_ne/iters/best/i/n_sw tail,
//     found by c2 sweep) steers the sav=50 ShellSort group back onto
//     PS's byte seats (n_s=BL, n_e=BH, n_ne=AH) after the new
//     conflict changed the group permutation.
// (3) The neighbour zeroing is TWO chained statements on one line:
//     `n_n = n_w = n_se = n_ne = n_sw = n_nw = 0; n_e = n_s = 0;`
//     -- the mem-var chain flows through BL and the separate
//     n_e/n_s chain places the xor bh AFTER the n_nw store (single
//     8-var chains and 8 split statements all canonicalize to the
//     xor-hoisted form; the 6+2 split is load-bearing).  best = orig
//     sits AFTER the zeroing (its win-witnessed 'before' position was
//     only right for the split-init landscape).
// Statement packing (memset one-liner, guard+body one-liners,
// gmn_x/gmn_y one line, 6+2 zero line) matches the -d1 stream
// exactly.  MSVC /Od canonicalizes `a < b` == `b > a`, so the mixed
// compare-arm forms are win-consistent; WIN's `idx >= i` loop guard
// is a port artifact (DOS emits jle from `i <= idx`).
void trace_back_route_elastic(void)
{
    unsigned char orig;
    int idx;
    unsigned char n_n;
    unsigned char n_nw;
    unsigned char n_e;
    unsigned char n_se;
    unsigned char dir;
    unsigned char n_w;
    unsigned char n_s;
    unsigned char n_ne;
    int iters;
    unsigned char best;
    int i;
    unsigned char n_sw;

    idx   = 0;
    iters = 0;
    for (i = 0; i < 16; i++) temp_route[i].x = temp_route[i].y = 0;

    gmn_x = over_x; gmn_y = over_y;
    gmn_sptr = ((gmn_x) + (gmn_y) * 60) * 8;
    temp_route[idx].x = gmn_x;
    temp_route[idx].y = gmn_y;

    while (++iters < 1000) {
        orig = ((unsigned char *)region_map)[gmn_sptr + 2];
        n_n = n_w = n_se = n_ne = n_sw = n_nw = 0; n_e = n_s = 0;
        best = orig;
        if (gmn_y > 0) n_n = ((unsigned char *)region_map)[gmn_sptr - 0x1de];
        if (gmn_x < 0x3b) n_e = ((unsigned char *)region_map)[gmn_sptr + 0xa];
        if (gmn_y < 0x3b) n_s = ((unsigned char *)region_map)[gmn_sptr + 0x1e2];
        if (gmn_x > 0) n_w = ((unsigned char *)region_map)[gmn_sptr - 6];
        if (gmn_y > 0 && gmn_x < 0x3b) n_ne = ((unsigned char *)region_map)[gmn_sptr - 0x1d6];
        if (gmn_x < 0x3b && gmn_y < 0x3b) n_se = ((unsigned char *)region_map)[gmn_sptr + 0x1ea];
        if (gmn_y < 0x3b && gmn_x > 0) n_sw = ((unsigned char *)region_map)[gmn_sptr + 0x1da];
        if (gmn_x > 0 && gmn_y > 0) n_nw = ((unsigned char *)region_map)[gmn_sptr - 0x1e6];

        if (n_n  != 0 && best > n_n) { best = n_n;  dir = 0; }
        if (n_e  != 0 && n_e  < best) { best = n_e;  dir = 2; }
        if (n_s  != 0 && n_s  < best) { best = n_s;  dir = 4; }
        if (n_w  != 0 && n_w  < best) { best = n_w;  dir = 6; }
        if (n_ne != 0 && n_ne < best) { best = n_ne; dir = 1; }
        if (n_se != 0 && n_se < best) { best = n_se; dir = 3; }
        if (n_sw != 0 && n_sw < best) { best = n_sw; dir = 5; }
        if (n_nw != 0 && best > n_nw) { best = n_nw; dir = 7; }

        if (orig != best) {
            gmn_x += gmn_ofsets[dir].dx;
            gmn_y += gmn_ofsets[dir].dy;
            idx++;
            temp_route[idx].x = gmn_x;
            temp_route[idx].y = gmn_y;
            if (best == 1) break;
            gmn_sptr = ((gmn_x) + (gmn_y) * 60) * 8;
            (*(struct region_cell *)((unsigned char *)region_map + (gmn_sptr))).edge_bits |= 0x40;
        }
    }

    for (i = 0; i <= idx; i++) {
        army_routes[army_list[tracking_army].cohort_id]
            .points[this_route_number][i].x = temp_route[idx - i].x;
        army_routes[army_list[tracking_army].cohort_id]
            .points[this_route_number][i].y = temp_route[idx - i].y;
    }
    army_routes[army_list[tracking_army].cohort_id]
        .row_len[this_route_number] = (unsigned char)idx + 1;
}

// FUNCTION: C2 0x6F0FA
// WIN: 0x004ae1a9
// Lines 4245–4256
//
// Reset every flag-marker subsystem (city / province / danger).
// Zeros all the count + cursor + decay scalars, then fills the
// three 20-entry int arrays with -1 (fill loops; Watcom lowers
// each to `call __STOSD`).
void init_flag_markers(void)
{
    int i;

    flag_mode = 0;
    flag_mode_decay_count = 0;
    danger_flag_map_mode = 0;
    no_of_danger_flags = 0;
    no_of_prov_flags = 0;
    no_of_city_flags = 0;
    last_danger_flag = 0;
    last_prov_flag = 0;
    last_city_flag = 0;
    for (i = 0; i < 0x14; i++)
        city_flag_list[i] = -1;
    for (i = 0; i < 0x14; i++)
        prov_flag_list[i] = -1;
    for (i = 0; i < 0x14; i++)
        danger_flag_list[i] = -1;
}

// FUNCTION: C2 0x6F173
// WIN: 0x004ae2e2  (unverified)
// Lines 4258–4263
//
// Count active entries (≠ -1) in city_flag_list.
void count_city_flags(void)
{
    int i;
    no_of_city_flags = 0;
    for (i = 0; i < 0x14; i++) {
        if (city_flag_list[i] != -1)
            no_of_city_flags++;
    }
}

// FUNCTION: C2 0x6F196
// WIN: 0x004ae32f  (unverified)
// Lines 4265–4270
//
// Count active entries (≠ -1) in prov_flag_list.
void count_prov_flags(void)
{
    int i;
    no_of_prov_flags = 0;
    for (i = 0; i < 0x14; i++) {
        if (prov_flag_list[i] != -1)
            no_of_prov_flags++;
    }
}

// FUNCTION: C2 0x6F1B9
// WIN: 0x004ae37c
// Lines 4279–4286
//
// If `val` is in city_flag_list, clear it and return 1.
// Otherwise route to put_city_flag and return 1 on hit, 0
// otherwise.
int toggle_city_flag(int val)
{
    int i;
    for (i = 0; i < 0x14; i++) {
        if (val == city_flag_list[i]) {
            clear_city_flag(val);
            return 1;
        }
    }
    if (put_city_flag(val)) return 1;
    return 0;
}

// FUNCTION: C2 0x6F1ED
// WIN: 0x004ae3f6
// Lines 4288–4295
//
// Mirror of toggle_city_flag for prov_flag_list.
int toggle_prov_flag(int val)
{
    int i;
    for (i = 0; i < 0x14; i++) {
        if (val == prov_flag_list[i]) {
            clear_prov_flag(val);
            return 1;
        }
    }
    if (put_prov_flag(val)) return 1;
    return 0;
}

// FUNCTION: C2 0x6F221
// WIN: 0x004ae470  (unverified)
// Lines 4298–4315
//
// Insert `val` (a cm_ptr) into the next free slot of
// city_flag_list[20], starting the search from last_city_flag+1
// (wrapping at 20).  Returns 1 on insert, 0 if the list is full
// (no_of_city_flags >= 20) or no free slot was found in 20
// attempts.  Special-cases val == danger_flag_list[0]: returns
// 1 immediately without inserting.  Sets city_map[val/20].
// road_aqueduct = 1 to mark the cell as flagged.
int put_city_flag(int val)
{
    int i;

    count_city_flags();
    if (val == danger_flag_list[0]) return 1;
    if (no_of_city_flags >= 0x14) return 0;
    for (i = 0; i < 0x14; i++) {
        last_city_flag++;
        if (last_city_flag >= 0x14) last_city_flag = 0;
        if (city_flag_list[last_city_flag] == -1) {
            city_flag_list[last_city_flag] = val;
            (*(struct city_cell *)((unsigned char *)city_map + (val))).road_aqueduct = 1;
            return 1;
        }
    }
    return 0;
}

// FUNCTION: C2 0x6F290
// WIN: 0x004ae529  (unverified)
// Lines 4317–4334
//
// Sister of put_city_flag for the region map: inserts `val`
// into prov_flag_list[20], cycling last_prov_flag, marking
// region_map[(val/20)].+0x2 = 1.  Same special-case for
// danger_flag_list[0].
int put_prov_flag(int val)
{
    int i;

    count_prov_flags();
    if (val == danger_flag_list[0]) return 1;
    if (no_of_prov_flags >= 0x14) return 0;
    for (i = 0; i < 0x14; i++) {
        last_prov_flag++;
        if (last_prov_flag >= 0x14) last_prov_flag = 0;
        if (prov_flag_list[last_prov_flag] == -1) {
            prov_flag_list[last_prov_flag] = val;
            (*(struct region_cell *)((unsigned char *)region_map + (val))).place_state = 1;
            return 1;
        }
    }
    return 0;
}

// FUNCTION: C2 0x6F2FF
// WIN: 0x004ae5e2
// Lines 4336–4339
//
// Latch a single danger flag at slot 0 of danger_flag_list and
// reset the cursor.  Always returns 1.
int put_danger_flag(int val)
{
    danger_flag_list[0] = val;
    last_danger_flag = 0;
    return 1;
}

// FUNCTION: C2 0x6F312
// WIN: 0x004ae609
// Lines 4343–4353
//
// Clear every city_flag_list slot whose value matches `val`,
// also wiping the road/aqueduct byte (+0x02) of the
// corresponding city_map cell, then refresh the running flag
// count.  Loop scans the full 20-entry table without an
// early-out so duplicate entries are all cleared.
//
void clear_city_flag(int val)
{
    int i;
    for (i = 0; i < 0x14; i++) {
        if (city_flag_list[i] == val) {
            city_flag_list[i] = -1;
            (*(struct city_cell *)((unsigned char *)city_map + (val))).road_aqueduct = 0;
        }
    }
    count_city_flags();
}

// FUNCTION: C2 0x6F34C
// WIN: 0x004ae665
// Lines 4355–4365
//
// Mirror of clear_city_flag for prov_flag_list / region_map.
void clear_prov_flag(int val)
{
    int i;
    for (i = 0; i < 0x14; i++) {
        if (prov_flag_list[i] == val) {
            prov_flag_list[i] = -1;
            (*(struct region_cell *)((unsigned char *)region_map + (val))).place_state = 0;
        }
    }
    count_prov_flags();
}

// FUNCTION: C2 0x6F386
// WIN: 0x004ae6c1
// Lines 4367–4367
//
// Clear the (single) danger flag slot, then recount (a tail call to the
// immediately-following count_danger_flags, which Watcom elides to a
// fall-through -- PS's clear_danger_flag is 10 B with no ret).
void clear_danger_flag(void)
{
    danger_flag_list[0] = -1;
    count_danger_flags();
}

// FUNCTION: C2 0x6F390
// WIN: 0x004ae295  (unverified)
// Lines 4370–4370
//
// Count active entries (≠ -1) in danger_flag_list.
void count_danger_flags(void)
{
    int i;
    no_of_danger_flags = 0;
    for (i = 0; i < 0x14; i++) {
        if (danger_flag_list[i] != -1)
            no_of_danger_flags++;
    }
}

// FUNCTION: C2 0x6F3B3
// WIN: 0x004ae761
// Lines 4374–4385
//
// Cycle the "selected city flag" pointer forward to the next
// valid (i.e. non-empty) entry in city_flag_list.  Returns 1
// if a valid flag was found, 0 if the list is empty after the
// recount.
int next_city_flag(void)
{
    int i;

    count_city_flags();
    if (no_of_city_flags <= 0) return 0;
    for (i = 0; i < 0x14; i++) {
        last_city_flag++;
        if (last_city_flag >= 0x14) last_city_flag = 0;
        if (city_flag_list[last_city_flag] != -1) return 1;
    }
    return 0;
}

// FUNCTION: C2 0x6F405
// WIN: 0x004ae7e7
// Lines 4387–4398
//
// Cycle the "selected province flag" pointer forward to the next
// valid entry in prov_flag_list.  Returns 1 on success, 0 when the
// list is empty.
int next_prov_flag(void)
{
    int i;

    count_prov_flags();
    if (no_of_prov_flags <= 0) return 0;
    for (i = 0; i < 0x14; i++) {
        last_prov_flag++;
        if (last_prov_flag >= 0x14) last_prov_flag = 0;
        if (prov_flag_list[last_prov_flag] != -1) return 1;
    }
    return 0;
}

// FUNCTION: C2 0x6F457
// WIN: 0x004ae6db
// Lines 4400–4411
//
// Cycle the "selected danger flag" cursor forward to the next
// active danger marker.  Returns 1 on success, 0 when the list is
// empty.
int next_danger_flag(void)
{
    int i;

    count_danger_flags();
    if (no_of_danger_flags <= 0) return 0;
    for (i = 0; i < 0x14; i++) {
        last_danger_flag++;
        if (last_danger_flag >= 0x14) last_danger_flag = 0;
        if (danger_flag_list[last_danger_flag] != -1) return 1;
    }
    return 0;
}

// FUNCTION: C2 0x6F4A9
// WIN: 0x004ae86d
// Lines 4413–4439
//
// Switch the UI into flag-marker mode (used by the city- and
// province-level alert overlays).  Sets flag_mode = 1, blanks
// the city + region maps for layer 2 ("flag overlay"), then
// repaints up to 20 city flags (elastic = 1), 20 province flags
// (elastic = 2), and 20 "danger" flags (elastic = 3 on city or
// region map depending on `danger_flag_map_mode`).  Each *_list
// slot is `-1` when unused.
//
// Source-shape lever: each `if (X[i] != -1)` block stores the
// indexed value into a single function-scope `int p` before the
// store, then references `p`.  Sharing one `p` across the three
// blocks evicts `i` from EAX (p sav > i sav) so PS's i->EDX falls
// out naturally; the per-block `p = X[i];` statements also recover
// the L4425/L4435 line marks PS emits between the cmp/je and the
// CM_CELL/RM_CELL store.
void goto_flag_marker_mode(void)
{
    int i;
    int p;

    flag_mode = 1;
    clear_all_cm(2);
    clear_all_rm(2);

    for (i = 0; i < 20; i++) {
        if (city_flag_list[i] != -1) {
            p = city_flag_list[i];
            (*(struct city_cell *)((unsigned char *)city_map + (p))).road_aqueduct = 1;
        }
        if (prov_flag_list[i] != -1) {
            p = prov_flag_list[i];
            (*(struct region_cell *)((unsigned char *)region_map + (p))).place_state = 2;
        }
        if (danger_flag_list[i] != -1) {
            p = danger_flag_list[i];
            if (danger_flag_map_mode == 0)
                (*(struct city_cell *)((unsigned char *)city_map + (p))).road_aqueduct = 3;
            else
                (*(struct region_cell *)((unsigned char *)region_map + (p))).place_state = 3;
        }
    }
}
