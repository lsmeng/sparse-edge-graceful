#!/usr/bin/env python3
"""One-step lookahead gate over the free-token alphabet catalogue.

Input: ``data/alphabet_families.json`` written by
``assemble_alphabet_catalogue.py``.

Setting.  A parent cell ``P`` whose context has an active child
(``ctx.active`` in ``{"free", "L1", "L11"}``) carries a pinned *input* label
``x``: that label IS the shared edge, i.e. the exposed head of the child cell
``C`` hung underneath.  For an ``L1``/``L11`` joint the residue-1 letter(s)
are already folded into ``P`` as its lower rows, so ``P``'s input ``x`` sits on
the bottom row and the relevant ``C`` is the family hung below that row -- an
ordinary head-carrying family, handled by the same test.

Gate.  A one-step identity collision occurs when a label of ``P`` that is
*forced* (its coefficient vector is nonzero only on ``x``, so the label equals
``q*x`` whatever the free parameters do) is identically equal to a label of
``C`` that depends only on ``y`` (equal to ``q*y``).  Such a pair of labels can
never be separated by a parameter choice, so that (child family, parent
family) combination is inadmissible.  The parent's own input label
(``q == 1``) is dropped: it is the shared edge, and the shared edge is placed
exactly once.

Identification.  The exposed head of ``C`` is ``h*y`` with an integer head
multiplier ``h >= 1`` (the CP-SAT batch runs with ``--head-mult-free``), and it
is the head label that is the shared edge, so ``x = h*y`` and a child label
``q*y`` equals ``(q/h)*x``.  The default comparison is this normalised one;
``--raw`` compares the ratios directly (the literal ``y = x`` reading).  The
two coincide exactly when ``h == 1``.

Modes.

    default   one chosen family per context (``menu[0]``): every ordered
              (child family, parent family) pair is tested.
    --menu    every ordered (child context, parent context) pair is tested
              against the FULL menus: the pair passes when SOME combination of
              a child family and a parent family from the two menus has no
              collision.  Reports the context pairs with no passing
              combination.

Also echoes the pairwise token Jacobian recorded by the assembler: a token
whose three coefficient vectors span fewer than two dimensions cannot be
paired by solving ``T_B = -T_A`` with a positive-dimensional solution set.

All ratio arithmetic is exact (``fractions.Fraction``).

Usage:
    check_lookahead_gate.py [CATALOGUE.json] [--menu] [--raw] [--json OUT]
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
INPUT_ACTIVE = ("free", "L1", "L11", True)
MAX_SET_PRINT = 200


def frac(s):
    """Exact Fraction from the catalogue's string ratio (None on garbage)."""
    try:
        return Q(str(s))
    except (ValueError, ZeroDivisionError, TypeError):
        return None


def families_of(entry):
    """The menu of an entry (older catalogues carry the chosen family only)."""
    menu = entry.get("menu")
    if isinstance(menu, list) and menu:
        return menu
    return [entry]


def parent_forced(fam, stats):
    """Non-shared-edge forced ratios: {Fraction -> [label names]}.

    The pinned input label is the shared edge and is excluded (this is the
    ``q != 1`` exemption); any *other* forced label with ratio 1 is kept, since
    it would place the value ``x`` a second time.
    """
    out = defaultdict(list)
    for f in fam.get("forced_forms") or []:
        if not isinstance(f, dict):
            stats["bad_forced_form"] += 1
            continue
        if f.get("kind") == "input":
            continue
        q = frac(f.get("ratio"))
        if q is None:
            stats["bad_forced_ratio"] += 1
            continue
        out[q].append(f.get("name"))
    return out


def child_head_only(fam, stats, h, normalise):
    """Head-only ratios in the parent's ``x`` units: {Fraction -> [names]}."""
    out = defaultdict(list)
    for f in fam.get("head_only_forms") or []:
        if not isinstance(f, dict):
            stats["bad_head_only_form"] += 1
            continue
        q = frac(f.get("ratio"))
        if q is None:
            stats["bad_head_only_ratio"] += 1
            continue
        out[q / h if normalise else q].append(f.get("name"))
    return out


