# vendor/ — third-party source references (gitignored, regenerable)

Large reference trees that are useful to have locally but are **not** part of
this repo's tracked history. Everything under `vendor/` is gitignored except
this README.

## `vendor/miles-ail-sdk/` — Miles AIL multi-version header collection

Upstream Miles AIL / MSS headers across the product's history (`AIL.H` 3.6B
from MiG Alley, the AIL2 v2.14 set, AIL/32 v1.05, MSS 6.1a, …) plus the RAD
dev-history changelog. Reference evidence only — nothing builds against it.
The **analysis** (the PS.EXE AIL 3.03 pin, per-file provenance table, the
`modify exact [eax gs]` pragma evidence) is tracked in
`docs/external-libs/miles-ail-sdk.md` and
`docs/external-libs/miles-ail-versions.md`, which carry the source repo +
commit pin for every file. To regenerate, re-download from the repos listed
there (primary: `gondur/mig_src` @ `7adf5e68` for `AIL.H`; `Tronix286/AIL2`;
`Wohlstand/ail32-sandbox`; `CookiePLMonster/VBdec`; RAD's `msshist.htm`).

## `vendor/external-libs-headers/` — canonical AIL 3.03 + Smacker 2.x API surfaces

The licensee-era compile-time reference headers (`ail/mss-v1.01.h` — THE
V3.03 header, `ail/ail32-v1.05.h` + its public-domain license,
`ail/mssw-win32.h`, `smacker/smack-v3.2f.h`). Analysis + per-file provenance
(source repos, archive.org URLs): `docs/external-libs/headers.md` and
`docs/external-libs/README.md`. Not part of the build — the decomp links the
delinked binary objects and uses the hand-rolled `decomp/include/{ail,smacker}.h`.

## `vendor/open-watcom/` — Open Watcom code-generator source

The earliest open-source Open Watcom snapshot, used as the **algorithm /
structure oracle** for the Watcom internals the docs cite (`bld/cg/c/optcom.c`
for cross-function tail-merge, `bld/cg/c/regalloc.c` + `regsave.c` for the
register allocator, `bld/cg/c/encode.c::CodeLabel` for jump-table padding,
`bld/cc/c/coptions.c`/`cdata.c` for front-end flag defaults, `bld/clib` for the
CRT, `bld/wl` for the linker, …). Doc references of the form `bld/...` resolve
under `vendor/open-watcom/bld/...`.

### ⚠ It is a HINT, not ground truth

This is the **2002-05-15 "Initial checkin"** of `open-watcom-v2`
(commit `6b9cb44389`) — the first public release of the Sybase source. It is
**~7 years newer** than the Watcom **10.0a** (1995) that actually built
`PS.EXE`, and the code generator changed across those releases (e.g. the
"common epilogue"/tail-merge default was toggled off in 11.0b/c and re-enabled
in OW v2; `bool` cleanup; `OC_NORET`). So:

* Use it to understand **how an algorithm works** — control flow, the cost
  model's *shape*, which function does what, the *names* of things.
* **Do NOT treat its exact constants, thresholds, line numbers, or codegen as
  10.0a behaviour.** Where the two could diverge, 10.0a wins.
* **Ground truth for 10.0a is established only by reverse-engineering the
  actual 10.0a binary** — see the sibling repo's `docs/wcc386-re/` (the findings) and its
  repo `~/git/ReverseEngineering/watcom10.0a` (the instrumentation: the
  `-trace` image, QEMU harness, reference model) — and by `c2 cgex`
  experiments against the `watcom-10.0a-dosemu2` container.

### Regenerate

```bash
mkdir -p vendor/open-watcom
git -C ~/git/open-watcom/open-watcom-v2 archive 6b9cb44389 | tar -x -C vendor/open-watcom
```

(18,504 files, ~22 MB. `6b9cb44389` is the earliest commit:
`git -C ~/git/open-watcom/open-watcom-v2 log --reverse --oneline | head -1`.)
