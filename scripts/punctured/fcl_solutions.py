"""Folded cyclic Langford FCL(M,t): differences [M+1,M+t], positions [M+t+1,K], K=M+3t, n=2K+1.
Print solutions at and near the threshold, with type-B count maximised and then minimised."""
from ortools.sat.python import cp_model
def fcl(M,K,maxB=True,tlim=30):
    t=(K-M)//3; n=2*K+1; D=range(M+1,M+t+1); pos=list(range(M+t+1,K+1)); P=set(pos)
    m=cp_model.CpModel(); var={}
    for d in D:
        for p in pos:
            if p+d in P: var[(d,p,p+d,'B')]=m.NewBoolVar("")
            q=n-d-p
            if q in P and q>p: var[(d,p,q,'A')]=m.NewBoolVar("")
    for d in D: m.Add(sum(x for k,x in var.items() if k[0]==d)==1)
    for p in pos: m.Add(sum(x for k,x in var.items() if p in k[1:3])==1)
    nb=sum(x for k,x in var.items() if k[3]=='B')
    (m.Maximize if maxB else m.Minimize)(nb)
    s=cp_model.CpSolver(); s.parameters.max_time_in_seconds=tlim; s.parameters.num_search_workers=4
    r=s.Solve(m)
    return sorted(k for k,x in var.items() if s.Value(x)) if r in (cp_model.OPTIMAL,cp_model.FEASIBLE) else None
for M in (7,10,13):
    for K in (3*M+1,3*M+4,3*M+7,3*M+10):
        for mx in (True,False):
            sol=fcl(M,K,mx)
            print(f"M={M} K={K} t={(K-M)//3} n={2*K+1} {'maxB' if mx else 'minB'}: {sol}")
