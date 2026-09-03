"""Minimal number of odd blocks in an interval design, by brute force (no solver).
Design: odd composition (a_1..a_m) of t for rows; column intervals are the same parts in some order;
block k (rows start r_k) -> column interval with start c_{k}; sums = interval [r_k+c_k+(a_k-1)/2, r_k+c_k+(3a_k-3)/2].
Valid iff sum intervals are disjoint, in W=[-s,2t-1-s], each on one side of C/2, and no I_k meets C-I_l.
Reports min blocks (<=B) per (t,s)."""
import sys, itertools
def valid(ints,t,s):
    C=2*t-1-2*s
    for lo,hi in ints:
        if lo< -s or hi>2*t-1-s: return False
        if not (2*hi<=C-1 or 2*lo>=C+1): return False
    for (lo,hi),(lo2,hi2) in itertools.combinations(ints,2):
        if not (hi<lo2 or hi2<lo): return False
        if not (hi<C-hi2 or C-lo2<lo): return False
    return True
def compositions(t,B):
    out=[]
    def rec(rem,cur):
        if rem==0: out.append(tuple(cur)); return
        if len(cur)>=B: return
        for a in range(1,rem+1,2): rec(rem-a,cur+[a])
    rec(t,[]); return out
def min_blocks(t,s,B):
    best=None
    for comp in sorted(compositions(t,B),key=len):
        if best is not None and len(comp)>=best[0]: break
        m=len(comp); rs=[sum(comp[:k]) for k in range(m)]
        for order in itertools.permutations(range(m)):
            # column interval for block k starts at the position of k in 'order'
            cs=[0]*m; pos=0
            for k in order: cs[k]=pos; pos+=comp[k]
            ints=[(rs[k]+cs[k]+(comp[k]-1)//2, rs[k]+cs[k]+(3*comp[k]-3)//2) for k in range(m)]
            if valid(ints,t,s): best=(m,comp,order); break
        if best and best[0]==len(comp): break
    return best
B=int(sys.argv[1]); tmax=int(sys.argv[2])
for t in range(5,tmax+1):
    lo=-((t-1)//2); hi=(t+1)//2; row=[]
    for s in range(lo,hi+1):
        b=min_blocks(t,s,B); row.append("-" if b is None else str(b[0]))
    print(f"t={t:2d} s in [{lo},{hi}]: {''.join(row)}", flush=True)
