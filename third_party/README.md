# Bundled third-party code

Everything under `third_party/` is a plain copy of an upstream project that
no distribution packages and whose upstream is designed to be dropped into a
consumer's source tree. All packaged dependencies (SDL3, zlib, libbacktrace,
Unity) are found on the build host by CMake and are never bundled. There are
no git submodules; a release tarball builds as-is.

Packagers: declare these as bundled, e.g. `Provides: bundled(nuked-opl3)`.

| Directory | Upstream | Version | License | Local changes |
|---|---|---|---|---|
| `libsmacker/` | https://github.com/GregKennedy/libsmacker | commit `76094fb9` (1.2.0 + fixes, 2023) | LGPL-2.1-or-later (`COPYING`) | `patches/0001..0003`: decoder robustness fixes carried in the [second-impressions fork](https://github.com/second-impressions/libsmacker); submitted upstream |
| `nuked-opl3/` | https://github.com/nukeykt/Nuked-OPL3 | 1.8 | LGPL-2.1-or-later (`LICENSE`) | none |
| `font8x8/` | https://github.com/dhepper/font8x8 | `font8x8_basic.h` | Public domain | none |

Only the files the port compiles are kept: `smacker.c`, `smacker.h`,
`smk_malloc.h` from libsmacker; `opl3.c`, `opl3.h` from Nuked OPL3. To update
one, replace the files from upstream, re-apply `patches/` where present, and
record the new version here.
