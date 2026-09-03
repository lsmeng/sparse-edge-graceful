"""Probe the linear punctured-interval conjecture beyond the exact audit box.

For I subseteq [1,M] and K, does [1,K] \ I contain floor((K-|I|)/3) disjoint
triples, each with a+b=c or a+b+c=2K+1?  CP-SAT, one boolean per admissible
triple.  Reports, for the hardest known witness I=[1,M], the last K that fails
in [2M, 5M]; and the failure rate over random I at K = 3M and K = 4M.
"""
import random, sys, itertools
from ortools.sat.python import cp_model

def pack(avail, K, need, tlim=20):
    n = 2*K+1; av = sorted(avail); S = set(av)
    tr = []
    for a, b in itertools.combinations(av, 2):
        c = a+b
        if c in S and c > b: tr.append((a, b, c))
        c = n-a-b
        if c in S and c > b: tr.append((a, b, c))
    m = cp_model.CpModel(); x = [m.NewBoolVar(f"t{i}") for i in range(len(tr))]
    by = {v: [] for v in av}
    for i, t in enumerate(tr):
        for v in t: by[v].append(x[i])
    for v in av: m.Add(sum(by[v]) <= 1)
    m.Add(sum(x) >= need)
    s = cp_model.CpSolver(); s.parameters.max_time_in_seconds = tlim; s.parameters.num_search_workers = 4
    r = s.Solve(m)
    return {cp_model.OPTIMAL: "SAT", cp_model.FEASIBLE: "SAT", cp_model.INFEASIBLE: "UNSAT"}.get(r, "UNKNOWN")

random.seed(1)
print("== hardest witness I=[1,M]: last failing K in [2M,5M] ==")
for M in range(6, 21, 2):
    last_bad = None; unknown = []
    for K in range(2*M, 5*M+1):
        avail = set(range(M+1, K+1)); need = (K-M)//3
        v = pack(avail, K, need, tlim=15)
        if v == "UNSAT": last_bad = K
        elif v == "UNKNOWN": unknown.append(K)
    print(f"M={M:2d}: last bad K={last_bad}  (ratio {None if last_bad is None else round(last_bad/M,2)})  unknown={unknown[:5]}", flush=True)
print("== random I subseteq [1,M], failure counts out of 60 at K=3M and K=4M ==")
for M in (8, 12, 16):
    for K in (3*M, 4*M):
        bad = unk = 0
        for _ in range(60):
            I = {i for i in range(1, M+1) if random.random() < 0.5}
            avail = set(range(1, K+1)) - I; need = (K-len(I))//3
            v = pack(avail, K, need, tlim=15)
            bad += v == "UNSAT"; unk += v == "UNKNOWN"
        print(f"M={M:2d} K={K:3d}: UNSAT {bad}/60, UNKNOWN {unk}/60", flush=True)
