# TODO — live remaining work

Updated 2026-07-15 (toolkit-retirement pass).  This file is intentionally a
short list of unfinished work.  Completed campaigns and stale corpus
snapshots belong in git history and the dated documents under `docs/`.

## Current verified state

- reccmp (`c2 reccmp code` / `data`): **2234/2234 functions implemented and
  address-aligned at 100% accuracy; 1593 initialized-data symbols, 0
  issues**.
- Final-link comparison (`c2 rebuild`, every line exact):
  - game C 1435/1435 · c2-asm 87/87 · av-delink 517/517 · crt 195/195;
  - initialized data 341/341; LE sizes all exact;
  - placement: code starts 2234/2234 exact; data placement 1538/1538 named
    exact, 58 statics via delink/anchor;
  - **strict whole-code-object: 0 differing bytes / 508368** with only
    loader fixups masked and every relative branch displacement visible.

The burn-down diagnostic toolkit was retired 2026-07-15 (see git history);
verification is `c2 rebuild` + the reccmp fork.

## 1. Header provenance, not data placement

Corroborate original header filenames / include graph and the 35 non-data
lib32 slots only if an external source artifact appears.  Do not sacrifice
exact BSS placement for an unsupported filename guess.

## 2. Oracle data reintroduction (eventually)

The Mac/Windows oracle data (windows func/global maps, crossbuild map,
flag-survey results) was removed with the diagnostic toolkit; copies exist
outside the repo and can be reintroduced if a use case appears.

## Explicitly out of scope

- byte-exact Watcom debug section;
- original source file/path strings and file naming;
- inverse-compiler research (continues in the watcom10.0a sibling repo).
