"""Cyclic-Langford hypothesis for the clean tail [M+1,K], K-M=3t, n=2K+1:
differences D = [M+1, M+t] exactly (the t smallest), positions = [M+t+1, K];
each d in D gets a pair {p,q} of positions with q-p = d (type B) or p+q = n-d (type A).
Exact CP-SAT; '1' feasible, '.' infeasible, '?' timeout."""
from ortools.sat.python import cp_model
def cyc(M,K,tlim=12):
    t=(K-M)//3; n=2*K+1; D=range(M+1,M+t+1); pos=list(range(M+t+1,K+1)); P=set(pos)
    m=cp_model.CpModel(); var={}
    for d in D:
        for p in pos:
            for q in (p+d, n-d-p):
                if q in P and q>p: var[(d,p,q)]=m.NewBoolVar("")
    for d in D: m.Add(sum(x for k,x in var.items() if k[0]==d)==1)
    for p in pos: m.Add(sum(x for k,x in var.items() if p in k[1:])==1)
    s=cp_model.CpSolver(); s.parameters.max_time_in_seconds=tlim; s.parameters.num_search_workers=3
    r=s.Solve(m)
    return {cp_model.OPTIMAL:"1",cp_model.FEASIBLE:"1",cp_model.INFEASIBLE:"."}.get(r,"?")
for M in range(5,15):
    Ks=[K for K in range(3*M+1,7*M+7) if (K-M)%3==0]
    print(f"M={M:2d} K={Ks[0]:3d}..{Ks[-1]:3d} step3: {''.join(cyc(M,K) for K in Ks)}", flush=True)
