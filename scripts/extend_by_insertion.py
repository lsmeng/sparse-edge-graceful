#!/usr/bin/env python3
"""Build families for long-armed contexts from short-armed ones.

The six-edge insertion replaces an arm by one that is six longer and changes
nothing else in the cell.  Writing c for the label at the owner end of the arm
and d for the next label, the six new labels are

    (-2c-d)/3, (c-d)/3, (c+2d)/3, (2c+d)/3, (-c+d)/3, (-c-2d)/3,

three inverse pairs; the seven outputs they create are exactly those six
labels together with the output c+d that the arm had before, so P=O holds
identically in the parameters.  For a port, an arm of length zero whose only
label is c and whose output is c itself, the six new labels are

    c/3, -2c/3, 4c/3, -c/3, 2c/3, -4c/3,

and the same statement holds with c in place of c+d.  Both identities are
checked by scripts/six_edge_insertion.py and are verified by hand in the
manuscript.

This script applies the insertion to catalogue families and writes the result
in the batch JSONL format, so that the ordinary assembler and the independent
checker take it from there.  Nothing here is trusted: the emitted families are
re-verified by check_alphabet_families.py like any other.

usage: extend_by_insertion.py [--out data/batches/insert_extended.jsonl]
"""
import argparse
import json
import os
import sys
from fractions import Fraction as Q
from math import gcd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from run_alphabet_batch import key, row_specs  # noqa: E402

DATA = os.path.normpath(os.path.join(HERE, "..", "data"))
ARM_MULT = [(-2, -1), (1, -1), (1, 2), (2, 1), (-1, 1), (-1, -2)]
PORT_MULT = [Q(1, 3), Q(-2, 3), Q(4, 3), Q(-1, 3), Q(2, 3), Q(-4, 3)]


def form(vec, params, L):
    ts = []
    for v, p in zip(vec, params):
        if not v:
            continue
        q = Q(v, L)
        ts.append(f"{q}*{p}" if q != 1 else p)
    return " + ".join(ts) if ts else "0"


def new_row_specs(fam, ctx):
    """The base row specs with row 0's arms and ports replaced by ctx's."""
    rs = [dict(r) for r in (fam.get("row_specs") or [])]
    if not rs:
        return None
    rs[0] = dict(rs[0])
    rs[0]["arms"] = list(ctx["arms"])
    rs[0]["ports"] = ctx["ports"]
    return rs


