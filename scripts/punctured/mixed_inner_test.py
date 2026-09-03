"""Block structure with ARBITRARY inner permutations: rows cut into consecutive blocks with sizes from a
set SZ (composition chosen by the solver via boundary booleans is hard; instead enumerate compositions
with sizes in SZ, few of them for t<=24), columns use the same block partition, sigma maps blocks to
same-size blocks, inner maps free.  Reports feasibility per (t,s) for SZ in {(3,4),(3,5),(4,5),(3,4,5)}."""
import sys, itertools
from ortools.sat.python import cp_model
def comps(t,SZ):
    out=[]
    def rec(rem,cur):
        if rem==0: out.append(tuple(cur)); return
        for a in SZ:
            if a<=rem: rec(rem-a,cur+[a])
    rec(t,[]); return out
def feas(t,s,comp,tlim=6):
    m=cp_model.CpModel(); nb=len(comp); st=[sum(comp[:k]) for k in range(nb)]
    pi=[m.NewIntVar(0,t-1,"") for _ in range(t)]; m.AddAllDifferent(pi)
    sig=[m.NewIntVar(0,nb-1,"") for _ in range(nb)]; m.AddAllDifferent(sig)
    for u in range(nb):
        for v in range(nb):
            if comp[u]!=comp[v]: m.Add(sig[u]!=v)
        tgt=m.NewIntVar(0,t,""); m.AddElement(sig[u],st,tgt)
        for w in range(comp[u]):
            m.Add(pi[st[u]+w]>=tgt); m.Add(pi[st[u]+w]<=tgt+comp[u]-1)
    tau=[i+pi[i] for i in range(t)]
    for i in range(t):
        m.Add(tau[i]>=-s); m.Add(tau[i]<=2*t-1-s)
        for j in range(i+1,t): m.Add(tau[i]!=tau[j]); m.Add(tau[i]+tau[j]!=2*t-1-2*s)
    sol=cp_model.CpSolver(); sol.parameters.max_time_in_seconds=tlim; sol.parameters.num_search_workers=2
    return sol.Solve(m) in (cp_model.OPTIMAL,cp_model.FEASIBLE)
for SZ in ((3,4),(3,5),(4,5),(3,4,5)):
    print(f"=== sizes {SZ} ===", flush=True)
    for t in range(10,25):
        lo=-((t-1)//2); hi=(t+1)//2; row=""
        cs=comps(t,SZ)
        if not cs: print(f"t={t}: no composition"); continue
        for s in range(lo,hi+1):
            ok=any(feas(t,s,c) for c in cs[:12])   # first 12 compositions
            row+="1" if ok else "."
        print(f"t={t:2d} s in [{lo},{hi}]: {row}", flush=True)
