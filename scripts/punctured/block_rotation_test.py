"""Block-diagonal template: pi is a sequence of at most B consecutive blocks [a_b, a_b+L_b-1],
each mapped onto itself by a cyclic rotation by r_b (r_b=0 is the identity block).  Rotated odd
blocks give an interval of sums, identity blocks an even AP.  Test feasibility over the window
for t<=30 and B in {3,4,5}; print the block structure of one solution per (t,s) for B=5."""
import sys
from ortools.sat.python import cp_model
def feas(t,s,B,tlim=15,want=False):
    m=cp_model.CpModel()
    pi=[m.NewIntVar(0,t-1,"") for _ in range(t)]; m.AddAllDifferent(pi)
    a=[m.NewIntVar(0,t,"") for _ in range(B+1)]; m.Add(a[0]==0); m.Add(a[B]==t)
    for b in range(B): m.Add(a[b]<=a[b+1])
    r=[m.NewIntVar(0,t,"") for _ in range(B)]
    for b in range(B):
        L=a[b+1]-a[b]; m.Add(r[b]<=L-1).OnlyEnforceIf(m.NewBoolVar("")) if False else None
    for i in range(t):
        inblk=[]
        for b in range(B):
            x=m.NewBoolVar(""); inblk.append(x)
            m.Add(a[b]<=i).OnlyEnforceIf(x); m.Add(i<a[b+1]).OnlyEnforceIf(x)
            # rotation: pi(i) = a_b + ((i - a_b + r_b) mod L_b); encode as pi = i + r_b or i + r_b - L_b
            up=m.NewBoolVar("")
            m.Add(pi[i]==i+r[b]).OnlyEnforceIf([x,up]); m.Add(pi[i]<a[b+1]).OnlyEnforceIf([x,up])
            m.Add(pi[i]==i+r[b]-(a[b+1]-a[b])).OnlyEnforceIf([x,up.Not()]); m.Add(pi[i]>=a[b]).OnlyEnforceIf([x,up.Not()])
        m.AddExactlyOne(inblk)
    tau=[i+pi[i] for i in range(t)]
    for i in range(t):
        m.Add(tau[i]>=-s); m.Add(tau[i]<=2*t-1-s)
        for j in range(i+1,t): m.Add(tau[i]!=tau[j]); m.Add(tau[i]+tau[j]!=2*t-1-2*s)
    sol=cp_model.CpSolver(); sol.parameters.max_time_in_seconds=tlim; sol.parameters.num_search_workers=2
    res=sol.Solve(m); ok=res in (cp_model.OPTIMAL,cp_model.FEASIBLE)
    if want and ok:
        return [(sol.Value(a[b]),sol.Value(a[b+1])-sol.Value(a[b]),sol.Value(r[b])) for b in range(B) if sol.Value(a[b+1])>sol.Value(a[b])]
    return ok if res!=cp_model.UNKNOWN else None
for t in range(6,31):
    lo=-((t-1)//2); hi=(t+1)//2; out=[]
    for B in (3,4,5):
        bad=[s for s in range(lo,hi+1) if feas(t,s,B) is False]; unk=[s for s in range(lo,hi+1) if feas(t,s,B) is None]
        out.append(f"B={B} fail {bad}{' unk '+str(unk) if unk else ''}")
    print(f"t={t:2d} [{lo},{hi}]: "+" | ".join(out), flush=True)
print("block structures (start,length,rotation) with B=5:")
for t in (13,14,21,22):
    for s in range(-((t-1)//2),(t+1)//2+1):
        print(f"  t={t} s={s:3d}: {feas(t,s,5,25,True)}", flush=True)
