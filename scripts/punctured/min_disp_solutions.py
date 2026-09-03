from ortools.sat.python import cp_model
def solve(t,s,tlim=25):
    m=cp_model.CpModel()
    pi=[m.NewIntVar(0,t-1,"") for _ in range(t)]; m.AddAllDifferent(pi)
    k=[m.NewIntVar(0,t-1,"") for _ in range(t)]; m.AddAllDifferent(k)
    bs=[]; disp=[]
    for i in range(t):
        u=i+pi[i]+s; b=m.NewBoolVar(""); bs.append(b)
        m.Add(k[i]==u).OnlyEnforceIf(b); m.Add(k[i]==2*t-1-u).OnlyEnforceIf(b.Not())
        dv=m.NewIntVar(0,t,""); m.AddAbsEquality(dv, pi[i]-i); disp.append(dv)
    m.Minimize(sum(disp))
    sol=cp_model.CpSolver(); sol.parameters.max_time_in_seconds=tlim; sol.parameters.num_search_workers=3
    r=sol.Solve(m)
    if r not in (cp_model.OPTIMAL,cp_model.FEASIBLE): return None
    return [sol.Value(v) for v in pi],[sol.Value(v) for v in k],"".join("B" if sol.Value(b) else "A" for b in bs), sol.Value(sum(disp))
for t in (12,13):
    for s in range(-((t-1)//2),(t+1)//2+1):
        r=solve(t,s)
        if r: pi,k,ty,dd=r; print(f"t={t} s={s:3d} disp={dd:2d}: pi-i={[p-i for i,p in enumerate(pi)]} types={ty}")
for s in (-7,-4,4,7,10):
    r=solve(21,s,40)
    if r: pi,k,ty,dd=r; print(f"t=21 s={s:3d} disp={dd:2d}: pi-i={[p-i for i,p in enumerate(pi)]} types={ty}")
