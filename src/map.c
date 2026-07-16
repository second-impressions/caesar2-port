#include "c2_data.h"

/* File-local map state. */
struct byte_point_rec temp_route[16];

extern void copy(unsigned char *src, unsigned char *dst, int n);

// Clear the city-map layers, seed scrub terrain, and generate the river layout.
// FUNCTION: C2 0x65f4c
// FUNCTION: C2WIN 0x0049f830
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

// Trace one river path across the 80×80 city_map. The path is a random walk biased to flow
// southward; each visited cell is flagged as a "river atom" (city_map[+1] |= 0x10 and city_map[+0]
// = 4) for the flesh_river_atoms pass to turn into concrete tiles.
// FUNCTION: C2 0x66014
// FUNCTION: C2WIN 0x0049f923
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

// Initial-state generator for the city map's scrub layer. Sets every cell's `base_kind` (byte 0)
// to a random scrub tile in 8..23 (8 + (rand128 & 0xf)).
// FUNCTION: C2 0x6623d
// FUNCTION: C2WIN 0x0049fc8b
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

// Replace every flagged river atom with the concrete river tile selected by its terrain pattern.
// FUNCTION: C2 0x66281
// FUNCTION: C2WIN 0x0049fd08
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

// BFS layer pass for the city-map elastic preview. Called from get_road_elastic, get_wall_elastic
// and get_aquaduct_elastic with r = 1, 2, 3, … to expand the candidate-slot stamp (city_map[+2])
// outward from (act_start_x, act_start_y) one ring at a time.
// FUNCTION: C2 0x663ab
// FUNCTION: C2WIN 0x0049febf
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

// Among the four neighbouring city-map cells around byte offset `ptr`, pick the non-zero elastic
// byte (+2) with the lowest value, respecting map bounds. Search starts at `dirc` and wraps
// through all directions; results are published in best_elastic_value/best_elastic_dirc.
// FUNCTION: C2 0x666a4
// FUNCTION: C2WIN 0x004a03c4
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

// BFS layer pass for the region-map elastic preview; region-map twin of test_elastic_range. Called
// from get_reg_road_elastic with strict=0 and from get_reg_wall_elastic with strict=1, both with
// reject_mask = 0xD9.
// FUNCTION: C2 0x6675a
// FUNCTION: C2WIN 0x004a0576
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

// Pick the cheapest non-wall, non-blocking neighbour (slot byte +2) in the four cardinal
// directions starting from `dirc` and rotating through all four. Region-map sister of
// get_best_elastic_value; publishes best_elastic_value / best_elastic_dirc.
// FUNCTION: C2 0x66a53
// FUNCTION: C2WIN 0x004a0a83
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

// Grow and transform the elastic road preview from the current construction start cell.
// FUNCTION: C2 0x66b05
// FUNCTION: C2WIN 0x004a0c35
void get_road_elastic(void)
{
    int i;

    set_range(act_start_x, act_start_y, 0x15, 2, 0);
    (*(struct city_cell *)((unsigned char *)city_map + (act_start_pm_ptr))).road_aqueduct = 1;
    for (i = 1; i <= 20; i++)
        test_elastic_range(i, 9);
    transform_road_elastic(20);
}

// City-map twin of transform_reg_road_elastic. Marks cells of city_map inside a radius-r square
// around (act_start_x, act_start_y) as candidate road tiles (city_map[+2] = 0xFF) when their
// terrain + edge mask match the city-road criteria.
// FUNCTION: C2 0x66b56
// FUNCTION: C2WIN 0x004a0c9f
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

// Commit the player-drawn city road. City-map twin of build_reg_road_from_elastic; operates on the
// elastic preview marks left by transform_road_elastic on the 80×80 city_map (20-byte cells).
// FUNCTION: C2 0x66d22
// FUNCTION: C2WIN 0x004a0f4e
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

// Recompute road sprites in the clamped 3x3 neighbourhood around (x,y).
// FUNCTION: C2 0x67109
// FUNCTION: C2WIN 0x004a1612
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

// Wall sister of get_road_elastic / get_aquaduct_elastic. Pre-grow elastic for wall construction
// at (act_start_x, act_start_y).
// FUNCTION: C2 0x67333
// FUNCTION: C2WIN 0x004a1998
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

// City-map wall preview pass (twin of transform_aquaduct_elastic and transform_reg_wall_elastic).
// Walks the clipped 80×80 bounding box of radius r around (act_start_x, act_start_y) and stamps
// the candidate-wall byte (city_map[+2]) based on terrain + edge mask.
// FUNCTION: C2 0x673a8
// FUNCTION: C2WIN 0x004a1a34
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

// Walks an elastic-wall placement preview to its final cells. Two-pass: first pass marks each
// preview cell, second pass calls wall_ramifications() at each step.
// FUNCTION: C2 0x67653
// FUNCTION: C2WIN 0x004a1ee0
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

// Validate wall connections at (x, y) and across the 3×3 (or smaller, if at edges) neighbourhood.
// FUNCTION: C2 0x678bb
// FUNCTION: C2WIN 0x004a2251
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

// Re-evaluate the wall sprite for a single city-map cell at (gmn_x, gmn_y). Tests the cell's
// neighbour mask (via test_citymap_neighbours_negedge) and picks a sprite id from the wall-data
// table; returns 0 when no valid wall sprite is available.
// FUNCTION: C2 0x67944
// FUNCTION: C2WIN 0x004a2362
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

