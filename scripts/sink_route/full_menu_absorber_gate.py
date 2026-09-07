#!/usr/bin/env python3
"""Absorber collision gate over EVERY MENU ENTRY of the catalogue.

``absorber_gate.py`` runs the same test over one family per context, the one
the scheduler prefers there.  This driver runs it over every entry of every
menu, in a fixed order, and writes a certificate that records

* the SHA-256 of the catalogue file it read,
* the parent and child pool sizes and the total number of ordered pairs,
* the histogram of collision-free role orders (0..36),
* the minimum number of collision-free orders over all pairs,
* the full list of pairs with no collision-free order (empty means PASS).

The pair test itself is imported from :mod:`absorber_gate`, so this file adds
the menu enumeration and the bookkeeping only.  ``verify_full_menu_gate.py``
recomputes the same quantities from scratch and shares no code with either.

usage:
    .venv/bin/python scripts/sink_route/full_menu_absorber_gate.py \
        --out research/antimagic/data/sink_route/full_menu_gate.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import absorber_gate as ag                                   # noqa: E402


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def menu_of(rec: dict):
    """Every family of a catalogue record, the preferred one first."""
    menu = rec.get("menu")
    if menu:
        return list(menu)
    fam = rec.get("family")
    return [fam] if fam else []


def build_pools_all_menus(catalog: dict):
    """The same pools as :func:`absorber_gate.build_pools`, over every menu.

    A menu entry may be stored either as the family dict itself or wrapped as
    ``{"family": ...}``; both shapes appear in the catalogue.  Entries are
    de-duplicated by (context, index) and enumerated in sorted context order,
    so the run is reproducible.
    """
    parents, children = [], []
    for ctx_key in sorted(catalog):
        rec = catalog[ctx_key]
        ctx = rec.get("ctx", {})
        for idx, entry in enumerate(menu_of(rec)):
            fam = entry.get("family") if isinstance(entry, dict) and "family" in entry else entry
            if not isinstance(fam, dict) or "coefficients_by_label" not in fam:
                continue
            if not fam.get("token_named"):
                continue
            params = fam.get("parameters", [])
            tag = f"{ctx_key}#{idx}"
            if ctx.get("active") == "free" and params.count("x") == 1:
                ent = ag.build_pool_entry(tag, fam)
                if ent is not None:
                    ent["x_idx"] = params.index("x")
                    parents.append(ent)
            if "y" in params:
                ent = ag.build_pool_entry(tag, fam)
                if ent is not None:
                    ent["y_idx"] = params.index("y")
                    children.append(ent)
    return parents, children


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalogue", default=ag.CATALOGUE)
    ap.add_argument("--out", required=True)
    ap.add_argument("--progress", type=int, default=40)
    a = ap.parse_args()

    t0 = time.time()
    digest = sha256(a.catalogue)
    with open(a.catalogue) as f:
        catalog = json.load(f)
    parents, children = build_pools_all_menus(catalog)
    ag.log(f"catalogue sha256 {digest}")
    ag.log(f"parent pool {len(parents)}, child pool {len(children)}, "
           f"{len(parents)*len(children)} ordered pairs")

    pdenoms = sorted({e["denom"] for e in parents})
    cdenoms = sorted({e["denom"] for e in children})
    for e in parents:
        ag.precompute_scaled_cores(e, cdenoms)
    for e in children:
        ag.precompute_scaled_cores(e, pdenoms)

    hist: dict = {}
    zero_pairs = []
    n_pairs = 0
    minimum = 37
    step = max(1, (len(parents) * len(children)) // max(1, a.progress))
    for P in parents:
        for C in children:
            free_count = ag.analyze_pair(P, C)[0]
            n_pairs += 1
            hist[free_count] = hist.get(free_count, 0) + 1
            if free_count < minimum:
                minimum = free_count
            if free_count == 0:
                zero_pairs.append([P["ctx"], C["ctx"]])
            if n_pairs % step == 0:
                ag.log(f"  {n_pairs} pairs, min so far {minimum}, "
                       f"{time.time()-t0:.0f}s")

    out = {
        "script": "full_menu_absorber_gate.py",
        "catalogue": os.path.abspath(a.catalogue),
        "catalogue_sha256": digest,
        "parent_pool": len(parents),
        "child_pool": len(children),
        "pairs": n_pairs,
        "min_free_orders": minimum if n_pairs else None,
        "histogram_free_orders": {str(k): hist[k] for k in sorted(hist)},
        "zero_free_pairs": zero_pairs,
        "pass": len(zero_pairs) == 0,
        "seconds": round(time.time() - t0, 1),
    }
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w") as f:
        json.dump(out, f, indent=1)
    ag.log(f"wrote {a.out}: pairs={n_pairs} min={minimum} "
           f"pass={out['pass']} in {out['seconds']}s")
    return 0 if out["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
