#!/usr/bin/env python3
"""Enumerate the finite context alphabet for the free-token programme.

A context is (residual arm multiset, number of recruited ports, active child
type).  Residues are representatives modulo six; six-edge mothers extend arms.

Bottom contexts (no active child):
  * portless singleton arm ell in {3,4,5,6,7,8};
  * singleton arm residue r in {1..6} with p in {1,2,3} recruited ports;
  * {1,3}, {odd,even}, {1,3,even} with p in {0..3};
  * the portless repairs (1,1,1), (2,2,2), (1,even,even), (2,odd,odd).
Continuing contexts (one active child with prescribed free head x):
  * residual R in {(r), {1,3}, {o,e}, {1,3,e}, empty} with p in {0,1,2}.

Each context records the label width and whether the composite can be
head+mirror (odd width) or needs one token (even width).  Output: JSON list
usable by the symbolic CP-SAT batch runner.
"""
import json
import sys

ODD = (1, 3, 5)
EVEN = (2, 4, 6)


def width(arms, ports, active, head=0):
    # free: the active child edge (input x); L1: shared edge + two arm labels + input x
    # L11: shared edge + two arm labels + one port of the (1;1 port) bottom child
    # V21/V22: child row (arms=1 or 2; two input heads): shared edge + (arm+1) labels + 2 inputs
    # act2: two input heads on this row
    # L12: the (1,2) opposite-parity bottom (shared edge + 2 + 3 arm labels)
    extra = {False: 0, "none": 0, True: 1, "free": 1, "L1": 4, "L11": 4, "L12": 6, "V21": 5, "V22": 6, "act2": 2, "A2": 7, "L1A2": 11}[active]
    return (head + 1) + sum(a + 1 for a in arms) + ports + extra


