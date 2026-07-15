# PS.EXE source-style guide (inferred from the byte-exact corpus)

> ## ⛔ MANDATORY READING
>
> **Every agent working on a byte-equality goal MUST read this guide before
> writing or editing a single `decomp/src/*.c` function.**  Most of the rules
> below are codegen levers proven against the binary — choosing the wrong
> spelling silently moves bytes and burns the whole session.  Forms in §0 are
> not stylistic preferences: they are **physically banned** (Watcom 10.0a
> rejects them) or **proven byte-equivalent** to a canonical form that the
> corpus uses uniformly.  Adhere to them mechanically.

Survey of **1029 byte-exact C functions** (all `// FUNCTION:` bodies that
currently verify byte-identical to PS.EXE), restricted to source shapes that
**actually change Watcom 10.0a codegen**. Cosmetic choices that do *not* move
the compiler output were deliberately excluded:

* `register` keyword — no-op in 10.0a (`DoAutoDecl` routes `SC_REGISTER` ==
  `SC_AUTO`). Only 2 uses in the corpus anyway.
* literal radix (hex vs decimal vs octal) — an artifact of our decomp, and a
  constant is the same constant whatever base it's written in.
* whitespace, brace placement, comment style — invisible to codegen.
* declaration *placement* (top-of-function vs scoped) — codegen-neutral within
  the C89 forms, but **two specific non-C89 forms are physically rejected** by
  Watcom 10.0a (see §0).  The corpus is uniformly **strict-C89 top-of-function
  declaration**, and that is what new/edited functions must use.

The columns below are **OBSERVED** (the house idiom — write it this way by
default, the corpus does so overwhelmingly) vs **NOT OBSERVED** (forms the
authors essentially never used; treat as a deviation that needs disasm
justification, or as an untried lever).

---

## 0. Banned source forms — **never write these** ⛔

Three forms are forbidden across the whole `decomp/src/` tree.  Two are
physically rejected by Watcom 10.0a (so the original PS source CANNOT have used
them); the third is codegen-equivalent to the canonical form, so writing it
adds noise without any compensating signal.  Proof and worked examples below.

