#!/usr/bin/env python3
"""Independent verifier for ``full_menu_absorber_gate.py``.

Shares no code with :mod:`absorber_gate`: labels are carried as exact
``Fraction`` vectors over an explicit joint coordinate list rather than as
scaled integer vectors, the pools are rebuilt from the catalogue here, and the
collision test is written out again.  It recomputes the whole run and compares
its own totals with the certificate.

usage:
    .venv/bin/python scripts/sink_route/verify_full_menu_gate.py \
        --cert research/antimagic/data/sink_route/full_menu_gate.json
exit status 0 iff the certificate is reproduced exactly.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import os
import sys
import time
from fractions import Fraction

ORDERS = [(i, j) for i in range(3) for j in range(3) if i != j]   # 6


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def families(rec):
    menu = rec.get("menu")
    if menu:
        for e in menu:
            yield e.get("family") if isinstance(e, dict) and "family" in e else e
    elif rec.get("family"):
        yield rec["family"]


def entry(tag, fam):
    """``(tag, params, {label: [Fraction, ...]}, [3 token labels])`` or None."""
    tn = fam.get("token_named")
    if not tn:
        return None
    params = fam.get("parameters", [])
    coeffs = fam.get("coefficients_by_label", {})
    den = Fraction(fam.get("denominator", 1))
    toks = [tn.get("a"), tn.get("b"), tn.get("c")]
    if any(t not in coeffs for t in toks):
        return None
    vecs = {}
    for lbl, raw in coeffs.items():
        if len(raw) != len(params):
            return None
        vecs[lbl] = [Fraction(int(x)) / den for x in raw]
    return (tag, params, vecs, toks)


def pools(catalog):
    par, chi = [], []
    for key in sorted(catalog):
        rec = catalog[key]
        act = (rec.get("ctx") or {}).get("active")
        for idx, fam in enumerate(families(rec)):
            if not isinstance(fam, dict) or "coefficients_by_label" not in fam:
                continue
            e = entry(f"{key}#{idx}", fam)
            if e is None:
                continue
            params = e[1]
            if act == "free" and params.count("x") == 1:
                par.append(e)
            if "y" in params:
                chi.append(e)
    return par, chi


def joint(P, C):
    """Coordinate map, by POSITION not by name.

    A family may list the same parameter name twice (59 of them do, e.g.
    ``[y, t1, t2, u1, t1]``); those are two independent unknowns and the
    columns must stay separate, so the map is positional: the parent keeps its
    own columns, the child's column ``y_idx`` lands on the parent's ``x``
    column, and every other child column gets a fresh one.
    """
    pp, cp = P[1], C[1]
    x_idx = pp.index("x")
    y_idx = cp.index("y")
    n_p, n_c = len(pp), len(cp)
    d = n_p + n_c - 1

    def lift_p(vec):
        out = [Fraction(0)] * d
        for i in range(n_p):
            out[i] += vec[i]
        return tuple(out)

    def lift_c(vec):
        out = [Fraction(0)] * d
        for k in range(n_c):
            if k == y_idx:
                out[x_idx] += vec[k]
            else:
                out[n_p + (k if k < y_idx else k - 1)] += vec[k]
        return tuple(out)

    return lift_p, lift_c


def neg(v):
    return tuple(-x for x in v)


def comb(*terms):
    """Linear combination of ``(coefficient, vector)`` pairs."""
    d = len(terms[0][1])
    out = [Fraction(0)] * d
    for coef, v in terms:
        for i in range(d):
            out[i] += coef * v[i]
    return tuple(out)


def free_orders(P, C):
    lift_p, lift_c = joint(P, C)
    lab_p = {k: lift_p(v) for k, v in P[2].items()}
    lab_c = {k: lift_c(v) for k, v in C[2].items()}
    forbidden = set()
    for v in list(lab_p.values()) + list(lab_c.values()):
        forbidden.add(v)
        forbidden.add(neg(v))
    dim = len(P[1]) + len(C[1]) - 1
    zero = tuple([Fraction(0)] * dim)
    forbidden.add(zero)
    tp = [lab_p[t] for t in P[3]]
    tc = [lab_c[t] for t in C[3]]
    good = 0
    for i, j in ORDERS:
        a, b = tp[i], tp[j]
        for k, l in ORDERS:
            c, d_ = tc[k], tc[l]
            f1 = comb((Fraction(1), a), (Fraction(1), b), (Fraction(1), d_))
            f3 = comb((Fraction(2), a), (Fraction(1), b), (Fraction(-1), c))
            forms = [f1, neg(f1), f3, neg(f3)]
            if len(set(forms)) != 4:
                continue
            if any(f in forbidden for f in forms):
                continue
            good += 1
    return good


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cert", required=True)
    ap.add_argument("--catalogue", default=None)
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--shards", type=int, default=1)
    ap.add_argument("--partial", default=None,
                    help="write this shard's histogram here instead of "
                         "comparing with the certificate")
    a = ap.parse_args()
    if a.shards < 1 or not (0 <= a.shard < a.shards):
        ap.error("--shard must be in [0, --shards)")
    cert = json.load(open(a.cert))
    cat_path = a.catalogue or cert["catalogue"]
    digest = sha256(cat_path)
    problems = []
    if digest != cert["catalogue_sha256"]:
        problems.append(f"catalogue sha256 {digest} != {cert['catalogue_sha256']}")
    catalog = json.load(open(cat_path))
    par, chi = pools(catalog)
    if len(par) != cert["parent_pool"]:
        problems.append(f"parent pool {len(par)} != {cert['parent_pool']}")
    if len(chi) != cert["child_pool"]:
        problems.append(f"child pool {len(chi)} != {cert['child_pool']}")
    t0 = time.time()
    hist = {}
    zeros = []
    n = 0
    minimum = 37
    mine = [P for i, P in enumerate(par) if i % a.shards == a.shard]
    step = max(1, (len(mine) * len(chi)) // 20)
    for P in mine:
        for C in chi:
            g = free_orders(P, C)
            n += 1
            hist[g] = hist.get(g, 0) + 1
            minimum = min(minimum, g)
            if g == 0:
                zeros.append([P[0], C[0]])
            if n % step == 0:
                print(f"  {n} pairs, min {minimum}, {time.time()-t0:.0f}s",
                      file=sys.stderr, flush=True)
    if a.partial is not None:
        with open(a.partial, "w") as fh:
            json.dump({"shard": a.shard, "shards": a.shards,
                       "catalogue_sha256": digest,
                       "parent_pool": len(par), "child_pool": len(chi),
                       "pairs": n, "min_free_orders": minimum,
                       "histogram_free_orders": {str(k): hist[k]
                                                 for k in sorted(hist)},
                       "zero_free_pairs": zeros,
                       "seconds": round(time.time() - t0, 1)}, fh)
        print(f"shard {a.shard}/{a.shards}: {n} pairs, min {minimum}, "
              f"{len(zeros)} zero-free, {time.time()-t0:.0f}s",
              file=sys.stderr, flush=True)
        return 0
    if n != cert["pairs"]:
        problems.append(f"pairs {n} != {cert['pairs']}")
    if minimum != cert["min_free_orders"]:
        problems.append(f"min {minimum} != {cert['min_free_orders']}")
    mine = {str(k): hist[k] for k in sorted(hist)}
    if mine != cert["histogram_free_orders"]:
        problems.append("histogram differs")
    if sorted(map(tuple, zeros)) != sorted(map(tuple, cert["zero_free_pairs"])):
        problems.append("zero-free pair list differs")
    print(json.dumps({"pairs": n, "min_free_orders": minimum,
                      "zero_free_pairs": len(zeros),
                      "histogram_free_orders": mine,
                      "agrees_with_certificate": not problems,
                      "problems": problems,
                      "seconds": round(time.time() - t0, 1)}, indent=1))
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
