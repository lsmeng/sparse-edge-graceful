"""Block-product template: t = a*b; index i = a*u + w (u in [0,b-1] block, w in [0,a-1] offset).
pi(a*u+w) = a*sigma(u) + ((w + r_u) mod a): block u goes to block sigma(u) with an internal rotation r_u.
Sums: a*(u+sigma(u)) + (w + (w+r_u mod a)).  Exact feasibility over the window for several factorisations."""
import sys
from ortools.sat.python import cp_model
def feas(t,a,s,tlim=15):
    b=t//a; m=cp_model.CpModel()
    sig=[m.NewIntVar(0,b-1,"") for _ in range(b)]; m.AddAllDifferent(sig)
    rot=[m.NewIntVar(0,a-1,"") for _ in range(b)]
    pi=[m.NewIntVar(0,t-1,"") for _ in range(t)]
    for u in range(b):
        for w in range(a):
            i=a*u+w
            # (w + rot) mod a  ->  w+rot or w+rot-a
            wrap=m.NewBoolVar("")
            m.Add(w+rot[u]<=a-1).OnlyEnforceIf(wrap.Not()); m.Add(w+rot[u]>=a).OnlyEnforceIf(wrap)
            m.Add(pi[i]==a*sig[u]+w+rot[u]).OnlyEnforceIf(wrap.Not())
            m.Add(pi[i]==a*sig[u]+w+rot[u]-a).OnlyEnforceIf(wrap)
    m.AddAllDifferent(pi)
    tau=[i+pi[i] for i in range(t)]
    for i in range(t):
        m.Add(tau[i]>=-s); m.Add(tau[i]<=2*t-1-s)
        for j in range(i+1,t): m.Add(tau[i]!=tau[j]); m.Add(tau[i]+tau[j]!=2*t-1-2*s)
    sol=cp_model.CpSolver(); sol.parameters.max_time_in_seconds=tlim; sol.parameters.num_search_workers=2
    r=sol.Solve(m)
    return {cp_model.OPTIMAL:"1",cp_model.FEASIBLE:"1",cp_model.INFEASIBLE:"."}.get(r,"?")
for t,a in ((15,3),(15,5),(21,3),(21,7),(25,5),(27,3),(27,9),(35,5),(35,7),(33,3),(33,11)):
    lo=-((t-1)//2); hi=(t+1)//2
    row="".join(feas(t,a,s) for s in range(lo,hi+1))
    print(f"t={t:2d} a={a:2d} b={t//a:2d} s in [{lo},{hi}]: {row}", flush=True)
