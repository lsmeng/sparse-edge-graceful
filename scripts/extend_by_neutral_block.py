#!/usr/bin/env python3
"""Build families for wide contexts by adjoining neutral blocks to narrow ones.

A neutral block (data/neutral_blocks.json, built and re-verified by
build_neutral_blocks.py) is a set of arms and ports whose labels, written in
one fresh parameter t, satisfy: the block's contribution to the owner's output
is zero, the block's labels equal its outputs as a multiset, the labels are
closed under negation, and they are nonzero and pairwise distinct.

Adjoining a block to a family for a context C therefore gives a family for the
context with those arms and ports added.  P = O is preserved because the block
matches its own outputs and leaves the owner's untouched; the signature
partition is extended by the block's mirror pairs; the new labels are distinct
from the host's and from each other because t is a fresh parameter on which
every host label vanishes and no two block labels agree; and the head, the
input and the token are not touched, so the head-free, input-exact and
token-rank conditions carry over verbatim.

Several blocks may be adjoined at once, each with its own fresh parameter.
Nothing here is trusted: the emitted families are written in the batch JSONL
format and re-verified by check_alphabet_families.py like any other.

usage: extend_by_neutral_block.py [--targets FILE] [--out FILE]
"""
import argparse
import json
import os
import sys
from collections import Counter
from fractions import Fraction as Q

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from run_alphabet_batch import key  # noqa: E402
from neutral_closure import load_blocks, route  # noqa: E402

DATA = os.path.normpath(os.path.join(HERE, "..", "data"))


def form(vec, params, L):
    ts = []
    for v, p in zip(vec, params):
        if not v:
            continue
        q = Q(v, L)
        ts.append(f"{q}*{p}" if q != 1 else p)
    return " + ".join(ts) if ts else "0"


def block_labels(block, L, slot, npar):
    """Port vectors and per-arm vectors of one block, over denominator L.

    A block's own labels are coefficient tuples in its own parameters, which
    are placed in the fresh slots starting at ``slot``.
    """
    def vec(c):
        v = [0] * npar
        for j, x in enumerate(c):
            v[slot + j] = x * L
        return v
    lab = [c if isinstance(c, list) else [c] for c in block["labels"]]
    ports = [vec(lab[i]) for i in range(block["ports"])]
    arms, i = [], block["ports"]
    for ell in block["arms"]:
        arms.append((ell, [vec(c) for c in lab[i:i + ell + 1]]))
        i += ell + 1
    return ports, arms


def block_width(block):
    lab = block["labels"]
    return len(lab[0]) if isinstance(lab[0], list) else 1


