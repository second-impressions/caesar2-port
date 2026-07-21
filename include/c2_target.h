#ifndef C2_TARGET_H
#define C2_TARGET_H

/*
 * Target and feature selection for the Caesar II reconstruction.
 *
 * PLATFORM macros name a build platform:
 *
 *   PLATFORM_DOS       the DOS release (PS.EXE), retained as the byte-exact
 *                      reconstruction target.
 *   PLATFORM_WINDOWS   the shipped Windows source witness. Which Windows
 *                      build is meant is C2_PATCHLEVEL's job.
 *   PLATFORM_PORTABLE  the modern SDL-based continuation. This platform
 *                      keeps recovered engine code shared while replacing
 *                      shipped platform services behind portable shims.
 *
 * Exactly one platform is 1 and every other platform is 0. Builds should
 * select their platform explicitly. An unspecified build defaults to the
 * original DOS platform without inferring a platform from compiler identity.
 */
#if !defined(PLATFORM_DOS) && !defined(PLATFORM_WINDOWS) && !defined(PLATFORM_PORTABLE)
#  define PLATFORM_DOS 1
#endif
#ifndef PLATFORM_DOS
#  define PLATFORM_DOS 0
#endif
#ifndef PLATFORM_WINDOWS
#  define PLATFORM_WINDOWS 0
#endif
#ifndef PLATFORM_PORTABLE
#  define PLATFORM_PORTABLE 0
#endif
#if PLATFORM_DOS + PLATFORM_WINDOWS + PLATFORM_PORTABLE != 1
#  error "exactly one PLATFORM_* must be selected"
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
#define C2_FEAT_TILE_REFRESH      PLATFORM_DOS

/* The Windows build-A rotate handlers clamp the pseudo-map viewport
 * with a pm_limits() tail call that the DOS build does not make
 * (verified at C2WIN 0x4b6f46 / 0x4b6f99). */
#define C2_FEAT_ROTATE_PM_LIMITS  PLATFORM_WINDOWS

/* The Windows build resets each compression work-table pointer to
 * null after freeing it in free_pumping_memory; the DOS build leaves
 * the pointers dangling (verified at C2WIN 0x43c7e8 vs C2 0x6fffc). */
#define C2_FEAT_PUMP_FREE_NULLS   PLATFORM_WINDOWS

/* The DOS promotion offer spins a nested input loop over the
 * want-promotion box; the Windows port made the box modal (it returns
 * the choice) and re-shows any open advisor windows after a review
 * choice (verified at C2WIN 0x454e88 vs C2 0x554b1). */
#define C2_FEAT_MODAL_PROMOTION   PLATFORM_WINDOWS

/* The Windows wait-state transition preserves visibility bit 0 while
 * clearing bit 1, then sets bit 0.  The DOS build clears both low bits
 * before the same final set (verified at C2WIN 0x477fae vs C2 0x4dd39). */
#define C2_FEAT_WAIT_KEEP_VISIBLE PLATFORM_WINDOWS

/* The Windows name-entry dialog seeds the format-buffer count from
 * the cleared insert cursor; the DOS build clears this_letter instead
 * (verified at C2WIN 0x4b96d2 vs C2 0x34cfa). */
#define C2_FEAT_NAME_EDIT_FB_COUNT PLATFORM_WINDOWS

/* The portable target accepts the text resources shipped with both the
 * original 1995 engine and the expanded 1996/Windows UI.  The shipped DOS
 * and Windows targets retain their version-specific source paths. */
#ifndef C2_FEAT_TEXT_ASSET_COMPAT
#  define C2_FEAT_TEXT_ASSET_COMPAT PLATFORM_PORTABLE
#endif

/* The shipped builds held file-operation messages for throughput-bound idle
 * frames after synchronous I/O had completed (1,000 after save, 200 after
 * load). A paced portable renderer would turn those CPU-era cosmetic spins
 * into fixed multi-second delays, so portable builds return when I/O ends. */
#define C2_FEAT_POST_FILE_BUSY_WAIT (!PLATFORM_PORTABLE)

/* Read-only engine observations and their smoke driver are development
 * instrumentation. CMake selects them only for portable Debug builds. */
#if defined(C2_DEBUG_BUILD)
#  define C2_FEAT_DEBUG_OBSERVATION PLATFORM_PORTABLE
#else
#  define C2_FEAT_DEBUG_OBSERVATION 0
#endif

/* Native fatal-signal diagnostics are compiled only where the selected Debug
 * backend provides an implementation. */
#if defined(C2_ENABLE_POSIX_CRASH_HANDLER)
#  define C2_FEAT_DEBUG_CRASH_HANDLER PLATFORM_PORTABLE
#else
#  define C2_FEAT_DEBUG_CRASH_HANDLER 0
#endif

#endif /* C2_TARGET_H */
