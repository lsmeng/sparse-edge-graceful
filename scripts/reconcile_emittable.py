#!/usr/bin/env python3
"""Reconcile the emittable context set with the catalogue and the gate.

Inputs: data/alphabet_contexts_emittable.json (from enumerate_emittable_contexts.py),
data/alphabet_families.json, and optionally a gate JSON (check_lookahead_gate.py --json).
Outputs a report: emittable keys without a family (by width and kind), emittable keys
covered only by the rigid residue-two row, and the gate's failing pairs restricted to
emittable children and parents.

usage: reconcile_emittable.py [--emittable FILE] [--catalogue FILE] [--gate FILE]
"""
import argparse
import json
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from run_alphabet_batch import key  # noqa: E402

DATA = os.path.normpath(os.path.join(HERE, "..", "data"))
RIGID = {"h0_2_p0_act"}   # residue-two rigid ray (constructor template), not a catalogue family


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--emittable", default=os.path.join(DATA, "alphabet_contexts_emittable.json"))
    ap.add_argument("--catalogue", default=os.path.join(DATA, "alphabet_families.json"))
    ap.add_argument("--gate", default=None)
    ap.add_argument("--out", default=os.path.join(DATA, "reconcile_report.md"))
    a = ap.parse_args()
    emit = json.load(open(a.emittable))
    E = {key(c): c for c in emit}
    cat = json.load(open(a.catalogue))
    lines = [f"# Reconciliation ({len(E)} emittable contexts, catalogue {len(cat)} contexts)\n"]
    xtok_path = os.path.join(DATA, "alphabet_families_xtok.json")
    xtok = json.load(open(xtok_path)) if os.path.exists(xtok_path) else {}

    def base_key(k):
        for suf in ("_L1", "_L11", "_L12", "_A2"):
            if k.endswith(suf):
                return k[: -len(suf)] + "_act"
        return None

    def covered_by_xtok(k):
        # a missing joint key is covered when the parent's base context has an
        # input-in-token family (the FA child is then absorbed, not joined)
        b = base_key(k)
        return b is not None and b in xtok

    missing_all = sorted(k for k in E if k not in cat and k not in RIGID)
    joint_cov = sorted(k for k in missing_all if covered_by_xtok(k))
    missing = sorted(k for k in missing_all if k not in joint_cov)
    lines.append(f"* emittable keys without a family: {len(missing_all)}; of which joint keys covered by an "
                 f"input-in-token family of the parent's base context: {len(joint_cov)}; remaining: {len(missing)}")
    # every emittable free-child context must be able to absorb an FA child:
    # input-in-token family, or an A2 joint family (the L1/L11 joints are
    # emitted as their own keys and checked above)
    fa_parents = sorted(k for k in E if k.endswith("_act"))
    fa_unc = [k for k in fa_parents if k not in xtok and (k[:-4] + "_A2") not in cat]
    lines.append(f"* emittable free-child contexts: {len(fa_parents)}; without input-in-token family and without A2 joint: {len(fa_unc)}")
    # the FA joint "letter over the two-input owner" (h0_1_p0_A2) as a child
    # needs, at a parent without input-in-token family, the three-row joint L1A2
    l1a2_unc = [k for k in fa_parents if k not in xtok and (k[:-4] + "_L1A2") not in cat]
    lines.append(f"* ... without input-in-token family and without L1A2 joint (letter-over-A2 child): {len(l1a2_unc)}")
    for k in fa_unc[:60]:
        lines.append(f"    - {k}  width {E[k]['width']}")
    # two-input owners with two forced-antipode children need the "all"
    # variant (every input in a token) or a joint; L1 joints whose bottom
    # letter has a forced-antipode input need the "x" variant of the joint
    xall_path = os.path.join(DATA, "alphabet_families_xall.json")
    xall = json.load(open(xall_path)) if os.path.exists(xall_path) else {}
    two_in = sorted(k for k in E if k.endswith("_act2") or k.endswith("_A2"))
    two_unc = [k for k in two_in if k not in xall]
    lines.append(f"* emittable two-input contexts: {len(two_in)}; without an all-inputs-in-token variant: {len(two_unc)}")
    # an L1 joint keeps the letter's own active child as its input, so an FA
    # grandchild there must be absorbed by the joint itself; an L11 joint folds
    # in a bottom cell and has no input at all, so it needs nothing.
    l1_keys = sorted(k for k in E if k.endswith("_L1"))
    l1_unc = [k for k in l1_keys if k not in xtok]
    lines.append(f"* emittable L1 joints: {len(l1_keys)}; without an input-in-token variant (FA grandchild): {len(l1_unc)}")
    lines.append(f"* emittable L11 joints: {sum(1 for k in E if k.endswith('_L11'))} (no input, nothing required)")
    lines.append(f"    widths: {sorted(Counter(E[k]['width'] for k in missing).items())}")
    lines.append(f"    by kind/active: {Counter((E[k]['kind'], str(E[k]['active'])) for k in missing).most_common()}")
    for k in missing:
        lines.append(f"    - {k}  width {E[k]['width']}")
    lines.append(f"* emittable keys handled by the rigid row: {sorted(k for k in E if k in RIGID)}")
    lines.append(f"* catalogue contexts never emitted (slack): {sum(1 for k in cat if k not in E)}")
    if a.gate:
        g = json.load(open(a.gate))
        fp = g["menu_gate"]["failing_pairs"]
        real = [(c, p) for c, p in fp if c in E and p in E]
        lines.append(f"* menu-gate failing pairs: {len(fp)}; with both contexts emittable: {len(real)}")
        lines.append(f"    children: {Counter(c for c, p in real).most_common(20)}")
        lines.append(f"    parents: {Counter(p for c, p in real).most_common(20)}")
        json.dump(real, open(os.path.join(DATA, "gate_failing_realizable.json"), "w"))
    open(a.out, "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
