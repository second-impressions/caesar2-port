#!/usr/bin/env bash
# Turn the build artifacts of one CI run into a public downloads directory
# for the Pages site, beside the web build of the same commit.
#
#   assemble-downloads.sh <artifact-dir> <out-dir> <build-label> <git-hash>
#
# artifact-dir holds one subdirectory per artifact as actions/download-artifact
# writes them (caesar2-<label>-linux-x64-package, -windows-x64, -macos-arm64).
# Actions artifacts can only be fetched by someone signed in to GitHub with
# access to the repository; the Pages site can be fetched by anyone.
set -euo pipefail
artifacts=$(cd "$1" && pwd)
out=$2
label=$3
hash=$4
short=${hash:0:7}
stamp="${label}-${short}"

mkdir -p "$out"

# Linux: the staged install tree, as a tarball that keeps modes.
if [ -d "$artifacts/caesar2-${label}-linux-x64-package" ]; then
    tar -C "$artifacts/caesar2-${label}-linux-x64-package" -czf \
        "$out/caesar2-${stamp}-linux-x64.tar.gz" .
fi
# Windows: the staged bin/ directory and the symbol file.
if [ -d "$artifacts/caesar2-${label}-windows-x64" ]; then
    (cd "$artifacts/caesar2-${label}-windows-x64" && zip -qr "$OLDPWD/$out/caesar2-${stamp}-windows-x64.zip" .)
fi
# macOS: already a zip that keeps the bundle's executable bit.
if [ -f "$artifacts/caesar2-${label}-macos-arm64/caesar2-macos-arm64.zip" ]; then
    cp "$artifacts/caesar2-${label}-macos-arm64/caesar2-macos-arm64.zip" "$out/caesar2-${stamp}-macos-arm64.zip"
fi

# A plain index: name, size, checksum. Pages does not list directories.
(
    cd "$out"
    sha256sum caesar2-* > SHA256SUMS
    {
        printf '<!doctype html>\n<meta charset="utf-8">\n<title>Caesar II port %s: downloads</title>\n' "$stamp"
        printf '<style>body{font:15px/1.5 system-ui,sans-serif;max-width:48rem;margin:3rem auto;padding:0 1rem}td{padding:.2rem 1rem .2rem 0}code{font-size:.9em}</style>\n'
        printf '<h1>Caesar II port &mdash; build %s</h1>\n' "$stamp"
        printf '<p>Unsigned development builds of commit <code>%s</code>. The game data is not included; the game asks for it on first start. <a href="../">Run this build in the browser</a> instead.</p>\n' "$hash"
        printf '<table>\n'
        for f in caesar2-*; do
            size=$(du -h "$f" | cut -f1)
            printf '<tr><td><a href="%s">%s</a></td><td>%s</td></tr>\n' "$f" "$f" "$size"
        done
        printf '<tr><td><a href="SHA256SUMS">SHA256SUMS</a></td><td></td></tr>\n'
        printf '</table>\n'
    } > index.html
)
ls -l "$out"
