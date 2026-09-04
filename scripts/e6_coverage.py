#!/usr/bin/env python3
"""(E6) coverage over the emittable contexts, by the literal reading of (E6).

The manuscript's (E6) has two clauses:

    (a) the only label depending on an input alone is the antipode of that
        input, and
    (b) no non-head label is a rational multiple of the head.

The assembler records (b) as the flag ``clean`` and (a) as the separate flag
``forced_only_antipode``, and the latter is computed against ONE input index,
so it says nothing about the second input of a two-input row.  A family
satisfies (E6) exactly when both hold, in the two-input case for both inputs.
``audit_e4_e6.audit`` is the literal test and is what this program uses.

Reported: for each of the three predicates, how many emittable contexts have
at least one menu family satisfying it.

usage: e6_coverage.py [CATALOGUE]
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from audit_e4_e6 import audit  # noqa: E402
from run_alphabet_batch import key  # noqa: E402

DATA = os.path.normpath(os.path.join(HERE, "..", "data"))


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(DATA, "alphabet_families.json")
    cat = json.load(open(path))
    emit = json.load(open(os.path.join(DATA, "alphabet_contexts_emittable.json")))
    E = [key(c) for c in emit]
    have = {"clean only (b)": 0, "forced_only_antipode only (a)": 0,
            "both flags": 0, "(E6) literal": 0}
    n_with_family = 0
    literal_missing = []
    for k in E:
        e = cat.get(k)
        if e is None:
            continue
        n_with_family += 1
        fams = e.get("menu") or [e]
        raw = [f.get("family") or f for f in fams]
        if any(f.get("clean") for f in fams):
            have["clean only (b)"] += 1
        if any(f.get("forced_only_antipode") for f in fams):
            have["forced_only_antipode only (a)"] += 1
        if any(f.get("clean") and f.get("forced_only_antipode") for f in fams):
            have["both flags"] += 1
        ok = False
        for f in raw:
            if not isinstance(f, dict) or "coefficients_by_label" not in f:
                continue
            if not audit(f)[1]:
                ok = True
                break
        if ok:
            have["(E6) literal"] += 1
        else:
            literal_missing.append(k)
    print(f"emittable contexts with a family : {n_with_family}")
    for nm, v in have.items():
        print(f"  at least one family with {nm:<32}: {v:5d}   "
              f"({n_with_family - v} without)")
    print(f"\ncontexts with NO family satisfying (E6) as written: {len(literal_missing)}")
    from collections import Counter
    c = Counter(k.rsplit("_", 1)[1] for k in literal_missing)
    print("  by child type:", dict(c.most_common()))
    json.dump(sorted(literal_missing),
              open(os.path.join(DATA, "e6_missing_contexts.json"), "w"))


if __name__ == "__main__":
    main()
