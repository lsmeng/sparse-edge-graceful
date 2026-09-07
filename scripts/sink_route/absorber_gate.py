#!/usr/bin/env python3
"""Absorber collision gate over the alphabet_families.json catalogue.

For every ordered pair (P, C) of catalogue families where:
  - P is a possible PARENT: ctx["active"] == "free" and family["parameters"]
    contains "x" exactly once, and family has a token_named.
  - C is a possible CHILD: "y" in family["parameters"], and family has a
    token_named.

we identify C's parameter "y" with P's parameter "x" (all other parameters of
P and C kept distinct, even if they share a raw name like "u1" -- they are
different unknowns), giving a joint parameter space of dimension
D = pP + pC - 1.

P's free token is the 3 labels in P.token_named.values(); these sum to zero.
Likewise for C. An "order" picks an ordered pair (a,b) from P's 3 token
labels (6 ways) and an ordered pair (c,d) from C's 3 token labels (6 ways):
36 orders total. The absorber forms
    F1 = a + b + d
    F2 = -F1
    F3 = 2a + b - c
    F4 = -F3
as linear forms over the joint parameter space. A COLLISION is: some Fi
equal to some label of P or of C (or its negative), or Fi == Fj (i != j),
or Fi == 0. An order is collision-free if none of these hold.

All forms are compared as exact rational vectors: we scale by
Lc = lcm(L_P, L_C) and compare integer numerator vectors for exact equality.
"""
import json, itertools, os, sys, time
from math import gcd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.normpath(os.path.join(HERE, "..", "..", "data"))
CATALOGUE = os.path.join(DATA, "alphabet_families.json")
OUT_DIR = os.path.join(DATA, "sink_route")

ROLE_PAIRS = list(itertools.permutations(range(3), 2))  # 6 ordered (i,j), i != j


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def lcm(a, b):
    return a * b // gcd(a, b)


def build_pool_entry(ctx_key, fam):
    params = fam["parameters"]
    coeffs = fam["coefficients_by_label"]
    tn = fam.get("token_named")
    if not tn:
        return None
    tok_labels = [tn["a"], tn["b"], tn["c"]]
    for lbl in tok_labels:
        if lbl not in coeffs:
            return None
    # sanity: token sums to zero (not required for filtering, just a check)
    L = fam["denominator"]
    tok_vecs = [coeffs[lbl] for lbl in tok_labels]
    sumzero = all(sum(tok_vecs[0][i] + tok_vecs[1][i] + tok_vecs[2][i] for i in range(1)) == 0 for _ in [0]) \
        if False else all((tok_vecs[0][j] + tok_vecs[1][j] + tok_vecs[2][j]) == 0 for j in range(len(params)))
    return dict(
        ctx=ctx_key,
        params=params,
        denom=L,
        coeffs=coeffs,           # label -> raw int vector (over `params`)
        tok_labels=tok_labels,   # 3 label names
        sumzero=sumzero,
    )


def load_catalogue():
    t0 = time.time()
    log("loading catalogue json ...")
    with open(CATALOGUE) as f:
        catalog = json.load(f)
    log(f"loaded {len(catalog)} records in {time.time()-t0:.1f}s")
    return catalog


def build_pools(catalog):
    parent_pool = []
    child_pool = []
    n_parent_raw = n_child_raw = 0
    n_parent_bad = n_child_bad = 0
    for ctx_key, rec in catalog.items():
        fam = rec.get("family")
        ctx = rec.get("ctx", {})
        if not fam:
            continue
        params = fam.get("parameters", [])
        is_parent = (ctx.get("active") == "free") and params.count("x") == 1
        is_child = "y" in params
        if is_parent and fam.get("token_named"):
            n_parent_raw += 1
            ent = build_pool_entry(ctx_key, fam)
            if ent is None:
                n_parent_bad += 1
            else:
                ent["x_idx"] = params.index("x")
                parent_pool.append(ent)
        if is_child and fam.get("token_named"):
            n_child_raw += 1
            ent = build_pool_entry(ctx_key, fam)
            if ent is None:
                n_child_bad += 1
            else:
                ent["y_idx"] = params.index("y")
                child_pool.append(ent)
    log(f"parent pool: raw={n_parent_raw} usable={len(parent_pool)} bad={n_parent_bad}")
    log(f"child pool: raw={n_child_raw} usable={len(child_pool)} bad={n_child_bad}")
    n_tok_sumzero_bad_p = sum(1 for e in parent_pool if not e["sumzero"])
    n_tok_sumzero_bad_c = sum(1 for e in child_pool if not e["sumzero"])
    log(f"parent token sum-zero violations: {n_tok_sumzero_bad_p}; child: {n_tok_sumzero_bad_c}")
    return parent_pool, child_pool


