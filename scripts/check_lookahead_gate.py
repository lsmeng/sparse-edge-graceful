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

Unit-negation extension (default; ``--legacy`` disables it).  A family's
*token* labels (``token_named`` and ``token2_named``, i.e. the ``a``/``b``/
``c`` roles of its one or two tokens) are its *units*.  Any antipodal PAIR
among them -- two units whose coefficient vectors are exact negatives of one
another, comparing the raw vectors from ``coefficients_by_label`` so pairs
may straddle the two tokens -- cancels: the pair already places a value and
its negative inside the SAME family, so neither member is a fresh commitment.
What survives is the family's set of units.  The construction places the
*negative* of every surviving unit label somewhere else in the tree, so a
one-step identity collision also occurs when:

    (i)  the negative of a unit label of P that is forced (depends only on
         ``x``) is identically equal to a label of C that depends only on
         ``y`` (i.e. lands in C's existing head-only set); or
    (ii) the negative of a unit label of C that is head-only (depends only
         on ``y``) is identically equal to a label of P that is forced
         (i.e. lands in P's existing forced set).

Both checks reuse the already-computed, denominator-correct ``forced``/
``head_only`` ratio tables (keyed back by label name) -- a unit that is
neither forced nor head-only depends on some other, unrelated free
parameter of its own family and so cannot coincide identically with
anything in the other family.  The one designed exception is P's own unit
label being exactly the input ``x`` itself (ratio exactly 1): its negative
is the antipode of C's head, placed once on purpose, not a fresh collision;
other multiples of the input are NOT exempted.  (In practice this exception
is automatic: the forced table already drops the literal input entry, so a
unit named ``x`` never reaches the ``(i)`` test.)  No analogous exception is
needed on the C side -- C's own head label never occurs as one of its unit
names in the catalogue.

The extension is wired into the ``--menu`` context-level gate (the report
``paper_numbers.py`` reads for ``\\NumGateFail``/``\\NumGateFailRealizable``);
the single-chosen-family gate printed by default is diagnostic only and is
unaffected either way.

Usage:
    check_lookahead_gate.py [CATALOGUE.json] [--menu] [--raw] [--legacy]
                             [--json OUT]
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


def unit_labels(rec, stats=None):
    """A family's units: its token labels, minus antipodal pairs.

    ``rec`` is a menu entry (carries ``token_named``/``token2_named`` and a
    nested ``family`` dict with ``coefficients_by_label``).  Returns the
    surviving unit label *names*, in stable order.  Two units cancel when
    their raw coefficient vectors are exact negatives of one another --
    raw, not divided by the family's ``denominator``, since that denominator
    is common to every label of one family and negation/equality both
    survive a common positive rescaling unchanged.
    """
    fam = rec.get("family") or rec
    cbl = fam.get("coefficients_by_label") or {}
    names, seen = [], set()
    for tok_key in ("token_named", "token2_named"):
        tn = rec.get(tok_key) or fam.get(tok_key) or {}
        if not isinstance(tn, dict):
            continue
        for name in tn.values():
            if name not in seen:
                seen.add(name)
                names.append(name)
    vecs = {}
    for n in names:
        v = cbl.get(n)
        if v is None:
            if stats is not None:
                stats["unit_label_missing_vector"] += 1
            continue
        vecs[n] = tuple(v)
    removed = set()
    ordered = [n for n in names if n in vecs]
    for i, a in enumerate(ordered):
        if a in removed:
            continue
        va = vecs[a]
        for b in ordered[i + 1:]:
            if b in removed:
                continue
            vb = vecs[b]
            if len(va) == len(vb) and all(x == -y for x, y in zip(va, vb)):
                removed.add(a)
                removed.add(b)
                break
    return [n for n in ordered if n not in removed]


def invert_ratio_names(d):
    """{Fraction: [names]} -> {name: Fraction}, as built by parent_forced /
    child_head_only (each name occurs under exactly one ratio there)."""
    out = {}
    for q, names in d.items():
        for n in names:
            out[n] = q
    return out


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


def collect(cat, normalise, stats, units_ext=True):
    """Parent and child family records, keyed by context.

    When ``units_ext`` (the default; ``False`` under ``--legacy``), each
    parent record also carries ``forced_neg_units`` and each child record
    ``head_only_neg_units`` -- the negated ratios of the family's surviving
    unit labels (see ``unit_labels``) that are themselves forced/head-only,
    keyed the same way as ``forced``/``head_only`` ({Fraction: [names]}).
    The designed exception (a parent's unit label being exactly its own
    input) is automatic: ``parent_forced`` already drops that entry, so a
    unit named ``x`` is never a key of ``name_to_forced`` below.
    """
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
                    forced = parent_forced(fam, stats)
                    neg_units = defaultdict(list)
                    if units_ext:
                        name_to_forced = invert_ratio_names(forced)
                        for u in unit_labels(fam, stats):
                            q = name_to_forced.get(u)
                            if q is not None:
                                neg_units[-q].append(u)
                    parents[key].append(
                        {"key": key, "pos": pos, "joint": joint,
                         "forced": forced, "forced_neg_units": dict(neg_units),
                         "fam": fam})
            if fam.get("has_head"):
                h = frac(fam.get("head_ratio"))
                if h is None or h == 0:
                    stats["skipped_child_without_head_ratio"] += 1
                else:
                    head_only = child_head_only(fam, stats, h, normalise)
                    neg_units = defaultdict(list)
                    if units_ext:
                        name_to_ho = invert_ratio_names(head_only)
                        for u in unit_labels(fam, stats):
                            q = name_to_ho.get(u)
                            if q is not None:
                                neg_units[-q].append(u)
                    children[key].append(
                        {"key": key, "pos": pos, "head": h,
                         "head_only": head_only,
                         "head_only_neg_units": dict(neg_units),
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
    ap.add_argument("--legacy", action="store_true",
                    help="disable the unit-negation extension in --menu "
                         "(restores the pre-extension gate: forced/head-only "
                         "identity collisions only)")
    ap.add_argument("--json", default=None, help="also write the report as JSON")
    ap.add_argument("--limit", type=int, default=40,
                    help="print at most N examples per list (0 = all)")
    a = ap.parse_args(argv)
    normalise = not a.raw
    units_ext = not a.legacy
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
    parents, children = collect(cat, normalise, stats, units_ext)

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
        # per context: the distinct signatures its menu can offer.  Each
        # parent signature is now a pair (forced, forced_neg_units); each
        # child signature a pair (head_only, head_only_neg_units).  Under
        # --legacy the *_neg_units tables are always empty, so this reduces
        # identically to the pre-extension signatures.
        pmenu = {k: frozenset((frozenset(p["forced"]),
                                frozenset(p.get("forced_neg_units") or {}))
                               for p in v)
                 for k, v in parents.items()}
        cmenu = {k: frozenset((frozenset(c["head_only"]),
                                frozenset(c.get("head_only_neg_units") or {}))
                               for c in v)
                 for k, v in children.items()}
        pclass, cclass = defaultdict(list), defaultdict(list)
        for k, s in pmenu.items():
            pclass[s].append(k)
        for k, s in cmenu.items():
            cclass[s].append(k)

        def passes_base(cs_set, ps_set):
            """The original test: some combo has no forced/head-only hit."""
            for cs, _ in cs_set:
                if not cs:
                    return True
                for ps, _ in ps_set:
                    if not (cs & ps):
                        return True
            return False

        def passes(cs_set, ps_set):
            """Base test, plus the unit-negation channels (i) and (ii)."""
            for cs, cs_neg in cs_set:
                for ps, ps_neg in ps_set:
                    if (cs & ps) or (ps_neg & cs) or (ps & cs_neg):
                        continue
                    return True
            return False

        n_ctx_pairs = len(cmenu) * len(pmenu)
        failing, failing_base = [], []
        n_fail = n_fail_base = 0
        for cs_set, ckeys in cclass.items():
            for ps_set, pkeys in pclass.items():
                ext_ok = passes(cs_set, ps_set)
                base_ok = passes_base(cs_set, ps_set)
                if not ext_ok:
                    n_fail += len(ckeys) * len(pkeys)
                    failing.extend((ck, pk) for ck in ckeys for pk in pkeys)
                if not base_ok:
                    n_fail_base += len(ckeys) * len(pkeys)
                    failing_base.extend((ck, pk) for ck in ckeys for pk in pkeys)
        failing.sort()
        failing_base.sort()
        failing_set, failing_base_set = set(failing), set(failing_base)
        # the base predicate only drops conditions from the extended one, so
        # blocking is monotone: whatever fails under base still fails
        # under the extension.
        assert failing_base_set <= failing_set, "extension is not monotone"
        new_failing = sorted(failing_set - failing_base_set)

        # ---- attribute each newly-failing context pair's family-pairs to
        # ---- channel (i), (ii), both, or neither (i.e. it was already
        # ---- base-blocked and the pair fails for a reason unrelated to the
        # ---- specific family combination examined here).
        new_i = new_ii = new_both = 0
        new_i_examples, new_ii_examples = [], []
        parent_ctx_hits = Counter()
        for ck, pk in new_failing:
            parent_ctx_hits[pk] += 1
            for c in children.get(ck, []):
                ho, ho_neg = c["head_only"], c.get("head_only_neg_units") or {}
                for p in parents.get(pk, []):
                    fo, fo_neg = p["forced"], p.get("forced_neg_units") or {}
                    if fo.keys() & ho.keys():
                        continue  # already base-blocked; not a new event
                    hit_i = bool(fo_neg.keys() & ho.keys())
                    hit_ii = bool(fo.keys() & ho_neg.keys())
                    if hit_i and hit_ii:
                        new_both += 1
                    elif hit_i:
                        new_i += 1
                        if len(new_i_examples) < a.limit or a.limit <= 0:
                            new_i_examples.append((ck, pk, sorted(fo_neg.keys() & ho.keys(), key=str)))
                    elif hit_ii:
                        new_ii += 1
                        if len(new_ii_examples) < a.limit or a.limit <= 0:
                            new_ii_examples.append((ck, pk, sorted(fo.keys() & ho_neg.keys(), key=str)))
        top_new_parent_contexts = parent_ctx_hits.most_common(10)

        print()
        print(f"menu gate: {n_ctx_pairs} ordered context pairs, "
              f"{n_fail} with NO passing (child family, parent family) "
              f"combination  [base predicate alone: {n_fail_base}]")
        print(f"  distinct menu signature classes: parents {len(pclass)}, "
              f"children {len(cclass)}")
        print(f"  newly-failing context pairs from the unit extension: "
              f"{len(new_failing)}")
        print(f"  new family-pair collision events: (i) only {new_i}, "
              f"(ii) only {new_ii}, both {new_both}")
        print("  top parent contexts among the newly-failing context pairs: "
              + (", ".join(f"{k}:{n}" for k, n in top_new_parent_contexts)
                 or "(none)"))
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
            tag = " [NEW]" if (ck, pk) not in failing_base_set else ""
            print(f"    child {ck:<24s} parent {pk:<24s}  "
                  f"child ratios {{{','.join(str(q) for q in cs)}}}  "
                  f"parent forced {{{','.join(str(q) for q in ps)}}}{tag}")
        if not failing:
            print("    (none)")
        elif a.limit > 0 and len(failing) > a.limit:
            print(f"    ... {len(failing) - a.limit} more (use --limit 0)")
        if new_failing:
            print("  newly-failing context pairs (not failing under the "
                  "base predicate):")
            for ck, pk in cap(new_failing):
                print(f"    child {ck:<24s} parent {pk}")
            if a.limit > 0 and len(new_failing) > a.limit:
                print(f"    ... {len(new_failing) - a.limit} more (use --limit 0)")
        menu_report = {
            "n_context_pairs": n_ctx_pairs, "n_failing": n_fail,
            "failing_pairs": [[c, p] for c, p in failing],
            "n_parent_classes": len(pclass), "n_child_classes": len(cclass),
            "children_failing_every_parent": dead_menu_c,
            "parents_failing_every_child": dead_menu_p,
            "n_failing_base": n_fail_base,
            "failing_pairs_base": [[c, p] for c, p in failing_base],
            "new_failing_pairs": [[c, p] for c, p in new_failing],
            "n_new_failing": len(new_failing),
            "new_collisions_i": new_i,
            "new_collisions_ii": new_ii,
            "new_collisions_both": new_both,
            "new_collisions_i_examples": [[c, p, [str(q) for q in rs]]
                                          for c, p, rs in new_i_examples],
            "new_collisions_ii_examples": [[c, p, [str(q) for q in rs]]
                                           for c, p, rs in new_ii_examples],
            "top_new_parent_contexts": [[k, n] for k, n in top_new_parent_contexts],
            "units_extension": units_ext,
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
