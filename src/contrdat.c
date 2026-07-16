//
// Initialized control data.
// Data-only translation unit.

#include "c2_data.h"
#include "c2_funcs.h"

struct menu_item_rec file_items[4] = {
    { 0, 1, act_new_game, 0 },
    { 20, 2, act_load_game, 0 },
    { 40, 3, act_save_game, 0 },
    { 60, 4, act_exit_game, 0 }
};

struct menu_item_rec options_items[5] = {
    { 0, 1, act_toggle_tunes, 0 },
    { 20, 2, act_toggle_sound_fx, 0 },
    { 40, 3, act_toggle_anims, 0 },
    { 60, 4, act_toggle_year_end, 0 },
    { 80, 5, act_census, 0 }
};

struct menu_item_rec speed_items[3] = {
    { 0, 1, act_game_speed, 0 },
    { 20, 2, act_scroll_speed, 0 },
    { 40, 3, act_pause, 0 }
};

struct menu_item_rec help_items[5] = {
    { 0, 1, act_help_tips, 0 },
    { 20, 2, act_help_game, 0 },
    { 40, 3, act_help_history, 0 },
    { 60, 4, act_help_icons, 0 },
    { 80, 5, act_about, 0 }
};

struct menu_rec main_menu[4] = {
    { { 10 }, 6, 1, file_items, 4 },
    { { 10 }, 6, 2, options_items, 5 },
    { { 10 }, 6, 3, speed_items, 3 },
    { { 10 }, 6, 4, help_items, 5 }
};

struct selection_rec houses_selection[6] = {
    { 0, 0, act_house1, 0, 0, 16, 0, 0, 0 },
    { 0, 1, act_house2, 0, 0, 16, 0, 0, 0 },
    { 0, 2, act_house3, 0, 0, 16, 0, 0, 0 },
    { 0, 3, act_house4, 0, 0, 16, 0, 0, 0 },
    { 0, 4, act_house5, 0, 0, 16, 0, 0, 0 },
    { 0, 5, act_select_cancel, 0, 0, 16, 0, 0, 0 }
};

struct selection_rec water_selection[5] = {
    { 0, 0, act_resevoir, 0, 0, 16, 0, 0, 6 },
    { 0, 1, act_aquaduct, 0, 0, 16, 0, 0, 4 },
    { 0, 2, act_well, 0, 0, 16, 0, 0, 9 },
    { 0, 3, act_fountain, 0, 0, 16, 0, 0, 12 },
    { 0, 4, act_select_cancel, 0, 0, 16, 0, 0, 0 }
};

struct selection_rec security_selection[5] = {
    { 0, 0, act_wall, 0, 0, 16, 0, 0, 3 },
    { 0, 1, act_tower, 0, 0, 16, 0, 0, 5 },
    { 0, 2, act_barracks, 0, 0, 16, 0, 0, 13 },
    { 0, 3, act_prefecture, 0, 0, 16, 0, 0, 14 },
    { 0, 4, act_select_cancel, 0, 0, 16, 0, 0, 0 }
};

struct selection_rec health_selection[3] = {
    { 0, 0, act_baths, 0, 0, 16, 0, 0, 10 },
    { 0, 1, act_hospital, 0, 0, 16, 0, 0, 11 },
    { 0, 2, act_select_cancel, 0, 0, 16, 0, 0, 0 }
};

struct selection_rec forum_selection[4] = {
    { 0, 0, act_select_small_forum, 0, 0, 16, 0, 0, 70 },
    { 4, 1, act_select_medium_forum, 0, 400, 16, 0, 0, 74 },
    { 8, 2, act_select_large_forum, 0, 1800, 16, 0, 0, 78 },
    { 0, 3, act_select_cancel, 0, 0, 16, 0, 0, 0 }
};

struct selection_rec education_selection[4] = {
    { 0, 0, act_select_grammaticus, 0, 0, 16, 0, 0, 17 },
    { 1, 1, act_select_rhetor, 0, 0, 16, 0, 0, 18 },
    { 2, 2, act_select_library, 0, 1200, 16, 0, 0, 19 },
    { 0, 3, act_select_cancel, 0, 0, 16, 0, 0, 0 }
};

