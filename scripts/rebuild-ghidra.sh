#!/usr/bin/env bash
# Rebuild the Ghidra project for PS.EXE from scratch, reproducibly.
#
# The database is a disposable, fully-reconstructable artifact: this script
# is the single source of truth for how it is built.  It
#   1. regenerates data/out/symbols.json from PS.EXE (Watcom -d1 debug info),
#   2. deletes the existing Ghidra project,
#   3. imports PS.EXE with the LE-Style DOS loader + the x86:LE:32:watcom
#      language (ghidra-lx-loader extension), and
#   4. runs ghidra_scripts/ImportCaesar2.java as the post-script, which
#      applies symbols, calling conventions, line numbers, the Program Tree,
#      and \u2014 crucially \u2014 normalizes every function body to its authoritative
#      debug-symbol span (see Step 5.5 in that script).
#
# Result: exactly one function per unique debug symbol (~2234), each with a
# contiguous body, NO spurious FUN_ fragments, correct folded-alias labels,
# tail-merge / shared-epilogue / stack-check functions all intact.
#
# Requires the extensions build of Ghidra on PATH as `ghidra-analyzeHeadless`
# (provides the LE loader + watcom language).  `devenv shell` sets this up.
#
# Usage:
#   scripts/rebuild-ghidra.sh                 # rebuild ./C2 (the default project)
#   scripts/rebuild-ghidra.sh /tmp/scratch T  # rebuild into <dir>/<name>
set -euo pipefail

cd "$(dirname "$0")/.."
REPO="$(pwd)"

PROJECT_DIR="${1:-$REPO}"
PROJECT_NAME="${2:-C2}"
EXE="$REPO/data/PS.EXE"
LOADER="LeLoader"
LANGUAGE="x86:LE:32:watcom"
CSPEC="watcom"

command -v ghidra-analyzeHeadless >/dev/null 2>&1 || {
    echo "error: ghidra-analyzeHeadless not on PATH (run inside 'devenv shell')" >&2
    exit 1
}
[ -f "$EXE" ] || { echo "error: $EXE not found" >&2; exit 1; }

echo "== 1/3  Regenerating data/out/symbols.json =="
uv run c2 export "$EXE" >/dev/null

echo "== 2/3  Removing old project $PROJECT_DIR/$PROJECT_NAME =="
# Stop any ghidra-cli bridge holding a lock on the project, then delete it.
ghidra-cli stop --project "$PROJECT_DIR/$PROJECT_NAME" >/dev/null 2>&1 || true
rm -rf "$PROJECT_DIR/$PROJECT_NAME.gpr" "$PROJECT_DIR/$PROJECT_NAME.rep" \
       "$PROJECT_DIR/$PROJECT_NAME.lock" "$PROJECT_DIR/$PROJECT_NAME.lock~"

echo "== 3/3  Importing + running ImportCaesar2.java =="
ghidra-analyzeHeadless "$PROJECT_DIR" "$PROJECT_NAME" \
    -import "$EXE" \
    -loader "$LOADER" \
    -processor "$LANGUAGE" \
    -cspec "$CSPEC" \
    -scriptPath "$REPO/ghidra_scripts" \
    -postScript ImportCaesar2.java

echo
echo "Done.  Project: $PROJECT_DIR/$PROJECT_NAME  (program PS.EXE)"
echo "Verify:  ghidra-cli function list --count --limit 20000 --project $PROJECT_DIR/$PROJECT_NAME --program PS.EXE"
