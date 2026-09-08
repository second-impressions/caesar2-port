#!/usr/bin/env bash
# Build the macOS app bundle and wrap it in a .dmg. Runs on a Mac (the
# release workflow's macos runner), from the repository root:
#
#   packaging/macos/make-dmg.sh [extra cmake args]
#
# Output: dist/caesar2-<version>-macos.dmg with a universal (arm64 +
# x86_64) "Caesar II.app", ad-hoc signed. Without a Developer ID and
# notarization, Gatekeeper asks the user to allow it in System Settings.
set -euo pipefail

BUILD_DIR=${BUILD_DIR:-build/port/macos}
DIST_DIR=${DIST_DIR:-dist}

cmake -S . -B "$BUILD_DIR" -G Ninja \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_OSX_ARCHITECTURES="arm64;x86_64" \
    -DCMAKE_OSX_DEPLOYMENT_TARGET=11.0 \
    -DPORT_VENDOR_DEPENDENCIES=ON \
    -DPORT_WITH_LIBBACKTRACE=ON \
    -DBUILD_TESTING=OFF \
    "$@"
cmake --build "$BUILD_DIR"

APP="$BUILD_DIR/Caesar II.app"
BIN="$APP/Contents/MacOS/Caesar II"
test -x "$BIN"
VERSION=$("$BIN" --version | sed 's/^Caesar II //')
echo "built caesar2 $VERSION"
lipo -info "$BIN"
# Only system libraries may be dynamic (dependency lines are indented; the
# others name the file and, in a fat binary, each architecture).
if otool -L "$BIN" | grep '^	' | grep -vE '/usr/lib/|/System/Library/'; then
    echo "unexpected dynamic dependency" >&2
    exit 1
fi

# caesar2.icns is generated from icon-1024.png (PNG payloads in the icp4,
# icp5 and ic07..ic10 slots) by tools/make-icons.py; committed so the build
# needs neither ImageMagick nor iconutil.
mkdir -p "$APP/Contents/Resources"
cp packaging/macos/caesar2.icns "$APP/Contents/Resources/caesar2.icns"
mkdir -p "$APP/Contents/Resources/licenses"
cp LICENSE third_party/README.md third_party/libsmacker/COPYING third_party/nuked-opl3/LICENSE \
    "$APP/Contents/Resources/licenses/"

# Ad hoc: required for arm64 binaries to launch at all.
codesign --force --deep --sign - "$APP"
codesign --verify --verbose "$APP"

STAGE="$BUILD_DIR/dmg"
rm -rf "$STAGE"; mkdir -p "$STAGE"
cp -R "$APP" "$STAGE/"
ln -s /Applications "$STAGE/Applications"
mkdir -p "$DIST_DIR"
OUT="$DIST_DIR/caesar2-$VERSION-macos.dmg"
rm -f "$OUT"
# The volume gets the helmet too: a writable image first, the icon copied
# in and the folder's custom-icon bit set, then compressed read-only.
RW="$BUILD_DIR/caesar2-rw.dmg"
rm -f "$RW"
hdiutil create -volname "Caesar II" -srcfolder "$STAGE" -ov -format UDRW "$RW"
MOUNT=$(hdiutil attach -readwrite -noverify -nobrowse "$RW" | awk -F'\t' '/\/Volumes\//{print $NF}')
cp packaging/macos/caesar2.icns "$MOUNT/.VolumeIcon.icns"
SetFile -c icnC "$MOUNT/.VolumeIcon.icns"
SetFile -a C "$MOUNT"
hdiutil detach "$MOUNT"
hdiutil convert "$RW" -format UDZO -o "$OUT"
rm -f "$RW"
ls -la "$OUT"
