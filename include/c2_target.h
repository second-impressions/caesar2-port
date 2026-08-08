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
 *   PLATFORM_LINUX     the native Linux SDL continuation.
 *   PLATFORM_WASM      the browser SDL continuation compiled by Emscripten.
 *
 * Exactly one target platform is 1 and every other target platform is 0.
 * PLATFORM_PORTABLE is the derived family selector shared by Linux and Wasm;
 * build systems may export it for guards that precede the first project
 * header, but its value must match the selected leaf target. An unspecified
 * build defaults to DOS without inferring a platform from compiler identity.
 */
#if !defined(PLATFORM_DOS) && !defined(PLATFORM_WINDOWS) && \
    !defined(PLATFORM_LINUX) && !defined(PLATFORM_WASM)
#  define PLATFORM_DOS 1
#endif
#ifndef PLATFORM_DOS
#  define PLATFORM_DOS 0
#endif
#ifndef PLATFORM_WINDOWS
#  define PLATFORM_WINDOWS 0
#endif
#ifndef PLATFORM_LINUX
#  define PLATFORM_LINUX 0
#endif
#ifndef PLATFORM_WASM
#  define PLATFORM_WASM 0
#endif
#if PLATFORM_DOS + PLATFORM_WINDOWS + PLATFORM_LINUX + PLATFORM_WASM != 1
#  error "exactly one PLATFORM_* must be selected"
#endif
#ifndef PLATFORM_PORTABLE
#  define PLATFORM_PORTABLE (PLATFORM_LINUX || PLATFORM_WASM)
#elif PLATFORM_PORTABLE != (PLATFORM_LINUX || PLATFORM_WASM)
#  error "PLATFORM_PORTABLE must match the selected target family"
#endif

/* Historical memory-model and calling-convention keywords have no ABI effect
 * in the flat portable build, but remain in recovered declarations. */
#if PLATFORM_PORTABLE
#  ifndef __far
#    define __far
#  endif
#  ifndef __pascal
#    define __pascal
#  endif
#  ifndef __cdecl
#    define __cdecl
#  endif
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

/* The Windows audio port applies the configured effects volume to each
 * allocated sample handle; DOS sets the digital driver's master volume
 * (verified at C2WIN 0x40149b vs C2 0x11a53). */
#define C2_FEAT_PER_SAMPLE_VOLUME PLATFORM_WINDOWS

/* The DOS mouse poll consumes mse_button after updating the engine state.
 * The Windows port preserves the sampled byte for its Windows input path
 * (verified at C2WIN 0x44c216 vs C2 0x25ccc). */
#define C2_FEAT_PRESERVE_MOUSE_SAMPLE PLATFORM_WINDOWS

/* DOS Smacker playback changes to the movie's CD path before closing and
 * restores the main path afterwards. The Windows port opens movies through
 * its native file path and omits both calls. */
#define C2_FEAT_SMACK_CD_PATH     PLATFORM_DOS

/* The portable target accepts the text resources shipped with both the
 * original 1995 engine and the expanded 1996/Windows UI.  The shipped DOS
 * and Windows targets retain their version-specific source paths. */
#ifndef C2_FEAT_TEXT_ASSET_COMPAT
#  define C2_FEAT_TEXT_ASSET_COMPAT PLATFORM_PORTABLE
#endif

/* The shipped DOS hotkey path moves the mouse cursor by eight pixels for
 * each arrow-key event. Portable builds instead expose held arrow state to
 * the recovered map scroller, while retaining scan-code delivery to editors. */
#ifndef C2_FEAT_ARROW_KEY_SCROLL
#  define C2_FEAT_ARROW_KEY_SCROLL PLATFORM_PORTABLE
#endif

/* The shipped builds held file-operation messages for throughput-bound idle
 * frames after synchronous I/O had completed (1,000 after save, 200 after
 * load). A paced portable renderer would turn those CPU-era cosmetic spins
 * into fixed multi-second delays, so portable builds return when I/O ends. */
#define C2_FEAT_POST_FILE_BUSY_WAIT (!PLATFORM_PORTABLE)

/* Portable hosts save screenshots in a widely supported lossless format.
 * Shipped targets retain the recovered indexed LBM writer and filenames. */
#define C2_FEAT_PNG_SCREENSHOTS PLATFORM_PORTABLE

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

/* The later Windows map renderer rejects pseudo-map rows past the city-map
 * boundary before each scanline pass. */
#if PLATFORM_WINDOWS
#  define C2_CHECK_PM_ROW() if (pm_shown_y >= PM_H) return
#else
#  define C2_CHECK_PM_ROW()
#endif

#endif /* C2_TARGET_H */