struct selection_rec temple_selection[4] = {
    { 0, 0, act_select_small_temple, 0, 0, 16, 0, 0, 20 },
    { 1, 1, act_select_medium_temple, 0, 0, 16, 0, 0, 21 },
    { 2, 2, act_select_large_temple, 0, 0, 16, 0, 0, 22 },
    { 0, 3, act_select_cancel, 0, 0, 16, 0, 0, 0 }
};

struct selection_rec entertainment_selection[7] = {
    { 0, 0, act_select_theatre, 0, 0, 16, 0, 0, 23 },
    { 1, 1, act_select_odium, 0, 800, 16, 0, 0, 24 },
    { 2, 2, act_select_arena, 0, 0, 16, 0, 0, 25 },
    { 3, 3, act_select_colosseum, 0, 2400, 16, 0, 0, 26 },
    { 4, 4, act_select_circus, 0, 0, 16, 0, 0, 27 },
    { 5, 5, act_select_circus_max, 0, 4800, 16, 0, 0, 28 },
    { 0, 6, act_select_cancel, 0, 0, 16, 0, 0, 0 }
};

struct selection_rec ovmap_selection[11] = {
    { 0, 0, act_ov_geography, 0, 0, 16, 0, 0, 0 },
    { 0, 1, act_ov_landval, 0, 0, 16, 0, 0, 0 },
    { 0, 2, act_ov_water, 0, 0, 16, 0, 0, 0 },
    { 0, 3, act_ov_security, 0, 0, 16, 0, 0, 0 },
    { 0, 4, act_ov_unrest, 0, 0, 16, 0, 0, 0 },
    { 0, 5, act_ov_admin, 0, 0, 16, 0, 0, 0 },
    { 0, 6, act_ov_entertainment, 0, 0, 16, 0, 0, 0 },
    { 0, 7, act_ov_education, 0, 0, 16, 0, 0, 0 },
    { 0, 8, act_ov_health, 0, 0, 16, 0, 0, 0 },
    { 0, 9, act_ov_industry, 0, 0, 16, 0, 0, 0 },
    { 0, 10, act_select_cancel, 0, 0, 16, 0, 0, 0 }
};

struct selection_rec farm_selection[5] = {
    { 0, 0, act_select_farm, 0, 0, 0, 0, 0, 0 },
    { 1, 1, act_select_farm, 0, 0, 1, 0, 0, 0 },
    { 2, 2, act_select_farm, 0, 0, 2, 0, 0, 0 },
    { 3, 3, act_select_farm, 0, 0, 3, 0, 0, 0 },
    { 0, 4, act_select_cancel, 0, 0, 16, 0, 0, 0 }
};

struct selection_rec mine_selection[5] = {
    { 4, 0, act_select_farm, 0, 0, 4, 0, 0, 0 },
    { 5, 1, act_select_farm, 0, 0, 5, 0, 0, 0 },
    { 6, 2, act_select_farm, 0, 0, 6, 0, 0, 0 },
    { 7, 3, act_select_farm, 0, 0, 7, 0, 0, 0 },
    { 0, 4, act_select_cancel, 0, 0, 16, 0, 0, 0 }
};

struct selection_rec quarry_selection[5] = {
    { 8, 0, act_select_farm, 0, 0, 8, 0, 0, 0 },
    { 9, 1, act_select_farm, 0, 0, 9, 0, 0, 0 },
    { 10, 2, act_select_farm, 0, 0, 10, 0, 0, 0 },
    { 11, 3, act_select_farm, 0, 0, 11, 0, 0, 0 },
    { 0, 4, act_select_cancel, 0, 0, 16, 0, 0, 0 }
};

