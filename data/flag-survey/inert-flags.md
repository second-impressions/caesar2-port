# Provably-inert flags (dropped from the survey 2026-06-15)

Measured by compiling every C TU at `BASE` vs `BASE + flag` and comparing
the **full _TEXT code bytes** (bug-independent: the FIXUPP/`_dm` bugs only
affected diff *scoring*, never the compiled output). A flag is inert iff
it produces byte-identical `_TEXT` on **all 33 TUs**.

## Inert standalone (dropped)
`-ei`, `-fp2 -fp3 -fp5 -fpc -fpi -fpi87 -fpr` (all FP variants),
`-om -on -op -oz` (inert `-o` letters), `-r`, `-zp1` (== baseline default
pack), `-zdp -zff -zfp -zg -zgf -zgp -zl -zld`.

## Inert `-o` letters in COMBINATION too (dropped from the `-o` pool)
`m, n, p, z` — verified byte-identical when appended to `-os/-oa/-ol/-oe/`
`-oc/-ot/-ox/-or` across evolver/map/battle/action/int_c2. `-o` pool
shrinks 17 -> 13 letters (`acdefilorstux`).

## Settled dimension (dropped)
Debug is `-d1` only (confirmed). `-d2`, `-d3`, `-d1+`, `-ez` removed
(`-d2/-d3` force `-od` = no-opt, not PS's build; `-ez` breaks parsing).

## Effect
Config space 4390 -> 1603 (compiles 144,870 -> 52,899, ~80min -> ~29min).
Flags that DO change bytes and are kept: CPU `-3r/-3s/-4s/-5r/-5s`,
`-j -ri -sg -st`, packing `-zp2/-zp4/-zp8`, `-zc -zm -zu -zdf`, `-en -ee`,
and `-o` letters `a c d e f i l o r s t u x`.
