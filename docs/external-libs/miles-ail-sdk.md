# Miles AIL SDK reference header

This doc covers the **real, upstream Miles AIL (Audio Interface Library)
header** — `AIL.H` (not kept in this repo; re-acquire it from the
provenance below) — studied as *reference evidence* for how a 1995-era
Watcom C game was meant to talk to the Miles sound system.  It is NOT part of
the Caesar II decompilation source tree; it is a read-only reference used to
justify codegen claims (see `watcom10.0a repo docs/wcc386-re/farptr-return-edx-mustsave.md`).

See [`miles-ail-versions.md`](miles-ail-versions.md) for the full version index and the
**PS.EXE pin (AIL 3.03 base, 1995-06-18)**, plus the collected multi-version
headers and the RAD changelog (all re-acquirable from the sources listed
there).

## Provenance

- **Source:** `gondur/mig_src` on GitHub (Rowan Software's *MiG Alley* source
  release — `BOB_Src` / "Rowan's Battle of Britain").  MiG Alley shipped with
  a licensed copy of the Miles AIL SDK headers, including this `AIL.H`.
- **Commit / pin:** `7adf5e68c56f1bfbc79430064df39e36a4e665b6` (2015-08-07).
  Downloaded 2026-06-20.
- **License:** MiG Alley was released under a permissive source licence (see
  the repo's `LICENSE.md` / `LICENCE.DOC`).  Vendoring this one header here for
  RE-reference is consistent with that; the Caesar II decompilation itself
  does not link or build against it.

## What this header proves (the `modify exact [eax gs]` question)

The Caesar II `pcsound.c` far-ptr cluster (`start_sequences`,
`start_samples`, `pos_sound`, …) carries `#pragma aux <fn> modify exact
[eax gs]`.  Binary RE of Watcom 10.0a (`watcom10.0a repo docs/wcc386-re/`) proves this pragma
is the *only* C-level lever that makes a far-ptr-returning function push EDX
(`MustSaveRegs`@0x4b67b + `FullReg`@0x3e113: only `ROUTINE_MODIFY_EXACT`,
set solely by `modify exact` per `i86reg.c:~119`, spares EDX).  This header
is the evidence that the pragma is the **documented Miles/Watcom register-
contract idiom**, not a decomp hack:

1. **`AILCALLBACK __pascal`** (AIL.H:325) — AIL callbacks are `__pascal`.
2. **`AIL_DRIVER` carries `REALFAR seg; U32 sel;`** (AIL.H:~552) — each driver
   is a separately-loaded binary with its own selector (its own segment
   context, incl. `gs` — see ail32.asm's `push gs`/`pop gs`).
3. **AIL is interrupt-driven** — `AIL_register_timer(AILTIMERCB)` (1124),
   the `INT 66H` dispatcher (`this_ISR`/`prev_ISR`, 481-482), `PM_ISR`
   (IRQ #, 559), `AIL_disable_interrupts`/`AIL_restore_interrupts`
   (1093-1094).  Callbacks fire from the timer/IRQ service routine.
4. **The SDK itself declares register contracts via `#pragma aux ... modify
   [...]` pervasively** (AIL.H:~1011-1052): `AIL_memset`, `AIL_memcpy`,
   `AIL_strcpy`, … all spell out their exact clobber set with `modify [...]`.
   So `#pragma aux <fn> modify [exact] [...]` is the standard Miles/Watcom
   spelling for "this function clobbers exactly these registers, preserves
   the rest."

`modify exact [eax gs]` on a Caesar II sound-init wrapper therefore reads as:
*this function clobbers only `eax` (the far-ptr return) and `gs` (the
AIL/driver segment), and preserves `ebx`/`ecx`/`edx`/`esi`/`edi`/`ebp`
exactly*.  EDX getting pushed is the necessary consequence of EDX being
preserved *under a far-ptr return* (which would otherwise FullReg-strip it).
`gs` is in the list specifically because `modify exact` pushes any unlisted
register and an unlisted `gs` would emit a spurious `push gs` (the
`[eax]`-alone variant regresses to 134 b with a `push gs` — verified).

Corroborating push sets in PS.EXE: the far-ptr cluster (`start_sequences`,
`pos_sound`) all save `[ebx ecx edx esi edi ebp]` (EDX via the pragma);
whereas the void AIL functions (`choose_odd_tune`, `set_db_sound`,
`fade_sequence_in`) push EDX *naturally* (a void return's `return_reg` is
EMPTY so `MustSaveRegs` strips only EAX, leaving EDX savable with no
pragma).  The actual AIL trigger callback `_mood_modfication` saves only
`[esi]` and clobbers edx freely — callbacks follow the
`AIL_* modify [eax ebx ecx edx]` scratch contract, so the pragma on the
init wrappers is the wrappers' own caller contract, not callback
interrupt-safety.
