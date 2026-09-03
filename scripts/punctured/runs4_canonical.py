"""Canonical parity-interleaved solutions: each parity class of rows is split into at most 4
contiguous runs with constant shift v (pi(i)=i+v).  Objective: lexicographic-ish canonical form via
minimising sum |v| then number of runs, to make solutions comparable across (t,s).
Prints, per (t,s): even-class runs [(start,len,shift)], odd-class runs."""
import sys
from ortools.sat.python import cp_model
def solve(t,s,B=4,tlim=30):
    m=cp_model.CpModel()
    pi=[m.NewIntVar(0,t-1,"") for _ in range(t)]; m.AddAllDifferent(pi)
    tau=[i+pi[i] for i in range(t)]
    for i in range(t):
        m.Add(tau[i]>=-s); m.Add(tau[i]<=2*t-1-s)
        for j in range(i+1,t): m.Add(tau[i]!=tau[j]); m.Add(tau[i]+tau[j]!=2*t-1-2*s)
    absv=[]
    for p in (0,1):
        idx=list(range(p,t,2)); n=len(idx)
        ch=[]
        for q in range(n-1):
            b=m.NewBoolVar(""); m.Add(pi[idx[q+1]]-idx[q+1]!=pi[idx[q]]-idx[q]).OnlyEnforceIf(b); m.Add(pi[idx[q+1]]-idx[q+1]==pi[idx[q]]-idx[q]).OnlyEnforceIf(b.Not()); ch.append(b)
        m.Add(sum(ch)<=B-1)
        for i in idx:
            a=m.NewIntVar(0,t,""); m.AddAbsEquality(a,pi[i]-i); absv.append(a)
    m.Minimize(sum(absv))
    sol=cp_model.CpSolver(); sol.parameters.max_time_in_seconds=tlim; sol.parameters.num_search_workers=2
    r=sol.Solve(m)
    if r not in (cp_model.OPTIMAL,cp_model.FEASIBLE): return None
    P=[sol.Value(v) for v in pi]
    out=[]
    for p in (0,1):
        idx=list(range(p,t,2)); runs=[]
        for i in idx:
            v=P[i]-i
            if runs and runs[-1][2]==v: runs[-1][1]+=1
            else: runs.append([i,1,v])
        out.append([tuple(x) for x in runs])
    return out, r==cp_model.OPTIMAL
ts=[int(x) for x in sys.argv[1].split(",")]
for t in ts:
    for s in range(-((t-1)//2),(t+1)//2+1):
        r=solve(t,s)
        print(f"t={t:2d} s={s:3d}: "+("none" if r is None else f"even={r[0][0]} odd={r[0][1]}{'' if r[1] else ' (not proved optimal)'}"), flush=True)
