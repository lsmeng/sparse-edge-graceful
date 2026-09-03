"""Bipartite FCL hypothesis: differences D=[M+1,M+t], lower positions L=[M+t+1,M+2t], upper U=[M+2t+1,K];
each d takes one p in L and one q in U with q-p=d or p+q=n-d.   Also the rigid 'natural order' family
p_i = M+t+1+i for d_i = M+1+i (only the type is free).  '1' feasible, '.' infeasible, '?' timeout."""
from ortools.sat.python import cp_model
def bip(M,K,natural=False,tlim=12):
    t=(K-M)//3; n=2*K+1; D=list(range(M+1,M+t+1)); L=list(range(M+t+1,M+2*t+1)); U=set(range(M+2*t+1,K+1))
    m=cp_model.CpModel(); var={}
    for i,d in enumerate(D):
        for p in (L if not natural else [M+t+1+i]):
            for q in (p+d, n-d-p):
                if q in U: var[(d,p,q)]=m.NewBoolVar("")
    for d in D: m.Add(sum(x for k,x in var.items() if k[0]==d)==1)
    for p in L: m.Add(sum(x for k,x in var.items() if k[1]==p)==1)
    for q in U: m.Add(sum(x for k,x in var.items() if k[2]==q)==1)
    s=cp_model.CpSolver(); s.parameters.max_time_in_seconds=tlim; s.parameters.num_search_workers=3
    r=s.Solve(m)
    return {cp_model.OPTIMAL:"1",cp_model.FEASIBLE:"1",cp_model.INFEASIBLE:"."}.get(r,"?")
print("bipartite (p in lower half, q in upper half):")
for M in range(5,17):
    Ks=[K for K in range(3*M+1,7*M+7) if (K-M)%3==0]
    print(f"  M={M:2d} K={Ks[0]:3d}..{Ks[-1]:3d}: {''.join(bip(M,K) for K in Ks)}", flush=True)
print("natural order p_i=M+t+1+i (type free):")
for M in range(5,17):
    Ks=[K for K in range(3*M+1,7*M+7) if (K-M)%3==0]
    row="".join(bip(M,K,natural=True) for K in Ks)
    print(f"  M={M:2d} K={Ks[0]:3d}..{Ks[-1]:3d}: {row}   feasible K: {[K for K,c in zip(Ks,row) if c=='1']}", flush=True)
