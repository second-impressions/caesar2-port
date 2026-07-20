#include <stdio.h>
#include <string.h>

#define SCREEN_ROWS 64
#define SOURCE_SIZE 4096

typedef void (*hat_writer)(unsigned char *, int);

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

int main(void)
{
    run_hat("small-full", write_small_diamond_hat);
    run_hat("small-left", write_small_diamond_lefthat);
    run_hat("small-right", write_small_diamond_righthat);
    run_hat("medium-full", write_medium_diamond_hat);
    run_hat("medium-left", write_medium_diamond_lefthat);
    run_hat("medium-right", write_medium_diamond_righthat);
    run_hat("large-full", write_large_diamond_hat);
    run_hat("large-left", write_large_diamond_lefthat);
    run_hat("large-right", write_large_diamond_righthat);
    return 0;
}
