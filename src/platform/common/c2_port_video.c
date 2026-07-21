#include "c2_port.h"

void start_smacking(char *filename, int left, int top, int mode)
{
    (void)filename;
    (void)left;
    (void)top;
    (void)mode;
}

int continue_smacking(int left, int top, int mode)
{
    (void)left;
    (void)top;
    (void)mode;
    return 0;
}

void stop_smacking(void)
{
}

int are_smacking(void)
{
    return 0;
}

void wvbl2(void)
{
    c2_port_wait_vblank();
}

void set_vga_256x(void)
{
}

void unset_vga_256x(void)
{
}
