# Mac PPC verification of type cleanups

Methodology: scanned all 1575 functions in MAC/extracted/French retail/Caesar_II_1.0_fr.pef
for TOC-resolved global accesses. For each global, extracted load/store widths and the
lbz+extsb / lha / sth / stw patterns that encode source-level signed-ness and storage size.

Mac compiler: CodeWarrior Pro 1 for PowerPC, where `char` defaults to SIGNED.
Watcom WCC 10.0a (-mf -4r): `char` defaults to UNSIGNED (verified via 1-line probe).

## Validations

All cast removals from this session are CONFIRMED by the Mac binary:

| Global | Decl | Mac signal | Cleanup |
|--------|------|------------|---------|
| tracking_army | short | lha=118 sth=8 (signed short) | 57 redundant (signed short) casts removed |
| citizen_a | short | lha=71 sth=13 (signed short) | redundant casts removed |
| temp_army | short | lha=164 sth=16 (signed short) | redundant casts removed |
| created_army_no | short | lha=152 sth=2 (signed short) | redundant casts removed |
| army_a | short | lha=63 sth=8 (signed short) | redundant casts removed |
| q_lv | signed char | lbz+extsb=41 stb=1 (signed char) | (signed char)q_lv casts removed (override already in place) |
| gmn_x, gmn_y | int | lwz=181 stw=96 (int) | (unsigned char) casts removed (assignment to char field auto-truncates) |
| rand128, rand8 | int | lwz only (int) | kept (short)rand128 / (unsigned char)rand8 - real semantics |

## Non-actionable findings (source revision drift)

Mac source is 1996-11; PS source is ~1995. A few globals have different storage types:

| Global | PS decl & storage | Mac access | Reason |
|--------|------|------------|--------|
| screen_mode | char (1B gap) | lwz/stw (4B int) | Widened to int in 1996 Mac source |
| mouse_left_button | char (1B gap) | lwz heavy | Possibly widened in Mac source |

## ABI-default signedness differences

The following PS `char` globals show signed reads (lbz+extsb) in Mac, NOT a source bug:
* forum_dept, forum_dept_over, empire, warned_of_emperor_reply_month/level, q_people_list
Reason: Mac PPC compiler treats `char` as signed; WCC -mf treats `char` as unsigned.
Same C source, different codegen.

## Globals validated as correctly typed (Mac says int + PS dword storage)

* top_lv_x, top_lv_y: int (Mac uses lwz; PS uses `mov al, byte ptr [G]` as optimization
  when only low byte needed for a byte-field assignment, not a type bug)
* x_bit, y_bit, hlite_off_x, hlite_off_y: int (PS-side casts removed)
* placing_flags, reg_placing_flags: int (cast-to-char on OR-into-byte-field redundant)
