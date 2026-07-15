#!/usr/bin/env bash
# Extract Windows PE binaries (game + patch/updater) from each Caesar II CD zip.
# Dedup by sha256, keep a manifest, clean up all intermediates immediately.
set -euo pipefail

REPO=/home/simon/git/caesar2
OUT=$REPO/data/windows-builds
STORE=$OUT/store
WORK=/tmp/c2winwork
MANIFEST=$OUT/manifest.tsv

mkdir -p "$STORE"
: > "$MANIFEST"
echo -e "cd\tpath\tsize\tmtime\tsha256" >> "$MANIFEST"

# case-insensitive grep patterns for windows-relevant PE binaries
PAT='C2WIN95/.*\.(EXE|DLL)$|Patch/C2WINPCH\.EXE$|INSTALL/WINUPD.*\.EXE$'

for zip in "$REPO"/CDs/*.zip; do
  base=$(basename "$zip" .zip)
  [[ "$base" == WATCOM_C10A ]] && continue
  echo "==== $base ===="
  rm -rf "$WORK"; mkdir -p "$WORK/ex"
  unzip -oq "$zip" -d "$WORK" || { echo "  unzip failed"; continue; }
  cue=$(ls "$WORK"/*.cue 2>/dev/null | head -1 || true)
  if [[ -z "$cue" ]]; then echo "  no cue, skipping"; continue; fi
  ( cd "$WORK" && bchunk -w "$(ls *.bin | head -1)" "$(basename "$cue")" trk_ >/dev/null 2>&1 || \
                 bchunk    "$(ls *.bin | head -1)" "$(basename "$cue")" trk_ >/dev/null 2>&1 ) || true
  iso=$(ls "$WORK"/trk_01.iso "$WORK"/trk_*.iso 2>/dev/null | head -1 || true)
  if [[ -z "$iso" ]]; then echo "  bchunk produced no iso"; rm -rf "$WORK"; continue; fi
  # list windows binaries
  mapfile -t files < <(7z l "$iso" 2>/dev/null | awk '{ $1=$1; for(i=6;i<=NF;i++) printf "%s%s",$i,(i<NF?" ":"\n") }' | grep -iE "$PAT" || true)
  if [[ ${#files[@]} -eq 0 ]]; then echo "  (no windows binaries on this CD)"; rm -rf "$WORK"; continue; fi
  for f in "${files[@]}"; do
    7z e -y -o"$WORK/ex" "$iso" "$f" >/dev/null 2>&1 || { echo "  extract failed: $f"; continue; }
    fn=$(basename "$f")
    src="$WORK/ex/$fn"
    [[ -f "$src" ]] || continue
    sha=$(sha256sum "$src" | cut -d' ' -f1)
    sz=$(stat -c%s "$src")
    mt=$(7z l "$iso" "$f" 2>/dev/null | grep -iE "$(echo "$f" | sed 's/[.[\*^$]/\\&/g')$" | head -1 | awk '{print $1" "$2}')
    echo -e "${base}\t${f}\t${sz}\t${mt}\t${sha}" >> "$MANIFEST"
    if [[ ! -f "$STORE/$sha" ]]; then
      cp "$src" "$STORE/$sha"
      echo "  + NEW $fn  $sz  $sha"
    else
      echo "    dup $fn  $sha"
    fi
    rm -f "$src"
  done
  rm -rf "$WORK"
done
echo "==== done ===="
