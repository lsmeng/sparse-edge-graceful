#!/usr/bin/env python3
"""Run the FAITHFUL realiser (proof-draft bookkeeping: integer lattice, boxes,
pending tokens) on comb+bush trees and report what the realization stage does
on the chain of blocked cells, independently of the block-completion stand-in."""
import sys, os, json, random
sys.path.insert(0, os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..")))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import free_token_constructor as ftc
import context_scheduler as cs
from combbush import combbush

def faithful(par, tries=400, seed=1):
    n, parent, children, root0 = ftc.normalise_parent(par)
    catalogue = ftc.load_catalogue()
    root = root0
    old_of, new_of = ftc.relabel_to_root(parent, root)
    sched_parent = [-1]*n
    for v in range(n):
        if parent[v] != -1: sched_parent[new_of[v]] = new_of[parent[v]]
    sched_parent[0] = 0
    sched = cs.schedule(sched_parent)
    sched = ftc.translate_schedule(sched, old_of)
    plan = ftc.Plan(n, parent, children, root, sched)
    rng = random.Random(seed)
    real = ftc.FaithfulRealiser(plan, catalogue, rng, tries=tries, allow_fallback=True)
    err = None
    try:
        real.run()
    except ftc.Failure as exc:
        err = exc.report
    ctxs = [(v, x.key) for v, x in sorted(plan.nodes.items()) if x.is_owner]
    heads = []
    for v, x in sorted(plan.nodes.items()):
        if x.is_owner:
            hv = getattr(x, "head_value", None)
            heads.append((v, x.key, str(hv)))
    D = ftc.degree_two_count(parent)
    out = dict(n=n, D=D, err=err, max_magnitude=real.max_magnitude, magnitude_over_D1=(real.max_magnitude/(D+1)),
               lattice_M=real.M, counters=dict(real.counters), gaps=[dict(g) for g in real.gaps][:6],
               notes=list(real.notes)[:8], max_live=real.max_live, max_pending=real.max_pending,
               n_special=len(real.labels), heads=heads[:40])
    return out
if __name__ == "__main__":
    arm, sub = int(sys.argv[1]), int(sys.argv[2])
    for k in [int(x) for x in sys.argv[3].split(",")]:
        bush = int(sys.argv[4])*k
        par = combbush(k, arm, sub, bush)
        if len(par) % 2 == 0: par = combbush(k, arm, sub, bush+1)
        o = faithful(par)
        print(f"== arm={arm} sub={sub} k={k} n={o['n']} D={o['D']}: max_magnitude={o['max_magnitude']} ratio={o['magnitude_over_D1']:.1f} M={o['lattice_M']} live={o['max_live']} pending={o['max_pending']} special={o['n_special']}")
        print("   err:", o["err"])
        print("   counters:", {k2: v for k2, v in o["counters"].items() if v})
        if o["gaps"]: print("   gaps:", o["gaps"])
        if o["notes"]: print("   notes:", o["notes"])
        print("   heads:", o["heads"])
