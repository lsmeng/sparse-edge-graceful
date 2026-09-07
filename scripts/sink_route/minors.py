#!/usr/bin/env python3
"""Pairing systems between blocked token families: full 2x3 (adjacent, shared
parameter x_v = y_A) and 2x4 (non-adjacent) integer matrices for every
matching sigma; gcd of 2x2 minors (Z-surjectivity), unimodular blocks, and the
primitive kernel vector of the adjacent homogeneous system."""
import json, itertools, os
from math import gcd
from functools import reduce
S = os.path.dirname(os.path.abspath(__file__))
D = json.load(open(os.path.join(S, "blocked_families.json")))
def tok_fams(ctx):
    out = []
    for fi, f in enumerate(D[ctx]["families"]):
        for si, s in enumerate(f["signatures"]):
            r = s["token_rows"]
            if r[0][0]*r[1][1]-r[0][1]*r[1][0] == 0: continue   # rank-1 token, fails (E4)
            out.append((f"{ctx}#f{fi}s{si}", f["denominator"], [tuple(x) for x in r], s["token"]))
    return out
F = sum((tok_fams(c) for c in ["h0_3_p0_act", "h1_2_p0_act", "h0_5_p0_act"]), [])
print(len(F), "token families")
def det2(u, v): return u[0]*v[1]-u[1]*v[0]
def minors2(cols):   # cols: list of 3-vectors (rows 0..2); use rows 0,1 (rows sum to 0 so all agree up to sign)
    m = {}
    for i, j in itertools.combinations(range(len(cols)), 2):
        m[(i, j)] = cols[i][0]*cols[j][1]-cols[i][1]*cols[j][0]
    return m
perms = list(itertools.permutations(range(3)))
summary = []
for (n1, L1, r1, t1), (n2, L2, r2, t2) in itertools.product(F, F):
    a = tuple(r[0] for r in r1); b = tuple(r[1] for r in r1)     # resolver v: y-col, x-col over rows
    a2 = tuple(r[0] for r in r2); b2 = tuple(r[1] for r in r2)   # pending A
    best_adj = None; best_non = None
    for s in perms:
        sa2 = tuple(a2[s[i]] for i in range(3)); sb2 = tuple(b2[s[i]] for i in range(3))
        # T_v + sigma T_A = 0 ; rows scaled by L1 and L2 resp. -> put on common integer footing:
        # forms are rows/L ; equation (rows1/L1) K + sigma(rows2/L2) Lam = 0 -> multiply by lcm
        Lc = L1*L2//gcd(L1, L2)
        f1, f2 = Lc//L1, Lc//L2
        A = tuple(f1*x for x in a); B = tuple(f1*x for x in b)
        A2 = tuple(f2*x for x in sa2); B2 = tuple(f2*x for x in sb2)
        adj_cols = [A, tuple(B[i]+A2[i] for i in range(3)), B2]        # unknowns y_v, y_A(=x_v), x_A
        non_cols = [A, B, A2, B2]                                     # unknowns y_v, x_v, y_A, x_A
        ma = minors2(adj_cols); mn = minors2(non_cols)
        ga = reduce(gcd, [abs(v) for v in ma.values()]); gn = reduce(gcd, [abs(v) for v in mn.values()])
        # primitive kernel of the adjacent 2x3 system: (m12, -m02, m01)
        ker = (ma[(1, 2)], -ma[(0, 2)], ma[(0, 1)])
        g = reduce(gcd, [abs(v) for v in ker]) or 1
        ker = tuple(v//g for v in ker)
        rec = dict(sigma=s, adj_minors=ma, adj_gcd=ga, ker=ker, non_minors=mn, non_gcd=gn,
                   adj_unimodular=[k for k, v in ma.items() if abs(v) == 1],
                   non_unimodular=[k for k, v in mn.items() if abs(v) == 1])
        if best_adj is None or (ga, -len(rec["adj_unimodular"])) < (best_adj["adj_gcd"], -len(best_adj["adj_unimodular"])): best_adj = rec
        if best_non is None or (gn, -len(rec["non_unimodular"])) < (best_non["non_gcd"], -len(best_non["non_unimodular"])): best_non = rec
    summary.append((n1, n2, best_adj, best_non))
# print compact
for n1, n2, ba, bn in summary:
    if not (n1.startswith("h0_3") or n1.startswith("h1_2")) and not (n2.startswith("h0_3") or n2.startswith("h1_2")): continue
    print(f"{n1:22s} resolves {n2:22s} | adjacent: gcd={ba['adj_gcd']} unimod-blocks={ba['adj_unimodular']} ker={ba['ker']} sigma={ba['sigma']} | nonadjacent: gcd={bn['non_gcd']} unimod-blocks={bn['non_unimodular']}")
print()
print("over all ordered pairs (incl. h0_5): adjacent gcd distribution", 
      sorted(set(ba['adj_gcd'] for _,_,ba,_ in summary)), "nonadjacent gcd distribution", sorted(set(bn['non_gcd'] for _,_,_,bn in summary)))
bad_adj = [(n1,n2,ba['adj_gcd']) for n1,n2,ba,_ in summary if ba['adj_gcd'] != 1]
bad_non = [(n1,n2,bn['non_gcd']) for n1,n2,_,bn in summary if bn['non_gcd'] != 1]
print("pairs whose adjacent system is never Z-surjective:", len(bad_adj), bad_adj[:20])
print("pairs whose non-adjacent system is never Z-surjective:", len(bad_non), bad_non[:20])
json.dump([dict(resolver=n1, pending=n2, adjacent=ba, nonadjacent=bn) for n1,n2,ba,bn in summary],
          open(os.path.join(S, "pair_minors.json"), "w"), default=str, indent=0)
