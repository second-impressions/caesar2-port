// C:\DEVEL\PROJECTS\SMACK\20\sndail.cpp
//
// Caesar II ↔ Smacker AIL audio bridge.  Provides the `LOWSOUND*`
// callbacks that Smacker invokes (and `_SetSmackAILDigDriver` for the
// game side to plug in a Miles AIL driver).
//
// Only the storage is scaffolded here; no function bodies have been
// decompiled yet.  The auto-stub generator in c2.commands.decomp_verify
// supplies empty definitions for the public functions via stubs.c.
//
// Note: in the original PS source the data was file-scope ``static``,
// but the four diamond-rendering modules (dialarga.asm, dialargb.asm,
// dia_medi.asm, dia_smal.asm) reach into `sndinit` as a 20-byte shared
// scratch buffer (one dword per diamond size at offsets +2/+6/+10/+14).
// We therefore define the symbols with external linkage so the .asm
// modules' EXTRN refs resolve at link time.

int   fss;
int   didaninit;
int  *SmackAILDigDriver;
int   setbyprog;
int   count;
int   sndinit[5];     // shared dia_*.asm scratch
#ifdef __WATCOMC__
// `timer` is EXTRN'd by the DOS diamond .asm modules.  Under the MSVC
// win build there is no .asm and c2_funcs.h force-declares `int timer(int)`,
// so the data symbol of the same name is omitted to avoid the clash.
int   timer;          // separate location at 0x14898
#endif
