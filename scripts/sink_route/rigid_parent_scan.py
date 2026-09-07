#!/usr/bin/env python3
"""SCAN 2 (rigid-row parents) over the alphabet_families.json catalogue.

The residue-two rigid row is a child cell whose labels, in terms of its own
input t-parameter, are: head -3t, arm -t, arm -2t, arm t, input 2t. Its head
IS the parent's input x_P (t is identified with x_P via head = -3t = x_P
under the gluing convention used elsewhere in this project -- concretely,
the four NON-head labels of the rigid child, expressed in the parent's own
x_P, are x_P/3, 2*x_P/3, -x_P/3, -2*x_P/3).

For every catalogue family with exactly one input parameter named "x", we
ask: does ANY label of that family (from coefficients_by_label, i.e. not
just the token labels) sit EXACTLY on one of those four values -- i.e. is
some label vector exactly c * (x unit vector) for c in
{1/3, 2/3, -1/3, -2/3}? If so, gluing this family's x to a residue-two rigid
child's input would create an identical-label collision "for free" (the
child's non-head label would coincide with an existing parent label).

We then ask, per CONTEXT (grouping catalogue keys by the prefix before the
final "_<suffix>" menu-item tag) that "could be a parent of an active child"
(i.e. has at least one record with ctx["active"] == "free"): is there at
least one single-x family in that context's full menu (all suffixes, not
just the "free" one) that is FREE of this rigid-collision? If none of its
single-x menu members is free (either because all of them collide, or
because the menu has no single-x family at all), the context is flagged.

The same two questions are repeated for two-input families (parameters
containing both "x1" and "x2"), separately for the x1 axis and the x2 axis.
"""
import os
import json, sys, time
from collections import defaultdict
from math import gcd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.normpath(os.path.join(HERE, "..", "..", "data"))
CATALOGUE = os.path.join(DATA, "alphabet_families.json")
OUT_DIR = os.path.join(DATA, "sink_route")

TARGET_C = [(1, 3), (2, 3), (-1, 3), (-2, 3)]  # (num, den) for c in {1/3,2/3,-1/3,-2/3}


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def reduce_frac(num, den):
    if num == 0:
        return (0, 1)
    g = gcd(abs(num), abs(den))
    num, den = num // g, den // g
    if den < 0:
        num, den = -num, -den
    return (num, den)


def axis_collision(coeffs, params, denom, axis_name):
    """Return list of (label, vec, scalar_str) for labels of this family that
    are EXACTLY c * e_axis for c in {1/3,2/3,-1/3,-2/3} (rigid-row collision
    values)."""
    idx = params.index(axis_name)
    hits = []
    for lbl, vec in coeffs.items():
        ok = True
        for i, x in enumerate(vec):
            if i != idx and x != 0:
                ok = False
                break
        if not ok:
            continue
        num, den = reduce_frac(vec[idx], denom)
        if (num, den) in TARGET_C:
            hits.append((lbl, tuple(vec), f"{num}/{den}"))
    return hits


def context_prefix(ctx_key):
    return ctx_key.rsplit("_", 1)[0]


