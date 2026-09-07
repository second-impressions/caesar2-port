#!/usr/bin/env bash
# Build the portable Linux binary and wrap it as an AppImage.
#
# Runs inside an Ubuntu 22.04 container (the oldest glibc the AppImage
# supports is the one it is built against), from the repository root:
#
#   docker run --rm -v "$PWD:/src" -w /src ubuntu:22.04 packaging/appimage/build.sh [extra cmake args]
#
# Output: dist/caesar2-<version>-x86_64.AppImage
set -euo pipefail

BUILD_DIR=${BUILD_DIR:-build/port/linux-appimage}
DIST_DIR=${DIST_DIR:-dist}
ARCH=$(uname -m)

export DEBIAN_FRONTEND=noninteractive
if ! command -v ninja >/dev/null 2>&1 || ! command -v pip3 >/dev/null 2>&1; then
    apt-get update
    # SDL3 loads all of these with dlopen at run time; only their headers
    # are needed here so that every backend gets compiled in.
    apt-get install -y --no-install-recommends \
        build-essential git ca-certificates curl file pkg-config python3-pip \
        zlib1g-dev \
        libx11-dev libxext-dev libxrandr-dev libxcursor-dev libxi-dev libxfixes-dev \
        libxss-dev libxtst-dev libxkbcommon-dev libwayland-dev wayland-protocols libdecor-0-dev \
        libegl1-mesa-dev libgl-dev libgles2-mesa-dev libdrm-dev libgbm-dev \
        libasound2-dev libpulse-dev libpipewire-0.3-dev libsndio-dev \
        libdbus-1-dev libibus-1.0-dev libudev-dev libusb-1.0-0-dev \
        desktop-file-utils
    pip3 install --no-cache-dir "cmake>=3.25,<4" ninja
fi

git config --global --add safe.directory "$PWD" || true

cmake -S . -B "$BUILD_DIR" -G Ninja \
    -DCMAKE_BUILD_TYPE=Release \
    -DPORT_VENDOR_DEPENDENCIES=ON \
    -DPORT_WITH_LIBBACKTRACE=ON \
    -DBUILD_TESTING=OFF \
    "$@"
cmake --build "$BUILD_DIR"

VERSION=$("$BUILD_DIR/caesar2" --version | sed 's/^Caesar II //; s/+.*//')
echo "built caesar2 $VERSION"
# Only the C library may be dynamic.
if ldd "$BUILD_DIR/caesar2" | grep -vE 'linux-vdso|libc\.so|libm\.so|libdl\.so|libpthread\.so|librt\.so|ld-linux|libgcc_s'; then
    echo "unexpected dynamic dependency" >&2
    exit 1
fi

APPDIR="$BUILD_DIR/AppDir"
rm -rf "$APPDIR"
DESTDIR="$APPDIR" cmake --install "$BUILD_DIR" --prefix /usr
ID=io.github.second_impressions.caesar2
ln -sf usr/bin/caesar2 "$APPDIR/AppRun"
cp "$APPDIR/usr/share/applications/$ID.desktop" "$APPDIR/"
cp "$APPDIR/usr/share/icons/hicolor/scalable/apps/$ID.svg" "$APPDIR/"
ln -sf "$ID.svg" "$APPDIR/.DirIcon"
desktop-file-validate "$APPDIR/$ID.desktop"

TOOLS="$BUILD_DIR/tools"
mkdir -p "$TOOLS"
# appimagetool itself is an AppImage; without FUSE in a container it runs
# extracted. The static runtime (type2-runtime) needs no FUSE on the user's
# machine either.
[ -x "$TOOLS/appimagetool" ] || {
    curl -sSL -o "$TOOLS/appimagetool" \
        "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-$ARCH.AppImage"
    chmod +x "$TOOLS/appimagetool"
}
[ -f "$TOOLS/runtime" ] || curl -sSL -o "$TOOLS/runtime" \
    "https://github.com/AppImage/type2-runtime/releases/download/continuous/runtime-$ARCH"

mkdir -p "$DIST_DIR"
OUT="$DIST_DIR/caesar2-$VERSION-$ARCH.AppImage"
APPIMAGE_EXTRACT_AND_RUN=1 ARCH="$ARCH" "$TOOLS/appimagetool" \
    --runtime-file "$TOOLS/runtime" --no-appstream "$APPDIR" "$OUT"
ls -la "$OUT"
