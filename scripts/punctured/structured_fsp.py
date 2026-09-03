"""Structured folded sum permutations.  Transversal form: sums tau_i = i+pi(i) must be distinct,
lie in W=[-s, 2t-1-s], and no two sum to c=2t-1-2s.
(b1) pi(i)-i takes at most k distinct values (k=2,3,4).
(b2) pi is a piecewise shift on at most B contiguous blocks (B=3,4) i.e. pi(i)=i+a_r on block r.
Report the s-values in the window where the structured form is infeasible ('.' none)."""
from ortools.sat.python import cp_model
def base(t,s):
    m=cp_model.CpModel()
    pi=[m.NewIntVar(0,t-1,"") for _ in range(t)]; m.AddAllDifferent(pi)
    tau=[i+pi[i] for i in range(t)]
    for i in range(t):
        m.Add(tau[i]>=-s); m.Add(tau[i]<=2*t-1-s)
    for i in range(t):
        for j in range(i+1,t):
            m.Add(tau[i]!=tau[j]); m.Add(tau[i]+tau[j]!=2*t-1-2*s)
    return m,pi
def feas_kvals(t,s,k,tlim=8):
    m,pi=base(t,s)
    vals=[m.NewIntVar(-t,t,"") for _ in range(k)]
    for i in range(t):
        ch=[m.NewBoolVar("") for _ in range(k)]; m.AddExactlyOne(ch)
        for r in range(k): m.Add(pi[i]-i==vals[r]).OnlyEnforceIf(ch[r])
    sol=cp_model.CpSolver(); sol.parameters.max_time_in_seconds=tlim; sol.parameters.num_search_workers=2
    return sol.Solve(m) in (cp_model.OPTIMAL,cp_model.FEASIBLE)
def feas_blocks(t,s,B,tlim=8):
    m,pi=base(t,s)
    # block r covers [b_r, b_{r+1}) with 0=b_0<=...<=b_B=t ; pi(i)=i+a_r there
    b=[m.NewIntVar(0,t,"") for _ in range(B+1)]; m.Add(b[0]==0); m.Add(b[B]==t)
    for r in range(B): m.Add(b[r]<=b[r+1])
    a=[m.NewIntVar(-t,t,"") for _ in range(B)]
    for i in range(t):
        for r in range(B):
            inb=m.NewBoolVar(""); m.Add(b[r]<=i).OnlyEnforceIf(inb); m.Add(i<b[r+1]).OnlyEnforceIf(inb)
            m.Add(pi[i]-i==a[r]).OnlyEnforceIf(inb)
            # inb must be true iff i in block r: enforce via at-least-one over r
            setattr(m, f"_x{i}_{r}", inb)
        m.AddBoolOr([getattr(m,f"_x{i}_{r}") for r in range(B)])
    sol=cp_model.CpSolver(); sol.parameters.max_time_in_seconds=tlim; sol.parameters.num_search_workers=2
    return sol.Solve(m) in (cp_model.OPTIMAL,cp_model.FEASIBLE)
for t in range(6,25):
    lo=-((t-1)//2); hi=(t+1)//2; W=range(lo,hi+1)
    r2=[s for s in W if not feas_kvals(t,s,2)]; r3=[s for s in W if not feas_kvals(t,s,3)]; r4=[s for s in W if not feas_kvals(t,s,4)]
    b3=b4=["skipped"]
    print(f"t={t:2d} window[{lo},{hi}]  k=2 fails {r2}  k=3 fails {r3}  k=4 fails {r4}  | blocks3 fails {b3}  blocks4 fails {b4}", flush=True)
