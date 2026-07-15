"""Synthetic tests for the cross-corpus line-code index (line_corpus)."""
import sys
sys.path.insert(0, '.')

from c2.commands.line_corpus import (
    normalize_insn, is_useful_text, useful_suggestions,
    match_run, group_by_line, extract_line_runs,
    CorpusBuilder, MIN_RUN_BYTES, LineMatch,
)

# ── normalize_insn: relocations masked ───────────────────────────────────────
# mov eax, [0x87f28]  = A1 28 7F 08 00 ; the 4 address bytes are a fixup.
raw = bytes([0xA1, 0x28, 0x7F, 0x08, 0x00])
fix = {101, 102, 103, 104}      # code_off=100, bytes [1:5] relocated
n = normalize_insn(raw, 100, fix)
assert n == bytes([0xA1, 0, 0, 0, 0]), n.hex()
print("✓ normalize_insn masks relocation field")

# ── normalize_insn: branch displacements masked, no fixup needed ─────────────
assert normalize_insn(bytes([0xE8, 1, 2, 3, 4]), 0, set()) == bytes([0xE8, 0, 0, 0, 0])
assert normalize_insn(bytes([0x74, 0x05]), 0, set()) == bytes([0x74, 0x00])   # je rel8
assert normalize_insn(bytes([0xEB, 0x90]), 0, set()) == bytes([0xEB, 0x00])   # jmp rel8
assert normalize_insn(bytes([0x0F, 0x84, 1, 2, 3, 4]), 0, set()) == bytes([0x0F, 0x84, 0, 0, 0, 0])
print("✓ normalize_insn masks rel8/rel32 branch displacements")

# ── normalize_insn: real opcodes/regs/immediates KEPT ────────────────────────
addimm = bytes([0x83, 0xC0, 0x05])    # add eax, 5
assert normalize_insn(addimm, 0, set()) == addimm, "immediates must be kept"
print("✓ normalize_insn keeps opcodes/registers/immediates")

# ── is_useful_text: filter braces + function signatures ──────────────────────
assert not is_useful_text("}")
assert not is_useful_text("{")
assert not is_useful_text("int evacuate(unsigned char *src, unsigned char *dst)")
assert is_useful_text("kind = city_map[cm_sptr];")
assert is_useful_text("if (x > 0)")            # control kw -> kept
assert is_useful_text("return pmp_optr;")
assert is_useful_text("(void)stance;")       # leading '(' (cast) must not crash
assert is_useful_text("(")                   # degenerate fragment
print("✓ is_useful_text drops braces/signatures, keeps statements")

# ── group_by_line: inherited-line grouping ───────────────────────────────────
# insns at rel 0,2,5 ; lines: 0->10 (start), 2->none(inherit 10), 5->11
insns = [(0, b"\x90"), (2, b"\x91\x92"), (5, b"\xc3")]
lmap = {0: 10, 5: 11}     # base_off=0
groups = group_by_line(insns, 0, lmap)
assert [ln for ln, _ in groups] == [10, 11], groups
assert len(groups[0][1]) == 2 and len(groups[1][1]) == 1
print("✓ group_by_line inherits previous line for non-statement-start insns")

# ── match_run: dedup by whitespace, exclude self, rank by share count ────────
corpus = {
    "deadbeef0102": [
        {"func": "A", "file": "a.c", "line": 5, "text": "x = arr[i];", "nbytes": 6},
        {"func": "B", "file": "b.c", "line": 9, "text": "x = arr[i];", "nbytes": 6},
        {"func": "C", "file": "c.c", "line": 3, "text": "x = arr[i] ;", "nbytes": 6},  # ws variant
        {"func": "self", "file": "s.c", "line": 1, "text": "x = arr[i];", "nbytes": 6},
    ],
}
m = match_run("deadbeef0102", 6, corpus, self_func="self")
assert m is not None
assert m.n_functions == 3, m.n_functions                 # A,B,C (self excluded)
assert len(m.suggestions) == 1, m.suggestions            # ws variant deduped
assert m.suggestions[0]["count"] == 3
print("✓ match_run excludes self, dedupes whitespace variants, counts shares")

assert match_run("nope", 6, corpus) is None
print("✓ match_run returns None on miss")

