#!/usr/bin/env python3
"""Which contexts are reachable from the catalogue by adjoining neutral blocks?

A context (head, arm multiset, ports, child) is *reachable* when some verified
neutral block (data/neutral_blocks.json) can be stripped from it, repeatedly,
until a context with a catalogue family is reached.  Adjoining the stripped
blocks back, in reverse order, then gives a family for the original context.

usage: neutral_closure.py [--targets FILE] [--catalogue FILE] [--out FILE]
"""
import argparse
import itertools
import json
import os
import sys
from collections import Counter, deque

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from run_alphabet_batch import key  # noqa: E402


def load_blocks(path):
    return [(b["ports"], tuple(sorted(b["arms"])), i)
            for i, b in enumerate(json.load(open(path)))]


def strips(arms, ports, blocks):
    """(arms, ports, block index) reachable by removing one neutral block."""
    out = []
    ac = Counter(arms)
    for bp, ba, idx in blocks:
        if bp > ports:
            continue
        bc = Counter(ba)
        if any(bc[v] > ac[v] for v in bc):
            continue
        rest = list(arms)
        for v in ba:
            rest.remove(v)
        out.append((tuple(rest), ports - bp, idx))
    return out


def keyset(ctx, arms, ports):
    return {key({**ctx, "arms": list(p), "ports": ports})
            for p in set(itertools.permutations(arms))}


def route(ctx, catk, blocks, limit=4000):
    """Shortest list of block indices whose removal reaches a catalogue key."""
    start = (tuple(ctx["arms"]), ctx["ports"])
    seen = {start}
    dq = deque([(start, [])])
    while dq and len(seen) < limit:
        (arms, ports), path = dq.popleft()
        for nxt_arms, nxt_ports, idx in strips(arms, ports, blocks):
            st = (nxt_arms, nxt_ports)
            if st in seen:
                continue
            seen.add(st)
            hit = keyset(ctx, nxt_arms, nxt_ports) & catk
            if hit:
                return path + [idx], sorted(hit)[0]
            dq.append((st, path + [idx]))
    return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--targets", default="data/alphabet_contexts_missing_v6.json")
    ap.add_argument("--catalogue", default="data/alphabet_families.json")
    ap.add_argument("--blocks", default="data/neutral_blocks.json")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    tgt = json.load(open(a.targets))
    catk = set(json.load(open(a.catalogue)))
    blocks = load_blocks(a.blocks)
    reach, stuck = [], []
    for c in tgt:
        path, base = route(c, catk, blocks)
        if path is None:
            stuck.append(c)
        else:
            reach.append({"key": key(c), "ctx": c, "base": base, "blocks": path})
    print(f"targets {len(tgt)}: reachable {len(reach)}, stuck {len(stuck)}")
    print("stuck widths:", sorted(Counter(c["width"] for c in stuck).items()))
    for c in stuck:
        print("   ", key(c), "w=", c["width"])
    if a.out:
        json.dump({"reachable": reach, "stuck": stuck}, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
