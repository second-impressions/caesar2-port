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

`data/PS.EXE` is the spec.  **Any edit under `src/` or `include/` must keep the
reconstruction byte-exact**: run `c2 rebuild` (its comparison lines must all
stay exact / strict 0) and `c2 reccmp code` (100% accuracy) before
committing.  When editing source *style* (comments, formatting), remember
the code shape itself is load-bearing — the optimiser's output depends on
statement order, declaration order, and idiom choice.  The inferred PS
source-style guide (`observed-source-style.md`) and the 155-rule codegen
pattern catalogue (`watcom-codegen-patterns.md`) live in the watcom10.0a
sibling repo's `docs/`.

## Git discipline

* You may not be alone in this tree; other agents/sessions work in
  parallel.  Stage narrowly (`git add <file>`, never `-A`), commit small
  and fast, prefer targeted `edit`-tool undos over whole-file snapshot
  restores (stale snapshots silently revert parallel commits).
* Commit messages carry the postmortem: what was wrong, what fixed it, why.

---

## The toolkit

### The original (ground truth)

The copyrighted original lives untracked at **`data/PS.EXE`**; its SHA-256
is pinned in `reccmp-project.yml`.  Every consumer (`export`, `delink`,
`rebuild`, `reccmp prepare`) guards it via `c2.original.ensure_original` —
missing → instructions, hash mismatch → hard error
(`C2_ALLOW_ORIGINAL_MISMATCH=1` downgrades to a warning, e.g. for the
1995 release builds).  **`c2 fetch-original`** supplies it automatically:
downloads a pinned CD zip from the archive.org collection, md5-verifies
it, converts the BIN/CUE image on the fly, extracts `HD/PS.EXE` via
pycdlib, sha256-verifies, installs.  See README "Getting the original
PS.EXE".

### Build & link

