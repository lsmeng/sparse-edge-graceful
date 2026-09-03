"""Is a folded sum permutation with |pi(i)-i| <= w always available inside the window
s in [(1-t)/2, (t+1)/2]?  Tests w=1,2,3 for t<=24 (e=0).  Prints, per t, the s-values in the
window that FAIL under the locality restriction (and which are infeasible even unrestricted)."""
from ortools.sat.python import cp_model
def feas(t,s,w=None,tlim=6):
    m=cp_model.CpModel()
    pi=[m.NewIntVar(max(0,i-w) if w is not None else 0, min(t-1,i+w) if w is not None else t-1,"") for i in range(t)]
    m.AddAllDifferent(pi)
    k=[m.NewIntVar(0,t-1,"") for _ in range(t)]; m.AddAllDifferent(k)
    for i in range(t):
        u=i+pi[i]+s; b=m.NewBoolVar("")
        m.Add(k[i]==u).OnlyEnforceIf(b); m.Add(k[i]==2*t-1-u).OnlyEnforceIf(b.Not())
    sol=cp_model.CpSolver(); sol.parameters.max_time_in_seconds=tlim; sol.parameters.num_search_workers=2
    r=sol.Solve(m)
    return {cp_model.OPTIMAL:"1",cp_model.FEASIBLE:"1",cp_model.INFEASIBLE:"."}.get(r,"?")
for t in range(5,25):
    lo=-((t-1)//2); hi=(t+1)//2
    out=[]
    for w in (1,2,3):
        bad=[s for s in range(lo,hi+1) if feas(t,s,w)!="1"]
        out.append(f"w={w}: fail at s={bad}")
    unr=[s for s in range(lo,hi+1) if feas(t,s,None)!="1"]
    print(f"t={t:2d} window s in [{lo},{hi}]  " + "  ".join(out) + f"   unrestricted fail: {unr}", flush=True)
