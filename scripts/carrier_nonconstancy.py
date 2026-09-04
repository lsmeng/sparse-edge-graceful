#!/usr/bin/env python3
"""Item (iv) of the coefficient-bound repair: non-constancy after elimination.

When a token cell ``v`` resolves a pending token ``T_A``, Appendix B solves
``T_v = -T_A`` for the carrier ``K(F)`` of ``v``.  With ``M`` the 2x2 carrier
block of the token map of ``v`` and ``N`` the coefficient matrix of ``T_A`` on
the live set, a label ``l`` of ``v`` with carrier row ``r_l`` becomes

    l = -(r_l adj(M)) N Lambda / det(M) + const .

The appendix claims that every label of ``v`` that depends on the carrier stays
a NON-CONSTANT affine form in ``Lambda``.  That needs ``r_l adj(M) N != 0``,
which does not follow from (E3): (E3) only says ``r_l != 0``.  This program
checks it over every ordered pair (pending family A, resolving family F) that
the catalogue allows, at the minimising carrier of each, and over all three
matchings of the token coordinates.

A pair fails only if some carrier-dependent label of ``F`` becomes constant.
Such a pair, if any, must be excluded by the choice rule, so the count of
failures is what decides whether the repair is complete or needs a table.

usage: carrier_nonconstancy.py [CATALOGUE] [--limit N] [--out FILE]
"""
import argparse
import json
import os
import sys
from itertools import combinations, permutations

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from carrier_determinants import token_vectors  # noqa: E402

DATA = os.path.normpath(os.path.join(HERE, "..", "data"))


def best_carrier(rows, npar):
    """The carrier of least |det| for a token, as (det, i, j)."""
    a, b = rows[0], rows[1]
    best = None
    for i, j in combinations(range(npar), 2):
        d = a[i] * b[j] - a[j] * b[i]
        if d and (best is None or abs(d) < abs(best[0])):
            best = (d, i, j)
    return best


def tokens_of(fam):
    """[(tag, rows, npar, coefficients_by_label)] for each token of a family."""
    npar = len(fam.get("parameters") or [])
    cbl = fam.get("coefficients_by_label") or {}
    return [(tag, rows, npar, cbl) for tag, rows in token_vectors(fam)]


def collect(cat):
    out = []
    for k in sorted(cat):
        for i, f in enumerate(cat[k].get("menu") or [cat[k]], 1):
            fam = f.get("family") or f
            if not isinstance(fam, dict) or "coefficients_by_label" not in fam:
                continue
            for tag, rows, npar, cbl in tokens_of(fam):
                bc = best_carrier(rows, npar)
                if bc is None:
                    continue
                out.append({"key": k, "menu": i, "tag": tag, "rows": rows,
                            "npar": npar, "cbl": cbl, "carrier": bc})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("catalogue", nargs="?",
                    default=os.path.join(DATA, "alphabet_families.json"))
    ap.add_argument("--limit", type=int, default=0,
                    help="check only the first N resolving families (0 = all)")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    toks = collect(json.load(open(a.catalogue)))
    print(f"{len(toks)} tokens with a minimising carrier")

    # The pending side enters only through N, the coefficient matrix of T_A on
    # the live set.  Its rows are two of A's token vectors restricted to A's
    # own carrier, so the set of distinct N over the catalogue is small.
    Ns, seen = [], set()
    for t in toks:
        d, i, j = t["carrier"]
        N = (tuple(t["rows"][0][c] for c in (i, j)),
             tuple(t["rows"][1][c] for c in (i, j)))
        if N not in seen:
            seen.add(N)
            Ns.append(N)
    print(f"{len(Ns)} distinct pending matrices N")

    res = toks if not a.limit else toks[:a.limit]
    bad, checked = [], 0
    for t in res:
        d, i, j = t["carrier"]
        a0, b0 = t["rows"][0], t["rows"][1]
        # adj(M) for M = [[a_i, a_j], [b_i, b_j]]
        adj = ((b0[j], -a0[j]), (-b0[i], a0[i]))
        rows_dep = [(nm, (v[i], v[j])) for nm, v in t["cbl"].items()
                    if v[i] or v[j]]
        for N in Ns:
            for perm in permutations(range(2)):       # the coordinate matching
                Np = (N[perm[0]], N[perm[1]])
                for nm, (r0, r1) in rows_dep:
                    w = (r0 * adj[0][0] + r1 * adj[1][0],
                         r0 * adj[0][1] + r1 * adj[1][1])
                    z = (w[0] * Np[0][0] + w[1] * Np[1][0],
                         w[0] * Np[0][1] + w[1] * Np[1][1])
                    checked += 1
                    if z == (0, 0):
                        bad.append({"key": t["key"], "menu": t["menu"],
                                    "tag": t["tag"], "label": nm,
                                    "carrier": [i, j], "N": [list(x) for x in Np]})
    print(f"{checked} (label, pending matrix, matching) triples checked")
    print(f"constant after elimination: {len(bad)}")
    for b in bad[:20]:
        print("   ", b)
    if a.out:
        json.dump(bad, open(a.out, "w"))
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