// Aqueduct sister of get_road_elastic. Pre-grow elastic for aqueduct construction at (act_start_x,
// act_start_y).
// FUNCTION: C2 0x67c23
// FUNCTION: C2WIN 0x004a2894
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

// City-map aqueduct twin of transform_road_elastic. Walks the clipped 80×80 bounding box of radius
// r around (act_start_x, act_start_y) and marks each cell's candidate-aquaduct byte (city_map[+2])
// based on terrain + edge mask.
// FUNCTION: C2 0x67c75
// FUNCTION: C2WIN 0x004a292d
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

// Commit the player-drawn aqueduct: walks the elastic preview marks left by
// transform_aquaduct_elastic outward from the drag-end (over_x, over_y, pm_over_cm_ptr) in two
// phases.
// FUNCTION: C2 0x67f13
// FUNCTION: C2WIN 0x004a2d9f
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

// Validate aqueduct connections at (x, y) and across the 3×3 (or smaller, if at edges)
// neighbourhood. Calls `one_aquaduct_ramification()` (which reads gmn_x/gmn_y globals) for the
// center cell first; returns 0 immediately if the center cell is not a valid aqueduct connection.
// FUNCTION: C2 0x6811e
// FUNCTION: C2WIN 0x004a30d6
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

// Re-evaluate one cell of an aquaduct preview: re-anchors via get_aqua_web when the cell isn't on
// an existing aquaduct, then reads the surrounding neighbour mask and writes a matching sprite id.
// FUNCTION: C2 0x681ad
// FUNCTION: C2WIN 0x004a31e8
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

// Region-map sister of get_road_elastic. Pre-grow elastic for inter-province road construction at
// (act_start_x, act_start_y).
// FUNCTION: C2 0x68472
// FUNCTION: C2WIN 0x004a36d5
void get_reg_road_elastic(void)
{
    int i;

    set_rm_range(act_start_x, act_start_y, 0x15, 2, 0);
    (*(struct region_cell *)((unsigned char *)region_map + (act_start_pm_ptr))).place_state = 1;
    for (i = 1; i <= 20; i++)
        test_rm_elastic_range(1, i, 0xd9);
    transform_reg_road_elastic(20);
}

// Mark the cells of region_map inside a radius-r square around (act_start_x, act_start_y) as
// candidate road tiles (region_cell[+2] = 0xFF) when their terrain + edge mask match the
// regional-road criteria.
// FUNCTION: C2 0x684c8
// FUNCTION: C2WIN 0x004a3744
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

// Commit the player-drawn region road. Operates on the elastic preview marks left by
// transform_reg_road_elastic on region_map; runs a two-phase neighbour-pick walker that follows
// decreasing-slot values from the drag-end (over_x, over_y, pm_over_cm_ptr) toward 0.
// FUNCTION: C2 0x68654
// FUNCTION: C2WIN 0x004a39b8
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

// Recompute regional road sprites in the clamped 3×3 neighbourhood around (x,y). Wall/road
// crossings are delegated to one_reg_wall_ramification; plain road cells choose a road sprite from
// their positive-edge neighbours.
// FUNCTION: C2 0x688bb
// FUNCTION: C2WIN 0x004a3eb6
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

// Region-map sister of get_wall_elastic. Same shape: prime the elastic preview range via
// set_rm_range, mark the start cell, sweep test_rm_elastic_range over 20 segments, transform to
// final wall, then de-saturate the start cell.
// FUNCTION: C2 0x689f6
// FUNCTION: C2WIN 0x004a40d4
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

// Region-map wall preview pass (twin of transform_aquaduct_elastic but on the 60×60 region grid
// with 8-byte cells). Walks the clipped bounding box of radius r around (act_start_x, act_start_y)
// and stamps the candidate-wall byte (region_cell[+2]) based on terrain + edge mask.
// FUNCTION: C2 0x68a6a
// FUNCTION: C2WIN 0x004a4172
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

// Commit the player-drawn region wall. Same get_best_rm_ elastic_value-driven walker shape as
// build_aquaduct_from_elastic but on the 60×60 region_map (8-byte cells) and with the wall mask
// bits.
// FUNCTION: C2 0x68c7c
// FUNCTION: C2WIN 0x004a450a
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

// Region-map sister of wall_ramifications: validate wall connections at (x, y) and across the 3×3
// (or smaller, if at edges) neighbourhood. Region map is 60×60, so edge clamp is against 59
// (=0x3b) instead of 79 (=0x4f).
// FUNCTION: C2 0x68ea5
// FUNCTION: C2WIN 0x004a4841
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

// Region-map twin of one_wall_ramification: re-evaluate one wall sprite at (gmn_x, gmn_y) on the
// 60x60 region grid. Returns 0 if no valid sprite, caching (gmn_err_x/y/sptr) for the caller.
// FUNCTION: C2 0x68f2e
// FUNCTION: C2WIN 0x004a4953
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

// Fill a city-map rectangle with random garden tiles while preserving stone and flagged cells.
// FUNCTION: C2 0x69093
// FUNCTION: C2WIN 0x004a4bca
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

// Convert every clearable city-map cell in the inclusive rectangle bounded by (x1,y1) and (x2,y2)
// to plaza paving. Existing occupied structures (base_kind >= 0x1e), blocked terrain, and hard
// edges are left alone; if nothing was paved, mark the attempted build illegal.
// FUNCTION: C2 0x6921c
// FUNCTION: C2WIN 0x004a4dd7
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

