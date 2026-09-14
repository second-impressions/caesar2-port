#!/usr/bin/env sh
# Regenerate the FlatBuffers accessors for the save format from the schema.
# Needs the flatcc compiler (nixpkgs: flatcc; the runtime is bundled under
# third_party/flatcc). The output is checked in so ordinary builds need no
# flatcc; tests/test_save_schema.py checks it is current.
set -eu
root=$(cd "$(dirname "$0")/.." && pwd)
out="$root/src/platform/common/c2_save_gen"
flatcc=${FLATCC:-flatcc}
"$flatcc" --version >/dev/null
mkdir -p "$out"
"$flatcc" -a -o "$out" "$root/src/platform/common/c2_save.fbs"
echo "regenerated $out from c2_save.fbs"
