# Caesar II Reconstruction — Agent Guide

This repo holds the **finished, byte-exact reconstruction** of Caesar II's
DOS engine (`PS.EXE`, Watcom 10.0a, 1995/96).  As of 2026-07 every game
function is byte-exact: reccmp reports **2234/2234 functions at 100%
accuracy**, and the rebuilt link matches the original **strictly — 0
differing code bytes / 508,368** with only loader fixups masked.

The burn-down era's diagnostic toolkit (per-function byte oracle, regalloc
trace machinery, hint pipeline, subagent orchestrator, Mac/Windows shape
oracles) was retired once the corpus closed; verification is now the job of
**our reccmp fork** (pinned in `pyproject.toml`) plus `c2 rebuild`'s
built-in comparison.  If you need the old tooling, it lives in git history
(pre-2026-07-15); the compiler-RE knowledge lives in the sibling repo
`~/git/ReverseEngineering/watcom10.0a`.

Per-command details: `uv run c2 <cmd> --help`.

---

## ⚠️ THE PRIME INVARIANT: byte-exactness

`data/PS.EXE` is the spec.  **Any edit under `decomp/` must keep the
reconstruction byte-exact**: run `c2 rebuild` (its comparison lines must all
stay exact / strict 0) and `c2 reccmp code` (100% accuracy) before
committing.  When editing source *style* (comments, formatting), remember
the code shape itself is load-bearing — the optimiser's output depends on
statement order, declaration order, and idiom choice.
`docs/observed-source-style.md` is the inferred PS source-style guide;
`docs/watcom-codegen-patterns.md` catalogues the 155+ codegen rules that
constrain what the C may look like.

## ⚠️ THE GHIDRA DB IS REBUILT BY A SCRIPT, NOT HAND-CURATED

The Ghidra project (`./C2`, program `PS.EXE`) is a disposable artifact,
rebuilt from scratch by [`scripts/rebuild-ghidra.sh`](scripts/rebuild-ghidra.sh)
(LE-Style DOS loader + `x86:LE:32:watcom`, post-script
`ghidra_scripts/ImportCaesar2.java`).  It applies debug-symbol imports
(~2,234 functions), authoritative function boundaries, line-number
comments, program-tree organization, and calling conventions.  **Never run
bare `ghidra-cli analyze`** — it shreds the debug-symbol boundaries into
thousands of spurious `FUN_` fragments.  To fix the DB, rebuild it.

## Git discipline

* You may not be alone in this tree; other agents/sessions work in
  parallel.  Stage narrowly (`git add <file>`, never `-A`), commit small
  and fast, prefer targeted `edit`-tool undos over whole-file snapshot
  restores (stale snapshots silently revert parallel commits).
* Commit messages carry the postmortem: what was wrong, what fixed it, why.

---

## The toolkit

### Build & link

```bash
uv run c2 rebuild            # authentic 1995 link → build/PS.EXE (runnable)
uv run c2 delink --list      # recover third-party OMF objects from PS.EXE
uv run c2 decomp --force data/out/symbols.json --exe data/PS.EXE
                             # regenerate the 8 hand-written asm modules
uv run c2 export data/PS.EXE # parse LE + Watcom debug info → data/out/symbols.json
uv run c2 gen-header         # regenerate decomp/include/c2_data.h + c2_funcs.h
```

**`c2 rebuild`** emits the authentic link shape (`SYSTEM dos4g`;
`LIBRARY ail.lib, smack.lib, clib3r.lib`; 44 FILE objects in PS's module
order), reconstructs the vendor archives from the delink on every build,
and prepends PS.EXE's own byte-exact DOS/4GW 1.97 stub.  No auto-stubbing:
an undefined extern is a hard link error.  After every build it prints the
comparison, which must read:

```
game       1435/1435 exact          ← any less: source regression
c2-asm     87/87 exact              ← asm module regression
av-delink  517/517 exact            ← delinker bug
crt        195/195 exact            ← link-input/toolchain drift
layout     0 cross-module break(s)  ← module order fidelity
data       341/341 exact
strict     0 differing code byte(s) / 508368
```

Options: `-cv` (list diffing symbols), `--no-bind`, `--no-compare`.
Work dir `.c2-cache/rebuild/` (incremental, ~1 s warm).  Mechanism docs:
`docs/delinking.md`.

**Toolchain**: the Watcom 10.0a container image (`localhost/watcom-10.0a-wibo`)
with the proven-settled flags `PS_CFLAGS = -bt=dos -mf -4r -s -d1`
(default OptSize=50, unsigned char — the per-flag byte-level proofs are in
`decomp/docs/watcom-10.0a-flags.md` and `docs/char-signedness-proof.md`;
do not chase flags).  The canonical constant lives in `c2/buildenv.py`.

### Verification (reccmp)

```bash
uv run c2 reccmp prepare     # once: validate data/PS.EXE, write reccmp-user.yml
uv run c2 rebuild            # publishes build/PS.reccmp.EXE + .map
uv run c2 reccmp code        # function alignment/accuracy report
uv run c2 reccmp data        # initialized-data + relocation checks
```