// Clear/demolish every city-map cell in an inclusive rectangle.
// FUNCTION: C2 0x69344
// FUNCTION: C2WIN 0x004a4fa8
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

// Demolish a region-map rectangle while preserving protected forts and occupied army ranges.
// FUNCTION: C2 0x695b9
// FUNCTION: C2WIN 0x004a536b
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

// Clear one region-map atom at byte offset `sptr`, handling sized industry/port footprints and
// recalculating coast/road/wall side effects. This is the single-cell companion to
// clear_a_reg_area.
// FUNCTION: C2 0x697e7
// FUNCTION: C2WIN 0x004a564b
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

// Destroy one city-map atom, clear its footprint correctly, and refresh nearby aqueduct links.
// FUNCTION: C2 0x69907
// FUNCTION: C2WIN 0x004a57bd
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

// Directional fire-spread wrapper. Adjust the city_map byte offset by dir (0 north, 4 south, 6
// west, 2 east), skip protected ids 0xbc..0xe2, then dispatch by forum_gfxdat size class: 4 -> 2x2
// rubble, 9 -> 3x3, 0x10 -> 4x4, otherwise one cell.
// FUNCTION: C2 0x699d7
// FUNCTION: C2WIN 0x004a590a
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

// Directional wrapper around plague_an_atom: move the supplied city_map byte offset one cell
// north/south/west/east depending on dir (0,4,6,2 respectively), then plague the target building
// unless its edge_bits high bit is set.
// FUNCTION: C2 0x69a77
// FUNCTION: C2WIN 0x004a5a2b
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

// Plague-mark a building footprint based on the cell at byte-offset `sptr`.
// FUNCTION: C2 0x69afe
// FUNCTION: C2WIN 0x004a5b27
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

// Spread plague across the full `size` by `size` building footprint containing `sptr`.
// FUNCTION: C2 0x69b4b
// FUNCTION: C2WIN 0x004a5bc7
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

// Rubble-clear a size×size city building. The sub-tile index in activity_a (+5) identifies the
// clicked cell within the footprint; walk back to the top-left, rubble every cell, then handle
// linked 2×2 gatehouse halves (base kinds 0xe9..0xf0) by clearing the paired footprint as well.
// FUNCTION: C2 0x69bc6
// FUNCTION: C2WIN 0x004a5c9a
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
    xoff = n % size; yoff = n / size;

    sptr -= xoff * 20;
    sptr -= yoff * 1600;
    start = sptr;

    for (y = 0; y < size; y++, sptr += (80 - size) * 20)
        for (x = 0; x < size; x++, sptr += 20)
            clear_to_rubble(sptr, rubble_kind);

    if (old_kind < 0xe9) return;
    if (old_kind > 0xf0) return;

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

// Turn one city cell into rubble/smoke. rubble_kind selects fire rubble: set the high edge bit,
// seed smoke animation bytes, and play fire.wav.
// FUNCTION: C2 0x69e2b
// FUNCTION: C2WIN 0x004a602f
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

// Clear a single cell at byte-offset `sptr` to an "empty" scrub tile. Bumps the global
// stone_random_count (with wrap at 0x40); if the cell's old base_kind was outside the scrub range
// [0x1a, 0x1d], increments particles_cleared.
// FUNCTION: C2 0x69f41
// FUNCTION: C2WIN 0x004a6183
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

// Reset a city-map cell to its clean basic-terrain state.
// FUNCTION: C2 0x69f9e
// FUNCTION: C2WIN 0x004a6203
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

// Find the top-left of a sized (size×size) building anchored at `rm_offset` and call
// clear_reg_basic on every cell of the block.
// FUNCTION: C2 0x6a018
// FUNCTION: C2WIN 0x004a633c
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

// Reset a region-map cell to a clean basic state, choosing a stone tile id based on terrain bits
// at byte +1: bit 0x40 set: tile = 0x18 + (random>>2) /* mountain */ bit 0x80 set: tile = 0x1c +
// (random>>2) /* mountain alt*/ else: tile.
// FUNCTION: C2 0x6a0a6
// FUNCTION: C2WIN 0x004a6430
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

// Mark cell at byte-offset `sptr` as plague-stricken. Strips fpu_flag low bits (& 0xc0), sets
// edge_bits 0x81 (on-road + extra), advances stone_random_count by rand8 (with wrap at 0x40),
// copies one byte of stone_random_data to extra_edge, and sets activity_b to plague-marker 0x0a.
// FUNCTION: C2 0x6a17a
// FUNCTION: C2WIN 0x004a6555
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

// Build/fill every legal city-map cell in the inclusive rectangle bounded by (x1,y1) and (x2,y2).
// Illegal cells are skipped rather than aborting the whole fill.
// FUNCTION: C2 0x6a1cb
// FUNCTION: C2WIN 0x004a6605
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

// Place a 1×1 city-map atom at (x,y). Rejects blocked / occupied cells, records the placement
// origin globals, counts built/cleared particles, stamps base_kind/placing_flags/color/edge bits,
// and clears the secondary image byte.
// FUNCTION: C2 0x6a341
// FUNCTION: C2WIN 0x004a683b
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

