#!/usr/bin/env python3
"""Binary-exact reference of WATCOM 10.0a's conflict sort (the equal-savings
tie-break = H2).

Confirmed by decompiling wcc386.exe (see docs/regalloc-tiebreak-findings.md):

* `SortConflicts` (inlined in SelectRegisters @0x608f4) does
  `ConfList = SortList(ConfList, 0, ConfBefore)`.
* `ConfBefore` (@0x609f0):  `return c1->savings > c2->savings;`  -- STRICT,
  unsigned `>`, NO secondary key. savings is at conflict_node+0x14.
* `DoSortList` (@0x6ef1c) allocates a scratch pointer array and, when the
  alloc succeeds (always, for the small conflict lists real compiles build),
  uses the **unstable `ShellSort`** (@0x6efe1). Only on _Alloc failure (low
  memory) does it fall back to the stable merge sort.
* `AddConflictNode` (@0x59ef1) **prepends** each new conflict to ConfList, so
  the list handed to the sort is in *reverse* creation order.

So equal-savings ties are NOT broken by a comparator key (H1 is disproven);
they are whatever the unstable ShellSort yields from the conflict-creation
order.  This module reproduces that exactly.

Use: feed `sort_conflicts` the conflicts in **ConfList order** (the order the
allocator's list has them, i.e. reverse of creation) with each item's
`savings`; it returns the post-sort order = the order `GiveRegister` assigns
them (highest savings first; equal-savings resolved by ShellSort).
"""
from __future__ import annotations
from typing import Callable, Sequence, List, Any


def conf_before(a_savings: int, b_savings: int) -> bool:
    """ConfBefore @0x609f0: strict unsigned greater-than on savings."""
    return (a_savings & 0xFFFFFFFF) > (b_savings & 0xFFFFFFFF)


def shell_sort(array: List[Any], before: Callable[[Any, Any], bool]) -> None:
    """In-place, byte-exact port of wcc386 ShellSort @0x6efe1:

        gap = length; adjust = 1
        do {
            adjust = !adjust
            gap = gap/2 + adjust
            do {
                swap = FALSE
                for i in 0 .. length-gap-1:
                    if before(array[i+gap], array[i]): swap them; swap = TRUE
            } while (swap)
        } while (gap != 1)

    Unstable: equal elements can be reordered by the gap>1 passes depending on
    their initial positions -- this is the H2 tie-break mechanism.
    """
    length = len(array)
    if length < 2:
        return
    gap = length
    adjust = 1
    while True:
        adjust = 0 if adjust else 1
        gap = gap // 2 + adjust
        while True:
            swap = False
            for i in range(0, length - gap):
                if before(array[i + gap], array[i]):
                    array[i], array[i + gap] = array[i + gap], array[i]
                    swap = True
            if not swap:
                break
        if gap == 1:
            break


def sort_conflicts(conflicts: Sequence[Any],
                   savings_of: Callable[[Any], int] = None) -> List[Any]:
    """Return conflicts in allocation order (what GiveRegister iterates).

    `conflicts` must be in **ConfList order** (allocator list order = reverse
    of creation order from AddConflictNode's prepend).  `savings_of(c)` yields
    each conflict's savings (default: attribute/key ``savings``).
    """
    if savings_of is None:
        def savings_of(c):
            return c["savings"] if isinstance(c, dict) else c.savings
    arr = list(conflicts)
    shell_sort(arr, lambda a, b: conf_before(savings_of(a), savings_of(b)))
    return arr


def creation_order_to_conflist(created: Sequence[Any]) -> List[Any]:
    """AddConflictNode prepends, so ConfList = reverse of creation order."""
    return list(reversed(list(created)))


if __name__ == "__main__":
    # self-test: equal-savings run order is decided by ShellSort over input pos
    items = [{"id": i, "savings": s} for i, s in
             enumerate([5, 5, 9, 2, 5, 9])]
    out = sort_conflicts(items)
    print("savings:", [c["savings"] for c in out])
    assert [c["savings"] for c in out] == [9, 9, 5, 5, 5, 2], out
    # the two 9s and three 5s keep a deterministic (not input-stable) order:
    print("ids    :", [c["id"] for c in out])
    print("ShellSort/ConfBefore reference OK")
