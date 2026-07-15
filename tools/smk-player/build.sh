#!/usr/bin/env bash
# Build the Smacker+AIL playback test for the delinked RAD Smacker / Miles AIL
# OMF object.  End-to-end proof that `c2 delink` produces *working* objects:
# this links the delinked audio/video stack into a DOS/4GW program that decodes
# real .SMK videos WITH SOUND.  See README.md.
#
# Usage:  tools/smk-player/build.sh  [outdir]
# Run:    podman run --rm -v <outdir>:/src localhost/watcom-10.0a-dosemu2 \
#             playps.exe MOVIE.SMK        # PPM dump (headless, silent)
#         (VGA + sound: run playps.exe MOVIE.SMK vga under dosbox-x, see README)
set -euo pipefail

REPO="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="${1:-/tmp/smktest}"
IMG=localhost/watcom-10.0a-wibo
mkdir -p "$OUT"
cd "$REPO"

# 1. Delink the FULL audio/video stack (Smacker + Miles AIL + RAD file I/O)
#    in ONE analysis set (they interoperate and share scratch data --
#    unsmack's `simspeed` region overlays qread's buffer; see
#    docs/delinking.md), split per original module and packed into the
#    RECONSTRUCTED vendor archives ail.lib + smack.lib.  This player links
#    against them like any 1995 program linked against the real SDKs.
uv run c2 delink --group av --split --libs -o "$OUT/av" --verify

# 2. Compile the player + support C (radmalloc/radfree + one game stub).
cp "$REPO/tools/smk-player/"{player.c,radmem.c,gamestub.c,smacker.h} "$OUT/"
for c in player radmem gamestub; do
  podman run --rm -v "$OUT:/src" $IMG wcc386 -bt=dos -mf -4r -zq "$c.c"
done

# 3. Link an LE app (needs dos4gw.exe alongside).
cat > "$OUT/play.lnk" <<'EOF'
SYSTEM dos4g
NAME play.exe
OPTION QUIET, MAP=play.map
FILE player.obj
FILE radmem.obj
FILE gamestub.obj
LIBPATH Z:\opt\watcom\lib386;Z:\opt\watcom\lib386\dos
LIBRARY av\ail.lib
LIBRARY av\smack.lib
LIBRARY clib3r.lib
EOF
podman run --rm -v "$OUT:/src" $IMG wlink @play.lnk
echo "built $OUT/play.exe  (needs dos4gw.exe alongside)"

# 4. Make it self-contained THE WAY PS.EXE WAS MADE, but without the DOS/4GW
#    Professional bind tool.  Binding is a PURE PREFIX swap: 4GWBIND just
#    prepends the [MZ stub + VMM.EXP + 4GWPRO.EXP] extender image and leaves
#    the LE byte-for-byte untouched.  So we lift PS.EXE's OWN byte-exact
#    DOS/4GW Professional 1.97 stub and prepend it to our freshly-linked LE
#    -- no abandonware blob, no dosemu, and the stub is identical to the one
#    the shipped game boots with.
python3 - "$REPO/data/PS.EXE" "$OUT/play.exe" "$OUT/playps.exe" <<'PY'
import sys
ps = open(sys.argv[1], "rb").read()
le = open(sys.argv[2], "rb").read()
stub = ps[: ps.find(b"LE\x00\x00")]
open(sys.argv[3], "wb").write(stub + le[le.find(b"LE\x00\x00"):])
PY
echo "built $OUT/playps.exe  (PS.EXE-style: DOS/4GW bound, self-contained)"

# 5. Stage the Miles AIL digital sound driver + config (from the C2 demo) so
#    playps.exe ... vga has sound (SB16 under dosbox-x).
DEMO="$REPO/Demos/extracted/Caesar II Demo (1995-08-04)"
for f in DIG.INI SB16.DIG; do
  [ -f "$DEMO/$f" ] && cp "$DEMO/$f" "$OUT/" && echo "staged $f"
done

# 6. DOSBox-X config mirroring `c2 run` (how PS.EXE itself is launched): the
#    normal CPU core (the dyn recompiler can't run AIL's runtime-loaded DIG
#    driver code) and the SB16 + AIL v2 sound settings.
#    cycles=50000 (not c2 run's 10000): our standalone player does a full
#    mode-13h frame blit + palette load every frame, which 10000 cycles can't
#    finish before the next frame while the AIL sound timer ISR also eats the
#    budget -> visible tearing.  Raising cycles is safe for AIL timing: the
#    PIT (and thus AIL's timer) runs in REAL time in DOSBox regardless of the
#    cycle count, so audio stays paced; more cycles just lets the blit finish
#    inside the retrace window.  ${MOVIE:-REAL.SMK} plays in trace mode.
cat > "$OUT/smkplay.conf" <<EOF
[dosbox]
machine=svga_s3
[cpu]
core=normal
cputype=pentium
cycles=50000
[sblaster]
sbtype=sb16
sbbase=220
irq=7
dma=1
hdma=5
blaster environment variable=true
oplmode=opl3
dsp require interrupt acknowledge=false
dsp busy cycle rate=0
[dos]
hard drive data rate limit=0
[autoexec]
mount c $OUT
SET BLASTER=A220 I7 D1 H5 T6 P330
c:
playps.exe ${MOVIE:-REAL.SMK} trace
EOF
echo "wrote smkplay.conf (run: dosbox-x -conf $OUT/smkplay.conf)"
