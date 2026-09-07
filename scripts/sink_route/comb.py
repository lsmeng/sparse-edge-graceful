#!/usr/bin/env python3
"""Comb trees: a spine of k core vertices joined by direct edges, each with one
pendant arm of `arm` suppressed vertices (arm+1 edges); the top spine vertex
gets `root_extra` extra leaves so it is a branch vertex.  `sub` subdivides each
spine edge with that many degree-two vertices (head chain length)."""
import sys
def comb(k, arm=3, sub=0, root_extra=2, root_arms=0):
    par = [-1]           # vertex 0 = top spine vertex (root)
    spine = [0]
    def add(p):
        par.append(p); return len(par)-1
    def add_arm(v, L):
        cur = v
        for _ in range(L+1):
            cur = add(cur)
    for _ in range(root_extra):
        add(0)
    for _ in range(root_arms):
        add_arm(0, arm)
    prev = 0
    for i in range(k):
        if i > 0:
            cur = prev
            for _ in range(sub):
                cur = add(cur)
            v = add(cur); spine.append(v); prev = v
        add_arm(prev, arm)
    return par
if __name__ == "__main__":
    k = int(sys.argv[1]); arm = int(sys.argv[2]); sub = int(sys.argv[3]); re = int(sys.argv[4]); ra = int(sys.argv[5]) if len(sys.argv) > 5 else 0
    par = comb(k, arm, sub, re, ra)
    print(",".join(map(str, par)))
