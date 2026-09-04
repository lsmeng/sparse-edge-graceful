#!/usr/bin/env python3
"""The reset for a chain of residual-one direct-edge two-input rows.

The row with head chain 0, one arm of length one, no ports and two pinned
inputs is the one cell of the decomposition whose head is not an independent
parameter: enumerating every bijection between its five labels and its five
outputs leaves exactly one nondegenerate family, and its head is -x1-x2.  It
carries no token, so it neither resolves a pending token nor becomes one, and a
chain of such rows therefore carries a symbolic head upward for as many levels
as the chain is long.  Our scheduler does produce chains of length Theta(D).

This program shows that joining two consecutive such rows into one cell removes
the obstruction: the joint has families whose head is an independent parameter.
The chain can then be cut every two levels and the symbolic support is bounded
by a constant number of cells again.

usage: twoinput_reset.py [LEVELS] [--out FILE]
"""
import argparse
import itertools
import json
import os
import random
import sys
from fractions import Fraction as Q

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import symbolic_free_token_cpsat as sc  # noqa: E402

DATA = os.path.normpath(os.path.join(HERE, "..", "data"))


def topology(levels):
    """A stack of `levels` residual-one two-input rows, as one cell."""
    rows = [sc.parse_row("arms=1;active=2;input=1") for _ in range(levels - 1)]
    rows.append(sc.parse_row("arms=1;active2;input2"))
    return sc.Topology(rows)


def nullspace(rows, n):
    m = [r[:] for r in rows]
    piv, r = [], 0
    for c in range(n):
        p = next((i for i in range(r, len(m)) if m[i][c]), None)
        if p is None:
            continue
        m[r], m[p] = m[p], m[r]
        pv = m[r][c]
        m[r] = [a / pv for a in m[r]]
        for i in range(len(m)):
            if i != r and m[i][c]:
                f = m[i][c]
                m[i] = [a - f * b for a, b in zip(m[i], m[r])]
        piv.append(c)
        r += 1
        if r == len(m):
            break
    out = []
    for f in [c for c in range(n) if c not in piv]:
        v = [Q(0)] * n
        v[f] = Q(1)
        for i, c in enumerate(piv):
            v[c] = -m[i][f]
        out.append(v)
    return out


def search(levels, want_one=False):
    T = topology(levels)
    n = len(T.labels)
    names = [l["name"] for l in T.labels]
    A = [[Q(1) if i in set(o["terms"]) else Q(0) for i in range(n)]
         for o in T.outputs]
    ig = names.index("g0")
    inputs = [i for i, l in enumerate(T.labels) if l["kind"] == "input"]
    total = freehead = 0
    witness = None
    for perm in itertools.permutations(range(n)):
        rows = [[A[k][c] - (Q(1) if c == perm[k] else Q(0)) for c in range(n)]
                for k in range(n)]
        B = nullspace(rows, n)
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
        total += 1
        M = [[b[i] for b in B] for i in inputs]
        hf = [kv for kv in nullspace(M, len(B))
              if sum(kv[t] * B[t][ig] for t in range(len(B)))]
        if not hf:
            continue
        freehead += 1
        if witness is None:
            w = [sum(hf[0][t] * B[t][k] for t in range(len(B))) for k in range(n)]
            witness = {
                "levels": levels,
                "labels": names,
                "kinds": [l["kind"] for l in T.labels],
                "nullspace_dimension": len(B),
                "bijection": {T.outputs[k]["name"]: names[perm[k]] for k in range(n)},
                "integer_point": {names[k]: str(pt[k]) for k in range(n)},
                "head_free_direction": {names[k]: str(w[k]) for k in range(n) if w[k]},
                "P_equals_O": sorted(pt) == sorted(
                    sum(pt[i] for i in o["terms"]) for o in T.outputs),
                "distinct_and_nonzero": len(set(pt)) == n and 0 not in pt,
            }
            if want_one:
                break
    return total, freehead, witness


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("levels", nargs="?", type=int, default=2)
    ap.add_argument("--out", default=os.path.join(DATA, "twoinput_reset.json"))
    ap.add_argument("--first", action="store_true",
                    help="stop at the first witness instead of counting all")
    a = ap.parse_args()
    total, freehead, w = search(a.levels, a.first)
    print(f"levels = {a.levels}")
    print(f"  nondegenerate P=O families            : {total}")
    print(f"  of those with a head free of the inputs: {freehead}")
    if w:
        print(f"  P = O at the exhibited point           : {w['P_equals_O']}")
        print(f"  labels distinct and nonzero            : {w['distinct_and_nonzero']}")
        print(f"  head-free direction                    : {w['head_free_direction']}")
        json.dump(w, open(a.out, "w"), indent=1)
        print(f"  wrote {a.out}")
    return 0 if freehead else 1


if __name__ == "__main__":
    sys.exit(main())
