# Caesar II `.LBM` Screenshots (standard IFF PBM)

> ImHex pattern: [`tools/imhex/caesar2_lbm.hexpat`](../tools/imhex/caesar2_lbm.hexpat).

Caesar II's `.LBM` files are **not a custom format** — they are standard **EA IFF-85
`PBM `** (DeluxePaint chunky 8-bit LBM). Use the public spec; this note only records the
C2-specific choices.

- **Spec:** EA IFF 85 / ILBM (<https://wiki.amigaos.net/wiki/ILBM_IFF_Interleaved_Bitmap>),
  LBM/PBM (<https://moddingwiki.shikadi.net/wiki/LBM_Format>).
- **Structure:** `FORM <size> "PBM "` then chunks `BMHD`, `CMAP`, `BODY` (big-endian
  chunk ids + sizes, padded to even).

## C2 specifics (from `write_lbm` / `LBM_HEADER1`/`LBM_HEADER2` in `datainit.c`, verified)

| Field | Value |
|---|---|
| FORM type | `"PBM "` (chunky, not interleaved `ILBM`) |
| BMHD size | 640 × 480, 8 planes |
| BMHD compression | **0 (uncompressed)** |
| CMAP | 256 × 3 = 768 bytes, **8-bit** RGB (full 0–255, unlike the 6-bit `.256` palettes) |
| BODY | raw `0x4b000` = 307,200 bytes (640 × 480 indices, no RLE) |

> The byte comment on `LBM_HEADER1` in `datainit.c` labels the trailing `01 01` as
> "compress / pad"; those are actually the BMHD **xAspect / yAspect** fields. The real
> compression byte is `0`.

## Producers / consumers (PS.EXE)

- `capture_shot("shot1.lbm" … "shot6.lbm")` — F-key screenshot capture writes the LBM.
- `write_lbm` — emits `LBM_HEADER1`, the `CMAP` palette, `LBM_HEADER2` (`BODY` header),
  then the pixel data.
- `convert_lbm_file` / `show_lbm` — read a tutorial `.lbm` back into the screen buffer.
