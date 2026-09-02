#!/usr/bin/env python3
"""Independent, solver-free re-verification of the free-token alphabet catalogue.

This is a *second, independent* checker for the families in
``research/antimagic/data/alphabet_families.json`` (assembled by
``scripts/assemble_alphabet_catalogue.py`` from the CP-SAT output of
``scripts/symbolic_free_token_cpsat.py``) and for raw CP-SAT batch JSONL files
before assembly.  Those two scripts are read ONLY to learn the JSON schema
(``parameters``, ``denominator``, ``labels`` with ``kind``/``role``/``row``/
``arm``/``pos``, ``coefficients_by_label``, ``row_specs``, ``mirror_pairs``,
``token_indices``, ``root_row``, ``permutation_named``); none of their
verification code is imported or reused.  The topology (rows, chains, arms,
ports, active/input children) and the output multiset are rebuilt here from
scratch, purely from ``row_specs`` and the label metadata, and every claim is
re-derived and re-checked from ``coefficients_by_label`` alone.

Topology reconstruction (per family, rows listed top to bottom)
-----------------------------------------------------------------
Row ``k`` may carry:

* an incoming head edge (row 0's exposed head ``y``, or row ``k``'s share of
  the previous row's active child), optionally extended by a head chain
  ``head=h`` giving ``x_0..x_h`` (``x_0`` is the head edge itself);
* zero or more arms, an arm of length ``ell`` giving labels ``a_0..a_ell``;
* ``ports`` stationary single-label ports;
* optionally one active child: on a non-final row this is literally the next
  row's incoming head label (one physical label; its own stationary output is
  suppressed and replaced by the next row's owner output); on the final row,
  with ``input``, its label is pinned to the parameter ``x``, otherwise (with
  just ``active``) it keeps its own stationary output.

The top row may instead be a ``root`` row: no head label, no parameter ``y``;
its owner output is not a member of the output multiset ``O`` but must
instead equal the zero coefficient form.

Owner output of row ``k`` = (last label of its head chain, or nothing for a
root row) + (first label of every arm) + (every port) + (the active child
label, if any).  ``P`` is the multiset of all physical label forms, ``O`` the
multiset of all output forms (root row owner excluded); ``|P| = |O|`` always
holds for well-formed row_specs.

Checks (exact, over ``fractions.Fraction``, coefficient vectors divided by
the recorded denominator)
-----------------------------------------------------------------
 1. multiset(O) == multiset(P) (root owner handled as above, and separately
    required to be the zero form);
 2. all physical label forms pairwise distinct and nonzero;
 3. every listed mirror pair sums to zero; the token triple (if any) sums to
    zero; every non-head physical label lies in exactly one mirror pair or in
    the token (for a root family: every label, no exception for a head);
 4. the rank of the matrix of [head (if present); token labels a,b,c (if
    any)] equals the recorded token_rank (exactly 3) or is at least 2 (rank-2
    token) -- the computed rank is always reported;
 5. the head form is nonzero on ``y`` and zero on every other parameter (for
    a non-root family); the input label (if any) equals exactly the
    parameter ``x``;
 6. numeric sanity: three random integer parameter points reproduce P == O
    (and the root-owner zero, if applicable) as exact Fraction multisets.

Usage
-----
    check_alphabet_families.py                          # data/alphabet_families.json
    check_alphabet_families.py PATH.json
    check_alphabet_families.py --jsonl PATH.jsonl        # raw CP-SAT batch file
    check_alphabet_families.py --trials 5 --seed foo ...
    check_alphabet_families.py -v ...                    # print every sub-check
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
from collections import Counter
from fractions import Fraction as Q

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CATALOGUE = os.path.normpath(os.path.join(HERE, "..", "data",
                                                   "alphabet_families.json"))

CHECK_ORDER = (
    "0_root_row_field",
    "0_zero_label_field",
    "1_output_multiset",
    "1b_root_owner_zero",
    "2_distinct_forms",
    "2_nonzero_forms",
    "2b_zero_label_is_zero",
    "3_mirror_pairs_negate",
    "3_token_indices_present",
    "3_token_zero_sum",
    "3_signature_partition",
    "4_token_rank",
    "5_head_free",
    "5_input_exact",
    "6_numeric_sanity",
)


class Malformed(Exception):
    """The family payload is missing/inconsistent so it cannot be rebuilt."""


# ------------------------------------------------------------- linear algebra

def matrix_rank(rows):
    """Exact rank of an integer/Fraction matrix via Gaussian elimination."""
    if not rows:
        return 0
    ncols = len(rows[0])
    mat = [[Q(x) for x in row] for row in rows]
    nr = len(mat)
    rank = 0
    for col in range(ncols):
        piv = None
        for r in range(rank, nr):
            if mat[r][col] != 0:
                piv = r
                break
        if piv is None:
            continue
        mat[rank], mat[piv] = mat[piv], mat[rank]
        pv = mat[rank][col]
        mat[rank] = [x / pv for x in mat[rank]]
        for r in range(nr):
            if r != rank and mat[r][col] != 0:
                f = mat[r][col]
                mat[r] = [a - f * b for a, b in zip(mat[r], mat[rank])]
        rank += 1
        if rank == nr:
            break
    return rank


# ------------------------------------------------------------------ topology

class Rebuilt:
    """Independently reconstructed topology of one family payload."""

    def __init__(self, family):
        if not isinstance(family, dict):
            raise Malformed("family is not an object")
        self.family = family
        self.parameters = family.get("parameters")
        self.labels = family.get("labels")
        self.cbl = family.get("coefficients_by_label")
        self.row_specs = family.get("row_specs")
        self._denominator_raw = family.get("denominator")
        self._validate_basic()
        self.d = len(self.parameters)

        # -- label index --------------------------------------------------
        self.by_index = {}
        for pos, lb in enumerate(self.labels):
            if not isinstance(lb, dict) or not lb.get("name"):
                raise Malformed("labels[] entry without a name")
            idx = lb.get("index")
            idx = idx if isinstance(idx, int) else pos
            if idx in self.by_index:
                raise Malformed(f"duplicate label index {idx}")
            self.by_index[idx] = lb
        self.w = len(self.by_index)
        if sorted(self.by_index) != list(range(self.w)):
            raise Malformed("label indices are not a dense 0..w-1 range")

        self.vec = {}
        for idx, lb in self.by_index.items():
            name = lb["name"]
            raw = self.cbl.get(name)
            if not isinstance(raw, list) or len(raw) != self.d:
                raise Malformed(f"coefficient vector for label {name!r}")
            try:
                self.vec[idx] = [int(c) for c in raw]
            except (TypeError, ValueError):
                raise Malformed(f"non-integer coefficient for label {name!r}")

        # -- root-ness ------------------------------------------------------
        self.nrows = len(self.row_specs)
        if self.nrows == 0:
            raise Malformed("row_specs is empty")
        self.is_root = bool(self.row_specs[0].get("root", False))
        root_field = self.family.get("root_row")
        self.root_field_present = root_field is not None
        self.root_field_consistent = (
            not self.root_field_present or bool(root_field) == self.is_root)

        # -- generalized root condition: P' = P + {0} ------------------------
        # A root macro may carry an explicit "zero" kind label (name "0",
        # all-zero coefficient vector): a bookkeeping physical label that is
        # not placed by any row/arm/port/chain, is exempt from the
        # nonzero/distinct checks and from the mirror/token signature, and
        # balances the root owner output now being an ORDINARY output (P' =
        # P + {0}, O -> P' a plain bijection).  Older payloads (and any
        # family with ``root_zero_output`` true) keep the original pinned
        # scheme: the root owner output is excluded from O and required to
        # equal the zero form outright, with no zero label needed.
        zero_candidates = [idx for idx, lb in self.by_index.items()
                           if lb.get("kind") == "zero"]
        if len(zero_candidates) > 1:
            raise Malformed(f"more than one 'zero' kind label: {zero_candidates}")
        self.zero_idx = zero_candidates[0] if zero_candidates else None
        zero_field = self.family.get("zero_label_index")
        self.zero_field_present = zero_field is not None
        self.zero_field_consistent = (
            not self.zero_field_present or zero_field == self.zero_idx)
        self.root_zero_output = bool(self.family.get("root_zero_output"))
        # old pinned reconstruction (owner excluded from O) iff root and no
        # zero label exists to balance the count; root_zero_output alone
        # does NOT change the reconstruction (the reference topology is
        # built identically either way -- the flag only adds an extra
        # solver constraint / extra check that the owner equals zero).
        self.exclude_root_owner = self.is_root and self.zero_idx is None
        self.require_root_owner_zero = self.is_root and (
            self.exclude_root_owner or self.root_zero_output)

        self._validate_row_specs()
        self._index_labels()
        self._build_rows()

    # -- basic field validation --------------------------------------------
    def _validate_basic(self):
        if not isinstance(self.parameters, list) or not self.parameters:
            raise Malformed("parameters")
        if not isinstance(self.labels, list) or not self.labels:
            raise Malformed("labels")
        if not isinstance(self.cbl, dict) or not self.cbl:
            raise Malformed("coefficients_by_label")
        if not isinstance(self.row_specs, list) or not self.row_specs:
            raise Malformed("row_specs")
        try:
            L = int(self._denominator_raw)
        except (TypeError, ValueError):
            raise Malformed("denominator")
        if L < 1:
            raise Malformed("denominator < 1")
        self.denominator = L

    def _validate_row_specs(self):
        for k, row in enumerate(self.row_specs):
            if not isinstance(row, dict):
                raise Malformed(f"row_specs[{k}] is not an object")
            if row.get("root") and k != 0:
                raise Malformed(f"row_specs[{k}]: only row 0 may be root")
            if row.get("root") and (row.get("head", 0) or 0):
                raise Malformed("root row cannot carry a head chain")
            nact = int(row.get("active") or 0)
            ninp = int(row.get("input") or 0)
            if not 0 <= nact <= 2 or not 0 <= ninp <= 2:
                raise Malformed(f"row_specs[{k}]: active/input must be 0, 1 or 2")
            if ninp > nact:
                raise Malformed(f"row_specs[{k}]: input count exceeds active count")
            last = k == self.nrows - 1
            if not last and nact != 1:
                raise Malformed(
                    f"row_specs[{k}]: non-final row must have exactly one "
                    "active child (the next row's head)")
            if ninp and not last:
                raise Malformed(f"row_specs[{k}]: only the final row may be input")

    # -- label bucketing by row/arm/pos ------------------------------------
    def _index_labels(self):
        self.head_of_row = {}
        self.head_chain_of_row = {k: [] for k in range(self.nrows)}
        self.arms_of_row = {k: {} for k in range(self.nrows)}
        self.ports_of_row = {k: [] for k in range(self.nrows)}
        self.child_label_of_row = {}

        for idx, lb in self.by_index.items():
            kind = lb.get("kind")
            row = lb.get("row")
            if kind == "head" and lb.get("pos") == 0:
                if row in self.head_of_row:
                    raise Malformed(f"row {row} has more than one head label")
                self.head_of_row[row] = idx
            elif kind == "head_chain":
                self.head_chain_of_row.setdefault(row, []).append(idx)
            elif kind == "arm":
                self.arms_of_row.setdefault(row, {}).setdefault(
                    lb.get("arm"), []).append(idx)
            elif kind == "port":
                self.ports_of_row.setdefault(row, []).append(idx)
            elif kind in ("input", "active"):
                # up to 2 on the final row (active=2/input=2); collected as a
                # list and sorted below by label index, which -- since these
                # are created in rank order a=0,1,... by the reference
                # builder -- recovers the same 0,1 rank order (input-kind
                # labels first, any non-input active labels after).
                self.child_label_of_row.setdefault(row, []).append(idx)

        for k in range(self.nrows):
            self.head_chain_of_row[k].sort(key=lambda i: self.by_index[i].get("pos"))
            self.ports_of_row[k].sort(key=lambda i: self.by_index[i].get("pos"))
            self.child_label_of_row.setdefault(k, []).sort()
            for a in self.arms_of_row[k]:
                self.arms_of_row[k][a].sort(key=lambda i: self.by_index[i].get("pos"))

    # -- row/topology reconstruction ---------------------------------------
    def _build_rows(self):
        self.row_data = []
        for k in range(self.nrows):
            row = self.row_specs[k]
            last = k == self.nrows - 1
            is_root_row = k == 0 and self.is_root

            if is_root_row:
                head_idx = None
            else:
                if k not in self.head_of_row:
                    raise Malformed(f"row {k}: expected head label not found")
                head_idx = self.head_of_row[k]
            chain = ([] if head_idx is None else [head_idx]) \
                + list(self.head_chain_of_row.get(k, []))
            expect_head_len = row.get("head", 0) or 0
            if len(self.head_chain_of_row.get(k, [])) != expect_head_len:
                raise Malformed(f"row {k}: head chain length mismatch")

            arm_lens = row.get("arms") or []
            arms = []
            grouped = self.arms_of_row.get(k, {})
            if sorted(grouped.keys()) != list(range(len(arm_lens))):
                raise Malformed(f"row {k}: arm indices mismatch "
                                 f"(got {sorted(grouped.keys())}, "
                                 f"want {list(range(len(arm_lens)))})")
            for a, ell in enumerate(arm_lens):
                labs = grouped[a]
                if len(labs) != ell + 1:
                    raise Malformed(f"row {k}: arm {a} length mismatch")
                arms.append(labs)

            ports = self.ports_of_row.get(k, [])
            if len(ports) != (row.get("ports", 0) or 0):
                raise Malformed(f"row {k}: port count mismatch")

            # children: on a non-final row this is exactly one label of kind
            # "head" (the next row's head -- one shared physical edge, no
            # output of its own here).  On the final row it is 0, 1 or 2
            # labels: the first `ninp` are kind "input" (each pinned to its
            # own parameter, "x" alone or "x1","x2"), the rest ("active" =
            # count beyond input) are kind "active" (stationary).  EVERY
            # final-row child is "kept": it gets its own separate output AND
            # is summed into the owner output (both, for the double case).
            nact = int(row.get("active") or 0)
            ninp = int(row.get("input") or 0)
            found = self.child_label_of_row.get(k, [])
            if not last:
                # the non-final row's single active child is the NEXT row's
                # head (kind "head", registered under head_of_row[k+1] by
                # the label-bucketing pass, not under child_label_of_row --
                # "active"/"input" kind labels only ever occur on the final
                # row).  child_label_of_row[k] must be empty here.
                if found:
                    raise Malformed(
                        f"row {k}: unexpected input/active-kind label(s) on "
                        f"a non-final row: {found}")
                if nact != 1:
                    raise Malformed(
                        f"row {k}: non-final row must have active=1, got {nact}")
                if (k + 1) not in self.head_of_row:
                    raise Malformed(
                        f"row {k}: active child (next row's head) not found")
                children = [self.head_of_row[k + 1]]
                kept = []
            else:
                if len(found) != nact:
                    raise Malformed(
                        f"row {k}: expected {nact} active/input child "
                        f"label(s), found {len(found)}")
                for a, cidx in enumerate(found):
                    expect_kind = "input" if a < ninp else "active"
                    got_kind = self.by_index[cidx].get("kind")
                    if got_kind != expect_kind:
                        raise Malformed(
                            f"row {k}: child {a} has kind {got_kind!r}, "
                            f"expected {expect_kind!r}")
                children = list(found)
                kept = list(found)

            self.row_data.append(dict(chain=chain, arms=arms, ports=ports,
                                      children=children, kept=kept,
                                      is_root=is_root_row))

        used = set()
        for rd in self.row_data:
            used.update(rd["chain"])
            for arm in rd["arms"]:
                used.update(arm)
            used.update(rd["ports"])
            used.update(rd["children"])
        # the zero label (if any) is a bookkeeping atom, not placed by any
        # row/arm/port/chain -- exempt it from the completeness requirement.
        expected = set(self.by_index)
        if self.zero_idx is not None:
            expected.discard(self.zero_idx)
        if used != expected:
            missing = sorted(expected - used)
            extra = sorted(used - expected)
            raise Malformed(
                f"labels not placed in any row structure: {missing}"
                + (f"; unexpectedly placed: {extra}" if extra else ""))

    # -- derived vectors -----------------------------------------------
    def raw(self, idx):
        return self.vec[idx]

    def add(self, idxs):
        out = [0] * self.d
        for i in idxs:
            v = self.vec[i]
            out = [out[j] + v[j] for j in range(self.d)]
        return out

    def form(self, rawvec):
        L = self.denominator
        return tuple(Q(c, L) for c in rawvec)

    def outputs(self):
        """Return (O, root_owner_vec_or_None) as raw integer coefficient vectors.

        The root owner output is an ORDINARY member of O (matched against
        P' = P + {zero label}) unless ``self.exclude_root_owner`` -- the old
        pinned scheme used when no zero label balances the count (root and
        no zero label at all).  Either way ``root_owner`` is returned so
        callers can check it against the zero form when required.
        """
        O = []
        root_owner = None
        for rd in self.row_data:
            chain = rd["chain"]
            for i in range(len(chain) - 1):
                O.append(self.add([chain[i], chain[i + 1]]))
            # every child (1 shared edge on a non-final row, or 0-2 kept
            # input/active children on the final row) is summed into the
            # owner output.
            owner_terms = ([chain[-1]] if chain else []) \
                + [arm[0] for arm in rd["arms"]] + list(rd["ports"]) \
                + list(rd["children"])
            owner_vec = self.add(owner_terms)
            if rd["is_root"]:
                root_owner = owner_vec
                if not self.exclude_root_owner:
                    O.append(owner_vec)
            else:
                O.append(owner_vec)
            for arm in rd["arms"]:
                for i in range(len(arm) - 1):
                    O.append(self.add([arm[i], arm[i + 1]]))
                O.append(self.add([arm[-1]]))
            for p in rd["ports"]:
                O.append(self.add([p]))
            # each kept child (final-row input/active labels only) gets its
            # own separate stationary output.
            for c in rd["kept"]:
                O.append(self.add([c]))
        return O, root_owner

    def head_index(self):
        return None if self.is_root else self.head_of_row.get(0)

    def input_indices(self):
        """All 'input' kind label indices, in rank order (0, then 1).

        Rank order coincides with ascending label index: the reference
        builder creates input-kind labels for a=0..ninp-1 strictly before
        any non-input active labels (a=ninp..nact-1), in that order, so
        their label indices are already strictly increasing in rank order.
        """
        return sorted(idx for idx, lb in self.by_index.items()
                      if lb.get("kind") == "input")


# --------------------------------------------------------------------- checks

def run_checks(rebuilt, trials, rng):
    d = rebuilt.d
    L = rebuilt.denominator
    w = rebuilt.w
    params = rebuilt.parameters
    fam = rebuilt.family
    checks = {}

    if rebuilt.root_field_present and not rebuilt.root_field_consistent:
        checks["0_root_row_field"] = (False,
            f"family['root_row']={fam.get('root_row')!r} disagrees with "
            f"row_specs[0]['root']={rebuilt.is_root}")

    if rebuilt.zero_field_present and not rebuilt.zero_field_consistent:
        checks["0_zero_label_field"] = (False,
            f"family['zero_label_index']={fam.get('zero_label_index')!r} "
            f"disagrees with the independently found zero-kind label "
            f"index={rebuilt.zero_idx!r}")

    # ---- check 1: P' = O multiset ----------------------------------------
    # P' = P (all labels, incl. the zero label if present) since the zero
    # label is just an ordinary entry in "labels"/"coefficients_by_label".
    # O includes the root owner output as an ordinary output unless
    # exclude_root_owner (old pinned scheme, no zero label to balance it).
    O, root_owner = rebuilt.outputs()
    P_forms = sorted(rebuilt.form(rebuilt.raw(i)) for i in range(w))
    O_forms = sorted(rebuilt.form(v) for v in O)
    len_ok = len(O) == w
    multiset_ok = len_ok and P_forms == O_forms
    if multiset_ok:
        detail = ""
    else:
        cp, co = Counter(P_forms), Counter(O_forms)
        only_p = list((cp - co).elements())
        only_o = list((co - cp).elements())
        detail = (f"|O|={len(O)} (want {w}); forms only in P: {only_p[:5]}"
                  f"{'...' if len(only_p) > 5 else ''}; "
                  f"only in O: {only_o[:5]}{'...' if len(only_o) > 5 else ''}")
    checks["1_output_multiset"] = (multiset_ok, detail)

    if rebuilt.require_root_owner_zero:
        zero_ok = all(c == 0 for c in root_owner)
        reason = ("no zero label present (old pinned scheme)"
                  if rebuilt.exclude_root_owner else "root_zero_output=true")
        checks["1b_root_owner_zero"] = (
            zero_ok, "" if zero_ok else f"root owner output = {root_owner} ({reason})")

    # ---- check 2: distinct & nonzero physical forms -----------------------
    # (the zero label, if present, is exempt: it is the unique label allowed
    # to be the all-zero form, and is not required to be distinct from it)
    real_indices = [i for i in range(w) if i != rebuilt.zero_idx]
    forms_list = [rebuilt.form(rebuilt.raw(i)) for i in real_indices]
    distinct_ok = len(set(forms_list)) == len(real_indices)
    nonzero_ok = all(any(x != 0 for x in f) for f in forms_list)
    checks["2_distinct_forms"] = (distinct_ok,
        "" if distinct_ok else "duplicate label forms present (excl. the zero label)")
    checks["2_nonzero_forms"] = (nonzero_ok,
        "" if nonzero_ok else "a real physical label has the zero form")

    if rebuilt.zero_idx is not None:
        zvec = rebuilt.raw(rebuilt.zero_idx)
        zform_ok = all(c == 0 for c in zvec)
        checks["2b_zero_label_is_zero"] = (
            zform_ok, "" if zform_ok else f"zero label's own vector = {zvec}")

    # ---- check 3: mirror pairs / token / signature partition -------------
    mirror_pairs = fam.get("mirror_pairs") or []
    mp_ok = True
    mp_detail = []
    for pair in mirror_pairs:
        if not (isinstance(pair, (list, tuple)) and len(pair) == 2):
            mp_ok = False
            mp_detail.append(f"malformed pair {pair!r}")
            continue
        i, j = pair
        if i not in rebuilt.by_index or j not in rebuilt.by_index:
            mp_ok = False
            mp_detail.append(f"pair references unknown index {pair!r}")
            continue
        s = [rebuilt.vec[i][c] + rebuilt.vec[j][c] for c in range(d)]
        if any(s):
            mp_ok = False
            mp_detail.append(f"{pair} not negatives (sum={s})")
    checks["3_mirror_pairs_negate"] = (mp_ok, "; ".join(mp_detail))

    token_indices = fam.get("token_indices")
    has_token = bool(fam.get("token")) and isinstance(token_indices, dict)
    if fam.get("token") and not isinstance(token_indices, dict):
        checks["3_token_indices_present"] = (
            False, "token=True but token_indices missing/malformed")

    tok_idx_list = []
    if has_token:
        token_ok = True
        token_detail = ""
        try:
            tok_idx_list = [token_indices[r] for r in ("a", "b", "c")]
        except KeyError:
            token_ok = False
            token_detail = "token_indices missing role a/b/c"
        else:
            if any(t not in rebuilt.by_index for t in tok_idx_list):
                token_ok = False
                token_detail = "token_indices reference unknown index"
            else:
                s = [sum(rebuilt.vec[t][c] for t in tok_idx_list) for c in range(d)]
                if any(s):
                    token_ok = False
                    token_detail = f"token triple does not sum to zero (sum={s})"
        checks["3_token_zero_sum"] = (token_ok, token_detail)

    head_idx = rebuilt.head_index()
    all_idx = set(range(w))
    # everything must be mirror/token-covered except the exposed head
    # (non-root) and the zero label (root, when present) -- matches
    # Topology.signature_indices() in the reference solver exactly.
    sig_set = all_idx if rebuilt.is_root else (all_idx - {head_idx})
    if rebuilt.zero_idx is not None:
        sig_set = sig_set - {rebuilt.zero_idx}
    covered = {i: 0 for i in all_idx}
    for pair in mirror_pairs:
        if isinstance(pair, (list, tuple)) and len(pair) == 2:
            i, j = pair
            if i in covered:
                covered[i] += 1
            if j in covered:
                covered[j] += 1
    for t in tok_idx_list:
        if t in covered:
            covered[t] += 1
    # optional second token (signature mirrors + token1 + token2), recorded
    # by the solver as ``two_tokens`` / ``token2_indices``
    tok2_idx_list = []
    if fam.get("two_tokens"):
        t2 = fam.get("token2_indices")
        t2_ok, t2_detail = True, ""
        if not isinstance(t2, dict):
            t2_ok, t2_detail = False, "two_tokens=True but token2_indices missing"
        else:
            try:
                tok2_idx_list = [t2[r] for r in ("a", "b", "c")]
            except KeyError:
                t2_ok, t2_detail = False, "token2_indices missing role a/b/c"
            else:
                if any(t not in rebuilt.by_index for t in tok2_idx_list):
                    t2_ok, t2_detail = False, "token2_indices reference unknown index"
                else:
                    s2 = [sum(rebuilt.vec[t][c] for t in tok2_idx_list) for c in range(d)]
                    if any(s2):
                        t2_ok, t2_detail = False, f"token2 triple does not sum to zero (sum={s2})"
                    elif set(tok2_idx_list) & set(tok_idx_list):
                        t2_ok, t2_detail = False, "token2 shares a label with token1"
                    else:
                        a2, b2 = rebuilt.vec[tok2_idx_list[0]], rebuilt.vec[tok2_idx_list[1]]
                        spans = any(a2[i] * b2[j] - a2[j] * b2[i] != 0
                                    for i in range(d) for j in range(i + 1, d))
                        if not spans:
                            t2_ok, t2_detail = False, "token2 does not span a plane"
        checks["3_token2_zero_sum_and_plane"] = (t2_ok, t2_detail)
        for t in tok2_idx_list:
            if t in covered:
                covered[t] += 1
    part_ok = all(covered[i] == 1 for i in sig_set) and \
        all(covered[i] == 0 for i in all_idx - sig_set)
    bad = {i: covered[i] for i in all_idx if
           (i in sig_set and covered[i] != 1) or (i not in sig_set and covered[i] != 0)}
    checks["3_signature_partition"] = (
        part_ok, "" if part_ok else f"coverage counts off for indices {bad}")

    # ---- check 4: token rank ----------------------------------------------
    # The token constraints force A[it1] = L always, and for rank 3 also
    # A[it2] = 0, B[it1] = 0, B[it2] = L: that forced (it1, it2) sub-block
    # alone makes rank{A, B} == 2 EXACTLY -- 2 vectors can't exceed rank 2,
    # and the forced sub-block already reaches 2 -- independent of whether a
    # head exists.  A head, when present, is provably independent of
    # span{A, B} (it is pure-y, while A is forced nonzero on it1, a
    # coordinate the head is zero on), so it always adds exactly one more
    # dimension.  Hence the *deterministic* rank of [head?; A; B; C] is 3
    # with a head, 2 without one (a root row).
    #
    # For rank 2, only A[it1] = L is forced; B is otherwise free, so
    # rank{A, B} is only guaranteed to be >= 1 (from A alone) -- it can
    # genuinely come out as 1 if the solver happened to pick B parallel to
    # A, which does happen in real root families (verified by hand: e.g.
    # root_3-4_p0_bot's token triple is exactly (1,0), -3*(1,0), 2*(1,0)).
    # A head still forces the same +1 independent dimension, giving a
    # deterministic floor of 2 with a head, but only the trivial floor of 1
    # without one (root).
    rank_rows = []
    if head_idx is not None:
        rank_rows.append(rebuilt.vec[head_idx])
    for t in tok_idx_list:
        rank_rows.append(rebuilt.vec[t])
    computed_rank = matrix_rank(rank_rows)
    token_rank_recorded = fam.get("token_rank")
    has_head_row = head_idx is not None
    root_note = "" if has_head_row else " (root: no head row)"
    if token_rank_recorded == 3:
        expect = 3 if has_head_row else 2
        rank_ok = computed_rank == expect
        rank_detail = f"computed rank {computed_rank}, want exactly {expect}{root_note}"
    elif token_rank_recorded == 2:
        expect = 2 if has_head_row else 1
        rank_ok = computed_rank >= expect
        rank_detail = f"computed rank {computed_rank}, want >= {expect}{root_note}"
    else:
        rank_ok = True
        rank_detail = (f"computed rank {computed_rank} "
                        f"(no strict requirement, token_rank={token_rank_recorded!r})")
    checks["4_token_rank"] = (rank_ok, rank_detail)

    # ---- check 5: head free / input exact ---------------------------------
    if not rebuilt.is_root:
        if "y" not in params:
            checks["5_head_free"] = (False, "parameter 'y' absent for a non-root family")
        else:
            iy = params.index("y")
            v = rebuilt.vec[head_idx]
            free_ok = v[iy] != 0 and all(v[c] == 0 for c in range(d) if c != iy)
            if fam.get("free_head") and not free_ok:
                # rigid-head family (solver option --free-head): the head is a
                # nonzero form in the inputs, e.g. -(x1+x2); E5 is waived by
                # design and the head is handled like the residue-two ray
                ins = [c for c, nm in enumerate(params) if nm.startswith("x")]
                rigid_ok = any(v) and all(v[c] == 0 for c in range(d) if c not in ins)
                checks["5_head_free"] = (
                    rigid_ok, f"rigid head {v} (free_head mode; must depend on inputs only)"
                    if rigid_ok else f"rigid head {v} depends on non-input parameters")
            else:
                checks["5_head_free"] = (
                    free_ok, "" if free_ok else f"head vector {v} not pure-y (index {iy})")

    input_idxs = rebuilt.input_indices()
    if input_idxs:
        # single-input rows keep parameter name "x"; a double-input row
        # (active=2;input=2) uses "x1", "x2" -- one parameter per input
        # label, in the same rank order as the labels themselves.
        pnames = ["x"] if len(input_idxs) == 1 else \
            [f"x{r + 1}" for r in range(len(input_idxs))]
        in_ok = True
        in_detail = []
        for rank, (idx, pname) in enumerate(zip(input_idxs, pnames)):
            if pname not in params:
                in_ok = False
                in_detail.append(f"parameter {pname!r} absent (input[{rank}])")
                continue
            ip = params.index(pname)
            expect = [L if c == ip else 0 for c in range(d)]
            v = rebuilt.vec[idx]
            if v != expect:
                in_ok = False
                in_detail.append(f"input[{rank}] ({pname}) vector {v} != {expect}")
        checks["5_input_exact"] = (in_ok, "; ".join(in_detail))

    # ---- check 6: numeric sanity -------------------------------------------
    trial_reports = []
    numeric_ok = True
    for _ in range(trials):
        point = [rng.randrange(-97, 98) for _ in range(d)]
        pv = sorted(Q(sum(rebuilt.vec[i][c] * point[c] for c in range(d)), L)
                    for i in range(w))
        ov = sorted(Q(sum(vec[c] * point[c] for c in range(d)), L) for vec in O)
        ok = pv == ov
        entry = {"point": dict(zip(params, point)), "P_eq_O": ok}
        if rebuilt.require_root_owner_zero:
            rz = Q(sum(root_owner[c] * point[c] for c in range(d)), L)
            entry["root_zero"] = (rz == 0)
            ok = ok and entry["root_zero"]
        entry["ok"] = ok
        numeric_ok = numeric_ok and ok
        trial_reports.append(entry)
    checks["6_numeric_sanity"] = (numeric_ok, "" if numeric_ok else "; ".join(
        f"point={t['point']} ok={t['ok']}" for t in trial_reports if not t["ok"]))

    return checks, trial_reports


# ------------------------------------------------------------------- loaders

def load_catalogue(path):
    """Load the assembled catalogue: {key -> {..., "family": {...}}}."""
    with open(path) as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise Malformed(f"{path}: top level is not an object")
    items = []
    for key in sorted(data):
        entry = data[key]
        kind = None
        if isinstance(entry, dict):
            kind = entry.get("kind") or (entry.get("ctx") or {}).get("kind")
        if not isinstance(entry, dict) or not isinstance(entry.get("family"), dict):
            items.append(dict(label=key, fam=None, kind=kind,
                              skip="entry missing a 'family' object"))
            continue
        items.append(dict(label=key, fam=entry["family"], kind=kind, skip=None))
    return items


def load_jsonl(path):
    """Load a raw CP-SAT batch file: one {key, ctx, found, attempts, family} per line."""
    items = []
    with open(path) as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError as exc:
                items.append(dict(label=f"line{lineno}", fam=None, kind=None,
                                  skip=f"unparsable JSON line: {exc}"))
                continue
            if not isinstance(rec, dict):
                items.append(dict(label=f"line{lineno}", fam=None, kind=None,
                                  skip="record is not an object"))
                continue
            key = rec.get("key") or f"line{lineno}"
            label = f"{key} [line {lineno}]"
            kind = (rec.get("ctx") or {}).get("kind")
            if not rec.get("found"):
                items.append(dict(label=label, fam=None, kind=kind,
                                  skip="found=false"))
                continue
            fam = rec.get("family")
            if not isinstance(fam, dict):
                items.append(dict(label=label, fam=None, kind=kind,
                                  skip="found=true but 'family' missing/malformed"))
                continue
            items.append(dict(label=label, fam=fam, kind=kind, skip=None))
    return items


# --------------------------------------------------------------------- driver

def process(items, trials, seed):
    results = []
    n_pass = n_fail = n_skip = 0
    for it in items:
        label, fam, skip = it["label"], it["fam"], it["skip"]
        if skip is not None:
            n_skip += 1
            results.append(dict(label=label, status="SKIP", detail=skip,
                                checks={}, kind=it.get("kind")))
            continue
        rng = random.Random(f"{seed}:{label}")
        try:
            rebuilt = Rebuilt(fam)
            checks, trial_reports = run_checks(rebuilt, trials, rng)
        except Malformed as exc:
            n_fail += 1
            results.append(dict(label=label, status="FAIL",
                                detail=f"topology_reconstruction: {exc}",
                                checks={}, kind=it.get("kind")))
            continue
        except Exception as exc:  # pragma: no cover - defensive
            n_fail += 1
            results.append(dict(
                label=label, status="FAIL",
                detail=f"internal_error: {type(exc).__name__}: {exc}",
                checks={}, kind=it.get("kind")))
            continue
        failing = [name for name in CHECK_ORDER
                   if name in checks and not checks[name][0]]
        if failing:
            n_fail += 1
            detail = "; ".join(f"{name}[{checks[name][1]}]" for name in failing)
            results.append(dict(label=label, status="FAIL", detail=detail,
                                checks=checks, kind=it.get("kind")))
        else:
            n_pass += 1
            results.append(dict(label=label, status="PASS", detail="",
                                checks=checks, kind=it.get("kind")))
    return results, n_pass, n_fail, n_skip


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Independent, solver-free re-verification of alphabet_families.json "
                    "(or a raw CP-SAT batch JSONL file with --jsonl).")
    ap.add_argument("path", nargs="?", default=DEFAULT_CATALOGUE,
                    help=f"catalogue JSON (default: {DEFAULT_CATALOGUE}); with "
                         "--jsonl, a batch JSONL file instead")
    ap.add_argument("--jsonl", action="store_true",
                    help="treat PATH as a raw CP-SAT batch JSONL file (one "
                         "key/ctx/found/attempts/family record per line) instead "
                         "of the assembled catalogue JSON")
    ap.add_argument("--trials", type=int, default=3,
                    help="random integer parameter points for check 6 (default 3)")
    ap.add_argument("--seed", default="alphabet-check",
                    help="seed for the (reproducible) numeric trials")
    ap.add_argument("-v", "--verbose", action="store_true",
                    help="print every sub-check's result for every family, not "
                         "just the failing ones")
    args = ap.parse_args(argv)

    if not os.path.exists(args.path):
        print(f"error: {args.path} does not exist", file=sys.stderr)
        return 2

    if args.jsonl:
        items = load_jsonl(args.path)
    else:
        items = load_catalogue(args.path)

    print(f"== {args.path} =={' [jsonl batch]' if args.jsonl else ' [catalogue]'}")
    print(f"{len(items)} record(s)\n")

    results, n_pass, n_fail, n_skip = process(items, args.trials, args.seed)

    for r in results:
        tag = f"  [{r['kind']}]" if r.get("kind") else ""
        if r["status"] == "PASS":
            print(f"PASS  {r['label']}{tag}")
        elif r["status"] == "SKIP":
            print(f"SKIP  {r['label']}{tag}  ({r['detail']})")
        else:
            print(f"FAIL  {r['label']}{tag}")
            print(f"      {r['detail']}")
        if args.verbose and r["checks"]:
            for name in CHECK_ORDER:
                if name in r["checks"]:
                    ok, detail = r["checks"][name]
                    mark = "ok" if ok else "FAIL"
                    suffix = f"  -- {detail}" if detail else ""
                    print(f"        {name:<26s} {mark}{suffix}")

    print()
    print(f"summary: {len(items)} total, {n_pass} PASS, {n_fail} FAIL, {n_skip} SKIP")
    if n_fail:
        print("failing: " + ", ".join(r["label"] for r in results if r["status"] == "FAIL"))
    if n_skip:
        print("skipped: " + ", ".join(r["label"] for r in results if r["status"] == "SKIP"))
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
