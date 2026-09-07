#!/usr/bin/env python3
"""Three extensions of the absorber collision gate (see absorber_gate.py for
the base mechanics, which this module imports and reuses unchanged).

Extension 1 -- two-input parents:
    Families whose parameters contain both "x1" and "x2" (detected purely by
    parameter names, regardless of ctx["active"]) serve as parents. The child
    is identified either at x1 or at x2 (the other input remains an ordinary
    free parameter of the parent). Both token_named and token2_named (when
    present) of the two-input family are used as the parent's token. The
    child side is the original child pool (token_named only, "y" in params).

Extension 2 -- second tokens everywhere:
    Over the original one-input parent pool and original child pool, add the
    three combinations besides (token_named, token_named) [already computed
    in results.json]: (token2, token1), (token1, token2), (token2, token2),
    wherever the relevant token2_named exists.

Extension 3 -- same-cell pairs:
    For every family carrying both token_named and token2_named, treat the
    two tokens of that single family as the two sources over its own
    (unreduced) parameter space -- no parent/child identification. a,b range
    over token1's 3 labels (6 ordered choices), c,d over token2's 3 labels
    (6 ordered choices): 36 orders, judged against the family's own labels,
    negatives, the other absorber form, and zero.
"""
import json, os, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import absorber_gate as ag

CATALOGUE = ag.CATALOGUE
OUT_DIR = ag.OUT_DIR
ROLE_PAIRS = ag.ROLE_PAIRS
log = ag.log


def build_pool_entry_tok(ctx_key, fam, tok_field):
    params = fam["parameters"]
    coeffs = fam["coefficients_by_label"]
    tn = fam.get(tok_field)
    if not tn:
        return None
    tok_labels = [tn["a"], tn["b"], tn["c"]]
    for lbl in tok_labels:
        if lbl not in coeffs:
            return None
    L = fam["denominator"]
    tok_vecs = [coeffs[lbl] for lbl in tok_labels]
    sumzero = all((tok_vecs[0][j] + tok_vecs[1][j] + tok_vecs[2][j]) == 0 for j in range(len(params)))
    return dict(
        ctx=ctx_key,
        params=params,
        denom=L,
        coeffs=coeffs,
        tok_labels=tok_labels,
        sumzero=sumzero,
    )


def compute_caches(parent_pool, child_pool):
    parent_denoms = sorted(set(e["denom"] for e in parent_pool))
    child_denoms = sorted(set(e["denom"] for e in child_pool))
    for e in parent_pool:
        ag.precompute_scaled_cores(e, child_denoms)
    for e in child_pool:
        ag.precompute_scaled_cores(e, parent_denoms)


