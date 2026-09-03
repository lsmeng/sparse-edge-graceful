"""Generalised product: consecutive blocks of sizes a or a+1 (a odd), the same partition for rows
and columns, sigma permutes blocks within each size class, each block mapped by a rotation
(any amount).  Exact feasibility over the window; a in {3,5}."""
from ortools.sat.python import cp_model
def feas(t,a,s,tlim=15):
    # number of (a+1)-blocks: t = a*nb + x  ->  x blocks of size a+1, nb-x of size a  (0<=x<nb)
    nb=t//a; x=t-a*nb
    if x>=nb: return "-"
    sizes=[a+1]*x+[a]*(nb-x); starts=[sum(sizes[:k]) for k in range(nb)]
    m=cp_model.CpModel()
    sig=[m.NewIntVar(0,nb-1,"") for _ in range(nb)]; m.AddAllDifferent(sig)
    for u in range(nb):
        for v in range(nb):
            if sizes[u]!=sizes[v]: m.Add(sig[u]!=v)
    rot=[m.NewIntVar(0,a,"") for _ in range(nb)]
    pi=[m.NewIntVar(0,t-1,"") for _ in range(t)]
    for u in range(nb):
        L=sizes[u]; m.Add(rot[u]<=L-1)
        for w in range(L):
            i=starts[u]+w
            tgt=m.NewIntVar(0,t-1,"")   # start of block sig(u)
            m.AddElement(sig[u],starts,tgt)
            wrap=m.NewBoolVar("")
            m.Add(w+rot[u]<=L-1).OnlyEnforceIf(wrap.Not()); m.Add(w+rot[u]>=L).OnlyEnforceIf(wrap)
            m.Add(pi[i]==tgt+w+rot[u]).OnlyEnforceIf(wrap.Not()); m.Add(pi[i]==tgt+w+rot[u]-L).OnlyEnforceIf(wrap)
    m.AddAllDifferent(pi)
    tau=[i+pi[i] for i in range(t)]
    for i in range(t):
        m.Add(tau[i]>=-s); m.Add(tau[i]<=2*t-1-s)
        for j in range(i+1,t): m.Add(tau[i]!=tau[j]); m.Add(tau[i]+tau[j]!=2*t-1-2*s)
    sol=cp_model.CpSolver(); sol.parameters.max_time_in_seconds=tlim; sol.parameters.num_search_workers=2
    r=sol.Solve(m); return {cp_model.OPTIMAL:"1",cp_model.FEASIBLE:"1",cp_model.INFEASIBLE:"."}.get(r,"?")
for t in range(10,31):
    lo=-((t-1)//2); hi=(t+1)//2
    for a in (3,5):
        row="".join(feas(t,a,s) for s in range(lo,hi+1))
        print(f"t={t:2d} a={a} s in [{lo},{hi}]: {row}", flush=True)