def adjoin(fam, blocks, ctx):
    """Family for ctx built from fam by adjoining the given neutral blocks."""
    cbl = fam["coefficients_by_label"]
    L = int(fam["denominator"])
    base_params = list(fam["parameters"])
    rs = [dict(r) for r in (fam.get("row_specs") or [])]
    if not rs:
        return None
    bar = list(rs[0].get("arms") or [])
    bports = int(rs[0].get("ports") or 0)
    nfresh = sum(block_width(b) for b in blocks)
    npar = len(base_params) + nfresh
    params = base_params + [f"t{i + 1}" for i in range(nfresh)]

    def grow(v):
        return list(v) + [0] * (npar - len(v))

    # the arms and ports the block contributes, each in its own fresh parameter
    new_ports, new_arms, slot = [], [], len(base_params)
    tok_block = None            # (index into new_ports+new_arms flattening)
    for b in blocks:
        p, a = block_labels(b, L, slot, npar)
        if b.get("token"):
            if tok_block is not None:
                return None     # at most one token block per family
            flat = [v for v in p] + [v for _, row in a for v in row]
            tok_block = [tuple(flat[t]) for t in b["token"]]
        slot += block_width(b)
        new_ports.extend(p)
        new_arms.extend(a)
    if tok_block is not None and (fam.get("token2_indices") or fam.get("two_tokens")):
        return None             # the host already carries a second token

    # arms of the result, matched to the order the target context asks for
    src = [(bar[i], [grow(cbl[f"r0a{i}x{p}"]) for p in range(bar[i] + 1)])
           for i in range(len(bar))] + new_arms
    want = list(ctx["arms"])
    if sorted(want) != sorted(ell for ell, _ in src):
        return None
    order, used = [], [False] * len(src)
    for ell in want:
        for i, (e, _) in enumerate(src):
            if not used[i] and e == ell:
                used[i] = True
                order.append(i)
                break
        else:
            return None

    # reordering the arms renames the base family's own arm labels; the
    # mirror pairs and the token are recorded by name, so carry the map
    ren = {}
    for j, si in enumerate(order):
        if si < len(bar):
            for p in range(bar[si] + 1):
                ren[f"r0a{si}x{p}"] = f"r0a{j}x{p}"

    new, labs = {}, []
    keep = {l["name"]: l for l in fam["labels"]}
    for nm, l in keep.items():
        if l["kind"] in ("arm", "port") and l.get("row", 0) == 0:
            continue
        new[nm] = grow(cbl[nm])
        labs.append(dict(l))
    for j, si in enumerate(order):
        ell, vecs = src[si]
        for p in range(ell + 1):
            nm = f"r0a{j}x{p}"
            new[nm] = vecs[p]
            labs.append({"name": nm, "kind": "arm", "row": 0, "arm": j, "pos": p,
                         "role": f"row 0 arm {j} position {p}"})
    ports = [grow(cbl[f"r0p{i}"]) for i in range(bports)] + new_ports
    if len(ports) != ctx["ports"]:
        return None
    for j, v in enumerate(ports):
        nm = f"r0p{j}"
        new[nm] = v
        labs.append({"name": nm, "kind": "port", "row": 0, "arm": None, "pos": j,
                     "role": f"row 0 port {j}"})

    # nonzero and pairwise distinct (the block labels carry a fresh parameter,
    # so this can only fail if a block is malformed; checked anyway)
    zname = None
    zi = fam.get("zero_label_index")
    if zi is not None and 0 <= zi < len(fam["labels"]):
        zname = ren.get(fam["labels"][zi]["name"], fam["labels"][zi]["name"])
    seen = set()
    for nm, v in new.items():
        t = tuple(v)
        if nm != zname and all(x == 0 for x in t):
            return None
        if t in seen and nm != zname:
            return None
        seen.add(t)

    order_kind = {"head": 0, "head_chain": 1, "arm": 2, "port": 3, "input": 4,
                  "active": 5, "zero": 6}
    def sk(l):
        return (l.get("row") or 0, order_kind.get(l["kind"], 9),
                l["arm"] if l.get("arm") is not None else -1,
                l["pos"] if l.get("pos") is not None else -1, l["name"])
    labs.sort(key=sk)
    for i, l in enumerate(labs):
        l["index"] = i
    names = [l["name"] for l in labs]
    idx = {n: i for i, n in enumerate(names)}

    pairs_named = [[ren.get(p[0], p[0]), ren.get(p[1], p[1])]
                   for p in (fam.get("mirror_pairs_named") or [])]
    pairs_named = [p for p in pairs_named if p[0] in idx and p[1] in idx]
    # the block's own mirror pairs: match each new label to its negative
    fresh = [n for n in names if n.startswith("r0a") or n.startswith("r0p")]
    fresh = [n for n in fresh if any(new[n][len(base_params):])]
    tok2 = None
    if tok_block is not None:
        by_vec = {tuple(new[n]): n for n in fresh}
        if any(v not in by_vec for v in tok_block):
            return None
        tok2 = {r: by_vec[v] for r, v in zip("abc", tok_block)}
        fresh = [n for n in fresh if n not in set(tok2.values())]
    taken = set()
    for n in fresh:
        if n in taken:
            continue
        neg = tuple(-x for x in new[n])
        for m in fresh:
            if m != n and m not in taken and tuple(new[m]) == neg:
                pairs_named.append([n, m])
                taken.add(n)
                taken.add(m)
                break
        else:
            return None
    pairs = [[idx[x], idx[y]] for x, y in pairs_named]

    tok = fam.get("token_named") or None
    if not tok and isinstance(fam.get("token_indices"), dict):
        tok = {r: fam["labels"][i]["name"] for r, i in fam["token_indices"].items()}
    if isinstance(tok, dict):
        tok = {r: ren.get(v, v) for r, v in tok.items()}
    tok_idx = ({r: idx[v] for r, v in tok.items()}
               if isinstance(tok, dict) and all(v in idx for v in tok.values()) else None)
    # a host with no token of its own adopts the block's triple as its token,
    # rather than carrying a second token and no first
    if tok_idx is None and tok2 is not None:
        tok, tok2 = tok2, None
        tok_idx = {r: idx[v] for r, v in tok.items()}
    if tok2 is None:
        tok2 = fam.get("token2_named") or None
        if isinstance(tok2, dict):
            tok2 = {r: ren.get(v, v) for r, v in tok2.items()}
    tok2_idx = ({r: idx[v] for r, v in tok2.items()}
                if isinstance(tok2, dict) and all(v in idx for v in tok2.values()) else None)
    rs[0]["arms"] = list(want)
    rs[0]["ports"] = ctx["ports"]
    return {
        "status": "EXTENDED", "denominator": L, "parameters": params,
        "labels": labs, "coefficients": [new[n] for n in names],
        "coefficients_by_label": {n: new[n] for n in names},
        "forms": [form(new[n], params, L) for n in names],
        "mirror_pairs": pairs, "mirror_pairs_named": pairs_named,
        "token_indices": tok_idx, "token_named": tok if tok_idx else None,
        "token2_indices": tok2_idx, "token2_named": tok2 if tok2_idx else None,
        "token": bool(tok_idx), "two_tokens": bool(tok2_idx),
        "token_rank": (token_rank(new, names, labs, tok) if tok_idx else
                       fam.get("token_rank")), "width": len(names),
        "row_specs": rs, "root_row": bool(fam.get("root_row")),
        "zero_label_index": idx.get(zname) if zname else None,
        "root_owner_output_index": fam.get("root_owner_output_index"),
        "root_zero_output": fam.get("root_zero_output"),
        "head_mult": fam.get("head_mult"), "head_mult_free": fam.get("head_mult_free"),
        "input_in_token": fam.get("input_in_token"),
        "provenance": {"neutral_block": [b["arms"] + ["p"] * b["ports"] for b in blocks],
                       "from": key(fam.get("ctx", {})) if fam.get("ctx") else None},
    }


