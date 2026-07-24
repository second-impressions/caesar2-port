# Recovered source delta audit

Status: audited against `caesar2-reconstruction` commit `07d0bd3` on
2026-07-21.

## Policy

The `src/*.c` root is reserved for recovered Caesar II translation units.
Portable implementations live in `src/platform/common/`, concrete backends in
`src/platform/<backend>/`, and CPU translations of recovered assembly in
`src/asm/`.

A port-only edit to a recovered file is acceptable only when it does one of
the following:

- selects or delegates an actual platform operation;
- repairs a native ABI or pointer-width assumption;
- selects a named, independently switchable compatibility fix; or
- publishes a read-only observation compiled exclusively in Debug builds.

Recovered files may call same-signature compatibility functions or the narrow
`c2_port_*` adapter surface. They must not call `c2_host_*` or SDL directly.
Every `C2_FIX_*` defaults to `PLATFORM_PORTABLE`, so a retained DOS or Windows
build receives shipped behavior unless it opts into a fix explicitly.

## Recovered translation units

| File | Port-only delta | Audit result |
| --- | --- | --- |
| `action.c` | Debug observations; trailing-space name repair | Retained; both compile out outside their selected portable configurations. |
| `c2.c` | Portable entry/exit adapter, CD-bootstrap exclusion, observations, guarded graphics cleanup | Retained. The unused portable `test_cd_drive` no-op was removed; the historical body is now shipped-target-only. |
| `c2_vars.c` | Include order makes record types complete before portable extern declarations | Retained; declarations only, no engine behavior change. |
| `controls.c` | Portable forward declarations and confirmation observation | Retained; fixes modern prototype visibility and Debug-only instrumentation. |
| `data.c` | Guarded mosaic random-table sentinel | Retained; byte 64 names the value accidentally supplied by the following `mouse_ptr` object in both shipped binaries and removes linker-layout-dependent rendering. |
| `display.c` | Portable fatal-exit trap and complete VGA-movie branch | Retained. The VGA movie function genuinely mixes mode switching with recovered skip/control flow, so a selected body is appropriate. |
| `evolver.c`, `map.c` | Portable prototypes for calls that historically relied on implicit declarations | Retained; required to prevent modern ABI inference while preserving shipped call-site behavior. |
| `gloops.c` | Observations, text-resource capability selection, direct `provincial_difficulty` indexing | Retained. The direct array expression replaces a linker-layout-dependent out-of-bounds alias while naming the same recovered data. |
| `hotkeys.c` | Mutable cheat buffer and PNG screenshot selection | Retained. PNG encoding now delegates to `c2_port_save_screenshot`; the recovered file no longer calls the host API directly. |
| `lib32.c` | DOS body selection, portable input/timing/exit adapters, mutable numeric buffer | Retained. Redundant POSIX aliases and portable definitions of historical ABI keywords were removed. |
| `loadsave.c` | User-data operations, transactional save codec, success handling, observations, busy-wait feature | Retained. `loadmodel` was corrected to read immutable data through `readfile`/`--asset-root` instead of the process working directory. |
| `message.c` | Modal observation | Retained; Debug-only and read-only. |
| `mmedia.c` | Help-text repair and tutorial observation | Retained. The repair call is now explicitly portable-and-fix guarded rather than merely becoming a no-op in shipped builds. |
| `pcsound.c` | Larger guarded XMI buffer, portable speech replacement, portable Miles implementation | Retained. Dead raw-descriptor speech refill and obsolete Smacker-AIL bridge bodies are no longer compiled for the portable target. Watcom-only pragmas are DOS-selected. |
| `refresh.c` | Exclusion of banked physical refresh | Retained; `c2_port_compat.c` supplies the same-symbol framebuffer publication implementation. |
| `screens.c` | Structural compatibility with early and late official text assets | Retained; only verified resource/engine evolution points are selected. The native-width landfill pointer correction matches current reconstruction. |

All other recovered C translation units match the reconstruction and contain
no port-only changes.

## Shared recovered headers

| Header | Port-only delta | Audit result |
| --- | --- | --- |
| `c2_target.h` | Adds `PLATFORM_PORTABLE` and named portable features | Retained as the sole target/feature vocabulary. |
| `c2_data.h` | Exposes portable assembly declarations | Corrected: the manifest include is now `PLATFORM_PORTABLE`-only and cannot reach Watcom. |
| `entities.h` | Scoped one-byte packing and complete-type extern placement | Retained; required by the recovered ABI on standard C compilers. |
| `ail.h`, `smacker.h` | Target vocabulary and flattened portable ABI keywords | Retained. Miles `#pragma aux` declarations are now DOS-only. |
| `lib32.h` | Prototypes needed by portable adapters | Retained. |
| `pcsound.h` | Guarded XMI buffer size | Retained; the shipped size remains 27,500 bytes. |

Portable-only headers (`c2_host.h`, `c2_observation.h`, compatibility codecs,
and bug-fix declarations) remain in `include/` because they form interfaces,
but their implementations live below `src/platform/common/`.

## Enforced invariants

The static suite now checks that:

- SDL stays in `src/platform/sdl3/`;
- recovered sources do not call `c2_host_*`;
- portable common code does not call backend-private `c2_sdl_*` functions;
- portable helper translation units do not appear at the recovered `src/`
  root;
- the portable assembly manifest is excluded from the Watcom include path;
- raw compiler identity never selects source behavior; and
- every bug fix defaults to the portable target only.

Re-run this audit whenever a reconstruction cherry-pick changes one of the
files above. Compare by function and intent, not by accepting an entire-file
port snapshot over a newer recovered file.

The retained DOS build was re-run after this audit: all 1,435 recovered game
functions, 87 assembly functions, 517 recovered vendor functions, and 195 CRT
functions compared exact, with zero differing bytes across the 508,368-byte
code object.