def run_cartesian(parent_pool, child_pool, tag):
    """Run analyze_pair over the full parent_pool x child_pool product,
    return (n_pairs, histogram, zero_free_examples[<=60], wall_time)."""
    t0 = time.time()
    compute_caches(parent_pool, child_pool)
    n_pairs = 0
    histogram = {}
    zero_pairs = []
    log_every = max(1, (len(parent_pool) * len(child_pool)) // 20) if parent_pool and child_pool else 1
    for P in parent_pool:
        for C in child_pool:
            free_count, D, failing_orders, forbidden, Pt, Ct = ag.analyze_pair(P, C)
            n_pairs += 1
            histogram[free_count] = histogram.get(free_count, 0) + 1
            if free_count == 0:
                zero_pairs.append((P, C, D, failing_orders, forbidden, Pt, Ct))
            if n_pairs % log_every == 0:
                elapsed = time.time() - t0
                rate = n_pairs / elapsed if elapsed > 0 else 0
                log(f"[{tag}] progress: {n_pairs}/{len(parent_pool)*len(child_pool)} "
                    f"elapsed={elapsed:.1f}s rate={rate:.0f}/s")
    zero_examples = []
    for (P, C, D, failing_orders, forbidden, Pt, Ct) in zero_pairs[:60]:
        desc = ag.describe_order(P, C, failing_orders[0], D, forbidden, Pt, Ct) if failing_orders else None
        zero_examples.append(dict(parent=P["ctx"], child=C["ctx"], example_identity=desc))
    wall = time.time() - t0
    log(f"[{tag}] done: {n_pairs} pairs in {wall:.1f}s, {len(zero_pairs)} zero-free")
    return dict(
        n_pairs_examined=n_pairs,
        histogram_free_orders={str(k): v for k, v in sorted(histogram.items())},
        n_zero_free_pairs=len(zero_pairs),
        zero_free_pairs_examples=zero_examples,
        wall_time_s=wall,
    )


# ---------------------------------------------------------------------------
# Extension 1: two-input parents
# ---------------------------------------------------------------------------

def build_ext1_parent_pool(catalog):
    pool = []
    n_records = 0
    for ctxk, rec in catalog.items():
        fam = rec.get("family")
        if not fam:
            continue
        params = fam.get("parameters", [])
        if params.count("x1") != 1 or params.count("x2") != 1:
            continue
        n_records += 1
        for attach in ("x1", "x2"):
            for tok_field, tok_tag in (("token_named", "tok1"), ("token2_named", "tok2")):
                if not fam.get(tok_field):
                    continue
                ent = build_pool_entry_tok(ctxk, fam, tok_field)
                if ent is None:
                    continue
                ent["x_idx"] = params.index(attach)
                ent["ctx"] = f"{ctxk}@attach={attach}#{tok_tag}"
                pool.append(ent)
    log(f"ext1: {n_records} two-input records -> {len(pool)} parent entries")
    return pool


def run_extension1(catalog, orig_child_pool):
    parent_pool = build_ext1_parent_pool(catalog)
    return run_cartesian(parent_pool, orig_child_pool, "ext1")


# ---------------------------------------------------------------------------
# Extension 2: second tokens everywhere (one-input parents/children)
# ---------------------------------------------------------------------------

def build_ext2_tok2_pools(catalog):
    parent_tok2 = []
    child_tok2 = []
    for ctxk, rec in catalog.items():
        fam = rec.get("family")
        ctx = rec.get("ctx", {})
        if not fam:
            continue
        params = fam.get("parameters", [])
        is_parent = (ctx.get("active") == "free") and params.count("x") == 1
        is_child = "y" in params
        if is_parent and fam.get("token2_named"):
            ent = build_pool_entry_tok(ctxk, fam, "token2_named")
            if ent is not None:
                ent["x_idx"] = params.index("x")
                ent["ctx"] = f"{ctxk}#tok2"
                parent_tok2.append(ent)
        if is_child and fam.get("token2_named"):
            ent = build_pool_entry_tok(ctxk, fam, "token2_named")
            if ent is not None:
                ent["y_idx"] = params.index("y")
                ent["ctx"] = f"{ctxk}#tok2"
                child_tok2.append(ent)
    log(f"ext2: parent_tok2={len(parent_tok2)} child_tok2={len(child_tok2)}")
    return parent_tok2, child_tok2


# ---------------------------------------------------------------------------
# Extension 3: same-cell pairs (single family, two tokens, no identification)
# ---------------------------------------------------------------------------

def analyze_self_pair(fam):
    coeffs = fam["coefficients_by_label"]
    params = fam["parameters"]
    tn1 = fam["token_named"]
    tn2 = fam["token2_named"]
    D = len(params)
    tok1_labels = [tn1["a"], tn1["b"], tn1["c"]]
    tok2_labels = [tn2["a"], tn2["b"], tn2["c"]]
    for lbl in tok1_labels + tok2_labels:
        if lbl not in coeffs:
            return None
    tok1_vecs = [tuple(coeffs[l]) for l in tok1_labels]
    tok2_vecs = [tuple(coeffs[l]) for l in tok2_labels]

    forbidden = set()
    for v in coeffs.values():
        t = tuple(v)
        forbidden.add(t)
        forbidden.add(tuple(-x for x in t))
    zero = (0,) * D
    forbidden.add(zero)

    free_count = 0
    failing = []
    for (i, j) in ROLE_PAIRS:
        a, b = tok1_vecs[i], tok1_vecs[j]
        for (k, l) in ROLE_PAIRS:
            c, d = tok2_vecs[k], tok2_vecs[l]
            F1 = tuple(a[m] + b[m] + d[m] for m in range(D))
            F3 = tuple(2 * a[m] + b[m] - c[m] for m in range(D))
            negF3 = tuple(-x for x in F3)
            collide = (F1 in forbidden) or (F3 in forbidden) or (F1 == F3) or (F1 == negF3)
            if collide:
                failing.append((i, j, k, l))
            else:
                free_count += 1
    return dict(free_count=free_count, D=D, failing=failing, forbidden=forbidden,
                tok1_vecs=tok1_vecs, tok2_vecs=tok2_vecs,
                tok1_labels=tok1_labels, tok2_labels=tok2_labels)


def describe_self_order(fam, order, res):
    i, j, k, l = order
    tok1_vecs, tok2_vecs = res["tok1_vecs"], res["tok2_vecs"]
    tok1_labels, tok2_labels = res["tok1_labels"], res["tok2_labels"]
    D, forbidden = res["D"], res["forbidden"]
    a, b = tok1_vecs[i], tok1_vecs[j]
    c, d = tok2_vecs[k], tok2_vecs[l]
    a_lbl, b_lbl = tok1_labels[i], tok1_labels[j]
    c_lbl, d_lbl = tok2_labels[k], tok2_labels[l]
    F1 = tuple(a[m] + b[m] + d[m] for m in range(D))
    F3 = tuple(2 * a[m] + b[m] - c[m] for m in range(D))
    negF3 = tuple(-x for x in F3)
    zero = (0,) * D
    coeffs = fam["coefficients_by_label"]

    def find_label(vec):
        if vec == zero:
            return "0"
        for lbl, raw in coeffs.items():
            t = tuple(raw)
            if t == vec:
                return f"label[{lbl}]"
            if tuple(-x for x in t) == vec:
                return f"-label[{lbl}]"
        return None

    prefix = f"a={a_lbl}(tok1) b={b_lbl}(tok1) c={c_lbl}(tok2) d={d_lbl}(tok2)"
    if F1 in forbidden:
        return f"{prefix} :: F1=a+b+d = {find_label(F1)}"
    if F3 in forbidden:
        return f"{prefix} :: F3=2a+b-c = {find_label(F3)}"
    if F1 == F3:
        return f"{prefix} :: F1=F3 (a+b+d = 2a+b-c, i.e. a = c+d)"
    if F1 == negF3:
        return f"{prefix} :: F1=-F3 (a+b+d = -(2a+b-c), i.e. 3a+2b-c+d = 0)"
    return f"{prefix} :: (no collision found -- bug)"


def run_extension3(catalog):
    t0 = time.time()
    n_families = 0
    n_bad = 0
    histogram = {}
    zero_examples = []
    for ctxk, rec in catalog.items():
        fam = rec.get("family")
        if not fam:
            continue
        if not (fam.get("token_named") and fam.get("token2_named")):
            continue
        n_families += 1
        res = analyze_self_pair(fam)
        if res is None:
            n_bad += 1
            continue
        histogram[res["free_count"]] = histogram.get(res["free_count"], 0) + 1
        if res["free_count"] == 0 and len(zero_examples) < 60:
            desc = describe_self_order(fam, res["failing"][0], res) if res["failing"] else None
            zero_examples.append(dict(family=ctxk, example_identity=desc))
    n_zero = sum(1 for k, v in histogram.items() if k == 0)
    zero_count = histogram.get(0, 0)
    wall = time.time() - t0
    log(f"ext3: {n_families} families with both tokens ({n_bad} invalid/skipped), "
        f"{zero_count} zero-free, in {wall:.1f}s")
    return dict(
        n_pairs_examined=n_families - n_bad,
        n_invalid_skipped=n_bad,
        histogram_free_orders={str(k): v for k, v in sorted(histogram.items())},
        n_zero_free_pairs=zero_count,
        zero_free_pairs_examples=zero_examples,
        wall_time_s=wall,
    )


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    t0 = time.time()
    catalog = ag.load_catalogue()
    orig_parent_pool, orig_child_pool = ag.build_pools(catalog)

    log("=== running extension 1: two-input parents ===")
    ext1 = run_extension1(catalog, orig_child_pool)

    log("=== running extension 2: second tokens everywhere ===")
    parent_tok1 = [dict(e, ctx=f"{e['ctx']}#tok1") for e in orig_parent_pool]
    child_tok1 = [dict(e, ctx=f"{e['ctx']}#tok1") for e in orig_child_pool]
    parent_tok2, child_tok2 = build_ext2_tok2_pools(catalog)

    combos = [
        ("tok2xtok1", parent_tok2, child_tok1),
        ("tok1xtok2", parent_tok1, child_tok2),
        ("tok2xtok2", parent_tok2, child_tok2),
    ]
    n_pairs2 = 0
    histogram2 = {}
    zero_examples2 = []
    wall2 = 0.0
    n_zero2 = 0
    for name, ppool, cpool in combos:
        res = run_cartesian(ppool, cpool, f"ext2:{name}")
        n_pairs2 += res["n_pairs_examined"]
        n_zero2 += res["n_zero_free_pairs"]
        for k, v in res["histogram_free_orders"].items():
            histogram2[int(k)] = histogram2.get(int(k), 0) + v
        for ex in res["zero_free_pairs_examples"]:
            ex["combo"] = name
        zero_examples2.extend(res["zero_free_pairs_examples"])
        wall2 += res["wall_time_s"]
    ext2 = dict(
        n_pairs_examined=n_pairs2,
        histogram_free_orders={str(k): v for k, v in sorted(histogram2.items())},
        n_zero_free_pairs=n_zero2,
        zero_free_pairs_examples=zero_examples2[:60],
        wall_time_s=wall2,
    )

    log("=== running extension 3: same-cell pairs ===")
    ext3 = run_extension3(catalog)

    results = dict(
        n_records=len(catalog),
        extension1_two_input_parents=ext1,
        extension2_second_tokens=ext2,
        extension3_same_cell=ext3,
        total_wall_time_s=time.time() - t0,
    )
    out_path = os.path.join(OUT_DIR, "results_ext.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=1)
    log(f"wrote {out_path}")
    log(f"TOTAL wall time {time.time()-t0:.1f}s")

    print("ext1: n_pairs=%d n_zero_free=%d" % (ext1["n_pairs_examined"], ext1["n_zero_free_pairs"]))
    print("ext2: n_pairs=%d n_zero_free=%d" % (ext2["n_pairs_examined"], ext2["n_zero_free_pairs"]))
    print("ext3: n_pairs=%d n_zero_free=%d" % (ext3["n_pairs_examined"], ext3["n_zero_free_pairs"]))


if __name__ == "__main__":
    main()
