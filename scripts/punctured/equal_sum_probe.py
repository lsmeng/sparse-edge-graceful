"""(a) At K=3M+1: is the clean tail [M+1,K] perfectly packable by type-A triples ALONE?
   After the reflection x -> K+1-x this is: partition [1,2M+1] into triples of sum K+2 = 3M+3.
(b) Clean-tail perfect packing for K in [3M, 3M+12], M up to 40 (both types allowed)."""
import itertools, sys
from ortools.sat.python import cp_model
def pack(avail, K, need, allowA=True, allowB=True, tlim=20):
    n=2*K+1; av=sorted(avail); S=set(av); tr=[]
    for a,b in itertools.combinations(av,2):
        if allowB and a+b in S and a+b>b: tr.append((a,b,a+b))
        if allowA and n-a-b in S and n-a-b>b: tr.append((a,b,n-a-b))
    m=cp_model.CpModel(); x=[m.NewBoolVar("") for _ in tr]; by={v:[] for v in av}
    for i,t in enumerate(tr):
        for v in t: by[v].append(x[i])
    for v in av: m.Add(sum(by[v])<=1)
    m.Add(sum(x)>=need)
    s=cp_model.CpSolver(); s.parameters.max_time_in_seconds=tlim; s.parameters.num_search_workers=4
    r=s.Solve(m)
    return {cp_model.OPTIMAL:"SAT",cp_model.FEASIBLE:"SAT",cp_model.INFEASIBLE:"UNSAT"}.get(r,"UNK")
print("(a) K=3M+1, tail [M+1,K] of length 2M+1, type-A only, need floor((2M+1)/3):")
for M in range(4,41):
    K=3*M+1; L=2*M+1; need=L//3
    va=pack(set(range(M+1,K+1)),K,need,allowA=True,allowB=False,tlim=20)
    vb=pack(set(range(M+1,K+1)),K,need,allowA=True,allowB=True,tlim=20)
    print(f"  M={M:2d} L={L:2d} t=L/3={L/3:5.2f}  A-only:{va:5s}  A+B:{vb}", flush=True)
print("(b) clean tail, both types, K in [3M,3M+12]: list any UNSAT/UNK")
for M in range(4,41,3):
    bad=[(K,pack(set(range(M+1,K+1)),K,(K-M)//3,tlim=25)) for K in range(3*M,3*M+13)]
    bad=[(K,v) for K,v in bad if v!="SAT"]
    print(f"  M={M:2d}: {bad if bad else 'all SAT'}", flush=True)
