"""Closest-to-identity solutions: minimise the number of non-fixed points of pi, for s>=1
(the s<=-1 side is the mirror image).  Prints the non-fixed rows as i->pi(i) with sums, so the
'surgery' attached to the forced top sums [2t', 2t'+s-1] (t'=t-s) can be read off."""
import sys
from ortools.sat.python import cp_model
def solve(t,s,tlim):
    m=cp_model.CpModel()
    pi=[m.NewIntVar(0,t-1,"") for _ in range(t)]; m.AddAllDifferent(pi)
    tau=[i+pi[i] for i in range(t)]
    for i in range(t):
        m.Add(tau[i]>=-s); m.Add(tau[i]<=2*t-1-s)
        for j in range(i+1,t): m.Add(tau[i]!=tau[j]); m.Add(tau[i]+tau[j]!=2*t-1-2*s)
    nf=[]
    for i in range(t):
        b=m.NewBoolVar(""); m.Add(pi[i]!=i).OnlyEnforceIf(b); m.Add(pi[i]==i).OnlyEnforceIf(b.Not()); nf.append(b)
    m.Minimize(sum(nf))
    sol=cp_model.CpSolver(); sol.parameters.max_time_in_seconds=tlim; sol.parameters.num_search_workers=3
    r=sol.Solve(m)
    if r not in (cp_model.OPTIMAL,cp_model.FEASIBLE): return None
    P=[sol.Value(v) for v in pi]
    moved=[(i,P[i],i+P[i]) for i in range(t) if P[i]!=i]
    return sol.Value(sum(nf)), r==cp_model.OPTIMAL, moved
ts=[int(x) for x in sys.argv[1].split(",")]; tlim=float(sys.argv[2])
for t in ts:
    for s in range(1,(t+1)//2+1):
        r=solve(t,s,tlim)
        if r is None: print(f"t={t} s={s}: none", flush=True); continue
        n,opt,mv=r; print(f"t={t:2d} s={s:2d} t'={t-s:2d}: moved={n:2d}{'*' if opt else ' '} {mv}", flush=True)
