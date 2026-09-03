"""Punctured case as 'extra differences': available = J u [M+1,K], J subset [1,M].
Structure: differences D = J u [M+1, M+t'], positions [M+t'+1, K] with K-M-2|J| = 3t'.
Pairs: q-p = d or p+q = n-d.  Random J of each size; report feasibility."""
import random
from ortools.sat.python import cp_model
def feas(M,K,J,tlim=12):
    g=len(J); tp=(K-M-2*g)//3; n=2*K+1
    D=sorted(J)+list(range(M+1,M+tp+1)); pos=list(range(M+tp+1,K+1)); P=set(pos)
    m=cp_model.CpModel(); var={}
    for d in D:
        for p in pos:
            if p+d in P: var[(d,p,p+d)]=m.NewBoolVar("")
            q=n-d-p
            if q in P and q>p: var[(d,p,q)]=m.NewBoolVar("")
    for d in D: m.Add(sum(x for kk,x in var.items() if kk[0]==d)==1)
    for p in pos: m.Add(sum(x for kk,x in var.items() if p in kk[1:])==1)
    s=cp_model.CpSolver(); s.parameters.max_time_in_seconds=tlim; s.parameters.num_search_workers=2
    r=s.Solve(m)
    return {cp_model.OPTIMAL:"1",cp_model.FEASIBLE:"1",cp_model.INFEASIBLE:"."}.get(r,"?")
random.seed(11)
for M in (8,10,12):
    for K in (3*M+4, 4*M+1, 5*M+1, 6*M+1):
        res=""
        for g in range(1,M+1):
            # need K-M-2g = 0 mod 3: adjust by leaving out largest elements is NOT allowed here; skip mismatches
            if (K-M-2*g)%3: res+=" "; continue
            J=sorted(random.sample(range(1,M+1),g))
            res+=feas(M,K,J)
        print(f"M={M:2d} K={K:3d}: g=1..{M}: [{res}]", flush=True)
