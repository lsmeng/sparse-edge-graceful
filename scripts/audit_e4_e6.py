#!/usr/bin/env python3
"""Sweep EVERY menu family and test (E4) and (E6) exactly as the manuscript states them.

(E4) the three coefficient vectors of each token span a plane (rank 2 of the
     token alone, head NOT included), and the recorded carrier is a set of at
     most two parameters on which they already span a plane.
(E6) the only label depending on an input alone is the antipode of that input,
     and no non-head label is a rational multiple of the head.

The shipped checker verifies neither: its rank test folds the exposed head row
into the token rank, and it has no E6 test at all.  This script is the audit.
"""
import json, os, sys
from fractions import Fraction as Q

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.normpath(os.path.join(HERE, "..", "data"))

def rank(rows):
    m = [[Q(x) for x in r] for r in rows]; rk = 0
    for c in range(len(m[0]) if m else 0):
        p = next((r for r in range(rk, len(m)) if m[r][c]), None)
        if p is None: continue
        m[rk], m[p] = m[p], m[rk]; pv = m[rk][c]
        for r in range(len(m)):
            if r != rk and m[r][c]:
                f = m[r][c] / pv
                m[r] = [a - f*b for a, b in zip(m[r], m[rk])]
        rk += 1
    return rk

def menus(entry):
    return entry.get("menu") or [entry]

def audit(fam):
    """Return (e4_problems, e6_problems) as lists of strings."""
    e4, e6 = [], []
    params = fam.get("parameters") or []
    cbl = fam.get("coefficients_by_label") or {}
    labels = fam.get("labels") or []
    L = int(fam.get("denominator") or 1)
    idx = {p: i for i, p in enumerate(params)}
    head_name = next((l["name"] for l in labels if l.get("kind") == "head"), None)
    # the pinned input label IS the input; like the head it is not subject to
    # the E6 clause about labels that depend on an input alone
    pinned = {l["name"] for l in labels if l.get("kind") == "input"} | {"x", "x1", "x2"}
    is_root = bool(fam.get("root_row"))

    # ---- E4 ----
    for tag, key in (("token", "token_indices"), ("token2", "token2_indices")):
        ti = fam.get(key)
        if not isinstance(ti, dict): continue
        try:
            rows = [cbl[labels[ti[r]]["name"]] for r in ("a", "b", "c")]
        except Exception:
            e4.append(f"{tag}: indices unresolvable"); continue
        r_alone = rank(rows)
        if r_alone != 2:
            e4.append(f"{tag}: rank {r_alone} of the triple alone (E4 wants 2)")
        carrier = fam.get("carrier") or fam.get("carrier_named")
        if carrier:
            cols = [idx[p] for p in carrier if p in idx]
            if cols:
                sub = [[row[c] for c in cols] for row in rows]
                if rank(sub) != 2:
                    e4.append(f"{tag}: carrier {carrier} does not carry a plane")
    # ---- E6 ----
    inputs = [p for p in ("x", "x1", "x2") if p in idx]
    in_cols = {idx[p] for p in inputs}
    y_col = idx.get("y")
    for l in labels:
        nm = l["name"]
        if nm == head_name or nm in pinned: continue
        v = cbl.get(nm)
        if v is None: continue
        sup = {i for i, c in enumerate(v) if c}
        if not sup: continue
        if sup <= in_cols:                       # depends on inputs alone
            ok = False
            if len(sup) == 1:
                c = sup.pop(); ok = (v[c] == -L)
            if not ok:
                e6.append(f"{nm}: input-only label {v} is not the antipode of an input")
        if (not is_root) and y_col is not None and sup and sup <= {y_col}:
            e6.append(f"{nm}: non-head label is a rational multiple of the head")
    return e4, e6

def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(DATA, "alphabet_families.json")
    cat = json.load(open(path))
    tot = bad4 = bad6 = 0
    ctx4, ctx6 = set(), set()
    examples4, examples6 = [], []
    prim4 = prim6 = 0
    for k in sorted(cat):
        for i, f in enumerate(menus(cat[k]), 1):
            fam = f.get("family") or f
            if not isinstance(fam, dict) or "coefficients_by_label" not in fam: continue
            tot += 1
            e4, e6 = audit(fam)
            if e4:
                bad4 += 1; ctx4.add(k); prim4 += (i == 1)
                if len(examples4) < 8: examples4.append(f"{k} menu{i}: {e4[0]}")
            if e6:
                bad6 += 1; ctx6.add(k); prim6 += (i == 1)
                if len(examples6) < 8: examples6.append(f"{k} menu{i}: {e6[0]}")
    print(f"catalogue: {path}")
    print(f"menu families swept          : {tot}")
    print(f"(E4) violations              : {bad4}  over {len(ctx4)} contexts   [{prim4} are the PRIMARY family]")
    for e in examples4: print("    ", e)
    print(f"(E6) violations              : {bad6}  over {len(ctx6)} contexts   [{prim6} are the PRIMARY family]")
    for e in examples6: print("    ", e)

if __name__ == "__main__":
    main()
