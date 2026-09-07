#!/usr/bin/env python3
r"""Every family of the Lemma lem:reset joint, ranked by usable freedom.

``scripts/twoinput_reset.py`` proves Lemma lem:reset: of the 14 nondegenerate
``P = O`` families of the two-level joint, 12 have a direction along which the
head ``g0`` moves while every input is held fixed.  It records ONE of them in
``data/twoinput_reset.json``, the first its enumeration meets, which is enough
for the lemma but is the WEAKEST of the twelve for a constructor: with the
three inputs pinned, only three of its nine labels move
(``g0, r1a0x0, r1a0x1``), so ``g1``, ``r0a0x0`` and ``r0a0x1`` are fixed
outright by the children's heads and the joint cell cannot search for them.

This program re-runs the same enumeration, records all twelve, and ranks them
by how many labels still move once the inputs are pinned.  Seven of the twelve
move all SIX non-input labels: for those the joint has genuine two-parameter
freedom in every label it places, which is what
``reset_joint_constructor.py`` uses.

For each family the output carries the bijection outputs -> labels, an integer
point, the dimension, the moving set, and the COEFFICIENT TABLE of the nine
labels over the five parameters

    (y, u1, s0, x1, x2) = (g0, one internal label, the three pinned inputs)

obtained by inverting the 5x5 matrix that reads those five coordinates off the
nullspace basis.  ``reset_joint_constructor.verify_family`` re-derives ``P = O``
from that table independently, so the table is checked, not trusted.

usage: reset_joint_families.py [--out FILE] [--top N]
"""
from __future__ import annotations

import argparse
import itertools
import json
import os
import random
import sys
from fractions import Fraction as Q
from typing import List, Optional, Sequence

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.normpath(os.path.join(HERE, ".."))
for _p in (HERE, SCRIPTS):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import twoinput_reset as tr                        # noqa: E402

DATA = os.path.normpath(os.path.join(HERE, "..", "..", "data"))
OUT = os.path.join(DATA, "sink_route", "twoinput_reset_families.json")

#: the internal label tried, in order, as the second free parameter ``u1``
U1_CANDIDATES = ["r0a0x0", "r0a0x1", "g1", "r1a0x0", "r1a0x1"]


def _inverse(m: List[List[Q]]) -> Optional[List[List[Q]]]:
    n = len(m)
    a = [row[:] + [Q(1) if i == j else Q(0) for j in range(n)]
         for i, row in enumerate(m)]
    for c in range(n):
        p = next((i for i in range(c, n) if a[i][c]), None)
        if p is None:
            return None
        a[c], a[p] = a[p], a[c]
        pv = a[c][c]
        a[c] = [x / pv for x in a[c]]
        for i in range(n):
            if i != c and a[i][c]:
                f = a[i][c]
                a[i] = [x - f * y for x, y in zip(a[i], a[c])]
    return [row[n:] for row in a]


def coefficient_table(names: Sequence[str], B: Sequence[Sequence[Q]],
                      params: Sequence[str]):
    """Each label as a Q-combination of the five chosen coordinate labels."""
    idx = [names.index(p) for p in params]
    M = [[b[i] for i in idx] for b in B]           # basis coefficient -> coords
    Minv = _inverse(M)
    if Minv is None:
        return None
    table = {}
    for k, nm in enumerate(names):
        col = [b[k] for b in B]
        table[nm] = [sum(Minv[r][t] * col[t] for t in range(len(B)))
                     for r in range(len(B))]
    for r, p in enumerate(params):                 # sanity: a coordinate is itself
        want = [Q(1) if i == r else Q(0) for i in range(len(params))]
        if table[p] != want:
            return None
    return table


def enumerate_families() -> List[dict]:
    T = tr.topology(2)
    n = len(T.labels)
    names = [lb["name"] for lb in T.labels]
    kinds = [lb["kind"] for lb in T.labels]
    outs = [o["name"] for o in T.outputs]
    A = [[Q(1) if i in set(o["terms"]) else Q(0) for i in range(n)]
         for o in T.outputs]
    ig = names.index("g0")
    inputs = [i for i, lb in enumerate(T.labels) if lb["kind"] == "input"]
    input_names = [names[i] for i in inputs]
    found: List[dict] = []
    for perm in itertools.permutations(range(n)):
        rows = [[A[k][c] - (Q(1) if c == perm[k] else Q(0)) for c in range(n)]
                for k in range(n)]
        B = tr.nullspace(rows, n)
        if not B:
            continue
        random.seed(5)
        pt = None
        for _ in range(60):
            cs = [Q(random.randrange(-25, 25)) for _ in B]
            v = [sum(c * b[k] for c, b in zip(cs, B)) for k in range(n)]
            if 0 not in v and len(set(v)) == n:
                pt = v
                break
        if pt is None:
            continue
        M = [[b[i] for b in B] for i in inputs]
        K = [kv for kv in tr.nullspace(M, len(B))]
        moving, head_free = set(), False
        for kv in K:
            w = [sum(kv[t] * B[t][k] for t in range(len(B)))
                 for k in range(n)]
            moving |= {names[k] for k in range(n) if w[k]}
            if sum(kv[t] * B[t][ig] for t in range(len(B))):
                head_free = True
        if not head_free:
            continue
        table = params = None
        for u1 in U1_CANDIDATES:
            params = ["g0", u1] + input_names
            table = coefficient_table(names, B, params)
            if table is not None:
                break
        entry = {
            "labels": names, "kinds": kinds, "outputs": outs,
            "bijection": {outs[k]: names[perm[k]] for k in range(n)},
            "dimension": len(B),
            "free_after_pinning": len(K),
            "moving": sorted(moving), "n_moving": len(moving),
            "integer_point": {names[k]: str(pt[k]) for k in range(n)},
            "parameters": params,
            "coefficients_by_label":
                ({nm: [str(x) for x in row] for nm, row in table.items()}
                 if table else None),
        }
        found.append(entry)
    found.sort(key=lambda e: (-e["n_moving"], -e["free_after_pinning"],
                              json.dumps(e["bijection"], sort_keys=True)))
    return found


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--top", type=int, default=3)
    a = ap.parse_args(argv)
    fams = enumerate_families()
    print(f"{len(fams)} head-free families of the two-level joint")
    for e in fams[:a.top]:
        print(f"  dim={e['dimension']} free_after_pinning="
              f"{e['free_after_pinning']} moving={e['n_moving']}: "
              f"{e['moving']}")
        print(f"     bijection {e['bijection']}")
        print(f"     parameters {e['parameters']}")
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w") as fh:
        json.dump({"topology": "levels=2 (arms=1;active=2;input=1 over "
                                "arms=1;active2;input2)",
                   "source": "scripts/twoinput_reset.py enumeration, ranked",
                   "count": len(fams), "families": fams}, fh, indent=1)
    print(f"wrote {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
