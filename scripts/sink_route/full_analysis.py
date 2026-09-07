#!/usr/bin/env python3
"""Full-catalogue integer-lattice / image-index computation.

For every family in alphabet_families.json, build the integrality lattice
Lambda_F = {p in Z^k : C p in L Z^m} exactly (via an integer kernel of the
augmented matrix [C | -L I_m]), get a Z-basis B of it, then for every token
(token_named / token2_named) compute the "image index" (gcd of 2x2 minors of
T = [aB/L; bB/L]) and compare against the naive raw-coordinate carrier
determinant (min |2x2 minor| of [a;b] over all pairs of the k original
parameter columns).
"""
import json, os, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lattice import lattice_basis_and_index, token_image_index, naive_min_abs_minor

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.normpath(os.path.join(HERE, "..", "..", "data"))
CATALOGUE = os.path.join(DATA, "alphabet_families.json")
OUT_DIR = os.path.join(DATA, "sink_route")
FOCUS_KEYS = ["h0_3_p0_act", "h0_5_p0_act", "h1_2_p0_act", "h4_1-3-3-3_p0_act"]


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def famkey(fam):
    params = tuple(fam["parameters"])
    L = fam["denominator"]
    coeffs = tuple(sorted((lab, tuple(vec)) for lab, vec in fam["coefficients_by_label"].items()))
    return (params, L, coeffs)