def extend(fam, ctx, arm_index, is_port, port_index, at=0):
    """Return a CP-SAT-style payload for ctx, or None."""
    cbl = fam["coefficients_by_label"]
    params = fam["parameters"]
    L = int(fam["denominator"])
    labs = fam["labels"]
    L2 = L * 3 // gcd(L, 3)
    sc = L2 // L
    new = {nm: [v * sc for v in vec] for nm, vec in cbl.items()}
    meta = {l["name"]: l for l in labs}
    row = 0
    if is_port:
        pname = f"r{row}p{port_index}"
        if pname not in new:
            return None
        c = new.pop(pname)
        base = [dict(l) for l in labs if l["name"] != pname]
        arm_new = arm_index
        six = []
        for mu in PORT_MULT:
            r = [mu * v for v in c]
            if any(x.denominator != 1 for x in r):
                return None
            six.append([int(x) for x in r])
        names = [f"r{row}a{arm_new}x{i}" for i in range(7)]
        new[names[0]] = c
        for i, vec in enumerate(six):
            new[names[i + 1]] = vec
        for i, nm in enumerate(names):
            base.append({"kind": "arm", "name": nm, "role": f"row {row} arm {arm_new} position {i}",
                         "row": row, "arm": arm_new, "pos": i})
        # renumber the surviving ports of that row
        rest = sorted((l for l in base if l["kind"] == "port" and l["row"] == row),
                      key=lambda l: l["pos"])
        ren = {pname: names[0]}
        for i, l in enumerate(rest):
            old = l["name"]
            l["name"] = f"r{row}p{i}"
            l["pos"] = i
            if old != l["name"]:
                ren[old] = l["name"]
                new[l["name"]] = new.pop(old)
        pairs = remap_pairs(fam, ren) + [[names[1], names[4]], [names[2], names[5]],
                                         [names[3], names[6]]]
        return finish(new, base, params, L2, fam, ctx, pairs, ren)
    # ordinary arm: lengthen arm `arm_index` of row 0 by six
    ell = max(l["pos"] for l in labs if l.get("kind") == "arm" and l.get("arm") == arm_index
              and l.get("row") == row)
    if at + 1 > ell:
        return None
    c = new[f"r{row}a{arm_index}x{at}"]
    d = new[f"r{row}a{arm_index}x{at + 1}"]
    six = []
    for p, q in ARM_MULT:
        r = [Q(p * cc + q * dd, 3) for cc, dd in zip(c, d)]
        if any(x.denominator != 1 for x in r):
            return None
        six.append([int(x) for x in r])
    old = {i: new.pop(f"r{row}a{arm_index}x{i}") for i in range(ell + 1)}
    base = [dict(l) for l in labs
            if not (l.get("kind") == "arm" and l.get("arm") == arm_index and l.get("row") == row)]
    seq = [old[i] for i in range(at + 1)] + six + [old[i] for i in range(at + 1, ell + 1)]
    ren = {f"r{row}a{arm_index}x{i}": f"r{row}a{arm_index}x{i}" for i in range(at + 1)}
    for i in range(at + 1, ell + 1):
        ren[f"r{row}a{arm_index}x{i}"] = f"r{row}a{arm_index}x{i + 6}"
    for i, vec in enumerate(seq):
        nm = f"r{row}a{arm_index}x{i}"
        new[nm] = vec
        base.append({"kind": "arm", "name": nm, "role": f"row {row} arm {arm_index} position {i}",
                     "row": row, "arm": arm_index, "pos": i})
    six_names = [f"r{row}a{arm_index}x{i}" for i in range(at + 1, at + 7)]
    pairs = remap_pairs(fam, ren) + [[six_names[0], six_names[3]], [six_names[1], six_names[4]],
                                     [six_names[2], six_names[5]]]
    return finish(new, base, params, L2, fam, ctx, pairs, ren)


def remap_pairs(fam, ren):
    out = []
    for a, b in (fam.get("mirror_pairs_named") or []):
        out.append([ren.get(a, a), ren.get(b, b)])
    return out


