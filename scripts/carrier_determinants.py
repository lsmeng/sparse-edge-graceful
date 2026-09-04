#!/usr/bin/env python3
"""Can the carrier of every token family be chosen unimodular?

Appendix B resolves a pending token by solving T_v = -T_A for the carrier
K(F): two equations in two unknowns, M K = rhs, so K = M^{-1} rhs.  The audit
observed that M^{-1} = adj(M)/det(M) can both enlarge coefficients and destroy
integrality, so the catalogue's raw coefficient bound is not preserved.

(E4) only asks that SOME pair of parameters carries the token's plane.  The
carrier is therefore ours to choose, and if a pair with |det M| = 1 always
exists then M^{-1} is an integer matrix: integrality survives and the growth
is bounded by the entries of adj(M) alone.

Writing the token as a, b, c with a + b + c = 0, the three 2x2 minors on a
fixed pair of columns coincide up to sign, so each candidate carrier has one
well-defined |det|.  This script reports, per family, the minimum |det| over
all admissible carriers, and the resulting coefficient growth.
"""
import json, os, sys
from fractions import Fraction as Q
from itertools import combinations

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.normpath(os.path.join(HERE, "..", "data"))


def token_vectors(fam):
    out = []
    labs = fam.get("labels") or []
    cbl = fam.get("coefficients_by_label") or {}
    for keyname in ("token_indices", "token2_indices"):
        ti = fam.get(keyname)
        if not isinstance(ti, dict):
            continue
        try:
            rows = [cbl[labs[ti[r]]["name"]] for r in ("a", "b", "c")]
        except Exception:
            continue
        out.append((keyname, rows))
    return out


def analyse(fam):
    """min |det| over carriers, and the growth factor at the best carrier."""
    res = []
    cbl = fam.get("coefficients_by_label") or {}
    npar = len(fam.get("parameters") or [])
    for tag, rows in token_vectors(fam):
        a, b = rows[0], rows[1]
        best = None
        for i, j in combinations(range(npar), 2):
            d = a[i] * b[j] - a[j] * b[i]
            if d == 0:
                continue
            if best is None or abs(d) < abs(best[0]):
                best = (d, i, j)
        if best is None:
            res.append((tag, None, None, None))
            continue
        d, i, j = best
        # adj(M) = [[ b_j, -a_j], [-b_i, a_i]]; a label's carrier row r gives
        # r * adj(M), whose entries bound the post-elimination coefficients
        adj = ((b[j], -a[j]), (-b[i], a[i]))
        growth = 0
        for v in cbl.values():
            r0, r1 = v[i], v[j]
            for col in (0, 1):
                growth = max(growth, abs(r0 * adj[0][col] + r1 * adj[1][col]))
        res.append((tag, abs(d), growth, (i, j)))
    return res


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(DATA, "alphabet_families.json")
    cat = json.load(open(path))
    dets = {}
    worst_growth = 0
    worst_where = None
    no_carrier = []
    ntok = 0
    for k in sorted(cat):
        for i, f in enumerate(cat[k].get("menu") or [cat[k]], 1):
            fam = f.get("family") or f
            if not isinstance(fam, dict) or "coefficients_by_label" not in fam:
                continue
            for tag, d, g, cols in analyse(fam):
                ntok += 1
                if d is None:
                    no_carrier.append(f"{k} menu{i} {tag}")
                    continue
                dets[d] = dets.get(d, 0) + 1
                if g > worst_growth:
                    worst_growth, worst_where = g, f"{k} menu{i} {tag} carrier{cols}"
    print(f"catalogue         : {path}")
    print(f"tokens examined   : {ntok}")
    print(f"no valid carrier  : {len(no_carrier)}  {no_carrier[:5]}")
    print(f"min |det| histogram (minimum over admissible carriers):")
    for d in sorted(dets):
        print(f"    |det| = {d:<4}  {dets[d]} tokens")
    print(f"max coefficient growth |r . adj(M)| at the best carrier: {worst_growth}")
    print(f"    attained at {worst_where}")


if __name__ == "__main__":
    main()
