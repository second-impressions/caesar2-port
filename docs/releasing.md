# Releasing

A release is a git tag `vX.Y.Z` (or `vX.Y.Z-rc1` for a pre-release) on a
commit of `main` whose `CMakeLists.txt` says that version and whose
`CHANGELOG.md` has a section for it. `.github/workflows/release.yml` builds
every download from that commit and opens a **draft** GitHub release;
publishing it is the one decision no script makes.

## Cutting one

`main` only takes pull requests, so it is two commands with a merge between:

```bash
tools/release.py prepare 1.0.0
```

turns the changelog's *Unreleased* section into `## 1.0.0 - <today>` (and
refuses an empty one), sets `project(VERSION 1.0.0)`, adds the release to
the AppStream metainfo, and opens the pull request `release: 1.0.0`. Merge
it when CI is green. Then

```bash
tools/release.py publish 1.0.0
```

starts the Release workflow on the merged commit. The workflow tags it
`v1.0.0`, builds, attests and drafts the release. Look at the draft, try a
download, press *Publish*. Nothing is bumped afterwards: `project(VERSION)`
only names releases, and the next `prepare` sets the next one.

Pre-releases: `prepare 1.1.0-rc1` sets `project(VERSION 1.1.0)`, tags
`v1.1.0-rc1` and marks the GitHub release as a pre-release.

Running the workflow by hand without a version (`gh workflow run
release.yml`) builds everything from any commit without tagging or
releasing: a dry run of the pipeline.

## What a release contains

| File | What it is |
|---|---|
| `caesar2-X.Y.Z-x86_64.AppImage` | Linux, one file. SDL3, zlib and libbacktrace linked in; only glibc (2.35 or newer, Ubuntu 22.04 on) from the machine. Every X11/Wayland/ALSA/PulseAudio/PipeWire backend is compiled in and loaded when present. Uses the current static AppImage runtime: no FUSE needed. Keeps its DWARF, so a crash report has file and line. |
| `caesar2-X.Y.Z.flatpak` | The same game as a Flatpak bundle (`flatpak install caesar2-X.Y.Z.flatpak`), from `packaging/io.github.second_impressions.caesar2.yml`. |
| `caesar2-X.Y.Z-macos.dmg` | `Caesar II.app`, universal (Apple silicon and Intel), macOS 11 or newer; SDL3 and libbacktrace linked in. Ad-hoc signed only: the first launch needs *Open Anyway* in System Settings → Privacy & Security (see below). |
| `caesar2-X.Y.Z-windows-x64.zip` | `caesar2.exe` with `SDL3.dll`, `zlib1.dll`, `caesar2.pdb` and the licences. Unzip anywhere and run; the PDB next to the exe is what makes Windows crash reports readable. |
| `caesar2-X.Y.Z-web.zip` | The browser build. Publishing the release puts it at the root of the Pages site (`pages-release.yml`); it is also for self-hosting (needs the cross-origin isolation headers, see `docs/webassembly.md`). |
| `SHA256SUMS` | Checksums of the above. Every file also carries a GitHub build-provenance attestation (`gh attestation verify <file> --repo second-impressions/caesar2-port`). |

Version strings, as `--version`, the about box and crash reports print
them: a release is its version, `1.0.1` or `1.1.0-rc1` — there is only ever
one of each, and the tag names the commit. Everything else names its
origin and commit: `main-29c2a676` for the main branch, `pr21-4fa3c2d1` for
pull request 21 (its head commit, not GitHub's merge ref), `dev-29c2a676`
for a clean local checkout, and `local-20260907-153000` (the configure
time) for an edited tree, which matches no commit. Download names follow
the same strings.

## The Linux build

`packaging/appimage/build.sh` is the whole AppImage recipe and runs inside
an `ubuntu:22.04` container, in CI and locally:

```bash
docker run --rm -v "$PWD:/src" -w /src ubuntu:22.04 packaging/appimage/build.sh
```

It configures with `PORT_VENDOR_DEPENDENCIES=ON` (`cmake/VendorDependencies.cmake`:
SDL3 and libbacktrace from pinned sources, static), checks that nothing
but the C library is linked dynamically, installs into an AppDir and wraps
it with appimagetool. To try the result elsewhere:

```bash
docker run --rm -v "$PWD/dist/caesar2-…-x86_64.AppImage:/c.AppImage:ro" \
    -e APPIMAGE_EXTRACT_AND_RUN=1 docker.io/library/fedora:latest /c.AppImage --version
```

A fully static binary is deliberately not attempted: SDL3 loads the display
and audio libraries with `dlopen`, which a static libc cannot do.

## Flatpak and Flathub

The manifest builds libbacktrace and SDL3 as modules on the freedesktop
24.08 runtime and the game from the checkout (`type: dir`). CI substitutes
the `@C2_BUILD_NUMBER@`/`@C2_GIT_HASH@`/`@C2_RELEASE@` placeholders. For a
Flathub submission, copy the manifest into the Flathub repository with the
`caesar2` module's source replaced by

```yaml
      - type: git
        url: https://github.com/second-impressions/caesar2-port.git
        tag: vX.Y.Z
```

and the three placeholder options removed (a git checkout knows its own
version). The metainfo already carries the `<releases>` entries Flathub
wants, added by `release.py`. The sandbox permissions are the ones the game
needs: `--device=all` for reading a CD-ROM as a raw device, read-only
access to the home directory and the usual mount points for importing
game data from wherever it is kept.

## macOS

`packaging/macos/make-dmg.sh` builds the universal bundle with the same
vendored SDL3 and libbacktrace as the AppImage (`CMAKE_OSX_ARCHITECTURES`
arm64 and x86_64, deployment target 11.0), renders the icon set from
`packaging/macos/icon-1024.png` (`tools/make-icons.py`, committed as `caesar2.icns`), signs the bundle
ad hoc (which arm64 requires to launch at all) and makes the dmg with
`hdiutil`. It runs on the release workflow's `macos-14` runner.

Without a Developer ID certificate and notarization, Gatekeeper reports the
app as unverified and, since macOS 15, the way past it is System Settings →
Privacy & Security → *Open Anyway* after the first refused launch. Both
need the Apple Developer Program ($99 a year); the workflow has the hooks
(`codesign` and a `notarytool` step) to add when a certificate exists.

Discs on macOS are read from the volume the system mounts under
`/Volumes`, which the launcher lists like a drive.

## Windows

The zip is the MSVC build CI has always made, plus the PDB. There is no
installer: the launcher imports the game data into `%APPDATA%`, so nothing
needs installing, and an installer would not change the SmartScreen warning
an unsigned executable gets. Signing needs a certificate; not planned.

## Not yet

- Developer ID signing and notarization for macOS; Authenticode for
  Windows.
- A rolling `nightly` pre-release from `main`.
