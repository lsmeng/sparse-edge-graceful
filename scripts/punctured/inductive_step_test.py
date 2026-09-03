"""Inductive-step test.  From a solution pi of FSP(t,s), look for pi' of the target instance
that differs from a canonical embedding of pi in at most k rows.
 (A) (t,s) -> (t+1,s+1): embed pi as is (rows/cols [0,t-1]); new row t free.
 (B) (t,s) -> (t+2,s):   embed pi shifted by 2 in columns (pi'(i)=pi(i)+2); new rows t,t+1 free.
Reports, over 3 random solutions per (t,s), the minimal k in {0,1,2,3,4} that works."""
import sys, random
from ortools.sat.python import cp_model
def fsp(t,s,seed,tlim=15):
    m=cp_model.CpModel(); pi=[m.NewIntVar(0,t-1,"") for _ in range(t)]; m.AddAllDifferent(pi)
    tau=[i+pi[i] for i in range(t)]
    for i in range(t):
        m.Add(tau[i]>=-s); m.Add(tau[i]<=2*t-1-s)
        for j in range(i+1,t): m.Add(tau[i]!=tau[j]); m.Add(tau[i]+tau[j]!=2*t-1-2*s)
    sol=cp_model.CpSolver(); sol.parameters.max_time_in_seconds=tlim; sol.parameters.num_search_workers=2; sol.parameters.random_seed=seed
    r=sol.Solve(m); return [sol.Value(v) for v in pi] if r in (cp_model.OPTIMAL,cp_model.FEASIBLE) else None
def extend(base,t2,s2,k,tlim=15):
    m=cp_model.CpModel(); pi=[m.NewIntVar(0,t2-1,"") for _ in range(t2)]; m.AddAllDifferent(pi)
    tau=[i+pi[i] for i in range(t2)]
    for i in range(t2):
        m.Add(tau[i]>=-s2); m.Add(tau[i]<=2*t2-1-s2)
        for j in range(i+1,t2): m.Add(tau[i]!=tau[j]); m.Add(tau[i]+tau[j]!=2*t2-1-2*s2)
    diff=[]
    for i,v in base.items():
        b=m.NewBoolVar(""); m.Add(pi[i]!=v).OnlyEnforceIf(b); m.Add(pi[i]==v).OnlyEnforceIf(b.Not()); diff.append(b)
    m.Add(sum(diff)<=k)
    sol=cp_model.CpSolver(); sol.parameters.max_time_in_seconds=tlim; sol.parameters.num_search_workers=2
    return sol.Solve(m) in (cp_model.OPTIMAL,cp_model.FEASIBLE)
random.seed(5)
for t in (8,10,12,14,16):
    for s in range(-((t-1)//2)+1,(t+1)//2):
        resA=[]; resB=[]
        for seed in range(3):
            pi=fsp(t,s,seed)
            if pi is None: resA.append("x"); resB.append("x"); continue
            baseA={i:pi[i] for i in range(t)}; kA=next((k for k in range(5) if extend(baseA,t+1,s+1,k)),None)
            baseB={i:pi[i]+2 for i in range(t)}; kB=next((k for k in range(5) if extend(baseB,t+2,s,k)),None)
            resA.append(kA); resB.append(kB)
        print(f"t={t:2d} s={s:3d}: A (t+1,s+1) min-k {resA} | B (t+2,s) shift2 min-k {resB}", flush=True)
