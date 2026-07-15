#!/usr/bin/env python3
"""Validate Caesar II *.SAV files against the recovered savegame format.

Parses the 500-entry savegame_entries[] block table out of
decomp/src/datainit.c to build the offset map, then reads each save's key
fields directly and checks internal consistency.  Pure stdlib.

    python3 validate_savegame.py path/to/save.SAV
    python3 validate_savegame.py path/to/dir/      # all *.sav in dir
"""
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATAINIT = os.path.join(HERE, "..", "..", "decomp", "src", "datainit.c")

STATE_BYTES = 221745
HISTORY_BYTES = 4000
TOTAL = STATE_BYTES + HISTORY_BYTES  # 225745


def build_offmap(datainit_path=DATAINIT):
    """Return {name: (offset, size)} from savegame_entries[500] in table order."""
    lines = open(datainit_path).read().splitlines()
    start = next(i for i, l in enumerate(lines) if "savegame_entries[500]" in l)
    off, seen, offmap = 0, {}, {}
    for l in lines[start + 1:]:
        if l.strip().startswith("};"):
            break
        m = re.match(r"\s*\{ (.*), (\d+) \},?", l)
        if not m:
            continue
        raw, size = m.group(1).strip(), int(m.group(2))
        name = re.sub(r"^&", "", raw)
        cast = re.match(r"\(char \*\)&c2inf \+ (\d+)", raw)
        if cast:
            name = f"c2inf_byte{cast.group(1)}"
        if "dummy_sav" in name:
            name = "reserved_expansion"
        if name in seen:
            seen[name] += 1
            name = f"{name}_{seen[name]}"
        else:
            seen[name] = 1
        offmap[name] = (off, size)
        off += size
    assert off == STATE_BYTES, f"table sums to {off}, expected {STATE_BYTES}"
    return offmap


def scalar(data, offmap, name):
    o, s = offmap[name]
    return struct.unpack_from("<i" if s == 4 else "<b", data, o)[0]


def validate(path, offmap):
    data = open(path, "rb").read()
    name = os.path.basename(path)
    problems = []
    if len(data) != TOTAL:
        problems.append(f"size {len(data)} != {TOTAL}")

    year = scalar(data, offmap, "year")
    den = scalar(data, offmap, "denarii")
    tyd = scalar(data, offmap, "this_years_denarii")
    pop = scalar(data, offmap, "population")
    pt = scalar(data, offmap, "pop_tax_rate")
    it = scalar(data, offmap, "ind_tax_rate")
    he = scalar(data, offmap, "history_entries")
    ep = scalar(data, offmap, "history_end_ptr")

    if not 0 <= pt <= 100:
        problems.append(f"pop_tax_rate {pt} out of 0..100")
    if not 0 <= it <= 100:
        problems.append(f"ind_tax_rate {it} out of 0..100")
    if not 0 <= he <= 200:
        problems.append(f"history_entries {he} out of 0..200")
    if not 0 <= ep <= 200:
        problems.append(f"history_end_ptr {ep} out of 0..200")

    # history ring: newest row's pop/year should match the live fields
    tail = data[STATE_BYTES:]
    if he > 0:
        newest = (ep - 1) % 200
        h_pop, h_den, h_pt, h_it, h_year = struct.unpack_from("<5i", tail, newest * 20)
        if h_pop != pop:
            problems.append(f"newest history pop {h_pop} != live population {pop}")
        if h_year != year:
            problems.append(f"newest history year {h_year} != live year {year}")
    hrows = sum(1 for i in range(200) if any(struct.unpack_from("<5i", tail, i * 20)))

    status = "OK " if not problems else "FAIL"
    print(f"[{status}] {name:14s} size={len(data)} year={year:5d} "
          f"denarii={den:7d} pop={pop:6d} tax={pt}/{it} hist={hrows}/{he}")
    for p in problems:
        print(f"         - {p}")
    return not problems


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    offmap = build_offmap()
    target = argv[1]
    if os.path.isdir(target):
        paths = sorted(os.path.join(target, f) for f in os.listdir(target)
                       if f.lower().endswith(".sav"))
    else:
        paths = [target]
    ok = sum(validate(p, offmap) for p in paths)
    print(f"\n{ok}/{len(paths)} files passed")
    return 0 if ok == len(paths) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
