#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define SCREEN_ROWS 64
#define SOURCE_SIZE 4096

typedef void (*hat_writer)(unsigned char *, int);
typedef void (*roof_writer)(unsigned char *);
typedef void (*half_hat_writer)(unsigned char *, int, int);
typedef void (*half_roof_writer)(unsigned char *, int);

unsigned char framebuffer[641 * SCREEN_ROWS];
unsigned char source_data[SOURCE_SIZE];
unsigned char *internal_screen = framebuffer;
int screen_width = 641;
int sndinit[5];
int sprite_hat_start = 9;
int sprite_start;
int sprite_x = 4;
int sprite_y = 20;
int y_length;

void write_small_diamond_hat(unsigned char *, int);
void write_small_diamond_lefthat(unsigned char *, int);
void write_small_diamond_righthat(unsigned char *, int);
void write_medium_diamond_hat(unsigned char *, int);
void write_medium_diamond_lefthat(unsigned char *, int);
void write_medium_diamond_righthat(unsigned char *, int);
void write_large_diamond_hat(unsigned char *, int);
void write_large_diamond_lefthat(unsigned char *, int);
void write_large_diamond_righthat(unsigned char *, int);
void write_small_diamond_lefthalfhat(unsigned char *, int, int);
void write_small_diamond_righthalfhat(unsigned char *, int, int);
void write_medium_diamond_lefthalfhat(unsigned char *, int, int);
void write_medium_diamond_righthalfhat(unsigned char *, int, int);
void write_large_diamond_lefthalfhat(unsigned char *, int, int);
void write_large_diamond_righthalfhat(unsigned char *, int, int);
void write_small_diamond_roof(unsigned char *);
void write_small_diamond_leftroof(unsigned char *);
void write_small_diamond_rightroof(unsigned char *);
void write_medium_diamond_roof(unsigned char *);
void write_medium_diamond_leftroof(unsigned char *);
void write_medium_diamond_rightroof(unsigned char *);
void write_large_diamond_roof(unsigned char *);
void write_large_diamond_leftroof(unsigned char *);
void write_large_diamond_rightroof(unsigned char *);
void write_small_diamond_lefthalfroof(unsigned char *, int);
void write_small_diamond_righthalfroof(unsigned char *, int);
void write_medium_diamond_lefthalfroof(unsigned char *, int);
void write_medium_diamond_righthalfroof(unsigned char *, int);
void write_large_diamond_lefthalfroof(unsigned char *, int);
void write_large_diamond_righthalfroof(unsigned char *, int);

static unsigned int framebuffer_hash(void)
{
    unsigned int hash;
    unsigned int index;

    hash = 2166136261U;
    for (index = 0; index < sizeof(framebuffer); index++) {
        hash ^= framebuffer[index];
        hash *= 16777619U;
    }
    return hash;
}

static void reset_fixture(void)
{
    unsigned int index;

    memset(framebuffer, 0x5a, sizeof(framebuffer));
    memset(source_data, 0, sizeof(source_data));
    memset(sndinit, 0, sizeof(sndinit));
    for (index = 0; index < SOURCE_SIZE - (unsigned int)sprite_hat_start;
         index++) {
        source_data[sprite_hat_start + index] =
            index % 7 == 0 ? 0 : (unsigned char)(index * 29 + 3);
    }
}

static void run_hat(const char *name, hat_writer writer)
{
    static const int depths[] = {0, 2, 5};
    static const int lengths[] = {1, 4, 8};
    unsigned int depth_index;
    unsigned int length_index;

    for (depth_index = 0;
         depth_index < sizeof(depths) / sizeof(depths[0]); depth_index++) {
        for (length_index = 0;
             length_index < sizeof(lengths) / sizeof(lengths[0]);
             length_index++) {
            reset_fixture();
            y_length = lengths[length_index];
            writer(source_data, depths[depth_index]);
            printf("%s d%d h%d %08x\n", name, depths[depth_index], y_length,
                   framebuffer_hash());
        }
    }
}

static void run_roof(const char *name, roof_writer writer)
{
    static const int lengths[] = {1, 4, 8, 16};
    unsigned int length_index;

    for (length_index = 0;
         length_index < sizeof(lengths) / sizeof(lengths[0]); length_index++) {
        reset_fixture();
        y_length = lengths[length_index];
        writer(source_data);
        printf("%s h%d %08x\n", name, y_length, framebuffer_hash());
    }
}