struct selection_rec industry_selection[18] = {
    { 0, 0, act_market, 0, 0, 16, 0, 0, 15 },
    { 0, 1, act_business, 0, 0, 0, 0, 0, 16 },
    { 1, 2, act_business, 0, 0, 1, 0, 0, 16 },
    { 2, 3, act_business, 0, 0, 2, 0, 0, 16 },
    { 3, 4, act_business, 0, 0, 3, 0, 0, 16 },
    { 4, 5, act_business, 0, 0, 4, 0, 0, 16 },
    { 5, 6, act_business, 0, 0, 5, 0, 0, 16 },
    { 6, 7, act_business, 0, 0, 6, 0, 0, 16 },
    { 7, 8, act_business, 0, 0, 7, 0, 0, 16 },
    { 8, 9, act_business, 0, 0, 8, 0, 0, 16 },
    { 9, 10, act_business, 0, 0, 9, 0, 0, 16 },
    { 10, 11, act_business, 0, 0, 10, 0, 0, 16 },
    { 11, 12, act_business, 0, 0, 11, 0, 0, 16 },
    { 12, 13, act_business, 0, 0, 12, 0, 0, 16 },
    { 13, 14, act_business, 0, 0, 13, 0, 0, 16 },
    { 14, 15, act_business, 0, 0, 14, 0, 0, 16 },
    { 15, 16, act_business, 0, 0, 15, 0, 0, 16 },
    { 0, 17, act_select_cancel, 0, 0, 16, 0, 0, 0 }
};

struct selection_rec rm_security_selection[3] = {
    { 0, 0, act_wall_rm, 0, 0, 16, 0, 0, 3 },
    { 0, 1, act_rm_fort, 0, 0, 16, 0, 0, 4 },
    { 0, 2, act_select_cancel, 0, 0, 16, 0, 0, 0 }
};

struct selection_rec rm_industry_selection[7] = {
    { 0, 0, act_rm_farm, 0, 0, 16, 0, 0, 6 },
    { 0, 1, act_rm_mine, 0, 0, 16, 0, 0, 6 },
    { 0, 2, act_rm_quarry, 0, 0, 16, 0, 0, 6 },
    { 0, 3, act_rm_warehouse, 0, 0, 16, 0, 0, 8 },
    { 0, 4, act_rm_workhouse, 0, 0, 16, 0, 0, 5 },
    { 0, 5, act_rm_shipyard, 0, 0, 16, 0, 0, 7 },
    { 0, 6, act_select_cancel, 0, 0, 16, 0, 0, 0 }
};

struct selection_rec gardens_plaza_selection[3] = {
    { 0, 0, act_gardens, 0, 0, 16, 0, 0, 7 },
    { 0, 1, act_plaza, 0, 0, 16, 0, 0, 8 },
    { 0, 2, act_select_cancel, 0, 0, 16, 0, 0, 0 }
};

struct button_rec confirming_buttons[2] = {
    { 32, 48, 29, 32, act_yes, 0, 0, 0, 4, 0, 0 },
    { 80, 48, 31, 32, act_no, 0, 0, 0, 4, 0, 0 }
};

struct button_rec help_buttons[2] = {
    { 0, 0, 45, 24, act_rewind_help, 0, 0, 0, 4, 0, 0 },
    { 32, 0, 49, 24, act_start_help, 0, 0, 0, 4, 0, 0 }
};

struct button_rec queery_buttons[6] = {
    { 224, 376, 56, 32, act_query_help, 0, 0, 0, 4, 0, 0 },
    { 272, 376, 58, 32, act_query_tips, 0, 0, 0, 4, 0, 0 },
    { 320, 376, 60, 32, act_query_history, 0, 0, 0, 4, 0, 0 },
    { 32, 376, 52, 32, act_general_query, 0, 0, 0, 2, 0, 0 },
    { 80, 376, 62, 32, act_people_query, 0, 0, 0, 2, 0, 0 },
    { 128, 376, 54, 32, act_detailed_query, 0, 0, 0, 2, 0, 0 }
};

struct button_rec query_buttons2[1] = {
    { 240, 230, 33, 24, act_goto_city, 0, 0, 0, 4, 0, 0 }
};

struct button_rec adjusting_buttons[2] = {
    { 32, 28, 35, 24, act_adjust_up, 0, 0, 0, 4, 0, 0 },
    { 64, 28, 37, 24, act_adjust_down, 0, 0, 0, 4, 0, 0 }
};

struct button_rec skill1_buttons[4] = {
    { 320, 200, 19, 24, act_tutorial, 0, 0, 0, 4, 0, 0 },
    { 320, 152, 19, 24, act_preload, 0, 0, 0, 4, 0, 0 },
    { 320, 104, 19, 24, act_out, 0, 0, 0, 4, 0, 0 },
    { 320, 248, 19, 24, act_dos, 0, 0, 0, 4, 0, 0 }
};

