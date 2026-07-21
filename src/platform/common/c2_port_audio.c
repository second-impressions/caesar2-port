#include <stddef.h>

#include "c2_data.h"

int init_sample_buffer(int sample_count)
{
    (void)sample_count;
    return 1;
}

void free_sample_buffer(int sample_count)
{
    (void)sample_count;
}

int init_tune_buffer(void)
{
    return 1;
}

void free_tune_buffer(void)
{
}

void start_sounds(void)
{
    c2inf.samples_on = 0;
    c2inf.tunes_on = 0;
}

void stop_sounds(void)
{
}

void play_tune(char *filename, int loop_count)
{
    (void)filename;
    (void)loop_count;
}

void stop_tune(void)
{
}

void set_sequences_volume(void)
{
}

void set_samples_volume(void)
{
}

void stop_samples(void)
{
}

void stop_all_sounds(void)
{
}

void continue_db(void)
{
}

void stop_db(void)
{
}

void set_db_sound(char *filename)
{
    (void)filename;
}

void set_pri_sound(char *filename)
{
    (void)filename;
}

void set_sec_sound(char *filename)
{
    (void)filename;
}

void pos_sound(void)
{
}

void neg_sound(void)
{
}

void high_beep(void)
{
}

void low_beep(void)
{
}

void vhigh_beep(void)
{
}

void init_battle_ambients(void) {}
void init_city_ambients(void) {}
void init_prov_ambients(void) {}
void set_sound(char *filename, int loop_count)
{
    (void)filename;
    (void)loop_count;
}
void set_missile_fight_fx(int event) { (void)event; }
void set_battle_march_fx(int unit_type) { (void)unit_type; }
void set_battle_death_fx(int unit_type) { (void)unit_type; }
void set_battle_fight_fx(int event) { (void)event; }
void set_this_ambient(int ambient_idx) { (void)ambient_idx; }
void set_missile_fire_fx(int missile_type) { (void)missile_type; }
void sooth_mood(void) {}
void play_ambient_fx(void) {}
int get_old_mood(void) { return 0; }
void set_city_ambient(int building_kind) { (void)building_kind; }
void set_ambient_minimum(int ambient_idx, int minimum_delay)
{
    (void)ambient_idx;
    (void)minimum_delay;
}
void set_prov_ambient(int event) { (void)event; }
