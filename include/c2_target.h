#ifndef C2_TARGET_H
#define C2_TARGET_H

/*
 * Target and feature selection for the Caesar II reconstruction.
 *
 * TARGETS name a shipped platform build of the game:
 *
 *   C2_TARGET_DOS   the DOS release (PS.EXE) — Watcom 10.0a; the
 *                   byte-exact reconstruction target.
 *   C2_TARGET_WIN   the Windows port (reccmp target C2WIN) — MSVC; a
 *                   source-location/oracle target, not a full rebuild.
 *                   Which Windows build is meant is C2_PATCHLEVEL's job.
 *
 * Exactly one target is 1, every other target is 0.  The build selects
 * a target explicitly (`wcc386 -dC2_TARGET_DOS=1` / `cl /DC2_TARGET_WIN=1`);
 * without an explicit selection the historic compiler-to-target pairing
 * is derived so a bare compile of either toolchain still does the
 * right thing.
 */
#if !defined(C2_TARGET_DOS) && !defined(C2_TARGET_WIN)
#  ifdef _MSC_VER
#    define C2_TARGET_WIN 1
#  else
#    define C2_TARGET_DOS 1
#  endif
#endif
#ifndef C2_TARGET_DOS
#  define C2_TARGET_DOS 0
#endif
#ifndef C2_TARGET_WIN
#  define C2_TARGET_WIN 0
#endif
#if C2_TARGET_DOS + C2_TARGET_WIN != 1
#  error "exactly one C2_TARGET_* must be selected"
#endif

/*
 * PATCHLEVEL leaves room for other witnesses of the same platform
 * (CD rereleases, patches) to enter the source later.  Higher = later
 * build of that platform.  Registry so far:
 *
 *   DOS   1  debug-symbol rerelease build (the pinned PS.EXE ground truth)
 *   WIN   1  Windows build A (the CAESAR2.EXE witness)
 *
 * A feature below may condition on (target, patchlevel) once a second
 * build of a platform is transcribed.
 */
#ifndef C2_PATCHLEVEL
#  define C2_PATCHLEVEL 1
#endif

/*
 * FEATURES name a verified behavioral difference class between the
 * builds.  Guard version-specific function code with these — never with
 * raw compiler macros (`_MSC_VER`), which conflate "which compiler" with
 * "which build of the game".  `grep C2_FEAT_ include src` is the
 * catalogue of known cross-build differences.
 */

/* Dirty-tile renderer: the DOS build marks clean screen tiles for
 * redraw (setup_whole/map/battle_screen_refresh) after UI-state
 * changes; the Windows port repaints differently and dropped these
 * calls at all but a handful of sites (each guarded site verified
 * against CAESAR2.EXE machine code, 2026-07-17). */
#define C2_FEAT_TILE_REFRESH      C2_TARGET_DOS

/* The Windows build-A rotate handlers clamp the pseudo-map viewport
 * with a pm_limits() tail call that the DOS build does not make
 * (verified at C2WIN 0x4b6f46 / 0x4b6f99). */
#define C2_FEAT_ROTATE_PM_LIMITS  C2_TARGET_WIN

/* The Windows build resets each compression work-table pointer to
 * null after freeing it in free_pumping_memory; the DOS build leaves
 * the pointers dangling (verified at C2WIN 0x43c7e8 vs C2 0x6fffc). */
#define C2_FEAT_PUMP_FREE_NULLS   C2_TARGET_WIN

/* The DOS promotion offer spins a nested input loop over the
 * want-promotion box; the Windows port made the box modal (it returns
 * the choice) and re-shows any open advisor windows after a review
 * choice (verified at C2WIN 0x454e88 vs C2 0x554b1). */
#define C2_FEAT_MODAL_PROMOTION   C2_TARGET_WIN

/* The Windows wait-state transition preserves visibility bit 0 while
 * clearing bit 1, then sets bit 0.  The DOS build clears both low bits
 * before the same final set (verified at C2WIN 0x477fae vs C2 0x4dd39). */
#define C2_FEAT_WAIT_KEEP_VISIBLE C2_TARGET_WIN

/* The Windows name-entry dialog seeds the format-buffer count from
 * the cleared insert cursor; the DOS build clears this_letter instead
 * (verified at C2WIN 0x4b96d2 vs C2 0x34cfa). */
#define C2_FEAT_NAME_EDIT_FB_COUNT C2_TARGET_WIN

#endif /* C2_TARGET_H */
