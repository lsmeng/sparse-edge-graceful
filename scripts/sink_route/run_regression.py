#!/usr/bin/env python3
"""Regression programme for the sink route (:mod:`sink_constructor`).

Families
--------
* comb+bush     ``k in {5, 9, 15}``, ``bush = 12k`` (one extra leaf if n is even)
* comb+binary   ``depth in {7, 8, 9}`` x ``k in {5, 9, 15}``
* sparse trees  ``n in {101, 201, 401}``, five each
                (``free_token_constructor.sparse_trees(orders, 5, 1, 25)``)
* census        every free tree of order ``n in {7, 9, 11}``

Every certificate is written to ``data/sink_route/regression/`` and a summary
to ``data/sink_route/regression/summary.json``.

    .venv/bin/python scripts/sink_route/run_regression.py \
        --block-time 20 --outdir research/antimagic/data/sink_route/regression
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import sys
import time
from collections import Counter


class TreeTimeout(Exception):
    """The per-tree wall-clock cap ran out."""


def _alarm(_sig, _frame):
    raise TreeTimeout()

HERE = os.path.dirname(os.path.abspath(__file__))
for _p in (HERE, os.path.normpath(os.path.join(HERE, ".."))):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import free_token_constructor as ftc            # noqa: E402
import sink_constructor as sk                   # noqa: E402

DATA = os.path.normpath(os.path.join(HERE, "..", "..", "data"))
DEFAULT_OUT = os.path.join(DATA, "sink_route", "regression")


def families(which):
    if "combbush" in which:
        trees = []
        for k in (5, 9, 15):
            trees.append((f"combbush_k{k}", sk.combbush_tree(k, 12 * k)))
        yield "combbush", trees
    if "combbin" in which:
        trees = []
        for d in (7, 8, 9):
            for k in (5, 9, 15):
                trees.append((f"combbin_d{d}_k{k}", sk.combbin_tree(d, k)))
        yield "comb_binary", trees
    if "sparse" in which:
        yield "sparse", list(ftc.sparse_trees([101, 201, 401], 5, 1, 25))
    if "census" in which:
        yield "census", list(ftc.census_trees([7, 9, 11]))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--block-time", type=float, default=20.0)
    ap.add_argument("--tries", type=int, default=800)
    ap.add_argument("--seed", type=int, default=20260901)
    ap.add_argument("--roots", type=int, default=4)
    ap.add_argument("--outdir", default=DEFAULT_OUT)
    ap.add_argument("--families", default="combbush,combbin,sparse,census")
    ap.add_argument("--tree-cap", type=float, default=240.0,
                    help="per-tree wall-clock cap; a tree over it is a "
                         "'timeout' failure")
    ap.add_argument("--census-budget", type=float, default=600.0,
                    help="skip the census if it would take longer than this")
    a = ap.parse_args(argv)
    which = set(a.families.split(","))
    os.makedirs(a.outdir, exist_ok=True)
    catalogue = ftc.load_catalogue()

    summary = {}
    for fam, trees in families(which):
        print(f"\n=== {fam} ({len(trees)} trees) ===", flush=True)
        rows = []
        t0 = time.time()
        for name, par in trees:
            if fam == "census" and time.time() - t0 > a.census_budget:
                print(f"  census budget of {a.census_budget}s exceeded, "
                      f"stopping after {len(rows)} trees", flush=True)
                break
            t1 = time.time()
            signal.signal(signal.SIGALRM, _alarm)
            signal.alarm(int(a.tree_cap))
            try:
                cert = sk.construct_sink(par, catalogue=catalogue, seed=a.seed,
                                         tries=a.tries,
                                         block_time=a.block_time,
                                         root_candidates=a.roots)
            except TreeTimeout:
                cert = {"ok": False, "n": len(par), "mode": "sink",
                        "parent": list(par),
                        "failure": {"step": "timeout",
                                    "detail": f"more than {a.tree_cap}s of "
                                              "wall clock",
                                    "vertex": None, "context": None}}
            finally:
                signal.alarm(0)
            cert["tree"] = name
            cert["seconds"] = round(time.time() - t1, 2)
            with open(os.path.join(a.outdir, f"cert_{name}.json"), "w") as fh:
                json.dump(cert, fh)
            row = sk.summarise(cert)
            row["tree"] = name
            row["seconds"] = cert["seconds"]
            rows.append(row)
            flag = "ok " if row["ok"] else "FAIL"
            print(f"  {flag} {name:22s} n={row['n']:5d} D={row['D']} "
                  f"t={row['free_tokens']} direct={row['direct']} "
                  f"abs={row['absorbers']} "
                  f"mag/(D+1)={(row['magnitude_over_D1'] or 0):.3f} "
                  f"|S|/(D+1)={(row['support_over_D1'] or 0):.3f} "
                  f"({row['seconds']}s)", flush=True)
            if not row["ok"]:
                print(f"       {json.dumps(row.get('failure'))}", flush=True)
        okrows = [r for r in rows if r["ok"]]
        fails = Counter((r.get("failure") or {}).get("step", "?")
                        for r in rows if not r["ok"])
        summary[fam] = {
            "trees": len(rows),
            "ok": len(okrows),
            "failed": len(rows) - len(okrows),
            "failure_steps": dict(fails),
            "max_magnitude_over_D1": max(
                [r["magnitude_over_D1"] or 0 for r in okrows] or [0]),
            "max_support_over_D1": max(
                [r["support_over_D1"] or 0 for r in okrows] or [0]),
            "direct_sinks": sum(r["direct"] or 0 for r in okrows),
            "absorbers": sum(r["absorbers"] or 0 for r in okrows),
            "free_tokens": sum(r["free_tokens"] or 0 for r in okrows),
            "lemma_gaps": sum(r["lemma_gaps"] or 0 for r in okrows),
            "seconds": round(time.time() - t0, 1),
            "rows": rows,
        }
        s = summary[fam]
        print(f"  -> {s['ok']}/{s['trees']} ok, "
              f"max mag/(D+1)={s['max_magnitude_over_D1']:.3f}, "
              f"max |S|/(D+1)={s['max_support_over_D1']:.3f}, "
              f"direct={s['direct_sinks']}, absorbers={s['absorbers']}",
              flush=True)

    path = os.path.join(a.outdir, "summary.json")
    with open(path, "w") as fh:
        json.dump(summary, fh, indent=1)
    print(f"\nwrote {path}")
    total = sum(s["trees"] for s in summary.values())
    ok = sum(s["ok"] for s in summary.values())
    print(f"TOTAL {ok}/{total} ok")
    return 0 if ok == total else 1


if __name__ == "__main__":
    sys.exit(main())