def collect(cat, normalise, stats):
    """Parent and child family records, keyed by context."""
    parents, children = defaultdict(list), defaultdict(list)
    for key in sorted(cat):
        e = cat[key]
        if not isinstance(e, dict):
            stats["skipped_non_object_entry"] += 1
            continue
        ctx = e.get("ctx") if isinstance(e.get("ctx"), dict) else {}
        active = ctx.get("active")
        joint = active if active in ("free", "L1", "L11") else "free"
        for pos, fam in enumerate(families_of(e)):
            if not isinstance(fam, dict) or "forced_forms" not in fam:
                stats["skipped_family_without_derived_data"] += 1
                continue
            if fam.get("has_input") or active in INPUT_ACTIVE:
                if not fam.get("has_input"):
                    stats["skipped_parent_without_input_label"] += 1
                else:
                    parents[key].append(
                        {"key": key, "pos": pos, "joint": joint,
                         "forced": parent_forced(fam, stats), "fam": fam})
            if fam.get("has_head"):
                h = frac(fam.get("head_ratio"))
                if h is None or h == 0:
                    stats["skipped_child_without_head_ratio"] += 1
                else:
                    children[key].append(
                        {"key": key, "pos": pos, "head": h,
                         "head_only": child_head_only(fam, stats, h, normalise),
                         "fam": fam})
            elif ctx.get("kind") == "root":
                stats["root_family_not_usable_as_child"] += 1
    return parents, children


