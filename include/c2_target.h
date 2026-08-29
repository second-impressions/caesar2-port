#ifndef C2_TARGET_H
#define C2_TARGET_H

/*
 * Target and feature selection for the Caesar II reconstruction and its port.
 *
 * NAMESPACES
 * ==========
 * Two prefixes are in use, and the difference is load-bearing:
 *
 *   PLATFORM_* / C2_*   shared with caesar2-reconstruction.  These names
 *                       appear verbatim in the byte-exact upstream sources,
 *                       so recovered code carrying them cherry-picks in both
 *                       directions without edits.  Never rename one.
 *
 *   PORT_*              added by this repository.  Anything the port defines
 *                       for itself -- a host platform, a behavioral feature,
 *                       a bug fix, a build selector -- carries this prefix,
 *                       so a guard's provenance is readable at the use site
 *                       and a merge conflict involving port-added code is
 *                       obvious on sight.
 *
 * PLATFORMS
 * =========
 * Shipped targets, shared with the reconstruction:
 *
 *   PLATFORM_DOS          the DOS release (PS.EXE), retained as the
 *                         byte-exact reconstruction target.
 *   PLATFORM_WINDOWS      the shipped 1996 Windows source witness.  Which
 *                         Windows build is meant is C2_PATCHLEVEL's job.
 *                         This is NOT the modern Windows host target.
 *
 * Port targets, added here:
 *
 *   PORT_PLATFORM_LINUX   the native Linux SDL continuation.
 *   PORT_PLATFORM_WIN32   the native modern Windows SDL continuation, built
 *                         by MinGW-w64 or MSVC.  Deliberately distinct from
 *                         PLATFORM_WINDOWS: that macro selects recovered
 *                         1996 engine behavior, this one selects a
 *                         present-day host backend.  A build can be a Windows
 *                         binary (PORT_PLATFORM_WIN32) while still using the
 *                         DOS-era engine semantics (PLATFORM_WINDOWS = 0).
 *   PORT_PLATFORM_WASM    the browser SDL continuation compiled by Emscripten.
 *
 * Exactly one target platform is 1 and every other target platform is 0.
 * PORT_PLATFORM is the derived family selector shared by the Linux, Win32,
 * and Wasm continuations; build systems may export it for guards that precede
 * the first project header, but its value must match the selected leaf
 * target.  An unspecified build defaults to DOS without inferring a platform
 * from compiler identity.
 */
#if !defined(PLATFORM_DOS) && !defined(PLATFORM_WINDOWS) && \
    !defined(PORT_PLATFORM_LINUX) && !defined(PORT_PLATFORM_WIN32) && \
    !defined(PORT_PLATFORM_WASM)
#  define PLATFORM_DOS 1
#endif
#ifndef PLATFORM_DOS
#  define PLATFORM_DOS 0
#endif
#ifndef PLATFORM_WINDOWS
#  define PLATFORM_WINDOWS 0
#endif
#ifndef PORT_PLATFORM_LINUX
#  define PORT_PLATFORM_LINUX 0
#endif
#ifndef PORT_PLATFORM_WIN32
#  define PORT_PLATFORM_WIN32 0
#endif
#ifndef PORT_PLATFORM_WASM
#  define PORT_PLATFORM_WASM 0
#endif
#if PLATFORM_DOS + PLATFORM_WINDOWS + PORT_PLATFORM_LINUX + PORT_PLATFORM_WIN32 + \
    PORT_PLATFORM_WASM != 1
#  error "exactly one PLATFORM_*/PORT_PLATFORM_* target must be selected"
#endif
#ifndef PORT_PLATFORM
#  define PORT_PLATFORM (PORT_PLATFORM_LINUX || PORT_PLATFORM_WIN32 || PORT_PLATFORM_WASM)
#elif PORT_PLATFORM != (PORT_PLATFORM_LINUX || PORT_PLATFORM_WIN32 || PORT_PLATFORM_WASM)
#  error "PORT_PLATFORM must match the selected target family"
#endif

/* Historical memory-model and calling-convention keywords have no ABI effect
 * in the flat portable build, but remain in recovered declarations. */