def main():
    t0 = time.time()
    log("loading catalogue ...")
    with open(CATALOGUE) as f:
        catalog = json.load(f)
    log(f"loaded {len(catalog)} records in {time.time()-t0:.1f}s")

    # per-record classification
    single_x_records = {}   # ctx_key -> dict(has_collision, hits)
    two_input_records = {}  # ctx_key -> dict(has_collision_x1, hits_x1, has_collision_x2, hits_x2)
    ctx_active_free = defaultdict(bool)  # context_prefix -> True if any member has active=='free'
    all_context_members = defaultdict(list)  # context_prefix -> [ctx_key,...] (ALL records, any family)

    n_single_x = 0
    n_two_input = 0

    for ctx_key, rec in catalog.items():
        fam = rec.get("family")
        if not fam:
            continue
        ctx = rec.get("ctx", {})
        cp = context_prefix(ctx_key)
        all_context_members[cp].append(ctx_key)
        if ctx.get("active") == "free":
            ctx_active_free[cp] = True

        params = fam.get("parameters", [])
        coeffs = fam.get("coefficients_by_label", {})
        denom = fam.get("denominator", 1)

        if params.count("x") == 1:
            n_single_x += 1
            hits = axis_collision(coeffs, params, denom, "x")
            single_x_records[ctx_key] = dict(has_collision=len(hits) > 0, hits=hits)

        if "x1" in params and "x2" in params:
            n_two_input += 1
            hits1 = axis_collision(coeffs, params, denom, "x1")
            hits2 = axis_collision(coeffs, params, denom, "x2")
            two_input_records[ctx_key] = dict(
                has_collision_x1=len(hits1) > 0, hits_x1=hits1,
                has_collision_x2=len(hits2) > 0, hits_x2=hits2,
            )

    log(f"single-x families: {n_single_x}; two-input families: {n_two_input}")

    n_collision_single_x = sum(1 for v in single_x_records.values() if v["has_collision"])
    n_collision_x1 = sum(1 for v in two_input_records.values() if v["has_collision_x1"])
    n_collision_x2 = sum(1 for v in two_input_records.values() if v["has_collision_x2"])

    eligible_contexts = sorted([cp for cp, v in ctx_active_free.items() if v])
    log(f"eligible ('could be parent of active child') contexts: {len(eligible_contexts)}")

    def per_context_report(records_dict, collision_flag_key):
        """For each eligible context, look at ALL its menu members that are
        keys of records_dict; determine if >=1 is collision-free."""
        flagged = []          # all collide (>=1 single-x/two-input member, none free)
        no_member = []        # zero eligible single-x/two-input members in menu at all
        safe_count = 0
        for cp in eligible_contexts:
            members = [k for k in all_context_members[cp] if k in records_dict]
            if not members:
                no_member.append(cp)
                continue
            free_members = [k for k in members if not records_dict[k][collision_flag_key]]
            if free_members:
                safe_count += 1
            else:
                flagged.append(dict(context=cp, n_members=len(members), members=members))
        return dict(
            n_eligible_contexts=len(eligible_contexts),
            n_safe=safe_count,
            n_flagged_all_collide=len(flagged),
            flagged_list=flagged[:40],
            n_no_single_input_member=len(no_member),
            no_member_list=no_member[:40],
        )

    report_x = per_context_report(single_x_records, "has_collision")
    report_x1 = per_context_report(two_input_records, "has_collision_x1")
    report_x2 = per_context_report(two_input_records, "has_collision_x2")

    results = dict(
        n_total_records=len(catalog),
        n_single_x_families=n_single_x,
        n_single_x_with_rigid_collision=n_collision_single_x,
        n_two_input_families=n_two_input,
        n_two_input_with_rigid_collision_x1=n_collision_x1,
        n_two_input_with_rigid_collision_x2=n_collision_x2,
        n_eligible_contexts=len(eligible_contexts),
        report_single_x=report_x,
        report_two_input_x1=report_x1,
        report_two_input_x2=report_x2,
        wall_time_s=time.time() - t0,
    )

    out_path = f"{OUT_DIR}/scan2_rigid_results.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=1)
    log(f"wrote {out_path}")
    log(f"TOTAL wall time {time.time()-t0:.1f}s")
    summary = {k: v for k, v in results.items()
               if k not in ("report_single_x", "report_two_input_x1", "report_two_input_x2")}
    print(json.dumps(summary, indent=1))
    for name, rep in (("single_x", report_x), ("x1", report_x1), ("x2", report_x2)):
        print(name, "n_safe=", rep["n_safe"], "n_flagged_all_collide=", rep["n_flagged_all_collide"],
              "n_no_member=", rep["n_no_single_input_member"])


if __name__ == "__main__":
    main()
