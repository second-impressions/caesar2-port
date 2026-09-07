#!/usr/bin/env python3
"""Write packaging/macos/caesar2.icns from packaging/macos/icon-1024.png.

An .icns is a container; macOS 10.7 and later read PNG payloads in the
icp4 (16), icp5 (32), ic07 (128), ic08 (256), ic09 (512) and ic10 (1024)
slots, which is all this writes. Needs ImageMagick's `magick` to resize.
"""
import struct
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "packaging" / "macos" / "icon-1024.png"
TARGET = ROOT / "packaging" / "macos" / "caesar2.icns"
SLOTS = {16: b"icp4", 32: b"icp5", 128: b"ic07", 256: b"ic08", 512: b"ic09", 1024: b"ic10"}


def main():
    entries = b""
    for size, slot in SLOTS.items():
        png = subprocess.run(
            ["magick", str(SOURCE), "-resize", f"{size}x{size}", "-strip", "PNG32:-"],
            check=True, capture_output=True).stdout
        entries += slot + struct.pack(">I", 8 + len(png)) + png
    TARGET.write_bytes(b"icns" + struct.pack(">I", 8 + len(entries)) + entries)
    print(f"{TARGET}: {TARGET.stat().st_size} bytes")


if __name__ == "__main__":
    main()
