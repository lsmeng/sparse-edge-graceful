"""Transversal shape test.  W=[-s,2t-1-s], c=2t-1-2s, lower half Lo=[-s,t-1-s].
Shape F1: T = Lo with ONE interval [a1,a2] of Lo flipped to its reflection [c-a2,c-a1].
Sub-shapes: prefix (a1=-s), suffix (a2=t-1-s).  Report s-values in the window where the shape
is infeasible, for t<=30; print pi(i)-i for a few feasible cases."""
from ortools.sat.python import cp_model
def solve(t,s,mode,tlim=6,want_pi=False):
    m=cp_model.CpModel(); lo=-s; hi=t-1-s; c=2*t-1-2*s
    pi=[m.NewIntVar(0,t-1,"") for _ in range(t)]; m.AddAllDifferent(pi)
    a1=m.NewIntVar(lo,hi,"a1"); a2=m.NewIntVar(lo,hi,"a2"); m.Add(a1<=a2)
    if mode=="prefix": m.Add(a1==lo)
    if mode=="suffix": m.Add(a2==hi)
    # each row's sum is either an unflipped lower value or a flipped (upper) value
    for i in range(t):
        tau=i+pi[i]; up=m.NewBoolVar("")
        # lower & not in [a1,a2]
        m.Add(tau>=lo).OnlyEnforceIf(up.Not()); m.Add(tau<=hi).OnlyEnforceIf(up.Not())
        left=m.NewBoolVar(""); m.Add(tau<a1).OnlyEnforceIf([up.Not(),left]); m.Add(tau>a2).OnlyEnforceIf([up.Not(),left.Not()])
        # upper: c-tau in [a1,a2]
        m.Add(c-tau>=a1).OnlyEnforceIf(up); m.Add(c-tau<=a2).OnlyEnforceIf(up)
    # sums distinct (then automatically a transversal of the chosen shape, since T has t elements)
    for i in range(t):
        for j in range(i+1,t): m.Add(i+pi[i]!=j+pi[j])
    sol=cp_model.CpSolver(); sol.parameters.max_time_in_seconds=tlim; sol.parameters.num_search_workers=2
    r=sol.Solve(m)
    ok=r in (cp_model.OPTIMAL,cp_model.FEASIBLE)
    if want_pi and ok: return True,[sol.Value(v)-i for i,v in enumerate(pi)],(sol.Value(a1),sol.Value(a2))
    return ok,None,None
for t in range(6,25):
    lo=-((t-1)//2); hi=(t+1)//2; W=range(lo,hi+1)
    fa=[s for s in W if not solve(t,s,"any")[0]]; fp=[s for s in W if not solve(t,s,"prefix")[0]]; fs=[s for s in W if not solve(t,s,"suffix")[0]]
    print(f"t={t:2d} window[{lo},{hi}]: one-flipped-interval fails {fa} | prefix fails {fp} | suffix fails {fs}", flush=True)
print("examples (pi(i)-i, flipped interval):")
for t,s in ((13,3),(13,-3),(20,5),(20,-5),(21,8)):
    ok,d,ab=solve(t,s,"any",20,True); print(f"  t={t} s={s}: {d} flipped={ab}" if ok else f"  t={t} s={s}: none")
