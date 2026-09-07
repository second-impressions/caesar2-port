/*
 * Force-included (-include) into every recovered translation unit on
 * macOS. The recovered engine defines void random(void); glibc declares
 * libc's random() only outside -std=c11, Apple's stdlib.h always. Take the
 * system header first, under its own name, then give the engine's function
 * a link name of its own for the rest of the unit.
 */
#ifndef C2_DARWIN_PREFIX_H
#define C2_DARWIN_PREFIX_H

#include <stdlib.h>
#define random c2_engine_random

#endif /* C2_DARWIN_PREFIX_H */