// Stamp a 2x2 square on city_map starting at the placement anchor. Rotates the anchor by
// map_direction, validates the 4 cells are empty, then writes base_kind / edge_bits / color +
// diamond_ofsets_2x[n].
// FUNCTION: C2 0x6a43f
// FUNCTION: C2WIN 0x004a6a13
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

// Stamps a 3x3 building footprint onto the city map.
// FUNCTION: C2 0x6a669
// FUNCTION: C2WIN 0x004a6d79
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

// Sister of put_x2_area for a 4x4 square; uses diamond_ofsets_4x[n] for the per-cell color offset.
// FUNCTION: C2 0x6a889
// FUNCTION: C2WIN 0x004a70e7
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

// Stamp a square (1×1, 2×2, 3×3, or 4×4) on the city map starting at byte-offset `sptr`, writing
// `bk` to base_kind and computing the upper sprite (extra_edge) from `color` plus the
// size-specific diamond offset table (`diamond_ofsets_Nx[n]`).
// FUNCTION: C2 0x6aaab
// FUNCTION: C2WIN 0x004a7455
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

// Mark a directed size×size placement footprint on city_map. The visible anchor (x,y) is shifted
// according to map_direction so the footprint extends in the direction the cursor/building preview
// faces, then every covered city cell has edge_bits bit0 set.
// FUNCTION: C2 0x6ab34
// FUNCTION: C2WIN 0x004a7573
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

// Region-map 1×1 placement. `strict_flags` selects the occupancy check used by region industry
// placement: when true, only the low six flag bits block; otherwise any flag byte blocks.
// FUNCTION: C2 0x6ac09
// FUNCTION: C2WIN 0x004a76d5
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

// Region-map sister of put_x2_area: stamp a 2x2 square of region_map cells. `strict_flags` selects
// the occupancy check (when true, only low 6 flag bits block; otherwise any flag blocks).
// FUNCTION: C2 0x6acd1
// FUNCTION: C2WIN 0x004a7852
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

// Stamp a `size × size` square (size ∈ {1, 2, 3, …}) of region-map cells starting at byte-offset
// `rm_offset` from `region_map`. Every cell gets: +0 = (char)rm_byte // base value (e.g.
// FUNCTION: C2 0x6aeac
// FUNCTION: C2WIN 0x004a7b37
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

// Stamp an arbitrary size×size region-map square. Rejects cells with an occupant at +7, blocked
// bit 0x10, or low flag bit set; on success writes base_kind, placing flags, edge bits, and a
// size-dependent diamond/color byte.
// FUNCTION: C2 0x6af11
// FUNCTION: C2WIN 0x004a7c06
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

// OR mask_byte into the +1 terrain/flag byte of every region_map cell in a size×size square. The
// x/y origin is adjusted for map_direction so the square is anchored around the user-facing
// placement direction.
// FUNCTION: C2 0x6b08c
// FUNCTION: C2WIN 0x004a7ec5
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

// AND mask_byte into the +1 (terrain bits) byte of every region_map cell in the size x size square
// at (x, y). No-op if (x < 0) or (y < 0).
// FUNCTION: C2 0x6b126
// FUNCTION: C2WIN 0x004a7fd4
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

// Validate that a 2×2 region industry footprint overlaps exactly four cells with the requested
// terrain flag (farm/mine/quarry masks). The footprint anchor is rotated like other 2×2 region
// placements.
// FUNCTION: C2 0x6b18c
// FUNCTION: C2WIN 0x004a808c
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

// Validate a 2×2 port footprint: at least one covered tile must have a coast neighbour on its
// negative edge. On success, industry_build_ok is cleared; otherwise illegal_build is set.
// FUNCTION: C2 0x6b26d
// FUNCTION: C2WIN 0x004a81d2
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

// Re-evaluate coast tiles in a clipped region rectangle. For every water/coast candidate, compute
// neighbour bits, choose a matching coast sprite, and update the impassable/coast flag from
// coast_data.
// FUNCTION: C2 0x6b347
// FUNCTION: C2WIN 0x004a8311
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

// Sweep the 60x60 region_map grid. For cells whose +1 flag has bit 0x08 set, check the base tile
// byte against coast_data+0x220; if that coast-data byte is non-zero (and base < 0x7c), clear bit
// 0x10 in the same +1 flag.
// FUNCTION: C2 0x6b474
// FUNCTION: C2WIN 0x004a84fc
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

// Read the 8-neighbour mask of (gmn_x, gmn_y) on city_map into the gmn[0..7] array plus the
// various counters (gmn_count / polar / ns / ew / nesw / nwse / density / max_run).
// FUNCTION: C2 0x6b4f3
// FUNCTION: C2WIN 0x004a85d6
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

// Sister of test_citymap_neighbours_posedge with the opposite off-map convention: cells off the
// grid count as `0` (negative edge: "absent" outside the map).
// FUNCTION: C2 0x6b814
// FUNCTION: C2WIN 0x004a89f2
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

// Type-variant: edge sets gmn[i]=0 + decrements counter; non-edge computes byte^type (0 = match).
// Second pass: if (gmn[i] == 0) promote to 1 and increment counters; else gmn[i] = 0.
// FUNCTION: C2 0x6bb01
// FUNCTION: C2WIN 0x004a8dde
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

// Type-variant negedge: edge sets gmn[i]=1 (sentinel that fails the match-test below); non-edge
// computes byte^type. Second pass gates on `gmn[i] == 0`: match → promote to 1 + inc; else →
// gmn[i] = 0.
// FUNCTION: C2 0x6beb5
// FUNCTION: C2WIN 0x004a9272
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

