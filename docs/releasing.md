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
`v1.0.0`, builds, attests and drafts the release; for a final release the
script also opens the follow-up pull request `release: start 1.1.0`, so
builds from `main` are named `1.1.0-<build>-<hash>` from then on. Look at the
draft, try a download, press *Publish*.

Pre-releases: `prepare 1.1.0-rc1` requires `main` to be at `1.1.0` already
(it is, after the previous release's bump), tags `v1.1.0-rc1`, marks the
GitHub release as a pre-release, and bumps nothing.

Running the workflow by hand without a version (`gh workflow run
release.yml`) builds everything from any commit without tagging or
releasing: a dry run of the pipeline.

## What a release contains

| File | What it is |
|---|---|
| `caesar2-X.Y.Z-x86_64.AppImage` | Linux, one file. SDL3, zlib and libbacktrace linked in; only glibc (2.35 or newer, Ubuntu 22.04 on) from the machine. Every X11/Wayland/ALSA/PulseAudio/PipeWire backend is compiled in and loaded when present. Uses the current static AppImage runtime: no FUSE needed. Keeps its DWARF, so a crash report has file and line. |
| `caesar2-X.Y.Z.flatpak` | The same game as a Flatpak bundle (`flatpak install caesar2-X.Y.Z.flatpak`), from `packaging/io.github.second_impressions.caesar2.yml`. |
| `caesar2-X.Y.Z-windows-x64.zip` | `caesar2.exe` with `SDL3.dll`, `zlib1.dll`, `caesar2.pdb` and the licences. Unzip anywhere and run; the PDB next to the exe is what makes Windows crash reports readable. |
| `caesar2-X.Y.Z-web.zip` | The browser build, the same files GitHub Pages serves, for self-hosting (needs the cross-origin isolation headers, see `docs/webassembly.md`). |
| `SHA256SUMS` | Checksums of the above. Every file also carries a GitHub build-provenance attestation (`gh attestation verify <file> --repo second-impressions/caesar2-port`). |

Version strings: a release build prints `1.0.0+<hash>` (semver build
metadata: the commit is still in every crash report); builds from `main`
print `1.1.0-<build>-<hash>`; a build from an edited tree prints its
configure time.

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

## Windows

The zip is the MSVC build CI has always made, plus the PDB. There is no
installer: the launcher imports the game data into `%APPDATA%`, so nothing
needs installing, and an installer would not change the SmartScreen warning
an unsigned executable gets. Signing needs a certificate; not planned.

## Not yet

- macOS (`.dmg`): planned; needs the platform leaf and a Mac to test on.
  Gatekeeper wants Developer ID signing and notarization for a
  warning-free install.
- A rolling `nightly` pre-release from `main`.
