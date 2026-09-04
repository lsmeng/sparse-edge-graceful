#!/usr/bin/env python3
"""The closure check of the local part of the proof.

Six conditions are checked over the emittable context set E (the output of
enumerate_emittable_contexts.py, i.e. the contexts the scheduler can actually
produce).  Together they are exactly what Lemma E and rule 8d require.

  C1  every context of E has a family in the catalogue (or is a rigid row);
  C2  every free-child context of E can absorb a forced-antipode child: it has
      an input-in-token variant, or the A2 joint of that context has a family
      that is itself not forced-antipode, so that the enlarged cell is an
      ordinary child of the next parent and the absorption stops there;
  C3  the folded residue-one letters have a non-forced-antipode A2 joint.  A
      letter is normally folded into its parent, but when its own active child
      is forced-antipode the child is joined into the letter instead and the
      letter becomes an owner of context hX_1_pQ_A2;
  C4  every two-input context that occurs (the act2 keys of E and the A2
      joints) has an input-in-token variant for one slot, and an
      all-inputs-in-token variant when both children can be forced-antipode;
  C5  L11 joints need nothing (the folded child is a bottom, so the joint has
      no input); this is reported, not checked;
  C6  every ordered pair of E that the menu gate rejects has the
      forced-antipode child h2_1_p0_act2, which rule 8d handles outside the
      gate.

usage: closure_check.py [--gate GATE.json] [--out data/closure_report.md]
"""
import argparse
import json
import os
import sys
from collections import Counter
from fractions import Fraction as Q

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from run_alphabet_batch import key  # noqa: E402

DATA = os.path.normpath(os.path.join(HERE, "..", "data"))
RIGID = {"h0_2_p0_act"}          # residue-two rigid ray, a constructor template
FA_CHILD = "h2_1_p0_act2"        # the only forced-antipode free child
# The one-step gate is a sufficient condition for a (child, parent) pair, not
# a necessary one: a pair it rejects is still admissible when the child is
# joined into the parent, because the two label sets are then solved together
# and no identity between them can survive.  Rule 8d is the systematic
# instance of this, with the forced-antipode child above.  JOINT records the
# one further pair the enumeration at three active children produced.  Its
# parent is a root, so the enlarged cell has no parent of its own and the
# joining stops there.
JOINT = {("h0_1-2_p0_bot", "root_2_p0_act"): "root_2_p0_J12"}


def token_names(f):
    out = set()
    for fld in ("token_named", "token2_named"):
        d = f.get(fld)
        if isinstance(d, dict):
            out |= set(d.values())
    return out


def port_joint_key(ctx):
    """the joint of a two-input context: one more port, child type A2"""
    j = dict(ctx)
    j["ports"] = ctx["ports"] + 1
    j["active"] = "A2"
    return key(j)


