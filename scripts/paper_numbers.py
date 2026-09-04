#!/usr/bin/env python3
"""Emit the manuscript's numbers as LaTeX macros and the certificate table.

Writes ../../paper/numbers.tex (macros) and ../../paper/catalogue_table.tex
(the tabular body).  Every number the manuscript quotes about the search is
produced here, so a re-assembly of the catalogue updates the paper with one
command.

usage: paper_numbers.py [--paper DIR]
"""
import argparse
import glob
import json
import os
import re
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from run_alphabet_batch import key  # noqa: E402

DATA = os.path.normpath(os.path.join(HERE, "..", "data"))

GROUPS = [
    ("bottom cells", lambda c: c["kind"] != "root" and c["active"] in (False, "none")),
    ("continuing cells, free child", lambda c: c["kind"] != "root" and c["active"] == "free"),
    ("continuing cells, joined child", lambda c: c["kind"] != "root" and c["active"] in ("L1", "L11", "L12")),
    ("two-input cells", lambda c: c["kind"] != "root" and c["active"] in ("V21", "V22", "act2", "A2", "L1A2")),
    ("root cells", lambda c: c["kind"] == "root"),
]


def group(x):
    return f"{x:,}".replace(",", "{,}")


RIGID = {"h0_2_p0_act"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gate", default=None,
                    help="gate JSON from check_lookahead_gate.py --menu --json")
    ap.add_argument("--paper", default=os.path.normpath(os.path.join(HERE, "..", "..", "..", "paper")))
    a = ap.parse_args()
    emit = json.load(open(os.path.join(DATA, "alphabet_contexts_emittable.json")))
    cat = json.load(open(os.path.join(DATA, "alphabet_families.json")))
    xtok = json.load(open(os.path.join(DATA, "alphabet_families_xtok.json")))
    ctxlist = json.load(open(os.path.join(DATA, "alphabet_contexts.json")))
    E = {key(c): c for c in emit}
    rep = open(os.path.join(DATA, "emittable_report.md")).read()
    m = re.search(r"\((\d+) states\)", rep) or re.search(r"([\d,]+) states", rep)
    states = int(m.group(1).replace(",", "")) if m else 0

    def menu(k):
        e = cat[k]
        return e.get("menu") or [e]

    rows = []
    tot = [0] * 5
    for name, pred in GROUPS:
        ks = [key(c) for c in emit if pred(c)]
        # h0_2_p0_act is the rigid residue-two row, a constructor template
        # rather than a catalogue family, so it counts as covered
        wf = [k for k in ks if k in cat or k in RIGID]
        nf = sum(len(menu(k)) for k in wf if k in cat)
        cl = sum(1 for k in wf if k in cat and any(f.get("clean") for f in menu(k)))
        tk = sum(1 for k in wf if k in cat and any(f.get("token") for f in menu(k)))
        rows.append((name, len(ks), len(wf), nf, cl, tk))
        for i, v in enumerate((len(ks), len(wf), nf, cl, tk)):
            tot[i] += v
    tbl = [r"\begin{tabular}{lrrrrr}", r"\toprule",
           r"context kind & contexts & with a family & families & (E6) & token \\",
           r"\midrule"]
    for name, x1, x2, x3, x4, x5 in rows:
        tbl.append(f"{name} & {group(x1)} & {group(x2)} & {group(x3)} & {group(x4)} & {group(x5)} \\\\")
    tbl += [r"\midrule",
            "total & " + " & ".join(group(v) for v in tot) + r" \\",
            r"\bottomrule", r"\end{tabular}"]
    open(os.path.join(a.paper, "catalogue_table.tex"), "w").write("\n".join(tbl) + "\n")

    attempted = 0
    solver_runs = 0
    received = 0
    seen = set()
    for p in sorted(glob.glob(os.path.join(DATA, "batches", "alphabet_*.jsonl"))):
        if os.path.basename(p).startswith("_"):
            continue
        for line in open(p):
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except ValueError:
                continue
            attempted += 1
            solver_runs += len(r.get("attempts") or [])
            k = r.get("key")
            if r.get("found") and k not in seen:
                seen.add(k)
                received += 1
    allfam = sum(len(menu(k)) for k in cat)
    import math as _m
    W = max((f.get("width") or 0) for k in cat for f in menu(k))
    dens = {f["denominator"] for k in cat for f in menu(k)}
    M = 1
    for d in dens:
        M = M * d // _m.gcd(M, d)
    M = M * 24 // _m.gcd(M, 24)
    npar = max(len(f["parameters"]) for k in cat for f in menu(k))
    # the largest |coefficient| anywhere in the catalogue.  The solver caps
    # its own coefficients at 24, but the families built by the two
    # construction identities are not subject to that cap (the equal-pair
    # blocks reach 2^6 = 64), and it is the catalogue-wide value that the
    # realization lemma needs
    KMAX = max(abs(x) for k in cat for f in menu(k)
               for v in (f.get("family") or f)["coefficients_by_label"].values()
               for x in v)
    KMAX = max(KMAX, 24)
    # boxes of the realization lemma, in the notation of Appendix B
    # Carrier elimination (Appendix B, "Token, token pending").  The carrier is
    # chosen of least |det|; DMAX is the largest such minimum over the
    # catalogue and GMAX the largest |r . adj(M)| at the chosen carrier.  The
    # resolution step therefore works in the refined lattice M' = M * DMAX and
    # a label's coefficients after an elimination are bounded by 2 * GMAX *
    # KMAX rather than by KMAX.
    from carrier_determinants import token_vectors as _tv, analyse as _an
    DMAX, GMAX = 1, 0
    for k in cat:
        for f in menu(k):
            fam = f.get("family") or f
            if not isinstance(fam, dict) or "coefficients_by_label" not in fam:
                continue
            for _tag, d, g, _cols in _an(fam):
                if d is None:
                    continue
                DMAX, GMAX = max(DMAX, d), max(GMAX, g)
    MEFF = M * DMAX
    KEFF = 2 * GMAX * KMAX
    coord_lin, coord_con = 36 * W * M, M * (2 * W + W * W + 1)
    pair_lin, pair_con = 108 * W * MEFF, MEFF * (9 * W * W + 1)
    amax = npar * KEFF * (pair_lin + pair_con)          # D + 1 >= 1
    Aexp = len(str(amax)) - 1
    Alead = -(-amax // 10 ** Aexp)                      # round up

    fa_parents = [k for k in E if k.endswith("_act")]
    fa_cov = sum(1 for k in fa_parents if k in xtok or (k[:-4] + "_A2") in cat)
    pairs = []
    pp = os.path.join(DATA, "emittable_pairs.json")
    if os.path.exists(pp):
        pairs = [tuple(t) for t in json.load(open(pp))]
    gate_fail = gate_real = 0
    if a.gate and os.path.exists(a.gate):
        g = json.load(open(a.gate))
        fp = [tuple(t) for t in g["menu_gate"]["failing_pairs"]]
        gate_fail = len(fp)
        ps = set(pairs)
        gate_real = sum(1 for t in fp if t in ps)
    # the neutral blocks and the families the adjunction lemma produced
    bpath = os.path.join(DATA, "neutral_blocks_all.json")
    if not os.path.exists(bpath):
        bpath = os.path.join(DATA, "neutral_blocks.json")
    blocks = json.load(open(bpath)) if os.path.exists(bpath) else []
    nblocks = len(blocks)
    btbl = [r"% generated by scripts/paper_numbers.py -- do not edit",
            r"\begin{tabular}{cllp{0.52\textwidth}}", r"\hline",
            r"ports & arms & token & labels \\", r"\hline"]
    def _lab(v):
        v = v if isinstance(v, list) else [v]
        return "(" + ",".join(str(x) for x in v) + ")" if len(v) > 1 else str(v[0])
    for b in blocks:
        arms = ", ".join(str(x) for x in b["arms"]) or "---"
        lab = ", ".join(f"${_lab(v)}$" for v in b["labels"])
        tk = "yes" if b.get("token") else ""
        btbl.append(f"{b['ports']} & {arms} & {tk} & {lab} \\\\")
    btbl += [r"\hline", r"\end{tabular}"]
    open(os.path.join(a.paper, "blocks_table.tex"), "w").write("\n".join(btbl) + "\n")
    def nlines(nm):
        f = os.path.join(DATA, "batches", nm)
        return sum(1 for l in open(f) if l.strip()) if os.path.exists(f) else 0
    nb_targets = 0
    nb_built = nlines("neutral_extended.jsonl")
    nb_var = nlines("neutral_xtok.jsonl")
    nb_tok = nlines("neutral_tok1.jsonl")
    mt = os.path.join(DATA, "alphabet_contexts_missing_v6.json")
    if os.path.exists(mt):
        nb_targets = len(json.load(open(mt)))

    mac = {
        "NumMaxWidth": W,
        "NumLatticeM": M,
        "NumParams": npar,
        "NumCoefBound": KMAX,
        "NumDetMax": DMAX,
        "NumAdjMax": GMAX,
        "NumCoefBoundEff": KEFF,
        "NumLatticeMEff": MEFF,
        "NumCoordLin": coord_lin,
        "NumCoordCon": coord_con,
        "NumPairLin": pair_lin,
        "NumPairCon": pair_con,
        "NumPairs": len(pairs),
        "NumGateFail": gate_fail,
        "NumGateFailRealizable": gate_real,
        "NumContextList": len(ctxlist),
        "NumStates": states,
        "NumEmittable": len(E),
        "NumEmittableWithFamily": tot[1],
        "NumEmittableMissing": tot[0] - tot[1],
        "NumCatContexts": len(cat),
        "NumCatFamilies": allfam,
        "NumEmittableFamilies": tot[2],
        "NumCleanContexts": tot[3],
        "NumNotCleanContexts": tot[1] - tot[3],
        "NumTokenContexts": tot[4],
        "NumAttempted": attempted,
        "NumSolverRuns": solver_runs,
        "NumReceived": received,
        "NumVariantContexts": len(xtok),
        "NumVariantFamilies": sum(len(v.get("menu") or [v]) for v in xtok.values()),
        "NumFreeChildContexts": len(fa_parents),
        "NumFreeChildCovered": fa_cov,
        "NumNeutralBlocks": nblocks,
        "NumNeutralTargets": nb_targets,
        "NumNeutralBuilt": nb_built,
        "NumNeutralVariantBuilt": nb_var,
        "NumNeutralTokenBuilt": nb_tok,
    }
    out = ["% generated by scripts/paper_numbers.py -- do not edit",
           f"\\newcommand{{\\AConst}}{{{Alead}\\cdot 10^{{{Aexp}}}}}"]
    for k, v in mac.items():
        out.append(f"\\newcommand{{\\{k}}}{{{group(v)}}}")
    open(os.path.join(a.paper, "numbers.tex"), "w").write("\n".join(out) + "\n")
    for k, v in mac.items():
        print(f"{k:28s} {v}")


if __name__ == "__main__":
    main()
