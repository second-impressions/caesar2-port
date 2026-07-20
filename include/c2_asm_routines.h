#ifndef C2_ASM_ROUTINES_H
#define C2_ASM_ROUTINES_H

typedef void (*c2_legacy_callback)(void);

#define C2_ROUTINE_VOID_0(name) void name(void);
#define C2_ROUTINE_VOID_1(name, t1) void name(t1);
#define C2_ROUTINE_VOID_2(name, t1, t2) void name(t1, t2);
#define C2_ROUTINE_VOID_3(name, t1, t2, t3) void name(t1, t2, t3);
#define C2_ROUTINE_INT_2(name, t1, t2) int name(t1, t2);
#define C2_ROUTINE_INT_3(name, t1, t2, t3) int name(t1, t2, t3);
#include "c2_asm_routines.def"
#undef C2_ROUTINE_VOID_0
#undef C2_ROUTINE_VOID_1
#undef C2_ROUTINE_VOID_2
#undef C2_ROUTINE_VOID_3
#undef C2_ROUTINE_INT_2
#undef C2_ROUTINE_INT_3

#endif /* C2_ASM_ROUTINES_H */
