# Game-data import feasibility results

Measured 2026-08-23 with the current port, Emscripten 6.0.2, the local Caesar II release corpus, and disposable test programs under `/tmp`. No original game data or benchmark binaries are tracked.

## Result summary

- ZIP import with reduced libarchive is viable on native and Wasm.
- Libarchive is **not** compatible enough to be the sole ISO reader for the observed discs.
- A project-owned, read-only ISO-9660 reader is small enough and preferable.
- MODE1/2352 and MODE2/2352 BIN/CUE adaptation is required by the preserved corpus.
- WasmFS OPFS persists assets larger than the entire fixed Wasm heap without growing that heap.
- The current IDBFS setup and WasmFS cannot coexist unchanged; both user and asset storage should migrate to OPFS.
- A safe single-release optimized corpus is approximately 57 MB uncompressed and 35 MB as an ordinary deflated ZIP.
- Content-addressing makes an all-observed-language pack practical: all 13 DOS release profiles deduplicate to about 89 MB uncompressed.

## Reduced libarchive benchmark

### Build

Pinned inputs:

- libarchive 3.8.2, commit `7f53fce04e4e672230f4eb80b219af17975e4f83`;
- Emscripten 6.0.2-git;
- Emscripten zlib port 1.3.2;
- CMake 4.1.2 and Ninja 1.13.2; and
- native Clang 21.1.8.

The static build disabled programs, tests, crypto, ACL/xattr, XML, iconv, and all compression libraries except zlib. The harness registered only:

```c
archive_read_support_filter_none(archive);
archive_read_support_format_zip(archive);
archive_read_support_format_iso9660(archive);
```

Artifact sizes:

| Artifact | Size |
| --- | ---: |
| Native `libarchive.a` | 1.9 MiB |
| Wasm `libarchive.a` | 972 KiB |
| Linked native executable increment | 151,624 bytes |
| Linked Wasm increment | 145,645 bytes |
| Linked Wasm gzip increment | 62,233 bytes |
| JavaScript glue increment | 3,435 bytes |

Static section garbage collection makes the shipped impact much smaller than the library archive itself.

### Synthetic ZIP and ISO

A 27-file, 34,596,768-byte mixed-case Caesar-like fixture was packed both as a deflated ZIP with one outer directory and as a Joliet ISO with `HD`, `PL8`, `RAW`, `XMI`, and `SMK` roots.

All four native/Wasm-format combinations returned the same file count, byte count, and hash.

Median of five warm runs:

| Container | Native | Wasm under Node |
| --- | ---: | ---: |
| ZIP | 23.45 ms | 79.87 ms |
| ISO | 19.48 ms | 72.38 ms |

Peak increments:

| Container | Native RSS | Node/Wasm RSS |
| --- | ---: | ---: |
| ZIP | about 1.4 MiB | about 5.1 MiB |
| ISO | about 1.2 MiB | about 1.9 MiB |

The Wasm harness retained a fixed 64 MiB heap.

### Real ZIPs

The normalized 676-file, 58,808,176-byte European asset tree produced:

- stored ZIP: about 57 MB;
- deflated ZIP: about 35 MB;
- native read: 140.8 ms; and
- Wasm/Node read: 248.3 ms.

The actual German rerelease outer ZIP contains a 211,670,592-byte BIN plus its CUE. Reduced libarchive streamed the complete 211,670,725-byte payload with matching native/Wasm hashes in:

- native: 591.7 ms; and
- Wasm/Node: 972.4 ms.

This confirms ZIP is suitable both for optimized installation packs and for the observed ZIP-wrapped BIN/CUE dumps.

Libarchive correctly rejected truncated ZIP/ISO test inputs. It intentionally accepted traversal, absolute, and case-colliding entry names, confirming that project-owned canonicalization and quotas are mandatory.

## Real ISO corpus compatibility

Every one of the 13 local PC CD archives contains one BIN and one CUE. They were converted to logical 2048-byte sector streams using the existing proven adapter, then opened with reduced libarchive.

| Result | Releases |
| --- | ---: |
| Clean complete parse | 7/13 |
| Rejected during open | 3/13 |
| Enumerated files, then failed on invalid extent | 3/13 |

Clean parses included MODE1 and both MODE2 German rereleases. Failures included ordinary MODE1 releases. Disabling Joliet did not resolve them. PyCdlib and the existing project tooling can enumerate all 13, so the discs are usable but expose libarchive compatibility/strictness gaps.

Decision and implemented result:

- reduced libarchive is used for ZIP;
- the in-tree ISO-9660 reader uses a 2048-byte sector callback;
- plain ISO files feed that callback directly;
- BIN/CUE uses a MODE1/2352 or MODE2/2352 adapter; and
- the project reader catalogued all 13 releases. Ten matched PyCdlib's complete
  file count; three older discs each contained one dangling out-of-track
  installer/catalogue extent, which is reported and omitted while all required
  game assets remain available.

The required ISO subset is small: primary volume/root discovery, directory records, extent-bounded file reads, multi-sector files, `;1` normalization, and ASCII case folding. Joliet can be added only if a supported real image needs it.

## OPFS persistence benchmark

A disposable pthread/WasmFS probe was built with:

```text
-pthread
-sWASMFS
-sPTHREAD_POOL_SIZE=2
-sINITIAL_MEMORY=67108864
-sALLOW_MEMORY_GROWTH=0
```

