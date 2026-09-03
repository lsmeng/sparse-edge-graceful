"""Leftover handling.  For K-M = 3t+e (e=1,2) we omit the e SMALLEST elements (M -> M+e), which is
the clean e=0 case whenever K >= 3(M+e)+1.  Only K in [3M+1, 3M+3e] remain: check them exactly
(any structure), and record which elements a type-A-only packing leaves unused."""
import itertools
from ortools.sat.python import cp_model
def pack(avail,K,need,Aonly,tlim=20):
    n=2*K+1; av=sorted(avail); S=set(av); tr=[]
    for a,b in itertools.combinations(av,2):
        if not Aonly and a+b in S and a+b>b: tr.append((a,b,a+b))
        if n-a-b in S and n-a-b>b: tr.append((a,b,n-a-b))
    m=cp_model.CpModel(); x=[m.NewBoolVar("") for _ in tr]; by={v:[] for v in av}
    for i,t in enumerate(tr):
        for v in t: by[v].append(x[i])
    for v in av: m.Add(sum(by[v])<=1)
    m.Add(sum(x)>=need)
    s=cp_model.CpSolver(); s.parameters.max_time_in_seconds=tlim; s.parameters.num_search_workers=3
    r=s.Solve(m)
    if r not in (cp_model.OPTIMAL,cp_model.FEASIBLE): return None
    P=[t for i,t in enumerate(tr) if s.Value(x[i])]; used={v for t in P for v in t}
    return sorted(set(av)-used)
for M in range(5,31):
    out=[]
    for K in (3*M+1,3*M+2,3*M+3):
        e=(K-M)%3
        if e==0: continue
        need=(K-M)//3
        ua=pack(set(range(M+1,K+1)),K,need,True); ub=pack(set(range(M+1,K+1)),K,need,False)
        out.append(f"K={K}(e={e}) A-only unused={ua} any={'ok' if ub is not None else 'NONE'}")
    print(f"M={M:2d}: "+" | ".join(out), flush=True)