struct button_rec skill2_buttons[6] = {
    { 192, 80, 23, 24, act_skill_down, 0, 0, 0, 4, 0, 0 },
    { 224, 80, 21, 24, act_skill_up, 0, 0, 0, 4, 0, 0 },
    { 192, 160, 19, 24, act_tog_peace, 0, 0, 0, 4, 0, 0 },
    { 192, 208, 19, 24, act_choose_name, 0, 0, 0, 4, 0, 0 },
    { 192, 256, 19, 24, act_out, 0, 0, 0, 4, 0, 0 },
    { 192, 304, 19, 24, act_back_to_front_panel, 0, 0, 0, 4, 0, 0 }
};

struct button_rec exit_buttons[3] = {
    { 312, 176, 19, 24, act_do_exit, 0, 0, 0, 4, 0, 0 },
    { 312, 216, 19, 24, act_exit_and_save, 0, 0, 0, 4, 0, 0 },
    { 312, 256, 19, 24, act_dont_exit, 0, 0, 0, 4, 0, 0 }
};

struct button_rec loadsave_buttons[4] = {
    { 256, 64, 29, 32, act_yes, 0, 0, 0, 4, 0, 0 },
    { 304, 64, 31, 32, act_no, 0, 0, 0, 4, 0, 0 },
    { 352, 144, 21, 24, act_adjust_down, 0, 0, 0, 4, 0, 0 },
    { 352, 176, 23, 24, act_adjust_up, 0, 0, 0, 4, 0, 0 }
};

struct button_rec tunes_buttons[2] = {
    { 224, 16, 33, 24, act_tog_tunes, 0, 0, 0, 4, 0, 0 },
    { 224, 48, 33, 24, act_tunes_level, 0, 0, 0, 4, 0, 0 }
};

struct button_rec samples_buttons[5] = {
    { 224, 16, 33, 24, act_tog_samples, 0, 0, 0, 4, 0, 0 },
    { 224, 48, 33, 24, act_tog_ambients, 0, 0, 0, 4, 0, 0 },
    { 224, 80, 33, 24, act_tog_speech, 0, 0, 0, 4, 0, 0 },
    { 224, 112, 33, 24, act_samples_level, 0, 0, 0, 4, 0, 0 },
    { 224, 144, 33, 24, act_nof_samples, 0, 0, 0, 4, 0, 0 }
};

struct button_rec tog_anims_buttons[1] = {
    { 224, 16, 33, 24, act_tog_anims, 0, 0, 0, 4, 0, 0 }
};

struct button_rec tog_yearend_buttons[2] = {
    { 224, 16, 33, 24, act_tog_yearend, 0, 0, 0, 4, 0, 0 },
    { 224, 48, 33, 24, act_tog_autosave, 0, 0, 0, 4, 0, 0 }
};

struct button_rec promotion_buttons[3] = {
    { 256, 144, 33, 24, act_take_promotion, 0, 0, 0, 4, 0, 0 },
    { 256, 176, 33, 24, act_review_in_10, 0, 0, 0, 4, 0, 0 },
    { 256, 208, 33, 24, act_review_in_25, 0, 0, 0, 4, 0, 0 }
};

struct button_rec request_buttons[2] = {
    { 0, 0, 35, 24, act_request_up, 0, 0, 0, 4, 0, 0 },
    { 32, 0, 37, 24, act_request_down, 0, 0, 0, 4, 0, 0 }
};

struct button_rec goto_mess_buttons[1] = {
    { 0, 0, 33, 24, act_goto_message, 0, 0, 0, 4, 0, 0 }
};

struct button_rec admin_buttons[4] = {
    { 0, 0, 35, 24, act_pop_tax_up, 0, 0, 0, 4, 0, 0 },
    { 24, 0, 37, 24, act_pop_tax_down, 0, 0, 0, 4, 0, 0 },
    { 0, 24, 35, 24, act_ind_tax_up, 0, 0, 0, 4, 0, 0 },
    { 24, 24, 37, 24, act_ind_tax_down, 0, 0, 0, 4, 0, 0 }
};

struct button_rec career_buttons[3] = {
    { 0, 0, 35, 24, act_salary_up, 0, 0, 0, 4, 0, 0 },
    { 24, 0, 37, 24, act_salary_down, 0, 0, 0, 4, 0, 0 },
    { 0, 28, 33, 24, act_donation, 0, 0, 0, 4, 0, 0 }
};

