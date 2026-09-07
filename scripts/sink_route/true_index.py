#!/usr/bin/env python3
"""Index of a token map's image, computed on the family's OWN integrality
lattice {p in Z^k : all labels integral}, instead of det over (y,x) with a
separate denominator.  Brute force over residues mod L (k <= 4, L <= 12)."""
import json, itertools, os, sys
from math import gcd
from functools import reduce
S = os.path.dirname(os.path.abspath(__file__))
def lattice_basis(C, L, k):
    # generators: L*e_i and every residue vector r (0<=r_i<L) with C r = 0 mod L
    gens = [tuple(L if j == i else 0 for j in range(k)) for i in range(k)]
    for r in itertools.product(range(L), repeat=k):
        if all(sum(c*x for c, x in zip(row, r)) % L == 0 for row in C):
            gens.append(r)
    # Hermite normal form by integer row reduction
    M = [list(g) for g in gens]
    basis = []
    for col in range(k):
        rows = [r for r in M if r[col] != 0]
        if not rows: continue
        # gcd-reduce into one pivot row
        while True:
            rows = [r for r in M if r[col] != 0]
            if len(rows) <= 1: break
            rows.sort(key=lambda r: abs(r[col]))
            piv = rows[0]
            for r in rows[1:]:
                q = r[col] // piv[col]
                for j in range(k): r[j] -= q*piv[j]
            M = [r for r in M if any(r)]
        piv = next(r for r in M if r[col] != 0)
        basis.append(piv[:]); M.remove(piv)
    return basis   # k vectors (upper triangular)
def analyse(name, forms_coeffs, L, token_idx, params):
    k = len(params)
    C = [list(v) for v in forms_coeffs]
    B = lattice_basis(C, L, k)
    detB = 1
    for i in range(k): detB *= B[i][i]
    a, b = C[token_idx[0]], C[token_idx[1]]
    # token rows in lattice coordinates, divided by L (exact by construction)
    TA = [sum(a[j]*B[i][j] for j in range(k)) // L for i in range(k)]
    TB = [sum(b[j]*B[i][j] for j in range(k)) // L for i in range(k)]
    minors = [TA[i]*TB[j]-TA[j]*TB[i] for i in range(k) for j in range(i+1, k)]
    g = reduce(gcd, [abs(m) for m in minors]) if minors else 0
    print(f"{name}: L={L} params={params} lattice index [Z^k:Lambda_F]={detB}; token rows on lattice basis: {TA} {TB}; minors {minors}; IMAGE INDEX = {g}")
D = json.load(open(os.path.join(S, "blocked_families.json")))
def run(ctx, fi, si):
    f = D[ctx]["families"][fi]; s = f["signatures"][si]
    names = list(f["labels"].keys()); C = [f["labels"][n] for n in names]
    tok = [names.index(t) for t in s["token"]]
    analyse(f"{ctx} f{fi}", C, f["denominator"], tok, ["y", "x"])
run("h0_3_p0_act", 0, 0); run("h1_2_p0_act", 0, 0)
for fi, f in enumerate(D["h0_5_p0_act"]["families"]):
    for si, s in enumerate(f["signatures"]):
        r = s["token_rows"]
        if r[0][0]*r[1][1]-r[0][1]*r[1][0] == 0: continue
        # (E6) second clause: skip families with a pure multiple of y among non-head labels
        if any(v[1] == 0 and n != "g0" for n, v in f["labels"].items()): continue
        run("h0_5_p0_act", fi, si)
# h4 catalogue family: (y,x) core only
C4 = [[1,0],[-3,-3],[1,1],[0,-1],[2,3],[-2,-3],[1,2],[2,2],[-1,-1],[-2,-2],[2,1],[0,1]]
analyse("h4_1-3-3-3_p0_act (y,x core)", C4, 1, [1, 6], ["y", "x"])
