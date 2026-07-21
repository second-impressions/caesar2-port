#include "c2_asm_routines.h"

/* Complete portable implementation surface for the recovered assembly ABI. */
#define C2_ROUTINE_VOID_0(name) \
    void name(void) {}
#define C2_ROUTINE_VOID_1(name, t1) \
    void name(t1 c2_arg1) {}
#define C2_ROUTINE_VOID_2(name, t1, t2) \
    void name(t1 c2_arg1, t2 c2_arg2) {}
#define C2_ROUTINE_VOID_3(name, t1, t2, t3) \
    void name(t1 c2_arg1, t2 c2_arg2, t3 c2_arg3) {}
#define C2_ROUTINE_INT_2(name, t1, t2) \
    int name(t1 c2_arg1, t2 c2_arg2) { return 0; }
#define C2_ROUTINE_INT_3(name, t1, t2, t3) \
    int name(t1 c2_arg1, t2 c2_arg2, t3 c2_arg3) { return 0; }
#define C2_ASM_STUB(kind, ...) kind(__VA_ARGS__)
#define C2_ASM_IMPLEMENTED(kind, ...)
#include "c2_asm_routines.def"
#undef C2_ASM_STUB
#undef C2_ASM_IMPLEMENTED
#undef C2_ROUTINE_VOID_0
#undef C2_ROUTINE_VOID_1
#undef C2_ROUTINE_VOID_2
#undef C2_ROUTINE_VOID_3
#undef C2_ROUTINE_INT_2
#undef C2_ROUTINE_INT_3