```bash
uv run c2 fetch-original     # supply data/PS.EXE from archive.org (once)
uv run c2 export data/PS.EXE # parse LE + Watcom debug info → data/out/symbols.json
uv run c2 rebuild            # authentic 1995 link → build/PS.EXE (runnable)
uv run c2 delink --list      # recover third-party OMF objects from PS.EXE
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
Work dir `.c2-cache/rebuild/` (incremental, ~1 s warm).

Delinker facts worth not regressing: alias dedupe (two `-d1` names on one
body must not duplicate bytes); data PUBDEFs + the `_sndinit` allowlist;
per-module `_TEXT` alignment inferred from PS's pad bytes; the RAD asm
modules' code segments declared in canonical order.  `c2 delink --verify`
(verbatim byte check vs PS.EXE) should accompany any delinker change, and
rebuild's av-delink/layout buckets are the end-to-end gate.

**Toolchain**: the Watcom 10.0a container image (`localhost/watcom-10.0a-wibo`)
with the proven-settled flags `PS_CFLAGS = -bt=dos -mf -4r -s -d1`
(default OptSize=50, unsigned char — the per-flag byte-level proofs live in
the watcom10.0a repo's `docs/watcom-10.0a-flags.md` and
`docs/char-signedness-proof.md`; do not chase flags).  The canonical
constant lives in `c2/buildenv.py`.

### Verification (reccmp)

```bash
uv run c2 reccmp prepare     # once: validate data/PS.EXE, write reccmp-user.yml
uv run c2 rebuild            # publishes build/PS.reccmp.EXE + .map
uv run c2 reccmp code        # function alignment/accuracy report
uv run c2 reccmp data        # initialized-data + relocation checks
```

Never point reccmp at the runnable `build/PS.EXE` (it contains PS's grafted
debug trailer); the pre-bind `PS.reccmp.EXE` is the analysis image.  The
target hash is pinned in `reccmp-project.yml`; `prepare` writes the
machine-local `reccmp-user.yml`/`reccmp-build.yml` (both gitignored).

### Run the game

`c2 rebuild` produces a self-contained `build/PS.EXE`; install the CD's
`HD/` tree + media dirs and run it in DOSBox-X (see README).  Headless
smoke test:
`podman run --rm -v "$PWD/install/caesar2:/src" localhost/watcom-10.0a-dosemu2 PSREBLD.EXE`
(expect the CD-check prompt).  AV runtime test: `smk-player` in the
sibling **caesar2-tools** repo (links the reconstructed
ail.lib/smack.lib and decodes real `.SMK` cinematics — run it after
delinker changes; its `build.sh` finds this checkout via `C2_REPO`).

---

## Frozen generated artifacts

The corpus being closed, several tracked files are now FROZEN generated
artifacts — their generators were retired with the diagnostic toolkit
(git history ≤ 2026-07-15 has them):

* **`include/c2_data.h` / `c2_funcs.h`** — were produced by
  `c2 gen-header` from symbols.json + `_TYPE_OVERRIDES`.  Do not patch by
  hand; if types must change, resurrect the generator from history.
  `c2_funcs.h` **must not be included broadly** (prototype visibility
  changes Watcom call-site codegen; PS source had no global registry).
* **The 8 hand-written `.asm` modules** in `src/` — were produced by
  `c2 decomp` from PS.EXE bytes.

Hand-written: **`include/c2_types.h`** (wrapper around `entities.h`).
Per-file `extern` decls in `.c` files are authentic 1990s practice, not a
smell — PS source had `globals.h`-style shared types but no central
function registry (many cross-TU calls had no prototype at all).

---

## Caesar II context

- **Calling convention**: `__watcall` — eax, edx, ebx, ecx for the first 4
  int params; rest on stack right-to-left.
- **Format**: Linear Executable (LE-Style DOS); code base `0x10000`, data
  base `0x90000`; ~2,234 named functions from Watcom `-d1` debug info.
- **Third-party**: Miles AIL 3.03 (base, 1995-06-18) + RAD Smacker 2.0
  (delinked from PS.EXE, never decompiled — headers in
  `include/ail.h` / `smacker.h`); Watcom CRT from `clib3r.lib`.
- **Data layout**: `city_map` (80×80 grid of 20-byte `struct city_cell`,
  `cm_ptr = y * 80 + x`), `region_map`, `pseudo_map`, `battle_map`,
  `figure_list` / `army_list` / … — all documented in
  `include/entities.h`.
- **Shared globals**: `src/c2_vars.c` (773 BSS definitions in PS
  layout order); `datainit.c` carries recovered initializers.
- **Cross-build family**: three byte-distinct DOS builds from the same
  toolchain — `dbg-1996-04` (= `data/PS.EXE`, ships `-d1` debug info,
  SHA-256 in README.md), `rel-1995-10`, `rel-1995-09`.

## Knowledge base

The burn-down documentation was retired 2026-07-15 (this repo's git
history has all of it).  What remains lives in two places:

- The **watcom10.0a sibling repo**
  (`~/git/ReverseEngineering/watcom10.0a`) — all wcc386-10.0a compiler
  knowledge: `docs/observed-source-style.md` (the inferred PS source-style
  guide), `docs/watcom-codegen-patterns.md` (the 155-rule codegen
  catalogue), `docs/watcom-10.0a-flags.md` + `docs/char-signedness-proof.md`
  (the flag proofs), `docs/watcom-debug-format-spec.md`,
  `docs/codegen-experiments/` (the experiment record), `docs/wcc386-re/`
  (regalloc model, symbol maps), the instrumented trace image, and the
  vendor manuals (`docs/references/manuals/`).
- The **caesar2-tools sibling repo** — ImHex patterns for the
  reverse-engineered game file formats (prose specs in this repo's git
  history) + the smk-player AV test.
- Doc citations of the form `bld/cg/c/…` refer to the earliest public
  Open Watcom source (open-watcom-v2 commit `6b9cb44389`, 2002) — an
  algorithm *hint* only, ~7 years newer than the 10.0a that built PS.EXE;
  never treat its constants or codegen as 10.0a ground truth.

## Semantic code search (semble)

Prefer `semble_search` over grep/glob+read for any "where is… / how does…"
question across the C decompilation and the c2 toolkit; narrow with
`path`, fall back to exact grep only for every-literal-occurrence needs.
