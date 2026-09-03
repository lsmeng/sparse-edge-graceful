"""Template discovery for FSP(t,s).  Minimise the number of 'runs': positions i where the shift
v_i = pi(i)-i differs from v_{i+2} (runs within each parity class), i.e. Simpson-style interleaved
arithmetic families.  Also asserts the forced-sums fact:
  s>=1 : T contains 2t-2s..2t-1-s ;  s<=-1 : T contains |s|..2|s|.
Prints per (t,s): min runs, the shift sequence by parity class, and the run decomposition."""
import sys
from ortools.sat.python import cp_model
def solve(t,s,tlim):
    m=cp_model.CpModel()
    pi=[m.NewIntVar(0,t-1,"") for _ in range(t)]; m.AddAllDifferent(pi)
    tau=[i+pi[i] for i in range(t)]
    for i in range(t):
        m.Add(tau[i]>=-s); m.Add(tau[i]<=2*t-1-s)
        for j in range(i+1,t):
            m.Add(tau[i]!=tau[j]); m.Add(tau[i]+tau[j]!=2*t-1-2*s)
    ch=[]
    for i in range(t-2):
        b=m.NewBoolVar(""); m.Add(pi[i+2]-(i+2)!=pi[i]-i).OnlyEnforceIf(b); m.Add(pi[i+2]-(i+2)==pi[i]-i).OnlyEnforceIf(b.Not()); ch.append(b)
    m.Minimize(sum(ch))
    sol=cp_model.CpSolver(); sol.parameters.max_time_in_seconds=tlim; sol.parameters.num_search_workers=3
    r=sol.Solve(m)
    if r not in (cp_model.OPTIMAL,cp_model.FEASIBLE): return None
    P=[sol.Value(v) for v in pi]; T=[i+P[i] for i in range(t)]
    if s>=1: assert all(x in T for x in range(2*t-2*s,2*t-s)), "forced top sums violated"
    if s<=-1: assert all(x in T for x in range(-s,-2*s+1)), "forced bottom sums violated"
    v=[P[i]-i for i in range(t)]
    def runs(seq):
        out=[]; 
        for x in seq:
            if out and out[-1][0]==x: out[-1][1]+=1
            else: out.append([x,1])
        return out
    return sol.Value(sum(ch)), r==cp_model.OPTIMAL, runs(v[0::2]), runs(v[1::2])
ts=[int(x) for x in sys.argv[1].split(",")]; tlim=float(sys.argv[2])
for t in ts:
    lo=-((t-1)//2); hi=(t+1)//2
    for s in range(lo,hi+1):
        r=solve(t,s,tlim)
        if r is None: print(f"t={t} s={s}: no solution in time", flush=True); continue
        nch,opt,re,ro=r
        print(f"t={t:2d} s={s:3d}: changes={nch:2d}{'*' if opt else ' '}  even-i runs={re}  odd-i runs={ro}", flush=True)
