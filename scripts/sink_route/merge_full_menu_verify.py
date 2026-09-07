#!/usr/bin/env python3
"""Merge the shard files of ``verify_full_menu_gate.py --partial`` and compare
the total with the gate's certificate."""
import argparse, collections, glob, json, sys

ap = argparse.ArgumentParser()
ap.add_argument("--cert", required=True)
ap.add_argument("--partials", required=True, help="glob for the shard files")
a = ap.parse_args()

cert = json.load(open(a.cert))
files = sorted(glob.glob(a.partials))
hist = collections.Counter()
pairs = 0
zeros = []
digests = set()
shards = set()
for f in files:
    d = json.load(open(f))
    shards.add((d["shard"], d["shards"]))
    digests.add(d["catalogue_sha256"])
    pairs += d["pairs"]
    zeros += d["zero_free_pairs"]
    for k, v in d["histogram_free_orders"].items():
        hist[int(k)] += v

problems = []
n_shards = {s for _, s in shards}
if len(n_shards) != 1:
    problems.append(f"shard files disagree on the shard count: {n_shards}")
else:
    want = next(iter(n_shards))
    have = {i for i, _ in shards}
    if have != set(range(want)):
        problems.append(f"missing shards: {sorted(set(range(want)) - have)}")
if len(digests) != 1 or digests != {cert["catalogue_sha256"]}:
    problems.append(f"catalogue digests {digests} vs {cert['catalogue_sha256']}")
if pairs != cert["pairs"]:
    problems.append(f"pairs {pairs} != {cert['pairs']}")
mine = {str(k): hist[k] for k in sorted(hist)}
if mine != cert["histogram_free_orders"]:
    problems.append("histogram differs")
mn = min(hist) if hist else None
if mn != cert["min_free_orders"]:
    problems.append(f"min {mn} != {cert['min_free_orders']}")
if sorted(map(tuple, zeros)) != sorted(map(tuple, cert["zero_free_pairs"])):
    problems.append("zero-free pair list differs")

print(json.dumps({"shard_files": len(files), "pairs": pairs,
                  "min_free_orders": mn, "zero_free_pairs": len(zeros),
                  "histogram_free_orders": mine,
                  "agrees_with_certificate": not problems,
                  "problems": problems}, indent=1))
raise SystemExit(0 if not problems else 1)
