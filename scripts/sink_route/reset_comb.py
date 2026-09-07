#!/usr/bin/env python3
r"""The witness comb of Lemma lem:reset (paper/sparse_edge_graceful.tex).

The manuscript's sentence is

    "Our scheduler does produce arbitrarily long such chains, on a comb whose
     every core vertex has two active children and one arm of length one, so
     the length is Theta(D) in the worst case and not O(1)."

``reset_comb(k, bush)`` is that comb, made concrete.  Its spine is
``s_1 > s_2 > ... > s_k``; every spine vertex carries

  * an arm of length one   (``s_i - m_i - t_i``: one degree-two vertex and a
    leaf, i.e. the residual ``{1}``),
  * a second active child  ``w_i``, and
  * the next spine vertex  ``s_{i+1}``  (for ``i < k``; the bottom spine
    vertex ``s_k`` gets a second small owner ``w'_k`` instead),

so each ``s_i`` is a residual-{1} DIRECT-EDGE TWO-INPUT row: head chain
length 0, one residual arm of residue 1, no ports, two kept active children.
Its context key is :data:`context_scheduler.RESET_ROW_KEY` =
``h0_1_p0_act2``, whose only family has the forced head ``-x1-x2``, and
``s_1 > ... > s_k`` is a chain of exactly ``k`` such rows.

``w_i`` is the smallest owner that is neither a passthrough nor a
"residue-one zero-spare" owner (which would be folded into its parent as the
child type ``L1``/``L11``/``L12`` and would stop ``s_i`` from being an
``act2`` row at all): one arm of length one and one arm of length two, i.e.
the ordinary bottom context ``h0_1-2_p0_bot``.

The spine hangs off a bushy root, whose ``bush`` leaves make ``n`` grow
without touching the number of degree-two vertices, so ``n >> D``:

    n = 9k + 9 + bush (+1 to keep the order odd),   D = 4k + 4,

with ``bush = default_bush(k) = 40k + 60`` unless one is given.

The root also carries one arm of length one, which makes it the ordinary
owner ``root_1_p2_act`` rather than a stationary helper.  A helper has
exactly one label to place, ``-x`` with ``x`` the spine head, and no
parameter of its own, so a collision there can only be repaired by redoing
the whole tree; with ``root_arm=False`` (kept for comparison) that is what
happens.  The rest of the root's ports stay an ordinary zero-sum block and
are the sink route's direct-sink capacity, so ``bush`` must be large enough
for the ``k + 2`` free tokens of the small owners and the root, and large
enough for ``n`` to dwarf the special support (see :func:`default_bush`).

usage: reset_comb.py [K ...] [--bush B]
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import List, Optional, Sequence, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.normpath(os.path.join(HERE, ".."))
for _p in (HERE, SCRIPTS):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import context_scheduler as cs  # noqa: E402


#: default bush size: keeps n near 12*(D+1), which the modular step needs
def default_bush(k: int) -> int:
    """A bush large enough for ``n`` to dwarf the special support.

    The special labels are integers of magnitude up to about ``5(D+1)`` and
    must stay distinct MOD ``n``, so ``n`` has to be a comfortable multiple of
    ``D + 1``; ``D = 4k + 4`` here, and ``n = 9k + 9 + bush``.  With this bush
    ``n / (D + 1)`` is about 12.5 for every ``k``, the same ratio the existing
    comb+bush regression trees have.
    """
    return 40 * k + 60


def reset_comb(k: int, bush: Optional[int] = None,
               root_arm: bool = True) -> Tuple[List[int], List[int]]:
    """``(parent_array, spine)`` of the witness comb with ``k`` spine rows."""
    if k < 1:
        raise ValueError("k must be >= 1")
    bush = default_bush(k) if bush is None else bush
    if bush < 2:
        raise ValueError("the root needs a bush of at least two leaves")
    par: List[int] = [-1]

    def add(p: int) -> int:
        par.append(p)
        return len(par) - 1

    def small_owner(p: int) -> int:
        """``h0_1-2_p0_bot``: one arm of length 1, one arm of length 2."""
        w = add(p)
        a = add(w)
        add(a)                       # arm of length 1: w - a - leaf
        b = add(w)
        c = add(b)
        add(c)                       # arm of length 2: w - b - c - leaf
        return w

    root = 0
    prev = root
    spine: List[int] = []
    for _ in range(k):
        s = add(prev)
        spine.append(s)
        m = add(s)
        add(m)                       # the residual arm of length 1
        small_owner(s)               # the pinned second active child
        prev = s
    small_owner(prev)                # the bottom row's second active child
    if root_arm:
        r = add(root)
        add(r)                       # the root's own arm of length 1
    for _ in range(bush):
        add(root)
    if len(par) % 2 == 0:
        add(root)                    # the order must be odd
    return par, spine


def describe(k: int, bush: Optional[int] = None,
             root_arm: bool = True) -> dict:
    """Schedule the witness and report its reset chains and joints."""
    par, spine = reset_comb(k, bush, root_arm)
    sched = cs.schedule(par)
    chains = cs.reset_chains(sched["rows"])
    joints = sched["reset_joints"]
    keys = {o["vertex"]: o["context_key"] for o in sched["owners"]}
    deg = [0] * len(par)
    for v in range(1, len(par)):
        deg[v] += 1
        deg[par[v]] += 1
    return {"k": k, "bush": len(par) - 9 * k - 9, "n": len(par),
            "D": sum(1 for v in range(len(par)) if deg[v] == 2),
            "parent": par, "spine": spine,
            "root": sched["root"],
            "uncovered": sched["uncovered"],
            "owners": [(v, keys[v]) for v in sorted(keys)],
            "chain_lengths": [len(c) for c in chains],
            "chains": chains, "reset_joints": joints}


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("k", nargs="*", type=int, default=[6])
    ap.add_argument("--bush", type=int, default=None)
    ap.add_argument("--owners", action="store_true",
                    help="print the full owner list once")
    a = ap.parse_args(argv)
    printed = False
    for k in a.k:
        rep = describe(k, a.bush)
        print(f"k={rep['k']} n={rep['n']} D={rep['D']} root={rep['root']} "
              f"uncovered={len(rep['uncovered'])} "
              f"chain_lengths={rep['chain_lengths']} "
              f"reset_joints={len(rep['reset_joints'])}")
        for j in rep["reset_joints"]:
            print(f"    joint upper={j['upper']} lower={j['lower']} "
                  f"input_upper={j['input_upper']} "
                  f"inputs_lower={j['inputs_lower']}")
        if a.owners and not printed:
            printed = True
            print("  owners (vertex, context key):")
            for v, key in rep["owners"]:
                print(f"    {v:4d}  {key}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