Never point reccmp at the runnable `build/PS.EXE` (it contains PS's grafted
debug trailer); the pre-bind `PS.reccmp.EXE` is the analysis image.  Full
workflow: `docs/reccmp-workflow.md`.

### Run the game

```bash
uv run c2 cd unpack "CDs/<name>.zip"
uv run c2 cd install --full "CDs/extracted/<name>"   # → install/caesar2
uv run c2 run                # DOSBox-X, RECOMPILED game (auto-rebuilds)
uv run c2 run --original     # the shipped PS.EXE
```

Headless smoke test:
`podman run --rm -v "$PWD/install/caesar2:/src" localhost/watcom-10.0a-dosemu2 PSREBLD.EXE`
(expect the CD-check prompt).  AV runtime test: `tools/smk-player/`
(links the reconstructed ail.lib/smack.lib and decodes real `.SMK`
cinematics — run it after delinker changes).

### Inspection

```bash
uv run c2 disasm <fn>        # PS.EXE asm with -d1 line numbers + fixups
uv run c2 sym 0x726f8        # address → symbol
uv run c2 xrefs <symbol>     # who calls / reads / writes
```

### Game assets

`c2 image` (PL8 sprite export/import), `c2 textfile` (.ENG/.GER text
binaries), `tools/imhex/` (ImHex patterns for every reverse-engineered game
file format — see `docs/*-format.md`).

---

## Headers: `c2_data.h`, `c2_types.h`, `c2_funcs.h`

`uv run c2 gen-header` regenerates the generated headers from
`data/out/symbols.json` + the `.c` definitions:

1. **`decomp/include/c2_data.h`** — externs for all non-static data symbols,
   with `_TYPE_OVERRIDES` for known structs/arrays.  The only generated
   header normal `.c` files should include.
2. **`decomp/include/c2_funcs.h`** — canonical prototypes for tooling;
   **must not be included broadly** (prototype visibility changes Watcom
   call-site codegen; PS source had no global registry).

Hand-written: **`decomp/include/c2_types.h`** (wrapper around `entities.h`).
**Never patch generated headers by hand** — fix `_TYPE_OVERRIDES` in
`c2/commands/c_source.py` and re-run `gen-header`.

Per-file `extern` decls in `.c` files are authentic 1990s practice, not a
smell — PS source had `globals.h`-style shared types but no central
function registry (many cross-TU calls had no prototype at all).

---

## Caesar II context

- **Calling convention**: `__watcall` — eax, edx, ebx, ecx for the first 4
  int params; rest on stack right-to-left.
- **Format**: Linear Executable (LE-Style DOS); code base `0x10000`, data
  base `0x90000`; ~2,234 named functions from Watcom `-d1` debug info.
- **Third-party**: Miles AIL 3.03 + RAD Smacker 2.0 (delinked from PS.EXE,
  never decompiled — headers in `decomp/include/ail.h` / `smacker.h`);
  Watcom CRT from `clib3r.lib`.  Research: `docs/external-libs/`.
- **Data layout**: `city_map` (80×80 grid of 20-byte `struct city_cell`,
  `cm_ptr = y * 80 + x`), `region_map`, `pseudo_map`, `battle_map`,
  `figure_list` / `army_list` / … — all documented in
  `decomp/include/entities.h`.
- **Shared globals**: `decomp/src/c2_vars.c` (773 BSS definitions in PS
  layout order); `datainit.c` carries recovered initializers.
- **Cross-build family**: three byte-distinct DOS builds from the same
  toolchain — `dbg-1996-04` (= `data/PS.EXE`, ships `-d1` debug info,
  SHA-256 in README.md), `rel-1995-10`, `rel-1995-09`.

## Knowledge base

- `docs/observed-source-style.md` — the inferred PS source-style guide.
- `docs/watcom-codegen-patterns.md` — 155+ numbered Watcom 10.0a codegen
  rules learned during the byte-exact burn-down.
- `docs/codegen-experiments/` — the authored experiment scripts (historic;
  they drove the retired diagnostic tooling and are kept as the record).
- `docs/delinking.md`, `docs/reccmp-workflow.md` — mechanism docs for the
  build/verify pipeline.
- `docs/*-format.md` — game file-format specs (PL8, GD8, INF, LBM, …).
- The **watcom10.0a sibling repo** — the compiler RE: the instrumented
  wcc386 trace image, `docs/wcc386-re/` (regalloc model, symbol maps),
  the vendor manuals (`docs/references/manuals/`).
- `vendor/open-watcom/` (gitignored) — OW 2002 source as an algorithm
  *hint*, never 10.0a ground truth; see `vendor/README.md`.

## Semantic code search (semble)

Prefer `semble_search` over grep/glob+read for any "where is… / how does…"
question across the C decompilation, the c2 toolkit, and the docs; narrow
with `path`, fall back to exact grep only for every-literal-occurrence
needs.
