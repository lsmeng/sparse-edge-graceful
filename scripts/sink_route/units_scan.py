#!/usr/bin/env python3
"""SCAN 1 (units) over the alphabet_families.json catalogue.

For every catalogue family that has at least one token (fam["token_named"]
truthy), let L be the multiset of vectors of the token labels: the 3 labels
named in token_named.values(), plus (if present) the 3 labels named in
token2_named.values() for two-token families (6 total).

Remove from L every antipodal pair: two elements of the multiset whose raw
coefficient vectors sum to the zero vector (pairs may straddle the two
tokens of a two-token family). What remains is the UNITS set for that
family. We use a bucket/count based maximal-pairing (pair v with -v by
value, using min(count[v],count[-v]); a vector equal to its own negation,
i.e. the literal zero vector, self-pairs in twos) -- this is the unique
well-defined maximum removal since only value-equality (not identity)
matters for "sum to zero".

All comparisons are done on the RAW integer coefficient vectors exactly as
stored in coefficients_by_label. Since every label of one family shares the
same family-wide "denominator", equality/antipodal relations among labels of
the SAME family are exactly the same whether tested on raw vectors or on the
true rational vectors (raw/denominator) -- the common denominator cancels.
"""
import os
import json, sys, time
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.normpath(os.path.join(HERE, "..", "..", "data"))
CATALOGUE = os.path.join(DATA, "alphabet_families.json")
OUT_DIR = os.path.join(DATA, "sink_route")


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def neg(v):
    return tuple(-x for x in v)


def remove_antipodal_pairs(items):
    """items: list of (label_name, vector). Returns (units_items, removed_pairs)
    where units_items is the leftover list of (label_name, vector) not
    consumed by any antipodal pairing, and removed_pairs is a list of
    ((name1,vec1),(name2,vec2)) pairs actually removed (arbitrary but
    consistent choice of which concrete labels realize each value-pairing)."""
    # bucket by vector value -> list of (name, original_index)
    buckets = defaultdict(list)
    for idx, (name, vec) in enumerate(items):
        buckets[vec].append(idx)

    consumed = set()
    removed_pairs = []
    handled_values = set()
    for v in list(buckets.keys()):
        if v in handled_values:
            continue
        nv = neg(v)
        if nv == v:
            # self-antipodal (zero vector): pair up duplicates two at a time
            idxs = [i for i in buckets[v] if i not in consumed]
            k = len(idxs) // 2
            for t in range(k):
                i1, i2 = idxs[2 * t], idxs[2 * t + 1]
                consumed.add(i1); consumed.add(i2)
                removed_pairs.append((items[i1], items[i2]))
            handled_values.add(v)
        elif nv in buckets:
            idxs_v = [i for i in buckets[v] if i not in consumed]
            idxs_nv = [i for i in buckets[nv] if i not in consumed]
            k = min(len(idxs_v), len(idxs_nv))
            for t in range(k):
                i1, i2 = idxs_v[t], idxs_nv[t]
                consumed.add(i1); consumed.add(i2)
                removed_pairs.append((items[i1], items[i2]))
            handled_values.add(v)
            handled_values.add(nv)
        else:
            handled_values.add(v)

    units_items = [it for idx, it in enumerate(items) if idx not in consumed]
    return units_items, removed_pairs


def is_scalar_mult_of_axis(vec, axis_idx, denom):
    """Return the rational scalar c (as a (num,den) reduced-free float-free
    fraction tuple in lowest terms via raw ints (num, denom_local)) such that
    vec == c * e_axis_idx, or None if vec is not supported purely on axis_idx
    (including vec being the all-zero vector, which we treat as 'not a
    nonzero scalar multiple' -> returns (0, 1) explicitly handled by caller
    if needed). Here we just return the raw numerator vec[axis_idx] paired
    with denom, after checking all other entries are zero."""
    for i, x in enumerate(vec):
        if i != axis_idx and x != 0:
            return None
    return (vec[axis_idx], denom)  # true value = num/denom_local... wait denom already the family's denom


def reduce_frac(num, den):
    from math import gcd
    if num == 0:
        return (0, 1)
    g = gcd(abs(num), abs(den))
    num, den = num // g, den // g
    if den < 0:
        num, den = -num, -den
    return (num, den)


