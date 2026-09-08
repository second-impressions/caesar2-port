#!/usr/bin/env python3
"""Write every raster icon from packaging/macos/icon-1024.png (the helmet of
web/favicon.svg, rendered at 1024):

  packaging/macos/caesar2.icns     the app bundle's icon (and the dmg's)
  packaging/windows/caesar2.ico    the executable's icon, from caesar2.rc
  packaging/icon/caesar2-256.png   the window icon compiled into the binary,
                                   the hicolor 256x256 icon, the AppImage's

An .icns is a container; macOS 10.7 and later read PNG payloads in the
icp4 (16), icp5 (32), ic07 (128), ic08 (256), ic09 (512) and ic10 (1024)
slots. An .ico is a container too; Windows Vista and later read PNG
payloads at every size. Both are committed so the build needs neither
ImageMagick (`magick`, which this needs to resize) nor iconutil.
"""
import struct
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "packaging" / "macos" / "icon-1024.png"
ICNS = ROOT / "packaging" / "macos" / "caesar2.icns"
ICO = ROOT / "packaging" / "windows" / "caesar2.ico"
PNG256 = ROOT / "packaging" / "icon" / "caesar2-256.png"
ICNS_SLOTS = {16: b"icp4", 32: b"icp5", 128: b"ic07", 256: b"ic08", 512: b"ic09", 1024: b"ic10"}
ICO_SIZES = [16, 24, 32, 48, 64, 128, 256]


def resized(size):
    return subprocess.run(
        ["magick", str(SOURCE), "-resize", f"{size}x{size}", "-strip", "PNG32:-"],
        check=True, capture_output=True).stdout


def write_icns(pngs):
    entries = b""
    for size, slot in ICNS_SLOTS.items():
        entries += slot + struct.pack(">I", 8 + len(pngs[size])) + pngs[size]
    ICNS.write_bytes(b"icns" + struct.pack(">I", 8 + len(entries)) + entries)


def write_ico(pngs):
    header = struct.pack("<HHH", 0, 1, len(ICO_SIZES))
    offset = len(header) + 16 * len(ICO_SIZES)
    directory = b""
    payload = b""
    for size in ICO_SIZES:
        png = pngs[size]
        directory += struct.pack("<BBBBHHII", size % 256, size % 256, 0, 0, 1, 32,
                                 len(png), offset + len(payload))
        payload += png
    ICO.write_bytes(header + directory + payload)


def main():
    pngs = {size: resized(size) for size in sorted(set(ICNS_SLOTS) | set(ICO_SIZES))}
    write_icns(pngs)
    write_ico(pngs)
    PNG256.write_bytes(pngs[256])
    for path in (ICNS, ICO, PNG256):
        print(f"{path.relative_to(ROOT)}: {path.stat().st_size} bytes")


if __name__ == "__main__":
    main()
