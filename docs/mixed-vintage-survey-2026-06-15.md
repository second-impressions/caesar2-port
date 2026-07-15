# Is PS.EXE a mixed-vintage `.obj` link?  No — survey result

**Hypothesis (worth testing):** PS.EXE 1996-04 might link `.obj`s of
different compiler vintages — unchanged TUs carrying an *older*
compiler's codegen (reused `.obj`), changed TUs recompiled by a newer
one.  That would explain why our `wcc10a` reproduces ~87% but has a
stubborn ~13% residue (incl. the framed-mid-epilogue / Rule 135 class).

**Verdict: ruled out.**  It is a clean single-toolchain build; our
reproduction gap is uniform and complexity-correlated, not vintage-split.

## Evidence

Three byte-distinct DOS builds (`c2 crossbuild-map`): dbg-1996-04
(`data/PS.EXE`), rel-1995-10, rel-1995-09.  Only **~10 functions** differ
between 1995 and 1996; ~2030 are byte-identical across all three.  The
1996 build = 1995 game code + `-d1` debug info + ~119 added library
functions.

**1. Reproduction rate by build-history bucket** (our `wcc10a` vs the
crossbuild status of each function we compile):

| function set                              | reproduced |
|-------------------------------------------|-----------:|
| byte-STABLE across all 3 builds           | 1157/1323 = **87%** |
| CHANGED between builds (differs/near)      |   12/22  = 54% |
| NEW in 1996 (absent in 1995)              |  149/169 = **88%** |

A mixed link predicts NEW/CHANGED code reproduces *better* than STABLE
(it would match the "newer" compiler).  Instead STABLE and NEW are
equal (87 vs 88%) — our compiler relates to all of it the same way.
One toolchain.

**2. Per-TU rate is a smooth complexity gradient, not bimodal**
(50%→100%): evolver 51%, map 75%, battle 73%, … , action 96%,
common 100%.  Mixed compilers per TU would give some files ~100% and
others ~0%.  Moreover reproduction varies *within* a single TU
(map.c = 104 exact / 34 diff; the diffs are its complex functions) —
impossible if a whole TU's `.obj` came from a different compiler.

**3. The framed-mid-epilogue functions are crossbuild-EXACT**
(`sail_to_target`, `get_wf_dirc`, `try_this_regionmap_square`,
`devolve_a_building` — byte-identical across all three builds, never
recompiled), and **every Watcom 9.01e/9.5/9.5c/10.0a/11.0/11.0c
produces END** for the framed probe (`watcom10.0a/probes/framed-epilogue/FR3.C`,
86b on 9.x / 89b on 10.0a+, both END).  So it is neither a recompile
artifact nor a compiler-version difference.

## Consequence for the framed-mid-epilogue (Rule 135) open question

The survey + version sweep eliminate vintage/version as the cause.
Since the function is byte-stable across builds and no Watcom vintage
reproduces it from a faithful probe, the only surviving explanation is
a **source shape for the single shared RETURN block that we haven't
recovered** — the body is byte-exact (instructions match), only the
return-block gen_id (hence epilogue position) differs.  That is the FE
return-block-placement lever (mechanism A), now the sole candidate.

Do not re-investigate the mixed-vintage / newer-CRT idea — it is
closed.  (The CRT itself is already proven byte-identical across builds,
same toolchain, per `c2 crossbuild-map`.)
