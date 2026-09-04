#!/usr/bin/env python3
"""Assemble the free-token alphabet catalogue from CP-SAT batch JSONL files.

Input: one or more JSONL files produced by ``run_alphabet_batch.py`` (rank-3
pass, rank-2 pass, root pass, ...).  Each line is an object with keys ``key``,
``ctx``, ``found``, ``attempts``, ``family``; the ``family`` payload is the
JSON written by ``symbolic_free_token_cpsat.py`` (keys ``parameters``,
``denominator``, ``labels``, ``coefficients_by_label``, ``mirror_pairs``,
``token_indices``, ``permutation_named``, ``row_specs``, and for root macros
``root_row``, ``zero_label_index``, ``root_owner_output_index``,
``root_zero_output``).

Output: ``data/alphabet_families.json``, a map

    context key -> {ctx, kind, <derived data of the chosen family>,
                    family, menu, provenance}

``menu`` holds EVERY found family for that context, ordered by the preference
below; ``menu[0]`` is the chosen one and ``family`` repeats its payload for
compatibility.  The preference is, in order,

    1. larger token rank -- 3 beats 2 beats "no token"; the rank ``"any2"``
       (a token with no dedicated ``t`` parameters, only the requirement that
       the triple spans two dimensions) counts as 2 but is recorded verbatim,
    2. more effective internal freedom -- the number of labels whose
       coefficient vector is nonzero on some parameter other than the head
       ``y`` and the input ``x`` (i.e. on an internal ``u_i`` or on a token
       parameter ``t1``/``t2``),
    3. fewer forced labels,
    4. smaller denominator ``L``,
    5. input file order, then line order (stable).

Derived data (all label values are ``coefficient vector / L``; the bookkeeping
zero label of a root macro is never counted as a physical label):

    forced_forms      labels whose vector is nonzero ONLY on the input
                      parameter ``x``; the label equals ``q*x``.  The pinned
                      input label itself (kind ``input``, ``q == 1``) is
                      listed too and is tagged by its kind so the lookahead
                      gate can drop it as the shared edge.
    head_only_forms   labels other than the exposed head whose vector is
                      nonzero ONLY on ``y``; the label equals ``q*y``.
    free_labels       labels depending on at least one non-input, non-head
                      parameter (``t1``, ``t2``, ``u_1``, ...).
    clean             no head-only non-head labels at all.
    forced_only_antipode
                      every ``x``-only label is ``+x`` or ``-x``.
    token_jacobian    exact rank of the three token coefficient vectors over
                      all parameters, and over all parameters except ``x``.
                      Since ``c = -a-b`` the rank is at most 2; a rank below 2
                      means the token triple spans no plane, so pairing it
                      against a pending token (solving ``T_B = -T_A`` as sets)
                      has no positive-dimensional solution set on this side.

Ratios are exact ``fractions.Fraction`` values, serialised as strings.

Usage:
    assemble_alphabet_catalogue.py BATCH.jsonl [BATCH2.jsonl ...] [--out FILE]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from fractions import Fraction as Q

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.normpath(os.path.join(HERE, "..", "data"))

# parameters that are neither the exposed head nor the input head
RESERVED_PARAMS = ("y", "x")
# labels that are bookkeeping only, never physically placed
NON_PHYSICAL_KINDS = ("zero",)

BULKY = ("outputs", "verification", "coefficients", "rows_rendered")


class Malformed(Exception):
    """A record or family payload is missing a required field, or it is unusable."""


# ------------------------------------------------------------------ helpers

def nonzero_only(vec, i):
    """True iff ``vec`` is nonzero at coordinate ``i`` and zero elsewhere."""
    if i is None or i >= len(vec) or vec[i] == 0:
        return False
    return all(c == 0 for j, c in enumerate(vec) if j != i)


def exact_rank(rows):
    """Exact rank of a list of integer vectors (fraction-free enough for us)."""
    m = [[Q(int(c)) for c in r] for r in rows]
    if not m or not m[0]:
        return 0
    ncols = len(m[0])
    piv_row = 0
    for col in range(ncols):
        piv = next((r for r in range(piv_row, len(m)) if m[r][col] != 0), None)
        if piv is None:
            continue
        m[piv_row], m[piv] = m[piv], m[piv_row]
        pv = m[piv_row][col]
        for r in range(piv_row + 1, len(m)):
            if m[r][col] != 0:
                f = m[r][col] / pv
                m[r] = [a - f * b for a, b in zip(m[r], m[piv_row])]
        piv_row += 1
        if piv_row == len(m):
            break
    return piv_row


def ordered_labels(labels):
    """Labels sorted by their declared index (robust to a missing index)."""
    out = []
    for pos, lb in enumerate(labels):
        if not isinstance(lb, dict) or not lb.get("name"):
            raise Malformed("labels[] entry without a name")
        idx = lb.get("index")
        out.append((idx if isinstance(idx, int) else pos, pos, lb))
    out.sort()
    return [lb for _, _, lb in out]


def matrix_rank_local(rows):
    """Exact rank over the rationals, used for the (E4) plane test."""
    m = [[Q(x) for x in r] for r in rows]
    rk = 0
    for c in range(len(m[0]) if m else 0):
        piv = next((r for r in range(rk, len(m)) if m[r][c]), None)
        if piv is None:
            continue
        m[rk], m[piv] = m[piv], m[rk]
        pv = m[rk][c]
        for r in range(len(m)):
            if r != rk and m[r][c]:
                f = m[r][c] / pv
                m[r] = [a - f * b for a, b in zip(m[r], m[rk])]
        rk += 1
    return rk


def rank_value(raw, token):
    """Numeric preference weight of a family's token rank."""
    if not token:
        return 0
    if raw == "any2":
        return 2
    return raw if isinstance(raw, int) else 0


