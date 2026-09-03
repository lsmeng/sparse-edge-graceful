"""Odd-block interval designs.  Rows [0,t-1] are cut into consecutive blocks of ODD sizes a_1..a_m
(any composition of t into odd parts, size-1 blocks allowed); block k is mapped by the half-rotation
onto a column interval [c_k, c_k+a_k-1]; the column intervals must partition [0,t-1].  The sums of
block k form the interval centred at rowcentre_k + colcentre_k.  A design is valid iff the sum
intervals are disjoint, inside W, and reflection-free.  For each (t,s) search all odd compositions
(few blocks first) with CP-SAT placing the column intervals; report the first design found."""
import sys, itertools
from ortools.sat.python import cp_model
def odd_compositions(t):
    # generate compositions of t into odd parts, ordered by number of parts ascending
    res=[]
    def rec(rem,cur):
        if rem==0: res.append(tuple(cur)); return
        for a in range(1,rem+1,2): rec(rem-a,cur+[a])
    rec(t,[]); res.sort(key=len); return res
def place(t,s,comp,tlim=5):
    m=cp_model.CpModel(); mblk=len(comp)
    rs=[sum(comp[:k]) for k in range(mblk)]
    c=[m.NewIntVar(0,t-comp[k],"") for k in range(mblk)]
    # column intervals disjoint
    for k in range(mblk):
        for l in range(k+1,mblk):
            b=m.NewBoolVar("")
            m.Add(c[k]+comp[k]<=c[l]).OnlyEnforceIf(b); m.Add(c[l]+comp[l]<=c[k]).OnlyEnforceIf(b.Not())
    # sum interval of block k: [rs_k + c_k + (a-1)/2, rs_k + c_k + (3a-3)/2]
    lo=[rs[k]+c[k]+(comp[k]-1)//2 for k in range(mblk)]; hi=[rs[k]+c[k]+(3*comp[k]-3)//2 for k in range(mblk)]
    C=2*t-1-2*s
    for k in range(mblk):
        m.Add(lo[k]>=-s); m.Add(hi[k]<=2*t-1-s)
        # no self reflection: interval entirely below or above C/2  <=> hi < C-hi  or lo > C-lo
        b=m.NewBoolVar(""); m.Add(2*hi[k]<=C-1).OnlyEnforceIf(b); m.Add(2*lo[k]>=C+1).OnlyEnforceIf(b.Not())
        for l in range(k+1,mblk):
            # disjoint sum intervals
            d=m.NewBoolVar(""); m.Add(hi[k]<lo[l]).OnlyEnforceIf(d); m.Add(hi[l]<lo[k]).OnlyEnforceIf(d.Not())
            # reflection-free across: intervals I_k and C - I_l disjoint
            e=m.NewBoolVar(""); m.Add(hi[k]<C-hi[l]).OnlyEnforceIf(e); m.Add(C-lo[l]<lo[k]).OnlyEnforceIf(e.Not())
    sol=cp_model.CpSolver(); sol.parameters.max_time_in_seconds=tlim; sol.parameters.num_search_workers=2
    r=sol.Solve(m)
    if r in (cp_model.OPTIMAL,cp_model.FEASIBLE): return [sol.Value(v) for v in c]
    return None
ts=[int(x) for x in sys.argv[1].split(",")]
for t in ts:
    comps=odd_compositions(t)
    for s in range(-((t-1)//2),(t+1)//2+1):
        found=None
        for comp in comps:
            cs=place(t,s,comp)
            if cs is not None: found=(comp,cs); break
        print(f"t={t:2d} s={s:3d}: "+("NONE" if found is None else f"blocks={found[0]} colstarts={found[1]}"), flush=True)