def contexts():
    out = []

    def add(arms, ports, active, kind, heads=(0, 1, 2, 3, 4, 5)):
      for head in heads:
        w = width(arms, ports, active, head)
        out.append({
            "arms": list(arms), "ports": ports, "active": active, "kind": kind, "head": head,
            "width": w,
            # composite signature: head y plus (w-1) other labels (+ x counted
            # inside w when active).  Even w-1 -> mirror possible; odd -> token.
            "needs_token": (w - 1) % 2 == 1,
        })

    for ell in (3, 4, 5, 6, 7, 8):
        add((ell,), 0, False, "bottom_singleton")
    for r in range(1, 7):
        for p in (1, 2, 3):
            add((r,), p, False, "bottom_singleton_ports")
    for p in range(4):
        add((1, 3), p, False, "bottom_pair13")
        for o in ODD:
            for e in EVEN:
                add((o, e), p, False, "bottom_oe")
        for e in EVEN:
            add((1, 3, e), p, False, "bottom_13e")
    # s4 / s6 / s8 owners with one retained neutral pair or four-short unit
    for e0 in (4, 6, 8):
        for o1 in ODD:
            for o2 in ODD:
                if o1 <= o2 and {o1, o2} != {1, 3}:
                    add((e0, o1, o2), 0, False, "bottom_even_neutral")
        for e1 in EVEN:
            for e2 in EVEN:
                if e1 <= e2:
                    add((e0, e1, e2), 0, False, "bottom_even_neutral")
        add((e0, 1, 1, 1, 3), 0, False, "bottom_even_neutral")
        add((e0, 1, 3, 3, 3), 0, False, "bottom_even_neutral")
    # general short/even singleton repairs: residual r plus one retained neutral unit
    # a retained pair with representatives (1,3) can arise from raw lengths (1,9),(7,3),... so it is included
    units = [(o1, o2) for o1 in ODD for o2 in ODD if o1 <= o2] + \
            [(e1, e2) for e1 in EVEN for e2 in EVEN if e1 <= e2] + [(1, 1, 1, 3), (1, 3, 3, 3)]
    for r in (1, 2, 4, 6, 8):
        for u in units:
            add((r,) + u, 0, False, "bottom_repair")
    # odd lone arm with a head chain (even width, rays only): retain a unit
    for r in (3, 5):
        for u in units:
            add((r,) + u, 0, False, "bottom_repair", heads=(1, 2, 3, 4, 5))
    # the forced-antipode (1,2) bottom widened by one retained neutral unit (numeric sort)
    for u in units:
        add(tuple(sorted((1, 2) + u)), 0, False, "bottom_oe_widened", heads=(0,))
    add((1, 1, 1), 0, False, "bottom_repair")
    add((2, 2, 2), 0, False, "bottom_repair")
    for e1 in EVEN:
        for e2 in EVEN:
            if e1 <= e2:
                add((1, e1, e2), 0, False, "bottom_repair")
    for o1 in ODD:
        for o2 in ODD:
            if o1 <= o2:
                add((2, o1, o2), 0, False, "bottom_repair")
    for child in ("free", "L1", "L11", "L12"):
      for p in (0, 1, 2):
        for r in range(1, 7):
            add((r,), p, child, "continuing_singleton")
        add((1, 3), p, child, "continuing_pair13")
        for o in ODD:
            for e in EVEN:
                add((o, e), p, child, "continuing_oe")
        for e in EVEN:
            add((1, 3, e), p, child, "continuing_13e")
    # undone neutral pair residuals {o,o},{e,e} (same parity, not {1,3}) with
    # no ports or an active child, and empty-residual cells over an L1 child
    for child in ("none", "free", "L1", "L11", "L12"):
        for p in (0, 1, 2):
            for o1 in ODD:
                for o2 in ODD:
                    if o1 <= o2 and {o1, o2} != {1, 3}:
                        add((o1, o2), p, child, "bottom_samepar" if child == "none" else "continuing_samepar")
            for e1 in EVEN:
                for e2 in EVEN:
                    if e1 <= e2:
                        add((e1, e2), p, child, "bottom_samepar" if child == "none" else "continuing_samepar")
    # undone four-short unit as the residual (when a lone port must be absorbed)
    for child in ("none", "free", "L1", "L11"):
        for p in (0, 1, 2):
            for u in ((1, 1, 1, 3), (1, 3, 3, 3)):
                add(u, p, child, "bottom_fourshort" if child == "none" else "continuing_fourshort")
    for p in (0, 1, 2, 3):
        add((), p, "L1", "continuing_empty_L1")
        add((), p, "L11", "continuing_empty_L11")
        add((), p, "L12", "continuing_empty_L12")
    # two-input children (vertex with a short residual arm and two cancelled-impossible active heads)
    for child in ("V21", "V22"):
        for p in (0, 1, 2):
            for r in range(1, 7):
                add((r,), p, child, "continuing_singleton")
            add((1, 3), p, child, "continuing_pair13")
            for o in ODD:
                for e in EVEN:
                    add((o, e), p, child, "continuing_oe")
            for e in EVEN:
                add((1, 3, e), p, child, "continuing_13e")
            for pr in [(o1, o2) for o1 in ODD for o2 in ODD if o1 <= o2 and {o1, o2} != {1, 3}] + \
                      [(e1, e2) for e1 in EVEN for e2 in EVEN if e1 <= e2]:
                add(pr, p, child, "continuing_samepar")
        for p in (1, 2, 3):
            add((), p, child, "continuing_empty_V2")
    # direct two-input contexts (h>=1 only: h=0 with R={1},{2} is exactly infeasible)
    for r in (1, 2, 3, 4, 5, 6, 8):
        add((r,), 0, "act2", "continuing_act2", heads=(1, 2, 3, 4, 5))
    for r in (1, 2, 3, 4, 5, 6, 8):
        # r in {1, 2} at h == 0: the rigid rows (head forced by the inputs),
        # 2026-09-02; see data/batches/alphabet_rigid.jsonl
        add((r,), 0, "act2", "continuing_act2", heads=(0,))
    # A2 joints: the forced-antipode owner h2_1_p0_act2 joined into a parent
    # too small to carry an input-in-token family (free-child contexts of
    # width <= 7, and the empty residual with one or three ports)
    for h in range(6):
        for p in (1, 3):
            w = (h + 1) + p + 7
            out.append({"arms": [], "ports": p, "active": "A2", "kind": "continuing_empty_A2", "head": h,
                        "width": w, "needs_token": (w - 1) % 2 == 1})
    # root contexts: no head, output zero, recruited leaves 0..2
    residuals = [(r,) for r in range(1, 7)] + [(1, 3)] + [(o, e) for o in ODD for e in EVEN] + [(1, 3, e) for e in EVEN]
    # roots with one retained neutral pair (or an undone pair): (r,o,o),(r,e,e),(o,o),(e,e)
    pairs = [(o1, o2) for o1 in ODD for o2 in ODD if o1 <= o2 and {o1, o2} != {1, 3}] + \
            [(e1, e2) for e1 in EVEN for e2 in EVEN if e1 <= e2]
    residuals += [tuple(sorted((r,) + pr)) for r in range(1, 7) for pr in pairs] + pairs + [(1, 1, 1, 3), (1, 3, 3, 3)]
    residuals += [(r,) + u for r in range(1, 7) for u in ((1, 1, 1, 3), (1, 3, 3, 3))]
    # root with the forced-antipode pair (1,2) plus one retained unit
    residuals += [tuple(sorted((1, 2) + u)) for u in pairs] + [tuple(sorted((1, 2, 1, 1, 1, 3))), tuple(sorted((1, 2, 1, 3, 3, 3)))]
    for child in ("none", "free", "L1", "L11", "L12", "V21", "V22", "act2"):
        for p in (0, 1, 2):
            for R in residuals + [()]:
                if R == () and child == "none":
                    continue
                w = sum(a + 1 for a in R) + p + {"none": 0, "free": 1, "L1": 4, "L11": 4, "L12": 6, "V21": 5, "V22": 6, "act2": 2}[child]
                out.append({"arms": list(R), "ports": p, "active": child, "kind": "root", "head": 0,
                            "width": w, "needs_token": w % 2 == 1})
    # 2026-09-02: the A2 joint is available at EVERY free-child context, and the
    # port joint at every two-input context, since the absorption rule joins
    # whenever the parent has no input-in-token family.  Generated last, so
    # that the root contexts are included.
    for c in [c for c in out if c["active"] == "free"]:
        d = dict(c); d["active"] = "A2"; d["width"] = c["width"] - 1 + 7
        d["needs_token"] = ((d["width"] - 1) % 2 == 1) if c["kind"] != "root" else (d["width"] % 2 == 1)
        out.append(d)
    for c in [c for c in out if c["active"] == "act2"]:
        d = dict(c); d["active"] = "A2"; d["ports"] = c["ports"] + 1
        d["width"] = c["width"] - 2 + 1 + 7
        d["needs_token"] = ((d["width"] - 1) % 2 == 1) if c["kind"] != "root" else (d["width"] % 2 == 1)
        out.append(d)
    return out


if __name__ == "__main__":
    ctx = contexts()
    json.dump(ctx, open(sys.argv[1] if len(sys.argv) > 1 else "alphabet_contexts.json", "w"), indent=0)
    from collections import Counter
    print(len(ctx), "contexts;", Counter(c["kind"] for c in ctx))
    print("width distribution:", sorted(Counter(c["width"] for c in ctx).items()))