// Region-map sister of test_citymap_neighbours_posedge on the 60x60 region grid. Off-map cells
// count as `1`.
// FUNCTION: C2 0x6c22e
// FUNCTION: C2WIN 0x004a96d6
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

// Region-map sister of test_citymap_neighbours_negedge on the 60x60 region grid. Off-map cells
// count as `0`.
// FUNCTION: C2 0x6c54f
// FUNCTION: C2WIN 0x004a9af2
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

// Tests type regionmap neighbours posedge and returns the result.
// FUNCTION: C2 0x6c83c
// FUNCTION: C2WIN 0x004a9ede
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

// Sister of test_type_regionmap_neighbours_posedge: off-map cells count as `1` (treated as
// "matching").
// FUNCTION: C2 0x6cbf0
// FUNCTION: C2WIN 0x004aa372
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

// Walk `records` (8-slot match arrays + value + counter) and find the first record whose 8 match
// bits agree with the global gmn[] (skip-2 slots are wildcards, 1 needs gmn[i] != 0, 0 needs
// gmn[i] == 0).
// FUNCTION: C2 0x6cf69
// FUNCTION: C2WIN 0x004aa7d6
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

// Clear the "selected" byte (offset 11) of every entry in a 12-byte-strided choice array. Used to
// reset selection state on UI panels with a chooser list.
// FUNCTION: C2 0x6cfed
// FUNCTION: C2WIN 0x004aa8fd
void init_choices(struct choice_rec *arr, int count)
{
    int i;
    for (i = 0; i < count; i++, arr++)
        arr->counter = 0;
}

// Toggle every byte in gmn[0..16): 0 ↔ 1.
// FUNCTION: C2 0x6d002
void invert_gmn(void)
{
    int i;
    for (i = 0; i < 16; i++) {
        gmn[i] = (gmn[i] == 0);
    }
}

// Region-map sibling of ``clear_all_cm``. Region cells are 8 bytes each and the grid is 60×60.
// FUNCTION: C2 0x6d01e
// FUNCTION: C2WIN 0x004aaa92
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

// Battle-map sister of clear_all_cm: zero the byte at offset `layer` inside every cell of the
// 52×52 battle_map (cell stride 4 bytes, not 20). 4 byte-stores per inner iter × 13 inner iters ×
// 52 outer iters = 2704 cells = full battle_map.
// FUNCTION: C2 0x6d0b7
// FUNCTION: C2WIN 0x004aabba
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

// Walk the entire 80×80 city map and AND `mask` into a single byte field (at byte-offset
// `field_off` within each cell). Used to clear flag bits across the whole map (e.g.
// FUNCTION: C2 0x6d12c
// FUNCTION: C2WIN 0x004aac70
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

// Sister of \`unflag_all_cm\` for the 60×60 region map. Cells are 8 bytes wide; inner loop
// unrolled 10 cells wide (gmn_x < 6 × 10 = 60 cells per row).
// FUNCTION: C2 0x6d1b7
// FUNCTION: C2WIN 0x004aae45
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

// 60×60 region-map sweep that strips the upper 2 bits of the `+3` flags byte on every cell whose
// `+0` rm_byte is *not* 0xd4 (warehouse marker). Inner loop unrolled 4 cells wide (gmn_x < 15 × 4
// = 60 cells per row).
// FUNCTION: C2 0x6d24b
// FUNCTION: C2WIN 0x004ab0be
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

// Fill a clipped city-map square centered at (x,y), writing `value` to byte field `field_off` for
// every covered cell. The side length is 2*range+1.
// FUNCTION: C2 0x6d309
// FUNCTION: C2WIN 0x004ab1f8
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

// Region-map sister of set_range. Writes ``kind_byte`` to byte offset ``field_offset`` within
// every region_map cell of a (2*half_width+1)×(2*half_width+1) square centred on (x, y), clamped
// to the 60×60 region grid.
// FUNCTION: C2 0x6d3ed
// FUNCTION: C2WIN 0x004ab344
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

// Apply `mask` to a square city-map field around `(x, y)`, publishing the current scan position.
// FUNCTION: C2 0x6d4c1
// FUNCTION: C2WIN 0x004ab48d
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

// Stamp a (2*range+1)+extra-side square of city_map cells' entertainment byte (+0x0C) with
// `threshold` if the cell's current value, masked by `query_mask`, falls strictly below
// `threshold`.
// FUNCTION: C2 0x6d5aa
// FUNCTION: C2WIN 0x004ab603
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

// Set a byte field (`field_off`) on all four city-map neighbours that exist around (x,y). `sptr`
// is the current cell byte offset.
// FUNCTION: C2 0x6d6b5
// FUNCTION: C2WIN 0x004ab7b3
void set_4_neighbours(int x, int y, int sptr, unsigned char field_off, unsigned char value)
{
    if (x > 0)  ((unsigned char *)city_map)[sptr - 20 + field_off] = value;
    if (x < 79) ((unsigned char *)city_map)[sptr + 20 + field_off] = value;
    if (y > 0)  ((unsigned char *)city_map)[sptr - 1600 + field_off] = value;
    if (y < 79) ((unsigned char *)city_map)[sptr + 1600 + field_off] = value;
}