#if PORT_PLATFORM
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
 * "which build of the game".
 *
 * The prefix says who owns the difference:
 *
 *   C2_FEAT_*    a difference between the two shipped 1990s builds, each
 *                witnessed in original machine code.  Shared verbatim with
 *                caesar2-reconstruction.
 *   PORT_FEAT_*  a deliberate difference introduced by this port, selected
 *                by PORT_PLATFORM rather than by a shipped target.
 *   PORT_FIX_*   a correction to an original defect, defaulting on for port
 *                targets so a retained DOS or Windows build keeps the
 *                original behavior.
 *
 * `grep -E 'C2_FEAT_|PORT_FEAT_|PORT_FIX_' include src` is the catalogue.
 */

/* Dirty-tile renderer: the DOS build marks clean screen tiles for
 * redraw (setup_whole/map/battle_screen_refresh) after UI-state
 * changes; the Windows port repaints differently and dropped these
 * calls at all but a handful of sites (each guarded site verified
 * against CAESAR2.EXE machine code, 2026-07-17). */
/* Selected explicitly in the complete target profile below. */

/* The Windows build-A rotate handlers clamp the pseudo-map viewport
 * with a pm_limits() tail call that the DOS build does not make
 * (verified at C2WIN 0x4b6f46 / 0x4b6f99). */


/* The Windows build resets each compression work-table pointer to
 * null after freeing it in free_pumping_memory; the DOS build leaves
 * the pointers dangling (verified at C2WIN 0x43c7e8 vs C2 0x6fffc). */


/* The DOS promotion offer spins a nested input loop over the
 * want-promotion box; the Windows port made the box modal (it returns
 * the choice) and re-shows any open advisor windows after a review
 * choice (verified at C2WIN 0x454e88 vs C2 0x554b1). */


/* The Windows audio port applies the configured effects volume to each
 * allocated sample handle; DOS sets the digital driver's master volume
 * (verified at C2WIN 0x40149b vs C2 0x11a53). */

/* DOS Smacker playback changes to the movie's CD path before closing and
 * restores the main path afterwards. The Windows port opens movies through
 * its native file path and omits both calls. */
/* Additional recovered renderer choices needed by third targets. */

/* Every shipped target explicitly chooses every recovered behavior. */
#if PLATFORM_DOS
#  define C2_FEAT_TILE_REFRESH                  1
#  define C2_FEAT_ROTATE_PM_LIMITS              0
#  define C2_FEAT_PUMP_FREE_NULLS               0
#  define C2_FEAT_MODAL_PROMOTION               0
#  define C2_FEAT_SMACK_CD_PATH                 1
#  define C2_FEAT_REGION_SIDED_DRAW             0
#  define C2_FEAT_CITY_TOP_DIRECTION_INIT       0
#  define C2_FEAT_BATTLE_ZOOM2_ROTATE_CLAMP     1
#  define C2_FEAT_SOFTWARE_BATTLE_SETUP         1
#elif PLATFORM_WINDOWS
#  define C2_FEAT_TILE_REFRESH                  0
#  define C2_FEAT_ROTATE_PM_LIMITS              1
#  define C2_FEAT_PUMP_FREE_NULLS               1
#  define C2_FEAT_MODAL_PROMOTION               1
#  define C2_FEAT_SMACK_CD_PATH                 0
#  define C2_FEAT_REGION_SIDED_DRAW             1
#  define C2_FEAT_CITY_TOP_DIRECTION_INIT       1
#  define C2_FEAT_BATTLE_ZOOM2_ROTATE_CLAMP     0
#  define C2_FEAT_SOFTWARE_BATTLE_SETUP         0
#elif PORT_PLATFORM
/* Explicit continuation profile: software UI and host-backed media/files. */
#  define C2_FEAT_TILE_REFRESH                  0
#  define C2_FEAT_ROTATE_PM_LIMITS              0
#  define C2_FEAT_PUMP_FREE_NULLS               0
#  define C2_FEAT_MODAL_PROMOTION               0
#  define C2_FEAT_SMACK_CD_PATH                 0
#  define C2_FEAT_REGION_SIDED_DRAW             1
#  define C2_FEAT_CITY_TOP_DIRECTION_INIT       1
#  define C2_FEAT_BATTLE_ZOOM2_ROTATE_CLAMP     1
#  define C2_FEAT_SOFTWARE_BATTLE_SETUP         1
#else
#  error "target has no explicit recovered behavior profile"
#endif


