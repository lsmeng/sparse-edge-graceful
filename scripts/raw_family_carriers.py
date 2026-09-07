#!/usr/bin/env python3
"""Enumerate every P=O family of a small cell and report its safe carriers.

The catalogue is built by a CP-SAT search over one fixed signature, and twice
now that signature has been found to miss families that exist: the residue-two
ray, and the joint of two direct-edge two-input rows.  For the few contexts
where the catalogue's families all have their token spanning a plane on the
head and the input alone, it is therefore worth asking the question directly.

For a cell of small width this program enumerates every bijection between the
labels and the outputs, solves P = O exactly, keeps the solutions whose labels
are distinct and nonzero at a generic point, and then, for each of them, looks
for a signature of the manuscript's shape: one zero-sum triple among the
non-head labels (the token), the rest in mirror pairs.  It reports whether any
such token admits a carrier that is unimodular, or that avoids the head, which
are the two ways Remark rem:integrality is discharged.

usage: raw_family_carriers.py "arms=3;active;input" [more specs ...]
"""
import itertools
import json
import os
import random
import sys
from fractions import Fraction as Q
from math import gcd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import symbolic_free_token_cpsat as sc  # noqa: E402


def invert(rows, n):
    """Exact inverse of an n x n rational matrix, or None if singular."""
    m = [list(r) + [Q(1) if i == j else Q(0) for j in range(n)]
         for i, r in enumerate(rows)]
    for c in range(n):
        p = next((i for i in range(c, n) if m[i][c]), None)
        if p is None:
            return None
        m[c], m[p] = m[p], m[c]
        pv = m[c][c]
        m[c] = [a / pv for a in m[c]]
        for i in range(n):
            if i != c and m[i][c]:
                f = m[i][c]
                m[i] = [a - f * b for a, b in zip(m[i], m[c])]
    return [r[n:] for r in m]


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


def analyse(specs, limit_report=3, shard=0, shards=1):
    """Every P=O family of the cell, tested for a safe carrier.

    The carrier determinant is not invariant under a change of parameter basis,
    so the test is applied only after the family has been written over the
    basis the catalogue uses, namely the exposed head as ``y``, the pinned input
    as ``x``, and internal parameters after them.  Testing it on an arbitrary
    nullspace basis, as an earlier version of this program did, measures
    nothing.
    """
    T = sc.Topology([sc.parse_row(s) for s in specs])
    n = len(T.labels)
    names = [l["name"] for l in T.labels]
    kinds = [l["kind"] for l in T.labels]
    A = [[Q(1) if i in set(o["terms"]) else Q(0) for i in range(n)]
         for o in T.outputs]
    head = next((i for i, k in enumerate(kinds) if k == "head"), None)
    inp = next((i for i, k in enumerate(kinds) if k == "input"), None)
    nonhead = [i for i in range(n) if i != head]
    fams = safe = rebased = 0
    best, record = [], None
    for _pi, perm in enumerate(itertools.permutations(range(n))):
        if shards > 1 and _pi % shards != shard:
            continue
        rows = [[A[k][c] - (Q(1) if c == perm[k] else Q(0)) for c in range(n)]
                for k in range(n)]
        B = nullspace(rows, n)
        d = len(B)
        if d < 2:
            continue
        vec = {k: [B[t][k] for t in range(d)] for k in range(n)}
        random.seed(7)
        ok = False
        for _ in range(8):
            cs = [Q(random.randrange(-40, 40)) for _ in B]
            v = [sum(c * b[k] for c, b in zip(cs, B)) for k in range(n)]
            if 0 not in v and len(set(v)) == n:
                ok = True
                break
        if not ok:
            continue
        fams += 1
        if head is None or inp is None:
            continue
        basis = [vec[head][:], vec[inp][:]]
        for t in range(d):
            cand = [Q(1) if u == t else Q(0) for u in range(d)]
            if len(nullspace(basis + [cand], d)) == d - len(basis) - 1:
                basis.append(cand)
            if len(basis) == d:
                break
        if len(basis) != d:
            continue
        inv = invert(basis, d)
        if inv is None:
            continue
        vec = {i: [sum(vec[i][t] * inv[t][u] for t in range(d)) for u in range(d)]
               for i in range(n)}
        rebased += 1
        for trip in itertools.combinations(nonhead, 3):
            if any(sum(vec[i][t] for i in trip) for t in range(d)):
                continue
            rest = [i for i in nonhead if i not in trip]
            if len(rest) % 2:
                continue
            mp, mpi, seen, pairs_ok = [], [], set(), True
            for i in rest:
                if i in seen:
                    continue
                j = next((j for j in rest if j not in seen and j != i
                          and all(vec[i][t] + vec[j][t] == 0 for t in range(d))), None)
                if j is None:
                    pairs_ok = False
                    break
                seen.add(i)
                seen.add(j)
                mp.append([names[i], names[j]])
                mpi.append([i, j])
            if not pairs_ok:
                continue
            L = 1
            for i in range(n):
                for t in range(d):
                    L = L * vec[i][t].denominator // gcd(L, vec[i][t].denominator)
            iv = {i: [int(vec[i][t] * L) for t in range(d)] for i in range(n)}
            r3 = [iv[i] for i in trip]
            uni = hf = False
            for p_, q_ in itertools.combinations(range(d), 2):
                det = r3[0][p_] * r3[1][q_] - r3[0][q_] * r3[1][p_]
                if not det:
                    continue
                if abs(det) == 1:
                    uni = True
                if 0 not in (p_, q_):          # parameter 0 is the head y
                    hf = True
            if not (uni or hf):
                continue
            safe += 1
            if len(best) < limit_report:
                best.append({"token": [names[i] for i in trip],
                             "unimodular": uni, "head_free": hf,
                             "parameters": d, "denominator": L})
            if record is None:
                record = {
                    "parameters": ["y", "x"] + [f"u{t}" for t in range(1, d - 1)],
                    "denominator": L,
                    "labels": [dict(T.labels[i]) for i in range(n)],
                    "coefficients_by_label": {names[i]: iv[i] for i in range(n)},
                    "mirror_pairs": mpi, "mirror_pairs_named": mp,
                    "token": True, "token_rank": "any2",
                    "token_indices": {"a": trip[0], "b": trip[1], "c": trip[2]},
                    "token_named": {"a": names[trip[0]], "b": names[trip[1]],
                                    "c": names[trip[2]]},
                    "width": n, "row_specs": [dict(r) for r in T.rows],
                    "permutation_named": {T.outputs[k]["name"]: names[perm[k]]
                                          for k in range(n)},
                    "status": "ENUMERATED",
                }
            break
    return {"specs": specs, "labels": names, "families": fams,
            "rebased": rebased, "families_with_a_safe_token": safe,
            "examples": best, "record": record}


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--emit")]
    emit = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--emit=")), None)
    r = analyse(args)
    print(f"specs {r['specs']}: {len(r['labels'])} labels")
    print(f"  nondegenerate P=O families      : {r['families']}")
    print(f"  writable over (y, x, u...)      : {r['rebased']}")
    print(f"  with a safe token (unimodular or head-free carrier): "
          f"{r['families_with_a_safe_token']}")
    for e in r["examples"]:
        print("   ", json.dumps(e))
    if emit and r.get("record"):
        json.dump(r["record"], open(emit, "w"))
        print(f"  wrote a safe family to {emit}")
