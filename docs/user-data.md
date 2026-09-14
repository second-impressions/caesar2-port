# Mutable user data

## Ownership

The portable target has two deliberately disjoint filesystem namespaces:

- `--asset-root` contains read-only installed/CD resources; and
- `--user-data-dir` contains every file created or changed by the game.

Without an override, SDL selects the platform preference directory for
`second-impressions/caesar2`. On WebAssembly, a storage pthread mounts WasmFS
OPFS and selects `/persistent/user-data`; imported assets use the separate
`/persistent/game-data` namespace. The engine never falls back from one
namespace to the other. This keeps an installed game tree read-only and gives the
browser one persistent mount to synchronize.

The mutable files currently supported by the recovered engine are:

| File | Purpose |
| --- | --- |
| `*.sav`, including `lastyear.sav` | manual saves and yearly autosaves |
| `caesar2.inf` | 64-byte preferences and career block |
| `shot1.png` through `shot8.png` | portable screenshot hotkeys |
| a `--screenshot` filename | portable diagnostic PNG output |

`loadmodel` and the streamed speech database remain asset reads. DOS CD-drive
probing is not a user-data operation.

## Host boundary

The shared engine keeps its recovered save ordering, post-load repair, history
ring, and dialogs. The host boundary provides:

- whole-file and offset reads/writes for preferences, history, and complete
  validated save streams;
- lossless PNG encoding from the read-only indexed frame and VGA palette;
- existence checks in the mutable namespace; and
- bounded wildcard enumeration for the recovered `char directory[100][13]`
  save picker.

The SDL implementation rejects absolute paths, drive prefixes, and `..` path
components. Flat runtime filenames are resolved case-insensitively so a save
created as `ROME.SAV` can be read or overwritten as `rome.sav` on Linux.
Save-list results are sorted case-insensitively and exposed in DOS-style upper
case for deterministic recovered-UI behavior. Entries which cannot fit the
original 8.3-style 13-byte row are omitted.

Portable screenshot encoding is implemented by the SDL backend and requires
SDL 3.4 or newer. The recovered DOS and Windows targets retain their original
LBM writer and `shotN.lbm` names; only the portable feature branch uses PNG.

The engine worker uses these synchronous operations. In the browser, OPFS is
mounted before SDL host initialization. Successful writes are flushed before
the save operation completes; the recovered save code does not become
asynchronous. Export immediately downloads one `caesar2-user-data.zip`
containing every `*.sav`, `history.dat`, and `caesar2.inf` file in the durable
namespace. The same ZIP can be imported directly, with every entry passing the
normal size and filename validation before it is written.

      if (/\.sav$/i.test(name)) {
        // Either the original 225,745-byte layout or the port's container
        // (FlatBuffer with identifier "C2SV" at offset 4, docs/save-format.md).
        const isLegacy = data.byteLength === 225745;
        const head = new Uint8Array(data.buffer ?? data, data.byteOffset ?? 0, Math.min(8, data.byteLength));
        const isContainer = data.byteLength > 8 && head[4] === 0x43 && head[5] === 0x32 && head[6] === 0x53 && head[7] === 0x56;
        if (!isLegacy && !isContainer) throw new Error(`${name} is not a Caesar II save`);
      }