def main():
    t0 = time.time()
    with open(CATALOGUE) as f:
        catalog = json.load(f)
    log(f"loaded {len(catalog)} records in {time.time()-t0:.1f}s")

    fam_cache = {}          # famkey -> dict(B=..., det=..., lattice_index=..., k=..., m=...)
    unique_tokens = {}       # (famkey, tag, sorted token items) -> dict(...)
    context_tokens = {}      # ctx -> list of dicts (tag, image_index, lattice_index, naive)
    n_no_token = 0
    n_bad_labels = 0

    for ctx, rec in catalog.items():
        fam = rec["family"]
        params = fam["parameters"]
        k = len(params)
        L = fam["denominator"]
        coeffs = fam["coefficients_by_label"]
        fk = famkey(fam)
        if fk not in fam_cache:
            labels_sorted = sorted(coeffs.keys())
            C = [coeffs[lab] for lab in labels_sorted]
            B, det = lattice_basis_and_index(C, L, k)
            fam_cache[fk] = dict(B=B, det=det, lattice_index=abs(det), k=k, m=len(C), L=L)
        finfo = fam_cache[fk]
        B, lattice_index, L, k = finfo["B"], finfo["lattice_index"], finfo["L"], finfo["k"]

        toks_here = []
        had_any = False
        for tag in ("token_named", "token2_named"):
            tn = fam.get(tag)
            if not tn:
                continue
            had_any = True
            labs = (tn["a"], tn["b"], tn.get("c"))
            if any(lab is not None and lab not in coeffs for lab in labs) or tn["a"] not in coeffs or tn["b"] not in coeffs:
                n_bad_labels += 1
                continue
            a = coeffs[tn["a"]]
            b = coeffs[tn["b"]]
            image_index, TA, TB = token_image_index(a, b, B, L, k)
            naive = naive_min_abs_minor(a, b, k)
            entry = dict(tag=tag, image_index=image_index, lattice_index=lattice_index, naive=naive, k=k, L=L)
            toks_here.append(entry)

            tokkey = (fk, tag, tuple(sorted(tn.items())))
            if tokkey not in unique_tokens:
                unique_tokens[tokkey] = dict(image_index=image_index, lattice_index=lattice_index,
                                              naive=naive, example_ctx=ctx, tag=tag, k=k, L=L)
        if not had_any:
            n_no_token += 1
        context_tokens[ctx] = toks_here

    log(f"unique families (by content): {len(fam_cache)}")
    log(f"unique (family,token) pairs: {len(unique_tokens)}  contexts w/o any token: {n_no_token}  bad-label tokens skipped: {n_bad_labels}")

    # ---------- item 1: histogram of image indices over unique tokens ----------
    hist_image = {}
    for v in unique_tokens.values():
        hist_image[v["image_index"]] = hist_image.get(v["image_index"], 0) + 1
    n_unique_tokens = len(unique_tokens)
    frac_index1 = hist_image.get(1, 0) / n_unique_tokens if n_unique_tokens else 0.0

    # ---------- item 2: per-context minimum image index ----------
    ctx_min_index = {}
    for ctx, toks in context_tokens.items():
        if not toks:
            continue
        ctx_min_index[ctx] = min(t["image_index"] for t in toks)
    hist_ctx = {}
    for v in ctx_min_index.values():
        hist_ctx[v] = hist_ctx.get(v, 0) + 1
    contexts_gt1 = sorted(
        [(ctx, idx) for ctx, idx in ctx_min_index.items() if idx > 1],
        key=lambda t: (-t[1], t[0]),
    )

    # ---------- item 3: naive-vs-image comparison (over unique tokens) ----------
    naive_hist = {}
    for v in unique_tokens.values():
        nv = v["naive"]
        naive_hist[nv] = naive_hist.get(nv, 0) + 1
    naive_gt1_image_eq1 = sum(1 for v in unique_tokens.values() if (v["naive"] or 0) > 1 and v["image_index"] == 1)
    naive_le1_image_gt1 = sum(1 for v in unique_tokens.values() if (v["naive"] is not None and v["naive"] <= 1) and v["image_index"] > 1)
    naive_eq1_image_gt1 = sum(1 for v in unique_tokens.values() if v["naive"] == 1 and v["image_index"] > 1)
    naive_eq0_count = sum(1 for v in unique_tokens.values() if v["naive"] == 0)
    naive_none_count = sum(1 for v in unique_tokens.values() if v["naive"] is None)

    # ---------- item 4: the four focus contexts ----------
    focus = {}
    for k4 in FOCUS_KEYS:
        toks = context_tokens.get(k4, [])
        focus[k4] = dict(tokens=toks)

    results = dict(
        n_records=len(catalog),
        n_unique_families=len(fam_cache),
        n_context_tokens_total=sum(len(v) for v in context_tokens.values()),
        n_unique_family_token_pairs=n_unique_tokens,
        n_contexts_without_token=n_no_token,
        n_bad_label_tokens_skipped=n_bad_labels,
        histogram_image_index_over_unique_tokens=dict(sorted(hist_image.items())),
        fraction_image_index_1=frac_index1,
        histogram_context_min_image_index=dict(sorted(hist_ctx.items())),
        n_contexts_with_min_index_gt1=len(contexts_gt1),
        contexts_with_min_index_gt1=contexts_gt1,
        naive_histogram_over_unique_tokens_top=dict(sorted(naive_hist.items())[:20]),
        naive_eq0_count=naive_eq0_count,
        naive_none_count=naive_none_count,
        naive_gt1_and_image_eq1_count=naive_gt1_image_eq1,
        naive_le1_and_image_gt1_count=naive_le1_image_gt1,
        naive_eq1_and_image_gt1_count=naive_eq1_image_gt1,
        focus_contexts=focus,
    )

    out_path = os.path.join(OUT_DIR, "results.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=1, default=str)
    log(f"wrote {out_path}")
    log(f"total wall time {time.time()-t0:.1f}s")

    # ---- console summary ----
    print("=== HISTOGRAM: image index over unique (family,token) pairs ===")
    for idx, cnt in sorted(hist_image.items()):
        print(f"  index={idx}: {cnt}")
    print(f"  total unique tokens = {n_unique_tokens}, fraction index=1: {frac_index1:.4f}")
    print()
    print("=== HISTOGRAM: per-context MIN image index (5717 contexts) ===")
    for idx, cnt in sorted(hist_ctx.items()):
        print(f"  index={idx}: {cnt} contexts")
    print(f"  contexts w/o any token: {n_no_token}")
    print(f"  contexts with min index > 1: {len(contexts_gt1)}")
    print()
    print("=== Top 20 contexts with image index > 1 (largest first) ===")
    for ctx, idx in contexts_gt1[:20]:
        print(f"  {ctx}: {idx}")
    print()
    print("=== NAIVE vs IMAGE comparison (unique tokens) ===")
    print(f"  naive==0: {naive_eq0_count}  naive undefined (k<2): {naive_none_count}")
    print(f"  naive histogram (first 20 values): {dict(sorted(naive_hist.items())[:20])}")
    print(f"  naive>1 AND image==1 : {naive_gt1_image_eq1}")
    print(f"  naive<=1 AND image>1 : {naive_le1_image_gt1}  (of which naive==1 exactly: {naive_eq1_image_gt1})")
    print()
    print("=== FOCUS CONTEXTS ===")
    for k4 in FOCUS_KEYS:
        print(f"  {k4}: {focus[k4]['tokens']}")


if __name__ == "__main__":
    main()