The OPFS backend was created off the browser main thread. The probe wrote and reopened:

- an 80 MiB asset in 1 MiB chunks;
- `user-data/caesar2.sav`, 225,745 bytes; and
- `user-data/history.dat`, 4,000 bytes.

### Chromium 150

Creation, page reload, and a separate browser process using the same profile all passed. Heap size remained exactly 67,108,864 bytes before and after the 80 MiB write.

### Firefox 152

Creation and page reload also passed with the fixed heap unchanged.

### Browser JavaScript access

The persisted files were directly readable through `navigator.storage.getDirectory()`. This supports downloads without copying save files through the Wasm heap.

Headless Chromium reported roughly 84 MB used from a 10.8 GB quota. The data survived restart even though `navigator.storage.persist()` was denied in that automation profile. Production must request persistence after a user gesture and display whether the browser granted it; export remains important when storage is best-effort.

### Migration constraint

The current Wasm build sets `SDL_EMSCRIPTEN_PERSISTENT_PATH=/user-data`, which links IDBFS. Emscripten rejects linking `idbfs.js` with WasmFS. The production migration must therefore:

1. enable WasmFS;
2. remove SDL's IDBFS persistent-path setting;
3. mount one OPFS backend from a storage pthread;
4. place imported assets below `game-data/`;
5. place all mutable files below `user-data/`; and
6. start SDL/the engine only after storage initialization and source validation.

## Save-state corpus

Observed portable state:

| File | Size | Requirement |
| --- | ---: | --- |
| `caesar2.sav` | 225,745 | durable and exportable |
| `lastyear.sav` | 225,745 | durable and exportable |
| arbitrary `*.sav` | 225,745 when valid | durable and exportable |
| `history.dat` | 4,000 | durable and exportable |
| `caesar2.inf` | 64+ | durable settings/career state |

Each portable save already includes a 4,000-byte history tail, but the running game also maintains `history.dat`; exports should include both. Persist the complete user-data namespace. The default export UI should select all `*.sav` plus `history.dat`, with `caesar2.inf` offered as settings/career data.

## PC corpus inventory

The 13 full releases span Europe, USA, Germany, France, and Italy, including OEM and rerelease discs.

- 11 CUEs specify MODE1/2352.
- Two German rereleases specify MODE2/2352.
- Core layout is stable: about 368 `HD` files, 218 PL8s, 73 RAWs, 13 media SMKs plus the installed intro, and five XMIs.
- Later hybrid discs additionally contain a 683-file `C2WIN95` tree.

Runtime-relevant path intersection across all 13 releases:

- 631 paths;
- 56,910,462 bytes for the representative Europe contents;
- 537 byte-stable files; and
- 94 variant files.

The 94 variants comprise 71 RAW speech files, 16 PL8 graphics, three WAV files, two ENG files, one DAT, and one SMK. Observed text data contains six distinct `C2.ENG` variants and four distinct `HELP.ENG` variants.

A conservative capability split is:

| Group | Files | Europe bytes |
| --- | ---: | ---: |
| Core graphics/data/music/effects | 544 | 26,942,418 |
| Speech | 73 | 11,930,788 |
| Video | 14 | 18,037,256 |
| Complete conservative runtime set | 631 | 56,910,462 |

A source-literal scan found 387 files / 50.15 MB, but dynamic filename tables make that unsafe as a complete manifest. Five semantic smokes opened 102 files / 13.44 MB; province selection alone opened 34 files / 3.24 MB. These are lower bounds, not shipping manifests.

Content-addressing all observed DOS-release variants results in:

- 717 unique blobs;
- 89,053,630 uncompressed bytes; and
- only 32,143,168 bytes over one representative complete release.

Thus an all-observed-language asset pack is practical if stable files are stored once and profiles map canonical names to hashes.

## Higher-quality media testing

A hybrid tree using `C2WIN95/HD`, Win95 PL8/RAW/SMK, disc-root XMI, and the DOS `CAESAR.OPL` bank passed:

- province selection;
- city loop;
- all 25 tutorial pages;
- Campania speech transition; and
- the eight-second music-buffer smoke with no underflows.

The missing DOS OPL/AD bank produced warnings before it was added, so a portable music profile must include at least one supported bank even when all other media come from Win95.

Measured official video sets from the existing fidelity audit:

| Set | Uncompressed size |
| --- | ---: |
| DOS | 18.0 MB |
| Win95 | 28.6 MB |
| Mac | 32.3 MB |

Win95 and Mac use 500x240 versions of the five marquee cinematics. Mac has the highest bitrate where it differs and replaces `INTRO.SMK` with `INTRONEW.SMK`. The asset manifest must therefore support 64-bit sizes, arbitrary blob sizes, and logical aliases such as presenting `INTRONEW.SMK` to the engine as `INTRO.SMK`.

## Conclusion

The architecture is implemented with a fixed heap:

- isolated OPFS tests pass at 64 MiB; the integrated SDL/game/WasmFS build
  measured slightly above 71 MiB and now reserves a fixed 96 MiB;
- OPFS stores durable browser objects and user data;
- reduced libarchive for ZIP ingestion;
- a project-owned ISO reader plus BIN/CUE sector adapter;
- transactional, content-addressed generations; and
- manifest-selected language, speech, graphics, music, and video profiles.