| form | example | status | enforcement |
|---|---|---|---|
| **C99 mid-function decl** | `g_a = 1; int x = read_g(); use(x);` | Watcom 10.0a **rejects** at parse time (`E1099 Statement must be inside function. Probable cause: missing {`).  Physically impossible in PS source. | hard compile error |
| **C99 for-init decl** | `for (int i = 0; i < N; i++) …` | Watcom 10.0a **rejects** at parse time.  Physically impossible in PS source. | hard compile error |
| **bare `{ }` scope blocks for locals** | `f(); g(); { int x = h(); use(x); }` | Watcom accepts them; in the simple synthetic cases probed they are codegen-neutral to the canonical top-of-function form, AND the 21 corpus bare blocks present pre-normalization (2026-06-15 sweep) all stayed byte-exact after rewrite.  **But** we now have at least one empirical counter-example (`battle.c::fly_to_target`'s `int ptr;` block) where the bare block is load-bearing: flattening `ptr` to the function top pulls it into the *function-level* ConfBefore name queue and perturbs an UNRELATED value's (`delta_anim`) CountRegMoves seat (EAX→EDX); ~30 decl-order/assignment-order/embedded-assign/de-invent variants + `regtrace` confirm no top-of-function form reproduces it.  (It also needs the *deferred* `int ptr; ptr = …;` form — init-in-decl `int ptr = …;` breaks the bytes even with the block.)  `controls.c::control_buttons` was formerly cited here but is NOT load-bearing (its flat form is byte-exact with an identical line-compare).  So bare blocks are **corpus-rare, not prohibited**: prefer top-of-function form (it matches the overwhelming corpus norm), but if it demonstrably breaks the bytes, the bare-block form is fair game. | preference, not prohibition |

### The canonical C89 form

```c
void f(void)
{
    int x;            /* declaration at the function top */
    int i;

    g_a = 1;
    g_b = 2;

    x = read_g();     /* first assignment at the natural use site */
    if (x == 0) x = 8;
    sink(x);

    for (i = 0; i < 10; i++) {   /* counter declared at top, init in `for` */
        sink(i + g_b);
    }
}
```

### Proof (synthetic experiment + corpus normalization)

**`docs/codegen-experiments/decl-placement.py`** runs four block-scoped and two
for-loop trials through Watcom 10.0a and reports the byte sequence per trial:

```
trial            size  bytes (after fixup masking)
A-top              46  52c7050000000001000000c7050000000002000000e81500000089c285c07505ba0800000089d0e8020000005ac3
B-block-sep        46  …same bytes…
C-block-init       46  …same bytes…
D-c99-mid        FAIL  E1099
E-top-for          39  5231d2891500000000e81a000000a300000000a10000000001d0e8080000004283fa0a7cee5ac3
F-c99-for        FAIL  E1099
```

* **A / B / C are byte-for-byte identical** (top-of-function decl ≡ bare-block
  with separate `int x;` + `x = …` ≡ bare-block with `int x = …`).  The bare
  block adds *no codegen information*.
* **D and F are compile errors.**  Watcom 10.0a does not accept either C99
  declaration form.

Run it yourself with `uv run c2 cgex run decl-placement`.

Corpus normalization corroborates the synthetic test for SIMPLE cases:
every bare-block `{ … }` in the byte-exact corpus at the time of the sweep
(21 blocks across 16 functions in `bbarian.c`, `action.c`, `battle.c`,
`c2.c`, `formulae.c`, `int_c2.c`, `refresh.c`, `web.c`) was rewritten to
top-of-function form and **all 16 functions stayed byte-exact**.  Subsequent
work found that the equivalence is *not* universal: `battle.c::fly_to_target`'s
`int ptr;` block is byte-exact only with the bare-block form (top-of-function
rewrite flips an unrelated `delta_anim` EAX/EDX seat via the ConfBefore
name-queue — see §0).  So bare blocks are codegen-neutral in many cases but
can be byte-load-bearing when they keep a local out of the function-level
name queue.  (`controls.c::control_buttons`, previously cited here, is NOT
such a case — its flat form is byte-exact with identical line-compare.)

### What "top-of-function" means in practice

* All declarations sit at the top of the function body, **before** any
  statement other than another declaration.
* **One variable per declaration line** — never `int a, b;` or
  `struct army_rec *us, *them;`.  Comma declarator lists are opaque to the
  Rule 115 decl-order regalloc lever (see AGENTS.md "Source policy"); split
  them so each variable can be reordered individually if needed.
* The *first assignment* of a variable usually happens at the natural use
  site, not at the declaration (see §9; the initialization-point IS a
  codegen lever even though the declaration position is not).
* Counter variables for `for` / `while` / `do/while` loops are declared at
  the function top like any other local; the `for` header uses only an
  *assignment* in its init clause (`for (i = 0; …)`).
* Bare `{ }` scope blocks around local code — i.e. `{ int x; … }` where the
  braces are NOT attached to an `if` / `for` / `while` / `do` / `switch` —
  are **corpus-rare** (the byte-exact corpus has effectively zero after the
  2026-06-15 normalization sweep) but **not prohibited**.  Default to
  top-of-function form; only reach for a bare block when removing it
  demonstrably breaks byte-exact (the proven case is `fly_to_target`,
  where a bare-scoped `int ptr;` keeps `ptr` out of the function-level
  ConfBefore name queue so an unrelated `delta_anim` keeps PS's seat — a
  top-of-function rewrite flipped an EAX/EDX ConfBefore tie).

### Diagnostic command

```bash
# Find any remaining bare-block decls anywhere in the source tree.
uv run c2 decomp-verify --json --no-strict 2>/dev/null \
    | jq -r '.functions[] | select(.style_hints[]?.category == "c99-decl") | .name'
```

`style_check.py`'s `c99-decl` warn rule fires on the C99 mid-decl shape
specifically; the bare-block normalization is enforced by manual review during
decompilation.

---

## 1. Row/entity access: **inline index, never cache the pointer** ⭐ strongest signal

| form | count |
|---|---|
| inline `global[i].field` | **1658** |
| cached `p = &arr[i]; p->field` | **2** (`->field` total 41, mostly malloc'd nodes) |

The single most reliable rule in the whole codebase. PS source re-indexes the
global array at **every field touch** — `army_list[army].map_ref`,
`figure_list[n].x` — and lets Watcom fold `base + i*stride + field` into a
disp32 indexed operand each time. It almost never hoists a `struct foo *p`.

* **Try first:** write `global[idx].field` at every use site, even when the same
  `[idx]` repeats 6×. Watcom recomputes `idx*stride` per access; that *is* the
  PS shape.
* Caching a row pointer forces the base into a callee-save reg and adds a push.
  See Rules 63 / 73 / 74 — every one of those was *removing* a pointer cache.
* The handful of `->` cases are genuine linked structures (`web_node`, malloc'd
  buffers), not array rows.

### Function-level prevalence (the "don't cache a global" survey)

The use-site table above counts *accesses*; the function-level view is even
starker. Scanning the pycparser AST of every compared function for a **local
pointer initialized/assigned to the address of a global array element**
(`p = &svga_refresh_data[idx]`, `p = (T*)region_map + off`, etc., where the
base is a known global from `symbols.json`):

| function uses `p = &global_array[...]` | exact corpus | diffing corpus |
|---|---|---|
| carriers | **17 / 1180 (1.4 %)** | **74 / 341 (21.7 %)** |

A **15× raw** enrichment in the diffing set. Size-controlled (Mantel–Haenszel
over size buckets, so it is not just "big functions diff more and cache more")
the lift is still **1.64×**, and in *every* size bucket ≥ 200 b the carriers
diff at 50–100 % vs a bucket base rate of 15–70 % — i.e. taking the address of a
global array element into a local makes a function of any given size markedly
*less* likely to be byte-exact. This is the AST-level confirmation of the rule:
**don't introduce a local variable to hold (a pointer into) a global; index the
global inline at every touch.**

### The exception that proves it — copy a global *pointer*, don't address a global *array*

The 17 byte-exact "carriers" are almost all a **different** construct that is
NOT this anti-pattern:

| byte-exact "carrier" | what it actually does |
|---|---|
| `font_list`, `font_centre`, `get_text_pointer` (lib32.c) | `p = text_pointer;` — copies a global **`char *`** |
| `load_to_text_buffer` / `load_from_text_buffer` (lib32.c) | `p = text_buffer;` — copies a global pointer, then `*p++` |
| `general_sprite`, `write_general_sprite*` (display.c) | `p = data_ptr;` — copies a global pointer cursor |
| `GetBit`/`GetByte`/`EncodeEnd` (pump.c) | `p = pmp_inbuff/pmp_outbuff;` — moving cursor over a global buffer |
| `change_house`/`pad_house_with_domus` (evolver.c) | `p = city_qptr;` — copies a global pointer |

The distinction is sharp and worth internalizing:

* **`p = &global_array[i]`** (take the *address of an element* of a global
  *array*) → anti-pattern. Watcom pins the base in a callee-save reg + push;
  PS keeps `idx` in a reg and folds `global + idx*stride + field` into a
  disp32 indexed operand. **Inline `global_array[i].field` at every use.**
* **`p = global_pointer`** (copy the *value* of a global that is *already a
  pointer*, to walk it with `*p++`) → fine, and idiomatic. The global holds the
  base; the local is a genuine moving cursor that PS source also used. Not a
  row-cache.

So the precise rule is *"never make a local that holds the address of a global
array element"*, not *"never assign a global to a local"*. The scalar variant
(`int x = global_scalar;`) shows the same direction but is rarer and noisier
(size-controlled lift ≈ 1.6 over only 40 carriers); prefer reading the global
inline there too, but it is a weaker tell.

*(Survey reproducible from `.c2-cache/verify.json` + `data/out/symbols.json`;
the canonical example is `refresh_svga_screen`, whose entire ~120 b residue is
the `cell = &svga_refresh_data[idx]` cache vs PS's `[ecx*8 + disp32]` indexed
form.)*

## 1b. Named intermediates: **inline memory-rooted values, don't hold them** (Rule 116)

The scalar generalisation of §1.  PS almost never writes `int t = <global>;` or
`int t = arr[i].field;` to hold a value used several times — it **inlines** the
expression and lets the compiler RELOAD the memory home at each use.  A named
local severs the value from its home and forces the compiler to HOLD it (a
callee-save register + `push`, or a private stack slot), which is a different
instruction stream.

| form | corpus tendency |
|---|---|
| inline `use(global); use2(global);` (reload) | the norm |
| named `int t = global; use(t); use2(t);` (hold) | **8× rarer per fn in the exact corpus** (0.06/fn) than diffing (0.48/fn); size-controlled lift 1.34→1.54 |

**Marker (read off PS disasm):** a value **re-read from its memory home**
(`[disp32]` / `[idx+disp]`) at each use — especially across a `call` — was
**inlined** (no temp); a value **materialised once and reused from a register /
`[esp+N]` slot**, never re-reading the home, was a **named temp**.  Single-use
values and register-only arithmetic temps are **byte-neutral** (no marker — write
either).  *Loop exception:* an inline invariant is hoisted-and-held by LICM
unless the loop body has a call/aliasing store, so "held across a loop" is not a
temp signal — match PS's loop call/store structure (§5 / Rule 50).

* **Try first:** when PS reloads a global your build holds (extra callee-save
  `push`, single load reused), **delete the `int t = …;` and inline the
  expression** at each use.
* Surfaced automatically: `decomp-verify -v` `Rule 116:` header +
  `--json` `reload_hint`.  Proof: `docs/codegen-experiments/reload-vs-hold.py`;
  live-allocator and causal evidence in Rule 116
  (`docs/watcom-codegen-patterns.md`).

## 2. Dispatch: **if/else-if chains, not `switch`**

| form | count |
|---|---|
| `else if` | **416** |
| `switch` | **5** |

The authors wrote multi-way branches as `if (x==A) … else if (x==B) …`. Watcom
turns a `switch` into a jump table (or a different compare/branch tree) above a
density threshold; the if-chain gives the linear `cmp/je` cascade PS emits.

* **Try first:** if/else-if. Reserve `switch` for the 5 cases that already use it
  (they tend to be dense small-integer dispatch).
* Negated else branches are spelled out explicitly when the test still emits a
  jump: `if (a > b) … else if (a <= b) …` (Rules 30/31) — Watcom does no
  value-range propagation, so the dead test must be written.

## 3. Doubling: two non-equivalent forms — `x + x` (→lea) vs `x * 2`/`x << 1` (→mov;add)

| form | count | lowers to |
|---|---|---|
| `x * 2` | 14 | `mov; add reg,reg` |
| `x + x` | 10 | `lea reg,[x+x]` |
| `x << 1` | 1 | `mov; add reg,reg` |

**Corrected finding (measured on `get_attackers`, `--no-cache`):** the split is
by *AST node*, not arithmetic value. The literal addition **`x + x`** folds into
`lea [x+x]` (3 b). Every *multiply/shift* doubling — **`x * 2`, `2 * x`,
`x << 1`** — goes through the multiply/shift node and emits `mov reg,src;
add reg,reg`. So `x * 2` is **not** equivalent to `x + x` (it equals `x << 1`).
This corrects the old Rule 62 table, which wrongly grouped `x * 2` with `x + x`.

The corpus uses **both** forms (`x * 2`×14 and `x + x`×10) — they're distinct
codegen, picked per context to match PS. Mnemonic: **`+` folds into `lea`;
`*`/`<<` do not.** Larger powers (`* 4`==`<< 2`, `* 8`==`<< 3`) are symmetric
(both `shl`); corpus uses `* 4`×20 freely.

## 4. Division by a constant: **write `/ N`, even for powers of two**

| form | count |
|---|---|
| `/ const` | 81 (`/2`×28, `/4`×7, `/8`×5, `/16`×6, …) |
| `>> n` | 23 |

For **signed** ints, `x / 2` emits the rounding-bias sequence
(`add sign-bit; sar`) while `x >> 1` is a bare `sar` — different bytes. PS source
uses `/N` for arithmetic division (the divisor is a count/total) and reserves
`>>` for genuine bitfield extraction / unsigned packing. **Don't "optimize" a
`/8` into `>>3`** unless the disasm shows a bare shift.

## 5. Loops: ascending counted `for`, post-increment

| trait | count / note |
|---|---|
| `for(i=0; i<N; i++)` ascending | **278** of 286 for-headers |
| descending `for(; i>=0; …)` | 1 |
| step is `++` | 266; `+=` 12 |
| bound is a single var/`literal` | 164 var / 97 literal / 23 expr |
| comma-step `for(; c; i+=A, s+=B)` | 31 |
| C99 decl-in-init `for (int i=0; …)` | **0** — rejected by Watcom 10.0a (§0) |

* **Try first:** `for (i = 0; i < N; i++)`. Counter names `i,j` then domain names
  (`row`, `col`, `army_no`, `figure_no`).
* **Parallel counters** (blit/copy) use the **comma-step** form, and *init order
  outside the loop sets the register binding* — first `= 0` wins the lower
  DoubleRegs slot, and the comma order fixes which `add` emits first (Rule 79).
* `while` (99) is used for scan-until / pointer-walk loops; `do/while` (22) for
  test-at-bottom. `goto` (69 uses across 26 fns) is deliberate and often
  load-bearing — see **§5b** (early-exit guards, continue-with-increment, and
  grid-walk reentry all resist structured normalization).

## 5b. Control flow: explicit `goto` is house style and frequently LOAD-BEARING

`goto` appears in 26 byte-exact functions (69 uses: 56 forward, 13 backward).
It is **not** a smell — Watcom 10.0a's structured-control-flow codegen often
does not reproduce the goto-based block layout, so PS's gotos must be matched
literally. Three categories, all tested:

| goto idiom | example | structured normalization | result |
|---|---|---|---|
| **`goto fail`** — early-exit guards to a shared tail `return CONST` | `mouse_in_area` (19 `fail` uses corpus-wide) | inline `return 0` at each guard | ✗ **+34 b** (early epilogue + backward jumps) |
| same | `mouse_in_area` | combined `if (a&&b&&c&&d) return 1;` | ✅ exact (when no interleaved side effects) |
| **`goto next`** — continue-but-run-trailing-increment | `get_next_word_length` (7 `next` uses) | structured `if (...) break;` fall-through | ✗ diff |
| **`goto outer_test/loop`** — nested grid-walk reentry | Rule 71 functions | structured `while` | ✗ diff (Rule 71) |

Key mechanism (Rule 92): **same-value early-exit guards funnel to ONE epilogue
at the function tail with forward jumps** (`goto fail` or a combined `&&`).
Writing `if (cond) return 0;` at each guard makes Watcom emit the epilogue
*early* (after guard 1) with later guards jumping *backward* — a whole-function
layout change. Use `goto fail` (or combined `&&` when guards are side-effect-
free); never duplicate `return CONST` across guards.

Also relevant: Rule 32 (a `goto` preserves the literal jcc opcode, skipping
Watcom's `FlipCond`) and Rule 71 (`goto outer_test` for do-while-in-while
grids). The takeaway: **when PS shows a forward jump to a shared tail, or a
flipped/preserved jcc you can't otherwise reproduce, the source used `goto`.**

## 6. Comparison operand order: **`var == literal`** (Rule 4)

`var == literal` 845× ; yoda `literal == var` **0**. Watcom preserves source
operand order literally into the `cmp`, so always put the variable on the left.

## 7. Parameter mutation as an idiom (Rules 43a / 64)

* `param *= stride;` then index adjacent fields off the scaled param: 11 sites.
* `saved_n = n; n *= …;` (keep the original in a named local for a later unscaled
  compare): 28 sites.

When PS shows `mov ebx,eax; shl eax,k` (original preserved in EBX, scaled index
in EAX), reproduce it by **mutating the parameter in place** and keeping the
original in a named local — not by computing two separate expressions.

## 8. RMW on a counter field: **prefix `++field` then wrap** (Rule 72)

`++field; if (field >= N) field = 0;` (44 prefix-incr sites, 11 wrap sites) emits
the in-place `inc byte [m]`. The cached-temp form
`c = field+1; field = c; if (c>=N) …` emits a 3-instruction register sequence.
Prefer the in-place increment.

## 9a. Compound `op=` on indexed/struct-array lvalues (Rule 91)

Always write `arr[i].field op= rhs;` (compound), never
`arr[i].field = arr[i].field op rhs;` (expanded). The compound form emits a
single in-place RMW computing the address once (`xor/and/or/add byte [base+idx+
disp], imm`); the expanded form emits load-op-store and re-indexes, diverging by
8+ bytes per site and cascading through following jumps. Only exempt case:
fixed-address global fields (`c2inf.x ^= 1`), where both spellings are
identical. The corpus uses compound `op=` on every indexed lvalue.

## 9. Initialization placement (not "decl at top") is the real lever

Decls sit at the **function top** (§0, strict C89, one variable per line) but
**the value is usually assigned later, in the body**, not at the declaration.
This matters: `int result;` left uninitialised and assigned only inside the
match branch reproduces the "return whatever was in EBX" fall-through (Rule
77); `int result = ref;` forces an extra `mov`. Match PS's *first-write
point*, not just the declaration.

Chained assignment (`a = b = 0;` — 36 uses) is house style and codegen-neutral
as grouping, *except* that the **left-to-right order of a chained `=`
assignment** and the order of `= 0` inits feed §5/Rule 79 register binding.

Multi-declarator lines (`int a, b, c;`) are **banned** by project policy even
though the corpus historically contained 353 of them and they are codegen-neutral
as grouping.  The reason is Rule 115: a comma-separated declarator list is
opaque to the decl-order regalloc lever — you can't move `i` relative to `j`
without dragging the type with it.  Always split: one `<type> <name>;` per
line.  See AGENTS.md "Source policy — one variable per declaration line,
ALWAYS" for the full rationale.

---

## NOT OBSERVED — deviations / untried levers

These forms are essentially absent from the byte-exact corpus. When a diff
tempts you toward one of them, treat it as a red flag (probably not the PS
shape) — *except* the two marked ⚙, which are real but **rare** levers reserved
for one specific regalloc situation each.

| form | count | meaning |
|---|---|---|
| cached row pointer `p = &arr[i]` | 2* | §1 — both are moving-cursor pointer-walks (false positives), not struct-row caches; genuine row-pointer caching is 0 |
| `switch` | 5 | §2 — use if/else-if |
| `x << 1` for doubling | 1 | §3 — use `*2`/`x+x` |
| `>>` for arithmetic divide | (rare) | §4 — use `/N` for signed division |
| descending `for(;i>=0;)` | 1 | §5 — loops count up |
| yoda `literal == var` | 0 | §6 — variable on the left |
| C99 decl-in-for-init `for (int i=0; …)` | 0 | §0 — **physically rejected by Watcom 10.0a** (compile error) |
| C99 mid-function decl `…; int x = …;` after a statement | 0 | §0 — **physically rejected by Watcom 10.0a** (compile error) |
| bare `{ … }` scope blocks for locals | 0 | §0 — codegen-neutral in the simple synthetic cases; corpus norm is top-of-function (normalized out 2026-06-15) but bare blocks are **allowed when byte-exact requires them** — `fly_to_target`'s `int ptr;` block is the proven counter-example (ConfBefore name-queue; `control_buttons`, formerly cited, is NOT one — its flat form is byte-exact) |
| ⚙ ternary `?:` | **3** | Rare, but it *is* the live-range-split lever (Rule 82): use `x = x==0 ? N : x;` to stop an indexed-load scratch from merging with the result reg. Don't reach for it as general style. |
| ⚙ assign-in-`while` `((c = *s))` | 2 | Only in `strcpy`-shaped scanners. A named byte-temp in a loop *pins* a byte reg (Rule 81); the corpus norm is to **double-load** `src[i]` in test and body instead. |
| nested ternary | 0 | unused |
| comma operator in plain statements | 3 | unused outside `for` steps |
| **enum-typed byte params** | **0** | corpus-grounded 2026-06-12 (see below) — byte params are plain `unsigned char` |

### Enum types: NOT used for byte params (corpus-grounded negative)

Watcom 10.0a without `-ei` (our flags) packs an enum into its smallest
fitting type, and an **enum-typed param compares WITHOUT widening**
(`cmp bl, 0xdb` directly), while an `unsigned char` param widens first
(`xor eax,eax; mov al,bl; cmp eax,imm` when the param has later uses;
`and ebx,0xff; cmp ebx,imm` single-use) — oracle probe `/tmp`-class,
2026-06-12.

Census over all of PS.EXE (capstone over `le_code.bin`): **3707**
byte-reg `cmp r8, imm` sites; all game-code instances are either the
AL memory-byte compare idiom (3615×, `mov al,[m]; cmp al,imm`) or
**byte-typed `switch` bound checks** (`cmp bl/dl, 7; ja default` before
a jump table: move_figure/backtrack_figure/move_citizen/move_army's
8-way direction switches, get_movement_image's chain, the
copy_*_256xscreen blitters) plus CRT char scanners.  ZERO sites match
the enum-param signature at a param position.

Conclusion: byte-kind params (devolve_a_building's `kind`, direction
bytes, building base_kind constants 0xA2..0xE2) are **plain `unsigned
char`** in the original; the magic constants were written as literals
(or #defines at most), never as enum-typed values.  When PS widens a
parm byte reg before a compare, type the param `unsigned char` — do NOT
introduce an enum type (it changes the cmp width).

### Levers we have *not* exercised at all (open questions)

Nothing in the corpus tests these, so we have no PS evidence either way — if a
diff seems to call for one, prove it from disasm first:

* `volatile` for forced reload/store ordering (0 confirmed uses).
* `static` *local* (data-segment storage duration) inside a hot function —
  14 `static` total, all file-scope.
* `#pragma aux ... modify exact [...]` on a *specific* callee to widen its
  advertised clobber set (documented in `formulae.c`'s header but applied
  sparingly).
* `__far` pointer tricks beyond the one `FP_SEG` DS-read (Rule 80).

---

---

## Normalization experiments (outlier → dominant form)

Method: take each byte-exact function that uses the *minority* form of an idiom,
rewrite it to the dominant form, and re-verify (`--no-cache`). If it stays exact,
the minority form was **noise** (equivalence-class members); if it breaks, the
minority form is **load-bearing** and the equivalence class has a real boundary.

### Ledger — every experiment run (correct ✅ / false ✗ examples)

| idiom tested | normalization | result | verdict |
|---|---|---|---|
| `register int x` (param) | drop `register` | ✅ still exact | **NOISE** — 10.0a no-op, removed |
| doubling `dir << 1` | → `dir * 2` / `2 * dir` | ✅ exact | both = `mov;add` |
| doubling `dir << 1` | → `dir + dir` | ✗ 1 b diff | `+ x` = `lea` (Rule 62 fixed) |
| `free_pages << 2` | → `* 4` | ✅ exact | **NOISE** — powers >2 symmetric |
| ternary `x = x==0?8:x` | → `if(x==0)x=8` (load-then-patch) | ✗ 3 b diff | **LOAD-BEARING** (Rule 82) |
| ternary | → `if(f==0)x=8; else x=f` (double-load) | ✅ exact | equivalence-class member |
| ternary | → `x=f; if(x==0)x=8` (patch) | ✗ 3 b diff | false form |
| ternary | → `x=8; if(f!=0)x=f` (overwrite) | ✗ 3 b diff | false form |
| assign-in-`while` `(c=*s)` | → body-load `char c=*s` | ✅ exact | **NOISE** — CSE'd |
| `if (!x)` | → `if (x == 0)` | ✅ exact (×5) | **NOISE** |
| chained `a = b = 0` | → `a=0; b=0` | ✅ exact | **NOISE** (mind §9 order) |
| compound `c2inf.x ^= 1` (fixed global) | → `x = x ^ 1` | ✅ exact | **NOISE** — const disp32 |
| compound `figure_list[i].sel ^= 1` (indexed) | → `= … ^ 1` | ✗ 28 b diff | **LOAD-BEARING** (Rule 91) |
| longhand `bmap.dirty = bmap.dirty \| 1` (pointer-cast field) | ← compound `\|=` | ✗ 236 b diff | **LOAD-BEARING both directions** — Rule 143 store-forwards the compound form; PS sometimes wrote longhand (re-read/or/store): mid3_line_with_sides_base 641→405 (ca233d2a).  Sibling sites in the same TU stay compound (byte-witnessed) — adjudicate per site. |
| compound `slave_req[k].cur -= n` | → expanded | ✗ diff | Rule 91 |
| compound `figure_list[n].def += d` | → expanded | ✗ diff | Rule 91 |
| scoped `{ int d; … }` | → hoist to top of function | ✅ exact in 18/18 simple cases (×2 initial probes + ×16 in the 2026-06-15 sweep), ❌ known to break byte-exact in at least one (`fly_to_target`'s `int ptr;` block; `control_buttons` is NOT one) | **CORPUS-RARE, NOT PROHIBITED** (§0) — prefer top-of-function form (codegen-neutral in the synthetic + simple-corpus cases); fall back to bare-block when removing it breaks the bytes |
| `goto fail` early-exit guards | → inline `return 0` each | ✗ 34 b diff | **LOAD-BEARING** (Rule 92) |
| `goto fail` | → combined `if(a&&b&&c) return 1` | ✅ exact | equivalent (side-effect-free guards) |
| `goto next` continue-w/-increment | → structured `if(...)break` | ✗ diff | **LOAD-BEARING** (Rule 92) |
| `do { } while(c)` | → top-test `while(c){}` | ✗ diff | **LOAD-BEARING** (Rule 93) |
| nested `if(a){if(b)X}` | → `if(a&&b)X` | ✅ exact | **NOISE** (Rule 94) |
| nested-with-else (sf02_death) | → flattened `&&` siblings | ✗ diff | **LOAD-BEARING** (Rules 30/31) |
| `if(a\|\|b)X` | → split `if(a)X else if(b)X` | ✗ diff | **LOAD-BEARING** (Rule 94/76) |
| `switch` | → if/else-if chain | ✗ diff | **LOAD-BEARING** (Rule 95) |
| `switch` | → arithmetic equivalent | ✗ diff | **LOAD-BEARING** (Rule 95) |
| `int a, b, c;` | → 3 separate lines | ✅ exact | **BANNED** (§9) — codegen-neutral as bytes, but the comma list is opaque to the Rule 115 decl-order regalloc lever; AGENTS.md "Source policy" mandates one variable per line |
| `int a, b, c;` | → reordered `int c, b, a;` | ✅ exact | NOISE on the *order* axis (use-order binds), but the multi-declarator FORM is still banned; split first, then reorder |
| `while (1)` | → `for (;;)` (and reverse) | ✅ exact | **NOISE** |
| standalone `++x;` | ↔ `x++;` | ✅ exact | **NOISE** (expr context differs — Rule 72) |
| `if (x != 0)` | → `if (x)` | ✅ exact | **NOISE** |
| `arr[i]` | → `*(arr + i)` | ✅ exact | **NOISE** |
| `(unsigned char)x` | → `x & 0xff` | ✗ diff | **LOAD-BEARING** (byte-reg ops vs 32-bit AND) |
| commutative `a + b` | → `b + a` | mostly ✅, 1/6 ✗ | usually NOISE; occasionally a regalloc use-order lever (Rule 4 / layer 3) |
| descending `for(k=6;k>0;k--)` | → ascending | ✗ diff | **SEMANTIC**, not style |
| C99 mixed decl `…; int x = …;` (no wrapping block) | — | n/a | **0 found and physically impossible** — Watcom 10.0a rejects at parse time (§0) |
| C99 for-init decl `for (int i=0; …)` | — | n/a | **0 found and physically impossible** — Watcom 10.0a rejects at parse time (§0) |
| cached `&text_buffer[off]` | — | n/a | false positive — moving cursor |
| named `int t = global;` (used 2×) | → inline both uses | ✗ 22 b diff | **LOAD-BEARING** (Rule 116) — PS reloads `[global]`, the temp forces a hold+push (causal: `running_pop_tax`) |
| named `int t = a*7+b;` (register-only) | → inline | ✅ exact | **NOISE** — no memory home, compiler builds the temp either way |
| single-use `int t = global;` | → inline | ✅ exact | **NOISE** — 1 use is byte-neutral (no marker) |

Detail for each row follows.

### `register` keyword — DEAD WEIGHT (removed)
`clear_to_empty` / `plague_it` (map.c) were the only two uses. Stripped
`register` from both params → still byte-exact. Confirms the 10.0a no-op.
Don't write it.

### Doubling at `get_attackers` — corrected the Rule 62 grouping
`get_attackers` (bbarian.c) `return dir << 1;`. PS emits `mov eax,ebx;
add eax,eax`. Measured byte-exactness of each spelling against that:

| spelling | result |
|---|---|
| `dir << 1` | ✅ exact (mov;add) |
| `dir * 2` | ✅ exact (mov;add) |
| `2 * dir` | ✅ exact (mov;add) |
| `dir + dir` | ✗ 1 b diff (lea) |

This **disproved** the old Rule 62 claim that `x * 2` lowers to `lea` like
`x + x`. In reality `x * 2`/`2 * x`/`x << 1` all lower to `mov; add`; only the
literal `x + x` folds to `lea`. Fixed in `docs/watcom-codegen-patterns.md`
Rule 62 and the `detect_rule_62` hint text. Normalized `get_attackers` to
`dir * 2` (matches PS, house multiply style). `get_dos_memory` `<< 2`→`* 4`
stays exact too (powers >2 symmetric).

### Rule 82 live-range split — equivalence class is broader than "ternary"
`barbarian_in_region` / `empire_in_region` (bbarian.c). The load-bearing effect
is: the row-index scratch (`movsx;imul;mov [scratch+disp]`) must land in a
*different* register from the result. The real trigger is **"assign the result
in every branch from a complete expression"**, not the `?:` token specifically:

| source form | result |
|---|---|
| `x = x == 0 ? 8 : x;` (ternary reassign) | ✅ exact |
| `x = field == 0 ? 8 : field;` (ternary, field double-loaded) | ✅ exact |
| `if (field == 0) x = 8; else x = field;` (**if/else, double-load**) | ✅ exact |
| `x = field; if (x == 0) x = 8;` (load-then-patch) | ✗ 3 b diff |
| `int m = field; x = m; if (m == 0) x = 8;` (temp + patch) | ✗ 3 b diff |
| `x = 8; if (field != 0) x = field;` (init-then-overwrite) | ✗ 3 b diff |

Takeaway for if/elif/else: **an `if/else` reaches the PS bytes too** — what
matters is that `x` is assigned exactly once *per path* from a fresh evaluation
(forcing a new SSA live range), versus loading `x` once and conditionally
patching it (which lets the index scratch reuse `x`'s register). When you see
the `movsx;imul;mov [eax+disp]` scratch-≠-result shape in PS, use ternary **or**
if/else-double-load; avoid load-then-patch. Fixed Rule 82 doc + `detect_rule_82`
framing accordingly.

### `<< 2` vs `* 4` — NOISE (symmetric)
`get_dos_memory` (lib32.c) `free_linear_pages << 2`. `<< 2` and `* 4` are
byte-identical (both `shl`). Normalized to `* 4` (house multiply style). Powers
> 2 have no lea/add asymmetry — only `× 2` does (§3).

### assign-in-`while` condition — NOISE (CSE'd)
`string_to_upper` (lib32.c) `while ((c = *s) != 0) { … c … }`. Rewriting as a
body-load `while (*s != 0) { char c = *s; … }` is **byte-identical** — Watcom
CSEs the two loads. So the assign-in-condition form is an equivalence-class
member here, not load-bearing. (Contrast Rule 81, where a *persisted* named
byte-temp across a copy loop *does* pin a register; the difference is whether
the temp's live range spans the whole loop body vs is re-derived each iter.)

### descending `for` — SEMANTIC, not a style choice
`alter_slave_reqs` (action.c) `for (k = 6; k > 0; k--)`. This walks slave
categories high→low and `return`s on the first non-empty one, so the order is
*algorithm-required* (take from the highest category first). Reversing to
ascending changes behaviour (and bytes). Not a codegen-style outlier — leave it.

### cached row pointer in `load_to_text_buffer` / `load_from_text_buffer` — FALSE POSITIVE
The `dst = &text_buffer[0x1c + off]` here is a **moving cursor** incremented in
a `while (…) dst++` scan, not a struct-row cache (§1). Pointer-walk cursors are
the legitimate use of pointer locals; the §1 anti-pattern is specifically
caching `&array[i]` to repeatedly read `.field` off it. No normalization.

---

## Second sweep — interchangeability of forms not yet probed



Proof (synthetic): `docs/codegen-experiments/decl-placement.py` shows the four
trials A-top / B-block-sep / C-block-init / D-c99-mid + E-top-for / F-c99-for
in one run, with byte-identical sequences for A/B/C and compile failures for
D/F.  Proof (corpus): the 2026-06-15 sweep over `bbarian.c::raider_in_region /
barbarian_in_region / empire_in_region`, `action.c::act_set_marker3 /
mouse_hunt_enemies / show_forum_screen / show_latest_route`,
`battle.c::sf04_fight`, `c2.c::main / new_province`,
`formulae.c::slave_welfare`, `int_c2.c::s03_map_admin / s07_army_patrol /
s08_vigile_patrol`, `refresh.c::refresh_svga_screen`, `web.c::push_node_value`
— 16 functions, 21 blocks, all stayed byte-exact after the rewrite.

Historical note: an earlier section here said inner `{ }` scope blocks "ARE
used (13 functions), and are codegen-NOISE — match PS's bracing for readability
if you like."  That phrasing was too permissive (it framed a stylistic
residue from our decomp as house style and produced inconsistent source that
reads at a glance like C99 mid-decls).  The 2026-06-15 sweep normalized those
out.  The current stance — strong-preference top-of-function, bare blocks
allowed only when they're byte-load-bearing — supersedes both that old
phrasing and the briefly-stronger "always banned" framing that replaced it.

#### Where inline decls sat (when they still existed) — historical census

A function-level AST survey of all 1444 compared functions quantifies how
strongly the corpus prefers top-of-function declarations and answers what kind
of variable, when one *is* declared inside a nested block, it tends to be.
Numbers below are the **pre-normalization snapshot** (before the 2026-06-15
bare-block sweep); after the sweep the byte-exact corpus has **0** standalone
`{ }` scope blocks and the figures shift slightly upward.

* **~94 % of functions declare every local at the function top.** Only **81
  functions (~6 %)** declare anything inside a control-flow body, and only ~13
  use a standalone `{ }` scope block (now 0 in byte-exact, normalized to
  top-of-function per §0).
* It is **not** a loop-index thing. Across both the byte-exact and the diffing
  corpora, **zero** of the inline-declared variables are the loop's controlling
  counter — those are always at the function top (C89: `int i; … for (i=…)`).
  The inline decls are branch-local / loop-local **values** (34/41 exact and
  133/136 diffing are plain scalars, only a handful are pointers).
* Where they sit differs by corpus: the byte-exact corpus splits them ~50/50
  between `if`/`else` bodies (20) and loop bodies (21); the **diffing** corpus
  is **79 % inside `if`/`else` bodies** (108/136). A nested decl carries a
  size-controlled diff lift of ≈ 1.5, strongest for decls **with an
  initializer** — consistent with § 9: it is the *initialization point* that is
  the codegen lever, not the declaration keyword position.
* The remaining **`if`/`else`-body decls** in DIFFING functions (108/136) are
  still legitimate targets to normalize → top-of-function per §0.  The
  byte-equivalence proof applies to them too; they were not yet swept in the
  2026-06-15 pass because the diffing-corpus sweep needs per-function
  verification (the rewrite must not increase `diff_byte_count`).
* The actionable codegen lever is the existing § 9: if hoisting changes bytes,
  it is because you moved the *initialization point*, not the declaration
  position.  Keep the *first assignment* at the same statement; only the
  `int x;` token migrates to the function top.

### `if (!x)` ≡ `if (x == 0)` — NOISE
Measured byte-identical across 5 functions (`act_query_do_help`, `act_undo_cm`,
`load_a_battle_gfx_file`, `start_a_new_game`, `show_detailed_query_panel`).
Both emit `test reg,reg; je`. Pure spelling choice.

### Chained `a = b = 0;` ≡ split `a = 0; b = 0;` — NOISE (mind §9 order)
`start_a_new_game`: splitting a constant-0 chained assignment is byte-identical.
The one caveat is the §9/Rule 79 ordering effect — the *order* of the resulting
`= 0` inits can bind registers in tight parallel-counter loops.

### Compound `op=` vs expanded `lhs = lhs op rhs` — **DEPENDS ON THE LVALUE** ⇒ new Rule 91
The big find of the second sweep:

| lvalue kind | example | compound vs expanded |
|---|---|---|
| fixed-address global field | `c2inf.speech_on ^= 1;` | ✅ identical (constant disp32 folds to RMW both ways) |
| **indexed / computed** | `figure_list[i].selected ^= 1;` | ✗ **diff** — compound = in-place `xor byte [base+idx+disp],1` (one address calc); expanded = `mov;xor;mov` load-op-store + re-indexed |

`select_a_unit` expanded → **+28 b** cascade; `alter_slave_reqs` (`-=`) and
`set_defense_shield` (`+=`) also regress when expanded. So **always use the
compound `op=` form on indexed/struct-array lvalues** — that's the PS shape, and
it's why the corpus uses compound assignment on `figure_list[i]` /
`slave_requirements[k]` everywhere. Generalises Rule 72 (`++field`) to all
operators. Documented as **Rule 91** in `watcom-codegen-patterns.md`.

---

## Third sweep — remaining control-flow & declaration axes

### `do/while` vs `while`/`for` — LOAD-BEARING (Rule 93)
Loop test placement is a real codegen axis. `do { } while (c)` compiles
test-at-bottom with **no entry jump** (body falls through, one conditional jump
loops back); `while (c) { }` / `for` compiles test-at-top (entry `jmp` to the
condition or a pre-guard). `wait_key`'s `do/while` → top-test `while` diffs.
PS shape `call body; cmp; je back` (no entry jump) ⇒ source was `do/while`.
Corpus: 19 byte-exact `do/while` functions. (Semantic too — do/while runs once
— but the byte consequence is the loop-entry shape.)

### `a && b` ≡ nested `if`, but `a || b` ≠ split if/else-if — ASYMMETRIC (Rule 94)
* **`if (a && b) X` is byte-identical to `if (a) { if (b) X }`** — both lower to
  forward skip-jumps to the same target. NOISE; write whichever reads better.
  Confirmed both with independent vars (`get_road_cover`) and a shared var
  (`find_nearest_target`).
* **`if (a || b) X` is NOT `if (a) X; else if (b) X;`** — the `||` funnels to one
  shared body via test-true-jumps; splitting duplicates the body block.
  `click_warning` split form diffs. LOAD-BEARING. (Rule 76 is the inverse: where
  PS *does* split an OR-chain into per-term branches.)
* **Caveat:** the `&&`≡nested equivalence is only for the plain no-`else` case.
  Add an `else`/`else if` chain and the nesting matters — Watcom does no
  value-range propagation (Rules 30/31; `sf02_death` flatten diffs).

### `switch` — LOAD-BEARING, distinct dispatch (Rule 95)
`switch` is not interchangeable with an if/else-if chain *or* an
arithmetically-equivalent expression. `get_movement_image`'s `switch (d)` →
if/else-if diffs, and → `img_base += d*3` also diffs. Watcom builds its own
dispatch (jump table / compare tree). Use `switch` only where PS shows the
switch shape (5 corpus functions); if/else-if everywhere else (§2).

### Declaration grouping & order — codegen-NEUTRAL but multi-decl form is BANNED (§9)
`int a, b, c;` vs three separate lines vs reordered `int c, b, a;` are all
byte-identical (`change_house`, `get_best_lv`).  Register binding is by
first-**use** order (regalloc model layer 3 / Rule 79), **not** declaration
order — so reordering the decls does not move bytes by itself.  The §9/Rule 79
ordering lever is about **assignment/init statement** order (`i = 0; s = 0;`),
not where the variable is declared.

Despite the byte equivalence, **the comma-declarator form `int a, b, c;` is
banned by project policy** because Rule 115 (the declaration-order tie-break
lever) operates per-variable and a comma list is opaque to it — you cannot
move `a` relative to `b` without also moving the type.  Split mechanically:
one `<type> <name>;` per line.  See AGENTS.md "Source policy".  Splitting is
byte-neutral (corpus rows above), and reordering after splitting is the actual
lever.

### `while (1)` ≡ `for (;;)` — NOISE
Interchangeable infinite-loop forms (no entry test, body + unconditional jump
back). Byte-identical both ways. Corpus uses both (`while(1)`×7, `for(;;)`×8).

### Standalone `++x;` ≡ `x++;` — NOISE
As a full statement, prefix and post increment are byte-identical (no value
consumed). Confirmed both directions. **Expression context is different**:
`arr[i++]`, `*s++`, `while (++i < n)` change semantics *and* codegen, and Rule
72 is the specific load-bearing case (`++field` in an if-wrap forces the
in-place `inc byte [m]` RMW vs a cached-temp sequence).

### Fourth sweep — expression-level axes

* **`if (x != 0)` ≡ `if (x)`** — NOISE. Both emit `test reg,reg; je`. (Corpus
  uses explicit `!= 0` 4× more often, but it's free choice.)
* **`arr[i]` ≡ `*(arr + i)`** — NOISE. Identical addressing. Corpus overwhelmingly
  uses `arr[i]` (2994 vs 11), so prefer it for readability.
* **`(unsigned char)x` vs `x & 0xff`** — **LOAD-BEARING**. The cast lets Watcom
  keep the value in a byte register and use byte ops (`movsx cl`, byte `cmp`);
  `& 0xff` forces an explicit 32-bit AND mask (`and eax, 0xff`). `evolve_a_plaza`
  diffs when swapped. Match PS's extension idiom (relates to the char-width
  Rules 8/23/49). Don't "simplify" a cast into a mask or vice versa.
* **commutative `a + b` vs `b + a`** — usually NOISE (5/6 byte-exact) but
  occasionally a regalloc lever: which operand is *used first* can change the
  register assignment (regalloc-model layer 3 / the same first-use tie-break as
  Rule 28a; `write_general_sprite_with_front_ofset` diffs). Match PS's source
  operand order when a diff row is a clean reg swap on a commutative op.

### Codegen-neutral spellings — don't waste time on these
Proven byte-identical *as bytes* (pick for readability, they never move
bytes): `if (!x)` ≡ `if (x == 0)`; `a = b = 0;` ≡ split (mind init order);
`while(1)` ≡ `for(;;)`; standalone `++x` ≡ `x++`; `<< 2` ≡ `* 4` (powers
>2); `x * 2` ≡ `2 * x` ≡ `x << 1` (all `mov;add`); compound `op=` on a
*fixed-global* field ≡ expanded; `a && b` ≡ nested if (no else);
`if (x != 0)` ≡ `if (x)`; `arr[i]` ≡ `*(arr + i)`.

Two equivalence classes that are byte-identical but **still banned by policy**
— pick the canonical form even though the bytes won't tell you which you used:

* scoped `{ int d; … }` ≡ hoisted decl at the function top — **always use
  top-of-function form** (§0).
* `int a, b, c;` ≡ three separate lines ≡ reordered — **always use one variable
  per line** (§9, AGENTS.md "Source policy"), then reorder per Rule 115 if
  needed.

## TL;DR — default writing recipe

1. Index globals inline every time: `global[i].field`. Never cache the row ptr.
2. Multi-way → `if/else if` chains; spell out negated else tests. `switch` only
   where PS shows switch dispatch (Rule 95). Match PS's loop-entry shape:
   `do/while` = test-at-bottom (no entry jump), `while`/`for` = test-at-top
   (Rule 93). Match PS's boolean structure: `a && b` ≡ nested if, but `a || b`
   is its own shared-body form (don't split it; Rule 94).
3. `×2`: `x + x` only if PS shows `lea [x+x]`; `x * 2`/`x << 1` if PS shows
   `mov; add` (they are NOT interchangeable). Arithmetic `÷` → `/N` (even
   powers of two); `>>`/`<<` only for real bit work.
4. Loops count up: `for (i=0; i<N; i++)`, post-increment, single-var bound;
   parallel counters use comma-step and init-order picks the registers.
5. `var == literal`, never yoda.
6. Counter-field wrap: `++field; if (field>=N) field=0;`; and **compound `op=`
   on every indexed/struct-array lvalue** (`arr[i].f &= m;`), never the expanded
   load-op-store form (Rule 91).
7. Mutate params in place (`n *= stride`), keep the original in a named local.
8. Assign the value at PS's first-write point, not necessarily at the decl.
9. Keep `switch`, `?:`, `||`-chains, `do/while`, `goto`, assign-in-`while`, and
   pointer caching for the specific situations where PS actually used them —
   all are load-bearing, not interchangeable with their structured rewrites.

**Codegen-neutral as bytes (free spelling choice, never moves bytes):**
`if(!x)`≡`if(x==0)`; `while(1)`≡`for(;;)`; standalone `++x`≡`x++`;
`a && b`≡nested-if (no else); `<<2`≡`*4`. See §"Codegen-neutral spellings".

**Codegen-neutral as bytes BUT banned by policy (use the canonical form
anyway):** `int a,b,c;`≡separate-lines (use separate; §9 / AGENTS.md);
scoped `{int d;}`≡hoisted-at-function-top (use hoisted; §0).

**Physically rejected by Watcom 10.0a (compile error):** C99 mid-decl,
C99 for-init (§0).

## §10 The range-walker family idioms (2026-06-12, Mac-oracle sweep)

Grounded by flag_range / set_range / test_area_for_population going
BYTE-EXACT (and test_range_for 254→179) in map.c.  The 80×80 (and 60×60
region) clipped-square walkers share one source skeleton; when recovering
any sibling (put_rm_area, build_an_area, put_reg_x2_area,
get_reg_*_in_radius, destroy_reg_atom, clear_to_rubble, ...):

1. **Params clobbered in place**: `x -= range; y -= range;` (no x0/y0) —
   EXCEPT members whose PS frame is larger (test_range_for_road's
   `sub esp,8`): there x0/y0 are named init-decls.  Check PS's `sub esp`.
2. **Chained dimension init**: `width = height = 2*range + 1;` and (with
   the widen param) `height = width = height + extra;` — single source
   lines (one line mark over lea+mov).
3. **xend/yend are named locals**, computed width-first (`xend = width + x;`)
   immediately before each clamp if; both clamp arms read the same lea.
4. **Loop increments live in the for comma clause**:
   `for (gmn_y = y; gmn_y < y + height; gmn_y++, sptr += row_skip)`.
5. **The cell cursor can be a LOCAL `sptr`** — verify whether PS writes the
   gmn_sptr global inside the loop (`add [m],0x14` = global; `add eax,0x14`
   = local).  The "publish convention" holds only for gmn_x/gmn_y in some
   members.
6. **Init-statements sit AFTER the sptr/row_skip lines** (`total = 0;`,
   `test_result1..4 = 0;`) — init-decls at the top cost 50-100 cascade
   bytes.
7. **Byte locals**: footprint nibbles read first as char locals
   (`sub = city_map[sptr+5] & 0xf;` → DH/CL byte ops); kind via the
   2-line `kind_byte = city_map[sptr]; kind = (unsigned char)kind_byte;`
   (cast = xor+mov) or `& 0xff` (= and-form) — pick by PS's idiom at the
   zext site (Rule 49).  A STACK byte arg that PS caches early wants a
   hoisted `unsigned char fo = field_off;` local (births its conflict
   before the other byte args'); REGISTER byte args want the plain use.
8. Park-class residue in this family: tie-group internal order between
   anonymous dword temps and named byte locals (flag_range3's y-homing,
   test_range_for's chain temp).  Document and move on; the levers above
   don't reach it.

Workflow: `c2 mac-fn <name>` for the statement skeleton (arms, constants,
expression order), then PS's -v listing for the PC-only facts (chained
assignments, byte-reg homes, init positions, local-vs-global cursor).

## §11 De-inventing temps (2026-06-12 B-batch, 8 functions, 7 EXACT)

The single most productive lever of the batch: variables WE named were
never in the source -- Watcom manufactures the register caches itself.
Read the Mac build's CALLEE-SAVED registers as the named-locals census
(`stmw rN` count = locals + CW-hoisted TOC bases); caller-saved chains
are expressions.  Mac register REUSE = source variable reuse.

Recurring 1995 idioms confirmed across the batch:

* Globals mutated directly, re-read repeatedly (get_string_width:
  sprite_image_no = letter_table[c-' ']; sprite_image_no--; ...) --
  Watcom's CSE turns them into the temps we kept naming.
* Variable reuse through divmod AND the loops that follow
  (plague_sized / clear_sized_to_reg_basic: x holds packed value,
  y = x % size, x /= size, then for(y...)for(x...) reuse both).
* Chained assignment everywhere a line stores twice:
  `first_help_page = this_help_page = page;`, `out3 = out2 = 1;`,
  `for (no_of = i = 0; ...)`.  A chained store emits REGISTER stores
  (through the chain temp); a lone assignment emits an IMMEDIATE
  store -- the byte pattern distinguishes them (launch_help).
* Compound assignment EMBEDDED in a call argument:
  mouse_in_area(..., y_top += 0x12, ...) -- no separate line mark;
  the store-back dead-elides into a lea (get_linked_page).
* Comma-clause for-increments for pointer walks, counter FIRST:
  for (...; x++, sptr += 20) body-one-line (plague_sized; SS10).
* `for (...; cond; )` ROTATES (bottom test + entry jump); the
  equivalent `while (cond)` stays TOP-TESTED -- when PS shows an
  entry jump use the for spelling (get_cohorts_in_action).
* Early `return value;` inside loops, not break-and-return
  (get_string_width: the break form re-shapes the exits and the
  epilogue cross-function tail-merges away).

## §12 The c2.c burn-down patterns (2026-06-13, 4/4 EXACT)

c2.c went 16/20 -> 20/20 (new_province, load_map_graphics,
load_battle_graphics, main).  New mechanisms, all verified byte-exact:

* **W107 retval funnel, source side** (load_map_graphics): when PS
  shows `mov [esp],1 ... funnel: mov eax,[esp]` (return temp exiled to
  the frame slot), the shape is `ret = 1; goto done;` + fail blocks
  AFTER the loop + a SINGLE `done: return ret;` at the very end that
  the exit(100) paths fall into.  Two separate `return ret;` statements
  give wcc separate exits (no uninit-live join) and EAX seating; the
  single join read is what exiles the temp.  sub esp,4 appears/vanishes
  with it.
* **Per-arm self-contained blocks + tail-merge** (load_map_graphics):
  PS's "shared" NULL-check/readfile blocks with backward jmps from the
  other arms are NOT a source label/goto -- every arm is written
  self-contained (`X = malloc(size); if (X == NULL) goto alloc_fail;
  if (!readfile(fname, X, size, 0)) goto file_fail;`) and Watcom
  tail-merges the identical suffixes (rover renders each global read
  as the same eax byte pattern).  The arm whose check FALLS THROUGH
  (last else-if) stays inline; line marks land on the per-arm jmps.
  Corollary: the `buf` join local never existed.
* **Param names make registers scratch** (main): PS main writes EDX
  without saving it => `void main(int argc, char *argv[])`.  Incoming
  __watcall arg regs are caller-scratch even when the params are
  unused.  Check PS callee-saves vs param count before chasing rover
  or pressure levers.
* **Dead-argument signatures** (free_sample_buffer(10)): a lone
  `mov eax,K` before a call to a void-bodied helper means the ORIGINAL
  prototype took an int the callee ignores (symmetric with its init_
  sibling).  Keep the param in both decl and def; callee bytes don't
  change.
* **Loop-tail spelled without break** (main): PS `jne loop_top` at the
  body end = `if (flag == 0) last_stmt;` + natural loop close, not
  `if (flag != 0) break; last_stmt;`.  The back-edge re-test does the
  exiting.
* **Hoist-once loop prologue** (main): back-edges re-entering AFTER a
  clear (`turbo_mode = 0`) put that clear BEFORE the while(1), not in
  the body.
* **Name reuse, 5th confirmation** (load_battle_graphics): the merc
  tribe index is `idx_base` REASSIGNED (one web -> ESI + the extra EDI
  save for the +1 offset), not a fresh `merc_idx_base`.
* **Statement order from store marks** (new_province): PS L289 stores
  `denarii` BEFORE loading the reduction (L290) -- the hoisted-`r`
  "byte-exact hack" was wrong order; plain `denarii = tbl[skill];
  r = tbl2[skill]; denarii -= r * completed_provinces;` is exact.


## §13 The gloops.c burn-down patterns (2026-06-13, initreg_game_loop 228→17b)

initreg_game_loop closed 211b in one pass with three combined fixes; the
patterns generalize:

* **De-invent the local that copies a global with post-call uses**
  (initreg_game_loop's `region`): the natural shape
    `region = region_over; if (region == 0) goto end; ...; this_region(); ... region_warned_status[region_over] = 6;`
  PESSIMIZES — the `region` local terminates BEFORE this_region(), so
  region_over needs a fresh load in the post-call decision arm.  PS's
  shape is *no local at all* — every `region_over` read is direct, so
  the compiler enregisters region_over in a callee-save (EBP) across
  the call and uses it for the post-call indexing.  Rule: a global
  whose uses fan out across a call boundary is BETTER LEFT AS A GLOBAL;
  the local copy only helps when no calls intervene.

  **Corpus signal (2026-06-25, AST scan over 1449 fns).**  This
  pattern is also harmful WITHOUT a call between assign and use --
  the named local still adds a front-end conflict to the regalloc
  queue.  Counting single-assignment locals whose RHS is a global /
  global-field / global-subscript expression with NEITHER (a) the
  same memory written between the assignment and the last read NOR
  (b) a function call in that window:

  | category | with-mirror | without | % with |
  |---|---|---|---|
  | EXACT  fns ( ≈1307) | 25 |  ≈1282 | 1.8% |
  | DIFF   fns ( ≈ 125) | 12 |  ≈ 113 | 9.6% |

  A **5x bias toward diffing**.  Worked closures: `figure_update`
  (77b → 0b, drop `unit_no` = `temp_unit` mirror), `swap_2_figures`
  (19b → 0b code, drop `state` = `figure_list[enemy_figure].state_idx`),
  `get_fig_fight_image` (-16b, drop `fight_state`/`md`/`sub_state`),
  `dock_the_ship_in_good_port` (-30b, drop `compass_side`/`cohort_class`
  + split a doubly-assigned `was_sea` into two slots), `push_shell`
  (-15b, drop `dir` = `shell_push_direction`),
  `mid3_line_no_sides_base` (-6b, drop `h` = `pm_diamond_half_height`).

  **Mechanism (Watcom-source verified, `cg/h/name.h:209` + cgex
  experiment 2026-06-25):**

        #define _FrontEndTmp( op ) ( !( (op)->t.temp_flags & CONST_TEMP ) && \
                                       (op)->v.symbol != NULL )

  A named C local has a non-null FE symbol pointer; an inline /
  CSE / index temp has `symbol == NULL`.  Both compete in the SAME
  `ConfBefore`-sorted conflict queue with the SAME savings cost
  model, but the mechanism is sharper than a tie-break.  The
  `docs/codegen-experiments/named-local-tiebreak.py` cgex experiment
  (PROVEN under PS_CFLAGS):

      named_named   `int a=G1, b=G2; sink(); a×4; b×4;`
                    -> 2 FE conflicts, both sav=5 (4 uses + 1 def)
                       a -> EDX, b -> EBX
      named_inline  `int a=G1; sink(); a×4; G2×4-inline;`
                    -> 1 FE conflict sav=5 (a) + 4 anon sav=2 leaves
                       a -> EDX, anon leaves -> EDX (reused, disjoint live ranges)
      inline_inline `sink(); G1×4-inline; G2×4-inline;`
                    -> 0 FE conflicts + 8 anon sav=2 leaves
                       all -> EAX (no callee-saves needed)

  **The named-local form does NOT auto-CSE into a single high-savings
  temp; each inline read stays a separate sav=2 leaf** under PS's
  BlockByBlock=TRUE compile mode.  So introducing `local = G;` where
  PS source had inline reads UPGRADES N sav=2 leaves into ONE sav=N+1
  FE conflict that jumps to the TOP of the queue and out-prioritises
  ANY rival at sav ≤ N+1.  This is a **structural rank change**, not a
  ConfBefore tie-break -- the named local doesn't need to tie with
  anything to perturb downstream allocations.  Worked downstream
  effect in our corpus: the new top-of-queue conflict claims a callee-
  save (EBX/EDX) that PS source never asked for, then displaces other
  values; the prologue grows a `push ebx` PS doesn't have, frame
  offsets shift, byte cascade follows.

  **False-positive guard.**  The (a) test must consider that the
  *write* and the *mirror RHS* may reference the same memory through
  different identifiers (e.g. `unit_list[temp_unit].prev_attack_off`
  vs the mirror `unit_list[unit_no].prev_attack_off` where
  `temp_unit == unit_no`): structurally-different lvalue/rhs, same
  memory.  Worked example: `get_fire_target`'s `prev_range` looks
  unjustified to a strict structural-equality AST scan, but PS
  actually materializes it at `[esp+0x10]` (real local -- keep).
  **Always confirm via PS asm (does PS materialize a stack/reg slot
  for the value, or reload the global inline?) before removing.**

  **Cases the mirror lever DOESN'T close.**  When the dominant
  residue is a byte-RMW shape (s04_map_markets, s10_get_business),
  whole-function regalloc spill divergence (push_shell's ymul /
  xstride spill), or massive (>20%) IR-shape mismatch
  (battle_auto_resolve, place2_sprite, get_fig_fight_image), mirror
  removal alone moves the bytes 0-16b -- fix the dominant shape
  first, *then* re-evaluate the mirror.

  **WIN-decompile is NOT a 1:1 source mirror for locals** (negative
  finding 2026-06-25).  Ghidra's MSVC \Od view inlines simple
  `int x = arr[i].field;` locals -- so a missing local in WIN does
  NOT prove the local was missing in PS source.  Counter-example:
  `get_region_revolt_points`'s WIN shows ONLY `bVar1` (= tile) and
  `uVar2` (= `rand128 & 3`), tempting one to drop `x`/`y`/`t`/`occ`.
  Tested: dropping `x` and `y` regresses IR shape 0/7 -> 6/7 (bytes
  drop 255 -> 213 but the SHAPE drifts away from PS).  PS \`-d1\`
  emits L362 = `hut_list[n].x` load and L363 = `hut_list[n].y` load
  as SEPARATE source lines -- the two locals ARE real.  WIN's other
  layers (control flow, call shape, expression precedence, constants)
  remain reliable; only the named-locals layer is /Od-fold-friendly.
  Reliable signals for the "is this a real local?" question:

  1. PS \`-d1\` line marks: a separate L# per assignment site = a
     separate source line = local likely.
  2. PS regalloc materialization (visible in `c2 disasm`): a stack
     slot or a callee-save register dedicated to the value = local in
     source.  Worked example: `prev_range` at `[esp+0x10]` in
     `get_fire_target`.
  3. The Mac PPC decompile (CodeWarrior, similar /Od caveats but a
     SECOND independent witness; the `shape-recon` B column).

  Open research direction (not implemented): a `c2 mirror-audit`
  command that triangulates the AST candidates against (1)+(2)+(3) to
  classify each mirror as `REAL`, `OVER`, or `UNKNOWN`.  The AST
  candidate list alone (helpers exposed in
  `c2.commands.deinvent_hints`) was tested as an automatic hint and
  rejected (~100% FP).

  Empirical verification (DONE, 2026-06-25): the cgex experiment
  `docs/codegen-experiments/named-local-tiebreak.py` confirms the
  mechanism stated above, with the sharper finding that it is a
  STRUCTURAL RANK CHANGE (1 sav=N+1 FE conflict vs N sav=2 anon
  leaves), not a tie-break.  Re-running it after a Watcom-source
  change is the regression check for this rule.
* **goto-end funnel makes the epilogue "framed enough" to decline
  inline-CloneCode** (initreg_game_loop): with 5 callee-save pushes
  (ebx/ecx/edx/edi/ebp), the epilogue is 6 bytes (5 pops + ret),
  exceeding CloneCode's <=5b threshold.  The source recipe — every
  early `return` rewritten as `goto end;` + a single `end:;` before the
  natural body epilogue — keeps the mid-function exits as `jmp end`
  (one byte) instead of inlined epilogues (5+ bytes each), matching
  PS's pattern.  Frameless function but still benefits from the
  threshold dance.
* **Rule 29 INVERSE (direct `if (g) g++;` not load-local-add-store)**
  (main_game_loop turbo_mode/flag_mode_decay_count): when PS shows
  `mov reg,[g]; test reg,reg; lea reg2,[reg±1]; mov [g],reg2` (the
  LEA-preserve form), source is direct `if (g != 0) g = g ± 1;`, NOT
  the load-local-modify-store form `t = g; if (t) g = t ± 1;`.  The
  local destroys the value (compiler emits 1-byte dec/inc), the direct
  form preserves it (compiler emits 3-byte LEA for "writes new, keeps
  old" semantics).  Already documented as Rule 29, but the INVERSE
  direction (us-with-local vs PS-with-direct) needs the same
  symmetric application.
* **3-arm `pick / 3` split is real** (empire.c set_new_province): when
  PS shows three consecutive `mov al, [reg + K + slot]` arms at
  offsets +1/+4/+7 in a stride-10 struct, the source is
  `if (pick < 3) v = arr.choices[slot]; else if (pick < 6)
  v = arr.choices[3 + slot]; else v = arr.choices[6 + slot];`
  with `slot = pick % 3` hoisted and `v &= 0xff;` at the join.  Mac
  confirms the same shape (controls.c already uses it).  CAVEAT: the
  split alone increased the byte count on set_new_province due to a
  rover/OptPull cascade — landed as source-truthful regardless (Mac
  oracle wins over byte count when shape is provable).
* **Off-by-one semantic check via Mac** (initreg_game_loop revealed
  `(&empire_region_order[10])[region_over]` is mathematically
  `(&empire_region_order[9])[region_over+1]` and Mac's
  `(&empire_region_order[10])[province_is]` is yet another
  re-arrangement — semantically the SAME byte address but the source
  form influences the seat chosen for the loaded value); not always
  reachable without matching the literal base/index PS used.