def precompute_scaled_cores(entry, partner_denoms):
    """For every possible partner denominator d, precompute:
       fscale[d]      = Lc // own_denom
       label_core[d]  = {label: tuple(fscale[d]*c for c in raw_vec)}
       tok_core[d]    = [tuple(fscale[d]*c for c in raw_vec) for raw_vec in tok_vecs]
    keyed by d (the partner's denominator), reused across every partner sharing
    that denominator value.
    """
    L = entry["denom"]
    out = {}
    for d in partner_denoms:
        Lc = lcm(L, d)
        f = Lc // L
        label_core = {lbl: tuple(f * c for c in vec) for lbl, vec in entry["coeffs"].items()}
        tok_core = [label_core[lbl] for lbl in entry["tok_labels"]]
        out[d] = dict(f=f, label_core=label_core, tok_core=tok_core)
    entry["cache"] = out


def place_child_core(core_vec, pC, y_idx, pP, x_idx):
    """Embed a length-pC 'core' vector (already fC-scaled) into the joint
    D = pP + pC - 1 length space: column y_idx of the child maps onto column
    x_idx of the parent (the first pP columns); every other child column k
    maps onto column pP + (k if k < y_idx else k - 1)."""
    D = pP + pC - 1
    out = [0] * D
    for k in range(pC):
        v = core_vec[k]
        if v == 0:
            continue
        if k == y_idx:
            out[x_idx] += v
        else:
            col = pP + (k if k < y_idx else k - 1)
            out[col] += v
    return tuple(out)


def place_parent_core(core_vec, pC):
    """Embed a length-pP 'core' vector into the joint D=pP+pC-1 space: parent
    columns are always the first pP slots, zero elsewhere."""
    return core_vec + (0,) * (pC - 1)


def analyze_pair(P, C):
    """Returns (free_count, D, per-order diagnostics function).
    Diagnostics are NOT computed here (kept fast); call describe_order() for
    detail on any specific (i,j,k,l) after the fact."""
    pP, pC = len(P["params"]), len(C["params"])
    x_idx, y_idx = P["x_idx"], C["y_idx"]
    D = pP + pC - 1

    Pc = P["cache"][C["denom"]]
    Cc = C["cache"][P["denom"]]

    # forbidden set: every label of P and of C, plus its negative, plus 0
    forbidden = set()
    for core in Pc["label_core"].values():
        v = place_parent_core(core, pC)
        forbidden.add(v)
        forbidden.add(tuple(-x for x in v))
    for core in Cc["label_core"].values():
        v = place_child_core(core, pC, y_idx, pP, x_idx)
        forbidden.add(v)
        forbidden.add(tuple(-x for x in v))
    zero = (0,) * D
    forbidden.add(zero)

    # token vectors (3 each), embedded in joint space
    Pt = [place_parent_core(c, pC) for c in Pc["tok_core"]]
    Ct = [place_child_core(c, pC, y_idx, pP, x_idx) for c in Cc["tok_core"]]

    free_count = 0
    failing_orders = []
    for (i, j) in ROLE_PAIRS:
        a, b = Pt[i], Pt[j]
        for (k, l) in ROLE_PAIRS:
            c, d = Ct[k], Ct[l]
            F1 = tuple(a[m] + b[m] + d[m] for m in range(D))
            F3 = tuple(2 * a[m] + b[m] - c[m] for m in range(D))
            neg_F3 = tuple(-x for x in F3)
            collide = (F1 in forbidden) or (F3 in forbidden) or (F1 == F3) or (F1 == neg_F3)
            if collide:
                failing_orders.append((i, j, k, l))
            else:
                free_count += 1
    return free_count, D, failing_orders, forbidden, Pt, Ct