def token_jacobian(fam, labs, vec, params):
    """Rank of the token triple over all parameters and over all but ``x``.

    Returns ``None`` when the family carries no token or the token indices are
    unusable.
    """
    if not fam.get("token"):
        return None
    tok = fam.get("token_indices")
    names = None
    by_index = {lb.get("index"): lb["name"] for lb in labs}
    if isinstance(tok, dict) and set(tok) >= {"a", "b", "c"}:
        names = [by_index.get(tok.get(r)) for r in "abc"]
    if names is None or any(n is None for n in names):
        named = fam.get("token_named")
        if isinstance(named, dict) and set(named) >= {"a", "b", "c"}:
            names = [named.get(r) for r in "abc"]
    if names is None or any(n not in vec for n in names):
        return None
    rows = [vec[n] for n in names]
    ix = params.index("x") if "x" in params else None
    rows_no_x = ([[c for i, c in enumerate(r) if i != ix] for r in rows]
                 if ix is not None else rows)
    ra, rb = exact_rank(rows), exact_rank(rows_no_x)
    return {"token_labels": names, "rank_all": ra, "rank_without_x": rb,
            "degenerate": ra < 2}


def analyse_family(fam):
    """Derive the catalogue data of one family payload.

    Raises ``Malformed`` when a required field is absent or unusable.
    """
    if not isinstance(fam, dict):
        raise Malformed("family is not an object")
    params = fam.get("parameters")
    cbl = fam.get("coefficients_by_label")
    labels = fam.get("labels")
    if not isinstance(params, list) or not params:
        raise Malformed("parameters")
    if not isinstance(cbl, dict) or not cbl:
        raise Malformed("coefficients_by_label")
    if not isinstance(labels, list) or not labels:
        raise Malformed("labels")
    try:
        L = int(fam.get("denominator"))
    except (TypeError, ValueError):
        raise Malformed("denominator")
    if L < 1:
        raise Malformed("denominator < 1")

    d = len(params)
    labs = ordered_labels(labels)
    vec = {}
    for lb in labs:
        name = lb["name"]
        raw = cbl.get(name)
        if not isinstance(raw, list) or len(raw) != d:
            raise Malformed(f"coefficient vector for label {name!r}")
        try:
            vec[name] = [int(c) for c in raw]
        except (TypeError, ValueError):
            raise Malformed(f"non-integer coefficient for label {name!r}")

    iy = params.index("y") if "y" in params else None
    ix = params.index("x") if "x" in params else None
    free_ids = [i for i, p in enumerate(params) if p not in RESERVED_PARAMS]

    # a root macro carries a bookkeeping zero label (P' = P + {0}); it is not a
    # physical label and takes no part in the forced/head-only analysis.
    zero_names = [lb["name"] for lb in labs if lb.get("kind") in NON_PHYSICAL_KINDS]
    phys = [lb for lb in labs if lb.get("kind") not in NON_PHYSICAL_KINDS]
    is_root = bool(fam.get("root_row"))
    if not is_root:
        specs = fam.get("row_specs")
        if isinstance(specs, list) and specs and isinstance(specs[0], dict):
            is_root = bool(specs[0].get("root"))

    # the exposed head is the first physical label of a non-root macro
    head = phys[0] if (phys and not is_root and phys[0].get("kind") == "head") else None
    head_name = head["name"] if head else None
    head_ratio = None
    if head is not None and iy is not None and nonzero_only(vec[head_name], iy):
        head_ratio = Q(vec[head_name][iy], L)

    forced, head_only, free_labels = [], [], []
    for lb in phys:
        name = lb["name"]
        v = vec[name]
        kind = lb.get("kind")
        if nonzero_only(v, ix):
            forced.append({"name": name, "kind": kind,
                           "ratio": str(Q(v[ix], L))})
        if name != head_name and nonzero_only(v, iy):
            head_only.append({"name": name, "kind": kind,
                              "ratio": str(Q(v[iy], L))})
        if any(v[i] != 0 for i in free_ids):
            free_labels.append(name)

    # forced-antipode flag: some non-head label is identically minus the
    # exposed head (its parent could then absorb the head only by a token
    # containing the shared edge); such families are ranked last
    forced_antipode = False
    if head is not None:
        hv = vec[head_name]
        forced_antipode = any(vec[lb["name"]] == [-c for c in hv]
                              for lb in phys if lb["name"] != head_name)

    token = bool(fam.get("token"))
    raw_rank = fam.get("token_rank") if token else 0
    if raw_rank is None:
        raw_rank = 0
    width = fam.get("width")
    width = width if isinstance(width, int) else len(labs)
    forced_ratios = sorted({Q(f["ratio"]) for f in forced})

    return {
        "width": width,
        "n_physical_labels": len(phys),
        "denominator": L,
        "parameters": list(params),
        "is_root": is_root,
        "zero_labels": zero_names,
        "zero_label_index": fam.get("zero_label_index"),
        "root_owner_output_index": fam.get("root_owner_output_index"),
        "root_zero_output": fam.get("root_zero_output"),
        "token": token,
        "token_rank": raw_rank,
        "token_rank_value": rank_value(raw_rank, token),
        "token_indices": fam.get("token_indices"),
        "token_named": fam.get("token_named"),
        "token_jacobian": token_jacobian(fam, labs, vec, params),
        "two_tokens": bool(fam.get("two_tokens")),
        "token2_indices": fam.get("token2_indices"),
        "token2_named": fam.get("token2_named"),
        "input_in_token": bool(fam.get("input_in_token")),
        "forced_antipode": forced_antipode,
        "mirror_pairs": fam.get("mirror_pairs"),
        "n_mirror_pairs": len(fam.get("mirror_pairs") or []),
        "row_specs": fam.get("row_specs"),
        "forms": fam.get("forms"),
        "head_label": head_name,
        "head_ratio": str(head_ratio) if head_ratio is not None else None,
        "has_head": head_name is not None,
        "has_input": ix is not None and any(
            lb.get("kind") == "input" for lb in phys),
        "input_label": next((lb["name"] for lb in phys
                             if lb.get("kind") == "input"), None),
        "forced_forms": forced,
        "forced_ratios": [str(q) for q in forced_ratios],
        "n_forced": len(forced),
        "n_forced_non_input": sum(1 for f in forced if f["kind"] != "input"),
        "head_only_forms": head_only,
        "head_only_ratios": sorted({f["ratio"] for f in head_only},
                                   key=lambda s: Q(s)),
        "n_head_only": len(head_only),
        "free_labels": free_labels,
        "effective_freedom": len(free_labels),
        # flags computed from the coefficient vectors, not from the CP-SAT
        # request flags of the same name inside ``family``
        "clean": not head_only,
        "forced_only_antipode": all(q in (Q(1), Q(-1)) for q in forced_ratios),
    }


