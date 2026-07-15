// D:\C2\CODE\debug.c

#include "c2_data.h"


extern void put_a_font_string(char *str, int x, int y, unsigned char *font, int color);
extern void font_no(int value, char pad_char, char *suffix, int x, int y, unsigned char *font, int color);

// Functions

// Variables

/* struct industry_rec and `industry[]` are declared in c2_types.h. */

// FUNCTION: C2 0x713CF
// Lines 11–17
void debug_screen(void) {
    show_debug_screen();
    wait_key();
    if (map_mode == 0)
        city_map_screen(1);
    else if (map_mode == 1)
        region_map_screen(1);
}

// FUNCTION: C2 0x713FD
// Lines 19–224
void show_debug_screen(void) {
    cover_mouse_droppings();
    show_a_system_window(0, 0, 0x28, 0x1e);

    // line 26-27: Fountains
    put_a_font_string("Fountains ", 8, 8, font1, 0x3f);
    font_no(fountains_count, 0x20, " ", 100, 8, font1, 0x3f);
    // line 28-29: -supplied
    put_a_font_string("-supplied ", 8, 0x17, font1, 0x3f);
    font_no(supplied_fountains_count, 0x20, " ", 100, 0x17, font1, 0x3f);
    // line 30-31: Baths
    put_a_font_string("Baths ", 8, 0x26, font1, 0x3f);
    font_no(baths_count, 0x20, " ", 100, 0x26, font1, 0x3f);
    // line 32-33: -supplied
    put_a_font_string("-supplied ", 8, 0x35, font1, 0x3f);
    font_no(supplied_baths_count, 0x20, " ", 100, 0x35, font1, 0x3f);

    // line 35-36: Hospitals
    put_a_font_string("Hospitals ", 8, 0x44, font1, 0x3f);
    font_no(hospitals_count, 0x20, " ", 100, 0x44, font1, 0x3f);
    // line 37-38: -accessed
    put_a_font_string("-accessed ", 8, 0x53, font1, 0x3f);
    font_no(accessed_hospitals_count, 0x20, " ", 100, 0x53, font1, 0x3f);
    // line 39-40: -cover
    put_a_font_string("-cover ", 8, 0x62, font1, 0x3f);
    font_no(hospital_cover, 0x20, " %", 100, 0x62, font1, 0x3f);
    // line 41-42: -disease
    put_a_font_string("-disease ", 8, 0x71, font1, 0x3f);
    font_no(plague_running_count, 0x20, " ", 100, 0x71, font1, 0x3f);

    // line 44-45: Libraries
    put_a_font_string("Libraries ", 8, 0x80, font1, 0x3f);
    font_no(libraries_count, 0x20, " ", 100, 0x80, font1, 0x3f);
    // line 46-47: -accessed
    put_a_font_string("-accessed ", 8, 0x8f, font1, 0x3f);
    font_no(accessed_libraries_count, 0x20, " ", 100, 0x8f, font1, 0x3f);
    // line 48-49: -cover
    put_a_font_string("-cover ", 8, 0x9e, font1, 0x3f);
    font_no(library_cover, 0x20, " %", 100, 0x9e, font1, 0x3f);

    // line 51-52: Temples (sum of small+med+large)
    put_a_font_string("Temples ", 8, 0xad, font1, 0x3f);
    font_no(large_temples_count + med_temples_count + small_temples_count, 0x20, " ", 100, 0xad, font1, 0x3f);
    // line 53-54: - culture (sum)
    put_a_font_string("- culture ", 8, 0xbc, font1, 0x3f);
    font_no(large_temples_culture_count + med_temples_culture_count + small_temples_culture_count, 0x20, " ", 100, 0xbc, font1, 0x3f);

    // line 56-57: Pleasure (sum of entertainment venues)
    put_a_font_string("Pleasure ", 8, 0xcb, font1, 0x3f);
    font_no(theatre_count + odium_count + arena_count + colosseum_count + circus_count + circus_maximus_count, 0x20, " ", 100, 0xcb, font1, 0x3f);
    // line 58-59: - culture (culture sum)
    put_a_font_string("- culture ", 8, 0xda, font1, 0x3f);
    font_no(theatre_culture_count + odium_culture_count + arena_culture_count + colosseum_culture_count + circus_culture_count + circus_maximus_culture_count, 0x20, " ", 100, 0xda, font1, 0x3f);

    // line 61-62: Entertain.
    put_a_font_string("Entertain. ", 8, 0xe9, font1, 0x3f);
    font_no(entertainment_level, 0x20, " ", 100, 0xe9, font1, 0x3f);
    // line 63-64: Religion
    put_a_font_string("Religion ", 8, 0xf8, font1, 0x3f);
    font_no(religion_level, 0x20, " ", 100, 0xf8, font1, 0x3f);
    // line 65-66: Utilities
    put_a_font_string("Utilities ", 8, 0x107, font1, 0x3f);
    font_no(utility_level, 0x20, " ", 100, 0x107, font1, 0x3f);

    // line 68-69: GDP
    put_a_font_string("GDP ", 8, 0x116, font1, 0x3f);
    font_no(current_gdp, 0x20, " ", 100, 0x116, font1, 0x3f);
    // line 70-72: rolling profit (signed)
    put_a_font_string("rolling ", 8, 0x125, font1, 0x3f);
    if (rolling_profit < 0) font_no(-rolling_profit, 0x2d, " ", 100, 0x125, font1, 3);
    else font_no(rolling_profit, 0x20, " ", 100, 0x125, font1, 0x3f);

    // line 74-75: Fire rate
    put_a_font_string("Fire rate ", 8, 0x143, font1, 0x3f);
    font_no(fire_rate, 0x20, " ", 100, 0x143, font1, 0x3f);
    // line 76-77: Road rate
    put_a_font_string("Road rate ", 8, 0x152, font1, 0x3f);
    font_no(road_rate, 0x20, " ", 100, 0x152, font1, 0x3f);
    // line 78-79: Wall rate
    put_a_font_string("Wall rate ", 8, 0x161, font1, 0x3f);
    font_no(wall_rate, 0x20, " ", 100, 0x161, font1, 0x3f);
    // line 80-81: Water rate
    put_a_font_string("Water rate ", 8, 0x170, font1, 0x3f);
    font_no(water_trouble_rate, 0x20, " ", 100, 0x170, font1, 0x3f);

    // line 83-84: Road acc
    put_a_font_string("Road acc", 8, 0x17f, font1, 0x3f);
    font_no(road_accident, 0x20, " ", 100, 0x17f, font1, 0x3f);
    // line 85-86: Wall acc
    put_a_font_string("Wall acc", 8, 0x18e, font1, 0x3f);
    font_no(wall_accident, 0x20, " ", 100, 0x18e, font1, 0x3f);
    // line 87-88: Fire acc
    put_a_font_string("Fire acc", 8, 0x19d, font1, 0x3f);
    font_no(fire_accident, 0x20, " ", 100, 0x19d, font1, 0x3f);

    // line 90-91: Wall cov
    put_a_font_string("Wall cov", 8, 0x1ac, font1, 0x3f);
    font_no(wall_cover, 0x20, " ", 100, 0x1ac, font1, 0x3f);

    // line 95-97: pop growth (signed)
    put_a_font_string("pop growth ", 0xc8, 8, font1, 0x3f);
    if (pop_growth_factor < 0) font_no(-pop_growth_factor, 0x2d, " ", 300, 8, font1, 3);
    else font_no(pop_growth_factor, 0x20, " ", 300, 8, font1, 0x3f);
    // line 99-101: - future (signed)
    put_a_font_string("- future ", 0xc8, 0x17, font1, 0x3f);
    if (pop_growth_future < 0) font_no(-pop_growth_future, 0x2d, " ", 300, 0x17, font1, 3);
    else font_no(pop_growth_future, 0x20, " ", 300, 0x17, font1, 0x3f);
    // line 103-105: ind growth (signed)
    put_a_font_string("ind growth ", 0xc8, 0x26, font1, 0x3f);
    if (ind_growth_factor < 0) font_no(-ind_growth_factor, 0x2d, " ", 300, 0x26, font1, 3);
    else font_no(ind_growth_factor, 0x20, " ", 300, 0x26, font1, 0x3f);
    // line 107-109: - future (signed)
    put_a_font_string("- future ", 0xc8, 0x35, font1, 0x3f);
    if (ind_growth_future < 0) font_no(-ind_growth_future, 0x2d, " ", 300, 0x35, font1, 3);
    else font_no(ind_growth_future, 0x20, " ", 300, 0x35, font1, 0x3f);
    // line 111-113: insurrection (signed)
    put_a_font_string("insurrection ", 0xc8, 0x44, font1, 0x3f);
    if (insurrection_factor < 0) font_no(-insurrection_factor, 0x2d, " ", 300, 0x44, font1, 3);
    else font_no(insurrection_factor, 0x20, " ", 300, 0x44, font1, 0x3f);
    // line 115-117: - future (signed)
    put_a_font_string("- future ", 0xc8, 0x53, font1, 0x3f);
    if (insurrection_future < 0) font_no(-insurrection_future, 0x2d, " ", 300, 0x53, font1, 3);
    else font_no(insurrection_future, 0x20, " ", 300, 0x53, font1, 0x3f);

    // line 119-120: conscription rate
    put_a_font_string("conscription rate", 0xc8, 0x62, font1, 0x3f);
    font_no(conscription_rate, 0x20, " ", 300, 0x62, font1, 0x3f);
    // line 121-122: employment
    put_a_font_string("employment", 0xc8, 0x71, font1, 0x3f);
    font_no(employment_rate, 0x20, " ", 300, 0x71, font1, 0x3f);
    // line 123-124: employees
    put_a_font_string("employees", 0xc8, 0x80, font1, 0x3f);
    font_no(employees, 0x20, " ", 300, 0x80, font1, 0x3f);
    // line 125-126: population
    put_a_font_string("population", 0xc8, 0x8f, font1, 0x3f);
    font_no(population, 0x20, " ", 300, 0x8f, font1, 0x3f);

    // line 128-129: grain sup/sat
    put_a_font_string("grain sup/sat", 0xc8, 0x9e, font1, 0x3f);
    x_is = 0;
    // line 130-131
    font_no(industry[0].city_supply, 0x20, " ", 300, 0x9e, font1, 0x3f);
    font_no(industry[0].supply_pipeline[0], 0x2f, " ", x_is + 300, 0x9e, font1, 0x3f);
    // line 132-133: grapes
    put_a_font_string("grapes sup/sat", 0xc8, 0xad, font1, 0x3f);
    x_is = 0;
    // line 134-135
    font_no(industry[1].city_supply, 0x20, " ", 300, 0xad, font1, 0x3f);
    font_no(industry[1].supply_pipeline[0], 0x2f, " ", x_is + 300, 0xad, font1, 0x3f);
    // line 136-137: cattle
    put_a_font_string("cattle sup/sat", 0xc8, 0xbc, font1, 0x3f);
    x_is = 0;
    // line 138-139
    font_no(industry[2].city_supply, 0x20, " ", 300, 0xbc, font1, 0x3f);
    font_no(industry[2].supply_pipeline[0], 0x2f, " ", x_is + 300, 0xbc, font1, 0x3f);
    // line 140-141: timber
    put_a_font_string("timber sup/sat", 0xc8, 0xcb, font1, 0x3f);
    x_is = 0;
    // line 142-143
    font_no(industry[3].city_supply, 0x20, " ", 300, 0xcb, font1, 0x3f);
    font_no(industry[3].supply_pipeline[0], 0x2f, " ", x_is + 300, 0xcb, font1, 0x3f);
    // line 144-145: gems
    put_a_font_string("gems sup/sat", 0xc8, 0xda, font1, 0x3f);
    x_is = 0;
    // line 146-147
    font_no(industry[4].city_supply, 0x20, " ", 300, 0xda, font1, 0x3f);
    font_no(industry[4].supply_pipeline[0], 0x2f, " ", x_is + 300, 0xda, font1, 0x3f);
    // line 148-149: lead
    put_a_font_string("lead sup/sat", 0xc8, 0xe9, font1, 0x3f);
    x_is = 0;
    // line 150-151
    font_no(industry[5].city_supply, 0x20, " ", 300, 0xe9, font1, 0x3f);
    font_no(industry[5].supply_pipeline[0], 0x2f, " ", x_is + 300, 0xe9, font1, 0x3f);
    // line 152-153: iron
    put_a_font_string("iron sup/sat", 0xc8, 0xf8, font1, 0x3f);
    x_is = 0;
    // line 154-155
    font_no(industry[6].city_supply, 0x20, " ", 300, 0xf8, font1, 0x3f);
    font_no(industry[6].supply_pipeline[0], 0x2f, " ", x_is + 300, 0xf8, font1, 0x3f);
    // line 156-157: copper
    put_a_font_string("copper sup/sat", 0xc8, 0x107, font1, 0x3f);
    x_is = 0;
    // line 158-159
    font_no(industry[7].city_supply, 0x20, " ", 300, 0x107, font1, 0x3f);
    font_no(industry[7].supply_pipeline[0], 0x2f, " ", x_is + 300, 0x107, font1, 0x3f);
    // line 160-161: clay
    put_a_font_string("clay sup/sat", 0xc8, 0x116, font1, 0x3f);
    x_is = 0;
    // line 162-163
    font_no(industry[8].city_supply, 0x20, " ", 300, 0x116, font1, 0x3f);
    font_no(industry[8].supply_pipeline[0], 0x2f, " ", x_is + 300, 0x116, font1, 0x3f);
    // line 164-165: sand
    put_a_font_string("sand sup/sat", 0xc8, 0x125, font1, 0x3f);
    x_is = 0;
    // line 166-167
    font_no(industry[9].city_supply, 0x20, " ", 300, 0x125, font1, 0x3f);
    font_no(industry[9].supply_pipeline[0], 0x2f, " ", x_is + 300, 0x125, font1, 0x3f);
    // line 168-169: marble
    put_a_font_string("marble sup/sat", 0xc8, 0x134, font1, 0x3f);
    x_is = 0;
    // line 170-171
    font_no(industry[10].city_supply, 0x20, " ", 300, 0x134, font1, 0x3f);
    font_no(industry[10].supply_pipeline[0], 0x2f, " ", x_is + 300, 0x134, font1, 0x3f);
    // line 172-173: stone
    put_a_font_string("stone sup/sat", 0xc8, 0x143, font1, 0x3f);
    x_is = 0;
    // line 174-175
    font_no(industry[11].city_supply, 0x20, " ", 300, 0x143, font1, 0x3f);
    font_no(industry[11].supply_pipeline[0], 0x2f, " ", x_is + 300, 0x143, font1, 0x3f);
    // line 176-177: silk
    put_a_font_string("silk sup/sat", 0xc8, 0x152, font1, 0x3f);
    x_is = 0;
    // line 178-179
    font_no(industry[12].city_supply, 0x20, " ", 300, 0x152, font1, 0x3f);
    font_no(industry[12].supply_pipeline[0], 0x2f, " ", x_is + 300, 0x152, font1, 0x3f);
    // line 180-181: spices
    put_a_font_string("spices sup/sat", 0xc8, 0x161, font1, 0x3f);
    x_is = 0;
    // line 182-183
    font_no(industry[13].city_supply, 0x20, " ", 300, 0x161, font1, 0x3f);
    font_no(industry[13].supply_pipeline[0], 0x2f, " ", x_is + 300, 0x161, font1, 0x3f);
    // line 184-185: ivory
    put_a_font_string("ivory sup/sat", 0xc8, 0x170, font1, 0x3f);
    x_is = 0;
    // line 186-187
    font_no(industry[14].city_supply, 0x20, " ", 300, 0x170, font1, 0x3f);
    font_no(industry[14].supply_pipeline[0], 0x2f, " ", x_is + 300, 0x170, font1, 0x3f);
    // line 188-189: fish
    put_a_font_string("fish sup/sat", 0xc8, 0x17f, font1, 0x3f);
    x_is = 0;
    // line 190-191
    font_no(industry[15].city_supply, 0x20, " ", 300, 0x17f, font1, 0x3f);
    font_no(industry[15].supply_pipeline[0], 0x2f, " ", x_is + 300, 0x17f, font1, 0x3f);

    // line 193-194: Workcamps (column 2)
    put_a_font_string("Workcamps", 0xc8, 0x18e, font1, 0x3f);
    font_no(no_of_workcamps, 0x20, " ", 300, 0x18e, font1, 0x3f);
    // line 199-200: No of citizens (column 3)
    put_a_font_string("No of citizens", 0x190, 8, font1, 0x3f);
    font_no(no_of_citizens, 0x20, " ", 500, 8, font1, 0x3f);
    // line 202-203: No of armies
    put_a_font_string("No of armies", 0x190, 0x17, font1, 0x3f);
    font_no(no_of_armies, 0x20, " ", 500, 0x17, font1, 0x3f);
    // line 205-206: No of units
    put_a_font_string("No of units", 0x190, 0x26, font1, 0x3f);
    font_no(no_of_units, 0x20, " ", 500, 0x26, font1, 0x3f);
    // line 208-209: No of figures
    put_a_font_string("No of figures", 0x190, 0x35, font1, 0x3f);
    font_no(no_of_figures, 0x20, " ", 500, 0x35, font1, 0x3f);
    // line 211-212: No of arrows
    put_a_font_string("No of arrows", 0x190, 0x44, font1, 0x3f);
    font_no(no_of_arrows, 0x20, " ", 500, 0x44, font1, 0x3f);

    // line 214-215: Connections
    put_a_font_string("Connections", 0x190, 0x53, font1, 0x3f);
    x_is = 0;

    // line 216: N connection
    if (empire_connections[0] != 0)
        put_a_font_string("N", 0x1f4, 0x53, font1, 0x3f);
    // line 217: E connection
    if (empire_connections[1] != 0)
        put_a_font_string("E", x_is + 0x1f4, 0x53, font1, 0x3f);
    // line 218: S connection
    if (empire_connections[2] != 0)
        put_a_font_string("S", x_is + 0x1f4, 0x53, font1, 0x3f);
    // line 219: W connection
    if (empire_connections[3] != 0)
        put_a_font_string("W", x_is + 0x1f4, 0x53, font1, 0x3f);

    // line 221-223
    setup_whole_screen_refresh();
    refresh_svga_screen();
    hold_mouse_replace = 1;
}
