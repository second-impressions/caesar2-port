# Mac PPC cross-check of the entities.h `_unk`/`_reserved`/`_unused_writeonly` fields

The DOS `PS.EXE` and the Mac PPC build were compiled from the **same source**
by different compilers (Watcom 10.0a vs CodeWarrior).  A struct field that is
never read in **either** independently-compiled build is almost certainly
genuinely vestigial source-level slack — not merely "a reader we failed to
decompile in PS.EXE."  This doc records a global-access scan of the Mac binary
against every unknown field, to confirm (or refute) the `_pad`→`_unk` rename
classifications.

## Method

`c2/macref.py` disassembles the Mac PPC binary and annotates TOC-relative
global loads (`; &c2inf`, `; &figure_list`, …).  A dataflow scan
(see the session script; lives conceptually next to `c2 mac-fn`) taints the
register holding a global's address and follows it through:

* immediate-offset access `field(rBase)` on the global pointer,
* **array element** access — `mulli`/`slwi`/`rlwinm` scales the index by the
  struct stride, an optional `addi` adds the field offset, then an indexed
  `lbzx/lhzx/lwzx/stbx/…` reads/writes the field.  The field offset is recovered
  from the index accumulator.

Mac offsets are translated back to PS offsets via the PPC "power" alignment
layout (scalars aligned to size; PS is byte-packed → the two layouts differ once
an `int`/`short` is preceded by an odd number of bytes).

**Validation gate:** the scan is only trusted for a struct when it recovers
accesses for (almost) all *named* fields.  Coverage achieved:

| struct (container) | named-field coverage | functions |
|---|---|---|
| `figure_rec` (`figure_list`) | 66/66 | 87 |
| `unit_rec` (`unit_list`) | 38/39 | 32 |
| `citizen_rec` (`citizen_list`) | 35/36 | 54 |
| `army_rec` (`army_list`) | 61/63 | 113 |
| `web_node` (`web`) | 6/6 | 11 |
| `c2inf` (global) | all anchors | 108 |

The scan handles `mulli` **and** `slwi`/`rlwinm` index scaling (CodeWarrior
uses a shift for power-of-two strides, e.g. citizen `slwi rX,rX,6` = ×64), and
the layout parser is nested-struct aware (`struct century centuries[14]` inside
`army_rec`).

## Result — every checked unknown field is DEAD in the Mac build too

All of the following are **never read or written** in the Mac binary (except the
three write-only fields, which are write-only in *both* builds):

* **c2inf** `_unused_writeonly36` (PS+0x36 / Mac+0x38) — only `basic_inf_settings`
  stores it; no reader.  `_unused_writeonly38` (PS+0x38 / Mac+0x3A) — only
  `load_inf` stores it; no reader.  Both confirmed dead in both builds.
* **web_node** `_unused_writeonly02` (PS+0x02 / Mac+0x02) — only `init_web` zeroes
  it; no reader in either build.
* **figure_rec** `_unk21 _unk2A _unk34 _unk42 _reserved50` — no Mac access.
* **unit_rec** `_unk0A _unk19 _unk21 _unk24 _unk28 _unk2B _unk2F _unk33 _unk37
  _unk3C _reserved43` — no Mac access.
* **citizen_rec** `_unk1C _unk25 _reserved37` — no Mac access.
* **army_rec** `_unk20 _unk2B _unk31 _reservedA7` — no Mac access (113 fns).

**Conclusion:** these are genuine source-level slack/vestigial fields.  Two
compilers from the same source both never read them, which upgrades confidence
well beyond the single-build "we didn't find a reader" status.  The `_unk` /
`_reserved` / `_unused_writeonly` names are correct.

## Side finding (RESOLVED) — c2inf's Mac+0x45 is a Mac-only window-mode flag

While mapping c2inf, the scan found a **heavily-used** byte at **Mac c2inf+0x45**
(10 loads + 6 stores) by window-mode functions:

```
set_window_mode, set_dual_window_mode, act_toggle_window_mode,
show_map_windows, city_mode_show_provmap, prov_mode_show_citymap,
act_goto_city, AdjustMenus, start_a_new_game, start_a_promotion,
do_a_tutorial_page, mac_open_game
```

`set_window_mode` reads it as a boolean: 0 → single window (`set_title`),
nonzero → dual window (`select_window`).  It is the **dual-window-mode flag**.

**Resolution: it is Mac-only; the DOS struct is correct as-is.**
  * DOS `c2inf` is at 0x9CFF0 and the next named global, `negative_buffer`,
    sits at **exactly c2inf+0x40** — so the DOS struct genuinely ends at 0x40
    (`max_samples` is the last field).  There is no room for the flag.
  * PS.EXE has **no** `set_window_mode`/`select_window`/`set_title` symbols at
    all — dual/resizable windows are a Mac-port UI feature; the DOS build is
    full-screen.
  * So in the shared source the flag is `#ifdef`'d into the Mac build only.
    No DOS action needed; `entities.h` `c2inf_rec` (0x40 bytes) is complete.
    Noted in the struct comment for future readers.

## Not yet cross-checked in the Mac build (PS-only evidence)

`arrow_rec` (no `arrow*` TOC global resolved in the Mac map), `request_message`
/ `selection_rec` / `wall_gfx_rec` / `house_unrest_rec` (not Mac TOC globals, or
single-use). Their `_unk`/`_reserved` names stand on the PS-only evidence.

**Upgraded to *exhaustive* PS-only proof (whole-binary scan):** for fields that
the Mac scan can't reach, a full disassembly of PS.EXE's 512 KB code section
(capstone) collecting every memory-operand displacement, cross-checked with an
alignment-independent raw-byte scan for the field's displacement constant,
proves a field is *never* read or written anywhere in the binary (not merely
"no reader found in the functions we looked at"):

* **`arrow_rec._unk1F`** (+0x1F) — 0 accesses across the whole binary; every
  other arrow_rec field is touched.  0 in all 41 sample saves.  Confirmed dead.
* **`province_industry._unk08` / `._unk0C`** (+0x08 / +0x0C) — 0 accesses
  anywhere; only `.kind` (+0x00, 4×) and `.is_trader` (+0x04, 7×) are ever
  touched.  0 in all 41 sample saves.  Renamed `_f08`/`_f0C` → `_unk08`/`_unk0C`.

The scan is validated the same way as the Mac scan: it recovers the known-used
slots at their expected counts (province `.kind`=4, `.is_trader`=7; arrow
`anim_delta`=9, `fire_range`=5), so a zero for a candidate field is a real
absence, not a coverage gap.