def describe_order(P, C, order, D, forbidden, Pt, Ct):
    """Produce a human-readable identity string for one failing order."""
    i, j, k, l = order
    pP, pC = len(P["params"]), len(C["params"])
    x_idx, y_idx = P["x_idx"], C["y_idx"]
    a, b = Pt[i], Pt[j]
    c, d = Ct[k], Ct[l]
    a_lbl, b_lbl = P["tok_labels"][i], P["tok_labels"][j]
    c_lbl, d_lbl = C["tok_labels"][k], C["tok_labels"][l]
    F1 = tuple(a[m] + b[m] + d[m] for m in range(D))
    F3 = tuple(2 * a[m] + b[m] - c[m] for m in range(D))
    neg_F3 = tuple(-x for x in F3)
    zero = (0,) * D

    Pc = P["cache"][C["denom"]]
    Cc = C["cache"][P["denom"]]

    def find_label_match(vec):
        if vec == zero:
            return "0"
        for lbl, core in Pc["label_core"].items():
            v = place_parent_core(core, pC)
            if v == vec:
                return f"label[{lbl}] of parent {P['ctx']}"
            if tuple(-x for x in v) == vec:
                return f"-label[{lbl}] of parent {P['ctx']}"
        for lbl, core in Cc["label_core"].items():
            v = place_child_core(core, pC, y_idx, pP, x_idx)
            if v == vec:
                return f"label[{lbl}] of child {C['ctx']}"
            if tuple(-x for x in v) == vec:
                return f"-label[{lbl}] of child {C['ctx']}"
        return None

    prefix = f"a={a_lbl}(P) b={b_lbl}(P) c={c_lbl}(C) d={d_lbl}(C)"
    if F1 in forbidden:
        m = find_label_match(F1)
        return f"{prefix} :: F1=a+b+d = {m}"
    if F3 in forbidden:
        m = find_label_match(F3)
        return f"{prefix} :: F3=2a+b-c = {m}"
    if F1 == F3:
        return f"{prefix} :: F1=F3 (a+b+d = 2a+b-c, i.e. a = c+d)"
    if F1 == neg_F3:
        return f"{prefix} :: F1=-F3 (a+b+d = -(2a+b-c), i.e. 3a+2b-c+d = 0)"
    return f"{prefix} :: (no collision found -- bug)"


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    t0 = time.time()
    limit = None
    if len(sys.argv) > 1 and sys.argv[1] == "--limit":
        limit = int(sys.argv[2])

    catalog = load_catalogue()
    parent_pool, child_pool = build_pools(catalog)

    if limit:
        parent_pool = parent_pool[:limit]
        child_pool = child_pool[:limit]
        log(f"LIMIT MODE: parent_pool={len(parent_pool)} child_pool={len(child_pool)}")

    parent_denoms = sorted(set(e["denom"] for e in parent_pool))
    child_denoms = sorted(set(e["denom"] for e in child_pool))
    log(f"parent denoms: {parent_denoms}; child denoms: {child_denoms}")

    t1 = time.time()
    for e in parent_pool:
        precompute_scaled_cores(e, child_denoms)
    for e in child_pool:
        precompute_scaled_cores(e, parent_denoms)
    log(f"precomputed scaled cores in {time.time()-t1:.1f}s")

    n_pairs = 0
    histogram = {}
    zero_pairs = []  # (P_ctx, C_ctx)
    t2 = time.time()
    log_every = max(1, (len(parent_pool) * len(child_pool)) // 40)

    sanity_result = None

    for pi, P in enumerate(parent_pool):
        for C in child_pool:
            free_count, D, failing_orders, forbidden, Pt, Ct = analyze_pair(P, C)
            n_pairs += 1
            histogram[free_count] = histogram.get(free_count, 0) + 1
            if free_count == 0:
                zero_pairs.append((P["ctx"], C["ctx"]))
            if P["ctx"] == "h0_3_p0_act" and C["ctx"] == "h0_3_p0_act":
                sanity_result = dict(free_count=free_count, D=D,
                                      failing_orders=[describe_order(P, C, o, D, forbidden, Pt, Ct) for o in failing_orders])
            if n_pairs % log_every == 0:
                elapsed = time.time() - t2
                rate = n_pairs / elapsed if elapsed > 0 else 0
                log(f"progress: {n_pairs} pairs ({100.0*n_pairs/(len(parent_pool)*len(child_pool)):.1f}%) "
                    f"elapsed={elapsed:.1f}s rate={rate:.0f} pairs/s")

    log(f"main loop done: {n_pairs} pairs in {time.time()-t2:.1f}s")

    # second pass: diagnostics for up to 60 zero-free pairs
    zero_pairs_examples = []
    parent_by_ctx = {e["ctx"]: e for e in parent_pool}
    child_by_ctx = {e["ctx"]: e for e in child_pool}
    for (pctx, cctx) in zero_pairs[:60]:
        P = parent_by_ctx[pctx]
        C = child_by_ctx[cctx]
        free_count, D, failing_orders, forbidden, Pt, Ct = analyze_pair(P, C)
        desc = describe_order(P, C, failing_orders[0], D, forbidden, Pt, Ct) if failing_orders else None
        zero_pairs_examples.append(dict(parent=pctx, child=cctx, example_identity=desc))

    if sanity_result is None:
        log("WARNING: sanity pair h0_3_p0_act/h0_3_p0_act not found in pools under this limit")

    results = dict(
        n_records=len(catalog),
        n_parent_pool=len(parent_pool),
        n_child_pool=len(child_pool),
        n_pairs_examined=n_pairs,
        histogram_free_orders={str(k): v for k, v in sorted(histogram.items())},
        n_zero_free_pairs=len(zero_pairs),
        zero_free_pairs_examples=zero_pairs_examples,
        sanity_check_h0_3_p0_act_self=sanity_result,
        wall_time_s=time.time() - t0,
    )
    out_path = os.path.join(OUT_DIR, "results.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=1)
    log(f"wrote {out_path}")
    log(f"TOTAL wall time {time.time()-t0:.1f}s")

    print(json.dumps({k: v for k, v in results.items() if k not in ("zero_free_pairs_examples",)}, indent=1))
    print("sanity:", sanity_result)
    print("first few zero-free examples:", zero_pairs_examples[:5])


if __name__ == "__main__":
    main()
