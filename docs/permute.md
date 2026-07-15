# `c2 permute` — Watcom-x86 source permuter

A Caesar-II-specific port of the matching-decomp permuter idea
([simonlindholm/decomp-permuter](https://github.com/simonlindholm/decomp-permuter))
to our Watcom 10.0a / x86 / DOS setup.  The upstream tool only
targets MIPS / PPC / ARM32, so we wrote our own to chip away at
the regalloc / source-shape tail of our 500-function byte-diff
backlog.

## On-disk safety: the real source tree is NEVER mutated

The permuter sets up a scratch worktree under `/tmp/c2-permute-…/`
that hard-links every file in `decomp/src/` (and symlinks the
read-only sibling dirs).  All variant writes happen inside that
scratch tree; the verifier is pointed at it via `--decomp`.  The
real `decomp/src/<file>.c` is read ONCE at session start (to
compute the body) and is never written by the permuter except by
the explicit `--keep-best` flag, which writes the final winner
back.  Aborting the tool (Ctrl-C, exception, kill) leaves the
real tree untouched.

## ⚠️ Critical safety rule — read first

**The permuter is a regalloc / source-shape exploration tool, NOT
a correctness tool.**  It rewrites your function body in dozens of
semantically equivalent ways and keeps whichever variant produces
the smallest byte-diff against `PS.EXE`.  If your decompiled C
is *behaviourally wrong* in some subtle way, a permutation can
accidentally produce shorter byte-diffs without being any more
correct than what you started with — and worse, it may bake the
wrong shape into the source.

**Only run `c2 permute` on functions where:**

1. The C body has been hand-decompiled (or at minimum hand-reviewed)
   and the operator believes it is **semantically equivalent** to
   the PS asm.
2. The remaining diff has been visually classified as regalloc /
   ordering / encoding noise — not as missing branches, wrong
   loop bounds, swapped operands, mis-typed parameters, mis-counted
   args, or other structural bugs.
3. The function is *not* a stub.  Stubs are auto-generated and
   permuting them will surface random near-matches that look like
   wins but mean nothing.

If you are not sure: run `c2 decomp-verify -v -f <fn>` first,
read the diff rows, and only invoke the permuter once you have a
mental model of what's diverging.  Mismatches in instruction
count, mnemonic, or branch targets are *not* regalloc problems
and the permuter cannot fix them.

When in doubt, prefer hand-editing per the rules in
[`docs/watcom-codegen-patterns.md`](watcom-codegen-patterns.md).

## What it does

1. Locates the named function in `decomp/src/*.c` via its
   `// FUNCTION:` annotation.
2. Extracts the function body (the `{` … `}` block).
3. Runs a registry of named **mutators** against the body.  Each
   mutator emits zero or more rewritten variants of the body.
4. Optionally composes mutators up to `--depth N` (BFS, body-hash
   deduped).
5. Compiles every variant via the existing `decomp-verify`
   pipeline (single-TU recompile + relink) and captures the
   resulting `diff_byte_count` against PS.EXE.
6. Reports: improvements, byte-equal variants, regressions, build
   failures, with a full diagnostic header up front.

## Usage

```bash
# Singletons, in-process, default mutator set.
uv run c2 permute <function>

# Singletons + every ordered pair.
uv run c2 permute <function> --depth 2

# Hill-climbing: after each round, lock in the best variant as the
# new base and re-run.  Stops on the first no-improvement round.
uv run c2 permute <function> --depth 2 --climb 5

# Parallel: 4 worker subprocesses, each with its own warm container.
# ~30 s/worker cold start, then ~1.5 s per trial.
uv run c2 permute <function> --jobs 4

# Restrict to a subset of mutators.
uv run c2 permute <function> --only swap_cmp,shift_vs_add

# Or drop noisy mutators.
uv run c2 permute <function> --exclude rename_local,reorder_decls

# Preview without compiling.
uv run c2 permute <function> --dry-run --depth 2

# Auto-apply the best improvement to disk.
uv run c2 permute <function> --keep-best
```

### Flags

| Flag | Default | Purpose |
|------|---------|---------|
| `--only / -o slug,…`        | none | restrict the active mutator set |
| `--exclude / -x slug,…`     | none | drop specific mutators |
| `--depth / -D N`            | 1    | mutator composition depth (BFS, body-hash deduped) |
| `--climb / -c N`            | 0    | hill-climb iterations on top of `--depth` |
| `--jobs / -j N`             | 1    | parallel workers (each has its own cwd + container) |
| `--reuse-container/--no-`   | on   | keep one podman container across trials |
| `--max-variants N`          | 120  | hard cap on total variants compiled |
| `--limit / -n N`            | 20   | rows per result table |
| `--keep-best`               | off  | apply the winning variant to disk |
| `--emit-bodies/--no-`       | on   | dump improvement bodies to stdout |
| `--dry-run`                 | off  | enumerate variants without compiling |
| `--quiet / -q`              | off  | suppress per-trial progress |

### Output

Diagnostic header (stderr):

```
helping  decomp/src/action.c
  size:    52 b
  current: 10 byte / 6 row diff(s)
  rules:   Rule 16x2
  tail:    merges into act_about +0x70
  variants:  18 from 4 active mutator(s) -- depth=2
  top mut: rename_local x14  cache_global x7  neutral_alias x7  inline_global x3
  skipped: 18 zero-variant mutator(s): array_form, byte_zext, ...
```

Per-trial progress (stderr):

```
[  3/18] neutral_alias       alias:saved_mode@97              ↑ 14
[  4/18] rename_local        rename:saved_mode->_saved_mode   = 10
[ 12/18] cache_global        cache_global:foo                 ↓  6
```

Colour key: `↓` improvement (green), `=` byte-equal (cyan),
`↑` regression (red), `FAIL` build failure (yellow).

Result tables (stdout, so you can pipe / capture):

* **improvements** — sorted by Δ, then slug.  Followed by a
  unified diff + full fenced body for each improvement so you can
  copy-paste straight into the source.
* **byte-equal variants** — useful as equivalence classes;
  confirms that a mutation is a no-op for this function (i.e.
  the lever doesn't apply or Watcom canonicalises both forms).
* **regressions** (top 10) — informs which levers actively hurt
  this function.
* **build failures** — counted per slug.

Summary footer (stderr):

```
improvements: 0   byte-equal: 4   regressions: 14   failed: 0   total: 18
```

## Mutators

Each mutator is text-level (regex + brace-aware), conservative,
and tagged with either a numbered rule in
[`docs/watcom-codegen-patterns.md`](watcom-codegen-patterns.md) or
a community lever from OoT / SotN / decomp-permuter prior art.

### Community-lever mutators

| Slug | Lever | What it does |
|------|-------|--------------|
| `same_line_join`   | Lever B (whitespace)         | join two adjacent simple stmts onto one line |
| `comma_join`       | Lever B (whitespace)         | join two adjacent stmts with `,` |
| `if_explicit_nz`   | Lever A (extra-mov)          | `if (c)` ↔ `if (c != 0)` |
| `split_add`        | Lever E / Rule 28            | `a = b + c;` → `a = b; a += c;` |
| `join_add`         | Lever E / Rule 28 (inverse)  | `a = b; a += c;` → `a = b + c;` |
| `cache_global`     | Rule 1 (inverse)             | `int t = G; … t …` (cache repeated globals) |
| `inline_global`    | Rule 1                       | inline a `t = G;` cache back to bare reads |
| `neutral_alias`    | Rule 24c                     | `Y + (s - s)` — keep an alias live |
| `reorder_decls`    | Lever / Rule 28a             | swap pairs of adjacent local declarations |
| `swap_assigns`     | Lever (OoT reorder)          | swap adjacent assignments to disjoint LHS |
| `for_multi_init`   | Lever C (loop pre-init)      | hoist a preceding init into the for-clause |
| `rename_local`     | Lever (regalloc tie-break)   | rename a local with a prefix to bias sort |
| `dup_for_cse`      | Lever D (deduplication)      | inline a temp's expression at both uses |

### Rule-based mutators

| Slug | Rule | What it does |
|------|------|--------------|
| `swap_cmp`         | Rule 4  | swap operand order of relational compares |
| `compare_pm1`      | SotN community | `x > k` ↔ `x >= k+1` |
| `shift_vs_add`     | Rule 62 | `x << 1` ↔ `x + x` (`mov;add` vs `lea [x+x]`) |
| `byte_zext`        | Rule 49 | `x & 0xff` ↔ `(unsigned char)x` |
| `postdec_form`     | Rule 54 | `x--;` ↔ `x = x - 1;` (statement form) |
| `array_form`       | Rules 46 / 21 | `arr + i` ↔ `&arr[i]` (SIB-scale reuse) |
| `for_to_while`     | Rule 50 | `for(init;cond;step)` → `init; while(cond){…; step;}` |
| `swap_mul_add`     | Rule 57 | `(a*b) + c` ↔ `c + (a*b)` (mul accumulator) |
| `return_nz_form`   | Rule 53 | `return (x != 0);` ↔ `return x;` |

Mutators that don't fire on the current function are automatically
dropped from the active set with a "skipped: … zero-variant
mutator(s)" notice in the diagnostic header.

## Multi-location and subset enumeration

A single mutator can match many sites in one function — `swap_cmp`
might fire on 12 different comparisons.  Each match is one
**atomic** variant.  Subset enumeration (apply at sites {1, 3} but
not 2) falls out of `--depth ≥ 2` composition for free:

  * `--depth 1` flips each site individually.
  * `--depth 2` applies a mutator to the body that already has
    *another* of its sites flipped.  Body-hash dedup makes
    `M{site=1} → M{site=2}` and `M{site=2} → M{site=1}`
    converge on the same body and one is skipped.
  * `--depth 3` enumerates 3-element subsets, etc.

This means you don't need a separate `--subset` flag — just bump
`--depth` (and cap with `--max-variants`).

## Performance

* In-process verify with the warm cache: ~1.5–2 s per variant.
* `--reuse-container` (default): saves ~250 ms per trial after
  the first build.
* `--jobs N`: each worker has its own cwd + warm container; ~30 s
  cold-start cost per worker, then ~1.5 s/trial parallel.  Only
  worthwhile for runs > ~50 variants.

The verifier already does **single-TU compile** — only the changed
`.c` file is recompiled inside `wmake` (mtime-driven cache);
relink takes ~250 ms; the dominant per-trial cost is the Python
work to load PS.EXE + parse the map + byte-compare.

## Tail-merge gotcha

When the diagnostic header shows a `tail:` line (Rule 42 tail-merge
donor), the function's last few bytes are emitted by the donor's
codegen, not its own.  Source-level changes inside this function
will *not* move those tail bytes — fixing them requires editing
the **donor**'s source instead.  The permuter will still try
mutations but it's best to first run the permuter on the donor
(or hand-edit per Rule 42).

## When to NOT use the permuter

* **Stubs.**  Auto-generated, signature-only.
* **Functions where the diff includes opcode mismatches, missing
  branches, or off-by-one constants.**  Those are semantic bugs;
  fix them by hand first.
* **Functions you haven't read yet.**  The permuter is best as a
  fine-tuner *after* the structure is right.
* **Whole-codebase sweeps.**  Each function takes 30 s + N × 1.5 s
  and produces best-of-N source that may or may not be the right
  shape; mass-applying it without review is a regression hazard.

## File map

| File | Purpose |
|------|---------|
| `c2/commands/permute.py`      | CLI + 22 mutators + search + worker pool |
| `c2/commands/decomp_verify.py`| `set_exec_container` / `start_warm_container` hooks |
| `docs/permute.md`             | this document |
| `docs/watcom-codegen-patterns.md` | the rules each mutator references |