// Same as set_4_neighbours, but do not overwrite neighbours whose terrain byte has wall/tower bits
// (0x06) set.
// FUNCTION: C2 0x6d6fb
// FUNCTION: C2WIN 0x004ab82e
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

// Set either east/west (`north_south == 0`) or north/south neighbours, skipping wall/tower cells.
// FUNCTION: C2 0x6d785
// FUNCTION: C2WIN 0x004ab8f9
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

// Stamp `value` at byte field_off on every cardinal neighbour (city_map) whose terrain bits 0x40 /
// 0x80 (aquaduct / reservoir) are clear.
// FUNCTION: C2 0x6d80a
// FUNCTION: C2WIN 0x004ab9d3
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

// Half-sister of set_4_neighbours_if_not_aquaductorresevoir: stamps only the E/W pair when
// north_south == 0, only the N/S pair when north_south != 0.
// FUNCTION: C2 0x6d894
// FUNCTION: C2WIN 0x004aba9e
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

// Region-map sister of set_4_neighbours: stamps `value` at field_off on every cardinal region-map
// neighbour whose terrain bits 0x02 / 0x04 (wall / tower) are clear.
// FUNCTION: C2 0x6d919
// FUNCTION: C2WIN 0x004abb78
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

// Sister of set_4_rm_neighbours_if_not_wallortower with a different mask (0x40 =
// aquaduct/reservoir bit).
// FUNCTION: C2 0x6d9a3
// FUNCTION: C2WIN 0x004abc43
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

// Increment the "elastic" field (byte +2 of city_cell) by 2 at each of the 4 cardinal neighbours
// of cell (x, y) at byte- offset `sptr`. Saturates at 0xff: a neighbour cell whose elastic value
// is already 0xff is left untouched.
// FUNCTION: C2 0x6da2d
// FUNCTION: C2WIN 0x004abd0e
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

// Tests for ns polar walls and returns the result.
// FUNCTION: C2 0x6daa6
// FUNCTION: C2WIN 0x004abdf9
int test_for_ns_polar_walls(int _eax_unused, int y, int sptr)
{
    (void)_eax_unused;
    if (y > 0     && ((*(struct city_cell *)((unsigned char *)city_map + ((sptr) - CITY_ROW))).terrain & 0x06)) return 1;
    if (y < 0x4f  && ((*(struct city_cell *)((unsigned char *)city_map + ((sptr) + CITY_ROW))).terrain & 0x06)) return 1;
    return 0;
}

// Tests for ew polar walls and returns the result.
// FUNCTION: C2 0x6dad6
// FUNCTION: C2WIN 0x004abe5b
int test_for_ew_polar_walls(int x, int _edx_unused, int sptr)
{
    (void)_edx_unused;
    if (x > 0     && ((*(struct city_cell *)((unsigned char *)city_map + ((sptr) - CITY_CELL_BYTES))).terrain & 0x06)) return 1;
    if (x < 0x4f  && ((*(struct city_cell *)((unsigned char *)city_map + ((sptr) + CITY_CELL_BYTES))).terrain & 0x06)) return 1;
    return 0;
}

// Tests for next to region wall and returns the result.
// FUNCTION: C2 0x6db08
// FUNCTION: C2WIN 0x004abebd
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

// Count cells of `building_kind` in a clipped rectangular region-map search area.
// FUNCTION: C2 0x6dbda
// FUNCTION: C2WIN 0x004ac027
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

// Count 3×3-neighbourhood regional industry/port tiles (0xdc..0xef) around (x,y), clipping at the
// 60×60 map edges.
// FUNCTION: C2 0x6dcb4
// FUNCTION: C2WIN 0x004ac19b
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

// Search a clipped radius around (x,y) for the nearest top-left tile of a
// logging-camp/trading-post style 2×2 building (0xe8..0xeb). The best cell offset is published in
// gmn_sptr; the return value is the longest-axis distance to that cell, or radius+1 if none found.
// FUNCTION: C2 0x6dd8c
// FUNCTION: C2WIN 0x004ac2ff
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

// Add `amount` goods of type `goods` to warehouses in the 4×4 area around (x,y). Warehouse cells
// store goods in region_map[(+7)]: high nibble = goods type, low nibble = amount.
// FUNCTION: C2 0x6dedf
// FUNCTION: C2WIN 0x004ac4e9
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

// Remove up to `amount` goods of type `goods` from warehouses, scanning the whole region map.
// Stops once the request is satisfied.
// FUNCTION: C2 0x6e10d
// FUNCTION: C2WIN 0x004ac84e
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

// Stamp `value` at field_off on the north + south city_map neighbours of `sptr` (skips the E/W
// pair). Used by polar neighbour passes.
// FUNCTION: C2 0x6e1cb
// FUNCTION: C2WIN 0x004ac9b3
void set_ns_polar(int x, int y, int sptr, unsigned char field_off, unsigned char value)
{
    (void)x;
    if (y > 0)  ((unsigned char *)city_map)[sptr - 1600 + field_off] = value;
    if (y < 79) ((unsigned char *)city_map)[sptr + 1600 + field_off] = value;
}

// Sister of set_ns_polar: stamps `value` on the E/W neighbours only.
// FUNCTION: C2 0x6e1f6
// FUNCTION: C2WIN 0x004ac9f6
void set_ew_polar(int x, int y, int sptr, unsigned char field_off, unsigned char value)
{
    (void)y;
    if (x > 0)  ((unsigned char *)city_map)[sptr - 20 + field_off] = value;
    if (x < 79) ((unsigned char *)city_map)[sptr + 20 + field_off] = value;
}

