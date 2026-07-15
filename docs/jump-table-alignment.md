# Jump-table label alignment (cluster #32 / "alignment NOP" residue)

> **Disposition: exact-for-decomp.**  `decomp-verify` classifies these
> functions as exact (`~` row, `_trailing_table_pad_only`): every diff
> byte sits *after* the last executed `ret`/dispatcher-`jmp`, in the
> dead alignment filler before the fixup-masked jump table.  The CODE
> is byte-exact; only the filler differs.  JSON output carries
> `trailing_pad_diff: <n>` for the final whole-image byte recreation.

## Symptom

Functions in residue cluster #32 (`sa16_army_lurk_round_coast` /
`fight_barbarian` / `try_this_battlemap_square`) have 2–4 byte diffs in
the NOP-pattern bytes immediately before the embedded jump table that
follows the function's `ret`.  PS and RC pick a different NOP
form/length there.

For `sa16_army_lurk_round_coast`:

* PS at function-relative +0x1a5: `ea 7e 03 00 …` — the first
  jump-table entry (link-time fixup).  **No padding.**
* RC at +0x1a5: `8d 40 00 20 33 02 00 …` — a 3-byte `lea eax, [eax]`
  NOP, **then** the first entry.

## Cause: an lc-parity cascade, NOT a compiler-version or flag delta

The filler comes from the encoder's `DoAlignment` path around trailing
`OC_IDATA` select tables.  Its length is
`len = -lc & (align-1)` — the bytes needed to round the current
section location counter `lc` up to the next 4-aligned address — emitted
as a size-keyed Watcom NOP (1: `90`, 2: `8b c0`, 3: `8d 40 00`, …).
`DoAlignment` wraps the pad in `SavePendingLine(0)`, so filler bytes
carry no `-d1` line records.

Three binary facts pin the cause to cumulative TU layout, ruling out
the earlier (now-discarded) "PS disabled label alignment via
`OptForSize > 50`" and "wcc386-version delta" theories:

1. **PS emits NOP filler too.**  `fight_barbarian`'s trailing table is
   preceded by a 3-byte `8d 40 00` NOP **in PS itself** (+0x2F..0x31).
   PS's compiler did not have label alignment disabled; `sa16` merely
   happened to need 0 filler bytes.
2. **Neither build 4-aligns jump tables.**  Across every
   `jmp [reg*4+disp32]` dispatcher, PS table starts are a mod-4 mixture
   {0:10, 3:8, 1:6} and RC's are {3:14, 2:6} (zero aligned).  The
   filler was never "table alignment".
3. **The pad length tracks `lc` parity.**  For `fight_barbarian`: PS
   pad-point `lc ≡ 2 (mod 4)` → pad 3 (`8d 40 00`); RC `lc ≡ 1` → pad 2
   (`8b c0`).  Pad delta == lc delta.  The pad point's `lc` is a
   function of the **cumulative upstream TU layout** (every preceding
   function's size in the segment), not of the function that owns the
   table.

Aside: the trailing table after `fight_barbarian` actually belongs to
the *next* function (`move_citizen` — all 8 entries target
`move_citizen+0x6C`..`+0x126`); Watcom dumps a function's select table
just before the next function's entry label, in the gap that
`symbols.json` attributes to the previous function.

`-os` (global or per-TU) does NOT fix it and is a large net loss: a
per-TU `-os` on `int_c2.c` eliminated `sa16`'s 2-byte pad but introduced
49 new diff bytes (multiply lowerings, prologue, scheduling all gated on
`OptForSize`); global `-os` drops corpus exactness 1202 → 357.

## Disposition

Keep classifying these as exact-for-decomp (`~` trailing_pad).  **The
cluster self-heals with no compiler patch** once every function upstream
in the affected TUs is byte-exact *and* size-exact — the `lc` parity at
the pad point then matches and the filler converges.  Re-check with:

```
decomp-verify --json | jq '[.functions[] | select(.trailing_pad_diff)]'
```