def token_rank(new, names, labs, tok):
    """Exact rank of [head; a; b; c], which is what the checker recomputes."""
    rows = [new[l["name"]] for l in labs if l["kind"] == "head"]
    rows += [new[tok[r]] for r in ("a", "b", "c")]
    mat = [[Q(x) for x in r] for r in rows]
    rank = 0
    for col in range(len(mat[0]) if mat else 0):
        piv = next((r for r in range(rank, len(mat)) if mat[r][col]), None)
        if piv is None:
            continue
        mat[rank], mat[piv] = mat[piv], mat[rank]
        pv = mat[rank][col]
        for r in range(len(mat)):
            if r != rank and mat[r][col]:
                f = mat[r][col] / pv
                mat[r] = [x - f * y for x, y in zip(mat[r], mat[rank])]
        rank += 1
    return rank


def strip_one(ctx, block):
    """ctx with one copy of the block's arms and ports removed, or None."""
    arms = list(ctx["arms"])
    if block["ports"] > ctx["ports"]:
        return None
    have, want = Counter(arms), Counter(block["arms"])
    if any(want[v] > have[v] for v in want):
        return None
    for v in block["arms"]:
        arms.remove(v)
    d = dict(ctx)
    d["arms"] = arms
    d["ports"] = ctx["ports"] - block["ports"]
    d["width"] = ctx["width"] - block["ports"] - sum(x + 1 for x in block["arms"])
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalogue", default=os.path.join(DATA, "alphabet_families.json"))
    ap.add_argument("--blocks", default=os.path.join(DATA, "neutral_blocks.json"))
    ap.add_argument("--token-blocks", default=None,
                    help="a second block file whose entries may carry a token triple; "
                         "one of these may be adjoined to a host with a single token")
    ap.add_argument("--targets", default=os.path.join(DATA, "alphabet_contexts_missing_v6.json"))
    ap.add_argument("--out", default=os.path.join(DATA, "batches", "neutral_extended.jsonl"))
    a = ap.parse_args()
    cat = json.load(open(a.catalogue))
    blocks = json.load(open(a.blocks))
    bsig = load_blocks(a.blocks)
    tblocks = [b for b in json.load(open(a.token_blocks))
               if b.get("token")] if a.token_blocks else []
    tgt = [c for c in json.load(open(a.targets)) if key(c) not in cat]
    tgt.sort(key=lambda c: c["width"])
    made = failed = 0
    reasons = {}
    with open(a.out, "w") as fh:
        for ctx in tgt:
            k = key(ctx)
            plans = []
            path, base = route(ctx, set(cat), bsig)
            if path is not None:
                plans.append(([blocks[i] for i in path], base))
            # second pass: strip one token block first, then ordinary blocks
            for tb in tblocks:
                red = strip_one(ctx, tb)
                if red is None:
                    continue
                if key(red) in cat:
                    plans.append(([tb], key(red)))
                p2, b2 = route(red, set(cat), bsig)
                if p2 is not None:
                    plans.append(([blocks[i] for i in p2] + [tb], b2))
            payload = None
            for bl, base in plans:
                e = cat[base]
                for fam in (e.get("menu") or [e]):
                    raw = fam.get("family") or fam
                    try:
                        payload = adjoin(raw, bl, ctx)
                    except Exception as exc:                 # noqa: BLE001
                        reasons[k] = f"{type(exc).__name__}: {exc}"
                        payload = None
                    if payload is not None:
                        break
                if payload is not None:
                    break
            if payload is None:
                failed += 1
                reasons.setdefault(k, "no route" if not plans else "adjoin failed")
                continue
            fh.write(json.dumps({"key": k, "ctx": ctx, "found": True,
                                 "attempts": [{"status": "EXTENDED"}],
                                 "family": payload}) + "\n")
            made += 1
            cat[k] = {"menu": [{"family": payload}]}
    print(f"targets {len(tgt)}; built {made}; failed {failed}")
    for k, v in sorted(reasons.items())[:20]:
        print("   ", k, "->", v)


if __name__ == "__main__":
    main()
