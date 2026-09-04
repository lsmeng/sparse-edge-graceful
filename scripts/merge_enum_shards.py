#!/usr/bin/env python3
"""Merge sharded runs of enumerate_emittable_contexts.py and compare with the catalogue.

The shipped enumeration caps the number of active children at two, so owners
with three or more active children were never enumerated abstractly; the
exhaustive scheduler regression cannot supply them either, because a tree on at
most nine vertices has no such owner.  This script merges the sharded k>=3 runs
and answers the only question that matters for Lemma C:

  * does any enumerated state emit a context that is NOT in the alphabet, and
  * does any emitted context lack a family in the catalogue?

Either would mean the case analysis of Appendix A is incomplete as a
mathematical statement, not merely in its write-up.

usage: merge_enum_shards.py SHARD_DIR [--out data/emittable_k3.json]
"""
import argparse
import glob
import json
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from run_alphabet_batch import key as ctx_key  # noqa: E402
from closure_check import RIGID  # noqa: E402

DATA = os.path.normpath(os.path.join(HERE, "..", "data"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("shard_dir")
    ap.add_argument("--alphabet", default=os.path.join(DATA, "alphabet_contexts.json"))
    ap.add_argument("--catalogue", default=os.path.join(DATA, "alphabet_families.json"))
    ap.add_argument("--out", default=None)
    ap.add_argument("--report", default=None)
    a = ap.parse_args()

    files = sorted(glob.glob(os.path.join(a.shard_dir, "s*.json")))
    if not files:
        print(f"error: no shards in {a.shard_dir}", file=sys.stderr)
        return 2
    emitted, all_keys, passthrough = Counter(), Counter(), Counter()
    where, pairs, crashes, states = {}, set(), [], 0
    for f in files:
        d = json.load(open(f))
        states += d.get("states", 0)
        emitted.update(d.get("emitted") or {})
        all_keys.update(d.get("all_keys") or {})
        passthrough.update(d.get("passthrough") or {})
        for k, st in (d.get("where") or {}).items():
            where.setdefault(k, st)
        for pr in d.get("pairs") or []:
            pairs.add(tuple(pr))
        crashes.extend(d.get("crashes") or [])

    alpha = {ctx_key(c): c for c in json.load(open(a.alphabet))}
    cat = json.load(open(a.catalogue))
    E = set(emitted) | {k for k in all_keys if k}
    not_in_alpha = sorted(k for k in E if k not in alpha)
    no_family = sorted(k for k in E if k in alpha and k not in cat and k not in RIGID)
    rigid_hit = sorted(k for k in E if k in RIGID)

    lines = [f"# Sharded enumeration merged from {len(files)} shards\n",
             f"* abstract states processed        : {states:,}",
             f"* scheduler crashes                : {len(crashes)}",
             f"* distinct keys emitted at target  : {len(emitted):,}",
             f"* all keys seen in fragments       : {len(E):,}",
             f"* realizable (child, parent) pairs : {len(pairs):,}",
             f"* passthrough markers              : {dict(passthrough)}",
             "",
             f"* keys NOT in the alphabet         : {len(not_in_alpha)}"]
    for k in not_in_alpha[:60]:
        lines.append(f"    - {k}   first seen in state {where.get(k)}")
    lines.append(f"* keys covered by a rigid template : {len(rigid_hit)} {rigid_hit}")
    lines.append(f"* emitted keys WITHOUT a family    : {len(no_family)}")
    for k in no_family[:60]:
        lines.append(f"    - {k}  width {alpha[k]['width']}   state {where.get(k)}")
    if crashes:
        cc = Counter(msg for _, msg in crashes)
        lines.append("* crash signatures:")
        for msg, n in cc.most_common(10):
            lines.append(f"    {n:5d}  {msg}")

    verdict = ("LEMMA C SURVIVES THIS ENUMERATION"
               if not not_in_alpha and not no_family and not crashes
               else "LEMMA C NOT ESTABLISHED BY THIS ENUMERATION")
    lines += ["", f"**{verdict}**"]
    text = "\n".join(lines)
    print(text)
    if a.report:
        open(a.report, "w").write(text + "\n")
    if a.out:
        json.dump([alpha[k] for k in sorted(E) if k in alpha], open(a.out, "w"))
        json.dump(sorted(list(p) for p in pairs),
                  open(a.out.replace(".json", "_pairs.json"), "w"))
    return 0 if (not not_in_alpha and not no_family and not crashes) else 1


if __name__ == "__main__":
    sys.exit(main())
