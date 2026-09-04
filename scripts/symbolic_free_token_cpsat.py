#!/usr/bin/env python3
"""Symbolic CP-SAT search for free-token ``P=O`` families.

Implements ``research/antimagic/SPEC_symbolic_free_token_cpsat.md``.

A macro is a rooted list of owner rows.  Row ``k`` carries

* one head edge ``g_k`` (its parent edge; ``g_0`` is the exposed head ``y``),
  optionally extended to a *head chain* ``x_0..x_h`` (``head=h``): ``x_0`` is
  the head edge itself, the chain contributes the outputs ``x_0+x_1, ...,
  x_{h-1}+x_h`` and the owner output uses ``x_h`` in place of ``g_k``,
* arms of lengths ``ell`` (labels ``x_0..x_ell``, outputs ``x_0+x_1, ...,
  x_{ell-1}+x_ell`` and the terminal ``x_ell``),
* ``r_k`` stationary ports (label ``p``, output ``p``),
* optionally *active child* edges.  For a non-final row there is exactly one
  and it is the head ``g_{k+1}`` of the next row: one physical label whose
  stationary output is replaced by the next row's owner output.  On the final
  row every active child keeps its own stationary output; with the ``input``
  flag its label is pinned to the parameter ``x`` (the project's route
  macros).  The final row may carry two of them, written ``active2;input2``
  (equivalently ``active=2;input=2``): two shared edges pinned to the
  parameters ``x1`` and ``x2``, each appearing once in ``P``, each with its own
  stationary output in ``O``, and both entering the owner output.

Owner output of row ``k`` = (end of the head chain) + sum of the first label
of every arm + sum of the ports + the active child label.  ``P`` is the
multiset of all physical labels (a shared edge counted once), ``O`` the
multiset of all outputs; ``|P| = |O|`` always.

The top row may instead be a *root* row (flag ``root``, incompatible with
``head=``).  A root row has no head label and no parameter ``y``.  Instead the
physical side gains the *zero label*: ``P' = P + {0}``, a label whose
coefficient vector is identically zero, exempt from the nonzero and
distinctness checks and from the mirror/token signature.  ``O`` contains every
output including the root owner output, and the search asks for a bijection
``O -> P'``, so the zero may be matched to any output -- the root owner output,
an arm adjacent sum, and so on.  ``--root-zero-output`` restores the stricter
variant in which the zero must be the root owner output itself.  Every real
root label takes part in the mirror/token signature.

Every physical label ``L`` is an integer coefficient vector ``c(L)`` over the
parameters ``(y, [x], t1, [t2], u_1..u_m)``; the true label is
``c(L) . params / denominator``.  The search asks for

1. ``P = O`` identically in the parameters (a permutation of the coefficient
   vectors, reified coordinatewise),
2. the support signature ``head + mirror pairs + one free token`` (or
   ``head + mirror`` under ``--no-token``),
3. genericity: all coefficient vectors pairwise distinct and nonzero.

Two optional structural filters narrow the menu: ``--no-head-only`` forbids
any label other than the exposed head from being a pure multiple of ``y`` (so
the macro can never identity-collide with a parent's forced multiples of the
shared head), and ``--forced-only-antipode`` allows ``+-x`` as the only labels
supported on the input parameter ``x`` alone.

At ``--token-rank 3`` (default) the token is three labels ``a, b, c`` with
``c(a)`` carrying the unit of ``t1``, ``c(b)`` the unit of ``t2`` and
``c(c) = -c(a) - c(b)``: the triple has two free coordinates.  At
``--token-rank 2`` the parameter ``t2`` is dropped, ``c(a)`` carries the unit
of ``t1`` and ``b, c`` are arbitrary subject to ``a + b + c = 0``: one free
coordinate once the head is fixed.  At ``--token-rank any2`` there are no
dedicated token parameters at all: the triple only has to satisfy
``a + b + c = 0`` and to span two dimensions over the existing parameters
``(y, x, u_i)``, which is enforced by requiring some 2x2 minor
``a_i b_j - a_j b_i`` to be nonzero.

Example invocations::

    symbolic_free_token_cpsat.py --rows "arms=4;ports=2" --denominator 2 \
        --coef-bound 2
    symbolic_free_token_cpsat.py --rows "arms=2,2,2"
    symbolic_free_token_cpsat.py --rows "head=2;arms=4;ports=1"
    symbolic_free_token_cpsat.py --rows "arms=4;active" --rows "arms=2,2,2"
    symbolic_free_token_cpsat.py --rows "arms=4;active;input" --no-token \
        --denominator 2
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from fractions import Fraction as Q
from math import gcd

from ortools.sat.python import cp_model


# --------------------------------------------------------------------- rows

def parse_row(spec: str) -> dict:
    """Parse one ``--rows`` argument, e.g. ``"head=2;arms=2,2;ports=1;active"``."""
    row = {"head": 0, "arms": [], "ports": 0, "active": 0, "input": 0,
           "root": False}
    for part in spec.split(";"):
        part = part.strip()
        if not part:
            continue
        if "=" in part:
            key, val = part.split("=", 1)
            key, val = key.strip().lower(), val.strip()
            if key == "arms":
                row["arms"] = [int(t) for t in val.split(",") if t.strip()]
            elif key == "ports":
                row["ports"] = int(val)
            elif key == "head":
                row["head"] = int(val)
            elif key in ("active", "input"):
                row[key] = int(val)
            else:
                raise ValueError(f"unknown row key {key!r} in {spec!r}")
        else:
            flag = part.strip().lower()
            if flag == "root":
                row["root"] = True
            elif flag in ("active", "input"):
                row[flag] = max(row[flag], 1)
            elif flag in ("active2", "input2"):
                row[flag[:-1]] = 2
            else:
                raise ValueError(f"unknown row flag {flag!r} in {spec!r}")
    if any(e < 0 for e in row["arms"]):
        raise ValueError(f"arm lengths must be >= 0 in {spec!r}")
    if row["ports"] < 0:
        raise ValueError(f"ports must be >= 0 in {spec!r}")
    if row["head"] < 0:
        raise ValueError(f"head chain length must be >= 0 in {spec!r}")
    if row["root"] and row["head"]:
        raise ValueError(f"a root row cannot carry a head chain: {spec!r}")
    for key in ("active", "input"):
        if not 0 <= row[key] <= 2:
            raise ValueError(f"{key} must be 0, 1 or 2 in {spec!r}")
    row["active"] = max(row["active"], row["input"])
    if not row["arms"] and not row["ports"] and not (row["active"] or row["input"]):
        raise ValueError(f"empty row {spec!r}")
    return row


def input_param_names(n):
    """Parameter names of the input heads: ``x`` alone, else ``x1, x2, ...``."""
    if n == 0:
        return []
    return ["x"] if n == 1 else [f"x{i + 1}" for i in range(n)]


class Topology:
    """Physical labels and output terms of a rooted list of owner rows."""

    def __init__(self, rows):
        self.rows = rows
        self.labels = []      # index -> dict(kind, name, role, ...)
        self.outputs = []     # index -> dict(terms=[label indices], name)
        self.head_index = []  # row -> label index of its head edge
        self.row_data = []
        self.input_indices = []
        self.root = bool(rows[0].get("root")) if rows else False
        self.root_owner_terms = None
        self.root_owner_output = None
        self.zero_index = None
        self._build()

    # -- construction -----------------------------------------------------
    def _label(self, kind, name, role, **kw):
        self.labels.append(dict(kind=kind, name=name, role=role, **kw))
        return len(self.labels) - 1

    def _output(self, terms, name):
        self.outputs.append(dict(terms=list(terms), name=name))

    def _build(self):
        nrows = len(self.rows)
        if nrows == 0:
            raise ValueError("at least one row is required")
        for k, row in enumerate(self.rows):
            if row["root"] and k != 0:
                raise ValueError("only the top row may be a root row")
        if self.root:
            self.head_index.append(None)
        else:
            self.head_index.append(self._label(
                "head", "g0", "row 0 head (exposed head y)", row=0, pos=0))
        for k, row in enumerate(self.rows):
            last = k == nrows - 1
            if not last and not row["active"]:
                raise ValueError(
                    f"row {k} is not the final row and must declare 'active' "
                    "so that it carries the next row's head")
            if row["input"] and not last and row["active"] - row["input"] != 1:
                raise ValueError(
                    "a non-final row may carry an input head only alongside the "
                    "next row's head, i.e. with active exactly one more than input")
            chain = [] if self.head_index[k] is None else [self.head_index[k]]
            for i in range(1, row["head"] + 1):
                chain.append(self._label(
                    "head_chain", f"r{k}h{i}",
                    f"row {k} head chain position {i}", row=k, pos=i))
            arms = []
            for a, ell in enumerate(row["arms"]):
                arms.append([self._label(
                    "arm", f"r{k}a{a}x{i}", f"row {k} arm {a} position {i}",
                    row=k, arm=a, pos=i) for i in range(ell + 1)])
            ports = [self._label("port", f"r{k}p{i}", f"row {k} port {i}",
                                 row=k, pos=i) for i in range(row["ports"])]
            nact, ninp = row["active"], row["input"]
            children, kept = [], []
            if not last:
                # One of this row's active children is the next row's head; any
                # others are pinned inputs of this row.  A stack of two-input
                # rows needs this, and it is the only way to express one: the
                # macro that resets such a chain has two active children at
                # every level, one of which continues the chain.
                if nact - ninp != 1:
                    raise ValueError(
                        f"row {k} is not the final row and must carry exactly "
                        "one active child more than its inputs (the next row's "
                        "head)")
                idx = self._label(
                    "head", f"g{k+1}",
                    f"row {k+1} head (active child of row {k})",
                    row=k + 1, pos=0)
                self.head_index.append(idx)
                children.append(idx)
                for a in range(ninp):
                    nm = f"s{k}" if ninp == 1 else f"s{k}_{a+1}"
                    jdx = self._label("input", nm,
                                      f"input head {nm} (parameter, row {k})",
                                      row=k, input_rank=a)
                    self.input_indices.append(jdx)
                    children.append(jdx)
                    kept.append(jdx)
            else:
                pnames = input_param_names(ninp)
                for a in range(nact):
                    if a < ninp:
                        nm = pnames[a]
                        idx = self._label("input", nm,
                                          f"input head {nm} (parameter)",
                                          row=k, input_rank=a)
                        self.input_indices.append(idx)
                    else:
                        nm = f"r{k}e" if nact - ninp == 1 else f"r{k}e{a}"
                        idx = self._label(
                            "active", nm,
                            f"row {k} active child {a} (stationary)", row=k)
                    children.append(idx)
                    kept.append(idx)
            self.row_data.append(dict(chain=chain, arms=arms, ports=ports,
                                      children=children, kept_children=kept))
        for k, rd in enumerate(self.row_data):
            chain = rd["chain"]
            for i in range(len(chain) - 1):
                self._output([chain[i], chain[i + 1]], f"r{k}h{i}out")
            terms = ([chain[-1]] if chain else []) \
                + [a[0] for a in rd["arms"]] + list(rd["ports"]) \
                + list(rd["children"])
            rd["owner_terms"] = terms
            if k == 0 and self.root:
                self.root_owner_terms = terms
                self.root_owner_output = len(self.outputs)
            self._output(terms, f"owner{k}")
            for a, arm in enumerate(rd["arms"]):
                for i in range(len(arm) - 1):
                    self._output([arm[i], arm[i + 1]], f"r{k}a{a}e{i}")
                self._output([arm[-1]], f"r{k}a{a}term")
            for i, p in enumerate(rd["ports"]):
                self._output([p], f"r{k}p{i}out")
            for c in rd["kept_children"]:
                self._output([c], self.labels[c]["name"] + "out")
        if self.root:
            # P' = P + {0}: the zero label balances the root owner output.
            self.zero_index = self._label(
                "zero", "0", "the zero label (P' = P + {0})")
        if len(self.outputs) != len(self.labels):
            raise AssertionError(
                f"|P'|={len(self.labels)} != |O|={len(self.outputs)}")

    # -- helpers ----------------------------------------------------------
    @property
    def width(self):
        return len(self.labels)

    def signature_indices(self):
        """Labels that must be mirror-paired or token.

        Everything except the exposed head (non-root macros) and the zero
        label (root macros).
        """
        idx = [j for j in range(self.width)
               if self.labels[j]["kind"] != "zero"]
        return idx if self.root else [j for j in idx if j != 0]

    def real_indices(self):
        """Physical labels proper, i.e. P without the zero label."""
        return [j for j in range(self.width)
                if self.labels[j]["kind"] != "zero"]

    def describe(self):
        parts = []
        for k, row in enumerate(self.rows):
            bits = []
            if row["root"]:
                bits.append("root")
            if row["head"]:
                bits.append(f"head={row['head']}")
            bits.append(f"arms={','.join(str(e) for e in row['arms']) or '-'}")
            if row["ports"]:
                bits.append(f"ports={row['ports']}")
            if row["active"]:
                bits.append("active" + ("2" if row["active"] == 2 else ""))
            if row["input"]:
                bits.append("input" + ("2" if row["input"] == 2 else ""))
            parts.append(f"row{k}[{';'.join(bits)}]")
        return " ".join(parts)


# ---------------------------------------------------------------- printing

def fmt_form(vec, names, denom):
    """Render an integer coefficient vector over ``names`` divided by ``denom``."""
    g = denom
    for v in vec:
        g = gcd(g, abs(int(v)))
    if g == 0:
        g = 1
    vec = [int(v) // g for v in vec]
    den = denom // g
    terms = []
    for coef, nm in zip(vec, names):
        if coef == 0:
            continue
        if not terms:
            sign = "-" if coef < 0 else ""
        else:
            sign = " - " if coef < 0 else " + "
        mag = abs(coef)
        terms.append(sign + (nm if mag == 1 else f"{mag}*{nm}"))
    if not terms:
        return "0"
    body = "".join(terms)
    if den == 1:
        return body
    return f"{body}/{den}" if len(terms) == 1 else f"({body})/{den}"


def render_rows(topo, coefs, names, denom):
    lines = []
    for k, rd in enumerate(topo.row_data):
        groups = [list(rd["chain"])] if rd["chain"] else []
        groups.extend(rd["arms"])
        if rd["ports"]:
            groups.append(list(rd["ports"]))
        extra = [c for c in rd["children"]
                 if topo.labels[c]["kind"] != "head"]
        if extra:
            groups.append(extra)
        body = "; ".join(", ".join(fmt_form(coefs[j], names, denom) for j in grp)
                         for grp in groups)
        tag = " [root]" if (k == 0 and topo.root) else ""
        lines.append(f"row {k}{tag}: ({body})")
    return lines


# -------------------------------------------------------------------- model

def build_model(topo, args, names, param_index):
    K = args.coef_bound
    L = args.denominator
    d = len(names)
    w = topo.width
    use_token = not args.no_token
    rank = args.token_rank
    model = cp_model.CpModel()

    # coefficient vectors -------------------------------------------------
    in_coord = [param_index[nm]
                for nm in input_param_names(len(topo.input_indices))]
    coef = []
    for j in range(w):
        kind = topo.labels[j]["kind"]
        row = []
        for i in range(d):
            nm = f"c_{j}_{i}"
            if j == 0 and not topo.root and args.free_head:
                # rigid-head mode: the exposed head is an arbitrary nonzero
                # form (it may depend on the inputs only, e.g. -(x1+x2))
                v = model.NewIntVar(-K, K, nm)
            elif j == 0 and not topo.root:
                if i == 0:
                    if args.head_mult_free:
                        vals = [L * h for h in range(1, K // L + 1)]
                        if not vals:
                            raise ValueError("--coef-bound must be >= --denominator")
                        v = model.NewIntVarFromDomain(
                            cp_model.Domain.FromValues(vals), nm)
                    else:
                        v = model.NewIntVar(L * args.head_mult, L * args.head_mult, nm)
                else:
                    v = model.NewIntVar(0, 0, nm)
            elif kind == "zero":
                v = model.NewIntVar(0, 0, nm)
            elif kind == "input":
                val = L if i == in_coord[topo.labels[j]["input_rank"]] else 0
                v = model.NewIntVar(val, val, nm)
            else:
                v = model.NewIntVar(-K, K, nm)
            row.append(v)
        coef.append(row)

    # genericity ----------------------------------------------------------
    base = 2 * K + 1
    enc = []
    for j in range(w):
        e = model.NewIntVar(0, base ** d - 1, f"enc{j}")
        model.Add(e == sum((coef[j][i] + K) * base ** i for i in range(d)))
        enc.append(e)
    real = topo.real_indices()
    model.AddAllDifferent([enc[j] for j in real])
    zero_code = sum(K * base ** i for i in range(d))
    for j in real:
        model.Add(enc[j] != zero_code)

    if args.forbid_antipode_x:
        if not topo.input_indices:
            print("warning: --forbid-antipode-x with no input head; ignored",
                  file=sys.stderr)
        for ix in in_coord:
            code = sum(((-L if i == ix else 0) + K) * base ** i for i in range(d))
            for j in range(w):
                model.Add(enc[j] != code)
    if args.forbid_antipode_port:
        pidx = [j for j, l in enumerate(topo.labels) if l["kind"] == "port"]
        if not pidx:
            print("warning: --forbid-antipode-port with no port; ignored", file=sys.stderr)
        for ip in pidx:
            negp = model.NewIntVar(0, base ** d - 1, f"neg_port_code{ip}")
            model.Add(negp == sum((K - coef[ip][i]) * base ** i for i in range(d)))
            for j in range(w):
                if j != ip:
                    model.Add(enc[j] != negp)
    if args.forbid_antipode_y and topo.root:
        print("warning: --forbid-antipode-y with a root row (no head); ignored",
              file=sys.stderr)
    elif args.forbid_antipode_y:
        negcode = model.NewIntVar(0, base ** d - 1, "neg_head_code")
        model.Add(negcode == sum((K - coef[0][i]) * base ** i for i in range(d)))
        for j in range(1, w):
            model.Add(enc[j] != negcode)

    # optional: no label besides the exposed head is a pure multiple of y ---
    if args.no_head_only and not topo.root:
        iy = param_index["y"]
        others = [i for i in range(d) if i != iy]
        for j in range(w):
            if j == 0 or topo.labels[j]["kind"] == "zero":
                continue
            lits = []
            for i in others:
                b = model.NewBoolVar(f"offy_{j}_{i}")
                model.Add(coef[j][i] != 0).OnlyEnforceIf(b)
                lits.append(b)
            if lits:
                model.AddBoolOr(lits)
            else:
                # y is the only parameter: every label is head-only.
                impossible = model.NewBoolVar(f"no_head_only_{j}")
                model.Add(impossible == 0)
                model.AddBoolOr([impossible])

    # optional: the only labels supported on x alone are +-x ----------------
    if args.forced_only_antipode:
        if not topo.input_indices:
            print("warning: --forced-only-antipode with no input head; ignored",
                  file=sys.stderr)
        # a label supported on a single input coordinate must carry +-L there;
        # labels mixing x1 and x2 are neither x1-only nor x2-only and are free.
        for ix in in_coord:
            xbase = sum(K * base ** i for i in range(d) if i != ix)
            for v in range(-K, K + 1):
                if v in (0, L, -L):
                    continue
                code = xbase + (v + K) * base ** ix
                for j in range(w):
                    model.Add(enc[j] != code)

    # token ---------------------------------------------------------------
    istok = None
    tok_lits = None
    if use_token:
        anyrank = rank == "any2"
        it1 = None if anyrank else param_index["t1"]
        it2 = param_index.get("t2")
        A = [model.NewIntVar(-K, K, f"tokA{i}") for i in range(d)]
        B = [model.NewIntVar(-K, K, f"tokB{i}") for i in range(d)]
        C = [model.NewIntVar(-K, K, f"tokC{i}") for i in range(d)]
        if not anyrank:
            model.Add(A[it1] == L)
        if rank == 3:
            model.Add(A[it2] == 0)
            model.Add(B[it1] == 0)
            model.Add(B[it2] == L)
        for i in range(d):
            model.Add(C[i] == -A[i] - B[i])
        if anyrank:
            # no dedicated token parameters: instead require rank(a, b) = 2,
            # i.e. some 2x2 minor of the (a; b) matrix is nonzero.  Because
            # c = -a-b, minor(a,c) = -minor(a,b), so the condition does not
            # depend on which two of the triple are used.
            minor_lits = []
            for i in range(d):
                for jj in range(i + 1, d):
                    p1 = model.NewIntVar(-K * K, K * K, f"mA_{i}_{jj}")
                    p2 = model.NewIntVar(-K * K, K * K, f"mB_{i}_{jj}")
                    model.AddMultiplicationEquality(p1, [A[i], B[jj]])
                    model.AddMultiplicationEquality(p2, [A[jj], B[i]])
                    lit = model.NewBoolVar(f"minor_nz_{i}_{jj}")
                    model.Add(p1 - p2 != 0).OnlyEnforceIf(lit)
                    minor_lits.append(lit)
            if minor_lits:
                model.AddBoolOr(minor_lits)
            else:
                # fewer than two parameters: a 2-dimensional span is impossible
                imp = model.NewBoolVar("any2_impossible")
                model.Add(imp == 0)
                model.AddBoolOr([imp])
        # only labels that take part in the signature may be token labels;
        # that is every label but the exposed head.  A pinned label such as the
        # input head x is eligible: under rank 2/3 the reified equality with
        # the t-units rules it out on its own, and under any2 it is a genuine
        # candidate (the residue-3 exporter's token contains x).
        eligible = set(topo.signature_indices())
        tok_lits = {}
        for role, vec in (("a", A), ("b", B), ("c", C)):
            lits = [model.NewBoolVar(f"tok{role}_{j}") for j in range(w)]
            model.AddExactlyOne(lits)
            for j in range(w):
                if j not in eligible:
                    model.Add(lits[j] == 0)
                    continue
                for i in range(d):
                    model.Add(coef[j][i] == vec[i]).OnlyEnforceIf(lits[j])
            tok_lits[role] = lits
        if args.all_inputs_in_token and not args.two_tokens and topo.input_indices:
            for j in topo.input_indices:
                model.AddBoolOr([tok_lits[r][j] for r in "abc"])
        if args.port_in_token:
            pidx = [j for j, l in enumerate(topo.labels) if l["kind"] == "port"]
            if not pidx:
                print("warning: --port-in-token with no port; ignored", file=sys.stderr)
            else:
                model.AddBoolOr([tok_lits[r][j] for r in "abc" for j in pidx])
        if args.input_in_token:
            # the pinned input label(s) must be token members (only meaningful
            # under --token-rank any2, where the token has no dedicated
            # coordinates); used to pair a forced-antipode child whose token
            # contains minus its own head.
            if not topo.input_indices:
                print("warning: --input-in-token with no input head; ignored",
                      file=sys.stderr)
            else:
                model.AddBoolOr([tok_lits[r][j] for r in "abc"
                                 for j in topo.input_indices])
        istok = [model.NewBoolVar(f"istok{j}") for j in range(w)]
        tcoords = ([] if anyrank else [it1]) + ([it2] if rank == 3 else [])
        for j in range(w):
            model.Add(tok_lits["a"][j] + tok_lits["b"][j] + tok_lits["c"][j]
                      == istok[j])
            if args.decouple_token:
                # strengthening: only the triple moves with the token
                # parameters, so sliding the token leaves the mirrors fixed.
                for i in tcoords:
                    model.Add(coef[j][i] == 0).OnlyEnforceIf(istok[j].Not())
        pos = {r: sum(j * tok_lits[r][j] for j in range(w)) for r in "abc"}
        if not args.no_symmetry:
            if rank == "any2":
                # a, b, c enter the constraints symmetrically (a+b+c=0 and the
                # minor condition are S_3 invariant) and no reparametrization
                # is involved, so the labels may simply be ordered.
                model.Add(pos["a"] < pos["b"])
                model.Add(pos["b"] < pos["c"])
            elif rank == 3:
                # a <-> b is the reparametrization (t1,t2)->(t2,t1), a
                # coordinate swap, so it preserves the box [-K,K].  The full
                # S_3 needs (t1,t2)->(-t1+t2,-t1), which can push a mirror
                # label out of the box; impose it only when the token is
                # decoupled (then every other t-coordinate is 0).
                model.Add(pos["a"] < pos["b"])
                if args.decouple_token:
                    model.Add(pos["b"] < pos["c"])
            else:
                # rank 2: a is pinned by the t1 unit but b and c are
                # interchangeable (a+b+c=0 is symmetric in them).
                model.Add(pos["b"] < pos["c"])

    # second token (mirrors + token1 + token2) -----------------------------
    tok2_lits = None
    istok2 = None
    if use_token and args.two_tokens:
        A2 = [model.NewIntVar(-K, K, f"tok2A{i}") for i in range(d)]
        B2 = [model.NewIntVar(-K, K, f"tok2B{i}") for i in range(d)]
        C2 = [model.NewIntVar(-K, K, f"tok2C{i}") for i in range(d)]
        for i in range(d):
            model.Add(C2[i] == -A2[i] - B2[i])
        minor2 = []
        for i in range(d):
            for jj in range(i + 1, d):
                p1 = model.NewIntVar(-K * K, K * K, f"m2A_{i}_{jj}")
                p2 = model.NewIntVar(-K * K, K * K, f"m2B_{i}_{jj}")
                model.AddMultiplicationEquality(p1, [A2[i], B2[jj]])
                model.AddMultiplicationEquality(p2, [A2[jj], B2[i]])
                lit = model.NewBoolVar(f"minor2_nz_{i}_{jj}")
                model.Add(p1 - p2 != 0).OnlyEnforceIf(lit)
                minor2.append(lit)
        if minor2:
            model.AddBoolOr(minor2)
        else:
            imp2 = model.NewBoolVar("two_tokens_impossible")
            model.Add(imp2 == 0)
            model.AddBoolOr([imp2])
        eligible2 = set(topo.signature_indices())
        tok2_lits = {}
        for role, vec in (("a", A2), ("b", B2), ("c", C2)):
            lits = [model.NewBoolVar(f"tok2{role}_{j}") for j in range(w)]
            model.AddExactlyOne(lits)
            for j in range(w):
                if j not in eligible2:
                    model.Add(lits[j] == 0)
                    continue
                for i in range(d):
                    model.Add(coef[j][i] == vec[i]).OnlyEnforceIf(lits[j])
            tok2_lits[role] = lits
        istok2 = [model.NewBoolVar(f"istok2_{j}") for j in range(w)]
        for j in range(w):
            model.Add(tok2_lits["a"][j] + tok2_lits["b"][j] + tok2_lits["c"][j]
                      == istok2[j])
        pos2 = {r: sum(j * tok2_lits[r][j] for j in range(w)) for r in "abc"}
        if args.all_inputs_in_token and topo.input_indices:
            for j in topo.input_indices:
                model.AddBoolOr([tok_lits[r][j] for r in "abc"] + [tok2_lits[r][j] for r in "abc"])
        if args.port_in_token:
            pidx = [j for j, l in enumerate(topo.labels) if l["kind"] == "port"]
            if pidx:
                model.AddBoolOr([tok_lits[r][j] for r in "abc" for j in pidx]
                                + [tok2_lits[r][j] for r in "abc" for j in pidx])
        if not args.no_symmetry:
            model.Add(pos2["a"] < pos2["b"])
            model.Add(pos2["b"] < pos2["c"])
            if not args.input_in_token:
                # the two tokens are interchangeable unless token1 is pinned
                # to the input: order them by their first label
                pos1a = sum(j * tok_lits["a"][j] for j in range(w))
                model.Add(pos1a < pos2["a"])

    # mirror pairs --------------------------------------------------------
    nonhead = topo.signature_indices()
    mvar = {}
    for ai in range(len(nonhead)):
        for bi in range(ai + 1, len(nonhead)):
            j, k = nonhead[ai], nonhead[bi]
            v = model.NewBoolVar(f"m_{j}_{k}")
            mvar[(j, k)] = v
            for i in range(d):
                model.Add(coef[j][i] + coef[k][i] == 0).OnlyEnforceIf(v)
    for j in nonhead:
        incident = [mvar[(min(j, k), max(j, k))] for k in nonhead if k != j]
        expr = sum(incident)
        if use_token:
            expr = expr + istok[j]
        if istok2 is not None:
            expr = expr + istok2[j]
        model.Add(expr == 1)

    # P = O ---------------------------------------------------------------
    match = [[model.NewBoolVar(f"b_{i}_{j}") for j in range(w)] for i in range(w)]
    for i in range(w):
        model.AddExactlyOne(match[i])
    for j in range(w):
        model.AddExactlyOne([match[i][j] for i in range(w)])
    for i, out in enumerate(topo.outputs):
        for c in range(d):
            expr = sum(coef[t][c] for t in out["terms"])
            for j in range(w):
                model.Add(expr == coef[j][c]).OnlyEnforceIf(match[i][j])

    # optional strict root variant: the zero must be the root owner output
    if topo.root and args.root_zero_output:
        model.Add(match[topo.root_owner_output][topo.zero_index] == 1)

    # redundant global cut implied by P = O: with mult(j) the multiplicity of
    # label j in the output multiset, sum_j (mult(j) - 1) c(j) = 0.  Without a
    # root row this says the non-head vectors sum to zero.
    mult = [0] * w
    for out in topo.outputs:
        for t in out["terms"]:
            mult[t] += 1
    for i in range(d):
        model.Add(sum((mult[j] - 1) * coef[j][i] for j in range(w)) == 0)

    # symmetry breaking ---------------------------------------------------
    if not args.no_symmetry:
        for rd, row in zip(topo.row_data, topo.rows):
            for a in range(len(row["arms"]) - 1):
                if row["arms"][a] == row["arms"][a + 1]:
                    model.Add(enc[rd["arms"][a][0]] < enc[rd["arms"][a + 1][0]])
            for i in range(len(rd["ports"]) - 1):
                model.Add(enc[rd["ports"][i]] < enc[rd["ports"][i + 1]])

    return model, coef, enc, match, mvar, tok_lits, tok2_lits


# --------------------------------------------------------------- verification

def verify(topo, coefs, perm, names, denom, mirror_pairs, token, rank,
           trials, seed, check_no_head_only=False,
           check_forced_only_antipode=False, root_zero_output=False,
           token2=None):
    d = len(names)
    w = topo.width
    rep = {}
    out_vecs = [[sum(coefs[t][i] for t in o["terms"]) for i in range(d)]
                for o in topo.outputs]
    rep["symbolic_P_eq_O"] = (sorted(tuple(v) for v in coefs)
                              == sorted(tuple(v) for v in out_vecs))
    rep["permutation_consistent"] = all(
        out_vecs[i] == list(coefs[perm[i]]) for i in range(w))
    real = topo.real_indices()
    rep["distinct_forms"] = (len({tuple(coefs[j]) for j in real}) == len(real))
    rep["nonzero_forms"] = all(any(coefs[j]) for j in real)
    rep["mirror_pairs_negate"] = all(
        all(coefs[a][i] + coefs[b][i] == 0 for i in range(d))
        for a, b in mirror_pairs)
    covered = [0] * w
    for a, b in mirror_pairs:
        covered[a] += 1
        covered[b] += 1
    if token:
        for j in token.values():
            covered[j] += 1
    if token2:
        for j in token2.values():
            covered[j] += 1
    sig = topo.signature_indices()
    rep["signature_partition"] = (
        all(covered[j] == 1 for j in sig)
        and all(covered[j] == 0 for j in range(w) if j not in set(sig)))
    if topo.root:
        zj = topo.zero_index
        rep["zero_label_is_zero"] = not any(coefs[zj])
        matched = [i for i in range(w) if perm[i] == zj]
        rep["zero_label_matched_once"] = len(matched) == 1
        if matched:
            rep["zero_output_name"] = topo.outputs[matched[0]]["name"]
            rep["zero_output_form_is_zero"] = not any(
                sum(coefs[t][i] for t in topo.outputs[matched[0]]["terms"])
                for i in range(d))
        if root_zero_output:
            rep["root_owner_is_the_zero"] = (
                bool(matched) and matched[0] == topo.root_owner_output)
    if token:
        a, b, c = token["a"], token["b"], token["c"]
        rep["token_zero_sum"] = all(
            coefs[a][i] + coefs[b][i] + coefs[c][i] == 0 for i in range(d))
        if rank == "any2":
            rep["token_spans_2d"] = any(
                coefs[a][i] * coefs[b][j] - coefs[a][j] * coefs[b][i] != 0
                for i in range(d) for j in range(i + 1, d))
            tc = []
        else:
            it1 = names.index("t1")
        if rank == 3:
            it2 = names.index("t2")
            rep["token_free"] = (
                coefs[a][it1] == denom and coefs[a][it2] == 0
                and coefs[b][it1] == 0 and coefs[b][it2] == denom)
            tc = [it1, it2]
        elif rank == 2:
            rep["token_free"] = coefs[a][it1] == denom
            tc = [it1]
        if tc:
            rep["token_decoupled"] = all(
                all(coefs[j][i] == 0 for i in tc)
                for j in range(w) if j not in (a, b, c))
    if token2:
        a2, b2, c2 = token2["a"], token2["b"], token2["c"]
        rep["token2_zero_sum"] = all(
            coefs[a2][i] + coefs[b2][i] + coefs[c2][i] == 0 for i in range(d))
        rep["token2_spans_2d"] = any(
            coefs[a2][i] * coefs[b2][j] - coefs[a2][j] * coefs[b2][i] != 0
            for i in range(d) for j in range(i + 1, d))
        rep["tokens_disjoint"] = (token is None
                                  or not (set(token.values()) & set(token2.values())))
    if check_no_head_only and not topo.root:
        iy = names.index("y")
        rep["no_head_only"] = all(
            any(coefs[j][i] != 0 for i in range(d) if i != iy)
            for j in range(w) if j != 0)
    if check_forced_only_antipode and topo.input_indices:
        ok = True
        for ix in [names.index(nm)
                   for nm in input_param_names(len(topo.input_indices))]:
            for j in range(w):
                if not any(coefs[j]):
                    continue
                if all(coefs[j][i] == 0 for i in range(d) if i != ix):
                    ok = ok and coefs[j][ix] in (denom, -denom)
        rep["forced_only_antipode"] = ok
    rng = random.Random(seed)
    trial_reports = []
    for _ in range(trials):
        point = None
        for _attempt in range(500):
            cand = [rng.randrange(-400, 401) for _ in range(d)]
            vals = [Q(sum(coefs[j][i] * cand[i] for i in range(d)), denom)
                    for j in real]
            if len(set(vals)) == len(real) and 0 not in vals:
                point = cand
                break
        if point is None:
            trial_reports.append({"point": None, "generic": False})
            continue
        pv = sorted(Q(sum(coefs[j][i] * point[i] for i in range(d)), denom)
                    for j in range(w))
        ov = sorted(Q(sum(v[i] * point[i] for i in range(d)), denom)
                    for v in out_vecs)
        real_vals = [Q(sum(coefs[j][i] * point[i] for i in range(d)), denom)
                     for j in real]
        mirror_ok = all(
            Q(sum(coefs[a][i] * point[i] for i in range(d)), denom)
            + Q(sum(coefs[b][i] * point[i] for i in range(d)), denom) == 0
            for a, b in mirror_pairs)
        trial_reports.append({
            "point": dict(zip(names, point)),
            "generic": True,
            "P_eq_O": pv == ov,
            "distinct": len(set(real_vals)) == len(real),
            "mirror_ok": mirror_ok,
        })
    rep["numeric_trials"] = trial_reports
    rep["numeric_ok"] = all(t.get("P_eq_O") and t.get("distinct")
                            and t.get("mirror_ok") for t in trial_reports)
    rep["all_ok"] = all(v for k, v in rep.items()
                        if isinstance(v, bool) and k != "token_decoupled")
    return rep


# --------------------------------------------------------------------- main

def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Symbolic CP-SAT search for free-token P=O families.")
    ap.add_argument("--rows", action="append", required=True,
                    help='row spec, e.g. "head=1;arms=2,2,2;ports=1;active"; '
                         "repeat for a joint macro (parent first).  The top row "
                         "may instead carry the flag 'root' (no head label, no "
                         "parameter y, owner output pinned to zero)")
    ap.add_argument("--coef-bound", type=int, default=3,
                    help="K: every coefficient lies in [-K, K] (default 3)")
    ap.add_argument("--internal", type=int, default=0,
                    help="number of extra internal parameters u_1..u_m")
    ap.add_argument("--denominator", type=int, default=1,
                    help="L: all fixed forms are scaled by L, so families with "
                         "rational entries of denominator L become integral")
    ap.add_argument("--no-token", action="store_true",
                    help="search for a pure head + mirror signature")
    ap.add_argument("--token-rank", default="3", choices=("2", "3", "any2"),
                    help="3: token spans the dedicated parameters t1 and t2 "
                         "(two free coordinates); 2: only t1 is a parameter, "
                         "b and c are arbitrary with a+b+c=0 (one free "
                         "coordinate); any2: no dedicated token parameters, "
                         "a+b+c=0 with a and b spanning two dimensions over "
                         "the existing parameters (y, x, u_i)")
    ap.add_argument("--decouple-token", action="store_true",
                    help="strengthening: force every non-token label to be "
                         "independent of the token parameters, so that sliding "
                         "the token leaves the mirror pairs fixed")
    ap.add_argument("--forbid-antipode-x", action="store_true")
    ap.add_argument("--port-in-token", action="store_true",
                    help="some port label must be a token member (the port stands for a "
                         "pinned active child that is forced-antipode)")
    ap.add_argument("--forbid-antipode-port", action="store_true",
                    help="no label is identically minus a port label")
    ap.add_argument("--forbid-antipode-y", action="store_true")
    ap.add_argument("--input-in-token", action="store_true",
                    help="require a pinned input label to be a token member "
                         "(use with --token-rank any2)")
    ap.add_argument("--free-head", action="store_true",
                    help="rigid-head mode: the exposed head is any nonzero "
                         "form, e.g. a function of the inputs (E5 dropped)")
    ap.add_argument("--all-inputs-in-token", action="store_true",
                    help="every pinned input label must be a token member "
                         "(token1 or, with --two-tokens, token2)")
    ap.add_argument("--two-tokens", action="store_true",
                    help="signature mirror pairs + token1 + token2 (both any2 "
                         "rank); --input-in-token applies to token1 only")
    ap.add_argument("--root-zero-output", action="store_true",
                    help="stricter root variant: require the zero label to be "
                         "matched to the root owner output itself, i.e. pin "
                         "the root owner output to the zero form.  By default "
                         "the zero may land on any output")
    ap.add_argument("--no-head-only", action="store_true",
                    help="forbid every label other than the exposed head from "
                         "being a pure multiple of y, so the macro carries no "
                         "head-only label that could identity-collide with a "
                         "parent's forced multiples of the shared head; a no-op "
                         "for root rows (which have no y)")
    ap.add_argument("--forced-only-antipode", action="store_true",
                    help="with an input head x, the only labels supported on x "
                         "alone are -x and the input head itself (rejects x/2, "
                         "2x, ...); a no-op without an input head")
    ap.add_argument("--head-mult", type=int, default=1,
                    help="exposed head is (h*L, 0, ...) with h = this value")
    ap.add_argument("--head-mult-free", action="store_true",
                    help="let h range over 1..K//L instead")
    ap.add_argument("--no-symmetry", action="store_true",
                    help="disable symmetry breaking on equal arms / ports / "
                         "token roles")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--time-limit", type=float, default=300.0)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--trials", type=int, default=3,
                    help="random parameter points used for verification")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--json", default=None)
    args = ap.parse_args(argv)

    args.token_rank = (int(args.token_rank) if args.token_rank in ("2", "3")
                       else "any2")
    if args.coef_bound < 1:
        ap.error("--coef-bound must be >= 1")
    if args.denominator < 1:
        ap.error("--denominator must be >= 1")
    if args.denominator > args.coef_bound:
        ap.error("--coef-bound must be >= --denominator (fixed forms use L)")
    if args.head_mult < 1:
        ap.error("--head-mult must be >= 1")
    if args.head_mult * args.denominator > args.coef_bound:
        ap.error("--head-mult * --denominator exceeds --coef-bound")

    rows = [parse_row(s) for s in args.rows]
    topo = Topology(rows)
    w = topo.width
    use_token = not args.no_token
    if args.two_tokens and (args.no_token or args.token_rank != "any2"):
        print("error: --two-tokens requires a token and --token-rank any2",
              file=sys.stderr)
        return 2
    if (not args.no_token) and args.token_rank == "any2" and args.decouple_token:
        print("warning: --decouple-token with --token-rank any2 (there are no "
              "token parameters); ignored", file=sys.stderr)
    if topo.root and (args.head_mult != 1 or args.head_mult_free):
        print("warning: --head-mult/--head-mult-free with a root row (there is "
              "no exposed head); ignored", file=sys.stderr)

    names = [] if topo.root else ["y"]
    names += input_param_names(len(topo.input_indices))
    if use_token and args.token_rank != "any2":
        names.append("t1")
        if args.token_rank == 3:
            names.append("t2")
    names += [f"u{i+1}" for i in range(args.internal)]
    param_index = {nm: i for i, nm in enumerate(names)}
    d = len(names)

    nonhead = len(topo.signature_indices())
    remainder = nonhead - (3 if use_token else 0)
    print(f"topology: {topo.describe()}")
    if topo.root:
        print("root row 0: no head and no parameter y; P' = P + {0} with the "
              "zero label, and O includes the root owner output "
              + "+".join(topo.labels[t]["name"] for t in topo.root_owner_terms)
              + (" (pinned to be the zero)" if args.root_zero_output
                 else " (the zero may land on any output)"))
    print(f"width |P| = |O| = {w}; parameters {names} (d={d}); "
          f"coef bound K={args.coef_bound}; denominator L={args.denominator}")
    print(f"signature: {'' if topo.root else 'head + '}{remainder // 2} "
          f"mirror pairs"
          + (f" + one token (rank {args.token_rank})" if use_token else ""))
    if remainder < 0 or remainder % 2:
        print(f"NOTE: {nonhead} signature labels cannot be split into "
              f"{'a token triple plus ' if use_token else ''}mirror pairs; "
              "the model is trivially infeasible.")
    if d == 0:
        print("NOTE: no parameters remain (a root row has no y, and neither "
              "an input head nor dedicated token coordinates nor --internal "
              ">= 1 supplies one); the model is trivially infeasible.")

    model, coef, enc, match, mvar, tok_lits, tok2_lits = build_model(
        topo, args, names, param_index)
    solver = cp_model.CpSolver()
    solver.parameters.num_workers = args.workers
    solver.parameters.max_time_in_seconds = args.time_limit
    solver.parameters.random_seed = args.seed
    solver.parameters.log_search_progress = args.verbose
    status = solver.Solve(model)
    status_name = solver.StatusName(status)
    print(f"status: {status_name}  (wall {solver.WallTime():.2f}s, "
          f"branches {solver.NumBranches()}, conflicts {solver.NumConflicts()})")

    result = {
        "rows": args.rows,
        "row_specs": rows,
        "width": w,
        "root_row": topo.root,
        "root_zero_output": args.root_zero_output,
        "zero_label_index": topo.zero_index,
        "root_owner_output_index": topo.root_owner_output,
        "root_owner_terms": topo.root_owner_terms,
        "root_owner_term_names": ([topo.labels[t]["name"]
                                   for t in topo.root_owner_terms]
                                  if topo.root else None),
        "parameters": names,
        "denominator": args.denominator,
        "coef_bound": args.coef_bound,
        "internal": args.internal,
        "token": use_token,
        "token_rank": args.token_rank if use_token else None,
        "decouple_token": args.decouple_token,
        "head_mult": args.head_mult,
        "head_mult_free": args.head_mult_free,
        "forbid_antipode_x": args.forbid_antipode_x,
        "forbid_antipode_y": args.forbid_antipode_y,
        "input_in_token": args.input_in_token,
        "port_in_token": args.port_in_token,
        "forbid_antipode_port": args.forbid_antipode_port,
        "two_tokens_requested": args.two_tokens,
        "free_head": args.free_head,
        "all_inputs_in_token": args.all_inputs_in_token,
        "no_head_only": args.no_head_only,
        "forced_only_antipode": args.forced_only_antipode,
        "labels": [{"index": j, "name": lb["name"], "kind": lb["kind"],
                    "role": lb["role"], "row": lb.get("row"),
                    "arm": lb.get("arm"), "pos": lb.get("pos")}
                   for j, lb in enumerate(topo.labels)],
        "outputs": [{"index": i, "name": o["name"], "terms": o["terms"],
                     "term_names": [topo.labels[t]["name"] for t in o["terms"]]}
                    for i, o in enumerate(topo.outputs)],
        "status": status_name,
        "wall_time": solver.WallTime(),
    }

    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        coefs = [[solver.Value(coef[j][i]) for i in range(d)] for j in range(w)]
        perm = [next(j for j in range(w) if solver.Value(match[i][j]))
                for i in range(w)]
        mirror_pairs = [k for k, v in mvar.items() if solver.Value(v)]
        token = None
        if use_token:
            token = {r: next(j for j in range(w) if solver.Value(tok_lits[r][j]))
                     for r in "abc"}
        token2 = None
        if tok2_lits:
            token2 = {r: next(j for j in range(w) if solver.Value(tok2_lits[r][j]))
                      for r in "abc"}
        print("\nphysical labels:")
        for j in range(w):
            role = ""
            if token and j in token.values():
                role = " [token " + next(r for r, i in token.items() if i == j) + "]"
            elif token2 and j in token2.values():
                role = " [token2 " + next(r for r, i in token2.items() if i == j) + "]"
            elif j == 0 and not topo.root:
                role = " [exposed head]"
            elif topo.labels[j]["kind"] == "zero":
                role = " [zero]"
            print(f"  {j:2d} {topo.labels[j]['name']:>10s} = "
                  f"{fmt_form(coefs[j], names, args.denominator):<26s}"
                  f"{role}   ({topo.labels[j]['role']})")
        print("\nrows:")
        for line in render_rows(topo, coefs, names, args.denominator):
            print("  " + line)
        print("\noutput permutation (output -> physical label):")
        out_vecs = [[sum(coefs[t][i] for t in o["terms"]) for i in range(d)]
                    for o in topo.outputs]
        for i, o in enumerate(topo.outputs):
            src = "+".join(topo.labels[t]["name"] for t in o["terms"])
            print(f"  {o['name']:>12s} = {src:<28s} = "
                  f"{fmt_form(out_vecs[i], names, args.denominator):<24s} -> "
                  f"{topo.labels[perm[i]]['name']}")
        if topo.root:
            rv = [sum(coefs[t][i] for t in topo.root_owner_terms)
                  for i in range(d)]
            print("\nroot owner output: "
                  + "+".join(topo.labels[t]["name"]
                             for t in topo.root_owner_terms)
                  + " = " + fmt_form(rv, names, args.denominator))
            zmatch = [i for i in range(w) if perm[i] == topo.zero_index]
            if zmatch:
                print("zero label matched to output "
                      + topo.outputs[zmatch[0]]["name"] + " = "
                      + "+".join(topo.labels[t]["name"]
                                 for t in topo.outputs[zmatch[0]]["terms"]))
        print("\nmirror pairs:")
        for a, b in sorted(mirror_pairs):
            print(f"  {topo.labels[a]['name']} <-> {topo.labels[b]['name']}  "
                  f"({fmt_form(coefs[a], names, args.denominator)} , "
                  f"{fmt_form(coefs[b], names, args.denominator)})")
        if token:
            print("token triple: " + ", ".join(
                f"{r}={topo.labels[j]['name']}="
                f"{fmt_form(coefs[j], names, args.denominator)}"
                for r, j in token.items()))
        if token2:
            print("token2 triple: " + ", ".join(
                f"{r}={topo.labels[j]['name']}="
                f"{fmt_form(coefs[j], names, args.denominator)}"
                for r, j in token2.items()))
        rep = verify(topo, coefs, perm, names, args.denominator, mirror_pairs,
                     token, args.token_rank, args.trials, args.seed,
                     check_no_head_only=args.no_head_only,
                     check_forced_only_antipode=args.forced_only_antipode,
                     root_zero_output=args.root_zero_output,
                     token2=token2)
        print("\nverification:")
        for key in ("symbolic_P_eq_O", "permutation_consistent", "distinct_forms",
                    "nonzero_forms", "mirror_pairs_negate", "signature_partition",
                    "zero_label_is_zero", "zero_label_matched_once",
                    "zero_output_form_is_zero", "root_owner_is_the_zero",
                    "no_head_only", "forced_only_antipode",
                    "token_zero_sum", "token_free", "token_spans_2d",
                    "token_decoupled", "token2_zero_sum", "token2_spans_2d",
                    "tokens_disjoint", "numeric_ok", "all_ok"):
            if key in rep:
                print(f"  {key:>22s}: {rep[key]}")
        for t in rep["numeric_trials"]:
            print(f"    point {t['point']} -> P=O {t.get('P_eq_O')}, "
                  f"distinct {t.get('distinct')}, mirror {t.get('mirror_ok')}")
        result.update({
            "coefficients": coefs,
            "coefficients_by_label": {
                topo.labels[j]["name"]: coefs[j] for j in range(w)},
            "forms": [fmt_form(coefs[j], names, args.denominator) for j in range(w)],
            "rows_rendered": render_rows(topo, coefs, names, args.denominator),
            "permutation": perm,
            "permutation_named": [[topo.outputs[i]["name"],
                                   topo.labels[perm[i]]["name"]]
                                  for i in range(w)],
            "mirror_pairs": [list(p) for p in sorted(mirror_pairs)],
            "mirror_pairs_named": [[topo.labels[a]["name"], topo.labels[b]["name"]]
                                   for a, b in sorted(mirror_pairs)],
            "token_indices": token,
            "token_named": ({r: topo.labels[j]["name"] for r, j in token.items()}
                            if token else None),
            "two_tokens": bool(token2),
            "token2_indices": token2,
            "token2_named": ({r: topo.labels[j]["name"] for r, j in token2.items()}
                             if token2 else None),
            "verification": rep,
        })
        if not rep["all_ok"]:
            print("VERIFICATION FAILED", file=sys.stderr)
    else:
        print("no family with this signature exists inside the stated bounds.")

    if args.json:
        with open(args.json, "w") as fh:
            json.dump(result, fh, indent=1, sort_keys=True)
        print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