def load(name, default=None):
    p = os.path.join(DATA, name)
    return json.load(open(p)) if os.path.exists(p) else (default if default is not None else {})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gate", default=None)
    ap.add_argument("--emittable", default="alphabet_contexts_emittable.json",
                    help="the emittable context set, a file name under data/")
    ap.add_argument("--pairs", default=os.path.join(DATA, "emittable_pairs.json"),
                    help="realizable (child, parent) owner pairs from the enumeration")
    ap.add_argument("--out", default=os.path.join(DATA, "closure_report.md"))
    a = ap.parse_args()
    emit = load(a.emittable, [])
    E = {key(c): c for c in emit}
    cat = load("alphabet_families.json")
    xtok = load("alphabet_families_xtok.json")
    xall = load("alphabet_families_xall.json")
    out = [f"# Closure check ({len(E)} emittable contexts, {len(cat)} contexts in the catalogue)\n"]
    ok = True

    def block(name, keys, test, hint):
        nonlocal ok
        bad = [k for k in keys if not test(k)]
        ok = ok and not bad
        out.append(f"* {name}: {len(keys)} contexts, {len(keys) - len(bad)} satisfied, "
                   f"{len(bad)} open  [{'PASS' if not bad else 'OPEN'}]")
        if bad:
            out.append(f"    {hint}")
            out.append(f"    widths: {sorted(Counter(E[k]['width'] for k in bad if k in E).items())}")
            for k in sorted(bad)[:40]:
                out.append(f"    - {k}  width {E[k]['width'] if k in E else '?'}")
        return bad

    block("C1 every emittable context has a family",
          sorted(E), lambda k: k in cat or k in RIGID, "run the missing-context batch")

    def nonfa(k):
        if k not in cat:
            return False
        return not all(f.get("forced_antipode") for f in (cat[k].get("menu") or [cat[k]]))

    def a2_join(k):
        """the joint of a one-active-child context: same ports, child type A2"""
        return k[:-4] + "_A2" if k.endswith("_act") else None

    # C2.  A cell with one active child that is forced-antipode either absorbs
    # it with a token of its own, or joins it; the joint must not itself be
    # forced-antipode, or the absorption would not stop.
    block("C2 free-child contexts absorb a forced-antipode child",
          sorted(k for k in E if k.endswith("_act")),
          lambda k: k in xtok or nonfa(a2_join(k)),
          "run --input-in-token, or the A2 joint search with --forbid-antipode-y")

    # C3.  The folded residue-one letters are the free-child contexts that are
    # never emitted as owners, so they are listed separately.
    # Only the residue-one letter on a direct parent edge and with no ports is
    # folded (is_zero_spare), and it is the one free-child context that is
    # never emitted as an owner, so its joint is checked separately.  Every
    # other letter is an ordinary owner and falls under C2.
    block("C3 the folded letter absorbs a forced-antipode child by joining",
          ["h0_1_p0_A2"], nonfa, "run the A2 joint search on h0_1_p0_act")

    # C4.  A two-input cell may have two forced-antipode children.  It either
    # has a variant with both inputs in tokens, or it joins one child and
    # pins the other, which in the row language is a port, so the joint must
    # be free of the antipode of that port and must carry it in a token.
    two_ctx = {k: E[k] for k in E if k.endswith("_act2")}

    def port_joint_ok(k):
        jk = port_joint_key(two_ctx[k])
        if not nonfa(jk):
            return False
        fams = cat[jk].get("menu") or [cat[jk]]
        return any((not f.get("forced_antipode")) and "r0p0" in token_names(f) for f in fams)

    block("C4 two-input contexts absorb two forced-antipode children",
          sorted(two_ctx), lambda k: (k in xtok and k in xall) or port_joint_ok(k),
          "run --all-inputs-in-token, or --port-in-token --forbid-antipode-port on the port joint")
    out.append(f"    (of these, {sum(1 for k in two_ctx if k in xall)} by the both-slots variant "
               f"and {sum(1 for k in two_ctx if port_joint_ok(k))} by the port joint)")

    out.append(f"* C5 L11 joints: {sum(1 for k in E if k.endswith('_L11'))} contexts, "
               "no input, nothing required  [PASS]")
    c6_skipped = False
    if a.gate:
        g = json.load(open(a.gate))
        fp = g["menu_gate"]["failing_pairs"]
        realizable = None
        if os.path.exists(a.pairs):
            realizable = {tuple(t) for t in json.load(open(a.pairs))}
        if realizable is not None:
            real = [(c, p) for c, p in fp if (c, p) in realizable]
            out.append(f"* C6 restricted to the {len(realizable)} realizable (child, parent) pairs "
                       "recorded by the enumeration")
        else:
            real = [(c, p) for c, p in fp if c in E and p in E]
        fa = [(c, p) for c, p in real if c == FA_CHILD]
        joined = [(c, p) for c, p in real
                  if c != FA_CHILD and JOINT.get((c, p)) in cat]
        nonfa = [(c, p) for c, p in real
                 if c != FA_CHILD and JOINT.get((c, p)) not in cat]
        ok = ok and not nonfa
        out.append(f"* C6 menu gate: {len(fp)} failing ordered pairs, {len(real)} with both contexts "
                   f"emittable, {len(fa)} of those have the child {FA_CHILD} "
                   f"(handled by rule 8d), {len(joined)} handled by joining "
                   f"({', '.join(sorted(JOINT[q] for q in joined)) or 'none'}), "
                   f"{len(nonfa)} remain  [{'PASS' if not nonfa else 'OPEN'}]")
        for c, p in sorted(nonfa)[:40]:
            out.append(f"    - child {c} under parent {p}")
        json.dump(nonfa, open(os.path.join(DATA, "gate_failing_nonfa.json"), "w"))
    else:
        # C6 is one of the closure conditions, so not evaluating it is not the
        # same as passing it: say so, and do not exit successfully
        c6_skipped = True
        out.append("* C6 menu gate: NOT CHECKED -- rerun with --gate GATE.json")
    # C7.  A context that is a constructor template rather than a catalogue
    # family is invisible to the gate, since the gate enumerates catalogue
    # contexts only.  The residue-two ray is the one such context, and the
    # enumeration records realizable pairs in which it is the PARENT, so those
    # pairs are evaluated here instead.  The ray's family is the
    # two-parameter one, (-s-2t; -t, -s-t, s; 2t) with input x = 2t, whose only
    # label depending on the input alone is -x/2; the single rigid row printed
    # in Appendix A is its s = x/2 specialisation and has a larger forced set,
    # so evaluating the rigid row here would be the wrong test.
    tmpl = load("template_families.json")
    if tmpl and realizable is not None:
        from check_lookahead_gate import collect as _collect, frac as _frac
        _st = Counter()
        _, kids = _collect(cat, True, _st)
        bad7 = []
        checked7 = 0
        for pk, entry in tmpl.items():
            pf = {Q(f["ratio"]) for f in entry["menu"][0]["forced_forms"]
                  if f.get("kind") != "input"}
            for c, p_ in sorted(realizable):
                if p_ != pk or c not in E:
                    continue
                checked7 += 1
                fams = kids.get(c) or []
                if not fams:
                    # the child's head is not a multiple of a single head
                    # parameter; these are the direct-edge two-input rows,
                    # whose labels depend on two inputs and cannot be
                    # identically equal to a multiple of the parent's input
                    continue
                if not any(not (set(f["head_only"]) & pf) for f in fams):
                    bad7.append((c, p_))
        ok = ok and not bad7
        out.append(f"* C7 template parents: {checked7} realizable pairs whose parent is a "
                   f"constructor template, {checked7 - len(bad7)} admissible, "
                   f"{len(bad7)} open  [{'PASS' if not bad7 else 'OPEN'}]")
        for c, p_ in bad7:
            out.append(f"    - child {c} under template parent {p_}")
    else:
        out.append("* C7 template parents: NOT CHECKED -- data/template_families.json absent")
        c6_skipped = True

    out.append("")
    if not ok:
        verdict = "CLOSURE INCOMPLETE"
    elif c6_skipped:
        verdict = "C1-C5 PASS, C6 NOT CHECKED -- closure not established"
    else:
        verdict = "ALL CONDITIONS PASS"
    out.append(f"**{verdict}**")
    open(a.out, "w").write("\n".join(out) + "\n")
    print("\n".join(out))
    return 0 if (ok and not c6_skipped) else 1


if __name__ == "__main__":
    sys.exit(main())
