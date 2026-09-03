"""Structured induction test: start from a PRODUCT solution (a=3 or 5) of FSP(ab, s0) and look for
solutions of neighbouring instances within small Hamming distance:
  (i)  (ab, s0+1) and (ab, s0-1), same rows/cols;
  (ii) (ab+1, s0) and (ab+2, s0): old rows keep their columns (+0 or +shift), new rows free.
Report the minimal k (<=6) for each neighbour."""
import sys
from ortools.sat.python import cp_model
def fsp(t,s,tlim=15):
    m=cp_model.CpModel(); pi=[m.NewIntVar(0,t-1,"") for _ in range(t)]; m.AddAllDifferent(pi)
    tau=[i+pi[i] for i in range(t)]
    for i in range(t):
        m.Add(tau[i]>=-s); m.Add(tau[i]<=2*t-1-s)
        for j in range(i+1,t): m.Add(tau[i]!=tau[j]); m.Add(tau[i]+tau[j]!=2*t-1-2*s)
    sol=cp_model.CpSolver(); sol.parameters.max_time_in_seconds=tlim; sol.parameters.num_search_workers=2
    r=sol.Solve(m); return [sol.Value(v) for v in pi] if r in (cp_model.OPTIMAL,cp_model.FEASIBLE) else None
def near(base,t2,s2,kmax=6,tlim=12):
    for k in range(kmax+1):
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
        if sol.Solve(m) in (cp_model.OPTIMAL,cp_model.FEASIBLE): return k
    return None
for a in (3,5):
    for b in range(4,9):
        for sp in range(-((b-1)//2),(b+1)//2+1):
            sig=fsp(b,sp)
            if sig is None: continue
            r=(a-1)//2; t=a*b; s0=a*(sp-1)+(a+1)//2
            prod=[a*sig[u]+((w+r)%a) for u in range(b) for w in range(a)]
            base={i:prod[i] for i in range(t)}
            res={}
            for ds in (-1,1):
                s2=s0+ds
                if -((t-1)//2)<=s2<=(t+1)//2: res[f"s{ds:+d}"]=near(base,t,s2)
            for dt in (1,2):
                res[f"t+{dt}"]=near(base,t+dt,s0)
                res[f"t+{dt},shift{dt}"]=near({i:v+dt for i,v in base.items()},t+dt,s0)
            print(f"a={a} b={b} s'={sp:3d} -> (t={t},s={s0:3d}): {res}", flush=True)
