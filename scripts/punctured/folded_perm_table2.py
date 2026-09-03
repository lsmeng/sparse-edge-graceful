"""Exact feasibility of folded sum permutations: permutation pi of [0,t-1], u_i=i+pi(i)+s,
k_i in {u_i, 2t-1+2e-u_i} a permutation of [0,t-1].  e in {0,1,2} is the number of unused
top elements (K-M = 3t+e).  Unbuffered output; one line per (e,t)."""
import sys
from ortools.sat.python import cp_model
def feas(t,s,e,tlim=6):
    m=cp_model.CpModel()
    pi=[m.NewIntVar(0,t-1,"") for _ in range(t)]; m.AddAllDifferent(pi)
    k=[m.NewIntVar(0,t-1,"") for _ in range(t)]; m.AddAllDifferent(k)
    for i in range(t):
        u=i+pi[i]+s; b=m.NewBoolVar("")
        m.Add(k[i]==u).OnlyEnforceIf(b); m.Add(k[i]==2*t-1+2*e-u).OnlyEnforceIf(b.Not())
    sol=cp_model.CpSolver(); sol.parameters.max_time_in_seconds=tlim; sol.parameters.num_search_workers=2
    r=sol.Solve(m)
    return {cp_model.OPTIMAL:"1",cp_model.FEASIBLE:"1",cp_model.INFEASIBLE:"."}.get(r,"?")
for e in (0,1,2):
    print(f"=== e={e}: columns s=-t..t+1, '|' marks s=(1-t)/2 (floor) and s=(t+1)/2 (floor) ===", flush=True)
    for t in range(3,31):
        row=""
        for s in range(-t,t+2):
            if s==-((t-1)//2): row+="|"
            row+=feas(t,s,e)
            if s==(t+1)//2: row+="|"
        print(f"t={t:2d}: {row}", flush=True)
