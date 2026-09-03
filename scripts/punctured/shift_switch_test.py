"""Induction step test: from a solution of FCL(M,K) (n=2K+1), shift positions by +3 (types preserved
with n'=n+6), then try to reach a solution of FCL(M,K+3) by re-pairing at most r old pairs together
with the two new positions M+t+2, M+t+3 and the new difference M+t+1.  Report the minimal r found."""
import random, itertools
from ortools.sat.python import cp_model
def fcl_any(M,K,seed,tlim=20):
    t=(K-M)//3; n=2*K+1; D=range(M+1,M+t+1); pos=list(range(M+t+1,K+1)); P=set(pos)
    m=cp_model.CpModel(); var={}
    for d in D:
        for p in pos:
            if p+d in P: var[(d,p,p+d)]=m.NewBoolVar("")
            q=n-d-p
            if q in P and q>p: var[(d,p,q)]=m.NewBoolVar("")
    for d in D: m.Add(sum(x for k,x in var.items() if k[0]==d)==1)
    for p in pos: m.Add(sum(x for k,x in var.items() if p in k[1:]) ==1)
    s=cp_model.CpSolver(); s.parameters.max_time_in_seconds=tlim; s.parameters.num_search_workers=2; s.parameters.random_seed=seed
    r=s.Solve(m)
    return [k for k,x in var.items() if s.Value(x)] if r in (cp_model.OPTIMAL,cp_model.FEASIBLE) else None
def min_switch(M,K,sol,rmax=3):
    t=(K-M)//3; K2=K+3; n2=2*K2+1; dnew=M+t+1; newpos=[M+t+2,M+t+3]
    shifted=[(d,p+3,q+3) for d,p,q in sol]
    # valid pairs under n2 for a difference d and positions set
    def ok(d,p,q): return q-p==d or p+q==n2-d
    for r in range(0,rmax+1):
        for chosen in itertools.combinations(range(len(shifted)),r):
            freeD=[dnew]+[shifted[i][0] for i in chosen]
            freeP=newpos+[v for i in chosen for v in shifted[i][1:]]
            # perfect matching of freeP into pairs realizing freeD (each once): brute force (small)
            def rec(ds,ps):
                if not ds: return True
                d=ds[0]
                for i in range(len(ps)):
                    for j in range(i+1,len(ps)):
                        p,q=sorted((ps[i],ps[j]))
                        if ok(d,p,q) and rec(ds[1:],[x for k,x in enumerate(ps) if k not in (i,j)]): return True
                return False
            if rec(freeD,freeP): return r
    return None
random.seed(3)
for M in (6,8,10):
    for K in [k for k in range(3*M+1,6*M) if (k-M)%3==0][:8]:
        res=[]
        for seed in range(3):
            sol=fcl_any(M,K,seed)
            res.append(min_switch(M,K,sol) if sol else 'nosol')
        print(f"M={M} K={K}->{K+3}: minimal switch sizes over 3 solutions: {res}", flush=True)
