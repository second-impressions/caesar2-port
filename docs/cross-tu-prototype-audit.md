# Cross-TU prototype consistency audit (Mac PPC + PS asm verified)

## Methodology

For each .c file in `decomp/src/`, parse the AST with `c2.commands.c_source.parse_c`
(pycparser-based) and collect:
  - Functions DEFINED (body present)
  - Functions DECLARED (extern/prototype only)
  - Functions CALLED (FuncCall nodes with name + arg count)

Cross-check by walking 37 TUs in parallel:
  1. **Undeclared cross-TU calls** -- function called without prototype in caller's TU
     (caller relies on K&R implicit-int)
  2. **Type-level prototype mismatches** -- same function declared differently across TUs
     (return type or param types differ, ignoring param names)
  3. **Arg-count mismatches** -- call site passes wrong number of args vs definition

## Findings

### Implicit-int call patterns (858 undeclared cross-TU calls)

None of the .c files include `c2_funcs.h` -- each maintains hand-written
forward declarations.  When a function is called without a prototype visible
in the TU, WCC silently applies K&R implicit-int return type assumption.

For functions returning `void` (710 of the 858), the implicit-int is
harmless -- caller just ignores the return.  For 10 char-returning functions
without prototype, the caller treats `eax` as int but callee only sets `al`;
in most cases the caller assigns to a char target via `mov [G], al` which
works correctly anyway.

**Confirmed intentional**: `int_c2.c` has an explicit source comment
("get_heading is char-returning in common.c; sa08 uses it as int (PS shows
no movsx/mask after the call), so we declare it implicitly here").  Adding
the `char get_heading` prototype to int_c2.c regresses 6 functions by
hundreds of bytes total (citizen_go_to_target 12->144b, region_go_to_target
67->497b, etc.).  PS source itself is missing this prototype.

Adding the prototype to battle.c instead was byte-neutral.

### Type-level prototype mismatches (1 found)

**`font_no`** -- canonical definition in `lib32.c`:
  `void font_no(int value, char pad_char, char *suffix, int x, int y, unsigned char *font, int color)`

8 other TUs (controls.c, debug.c, message.c, mmedia.c, pm_map1.c, pm_map2.c,
pm_map3.c, screens.c) declared param 2 as `int pad_char` instead of `char`.

Fixed in commit -- byte-neutral via Watcall (caller passes via EDX register
regardless of declared param size).

### Arg-count mismatches (9 found)

**Fixed:**
  - `region_map_screen()` in action.c (5 sites) - defined `(int do_black_out)`,
    callers passed no args.  PS asm happens to have `eax=1` from preceding cmp,
    matching the implicit pass.  Made explicit via `region_map_screen(1)` --
    byte-neutral.

**Kept (PS asm needs the divergent form):**
  - `place_righthalf_diamond(0)` in pm_map3.c (4 sites) - defined as `(void)`,
    callers pass (0).  Removing the (0) regresses mid3_line_with_sides_base
    by 1 byte.  PS source had the (0) too.

## Lesson

Cross-TU prototype HYGIENE matters less than EXACT MATCH with PS source.
When PS source had missing/wrong prototypes, our source must replicate them
byte-for-byte.  The Mac PPC binary is a useful cross-check: when Mac shows
extension and our TU has no prototype, the missing prototype is intentional
(Mac compiles the proper char-returning function under prototype visibility,
but PS source had no prototype).
