"""Composition theorem check.  Claim: if sigma is an FSP(b, s') and a is odd, then
    pi(a*u + w) = a*sigma(u) + ((w + (a-1)/2) mod a)
is an FSP(a*b, s) with s = a*(s'-1) + (a+1)/2.  Verify directly for many (a,b,s') using
CP-SAT only to obtain sigma; the check of pi is exact and solver-free."""
from ortools.sat.python import cp_model
def fsp(t,s,tlim=20):
    m=cp_model.CpModel(); pi=[m.NewIntVar(0,t-1,"") for _ in range(t)]; m.AddAllDifferent(pi)
    tau=[i+pi[i] for i in range(t)]
    for i in range(t):
        m.Add(tau[i]>=-s); m.Add(tau[i]<=2*t-1-s)
        for j in range(i+1,t): m.Add(tau[i]!=tau[j]); m.Add(tau[i]+tau[j]!=2*t-1-2*s)
    sol=cp_model.CpSolver(); sol.parameters.max_time_in_seconds=tlim; sol.parameters.num_search_workers=2
    r=sol.Solve(m); return [sol.Value(v) for v in pi] if r in (cp_model.OPTIMAL,cp_model.FEASIBLE) else None
def is_fsp(pi,s):
    t=len(pi)
    if sorted(pi)!=list(range(t)): return False
    tau=[i+pi[i] for i in range(t)]
    if len(set(tau))!=t: return False
    if any(x< -s or x>2*t-1-s for x in tau): return False
    c=2*t-1-2*s; S=set(tau)
    return all((c-x) not in S for x in tau)
ok=bad=0
for a in (3,5,7,9):
    for b in range(3,14):
        for sp in range(-((b-1)//2),(b+1)//2+1):
            sig=fsp(b,sp)
            if sig is None: continue
            r=(a-1)//2
            pi=[a*sig[u]+((w+r)%a) for u in range(b) for w in range(a)]
            s=a*(sp-1)+(a+1)//2
            if is_fsp(pi,s): ok+=1
            else: bad+=1; print("FAIL",a,b,sp,s)
print(f"composition theorem: {ok} verified, {bad} failures")