static void run_half_hat(const char *name, half_hat_writer writer)
{
    static const int depths[] = {0, 2, 5};
    static const int lengths[] = {1, 4, 8, 16};
    static const int edge_seams[] = {0, 2};
    unsigned int depth_index;
    unsigned int length_index;
    unsigned int seam_index;

    for (depth_index = 0;
         depth_index < sizeof(depths) / sizeof(depths[0]); depth_index++) {
        for (length_index = 0;
             length_index < sizeof(lengths) / sizeof(lengths[0]);
             length_index++) {
            for (seam_index = 0;
                 seam_index < sizeof(edge_seams) / sizeof(edge_seams[0]);
                 seam_index++) {
                reset_fixture();
                y_length = lengths[length_index];
                writer(source_data, depths[depth_index],
                       edge_seams[seam_index]);
                printf("%s d%d h%d s%d %08x\n", name,
                       depths[depth_index], y_length,
                       edge_seams[seam_index], framebuffer_hash());
            }
        }
    }
}

static void run_half_roof(const char *name, half_roof_writer writer)
{
    static const int lengths[] = {1, 4, 8, 15, 16, 17, 20};
    static const int edge_seams[] = {0, 2};
    unsigned int length_index;
    unsigned int seam_index;

    for (length_index = 0;
         length_index < sizeof(lengths) / sizeof(lengths[0]); length_index++) {
        for (seam_index = 0;
             seam_index < sizeof(edge_seams) / sizeof(edge_seams[0]);
             seam_index++) {
            reset_fixture();
            y_length = lengths[length_index];
            writer(source_data, edge_seams[seam_index]);
            printf("%s h%d s%d %08x\n", name, y_length,
                   edge_seams[seam_index], framebuffer_hash());
        }
    }
}

int main(int argc, char **argv)
{
    unsigned int index;

    if (argc == 3) {
        reset_fixture();
        y_length = atoi(argv[1]);
        write_large_diamond_righthalfroof(source_data, atoi(argv[2]));
        for (index = 0; index < sizeof(framebuffer); index++) {
            if (framebuffer[index] != 0x5a) {
                printf("%u %u\n", index, (unsigned int)framebuffer[index]);
            }
        }
        return 0;
    }

    run_hat("small-full", write_small_diamond_hat);
    run_hat("small-left", write_small_diamond_lefthat);
    run_hat("small-right", write_small_diamond_righthat);
    run_hat("medium-full", write_medium_diamond_hat);
    run_hat("medium-left", write_medium_diamond_lefthat);
    run_hat("medium-right", write_medium_diamond_righthat);
    run_hat("large-full", write_large_diamond_hat);
    run_hat("large-left", write_large_diamond_lefthat);
    run_hat("large-right", write_large_diamond_righthat);
    run_half_hat("small-left-half", write_small_diamond_lefthalfhat);
    run_half_hat("small-right-half", write_small_diamond_righthalfhat);
    run_half_hat("medium-left-half", write_medium_diamond_lefthalfhat);
    run_half_hat("medium-right-half", write_medium_diamond_righthalfhat);
    run_half_hat("large-left-half", write_large_diamond_lefthalfhat);
    run_half_hat("large-right-half", write_large_diamond_righthalfhat);
    run_roof("small-roof", write_small_diamond_roof);
    run_roof("small-leftroof", write_small_diamond_leftroof);
    run_roof("small-rightroof", write_small_diamond_rightroof);
    run_roof("medium-roof", write_medium_diamond_roof);
    run_roof("medium-leftroof", write_medium_diamond_leftroof);
    run_roof("medium-rightroof", write_medium_diamond_rightroof);
    run_roof("large-roof", write_large_diamond_roof);
    run_roof("large-leftroof", write_large_diamond_leftroof);
    run_roof("large-rightroof", write_large_diamond_rightroof);
    run_half_roof("small-left-halfroof", write_small_diamond_lefthalfroof);
    run_half_roof("small-right-halfroof", write_small_diamond_righthalfroof);
    run_half_roof("medium-left-halfroof", write_medium_diamond_lefthalfroof);
    run_half_roof("medium-right-halfroof", write_medium_diamond_righthalfroof);
    run_half_roof("large-left-halfroof", write_large_diamond_lefthalfroof);
    run_half_roof("large-right-halfroof", write_large_diamond_righthalfroof);
    return 0;
}