struct button_rec donation_buttons[3] = {
    { 0, 0, 35, 24, act_donation_up, 0, 0, 0, 4, 0, 0 },
    { 24, 0, 37, 24, act_donation_down, 0, 0, 0, 4, 0, 0 },
    { 0, 28, 33, 24, act_send_donation, 0, 0, 0, 4, 0, 0 }
};

struct button_rec clerk_buttons[2] = {
    { 0, 0, 41, 24, act_history_graph_shorter, 0, 0, 0, 4, 0, 0 },
    { 24, 0, 39, 24, act_history_graph_longer, 0, 0, 0, 4, 0, 0 }
};

struct button_rec army_buttons[8] = {
    { 190, 126, 56, 32, act_army_box_help, 0, 0, 0, 4, 0, 0 },
    { 120, 6, 35, 24, act_army_wage_up, 0, 0, 0, 4, 0, 0 },
    { 144, 6, 37, 24, act_army_wage_down, 0, 0, 0, 4, 0, 0 },
    { 120, 30, 35, 24, act_conscription_up, 0, 0, 0, 4, 0, 0 },
    { 144, 30, 37, 24, act_conscription_down, 0, 0, 0, 4, 0, 0 },
    { 392, 134, 41, 24, act_next_cohort, 0, 0, 0, 4, 0, 0 },
    { 416, 134, 39, 24, act_prev_cohort, 0, 0, 0, 4, 0, 0 },
    { 568, 134, 33, 24, act_demob_cohort, 0, 0, 0, 4, 0, 0 }
};

struct button_rec cohort_buttons[1] = {
    { 0, 0, 33, 24, act_demob_cohort, 0, 0, 0, 4, 0, 0 }
};

struct button_rec mercenary_buttons[2] = {
    { 160, 98, 35, 24, act_more_mercs, 0, 0, 0, 4, 0, 0 },
    { 184, 98, 37, 24, act_less_mercs, 0, 0, 0, 4, 0, 0 }
};

struct button_rec slave1_buttons[2] = {
    { 0, 0, 35, 24, act_slave_welfare_up, 0, 0, 0, 4, 0, 0 },
    { 24, 0, 37, 24, act_slave_welfare_down, 0, 0, 0, 4, 0, 0 }
};

struct button_rec slave2_buttons[12] = {
    { 0, 0, 35, 24, act_slave_fire_up, 0, 0, 0, 4, 0, 0 },
    { 24, 0, 37, 24, act_slave_fire_down, 0, 0, 0, 4, 0, 0 },
    { 0, 24, 35, 24, act_slave_city_road_up, 0, 0, 0, 4, 0, 0 },
    { 24, 24, 37, 24, act_slave_city_road_down, 0, 0, 0, 4, 0, 0 },
    { 0, 48, 35, 24, act_slave_city_water_up, 0, 0, 0, 4, 0, 0 },
    { 24, 48, 37, 24, act_slave_city_water_down, 0, 0, 0, 4, 0, 0 },
    { 0, 72, 35, 24, act_slave_city_wall_up, 0, 0, 0, 4, 0, 0 },
    { 24, 72, 37, 24, act_slave_city_wall_down, 0, 0, 0, 4, 0, 0 },
    { 0, 96, 35, 24, act_slave_reg_work_up, 0, 0, 0, 4, 0, 0 },
    { 24, 96, 37, 24, act_slave_reg_work_down, 0, 0, 0, 4, 0, 0 },
    { 0, 120, 35, 24, act_slave_reg_upkeep_up, 0, 0, 0, 4, 0, 0 },
    { 24, 120, 37, 24, act_slave_reg_upkeep_down, 0, 0, 0, 4, 0, 0 }
};

struct button_rec rome1_buttons[1] = {
    { 0, 0, 33, 24, act_send_gift, 0, 0, 0, 4, 0, 0 }
};

struct button_rec rome2_buttons[3] = {
    { 0, 0, 35, 24, act_gift_up, 0, 0, 0, 4, 0, 0 },
    { 24, 0, 37, 24, act_gift_down, 0, 0, 0, 4, 0, 0 },
    { 0, 24, 33, 24, act_gift_send, 0, 0, 0, 4, 0, 0 }
};
