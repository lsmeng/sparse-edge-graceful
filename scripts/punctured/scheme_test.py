"""Explicit scheme for FSP(t,s), s>=1, t'=t-s:
  top rows  t'+r        -> column t'+s-1-2r   (r=0..s-1)   sums 2t'+s-1-r  = the forced set [2t',2t'+s-1]
  band rows t'-s+m      -> column t'+s-2m     (m=1..s-1)   sums 2t'-m      = the run [2t'-s+1,2t'-1]
  identity  i -> i for i in [R+1, t'-s]
  repair    rows [0,R] permuted among columns [0,R] by the solver.
Totals match exactly; the only defect is the reflection conflict between small even sums <= s-2 and
the run, which the repair must fix.  Report feasibility for R in {s, s+2, 2s} across the window."""
import sys
from ortools.sat.python import cp_model
def scheme(t,s,R,tlim=10,want=False):
    tp=t-s; m=cp_model.CpModel()
    pi=[m.NewIntVar(0,t-1,"") for _ in range(t)]; m.AddAllDifferent(pi)
    for r in range(s): m.Add(pi[tp+r]==tp+s-1-2*r)
    for mm in range(1,s):
        row=tp-s+mm
        if row<0 or row>R: 
            if row>=0: m.Add(pi[row]==tp+s-2*mm)
            else: return None   # scheme not defined (s too large for t) -- shouldn't happen in window
        else: m.Add(pi[row]==tp+s-2*mm)
    for i in range(R+1,tp-s+1): m.Add(pi[i]==i)
    Rr=min(R,tp-s)
    for i in range(0,Rr+1): m.Add(pi[i]<=Rr)
    tau=[i+pi[i] for i in range(t)]
    for i in range(t):
        m.Add(tau[i]>=-s); m.Add(tau[i]<=2*t-1-s)
        for j in range(i+1,t): m.Add(tau[i]!=tau[j]); m.Add(tau[i]+tau[j]!=2*t-1-2*s)
    sol=cp_model.CpSolver(); sol.parameters.max_time_in_seconds=tlim; sol.parameters.num_search_workers=2
    r=sol.Solve(m)
    ok=r in (cp_model.OPTIMAL,cp_model.FEASIBLE)
    if want and ok: return [sol.Value(pi[i]) for i in range(min(R,tp-s)+1)]
    return ok if r!=cp_model.UNKNOWN else None
for t in range(6,41):
    out=[]
    for name,Rf in (("R=s",lambda s:s),("R=s+2",lambda s:s+2),("R=2s",lambda s:2*s)):
        bad=[]; unk=[]
        for s in range(1,(t+1)//2+1):
            v=scheme(t,s,Rf(s))
            if v is None: unk.append(s)
            elif not v: bad.append(s)
        out.append(f"{name}: fail {bad}{' unk '+str(unk) if unk else ''}")
    print(f"t={t:2d}: "+" | ".join(out), flush=True)
