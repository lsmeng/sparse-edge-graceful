#!/usr/bin/env python3
"""Dump every P=O family of the blocked contexts over the (y, x, u...) basis,
with every admissible signature (token + mirror pairs), the token's
coefficient rows, and its 2x2 minors on every parameter pair."""
import itertools, json, sys, os
from fractions import Fraction as Q
from math import gcd
sys.path.insert(0, os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..")))
import symbolic_free_token_cpsat as sc
from raw_family_carriers import invert, nullspace
import random

def families(specs):
    T = sc.Topology([sc.parse_row(s) for s in specs])
    n = len(T.labels)
    names = [l["name"] for l in T.labels]
    kinds = [l["kind"] for l in T.labels]
    A = [[Q(1) if i in set(o["terms"]) else Q(0) for i in range(n)] for o in T.outputs]
    head = next(i for i, k in enumerate(kinds) if k == "head")
    inp = next(i for i, k in enumerate(kinds) if k == "input")
    nonhead = [i for i in range(n) if i != head]
    out = []
    seen = set()
    for perm in itertools.permutations(range(n)):
        rows = [[A[k][c] - (Q(1) if c == perm[k] else Q(0)) for c in range(n)] for k in range(n)]
        B = nullspace(rows, n)
        d = len(B)
        if d < 2: continue
        vec = {k: [B[t][k] for t in range(d)] for k in range(n)}
        random.seed(7); ok = False
        for _ in range(8):
            cs = [Q(random.randrange(-40, 40)) for _ in B]
            v = [sum(c*b[k] for c, b in zip(cs, B)) for k in range(n)]
            if 0 not in v and len(set(v)) == n: ok = True; break
        if not ok: continue
        basis = [vec[head][:], vec[inp][:]]
        for t in range(d):
            cand = [Q(1) if u == t else Q(0) for u in range(d)]
            if len(nullspace(basis + [cand], d)) == d - len(basis) - 1: basis.append(cand)
            if len(basis) == d: break
        if len(basis) != d: continue
        inv = invert(basis, d)
        if inv is None: continue
        vec = {i: [sum(vec[i][t]*inv[t][u] for t in range(d)) for u in range(d)] for i in range(n)}
        L = 1
        for i in range(n):
            for t in range(d):
                L = L*vec[i][t].denominator//gcd(L, vec[i][t].denominator)
        iv = {i: tuple(int(vec[i][t]*L) for t in range(d)) for i in range(n)}
        key = tuple(sorted(iv.values()))
        if key in seen: continue          # same family, different bijection
        seen.add(key)
        sigs = []
        for trip in itertools.combinations(nonhead, 3):
            if any(sum(vec[i][t] for i in trip) for t in range(d)): continue
            rest = [i for i in nonhead if i not in trip]
            if len(rest) % 2: continue
            seenp, pairs, okp = set(), [], True
            for i in rest:
                if i in seenp: continue
                j = next((j for j in rest if j not in seenp and j != i and all(vec[i][t]+vec[j][t] == 0 for t in range(d))), None)
                if j is None: okp = False; break
                seenp |= {i, j}; pairs.append((names[i], names[j]))
            if not okp: continue
            r3 = [iv[i] for i in trip]
            minors = {}
            for p_, q_ in itertools.combinations(range(d), 2):
                minors[f"({p_},{q_})"] = r3[0][p_]*r3[1][q_] - r3[0][q_]*r3[1][p_]
            sigs.append({"token": [names[i] for i in trip], "token_rows": r3, "pairs": pairs, "minors": minors})
        out.append({"denominator": L, "params": d, "labels": {names[i]: iv[i] for i in range(n)},
                    "head": names[head], "input": names[inp], "signatures": sigs,
                    "perm": {T.outputs[k]["name"]: names[perm[k]] for k in range(n)}})
    return names, out

if __name__ == "__main__":
    res = {}
    for ctx, specs in [("h0_3_p0_act", ["arms=3;active;input"]),
                       ("h1_2_p0_act", ["head=1;arms=2;active;input"]),
                       ("h0_5_p0_act", ["arms=5;active;input"])]:
        names, fams = families(specs)
        res[ctx] = {"labels": names, "families": fams}
        print(f"## {ctx}: {len(fams)} distinct families; labels {names}")
        for f in fams:
            print(f"  L={f['denominator']} params={f['params']} labels={f['labels']}")
            for s in f["signatures"]:
                print(f"     token {s['token']} rows {s['token_rows']} minors {s['minors']} pairs {s['pairs']}")
    json.dump(res, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "blocked_families.json"), "w"), indent=1)