// Add signed `delta` to land_value (+0x0f) over a clipped city-map rectangle centered at (x,y).
// Radius plus extra width determines the side length; values are clamped to [-64, 64].
// FUNCTION: C2 0x6e221
// FUNCTION: C2WIN 0x004aca39
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

// Return the maximum ``land_value`` (cell field +0x0F) over a ``bp × bp`` square of city_map cells
// starting at ``base``. Used by evolve_* paths to score zone-suitable land before stamping new
// buildings.
// FUNCTION: C2 0x6e31b
// FUNCTION: C2WIN 0x004acbcf
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

// Given a city-map byte pointer into a multi-cell building, return a pointer to the building's
// top-left corner cell.
// FUNCTION: C2 0x6e36a
// FUNCTION: C2WIN 0x004acc61
unsigned char *get_ptr_to_corner(unsigned char *base_ptr, int size)
{
    int packed;
    int x_off;

    packed = base_ptr[5] & 0xf;
    x_off = packed % size; packed /= size;
    base_ptr -= x_off * 20;
    packed *= 1600; return base_ptr - packed;
}

// Returns 1 if any cell in a range×range square starting at `p` has `cell.education` (+0x0D)
// sharing any bit with `mask`. Special-cased range==1 path returns the bitwise AND directly (used
// for single-cell footprints like simple housing).
// FUNCTION: C2 0x6e3b5
// FUNCTION: C2WIN 0x004accc6
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

// Sibling of affected_by_cover1; same shape but reads `cell.health` (+0x0E) instead of
// `cell.education` (+0x0D).
// FUNCTION: C2 0x6e41c
// FUNCTION: C2WIN 0x004acd6f
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

// Scan a `range × range` block of city-map cells starting at `start` and return the maximum value
// of `cell->range_flag & mask` found in the block. Used by `cap_land_value` and `get_query_info`
// to find the highest range marker in a neighbourhood.
// FUNCTION: C2 0x6e47b
// FUNCTION: C2WIN 0x004ace18
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

// Sister of `get_range1` for `cell->entertain` (+0xc) instead of `cell->range_flag` (+0xa).
// Callers pass entertainment masks 0x3/0xc/0x30 (theatre/colosseum/circus 2-bit slots), confirming
// the field is CC_ENTERTAIN, not CC_FPU_FLAG.
// FUNCTION: C2 0x6e4f3
// FUNCTION: C2WIN 0x004aced1
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

// Scan a clipped square around (x, y) for housing cells (0x82..0xa1) that are top-left footprint
// cells.
// FUNCTION: C2 0x6e563
// FUNCTION: C2WIN 0x004acf8a
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

// Return true if any cell in a clipped city-map square has the road / plaza terrain bit 0x20 set.
// FUNCTION: C2 0x6e6d6
// FUNCTION: C2WIN 0x004ad1db
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

// Sum houses_to_people for top-left housing cells in a clipped area around (x,y). The optional
// extra parameter widens the square beyond radius.
// FUNCTION: C2 0x6e7a2
// FUNCTION: C2WIN 0x004ad339
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

// Snapshot the active map (city_map @ 80×80×20, or region_map @ 60×60×8) into the undo scratch
// buffer. City snapshot lives at scratch_buffer + 0..0x1F3FF; region snapshot at
// +0x1F400..+0x2647F.
// FUNCTION: C2 0x6e898
// FUNCTION: C2WIN 0x004ad4f0
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


// Roll back the city map (80×80×20 = 0x1F400 bytes) from the undo scratch buffer. Skip if the undo
// region was already flushed.
// FUNCTION: C2 0x6e8eb
// FUNCTION: C2WIN 0x004ad562
void restore_city_from_undo_buffer(void)
{
    if (sb_cm_undo_flushed != 0) return;
    copy(scratch_buffer, (unsigned char *)city_map, 0x1f400);
    particles_built = 0;
    particles_cleared = 0;
}

// Region-map equivalent: city undo lives at scratch_buffer +0..0x1F3FF, region undo at
// +0x1F400..+0x2647F (28 800 bytes). After the rollback, replays army-position adjustments
// invalidated by the undo.
// FUNCTION: C2 0x6e91b
// FUNCTION: C2WIN 0x004ad5ad
void restore_region_from_undo_buffer(void)
{
    if (sb_rm_undo_flushed != 0) return;
    copy(scratch_buffer + 0x1f400, (unsigned char *)region_map, 0x7080);
    particles_built = 0;
    particles_cleared = 0;
    army_restoring_adjusts();
}

// Reset every region-map layer and the city-map layers shared with regional state.
// FUNCTION: C2 0x6e955
// FUNCTION: C2WIN 0x004ad602
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

// Zero the byte at offset `layer` (0..19) inside every cell of the 80x80 city_map. 8 byte-stores
// per inner iter × 10 inner iters × 80 outer iters = 6400 cells = full city_map.
// FUNCTION: C2 0x6e99d
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

// Strip the edge-info bit (mask 0xfd) from byte +3 on every cell of the active map (city or
// region, picked by map_mode).
// FUNCTION: C2 0x6ea2d
void clear_edge_info(void)
{
    if (map_mode == 0) {
        unflag_all_cm(3, 0xfd);
    } else if (map_mode == 1) {
        unflag_all_rm(3, 0xfd);
    }
}