/* The portable target accepts the text resources shipped with both the
 * original 1995 engine and the expanded 1996/Windows UI.  The shipped DOS
 * and Windows targets retain their version-specific source paths. */
#ifndef PORT_FEAT_TEXT_ASSET_COMPAT
#  define PORT_FEAT_TEXT_ASSET_COMPAT PORT_PLATFORM
#endif

/* The shipped DOS hotkey path moves the mouse cursor by eight pixels for
 * each arrow-key event. Portable builds instead expose held arrow state to
 * the recovered map scroller, while retaining scan-code delivery to editors. */
#ifndef PORT_FEAT_ARROW_KEY_SCROLL
#  define PORT_FEAT_ARROW_KEY_SCROLL PORT_PLATFORM
#endif

/* The shipped builds held file-operation messages for throughput-bound idle
 * frames after synchronous I/O had completed (1,000 after save, 200 after
 * load). A paced portable renderer would turn those CPU-era cosmetic spins
 * into fixed multi-second delays, so portable builds return when I/O ends. */
#define PORT_FEAT_POST_FILE_BUSY_WAIT (!PORT_PLATFORM)

/* Portable hosts save screenshots in a widely supported lossless format.
 * Shipped targets retain the recovered indexed LBM writer and filenames. */
#define PORT_FEAT_PNG_SCREENSHOTS PORT_PLATFORM

/* The startup notice and the about box both identify the build the user is
 * actually running. Shipped targets read their fixed "Version 1.1" and
 * release-date lines from c2.eng; portable builds substitute this port's
 * exact version tag, which no shipped text asset can carry. */
#define PORT_FEAT_BUILD_STAMP PORT_PLATFORM

/* Portable hosts can put the game down while their own chrome is in front of
 * it. The pause itself stays the recovered act_pause(); the port only asks for
 * it and restores what the player had chosen. Shipped targets have no such
 * chrome, so the hook is compiled out of them entirely. */
#define PORT_FEAT_HOST_PAUSE PORT_PLATFORM

/* The DOS province construction lists use press-drag-release interaction.
 * Keep their initial release from dismissing the list in portable builds so
 * an ordinary click behaves like the city construction lists; dragging to an
 * entry and releasing remains available. */
#define PORT_FEAT_STICKY_REGION_DROPDOWNS PORT_PLATFORM

/* The shipped city/province score chooses its next XMI branch from the
 * simulation RNG. That RNG correctly stops while paused, but the MIDI branch
 * callback does not, causing one phrase to repeat indefinitely. Portable
 * builds use a separate deterministic branch sequence only while paused. */
#define PORT_FIX_PAUSED_MUSIC_VARIETY PORT_PLATFORM

/* Loading restarts the portable engine loop. A mouse button still held from
 * the load dialog can reach the province builder without its preceding press,
 * making the recovered empty-tool path restore an uninitialized treasury
 * snapshot. Ignore region builds with no selected tool and drain load input. */
#define PORT_FIX_REGION_IDLE_CLICK_FUNDS PORT_PLATFORM

/* Read-only engine observations and their smoke driver are development
 * instrumentation. CMake selects them only for portable Debug builds. */
#if defined(PORT_DEBUG_BUILD)
#  define PORT_FEAT_DEBUG_OBSERVATION PORT_PLATFORM
#else
#  define PORT_FEAT_DEBUG_OBSERVATION 0
#endif

/* Native fatal-signal diagnostics are compiled only where the selected Debug
 * backend provides an implementation. */
#if defined(PORT_ENABLE_POSIX_CRASH_HANDLER)
#  define PORT_FEAT_DEBUG_CRASH_HANDLER PORT_PLATFORM
#else
#  define PORT_FEAT_DEBUG_CRASH_HANDLER 0
#endif

/* The later Windows map renderer rejects pseudo-map rows past the city-map
 * boundary before each scanline pass. */
#if PLATFORM_WINDOWS
#  define C2_CHECK_PM_ROW() if (pm_shown_y >= PM_H) return
#else
#  define C2_CHECK_PM_ROW()
#endif

#endif /* C2_TARGET_H */
