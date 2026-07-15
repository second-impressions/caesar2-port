# Windows binaries — extracted corpus

Every distinct Windows PE/NE binary that ships across the 13 Caesar II CD
images (`CDs/*.zip`), de-duplicated by sha256.  Extracted with
[`scripts/extract_windows_binaries.sh`](../../scripts/extract_windows_binaries.sh)
(zip → bin/cue → `bchunk` ISO → `7z` pull of the windows files → hash-dedup →
delete all intermediates).

* `store/<sha256>` — the unique binaries (9 of them), content-addressed.
* `named/*` — readable symlinks into `store/`.
* `manifest.tsv` — every (CD, path, size, mtime, sha256) row: which build
  rode which disc.
* `fingerprint.json` — the compiler/flag verdict per binary (produced by
  [`scripts/fingerprint_pe.py`](../../scripts/fingerprint_pe.py)).

Full write-up + method: [`docs/windows-builds-fingerprint.md`](../../docs/windows-builds-fingerprint.md).

**Headline:** the game engine `CAESAR2.EXE` (3 builds: 1996-08, 1996-12 DE,
1997-02) is **Microsoft Visual C++ 4.0**, **Debug config**, **`/Od`** (no
optimization), static single-threaded debug CRT — PDB
`C:\develop\MSDEV\Projects\C2Win\Caesar2.pdb`.  Bundled DLLs are vendor code:
`WAIL32.DLL` = Miles Sound System 3.50 (MSVC 4.0, Release), `SMACKW32.DLL` =
RAD Smacker (Watcom C/C++32).  The 16-bit `WINUPD16`/`C2WINPCH` are
MSSETUP/PKSFX installer plumbing.
