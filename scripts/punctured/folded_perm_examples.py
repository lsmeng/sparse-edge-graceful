from ortools.sat.python import cp_model
def solve(t,s,tlim=20,prefer_B=True):
    m=cp_model.CpModel()
    pi=[m.NewIntVar(0,t-1,"") for i in range(t)]; m.AddAllDifferent(pi)
    k=[m.NewIntVar(0,t-1,"") for i in range(t)]; m.AddAllDifferent(k)
    bs=[]
    for i in range(t):
        u=i+pi[i]+s; b=m.NewBoolVar(""); bs.append(b)
        m.Add(k[i]==u).OnlyEnforceIf(b); m.Add(k[i]==2*t-1-u).OnlyEnforceIf(b.Not())
    (m.Maximize if prefer_B else m.Minimize)(sum(bs))
    sol=cp_model.CpSolver(); sol.parameters.max_time_in_seconds=tlim; sol.parameters.num_search_workers=3
    r=sol.Solve(m)
    if r not in (cp_model.OPTIMAL,cp_model.FEASIBLE): return None
    return [sol.Value(v) for v in pi],[sol.Value(v) for v in k],["B" if sol.Value(b) else "A" for b in bs]
for t in (7,8,9,10,11,12):
    for s in sorted({-(t-1)//2, -1, 0, 1, 2, (t+1)//2}):
        r=solve(t,s)
        if r: 
            pi,k,ty=r; print(f"t={t:2d} s={s:3d}: pi={pi}  k={k}  types={''.join(ty)}")
        else: print(f"t={t:2d} s={s:3d}: none")
