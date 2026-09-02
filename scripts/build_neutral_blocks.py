#!/usr/bin/env python3
"""Collect and re-verify the neutral blocks used by the adjunction lemma.

A neutral block is a set of arms plus a number of ports, hanging off an owner,
whose labels can be chosen (in one fresh parameter t) so that

  (i)   the block's contribution to the owner's output is zero,
  (ii)  the block's labels equal its outputs as a multiset,
  (iii) the labels are closed under negation,
  (iv)  the labels are nonzero and pairwise distinct.

Adjoining such a block to any family for a context C gives a family for the
context with those arms and ports added: (ii) preserves P = O, (i) leaves the
owner output untouched, (iii) extends the signature partition by mirror pairs,
and (iv) holds against the host family automatically because t is fresh.

The equal-length pair (l, l) has the closed form a_i = (-2)^i t on one arm and
its negative on the other; the other blocks come from neutral_block_search.py.
Every block is re-verified here from its labels alone.

usage: build_neutral_blocks.py [--dir data/neutral] [--out data/neutral_blocks.json]
"""
import argparse
import glob
import json
import os
from collections import Counter


def vadd(a, b):
    return tuple(x + y for x, y in zip(a, b))


def vneg(a):
    return tuple(-x for x in a)


def outputs(ports, arms, labels):
    """Outputs contributed by the block, and its contribution to the owner."""
    d = len(labels[0])
    out, owner, i = [], (0,) * d, 0
    for _ in range(ports):
        out.append(labels[i]); owner = vadd(owner, labels[i]); i += 1
    for ell in arms:
        row = labels[i:i + ell + 1]; i += ell + 1
        owner = vadd(owner, row[0])
        out.extend(vadd(row[k], row[k + 1]) for k in range(ell))
        out.append(row[ell])
    assert i == len(labels)
    return out, owner


def verify(ports, arms, labels, token=None):
    """None if the block satisfies (N1)-(N4); otherwise the reason it does not.

    ``labels`` is a list of coefficient tuples; ``token``, when given, is the
    list of three positions that form a token triple instead of mirror pairs.
    """
    labels = [tuple(v) for v in labels]
    n = ports + sum(a + 1 for a in arms)
    if len(labels) != n:
        return "label count"
    if any(all(x == 0 for x in v) for v in labels):
        return "zero label"
    if len(set(labels)) != n:
        return "duplicate label"
    rest = labels
    if token:
        if len(set(token)) != 3 or any(not 0 <= t < n for t in token):
            return "bad token positions"
        tv = [labels[t] for t in token]
        if any(sum(v[j] for v in tv) for j in range(len(tv[0]))):
            return "token does not sum to zero"
        a2, b2 = tv[0], tv[1]
        d = len(a2)
        if not any(a2[i] * b2[j] - a2[j] * b2[i]
                   for i in range(d) for j in range(i + 1, d)):
            return "token does not span a plane"
        rest = [v for i, v in enumerate(labels) if i not in set(token)]
    if Counter(rest) != Counter(vneg(v) for v in rest):
        return "not closed under negation"
    out, owner = outputs(ports, arms, labels)
    if any(owner):
        return "owner contribution %s" % (owner,)
    if Counter(out) != Counter(labels):
        return "P != O"
    return None


def equal_pair(ell):
    """(l, l) with a_i = (-2)^i on one arm and its negative on the other."""
    c = [(-2) ** i for i in range(ell + 1)]
    return [[v] for v in c] + [[-v] for v in c]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="data/neutral")
    ap.add_argument("--extra-dir", default=None,
                    help="a second directory of search results (e.g. token blocks)")
    ap.add_argument("--out", default="data/neutral_blocks.json")
    a = ap.parse_args()
    blocks = []
    # two ports labelled t and -t: each is its own output, and they cancel
    blocks.append({"ports": 2, "arms": [], "labels": [[1], [-1]],
                   "source": "closed form (t, -t)"})
    for ell in range(1, 9):
        blocks.append({"ports": 0, "arms": [ell, ell], "labels": equal_pair(ell),
                       "source": "closed form (-2)^i"})
    dirs = [a.dir] + ([a.extra_dir] if a.extra_dir else [])
    for f in sorted(g for d in dirs for g in glob.glob(os.path.join(d, "*.json"))):
        d = json.load(open(f))
        if d.get("status") not in ("OPTIMAL", "FEASIBLE"):
            continue
        cols = [j for j in range(len(d["labels"][0]))
                if any(r[j] for r in d["labels"])]
        lab = [[r[j] for j in cols] for r in d["labels"]]
        blocks.append({"ports": d.get("ports", 0), "arms": d["arms"],
                       "labels": lab, "token": d.get("token_positions"),
                       "source": os.path.basename(f)})
    ok, bad = [], []
    seen = set()
    for b in blocks:
        sig = (b["ports"], tuple(sorted(b["arms"])), bool(b.get("token")))
        err = verify(b["ports"], b["arms"], b["labels"], b.get("token"))
        if err:
            bad.append((sig, b["source"], err)); continue
        if sig in seen:
            continue
        seen.add(sig); ok.append(b)
    ok.sort(key=lambda b: (b["ports"], sorted(b["arms"])))
    json.dump(ok, open(a.out, "w"), indent=1)
    print(f"{len(ok)} verified neutral blocks -> {a.out}")
    for b in ok:
        print("   ports", b["ports"], " arms", str(b["arms"]).ljust(12),
              "token" if b.get("token") else "     ", "labels", b["labels"])
    if bad:
        print("REJECTED:")
        for sig, src, err in bad:
            print("   ", sig, src, err)


if __name__ == "__main__":
    main()