def rank_key(entry):
    """Sort key: best family first."""
    # clean families (no head-only labels, forced labels limited to the input
    # antipode) are universally compatible with the lookahead gate, so they
    # come first; among them the usual rank/freedom preference applies.
    return (bool(entry.get("forced_antipode")),
            not (entry.get("clean") and entry.get("forced_only_antipode", True)),
            -entry["token_rank_value"], -entry["effective_freedom"],
            entry["n_forced"], entry["denominator"],
            entry["_file_order"], entry["_line_order"])


# --------------------------------------------------------------------- main

def load(paths, stats):
    """Yield (file_order, line_order, record) for every parsable JSONL line."""
    for fo, path in enumerate(paths):
        if not os.path.exists(path):
            print(f"warning: {path} does not exist; skipped", file=sys.stderr)
            stats["missing_files"] += 1
            continue
        with open(path) as fh:
            for lo, line in enumerate(fh):
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    stats["unparsable_lines"] += 1
                    continue
                if not isinstance(rec, dict) or not rec.get("key"):
                    stats["records_without_key"] += 1
                    continue
                yield fo, lo, rec


def rank_label(entry):
    """Display form of a family's token rank."""
    r = entry["token_rank"]
    return "none" if (r == 0 or r is None) else str(r)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("batches", nargs="+", help="JSONL batch files, best pass first")
    ap.add_argument("--out", default=os.path.join(DATA, "alphabet_families.json"))
    ap.add_argument("--slim", action="store_true",
                    help="drop bulky family sub-objects from the output")
    ap.add_argument("--menu-limit", type=int, default=0,
                    help="keep at most N families per context (0 = all)")
    ap.add_argument("--indent", type=int, default=1)
    a = ap.parse_args(argv)

    stats = Counter()
    seen_ctx, seen_kind = {}, {}
    candidates = defaultdict(list)
    keys_seen = []

    for fo, lo, rec in load(a.batches, stats):
        key = rec["key"]
        if key not in seen_ctx:
            keys_seen.append(key)
            seen_ctx[key] = rec.get("ctx") if isinstance(rec.get("ctx"), dict) else {}
            seen_kind[key] = (seen_ctx[key] or {}).get("kind") or "?"
        stats["records"] += 1
        if not rec.get("found"):
            stats["records_not_found"] += 1
            continue
        fam = rec.get("family")
        try:
            derived = analyse_family(fam)
        except Malformed as exc:
            stats["records_malformed"] += 1
            stats[f"malformed:{exc}"] += 1
            print(f"warning: {key}: malformed family ({exc}); skipped",
                  file=sys.stderr)
            continue
        # (E4) as stated in the manuscript: the three coefficient vectors of a
        # token must span a plane.  A triple whose own vectors are parallel is
        # rejected here rather than carried into the catalogue; the recorded
        # token_rank folds in the exposed head row and cannot see this.
        bad_plane = None
        for tag in ("token_indices", "token2_indices"):
            ti = fam.get(tag)
            if not isinstance(ti, dict):
                continue
            try:
                rows = [derived["vec"][ti[r]] for r in ("a", "b", "c")] \
                    if "vec" in derived else \
                    [fam["coefficients_by_label"][fam["labels"][ti[r]]["name"]]
                     for r in ("a", "b", "c")]
            except Exception:
                continue
            if matrix_rank_local(rows) != 2:
                bad_plane = tag
                break
        if bad_plane is not None:
            stats["records_token_not_a_plane"] += 1
            print(f"warning: {key}: {bad_plane} triple does not span a plane "
                  f"((E4)); skipped", file=sys.stderr)
            continue
        derived["_file_order"] = fo
        derived["_line_order"] = lo
        derived["_source"] = os.path.basename(a.batches[fo])
        derived["_family"] = fam
        derived["_attempts"] = rec.get("attempts")
        candidates[key].append(derived)
        stats["records_usable"] += 1

    catalogue = {}
    for key in sorted(candidates):
        cands = sorted(candidates[key], key=rank_key)
        if a.menu_limit > 0:
            stats["menu_entries_dropped"] += max(0, len(cands) - a.menu_limit)
            cands = cands[:a.menu_limit]
        menu = []
        for c in cands:
            fam = c["_family"]
            if a.slim and isinstance(fam, dict):
                fam = {k: v for k, v in fam.items() if k not in BULKY}
            item = {k: v for k, v in c.items() if not k.startswith("_")}
            item["provenance"] = {"source": c["_source"], "line": c["_line_order"],
                                  "attempts": c["_attempts"]}
            item["family"] = fam
            menu.append(item)
        best = menu[0]
        entry = {k: v for k, v in best.items()
                 if k not in ("family", "provenance")}
        entry["key"] = key
        entry["ctx"] = seen_ctx.get(key, {})
        entry["kind"] = seen_kind.get(key, "?")
        entry["provenance"] = dict(best["provenance"], n_candidates=len(cands))
        entry["n_menu"] = len(menu)
        entry["family"] = best["family"]
        entry["menu"] = menu
        catalogue[key] = entry

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w") as fh:
        json.dump(catalogue, fh, indent=a.indent, sort_keys=True)

    # ------------------------------------------------------------- summary
    found_by_kind, missing_by_kind = Counter(), Counter()
    missing_keys = []
    for key in keys_seen:
        kind = seen_kind.get(key, "?")
        if key in catalogue:
            found_by_kind[kind] += 1
        else:
            missing_by_kind[kind] += 1
            missing_keys.append(key)

    kinds = sorted(set(found_by_kind) | set(missing_by_kind))
    wk = max([len(k) for k in kinds] + [len("kind")])
    print(f"wrote {a.out} ({os.path.getsize(a.out) / 1e6:.1f} MB)")
    print(f"contexts seen: {len(keys_seen)}   with a family: {len(catalogue)}"
          f"   without: {len(missing_keys)}")
    print()
    print(f"{'kind'.ljust(wk)}  {'found':>5}  {'missing':>7}  {'total':>5}")
    print(f"{'-' * wk}  {'-' * 5}  {'-' * 7}  {'-' * 5}")
    for k in kinds:
        f, m = found_by_kind[k], missing_by_kind[k]
        print(f"{k.ljust(wk)}  {f:>5}  {m:>7}  {f + m:>5}")
    print(f"{'-' * wk}  {'-' * 5}  {'-' * 7}  {'-' * 5}")
    print(f"{'TOTAL'.ljust(wk)}  {sum(found_by_kind.values()):>5}"
          f"  {sum(missing_by_kind.values()):>7}  {len(keys_seen):>5}")
    print()
    print(f"missing keys ({len(missing_keys)}):")
    for k in missing_keys:
        print(f"  {k}  [{seen_kind.get(k, '?')}]")
    if not missing_keys:
        print("  (none)")

    menu_sizes = Counter(e["n_menu"] for e in catalogue.values())
    total_menu = sum(e["n_menu"] for e in catalogue.values())
    print()
    print("record statistics:")
    for k in sorted(stats):
        print(f"  {k}: {stats[k]}")
    print(f"menu: {total_menu} families over {len(catalogue)} contexts; "
          f"sizes {dict(sorted(menu_sizes.items()))}")

    def rank_hist(items):
        c = Counter(rank_label(e) for e in items)
        return dict(sorted(c.items(), key=lambda kv: (kv[0] == "none", kv[0])))

    print(f"chosen token ranks: {rank_hist(catalogue.values())}")
    print("menu token ranks:   "
          f"{rank_hist(m for e in catalogue.values() for m in e['menu'])}")
    print(f"chosen clean (no head-only labels): "
          f"{sum(1 for e in catalogue.values() if e['clean'])}/{len(catalogue)}"
          f"   forced_only_antipode: "
          f"{sum(1 for e in catalogue.values() if e['forced_only_antipode'])}"
          f"/{len(catalogue)}")
    nroot = sum(1 for e in catalogue.values() if e["is_root"])
    nzero = sum(1 for e in catalogue.values() if e["zero_labels"])
    print(f"root macros: {nroot}   of which carrying a zero label: {nzero}"
          f"   root_zero_output set: "
          f"{sum(1 for e in catalogue.values() if e['root_zero_output'])}")

    # --------------------------------------------- token Jacobian (pairwise)
    tok_all = [(k, m) for k, e in catalogue.items() for m in e["menu"]
               if m["token"]]
    with_jac = [(k, m) for k, m in tok_all if m["token_jacobian"]]
    degen = [(k, m) for k, m in with_jac if m["token_jacobian"]["degenerate"]]
    ra = Counter(m["token_jacobian"]["rank_all"] for _, m in with_jac)
    rb = Counter(m["token_jacobian"]["rank_without_x"] for _, m in with_jac)
    print()
    print(f"token Jacobian over the menu: {len(tok_all)} token families, "
          f"{len(tok_all) - len(with_jac)} without usable token indices")
    print(f"  rank over all parameters:      {dict(sorted(ra.items()))}")
    print(f"  rank over parameters minus x:  {dict(sorted(rb.items()))}")
    print(f"  families with rank < 2 over all parameters: {len(degen)}")
    shown = 0
    for k, m in degen:
        print(f"    {k}  rank={m['token_jacobian']['rank_all']} "
              f"(no x: {m['token_jacobian']['rank_without_x']})  "
              f"token {','.join(m['token_jacobian']['token_labels'])}  "
              f"[{m['provenance']['source']}]")
        shown += 1
        if shown >= 40 and len(degen) > 40:
            print(f"    ... {len(degen) - shown} more")
            break
    if not degen:
        print("    (none)")
    degen_ctx = sorted({k for k, _ in degen})
    if degen_ctx:
        print(f"  contexts touched: {len(degen_ctx)}")
        all_degen = [k for k in degen_ctx
                     if all(m["token_jacobian"] and m["token_jacobian"]["degenerate"]
                            for m in catalogue[k]["menu"] if m["token"])]
        print(f"  contexts where EVERY token family is degenerate: "
              f"{len(all_degen)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