# ── CorpusBuilder + extract_line_runs end-to-end ─────────────────────────────
# Two instructions on line 5 of a tiny source; build an index entry.
import tempfile, pathlib
with tempfile.TemporaryDirectory() as d:
    src = pathlib.Path(d) / "x.c"
    src.write_text("l1\nl2\nl3\nl4\ntotal = a + b;\n")  # line 5
    insns = [(0, bytes([0x01, 0xD8])), (2, bytes([0xA3, 1, 2, 3, 4]))]  # add; mov [reloc]
    rc_base = 0
    fixset = {2 + 1, 2 + 2, 2 + 3, 2 + 4}   # second insn's addr field
    line_map = {0: 5}
    runs = extract_line_runs(insns, rc_base, fixset, line_map, src)
    assert len(runs) == 1, runs
    assert runs[0].line == 5 and runs[0].text == "total = a + b;"
    # normalized: 01 d8  a3 00 00 00 00
    assert runs[0].norm_hex == "01d8a300000000", runs[0].norm_hex
    b = CorpusBuilder()
    b.add_function("addfn", "x.c", runs)
    assert b.n_runs == 1 and runs[0].norm_hex in b.index
print("✓ extract_line_runs + CorpusBuilder map source line -> normalized code")

# Runs shorter than MIN_RUN_BYTES are dropped.
assert MIN_RUN_BYTES >= 4
short = extract_line_runs([(0, b"\x90")], 0, set(), {0: 5},
                          pathlib.Path("/nonexistent"))
assert short == []
print("✓ extract_line_runs drops sub-threshold / textless runs")

# ── CorpusBuilder.save(merge_processed=...): partial pass merges ─────────────
# Existing on-disk index: A@line5 (h1) and C@line9 (h2).  A partial pass that
# re-ran functions {A, B} must refresh A, add B, and PRESERVE C.
with tempfile.TemporaryDirectory() as d:
    p = pathlib.Path(d) / "corpus.json"
    import json as _json
    p.write_text(_json.dumps({
        "version": 1, "n_functions": 2, "n_runs": 2, "min_run_bytes": 5,
        "index": {
            "h1": [{"func": "A", "file": "a.c", "line": 5, "text": "old A",
                    "nbytes": 6}],
            "h2": [{"func": "C", "file": "c.c", "line": 9, "text": "keep C",
                    "nbytes": 6}],
        }}))
    b2 = CorpusBuilder()
    b2.index = {
        "h1": [{"func": "A", "file": "a.c", "line": 7, "text": "new A",
                "nbytes": 6}],
        "h3": [{"func": "B", "file": "b.c", "line": 3, "text": "new B",
                "nbytes": 6}],
    }
    b2.save(p, merge_processed={"A", "B"})
    out = _json.loads(p.read_text())["index"]
    # C preserved untouched
    assert out["h2"] == [{"func": "C", "file": "c.c", "line": 9,
                          "text": "keep C", "nbytes": 6}], out.get("h2")
    # A refreshed (old line-5 entry gone, new line-7 entry present)
    assert out["h1"] == [{"func": "A", "file": "a.c", "line": 7,
                          "text": "new A", "nbytes": 6}], out.get("h1")
    # B added
    assert out["h3"][0]["func"] == "B"
print("✓ CorpusBuilder.save(merge_processed) refreshes visited fns, keeps rest")

# A visited function that is no longer byte-exact (absent from the new build)
# is DROPPED on merge.
with tempfile.TemporaryDirectory() as d:
    p = pathlib.Path(d) / "corpus.json"
    import json as _json
    p.write_text(_json.dumps({
        "version": 1, "index": {
            "h1": [{"func": "A", "file": "a.c", "line": 5, "text": "A",
                    "nbytes": 6}],
            "h2": [{"func": "C", "file": "c.c", "line": 9, "text": "C",
                    "nbytes": 6}],
        }}))
    b3 = CorpusBuilder()          # A re-run but produced NO runs (now diffing)
    b3.save(p, merge_processed={"A"})
    out = _json.loads(p.read_text())["index"]
    assert "h1" not in out and out["h2"][0]["func"] == "C"
print("✓ merge drops a visited function that stopped being byte-exact")

print("\nALL line_corpus TESTS PASS")