// Reset the route elastic-band overlay: clear region-map layer 2 then call set_route_elastic_range
// for each band 1..15.
// FUNCTION: C2 0x6ea65
// FUNCTION: C2WIN 0x004ad6aa
void set_route_elastic(void)
{
    int i;
    clear_all_rm(2);
    for (i = 1; i <= 0xf; i++)
        set_route_elastic_range(i);
}

// BFS step for army route-finding on region_map.
// FUNCTION: C2 0x6ea84
// FUNCTION: C2WIN 0x004ad6ec
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

// Steepest-descent route reconstruction on region_map. Called from show_latest_route after
// set_route_elastic_range has filled cm[+2] of each region-map cell with the BFS distance from the
// chosen start.
// FUNCTION: C2 0x6ee0b
// FUNCTION: C2WIN 0x004adcc4
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

// Reset every flag-marker subsystem (city / province / danger).
// FUNCTION: C2 0x6f0fa
// FUNCTION: C2WIN 0x004ae1a9
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

// Count active entries (≠ -1) in city_flag_list.
// FUNCTION: C2 0x6f173
// FUNCTION: C2WIN 0x004ae2e2
void count_city_flags(void)
{
    int i;
    no_of_city_flags = 0;
    for (i = 0; i < 0x14; i++) {
        if (city_flag_list[i] != -1)
            no_of_city_flags++;
    }
}

// Count active entries (≠ -1) in prov_flag_list.
// FUNCTION: C2 0x6f196
// FUNCTION: C2WIN 0x004ae32f
void count_prov_flags(void)
{
    int i;
    no_of_prov_flags = 0;
    for (i = 0; i < 0x14; i++) {
        if (prov_flag_list[i] != -1)
            no_of_prov_flags++;
    }
}

// If `val` is in city_flag_list, clear it and return 1. Otherwise route to put_city_flag and
// return 1 on hit, 0 otherwise.
// FUNCTION: C2 0x6f1b9
// FUNCTION: C2WIN 0x004ae37c
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

// Mirror of toggle_city_flag for prov_flag_list.
// FUNCTION: C2 0x6f1ed
// FUNCTION: C2WIN 0x004ae3f6
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

// Insert `val` (a cm_ptr) into the next free slot of city_flag_list[20], starting the search from
// last_city_flag+1 (wrapping at 20). Returns 1 on insert, 0 if the list is full (no_of_city_flags
// >= 20) or no free slot was found in 20 attempts.
// FUNCTION: C2 0x6f221
// FUNCTION: C2WIN 0x004ae470
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

// Sister of put_city_flag for the region map: inserts `val` into prov_flag_list[20], cycling
// last_prov_flag, marking region_map[(val/20)].+0x2 = 1. Same special-case for
// danger_flag_list[0].
// FUNCTION: C2 0x6f290
// FUNCTION: C2WIN 0x004ae529
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

// Latch a single danger flag at slot 0 of danger_flag_list and reset the cursor. Always returns 1.
// FUNCTION: C2 0x6f2ff
// FUNCTION: C2WIN 0x004ae5e2
int put_danger_flag(int val)
{
    danger_flag_list[0] = val;
    last_danger_flag = 0;
    return 1;
}

// Clear every city_flag_list slot whose value matches `val`, also wiping the road/aqueduct byte
// (+0x02) of the corresponding city_map cell, then refresh the running flag count. Loop scans the
// full 20-entry table without an early-out so duplicate entries are all cleared.
// FUNCTION: C2 0x6f312
// FUNCTION: C2WIN 0x004ae609
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

// Mirror of clear_city_flag for prov_flag_list / region_map.
// FUNCTION: C2 0x6f34c
// FUNCTION: C2WIN 0x004ae665
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

// Clears danger flag.
// FUNCTION: C2 0x6f386
// FUNCTION: C2WIN 0x004ae6c1
void clear_danger_flag(void)
{
    danger_flag_list[0] = -1;
    count_danger_flags();
}

// Count active entries (≠ -1) in danger_flag_list.
// FUNCTION: C2 0x6f390
// FUNCTION: C2WIN 0x004ae295 REORDERED
void count_danger_flags(void)
{
    int i;
    no_of_danger_flags = 0;
    for (i = 0; i < 0x14; i++) {
        if (danger_flag_list[i] != -1)
            no_of_danger_flags++;
    }
}

// Cycle the "selected city flag" pointer forward to the next valid (i.e. non-empty) entry in
// city_flag_list.
// FUNCTION: C2 0x6f3b3
// FUNCTION: C2WIN 0x004ae761
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

// Cycle the "selected province flag" pointer forward to the next valid entry in prov_flag_list.
// Returns 1 on success, 0 when the list is empty.
// FUNCTION: C2 0x6f405
// FUNCTION: C2WIN 0x004ae7e7
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

// Cycle the "selected danger flag" cursor forward to the next active danger marker. Returns 1 on
// success, 0 when the list is empty.
// FUNCTION: C2 0x6f457
// FUNCTION: C2WIN 0x004ae6db REORDERED
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

// Switch the UI into flag-marker mode (used by the city- and province-level alert overlays).
// FUNCTION: C2 0x6f4a9
// FUNCTION: C2WIN 0x004ae86d
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
