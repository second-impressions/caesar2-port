"""last-use-creation-order — the tie-break for equal-savings register ties.

THE FINDING (confirmed against Watcom 10.0a + a byte-exact close,
get_reg_buildings_in_radius @ commit ef1467d4):

When two values have EQUAL register savings, which one gets the
"earlier" register is decided by their CONFLICT-CREATION ORDER, and the
creation order is REVERSE LAST-USE.  The chain, from the Open Watcom CG
source (vendor/open-watcom/bld/cg/c):

  1. liveinfo.c  -- LiveAnalysis scans instructions BACKWARD
     (`ins = last; ...; ins = ins->head.prev`).  The first time a name
     is touched in that backward walk is its LAST use, and that is where
     FindConflictNode -> AddOne -> AddConflictNode creates its conflict.
  2. conflict.c  -- AddConflictNode PREPENDS to ConfList
     (`new->next_conflict = ConfList; ConfList = new`).  So ConfList is
     in reverse-creation = forward-last-use order.
  3. regalloc.c  -- SortConflicts sorts ConfList with ConfBefore, which
     is the STRICT `c1->savings > c2->savings` (savings only, no
     tie-break key), via an UNSTABLE ShellSort (sortlist.c).  For an
     equal-savings pair `before` is false both ways, so their final
     order is whatever the unstable sort leaves -- driven by their
     positions in the reverse-last-use ConfList.

Net rule of thumb that actually closes functions:

    The value whose LAST USE comes EARLIER is created LAST, lands at the
    head of ConfList, and sorts FIRST -> it gets the EARLIER register.

So the SOURCE LEVER for an equal-savings register-identity tie is the
relative LAST-USE position of the two values: to give value V the
earlier register, make V's final read come earlier than the rival's
(hoist V's last use up, or push the rival's last use down).  Declaration
order and first-assignment order usually do NOT move it -- only the last
use does.

This experiment proves it in isolation: two functions identical except
for the last-use ORDER of two equal-savings locals `a` and `b`.  The
register each lands in flips with the last-use order.

  uv run c2 cgex run last-use-creation-order

Expected: in `a_last_later` (a's final read is the later one) a takes
the LATER register (ebx) and b the earlier (edx); in `b_last_later` the
two are swapped -- same loads `a=ga; b=gb`, opposite registers, purely
because the last-use order changed.

Worked real-world application -- get_reg_buildings_in_radius (map.c):
the 16b residue was an equal-savings span/radius tie (PS: radius->EAX,
span kept in EBX; ours: span->EAX, radius->EDX).  Rewriting

    width = radius * 2 + 1;        height = radius * 2 + 1;
    span--; width += span;   ->    span--;
    height = width;                width = height + span;
                                   height = width;

puts span's last use AFTER radius's, so radius is created last and sorts
first -> radius->EAX like PS -> byte-exact.
"""

from c2.commands.cgex import Experiment

exp = Experiment(
    name="last-use-creation-order",
    chk=False,
    externs={
        "ext": "extern int ext(int x);",
    },
)

# Both `a` and `b` are loaded from globals (equal savings: each read once
# pre and used twice post) and held across a call.  The ONLY difference
# between the two trials is which one's final read (`+ 1` store) comes
# last.

exp.add(
    "a_last_later",
    """
int ga, gb, gc, gd;

int f(void)
{
    int a;
    int b;
    a = ga;
    b = gb;
    ext(0);
    gc = b;
    gd = a;
    gc = b + 1;       /* b's last use */
    gd = a + 1;       /* a's last use -- LATER than b's */
    return 0;
}
""",
    note="a's final read is later -> a created first -> a sorts last -> a=ebx, b=edx",
)

exp.add(
    "b_last_later",
    """
int ga, gb, gc, gd;

int f(void)
{
    int a;
    int b;
    a = ga;
    b = gb;
    ext(0);
    gc = b;
    gd = a;
    gd = a + 1;       /* a's last use */
    gc = b + 1;       /* b's last use -- LATER than a's */
    return 0;
}
""",
    note="b's final read is later -> b created first -> b sorts last -> b=ebx, a=edx",
)
