#!/usr/bin/env bash
# Batch-compile every game TU with MSVC 4.0 /Od /Zp1 and report build status.
# Produces decomp/_objs/<tu>.obj for each TU that compiles cleanly.
# Successes/failures recorded to decomp/_objs/build.log.
set -u
cd "$(dirname "$0")/.."
OUT=decomp/_objs; mkdir -p "$OUT"; : > "$OUT/build.log"
ok=0; fail=0
for f in decomp/src/*.c; do
  bn=$(basename "$f" .c)
  log=$(podman run --rm -v "$PWD/decomp:/src" localhost/msvc-4.00-wibo \
    cl.exe /nologo /c /Od /Zp1 /I include /FIc2_funcs.h /D__pascal= /D__far= \
           /Fo_objs/${bn}.obj src/${bn}.c 2>&1)
  if [ -f "$OUT/${bn}.obj" ]; then
    ok=$((ok+1)); printf 'OK   %-14s %d B\n' "$bn" "$(stat -c%s "$OUT/${bn}.obj")"
    echo "OK $bn" >> "$OUT/build.log"
  else
    fail=$((fail+1)); first=$(printf '%s\n' "$log" | grep -E 'error|fatal' | head -1)
    printf 'FAIL %-14s %s\n' "$bn" "$first"
    echo "FAIL $bn :: $first" >> "$OUT/build.log"
  fi
done
echo
echo "summary: $ok built, $fail failed -> $OUT/"
