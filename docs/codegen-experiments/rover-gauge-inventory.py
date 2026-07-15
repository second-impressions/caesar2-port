"""rover-gauge-inventory -- the byte-neutrality census of walk-changing
edits, measured over the byte-exact corpus (the rover's "gauge moves").

Motivation (2026-07-09): rover-blocked functions need a byte-neutral
+-1 advance inside a named influence window.  The doctrine said "the
byte-neutral +1 lever is load-folding: the split lands the rover on
the same register = identical bytes, +1 advance" -- never measured.
This experiment byte-compiles EVERY fold/unfold candidate on the
byte-exact corpus, joins each with its trace-level walk delta
(c2.regalloc.lwalk), and attributes the first differing byte to the
EDIT SITE vs DOWNSTREAM.

Method
------
For all byte-exact fns >= 48 b with >= 1 fold (de_invent) / unfold
(cache_field) candidate (248 fns, 532 scored rows):
  1. compile the base TU (ForgeBuilder LE), require byte_diff 0;
  2. per candidate: trace both spellings (spelling_compare -> walk
     delta per rover class), byte-compile, find the FIRST differing
     byte, and compare it against the edit statement's offset (from
     the base compile's -d1 marks).

Results (532 rows; .c2-cache/rover-gauge-inventory.json)
--------------------------------------------------------
  walk-same (INERT@BURN class):     115 rows, 16 changed bytes (14%)
     -> confirms the spell-verdict-audit calibration at 5x the N.

  walk-differs (LIVE class):        417 rows
    family   kind      site-changing  downstream-only  fully-NEUTRAL
    fold     w/ delta        46             23               3
    fold     reorder-0      113             50               9
    unfold   w/ delta        62             27               0
    unfold   reorder-0       57             26               1

  KEY CORRECTIONS TO THE DOCTRINE:
  * "load-fold = identical bytes at the site" holds ~35% of the time
    (26/72 advance-carrying folds are site-neutral); the rest change
    codegen AT the fold statement (width/idiom shifts).  Every window
    candidate must be BYTE-SCREENED (c2 sweep / the audit harness,
    ~0.1 s each) -- the trace screener alone cannot certify site-
    neutrality.
  * DOWNSTREAM-ONLY ROTATORS exist in every advance class (dword+1
    x12, dword-1 x14, byte+-1 x17, dword+-2/4 x5) AND as pure walk
    reorders with zero advance delta (x76).  The window-lever menu is
    therefore much broader than "in-window foldable loads": any
    fold/unfold whose own site compiles identically and whose delta
    matches the window requirement is a candidate, and zero-delta
    walk reorders can move seat picks downstream by themselves.
  * FULLY-neutral advance carriers (advance with zero byte effect
    anywhere) are rare (3/417: EncodePosition de_invent(i)
    byte+1+dword+1, sf10_hunt_for_fight de_invent(latched) word+1,
    push_shell de_invent(d) dword+4) -- they need no downstream
    consumers of the rotated class, so they are NOT usable as window
    levers (nothing downstream changes, including the divergence).

Operational recipe for a Rover-blocked function:
  1. read the influence window + required delta off the Rover-fit
     hint;
  2. generate fold/unfold candidates at ALL lines in/at the window
     (spell --suggest --lines), not only census-flagged foldables;
  3. byte-compile every LIVE candidate whose delta sign matches --
     expect ~1/3 to be site-neutral; the byte oracle adjudicates.

Reproduce: the harvest loop lives in this file's git history /
the session notes; the row schema is
  {fn, tag, delta, walk_same, tree_same, changed, first_diff,
   site_off, edit_line, ps_len}
and the data is at .c2-cache/rover-gauge-inventory.json (regenerate
with the spell-verdict-audit harness extended with first-diff
attribution -- see docs/codegen-experiments/spell-verdict-audit.py).
"""
