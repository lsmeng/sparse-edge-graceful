#!/usr/bin/env python3
"""Build the input-in-token variant catalogues from the batch files.

Variant "x": some pinned input label is a token member and no label equals
minus an input (usable to absorb one forced-antipode child in that slot).
Variant "all": every pinned input label is a token member and no label equals
minus an input (both children forced-antipode).

Sources (data/batches): alphabet_xtok_any2, alphabet_xtok2_any2,
alphabet_xtokfix_*, alphabet_var{act2,A2,L1}_x1/x2 -> variant x;
alphabet_var{act2,A2}_all1/all2 -> variant all.  Records are filtered by the
coefficient vectors (not by the request flags) and assembled with
assemble_alphabet_catalogue.py into data/alphabet_families_xtok.json (x) and
data/alphabet_families_xall.json (all).
"""
import glob
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.normpath(os.path.join(HERE, "..", "data"))
B = os.path.join(DATA, "batches")


def token_names(fam):
    labs = fam["labels"]
    out = []
    for fld in ("token_indices", "token2_indices"):
        ti = fam.get(fld) or {}
        out.append([labs[i]["name"] for i in ti.values()] if isinstance(ti, dict) else [])
    return out


def classify(fam):
    """Per input slot: the slot is FA-safe when its label is a token member
    and no other label is identically minus that input.  Returns "all" if
    every slot is FA-safe, "x" if at least one is, None otherwise."""
    params = fam["parameters"]
    cb = fam["coefficients_by_label"]
    L = fam["denominator"]
    inputs = [nm for nm in cb if nm.startswith("x")]
    if not inputs:
        return None
    t1, t2 = token_names(fam)
    safe = set()
    for nm in inputs:
        if nm not in t1 and nm not in t2:
            continue
        ix = params.index(nm) if nm in params else None
        if ix is None:
            continue
        neg = any(sum(1 for c in v if c) == 1 and v[ix] == -L
                  for other, v in cb.items() if other != nm)
        if not neg:
            safe.add(nm)
    if not safe:
        return None
    return "all" if safe == set(inputs) else "x"


def filtered(paths, want):
    out = []
    for p in paths:
        if not os.path.exists(p):
            continue
        for line in open(p):
            if not line.strip():
                continue
            r = json.loads(line)
            if not r.get("found"):
                continue
            c = classify(r["family"])
            if c is None:
                continue
            if want == "x" or c == "all":
                out.append(line)
    return out


def main():
    # any family whose coefficient vectors satisfy the per-slot test is usable,
    # whatever flags produced it, so every batch file is a source
    x_src = sorted(glob.glob(os.path.join(B, "alphabet_*.jsonl"))
                   + glob.glob(os.path.join(B, "local_*.jsonl"))
                   + glob.glob(os.path.join(B, "ws_*.jsonl"))
                   + glob.glob(os.path.join(B, "h2_*.jsonl"))
                   + glob.glob(os.path.join(B, "insert_*.jsonl"))
                   + glob.glob(os.path.join(B, "neutral_*.jsonl")))
    x_src = [p for p in x_src if not os.path.basename(p).startswith("_")]
    all_src = list(x_src)
    for want, srcs, out in (("x", x_src, "alphabet_families_xtok.json"), ("all", all_src, "alphabet_families_xall.json")):
        lines = filtered(srcs, want)
        tmp = os.path.join(B, f"_variant_{want}.jsonl")
        open(tmp, "w").write("".join(lines))
        if not lines:
            json.dump({}, open(os.path.join(DATA, out), "w"))
            print(want, "no records")
            continue
        r = subprocess.run([sys.executable, os.path.join(HERE, "assemble_alphabet_catalogue.py"), tmp,
                            "--out", os.path.join(DATA, out)], capture_output=True, text=True)
        summary = [l for l in r.stdout.splitlines() if l.startswith("menu:") or "records_usable" in l]
        print(want, len(lines), "records;", " ".join(summary), r.stderr[-300:])


if __name__ == "__main__":
    main()