def finish(new, labs, params, L2, fam, ctx, pairs_named, ren):
    # the insertion is an identity, but the six new forms must still be
    # distinct from the ones already there and nonzero
    vals = list(new.values())
    if any(all(v == 0 for v in vec) for vec in vals):
        return None
    seen = set()
    for vec in vals:
        t = tuple(vec)
        if t in seen:
            return None
        seen.add(t)
    order = {"head": 0, "head_chain": 1, "arm": 2, "port": 3, "input": 4, "active": 5, "zero": 6}
    labs = sorted(labs, key=lambda l: (l.get("row", 0), order.get(l["kind"], 9),
                                       l.get("arm", -1), l.get("pos", 0), l["name"]))
    for i, l in enumerate(labs):
        l["index"] = i
    names = [l["name"] for l in labs]
    coefs = [new[n] for n in names]
    idx = {n: i for i, n in enumerate(names)}
    pairs = []
    for a, b in pairs_named:
        if a in idx and b in idx:
            pairs.append([idx[a], idx[b]])
    pairs_named = [[names[i], names[j]] for i, j in pairs]
    tok = {r: ren.get(v, v) for r, v in (fam.get("token_named") or {}).items()} or None
    tok_idx = {r: idx[v] for r, v in tok.items()} if isinstance(tok, dict) and all(v in idx for v in tok.values()) else None
    tok2 = {r: ren.get(v, v) for r, v in (fam.get("token2_named") or {}).items()} or None
    tok2_idx = {r: idx[v] for r, v in tok2.items()} if isinstance(tok2, dict) and all(v in idx for v in tok2.values()) else None
    return {
        "status": "EXTENDED", "denominator": L2, "parameters": params,
        "labels": labs, "coefficients": coefs,
        "coefficients_by_label": {n: new[n] for n in names},
        "forms": [form(new[n], params, L2) for n in names],
        "mirror_pairs": pairs, "mirror_pairs_named": pairs_named,
        "token_indices": tok_idx, "token_named": tok if tok_idx else None,
        "token2_indices": tok2_idx, "token2_named": tok2 if tok2_idx else None,
        "token": bool(tok_idx), "two_tokens": bool(tok2_idx),
        "token_rank": fam.get("token_rank"), "width": len(names),
        "row_specs": new_row_specs(fam, ctx), "root_row": bool(fam.get("root_row")),
        "zero_label_index": None, "root_owner_output_index": fam.get("root_owner_output_index"),
        "root_zero_output": fam.get("root_zero_output"),
        "head_mult": fam.get("head_ratio"), "head_mult_free": True,
        "input_in_token": fam.get("input_in_token"),
        "provenance": {"six_edge_insertion": True, "from": key(fam.get("ctx", {})) if fam.get("ctx") else None},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalogue", default=os.path.join(DATA, "alphabet_families.json"))
    ap.add_argument("--emittable", default=os.path.join(DATA, "alphabet_contexts_emittable.json"))
    ap.add_argument("--out", default=os.path.join(DATA, "batches", "insert_extended.jsonl"))
    ap.add_argument("--targets", default=None,
                    help="JSON list of contexts to build (default: the emittable contexts "
                         "absent from the catalogue)")
    a = ap.parse_args()
    cat = json.load(open(a.catalogue))
    if a.targets:
        E = {key(c): c for c in json.load(open(a.targets))}
        missing = sorted((k for k in E if k not in cat), key=lambda k: E[k]["width"])
    else:
        E = {key(c): c for c in json.load(open(a.emittable))}
        missing = sorted((k for k in E if k not in cat), key=lambda k: E[k]["width"])
    made = failed = 0
    with open(a.out, "w") as fh:
        for k in missing:
            ctx = E[k]
            arms = list(ctx["arms"])
            for i, ell in enumerate(arms):
                if ell < 6:
                    continue
                rest = arms[:i] + arms[i + 1:]
                is_port = (ell == 6)
                b = dict(ctx)
                b["arms"] = sorted(rest) if is_port else sorted(rest + [ell - 6])
                b["ports"] = ctx["ports"] + 1 if is_port else ctx["ports"]
                b["width"] = ctx["width"] - 6
                bk = key(b)
                if bk not in cat:
                    continue
                e = cat[bk]
                payload = None
                for fam in (e.get("menu") or [e]):
                    raw = fam.get("family") or fam
                    bar = list((raw.get("row_specs") or [{}])[0].get("arms") or b["arms"])
                    nctx = dict(ctx)
                    if is_port:
                        ai = len(bar)
                        nctx["arms"] = bar + [6]
                    else:
                        if (ell - 6) not in bar:
                            continue
                        ai = bar.index(ell - 6)
                        nctx["arms"] = bar[:ai] + [ell] + bar[ai + 1:]
                    for at in range(0, (ell - 6) if not is_port else 1):
                        try:
                            payload = extend(raw, nctx, ai, is_port, b["ports"] - 1, at)
                        except Exception:
                            payload = None
                        if payload is not None:
                            break
                    if payload is not None:
                        break
                if payload is None:
                    failed += 1
                    continue
                fh.write(json.dumps({"key": k, "ctx": ctx, "found": True,
                                     "attempts": [{"status": "EXTENDED"}],
                                     "family": payload}) + "\n")
                made += 1
                # a family just built can serve as the base for a longer one
                cat[k] = {"menu": [{"family": payload}]}
                break
    print(f"missing {len(missing)}; extended records written {made}; construction failed {failed}")


if __name__ == "__main__":
    main()
