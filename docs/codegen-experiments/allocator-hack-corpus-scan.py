"""Corpus scan for the "allocator-only source hack" class removed from
action.c build_city_item in commit 3a084b6e ("action: remove allocator-only
source hacks").  See docs/allocator-hack-cleanup-candidates.md for the
motivation, the killed-pattern taxonomy, and the curated candidate list.

Run:  uv run python docs/codegen-experiments/allocator-hack-corpus-scan.py


We keep only NON-IDIOMATIC forms (things a human would never write) and
drop legitimate C: for-loop comma clauses, multi-zero init chains,
ABI-unused-parameter void casts, idiomatic while((c=getc())!=EOF).
"""
import glob, os
import tree_sitter, tree_sitter_c

lang = tree_sitter.Language(tree_sitter_c.language())
parser = tree_sitter.Parser(lang)
files = sorted(glob.glob("decomp/src/*.c"))
SRC, TREE = {}, {}
for f in files:
    b = open(f, "rb").read()
    SRC[f], TREE[f] = b, parser.parse(b)


def walk(node):
    st = [node]
    while st:
        n = st.pop(); yield n; st.extend(reversed(n.children))


def txt(f, n):
    return SRC[f][n.start_byte:n.end_byte].decode("utf8", "replace")


def line(n):
    return n.start_point[0] + 1


def norm(s):
    return "".join(s.split())


def func_of(node):
    cur = node
    while cur is not None:
        if cur.type == "function_definition":
            d = cur.child_by_field_name("declarator")
            for n in (walk(d) if d else []):
                if n.type == "identifier":
                    return n.text.decode()
        cur = cur.parent
    return "?"


def in_for_clause(node):
    """True if node sits in the init/update (not body) of a for-loop."""
    cur = node
    while cur is not None:
        p = cur.parent
        if p is not None and p.type == "for_statement":
            body = p.child_by_field_name("body")
            # body subtree? then it's real code, not a clause
            if body is not None and body.start_byte <= node.start_byte < body.end_byte:
                return False
            return True
        cur = p
    return False


def assign_ops(node):
    """list of assignment_expression descendants (any depth)."""
    return [n for n in walk(node) if n.type == "assignment_expression"]


# ---------- S1: duplicated-store comma carrier ----------
# comma_expression whose two operands are BYTE-IDENTICAL assignments,
# or where an operand is a self-assign (x = x).  Pure rover +1 carriers.
s1 = []
for f in files:
    for n in walk(TREE[f].root_node):
        if n.type != "comma_expression":
            continue
        l = n.child_by_field_name("left")
        r = n.child_by_field_name("right")
        if l is None or r is None:
            continue
        flat = [c for c in walk(n) if c.type == "assignment_expression"]
        # self-assign operand
        selfassign = False
        for a in flat:
            al = a.child_by_field_name("left"); ar = a.child_by_field_name("right")
            op = a.child_by_field_name("operator")
            if al and ar and op and op.text == b"=" and norm(txt(f, al)) == norm(txt(f, ar)):
                selfassign = True
        # duplicated identical assignment operands directly under the comma
        dup = norm(txt(f, l)) == norm(txt(f, r)) and l.type == "assignment_expression"
        if selfassign or dup:
            s1.append((f, line(n), func_of(n), txt(f, n)))

# ---------- S2: standalone self-assign statement  x = x; ----------
s2 = []
for f in files:
    for n in walk(TREE[f].root_node):
        if n.type != "assignment_expression":
            continue
        op = n.child_by_field_name("operator")
        if not op or op.text != b"=":
            continue
        l = n.child_by_field_name("left"); r = n.child_by_field_name("right")
        if l and r and norm(txt(f, l)) == norm(txt(f, r)):
            # exclude when part of a comma carrier already in S1
            if n.parent and n.parent.type == "comma_expression":
                continue
            s2.append((f, line(n), func_of(n), txt(f, n)))

# ---------- S3: embedded assignment in a call argument ----------
s3 = []
for f in files:
    for n in walk(TREE[f].root_node):
        if n.type != "call_expression":
            continue
        args = n.child_by_field_name("arguments")
        if not args:
            continue
        for arg in args.named_children:
            a = arg
            while a is not None and a.type == "parenthesized_expression":
                k = [c for c in a.named_children if c.type != "comment"]
                a = k[0] if len(k) == 1 else None
            if a is not None and a.type in ("assignment_expression",):
                s3.append((f, line(arg), func_of(n), txt(f, n)[:100]))
            elif a is not None and a.type == "comma_expression" and assign_ops(a):
                s3.append((f, line(arg), func_of(n), txt(f, n)[:100]))

