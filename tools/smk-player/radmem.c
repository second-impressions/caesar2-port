/* RAD memory callbacks the Smacker library imports (RADMALLOC/RADFREE).
 * rad.h declares them lowercase __pascal; Watcom __pascal uppercases the
 * symbol, giving the RADMALLOC/RADFREE the delinked object references. */
#include <stdlib.h>

void *__pascal radmalloc(unsigned int size)
{
    return size ? malloc(size) : (void *)0;
}

void __pascal radfree(void *ptr)
{
    if (ptr) free(ptr);
}
