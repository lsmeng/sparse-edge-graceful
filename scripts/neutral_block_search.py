#!/usr/bin/env python3
"""Search for a neutral arm block that can be adjoined to any family.

A block is a set of arms of lengths ell_1..ell_k hanging off an owner.  Arm r
contributes labels a^r_0..a^r_{ell_r} and outputs a^r_0+a^r_1, ...,
a^r_{ell_r-1}+a^r_{ell_r}, a^r_{ell_r}; the label a^r_0 also enters the
owner's output.  The block is *neutral* when

  (i)  sum_r a^r_0 = 0,                         (the owner output is unchanged)
  (ii) multiset(labels) = multiset(outputs),    (P = O is preserved)
  (iii) the labels are closed under negation,   (mirror pairs; the signature)
  (iv) the labels are nonzero and pairwise distinct.

Every label is written over fresh parameters, so distinctness from the labels
of the host family is automatic and a solution proves the adjunction lemma
for every context at once.

usage: neutral_block_search.py --arms 1,3 [--params 2] [--coef 8] [--time 60]
"""
import argparse
import json

from ortools.sat.python import cp_model


def build(arms, npar, K, ports=0, token=False):
    m = cp_model.CpModel()
    lab, out = [], []
    firsts = []
    for i in range(ports):
        q = [m.NewIntVar(-K, K, f"q{i}_{j}") for j in range(npar)]
        lab.append(q)
        out.append(q)          # a port label is its own leaf output
        firsts.append(q)       # and it enters the owner sum
    for r, ell in enumerate(arms):
        row = [[m.NewIntVar(-K, K, f"a{r}_{i}_{j}") for j in range(npar)]
               for i in range(ell + 1)]
        lab.extend(row)
        firsts.append(row[0])
        for i in range(ell):
            out.append([row[i][j] + row[i + 1][j] for j in range(npar)])
        out.append(row[ell])
    n = len(lab)
    # (i) the owner contribution of the block cancels
    for j in range(npar):
        m.Add(sum(f[j] for f in firsts) == 0)
    # (iv) nonzero and pairwise distinct
    def nonzero(vec, tag):
        bs = []
        for j, v in enumerate(vec):
            b = m.NewBoolVar(f"{tag}_{j}")
            m.Add(v != 0).OnlyEnforceIf(b)
            m.Add(v == 0).OnlyEnforceIf(b.Not())
            bs.append(b)
        m.AddBoolOr(bs)
    for i in range(n):
        nonzero(lab[i], f"nz{i}")
    for i in range(n):
        for k in range(i + 1, n):
            d = [m.NewIntVar(-2 * K, 2 * K, f"d{i}_{k}_{j}") for j in range(npar)]
            for j in range(npar):
                m.Add(d[j] == lab[i][j] - lab[k][j])
            nonzero(d, f"ds{i}_{k}")
    # (iii) a fixed-point-free involution pairing labels to their negatives.
    # With --token three of the labels instead form a triple summing to zero,
    # which the host family may adopt as its token (it must then have none of
    # its own, or room for a second).
    tb = [m.NewBoolVar(f"tok{i}") for i in range(n)]
    if token:
        m.Add(sum(tb) == 3)
        # name the three token labels, so that the triple can be required to
        # sum to zero and to span a plane (the checker demands both)
        sel = [[m.NewBoolVar(f"sel{r}_{i}") for i in range(n)] for r in range(3)]
        T = [[m.NewIntVar(-K, K, f"T{r}_{j}") for j in range(npar)] for r in range(3)]
        for r in range(3):
            m.AddExactlyOne(sel[r])
            for i in range(n):
                for j in range(npar):
                    m.Add(T[r][j] == lab[i][j]).OnlyEnforceIf(sel[r][i])
        for i in range(n):
            m.Add(sum(sel[r][i] for r in range(3)) == tb[i])
        for j in range(npar):
            m.Add(sum(T[r][j] for r in range(3)) == 0)
        if npar >= 2:
            pr = []
            for (x, y0), (z, w) in (((0, 0), (1, 1)), ((0, 1), (1, 0))):
                v = m.NewIntVar(-K * K, K * K, f"det{x}{y0}")
                m.AddMultiplicationEquality(v, [T[x][y0], T[z][w]])
                pr.append(v)
            m.Add(pr[0] - pr[1] != 0)
    else:
        for i in range(n):
            m.Add(tb[i] == 0)
    y = [[m.NewBoolVar(f"y{i}_{k}") for k in range(n)] for i in range(n)]
    for i in range(n):
        m.Add(y[i][i] == 0)
        m.Add(sum(y[i]) == 1 - tb[i])
        m.Add(sum(y[k][i] for k in range(n)) == 1 - tb[i])
        for k in range(n):
            m.Add(y[i][k] == y[k][i])
            for j in range(npar):
                m.Add(lab[i][j] + lab[k][j] == 0).OnlyEnforceIf(y[i][k])
    # (ii) a permutation matching every output to a label
    z = [[m.NewBoolVar(f"z{i}_{k}") for k in range(n)] for i in range(n)]
    for i in range(n):
        m.AddExactlyOne(z[i])
        m.AddExactlyOne(z[k][i] for k in range(n))
        for k in range(n):
            for j in range(npar):
                m.Add(out[i][j] == lab[k][j]).OnlyEnforceIf(z[i][k])
    # break the scaling symmetry: the first label of arm 0 is positive on some coord
    m.Add(sum(lab[0][j] for j in range(npar)) >= 1)
    return m, lab, out, tb


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", default="")
    ap.add_argument("--ports", type=int, default=0)
    ap.add_argument("--token", action="store_true",
                    help="allow three labels to form a token triple instead of mirror pairs")
    ap.add_argument("--params", type=int, default=2)
    ap.add_argument("--coef", type=int, default=8)
    ap.add_argument("--time", type=float, default=60)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    arms = [int(x) for x in a.arms.split(",") if x.strip()]
    m, lab, out, tb = build(arms, a.params, a.coef, a.ports, a.token)
    s = cp_model.CpSolver()
    s.parameters.max_time_in_seconds = a.time
    s.parameters.num_search_workers = a.workers
    r = s.Solve(m)
    name = s.StatusName(r)
    res = {"arms": arms, "ports": a.ports, "params": a.params, "coef": a.coef,
           "token": a.token, "status": name}
    if r in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        res["labels"] = [[s.Value(v) for v in row] for row in lab]
        res["outputs"] = [[s.Value(v) for v in row] for row in out]
        res["token_positions"] = [i for i in range(len(tb)) if s.Value(tb[i])]
    print(json.dumps(res))
    if a.json:
        json.dump(res, open(a.json, "w"), indent=1)


if __name__ == "__main__":
    main()