# ---------- S4: statement-level comma carrier with an assignment ----------
# (not a for-clause, not a plain 2-var init) -- discards value of an assign.
s4 = []
for f in files:
    for n in walk(TREE[f].root_node):
        if n.type != "comma_expression":
            continue
        if in_for_clause(n):
            continue
        # skip ones already in S1
        if (f, line(n), func_of(n), txt(f, n)) in s1:
            continue
        # left operand is a side-effecting assignment whose value is discarded
        l = n.child_by_field_name("left")
        if l is None:
            continue
        ll = l
        while ll is not None and ll.type == "parenthesized_expression":
            k = [c for c in ll.named_children if c.type != "comment"]
            ll = k[0] if len(k) == 1 else None
        if ll is not None and ll.type == "assignment_expression":
            s4.append((f, line(n), func_of(n), txt(f, n)[:100]))

# ---------- S5: void-cast of a LOCAL variable (not a parameter) ----------
# Gather each function's parameter names; a (void)x on a non-param local is
# the invented-dead-carrier smell (the action.c route_idx class).
def param_names(fndef):
    names = set()
    d = fndef.child_by_field_name("declarator")
    # function_declarator -> parameter_list
    for n in walk(d) if d else []:
        if n.type == "parameter_declaration":
            dd = n.child_by_field_name("declarator")
            for x in walk(dd) if dd else []:
                if x.type == "identifier":
                    names.add(x.text.decode())
    return names

s5_local, s5_param = [], []
for f in files:
    for fn in walk(TREE[f].root_node):
        if fn.type != "function_definition":
            continue
        pnames = param_names(fn)
        name = func_of(fn)
        for n in walk(fn):
            if n.type == "cast_expression":
                ty = n.child_by_field_name("type")
                val = n.child_by_field_name("value")
                if ty is not None and ty.text == b"void" and val is not None and val.type == "identifier":
                    v = val.text.decode()
                    rec = (f, line(n), name, txt(f, n))
                    (s5_param if v in pnames else s5_local).append(rec)


def show(hits, label):
    print(f"\n===== {label}: {len(hits)} =====")
    seen = set()
    for f, ln, fn, s in hits:
        key = (f, ln, s)
        if key in seen:
            continue
        seen.add(key)
        print(f"{os.path.basename(f):14} L{ln:<5} {fn:30} {s[:92]}")


show(s1, "S1 duplicated-store / self-assign COMMA carrier  (strong rover hack)")
show(s2, "S2 standalone self-assign  x = x;")
show(s3, "S3 assignment embedded in a call argument")
show(s4, "S4 statement-level comma carrier (discarded assignment value)")
show(s5_local, "S5 void-cast of a NON-parameter local  (invented dead carrier)")
print(f"\n(for reference: {len(s5_param)} void-casts on genuine unused ABI parameters -- legitimate, not listed)")

# ---------- S6: dead const-carrier local (assigned a literal, used only as a call arg) ----------
print("\n\n########## S6: const-carrier locals ##########")
def id_uses_in(fn):
    counts = {}
    sites = {}
    for n in walk(fn):
        if n.type == "identifier":
            nm = n.text.decode()
            counts[nm] = counts.get(nm, 0) + 1
            sites.setdefault(nm, []).append(n)
    return counts, sites

s6 = []
for f in files:
    for fn in walk(TREE[f].root_node):
        if fn.type != "function_definition":
            continue
        # collect local declarations (simple scalar) names
        local_names = set()
        for n in walk(fn):
            if n.type == "declaration":
                for d in n.named_children:
                    for x in walk(d):
                        if x.type == "identifier":
                            local_names.add(x.text.decode()); break
        counts, sites = id_uses_in(fn)
        for nm in local_names:
            # look for assignment 'nm = <number_literal>;' and a call-arg use
            wrote_const = None
            call_arg_use = 0
            other_use = 0
            for u in sites.get(nm, []):
                p = u.parent
                # assignment target with constant rhs
                if p and p.type == "assignment_expression" and p.child_by_field_name("left") is u:
                    op = p.child_by_field_name("operator")
                    rhs = p.child_by_field_name("right")
                    if op and op.text == b"=" and rhs is not None and rhs.type == "number_literal":
                        wrote_const = txt(f, p); continue
                # is it a direct argument of a call?
                gp = p
                is_arg = False
                cur = u
                while cur is not None and cur.parent is not None:
                    if cur.parent.type == "argument_list":
                        is_arg = True; break
                    if cur.parent.type not in ("parenthesized_expression",):
                        break
                    cur = cur.parent
                if is_arg:
                    call_arg_use += 1
                else:
                    # count declaration occurrence and everything else
                    other_use += 1
            # heuristic: exactly one const write, exactly one call-arg use,
            # and no OTHER uses beyond the declaration identifier
            if wrote_const and call_arg_use == 1 and other_use <= 1:
                s6.append((f, line(sites[nm][0]), func_of(fn), f"{nm}: {wrote_const}"))

show(s6, "S6 dead const-carrier local (literal write + single call-arg use)")
