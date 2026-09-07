#!/usr/bin/env python3
"""For the comb of h0_3_p0_act f0 cells: every matching sigma, the 2x3 adjacent
pairing system in (y_v, y_A, x_A) (x_v = y_A shared), its minors, primitive
kernel, and the transfer ratio x_A/y_v that governs growth along the chain."""
import itertools, json, os
from math import gcd
from functools import reduce
S = os.path.dirname(os.path.abspath(__file__))
D = json.load(open(os.path.join(S, "blocked_families.json")))
def analyse(ctx, fi, si):
    f = D[ctx]["families"][fi]; s = f["signatures"][si]
    r = [tuple(x) for x in s["token_rows"]]; L = f["denominator"]
    a = tuple(x[0] for x in r); b = tuple(x[1] for x in r)
    print(f"{ctx} f{fi} token {s['token']} rows {r} (over /{L}); y-col {a} x-col {b}")
    for sg in itertools.permutations(range(3)):
        sa = tuple(a[sg[i]] for i in range(3)); sb = tuple(b[sg[i]] for i in range(3))
        cols = [a, tuple(b[i]+sa[i] for i in range(3)), sb]
        m = {}
        for i, j in itertools.combinations(range(3), 2):
            m[(i, j)] = cols[i][0]*cols[j][1]-cols[i][1]*cols[j][0]
        ker = (m[(1, 2)], -m[(0, 2)], m[(0, 1)])
        g = reduce(gcd, [abs(v) for v in ker]) or 1
        ker = tuple(v//g for v in ker)
        ratio = f"{ker[2]}/{ker[0]}" if ker[0] else "inf"
        print(f"   sigma={sg}: minors (y_v,y_A)={m[(0,1)]} (y_v,x_A)={m[(0,2)]} (y_A,x_A)={m[(1,2)]}  kernel (y_v,y_A,x_A) ~ {ker}  ratio x_A/y_v = {ratio}")
analyse("h0_3_p0_act", 0, 0)
analyse("h1_2_p0_act", 0, 0)
