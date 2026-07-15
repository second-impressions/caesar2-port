#!/usr/bin/env python3
"""Byte-space map of original vs rebuilt PS.EXE.

Reuses ``c2 rebuild``'s per-symbol comparison (``_compare_vs_original``,
which now tags every code/data entry with a ``status`` of exact / diff /
tail / missing) and renders the two code objects side by side, colored by
comparison bucket, with the diffing functions flagged in red and labelled.

Run ``c2 rebuild`` first (or pass --rebuild) so ``.c2-cache/rebuild/
psle.exe`` and ``ps.map`` are fresh, then::

    uv run python docs/codegen-experiments/rebuild-byte-space-map.py

Output: docs/rebuild-byte-space-<DATE>.png (PIL; no matplotlib needed).
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from c2.commands.rebuild import (
    _REBUILD_DIR, _compare_vs_original, _bucket_of,
)

ROOT = Path(__file__).resolve().parents[2]

# bucket -> fill colour (matches the 2026-07-10 snapshot legend)
BUCKET_RGB = {
    "game":     (46, 116, 210),    # blue   -- recovered C
    "c2-asm":   (150, 90, 190),    # purple -- hand-written asm modules
    "av-delink": (46, 160, 86),    # green  -- Smacker+AIL+RAD I/O
    "crt":      (222, 150, 40),    # orange -- Watcom clib3r.lib
}
DIFF_RGB = (208, 40, 40)           # red    -- in-flight decomp diff
TAIL_RGB = (232, 190, 40)          # yellow -- ~tail artefact
GAP_RGB  = (220, 220, 220)         # grey   -- gap / unnamed

LEGEND = [
    ("game (recovered C)", BUCKET_RGB["game"]),
    ("C2 asm modules", BUCKET_RGB["c2-asm"]),
    ("AV delinked (Smacker+AIL+RAD I/O)", BUCKET_RGB["av-delink"]),
    ("Watcom CRT (clib3r.lib)", BUCKET_RGB["crt"]),
    ("byte DIFF (in-flight decomp work)", DIFF_RGB),
    ("~tail artefact", TAIL_RGB),
    ("gap / unnamed", GAP_RGB),
]


def _font(sz: int):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
              "/usr/share/fonts/dejavu/DejaVuSans.ttf",
              "/nix/store"):
        try:
            return ImageFont.truetype(p, sz)
        except Exception:
            continue
    try:
        import glob
        for cand in glob.glob("/nix/store/*dejavu*/**/DejaVuSans.ttf",
                              recursive=True):
            return ImageFont.truetype(cand, sz)
    except Exception:
        pass
    return ImageFont.load_default()


def build(rebuild_first: bool) -> Path:
    if rebuild_first:
        subprocess.run(["uv", "run", "c2", "rebuild"], cwd=ROOT, check=True)

    symbols_json = ROOT / "data/out/symbols.json"
    exe_path = ROOT / "data/PS.EXE"
    d = json.load(open(symbols_json))
    mods = d["modules"]

    res = _compare_vs_original(_REBUILD_DIR, symbols_json, exe_path,
                               verbose=False)
    entries = res["entries"]
    sizes = res["sizes"]
    o_code, r_code = sizes["o_code"], sizes["r_code"]

    # rebuild spans: distance to the next placed rc offset
    placed = sorted(e["rc"] for e in entries if e["rc"] is not None)
    import bisect

    def rspan(rc: int) -> int:
        i = bisect.bisect_right(placed, rc)
        return (placed[i] if i < len(placed) else r_code) - rc

    # ── canvas ────────────────────────────────────────────────────────
    W, H = 1700, 2610
    im = Image.new("RGB", (W, H), "white")
    dr = ImageDraw.Draw(im)
    f_title = _font(26)
    f_hdr = _font(19)
    f_lbl = _font(15)
    f_small = _font(14)

    col_w = 120
    top = 90
    bot = H - 190
    span_px = bot - top
    x_ps = 300
    x_rc = 800

    def y_of(off: int, total: int) -> float:
        return top + span_px * off / total

    # column backgrounds (gap grey)
    for x in (x_ps, x_rc):
        dr.rectangle([x, top, x + col_w, bot], fill=GAP_RGB)

    # draw each entry as a band in both columns
    diff_rows = []          # (name, rc_y_center, bucket)
    for e in entries:
        b = e["bucket"]
        base = BUCKET_RGB.get(b, GAP_RGB)
        st = e.get("status", "exact")
        col = {"diff": DIFF_RGB, "tail": TAIL_RGB}.get(st, base)
        # PS column
        y0 = y_of(e["off"], o_code)
        y1 = y_of(e["off"] + e["span"], o_code)
        dr.rectangle([x_ps, y0, x_ps + col_w, max(y1, y0 + 0.4)], fill=col)
        # rebuild column
        if e["rc"] is not None:
            r0 = y_of(e["rc"], r_code)
            r1 = y_of(e["rc"] + rspan(e["rc"]), r_code)
            dr.rectangle([x_rc, r0, x_rc + col_w, max(r1, r0 + 0.4)], fill=col)
            if st == "diff":
                diff_rows.append((e["name"], (r0 + r1) / 2, e["diff_bytes"]))

    # ── TU labels down the left edge (module boundaries in game area) ──
    seen_mod = set()
    for e in entries:
        m = e["mod"]
        if m in seen_mod:
            continue
        seen_mod.add(m)
        name = (mods[m].get("name") or "").split("\\")[-1]
        if not name:
            continue
        y = y_of(e["off"], o_code)
        bkt = _bucket_of(mods[m].get("name") or "")
        # only label a representative subset to avoid clutter
        color = (60, 90, 170) if bkt == "game" else (
            (40, 130, 70) if bkt == "av-delink" else (120, 120, 120))
        if bkt in ("game", "av-delink"):
            dr.text((x_ps - 12 - dr.textlength(name, font=f_lbl), y - 7),
                    name, fill=color, font=f_lbl)
            dr.line([x_ps - 8, y, x_ps, y], fill=color, width=1)

    # ── diff labels down the right edge ───────────────────────────────
    used_y = []
    for name, yc, nb in sorted(diff_rows, key=lambda t: t[1]):
        y = yc
        while any(abs(y - u) < 18 for u in used_y):
            y += 18
        used_y.append(y)
        dr.line([x_rc + col_w, yc, x_rc + col_w + 40, y], fill=DIFF_RGB, width=1)
        dr.text((x_rc + col_w + 46, y - 8), f"{name}", fill=DIFF_RGB,
                font=f_lbl)

    # ── axis ticks (bytes) on both columns ────────────────────────────
    for kb in range(0, (o_code // 1024) + 1, 64):
        off = kb * 1024
        y = y_of(off, o_code)
        dr.line([x_ps - 4, y, x_ps, y], fill="black", width=1)
        dr.text((x_ps - 60, y - 8), f"{kb}K", fill="black", font=f_small)
    for kb in range(0, (r_code // 1024) + 1, 64):
        y = y_of(kb * 1024, r_code)
        dr.line([x_rc + col_w, y, x_rc + col_w + 4, y], fill="black", width=1)
        dr.text((x_rc + col_w + 8, y - 8), f"{kb}K", fill="black",
                font=f_small)

    # ── headers ───────────────────────────────────────────────────────
    dr.text((W / 2, 24), "Caesar II \u2014 original vs rebuilt PS.EXE byte "
            "space", fill="black", font=f_title, anchor="mm")
    dr.text((x_ps + col_w / 2, 58), "PS.EXE (original)", fill="black",
            font=f_hdr, anchor="mm")
    dr.text((x_ps + col_w / 2, 78), f"code {o_code:,} b", fill=(90, 90, 90),
            font=f_small, anchor="mm")
    dr.text((x_rc + col_w / 2, 58), "build/PS.EXE (rebuild)", fill="black",
            font=f_hdr, anchor="mm")
    dr.text((x_rc + col_w / 2, 78), f"code {r_code:,} b", fill=(90, 90, 90),
            font=f_small, anchor="mm")

    # ── summary + legend ──────────────────────────────────────────────
    cst = res["code"]
    tot_exact = sum(s["exact"] for s in cst.values())
    tot_diff = sum(s["diff"] for s in cst.values())
    tot_tail = sum(s.get("tail", 0) for s in cst.values())
    tot_miss = sum(s["missing"] for s in cst.values())
    dstat = res["data"]
    summary = (f"functions: {tot_exact} exact \u00b7 {tot_diff} diff \u00b7 "
               f"{tot_tail} ~tail \u00b7 {tot_miss} unmatched    |    "
               f"data: {dstat['exact']}/{dstat['exact']+dstat['diff']+dstat['missing']} "
               f"exact")
    dr.text((60, H - 130), summary, fill="black", font=f_hdr)

    lx = 60
    ly = H - 90
    for label, rgb in LEGEND:
        dr.rectangle([lx, ly, lx + 18, ly + 18], fill=rgb)
        dr.text((lx + 24, ly + 1), label, fill="black", font=f_lbl)
        lx += 34 + int(dr.textlength(label, font=f_lbl)) + 30

    date = _dt.date.today().isoformat()
    out = ROOT / f"docs/rebuild-byte-space-{date}.png"
    im.save(out)
    return out, res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--rebuild", action="store_true",
                    help="run `c2 rebuild` first to refresh psle.exe/ps.map")
    args = ap.parse_args()
    out, res = build(args.rebuild)
    print("wrote", out)
