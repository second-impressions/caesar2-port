# Mac PPC verification of function signatures

Approach: scan 1575 named functions in `Caesar_II_1.0_fr.pef` for PowerPC PowerOpen ABI
signals about declared parameter and return types.

ABI keys:
- Args passed in r3-r10 (integer types promoted to int)
- Returns in r3 (char/short returns NOT extended by callee; caller extends if needed)
- Char loads use lbz (no signedness) followed by extsb for signed, clrlwi r,r,24 for unsigned
- Short loads use lha (signed) or lhz (unsigned)

## Detection methodology

### Return type
At every `bl <func>` call site, look 1-2 instructions ahead:
- `extsb r3, r3` (or after `mr rD, r3` then `extsb rD, rD`) -> caller treats return as signed char
- `extsh r3, r3` -> signed short
- `clrlwi r3, r3, 24` (or 0x18) -> unsigned char
- `clrlwi r3, r3, 16` (or 0x10) -> unsigned short
- `stw r3, ...` / `mr rD, r3` / `cmpwi r3, ...` -> int (full word)

### Parameter type
At function entry, look at the first informative use of r3-r10:
- Same patterns as above on r3 (= arg1), r4 (= arg2), etc.
- Track register flow through `mr` to follow saved params
- Stop scanning after the register is overwritten by an unrelated value

## Findings

Three real type mismatches found and fixed:

| Function | Issue | Mac signal | Action |
|----------|-------|------------|--------|
| `get_reg_buildings_in_radius` | param4 `int building_kind` | `clrlwi r7, 0x18` (unsigned char) | Change to `unsigned char` -- -23b residue (191b -> 168b) |
| `one_letter` | param1 `int letter` | `clrlwi r4, 0x18` (unsigned char) | Change to `unsigned char` -- removed 5 `(unsigned char)letter` casts, byte-neutral |
| `city_test_for_road` | return `int` | All callers `clrlwi r3, 0x18` | Change to `unsigned char` -- removed 6 `(unsigned char)f(...)` casts, byte-neutral |

## Non-actionable findings

- `check_clock_ferret_move`, `check_anti_ferret_move`: return `signed char`, Mac callers use unsigned. 
  Returns `-1` as a sentinel; callers convert to `0xff`. Already byte-exact. Leave as-is.
- `affected_by_cover1/2`: return `char`, Mac callers extend to int. Function already byte-exact.
- `get_letter_width`: param `int letter`, body `(char)letter`. Source already has cast at body, not signature. Leave as-is.
- `change_sized`, `change_reg_sized`: params declared int, stored as bytes. Already byte-exact.

## ABI default char difference (reminder)

WCC -mf treats `char` as unsigned by default. CodeWarrior Pro 1 for PowerPC treats `char` as
signed by default. The same `char foo` parameter compiles to `movzx` in WCC and `extsb` in PPC.
Signedness mismatches between PS and Mac on `char` params/returns are ABI artifacts, not bugs.