def show_set(vals, label):
    print(f"{label} ({len(vals)}):")
    head = sorted(vals)[:MAX_SET_PRINT]
    print("  " + (", ".join(str(q) for q in head) or "(none)")
          + (f", ... {len(vals) - len(head)} more" if len(vals) > len(head) else ""))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("catalogue", nargs="?",
                    default=os.path.join(DATA, "alphabet_families.json"))
    ap.add_argument("--menu", action="store_true",
                    help="also run the context-level gate over the full menus")
    ap.add_argument("--raw", action="store_true",
                    help="compare ratios literally (y = x) instead of "
                         "normalising by the child's head multiplier")
    ap.add_argument("--json", default=None, help="also write the report as JSON")
    ap.add_argument("--limit", type=int, default=40,
                    help="print at most N examples per list (0 = all)")
    a = ap.parse_args(argv)
    normalise = not a.raw
    mode = "raw (y = x)" if a.raw else "normalised (x = h*y)"

    if not os.path.exists(a.catalogue):
        print(f"error: {a.catalogue} does not exist", file=sys.stderr)
        return 2
    with open(a.catalogue) as fh:
        cat = json.load(fh)
    if not isinstance(cat, dict):
        print("error: catalogue is not a key -> family map", file=sys.stderr)
        return 2

    stats = Counter()
    parents, children = collect(cat, normalise, stats)

    def cap(seq):
        return seq if a.limit <= 0 else seq[:a.limit]

    print(f"catalogue: {a.catalogue}")
    print(f"families: {sum(len(families_of(e)) for e in cat.values())} over "
          f"{len(cat)} contexts")
    print(f"parent contexts (with input x): {len(parents)}   "
          f"child contexts (with head y): {len(children)}")
    print(f"comparison: {mode}")

    # ------------------------------------------------- chosen-family gate
    # Families are grouped by their ratio signature so that the exact pair
    # counts can be obtained without enumerating every ordered pair.
    chosen_p = {k: v[0] for k, v in parents.items()}
    chosen_c = {k: v[0] for k, v in children.items()}
    psig = defaultdict(list)
    for k, p in chosen_p.items():
        psig[frozenset(p["forced"])].append(k)
    csig = defaultdict(list)
    for k, c in chosen_c.items():
        csig[frozenset(c["head_only"])].append(k)

    n_pairs = len(chosen_c) * len(chosen_p)
    n_blocked = 0
    ratio_hits = Counter()
    examples = []
    blocked_children, blocked_parents = Counter(), Counter()
    for cs, ckeys in csig.items():
        for ps, pkeys in psig.items():
            inter = cs & ps
            if not inter:
                continue
            n = len(ckeys) * len(pkeys)
            n_blocked += n
            for q in inter:
                ratio_hits[q] += n
            for ck in ckeys:
                blocked_children[ck] += len(pkeys)
            for pk in pkeys:
                blocked_parents[pk] += len(ckeys)
            room = 10 ** 9 if a.limit <= 0 else a.limit - len(examples)
            for ck in ckeys:
                for pk in pkeys:
                    if room <= 0:
                        break
                    examples.append((ck, pk, sorted(inter)))
                    room -= 1
                if room <= 0:
                    break
    print()
    print(f"chosen-family gate: {n_pairs} ordered pairs, "
          f"{n_blocked} blocked ({n_pairs - n_blocked} admissible)")
    print(f"  distinct forced signatures {len(psig)}, "
          f"head-only signatures {len(csig)}")
    print(f"  collisions by ratio: "
          + (", ".join(f"{q}:{n}" for q, n in
                       sorted(ratio_hits.items(), key=lambda kv: -kv[1])[:20])
             or "(none)"))
    dead_c = [k for k, n in blocked_children.items() if n == len(chosen_p)]
    dead_p = [k for k, n in blocked_parents.items() if n == len(chosen_c)]
    print(f"  child contexts blocked against EVERY parent: {len(dead_c)}")
    print(f"  parent contexts blocked against EVERY child: {len(dead_p)}")
    print("  example blocked pairs:")
    for ck, pk, rs in cap(examples):
        cn = ",".join(str(x) for q in rs
                      for x in chosen_c[ck]["head_only"].get(q, []))
        pn = ",".join(str(x) for q in rs
                      for x in chosen_p[pk]["forced"].get(q, []))
        print(f"    child {ck:<24s} parent {pk:<24s} "
              f"({chosen_p[pk]['joint']:>4s})  ratios "
              f"{','.join(str(q) for q in rs):<14s} {cn} == {pn}")
    if not examples:
        print("    (none)")
    elif a.limit > 0 and n_blocked > len(examples):
        print(f"    ... {n_blocked - len(examples)} more (use --limit 0)")

    # --------------------------------------------------------- global sets
    print()
    show_set({q for p in chosen_p.values() for q in p["forced"]},
             "global forced ratios of parents, input label excluded")
    show_set({q / c["head"] if not normalise else q
              for c in chosen_c.values() for q in c["head_only"]},
             "global head-only ratios of children, RAW")
    show_set({q if normalise else q / c["head"]
              for c in chosen_c.values() for q in c["head_only"]},
             "global head-only ratios of children, NORMALISED by h")
    hmults = Counter(str(c["head"]) for c in chosen_c.values())
    print(f"head multipliers over chosen child families: "
          f"{dict(sorted(hmults.items(), key=lambda kv: Q(kv[0])))}")

    # ------------------------------------------------------------ menu mode
    menu_report = None
    if a.menu:
        # per context: the distinct signatures its menu can offer
        pmenu = {k: frozenset(frozenset(p["forced"]) for p in v)
                 for k, v in parents.items()}
        cmenu = {k: frozenset(frozenset(c["head_only"]) for c in v)
                 for k, v in children.items()}
        pclass, cclass = defaultdict(list), defaultdict(list)
        for k, s in pmenu.items():
            pclass[s].append(k)
        for k, s in cmenu.items():
            cclass[s].append(k)

        def passes(cs_set, ps_set):
            for cs in cs_set:
                if not cs:
                    return True
                for ps in ps_set:
                    if not (cs & ps):
                        return True
            return False

        n_ctx_pairs = len(cmenu) * len(pmenu)
        failing = []
        n_fail = 0
        for cs_set, ckeys in cclass.items():
            for ps_set, pkeys in pclass.items():
                if passes(cs_set, ps_set):
                    continue
                n_fail += len(ckeys) * len(pkeys)
                for ck in ckeys:
                    for pk in pkeys:
                        failing.append((ck, pk))
        failing.sort()
        print()
        print(f"menu gate: {n_ctx_pairs} ordered context pairs, "
              f"{n_fail} with NO passing (child family, parent family) "
              f"combination")
        print(f"  distinct menu signature classes: parents {len(pclass)}, "
              f"children {len(cclass)}")
        fail_children = Counter(ck for ck, _ in failing)
        fail_parents = Counter(pk for _, pk in failing)
        dead_menu_c = sorted(k for k, n in fail_children.items()
                             if n == len(pmenu))
        dead_menu_p = sorted(k for k, n in fail_parents.items()
                             if n == len(cmenu))
        print(f"  child contexts appearing in a failure: {len(fail_children)}"
              f"   of which failing against EVERY parent context: "
              f"{len(dead_menu_c)}")
        print(f"  parent contexts appearing in a failure: {len(fail_parents)}"
              f"   of which failing against EVERY child context: "
              f"{len(dead_menu_p)}")
        if dead_menu_c:
            print("  children with no admissible parent at all: "
                  + ", ".join(cap(dead_menu_c))
                  + (f", ... {len(dead_menu_c) - a.limit} more"
                     if a.limit > 0 and len(dead_menu_c) > a.limit else ""))
        if dead_menu_p:
            print("  parents with no admissible child at all: "
                  + ", ".join(cap(dead_menu_p))
                  + (f", ... {len(dead_menu_p) - a.limit} more"
                     if a.limit > 0 and len(dead_menu_p) > a.limit else ""))
        print("  context pairs with no passing combination "
              "(ratios shown are the union over each menu):")
        for ck, pk in cap(failing):
            cs = sorted({q for c in children[ck] for q in c["head_only"]})
            ps = sorted({q for p in parents[pk] for q in p["forced"]})
            print(f"    child {ck:<24s} parent {pk:<24s}  "
                  f"child ratios {{{','.join(str(q) for q in cs)}}}  "
                  f"parent forced {{{','.join(str(q) for q in ps)}}}")
        if not failing:
            print("    (none)")
        elif a.limit > 0 and len(failing) > a.limit:
            print(f"    ... {len(failing) - a.limit} more (use --limit 0)")
        menu_report = {
            "n_context_pairs": n_ctx_pairs, "n_failing": n_fail,
            "failing_pairs": [[c, p] for c, p in failing],
            "n_parent_classes": len(pclass), "n_child_classes": len(cclass),
            "children_failing_every_parent": dead_menu_c,
            "parents_failing_every_child": dead_menu_p,
        }

    # ------------------------------------------------------ token Jacobian
    tok = [(k, i, f) for k, e in cat.items()
           for i, f in enumerate(families_of(e))
           if isinstance(f, dict) and f.get("token")]
    jac = [(k, i, f) for k, i, f in tok if isinstance(f.get("token_jacobian"), dict)]
    degen = [(k, i, f) for k, i, f in jac if f["token_jacobian"].get("degenerate")]
    print()
    print(f"token Jacobian: {len(tok)} token families, "
          f"{len(tok) - len(jac)} without a recorded rank")
    print("  rank over all parameters:     "
          + str(dict(sorted(Counter(f['token_jacobian']['rank_all']
                                    for _, _, f in jac).items()))))
    print("  rank over parameters minus x: "
          + str(dict(sorted(Counter(f['token_jacobian']['rank_without_x']
                                    for _, _, f in jac).items()))))
    print(f"  families with rank < 2 over all parameters: {len(degen)}")
    for k, i, f in cap(degen):
        j = f["token_jacobian"]
        print(f"    {k}  menu[{i}]  rank={j['rank_all']} "
              f"(no x: {j['rank_without_x']})  "
              f"token {','.join(str(t) for t in j.get('token_labels') or [])}")
    if not degen:
        print("    (none)")
    elif a.limit > 0 and len(degen) > a.limit:
        print(f"    ... {len(degen) - a.limit} more")

    if stats:
        print()
        print("skipped / malformed:")
        for k in sorted(stats):
            print(f"  {k}: {stats[k]}")

    if a.json:
        report = {
            "catalogue": os.path.abspath(a.catalogue),
            "mode": mode,
            "n_parent_contexts": len(parents), "n_child_contexts": len(children),
            "chosen_gate": {
                "n_pairs": n_pairs, "n_blocked": n_blocked,
                "ratio_hits": {str(q): n for q, n in ratio_hits.items()},
                "children_blocked_against_every_parent": sorted(dead_c),
                "parents_blocked_against_every_child": sorted(dead_p),
                "examples": [[c, p, [str(q) for q in rs]] for c, p, rs in examples],
            },
            "menu_gate": menu_report,
            "global_forced_ratios": sorted(
                {str(q) for p in chosen_p.values() for q in p["forced"]}, key=Q),
            "global_head_only_ratios": sorted(
                {str(q) for c in chosen_c.values() for q in c["head_only"]}, key=Q),
            "token_jacobian_degenerate": [[k, i] for k, i, _ in degen],
            "skipped": dict(stats),
        }
        with open(a.json, "w") as fh:
            json.dump(report, fh, indent=1, sort_keys=True)
        print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
