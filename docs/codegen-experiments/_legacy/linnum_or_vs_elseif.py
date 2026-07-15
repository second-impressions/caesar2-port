#!/usr/bin/env python3
"""Rule 131 oracle: || chain vs else-if chain -- LINNUM discriminates.

Both forms below compile to IDENTICAL control flow (je/je/jne into one
shared body -- ComTail merges the duplicated bodies), but the line table
differs: the multi-line `||` gets ONE entry for the whole condition,
the else-if chain gets an entry PER TERM (ascending lines, PS's
L+13/L+14/L+15 pattern in cd_path).

Run:
    python3 docs/codegen-experiments/linnum_or_vs_elseif.py
"""
import subprocess
import sys
sys.path.insert(0, "/home/simon/git/caesar2")

SRC = """extern int sc(char*,char*); extern char e[4]; int m;
void f(void){
    m = 1;
    if (sc("a",e)==0 ||
        sc("b",e)==0 ||
        sc("c",e)==0)
    {
        m = 0;
    }
}
void g(void){
    m = 1;
    if (sc("a",e)==0) m = 0;
    else if (sc("b",e)==0) m = 0;
    else if (sc("c",e)==0) m = 0;
}
"""


def linnums(path):
    data = open(path, "rb").read()
    i, out = 0, []
    while i + 3 <= len(data):
        typ = data[i]
        ln = data[i + 1] | (data[i + 2] << 8)
        if typ in (0x94, 0x95):
            body = data[i + 3:i + 3 + ln - 1]
            k = 2
            while k + 6 <= len(body):
                out.append((body[k] | (body[k + 1] << 8),
                            int.from_bytes(body[k + 2:k + 6], "little")))
                k += 6
        i += 3 + ln
    return out


def main():
    open("/tmp/lin.c", "w").write(SRC)
    subprocess.run(
        ["podman", "run", "--rm", "-v", "/tmp:/src",
         "localhost/watcom-10.0a-dosemu2",
         "wcc386 -bt=dos -mf -4r -s -d1 lin.c"],
        check=True, capture_output=True, timeout=300)
    pairs = linnums("/tmp/lin.obj")
    lines = [l for l, _ in pairs]
    # f: condition lines 4..6 -> ONLY line 4 present (one entry)
    assert 4 in lines and 5 not in lines and 6 not in lines, pairs
    # g: else-if terms lines 13,14,15 each present
    assert 13 in lines and 14 in lines and 15 in lines, pairs
    print("OK: || = one line entry; else-if chain = per-term entries")


if __name__ == "__main__":
    main()
