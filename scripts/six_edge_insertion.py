#!/usr/bin/env python3
"""Search for the six-edge insertion identity used by the mod-six reduction.

An arm of an owner is a path v - u1 - ... - u_l - leaf with labels
a_0, ..., a_l; the outputs it contributes are a_0+a_1, ..., a_{l-1}+a_l and
a_l, and a_0 also enters the owner's sum.  The insertion replaces the arm by
one of length l+6 by putting six new labels b_1, ..., b_6 between a_0 and a_1.
For the cell to stay P=O the multiset

    {a_0+b_1, b_1+b_2, ..., b_5+b_6, b_6+a_1}

must equal {a_0+a_1} together with {b_1, ..., b_6}, and for the support to
stay closed under negation the six new labels must form three inverse pairs.

We look for b_i as integer forms  b_i = p_i*c + q_i*d + r_i*t  in the two
endpoint labels c = a_0, d = a_1 and one free parameter t, over a common
denominator L, with coefficients bounded.  A solution is a proof of the
insertion lemma for every arm and every cell at once, since the identity
involves only the two endpoint labels.

usage: six_edge_insertion.py [--coef 6] [--denominator 2] [--time 120]
"""
import argparse
import itertools
import json

from ortools.sat.python import cp_model


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--coef", type=int, default=6)
    ap.add_argument("--denominator", type=int, default=2)
    ap.add_argument("--time", type=float, default=120)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--json", default=None)
    ap.add_argument("--kind", choices=["arm", "port"], default="arm",
                    help="arm: insert between a_0 and a_1; port: lengthen a leaf edge to an arm of length six")
    a = ap.parse_args()
    L, K = a.denominator, a.coef
    m = cp_model.CpModel()
    n = 6
    # b_i = (p_i*c + q_i*d + r_i*t)/L
    p = [[m.NewIntVar(-K, K, f"p{i}{j}") for j in range(3)] for i in range(n)]
    # the six new labels are closed under negation: a fixed-point-free
    # involution y with b_i = -b_{y(i)}
    y = [[m.NewBoolVar(f"y{i}{k}") for k in range(n)] for i in range(n)]
    for i in range(n):
        m.Add(y[i][i] == 0)
        m.AddExactlyOne(y[i])
        m.AddExactlyOne(y[k][i] for k in range(n))
        for k in range(n):
            m.Add(y[i][k] == y[k][i])
            for j in range(3):
                m.Add(p[i][j] + p[k][j] == 0).OnlyEnforceIf(y[i][k])
    # labels are nonzero and pairwise distinct as forms
    for i in range(n):
        m.AddBoolOr([m.NewBoolVar("") for _ in range(0)] ) if False else None
    def nonzero(vec, tag):
        bs = []
        for j, v in enumerate(vec):
            b = m.NewBoolVar(f"{tag}nz{j}")
            m.Add(v != 0).OnlyEnforceIf(b)
            m.Add(v == 0).OnlyEnforceIf(b.Not())
            bs.append(b)
        m.AddBoolOr(bs)
    for i in range(n):
        nonzero(p[i], f"b{i}")
    for i in range(n):
        for k in range(i + 1, n):
            d = [m.NewIntVar(-2 * K, 2 * K, f"d{i}{k}{j}") for j in range(3)]
            for j in range(3):
                m.Add(d[j] == p[i][j] - p[k][j])
            nonzero(d, f"df{i}{k}")
    # the new labels must also differ from the endpoint labels they sit
    # between, since all labels of a cell are distinct
    ends = [[L, 0, 0]] + ([[0, L, 0]] if a.kind == "arm" else [])
    for i in range(n):
        for e, ev in enumerate(ends):
            d = [m.NewIntVar(-2 * K, 2 * K, f"e{i}{e}{j}") for j in range(3)]
            for j in range(3):
                m.Add(d[j] == p[i][j] - ev[j])
            nonzero(d, f"de{i}{e}")
    # c and d as forms: c = (L,0,0)/L, d = (0,L,0)/L
    C = [L, 0, 0]
    D = [0, L, 0]
    outs = [[C[j] + p[0][j] for j in range(3)]]
    for i in range(n - 1):
        outs.append([p[i][j] + p[i + 1][j] for j in range(3)])
    if a.kind == "arm":
        outs.append([p[n - 1][j] + D[j] for j in range(3)])
        targets = [[C[j] + D[j] for j in range(3)]] + [p[i] for i in range(n)]
    else:
        # a port: the old output is the port label itself, and the new arm
        # terminates at b_6
        outs.append([p[n - 1][j] for j in range(3)])
        targets = [list(C)] + [p[i] for i in range(n)]
    # a permutation matching outs to targets
    x = [[m.NewBoolVar(f"x{i}{k}") for k in range(n + 1)] for i in range(n + 1)]
    for i in range(n + 1):
        m.AddExactlyOne(x[i])
        m.AddExactlyOne(x[k][i] for k in range(n + 1))
    for i in range(n + 1):
        for k in range(n + 1):
            for j in range(3):
                m.Add(outs[i][j] == targets[k][j]).OnlyEnforceIf(x[i][k])
    s = cp_model.CpSolver()
    s.parameters.max_time_in_seconds = a.time
    s.parameters.num_search_workers = a.workers
    st = s.Solve(m)
    name = s.StatusName(st)
    print("status", name)
    if st in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        sym = []
        for i in range(n):
            co = [s.Value(p[i][j]) for j in range(3)]
            terms = []
            for j, v in zip("cdt", co):
                if v:
                    terms.append(f"{v}*{j}")
            sym.append("(" + " + ".join(terms) + f")/{L}")
        print("b =", sym)
        if a.json:
            json.dump({"status": name, "denominator": L,
                       "coefficients": [[s.Value(p[i][j]) for j in range(3)] for i in range(n)],
                       "forms": sym}, open(a.json, "w"), indent=1)
    return 0


if __name__ == "__main__":
    main()
