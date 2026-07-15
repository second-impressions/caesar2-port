# semgrep rules

Pattern-matching rules for `decomp/src/*.c` source.  Run via the
semgrep CLI installed as a dev dependency:

```bash
# Lint mode — report matches, do not edit files
uv run semgrep scan --config c2/semgrep-rules/cell-offset-region.yaml \
    --quiet --no-git-ignore --metrics off decomp/src/

# Apply autofix — actually rewrite the source
uv run semgrep scan --config c2/semgrep-rules/cell-offset-region.yaml \
    --quiet --no-git-ignore --metrics off --autofix decomp/src/

# All rules at once
uv run semgrep scan --config c2/semgrep-rules/ --quiet \
    --no-git-ignore --metrics off decomp/src/
```

Always run `c2 baseline check baselines/pre-phase1.json` after an
autofix to confirm no codegen regressions.  These rewrites only
reorder commutative operands, so the apply pass should be byte-neutral
(verify each — Rule 113 makes the order matter once the offset lowers
to a `lea`).

## Current rules

The `CM_OFF` / `RM_OFF` / `BM_OFF` / `PM_OFF` cell-offset macros were
**removed** (Rule 113): they hard-coded the row-first operand order
`(y*W + x)*CB`, which swaps the final `lea` base/index versus PS's
column-first `(x + y*W)*CB`.  These rules therefore flag the *row-first*
spelling and rewrite it to the explicit *column-first* form — they no
longer recommend (or reintroduce) the deleted macros.

| File                              | Pattern (row-first)                  | Fix (column-first)   |
|-----------------------------------|---------------------------------------|----------------------|
| `cell-offset-city.yaml`           | `(y * 80 + x) * 20` (and variants)    | `(x + y * 80) * 20`  |
| `cell-offset-region.yaml`         | `(y * 60 + x) * 8`  (and variants)    | `(x + y * 60) * 8`   |
| `cell-offset-battle.yaml`         | `(y * 52 + x) * 4`  (and variants)    | `(x + y * 52) * 4`   |

Each rule enumerates only the **row-first** variants (`(Y*W+X)*CB`,
`CB*(Y*W+X)`) plus hex spellings of the constants
(`0x50`/`0x3C`/`0x34`/`0x14`).  Semgrep does NOT treat `60` and `0x3C`
as equal in patterns, so both forms must be written explicitly.  The
AST-based `c2 style_check` `offset-order` detector
(`c2/commands/style_check.py`) is the spelling-independent equivalent
used by `decomp-verify -v`.

## Writing a new rule

Drop a YAML file alongside the existing ones.  Each rule should:

1. Use a unique `id`.
2. Set `languages: [c]`.
3. Provide a multi-line `message` describing the migration.
4. List every commutative / hex / spacing variant under
   `pattern-either:`.
5. Supply `fix:` so `--autofix` works.
6. Set `severity: INFO` (these are stylistic refactors, not bugs).

Verify the rule with `--quiet ... decomp/src/<one-file>.c` before
running it across the whole tree.

## Setup notes

`semgrep` is a dev dependency; install with `uv sync --extra dev`.
A second dep, `setuptools < 81`, is required at runtime because
semgrep's transitive dep `opentelemetry-instrumentation-requests`
still imports `pkg_resources` (removed in setuptools 81+).  Both
are pinned in `pyproject.toml`.
