// C:\DEVEL\PROJECTS\SMACK\20\smackinp.cpp
//
// Smacker input/playback module — wraps the Smacker SDK's frame-pump
// state behind the SMACK* entry points (SMACKOPEN, SMACKDOFRAME,
// SMACKWAIT, etc.) consumed by smacker.c.
//
// Only the storage is scaffolded here; no function bodies have been
// decompiled yet.  SMACK* prototypes (and pragmas) live in smacker.h
// and the auto-stub generator supplies empty bodies via stubs.c.

int  lowloaded;
int  sounds;
int  trackbuf;
int  simspeed;

// ── Rule 45 SYM_TEMP padding ─────────────────────────────────────────
//
// PS.EXE shows 8 bytes `20 20 00 00 20 20 00 00` between the end of
// smacker.obj's _TEXT (last function: `show_smksum_screen`, 1-byte
// `ret`) and the start of the next .obj's _TEXT (first function:
// `_DLL_read` at 0x13A0F, from the linked-in `smackw32.lib`).
//
// Per Rule 45 (`docs/watcom-codegen-patterns.md`), under flat model
// `-mf` Watcom routes every SYM_TEMP static — including the backing
// store for `char[N] = "..."` aggregate-init locals — into
// `SEG_CODE` instead of `_DATA`.  These cluster at the START of each
// .obj's _TEXT contribution.  The 8 bytes above are TWO 4-byte
// SYM_TEMPs (each `"  \0\0"`) from `smackw32.lib`'s first .obj,
// which used `char x[4] = "  ";` somewhere internally.
//
// We don't have the smackw32 source, so we emulate the layout by
// emitting the same two SYM_TEMPs at the start of smackinp.obj's
// _TEXT (smackinp.obj is the next .obj after smacker.obj in our
// alphabetical link order, and currently contributes no code).
// Watcom merges the two empty function bodies into a single shared
// 1-byte `c3` at offset 0x8, so total TEXT contribution is exactly
// 9 bytes (8 SYM_TEMP + 1 shared `ret`).  The two pad functions are
// never called; their PUBDEFs are harmless.
void __smackw32_text_pad1(void) { char x[4] = "  "; (void)x; }
void __smackw32_text_pad2(void) { char y[4] = "  "; (void)y; }