def main():
    t0 = time.time()
    log("loading catalogue ...")
    with open(CATALOGUE) as f:
        catalog = json.load(f)
    log(f"loaded {len(catalog)} records in {time.time()-t0:.1f}s")

    token_families = []  # list of dicts with per-family info
    n_total = len(catalog)
    n_token = 0
    n_two_token = 0
    n_missing_label = 0

    for ctx_key, rec in catalog.items():
        fam = rec.get("family")
        if not fam:
            continue
        tn = fam.get("token_named")
        if not tn:
            continue
        n_token += 1
        t2n = fam.get("token2_named")
        coeffs = fam.get("coefficients_by_label", {})
        params = fam.get("parameters", [])
        denom = fam.get("denominator", 1)
        ctx = rec.get("ctx", {})

        items = []
        bad = False
        for role, lbl in tn.items():
            if lbl not in coeffs:
                bad = True
                continue
            items.append((f"tok1:{role}:{lbl}", tuple(coeffs[lbl])))
        is_two_token = bool(t2n)
        if is_two_token:
            n_two_token += 1
            for role, lbl in t2n.items():
                if lbl not in coeffs:
                    bad = True
                    continue
                items.append((f"tok2:{role}:{lbl}", tuple(coeffs[lbl])))
        if bad:
            n_missing_label += 1

        units_items, removed_pairs = remove_antipodal_pairs(items)

        token_families.append(dict(
            ctx_key=ctx_key,
            ctx=ctx,
            params=params,
            denom=denom,
            is_two_token=is_two_token,
            n_labels=len(items),
            units=units_items,
            n_units=len(units_items),
            removed_pairs=removed_pairs,
        ))

    log(f"n_total_records={n_total} n_token_families={n_token} n_two_token={n_two_token} "
        f"n_missing_label={n_missing_label}")

    # ---- histogram of |units| ----
    hist = Counter(tf["n_units"] for tf in token_families)
    expected = {0, 2, 3, 4, 6}
    alarms = {k: v for k, v in hist.items() if k not in expected}

    # ---- two-token families: how often |units| == 6 ----
    two_tok_units6 = sum(1 for tf in token_families if tf["is_two_token"] and tf["n_units"] == 6)
    two_tok_total = sum(1 for tf in token_families if tf["is_two_token"])

    # ---- quad (|units| == 4) analysis ----
    quads = [tf for tf in token_families if tf["n_units"] == 4]
    n_quad_families = len(quads)

    def context_prefix(ctx_key):
        return ctx_key.rsplit("_", 1)[0]

    quad_contexts = set(context_prefix(tf["ctx_key"]) for tf in quads)

    pair_type_counter = Counter()
    pair_type_examples = defaultdict(list)

    for tf in quads:
        params = tf["params"]
        denom = tf["denom"]
        # there should be exactly one removed pair (6 labels -> one pair -> 4 units)
        for (item1, item2) in tf["removed_pairs"]:
            (name1, vec1), (name2, vec2) = item1, item2

            def classify(vec):
                # is this vector exactly +-1 * e_axis for an input axis x/x1/x2?
                for axis_name in ("x", "x1", "x2"):
                    if axis_name in params:
                        idx = params.index(axis_name)
                        r = is_scalar_mult_of_axis(vec, idx, denom)
                        if r is not None:
                            num, den = reduce_frac(r[0], r[1])
                            if abs(num) == 1 and den == 1:
                                return axis_name, (1 if num == 1 else -1)
                return None

            c1 = classify(vec1)
            c2 = classify(vec2)
            if c1 is not None:
                axis, sign = c1
                pair_type_counter[f"{axis}/-{axis}"] += 1
                if len(pair_type_examples[f"{axis}/-{axis}"]) < 5:
                    pair_type_examples[f"{axis}/-{axis}"].append(
                        dict(ctx=tf["ctx_key"], label1=name1, label2=name2))
            elif c2 is not None:
                axis, sign = c2
                pair_type_counter[f"{axis}/-{axis}"] += 1
                if len(pair_type_examples[f"{axis}/-{axis}"]) < 5:
                    pair_type_examples[f"{axis}/-{axis}"].append(
                        dict(ctx=tf["ctx_key"], label1=name1, label2=name2))
            else:
                pair_type_counter["other"] += 1
                if len(pair_type_examples["other"]) < 5:
                    pair_type_examples["other"].append(
                        dict(ctx=tf["ctx_key"], label1=name1, label2=name2))

    # contexts with a quad family in EVERY menu member (every token-bearing
    # family record under that context prefix has |units| == 4)
    by_context = defaultdict(list)
    for tf in token_families:
        by_context[context_prefix(tf["ctx_key"])].append(tf)

    all_quad_menus = []
    for ctxp, members in by_context.items():
        if len(members) >= 1 and all(m["n_units"] == 4 for m in members):
            all_quad_menus.append(dict(context=ctxp, n_members=len(members),
                                        members=[m["ctx_key"] for m in members]))

    # ---- violation checks on UNIT labels ----
    # (a) no unit label has its negative among ALL labels of the family
    viol_neg_in_all = []
    # (b) no unit label is a rational multiple of the head vector (param "y")
    viol_head_mult = []
    # (c) no unit label is a rational multiple of an input vector OTHER than
    #     the input itself (i.e. scalar != +-1)
    viol_input_mult = []

    for ctx_key, rec in catalog.items():
        pass  # placeholder, real loop below uses token_families + catalog lookups

    for tf in token_families:
        rec = catalog[tf["ctx_key"]]
        fam = rec["family"]
        coeffs = fam.get("coefficients_by_label", {})
        params = tf["params"]
        denom = tf["denom"]
        y_idx = params.index("y") if "y" in params else None
        input_axes = [(name, params.index(name)) for name in ("x", "x1", "x2") if name in params]

        all_label_vecs = set(tuple(v) for v in coeffs.values())

        for (name, vec) in tf["units"]:
            # (a)
            if neg(vec) in all_label_vecs:
                viol_neg_in_all.append(dict(ctx=tf["ctx_key"], label=name, vec=list(vec)))
            # (b)
            if y_idx is not None:
                r = is_scalar_mult_of_axis(vec, y_idx, denom)
                if r is not None and r[0] != 0:
                    viol_head_mult.append(dict(ctx=tf["ctx_key"], label=name, vec=list(vec)))
            # (c)
            for axis_name, idx in input_axes:
                r = is_scalar_mult_of_axis(vec, idx, denom)
                if r is not None and r[0] != 0:
                    num, den = reduce_frac(r[0], r[1])
                    if not (abs(num) == 1 and den == 1):
                        viol_input_mult.append(dict(ctx=tf["ctx_key"], label=name, vec=list(vec),
                                                     axis=axis_name, scalar=f"{num}/{den}"))

    results = dict(
        n_total_records=n_total,
        n_token_families=n_token,
        n_two_token_families=two_tok_total,
        n_missing_label=n_missing_label,
        histogram_units=dict(sorted(hist.items(), key=lambda kv: str(kv[0]))),
        alarms_unexpected_unit_counts=alarms,
        two_token_units6_count=two_tok_units6,
        two_token_total=two_tok_total,
        quad=dict(
            n_quad_families=n_quad_families,
            n_quad_contexts=len(quad_contexts),
            quad_contexts_list=sorted(quad_contexts),
            removed_pair_type_counts=dict(pair_type_counter),
            removed_pair_type_examples={k: v for k, v in pair_type_examples.items()},
        ),
        all_quad_menus=dict(
            count=len(all_quad_menus),
            list=all_quad_menus,
        ),
        violations=dict(
            neg_in_all_labels=dict(count=len(viol_neg_in_all), examples=viol_neg_in_all[:10]),
            head_mult=dict(count=len(viol_head_mult), examples=viol_head_mult[:10]),
            input_mult_other_than_unit=dict(count=len(viol_input_mult), examples=viol_input_mult[:10]),
        ),
        wall_time_s=time.time() - t0,
    )

    out_path = f"{OUT_DIR}/scan1_units_results.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=1)
    log(f"wrote {out_path}")
    log(f"TOTAL wall time {time.time()-t0:.1f}s")
    print(json.dumps({k: v for k, v in results.items()}, indent=1)[:4000])


if __name__ == "__main__":
    main()
