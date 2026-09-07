#!/usr/bin/env python3
r"""Lemma lem:reset realised: the two-level joint of two two-input rows.

Background
----------
A RESET ROW is a residual-{1} direct-edge two-input owner (context key
``h0_1_p0_act2``): head chain length 0, one residual arm of residue 1, no
ports, two kept active children.  Its unique nondegenerate family is the
rigid row ``(-x1-x2; -x2, -x1; x1, x2)`` of ``data/batches/alphabet_rigid.jsonl``,
whose head is FORCED by the two pinned inputs, so a CHAIN of such rows -- each
the continuing active child of the one above -- has no head freedom anywhere
along it.  Lemma lem:reset (paper/sparse_edge_graceful.tex, appendix "Proof of
the realization lemma") says that JOINING two consecutive rows of a chain into
one cell of nine labels produces a family whose head is an independent
parameter, so the chain is cut into joints of two levels from the bottom and an
odd chain leaves a single (still rigid) row at its top.

This module realises those joints.  It leaves the faithful mode and the
existing sink mode untouched: it is a subclass of
``sink_constructor.SinkRealiser`` plus a scoped swap of the name
``sink_constructor.SinkRealiser`` while ``construct_sink`` runs -- the same
technique ``sink_constructor`` itself uses for ``ftc.complete_blocks``.  Sinks,
blocks, completion and ``free_token_lib.verify_edge_graceful`` are unchanged.

The joint family
----------------
The joint's topology is the two-row stack ``arms=1;active=2;input=1`` over
``arms=1;active2;input2`` -- the topology of ``scripts/twoinput_reset.py`` at
``levels = 2``.  Its nine labels, in that module's order, are

    g0, r0a0x0, r0a0x1, g1, s0, r1a0x0, r1a0x1, x1, x2

(the two heads, the two labels of each arm, the upper row's pinned input
``s0`` and the lower row's two pinned inputs ``x1, x2``), and its nine outputs
are the two owner sums, the four arm outputs and the three kept-child outputs.

``scripts/sink_route/reset_joint_families.py`` re-runs the enumeration of
``scripts/twoinput_reset.py`` and records all TWELVE head-free families in
``data/sink_route/twoinput_reset_families.json``, ranked by how many labels
still move once the three inputs are pinned.  The one family
``data/twoinput_reset.json`` happens to record is the weakest of the twelve --
only ``g0, r1a0x0, r1a0x1`` move there, so ``g1``, ``r0a0x0`` and ``r0a0x1``
would be fixed outright by the children's heads and the joint could not search
for them.  Seven of the twelve move all six non-input labels; this module uses
the first of those, the bijection

    owner0 -> g0     r0a0e0 -> r1a0x0  r0a0term -> r0a0x1  s0out -> s0
    owner1 -> r0a0x0 r1a0e0 -> g1      r1a0term -> r1a0x1
    x1out  -> x1     x2out  -> x2

whose solution space has dimension five.  Solving ``P = O`` for it gives, over
the parameters ``(y, u1, s0, x1, x2)`` with ``y = g0`` and ``u1 = r0a0x0``,

    g0     = y                       r0a0x0 = u1
    r0a0x1 = u1 + s0 - x1 - x2       g1     = -u1 - s0
    r1a0x0 = 2*u1 + s0 - x1 - x2     r1a0x1 = -3*u1 - 2*s0 + x1 + x2

so with the three inputs pinned by the already-realised children the head
``y`` and the internal parameter ``u1`` are free, EVERY one of the six labels
the joint places moves with them (slopes 1, 1, 1, -1, 2, -3), and the head is
chosen numerically like any other head.  :func:`verify_family` re-derives
``P = O`` symbolically from the topology (via
``free_token_constructor.multi_output_forms``, the same output rule the
constructor's own synthesiser uses), checks an integer point of the family,
and cross-checks the enumeration file and ``data/twoinput_reset.json``; it
runs once, at import time.

``free_token_lib.Family`` cannot hold this family: its ``_validate_row_specs``
rejects a non-final row that keeps an input (row 0 here has ``active=2`` and
``input=1``), so the family is carried by the small shim :class:`JointFamily`,
which exposes exactly what ``FaithfulRealiser`` reads off a family.

Usage
-----
    .venv/bin/python scripts/sink_route/reset_joint_constructor.py --verify
    ... --resetcomb 4,6,8
    ... --suite --mode both        # the existing sink regression families
    ... --json OUT.json
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from fractions import Fraction as Q
from typing import Dict, List, Optional, Sequence, Set

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.normpath(os.path.join(HERE, ".."))
for _p in (HERE, SCRIPTS):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import free_token_constructor as ftc              # noqa: E402
import free_token_lib as ftl                      # noqa: E402
import context_scheduler as cs                    # noqa: E402
import sink_constructor as sk                     # noqa: E402
from reset_comb import reset_comb                 # noqa: E402

LinForm = ftc.LinForm
Failure = ftc.Failure

DATA = os.path.normpath(os.path.join(HERE, "..", "..", "data"))
WITNESS_PATH = os.path.join(DATA, "twoinput_reset.json")
FAMILIES_PATH = os.path.join(DATA, "sink_route",
                             "twoinput_reset_families.json")

#: prefix of the certificate note that records how many joints were realised
JOINT_NOTE = "lem_reset joints realised: "


# ==========================================================================
# 1.  The nine-label joint family
# ==========================================================================

#: labels in the order ``twoinput_reset.py`` (and ``Topology``) produces them
JOINT_LABELS = ["g0", "r0a0x0", "r0a0x1", "g1", "s0",
                "r1a0x0", "r1a0x1", "x1", "x2"]

#: label kinds, parallel to :data:`JOINT_LABELS`
JOINT_KINDS = ["head", "arm", "arm", "head", "input", "arm", "arm",
               "input", "input"]

#: parameters: the free head, the lower row's free arm label, the three inputs
JOINT_PARAMS = ["y", "u1", "s0", "x1", "x2"]

#: coefficient table over :data:`JOINT_PARAMS`, denominator 1
JOINT_COEFFS: Dict[str, List[int]] = {
    "g0":     [1, 0, 0, 0, 0],
    "r0a0x0": [0, 1, 0, 0, 0],
    "r0a0x1": [0, 1, 1, -1, -1],
    "g1":     [0, -1, -1, 0, 0],
    "s0":     [0, 0, 1, 0, 0],
    "r1a0x0": [0, 2, 1, -1, -1],
    "r1a0x1": [0, -3, -2, 1, 1],
    "x1":     [0, 0, 0, 1, 0],
    "x2":     [0, 0, 0, 0, 1],
}

#: the bijection outputs -> labels of the family used
JOINT_BIJECTION = {
    "owner0": "g0", "r0a0e0": "r1a0x0", "r0a0term": "r0a0x1", "s0out": "s0",
    "owner1": "r0a0x0", "r1a0e0": "g1", "r1a0term": "r1a0x1",
    "x1out": "x1", "x2out": "x2",
}

#: an integer point of the family (nine distinct, nonzero, non-antipodal)
JOINT_WITNESS_PARAMS = {"y": 13, "u1": 3, "s0": 11, "x1": -7, "x2": 23}


def _row_structures() -> List["ftl.RowStructure"]:
    """The two rows of the joint, as ``free_token_lib`` row structures.

    Row 0 keeps the upper row's pinned input ``s0`` AND shares its child edge
    ``g1`` with row 1; that is the shape ``Family._validate_row_specs``
    forbids, which is why the joint needs the shim below.
    """
    row0 = ftl.RowStructure(
        index=0, is_root=False, chain=["g0"],
        arms=[["r0a0x0", "r0a0x1"]], ports=[], shared="g1",
        kept=["s0"], kept_kinds=["input"], inputs=["s0"],
        spec={"head": 0, "arms": [1], "ports": 0, "root": False,
              "active": 2, "input": 1})
    row1 = ftl.RowStructure(
        index=1, is_root=False, chain=["g1"],
        arms=[["r1a0x0", "r1a0x1"]], ports=[], shared=None,
        kept=["x1", "x2"], kept_kinds=["input", "input"],
        inputs=["x1", "x2"],
        spec={"head": 0, "arms": [1], "ports": 0, "root": False,
              "active": 2, "input": 2})
    return [row0, row1]


class JointFamily:
    """A family-shaped shim for the nine-label joint of Lemma lem:reset.

    Carries exactly what ``FaithfulRealiser`` reads off a family during a
    cell: ``parameters``, the denominator ``L``, ``labels`` with coefficient
    vectors (for ``Realiser.label_forms``), ``structure()``, the head name,
    the input names and ``token_labels()``.
    """

    def __init__(self) -> None:
        self.parameters = list(JOINT_PARAMS)
        self.d = len(self.parameters)
        self.denominator = 1
        self.L = 1
        self.key = "h0_1_p0_act2+h0_1_p0_act2"
        self.meta = {"provenance": "lem:reset two-level joint",
                     "key": self.key}
        self.payload: Dict[str, object] = {}
        self.ctx = {}
        self.kind = "reset_joint"
        self.token = False
        self.token_indices = None
        self.token_rank = None
        self.is_root = False
        self.labels: List[ftl.Label] = []
        self.by_name: Dict[str, ftl.Label] = {}
        rows = {"g0": 0, "r0a0x0": 0, "r0a0x1": 0, "g1": 1, "s0": 0,
                "r1a0x0": 1, "r1a0x1": 1, "x1": 1, "x2": 1}
        arms = {"r0a0x0": 0, "r0a0x1": 0, "r1a0x0": 0, "r1a0x1": 0}
        poss = {"g0": 0, "g1": 0, "r0a0x0": 0, "r0a0x1": 1,
                "r1a0x0": 0, "r1a0x1": 1}
        for i, (name, kind) in enumerate(zip(JOINT_LABELS, JOINT_KINDS)):
            lab = ftl.Label(index=i, name=name, kind=kind, row=rows[name],
                            arm=arms.get(name), pos=poss.get(name),
                            role_text=f"joint {name}",
                            coeffs=tuple(JOINT_COEFFS[name]))
            self.labels.append(lab)
            self.by_name[name] = lab
        self._structure = _row_structures()

    # -- the accessors FaithfulRealiser uses -----------------------------
    def structure(self) -> List["ftl.RowStructure"]:
        return self._structure

    def head_label(self) -> str:
        return "g0"

    def input_labels(self) -> List[str]:
        return ["s0", "x1", "x2"]

    def input_label(self) -> str:
        return "s0"

    def token_labels(self):
        return None

    def __repr__(self) -> str:
        return "<JointFamily lem:reset 9 labels>"


JOINT_FAMILY = JointFamily()


# ==========================================================================
# 2.  Verification of the family (P = O, as twoinput_reset.py does)
# ==========================================================================

def _param_vectors() -> Dict[str, List[Q]]:
    return {nm: [Q(c) for c in JOINT_COEFFS[nm]] for nm in JOINT_LABELS}


def verify_family() -> dict:
    """Re-derive ``P = O`` for the joint and check it against the witness.

    The output rule is ``free_token_constructor.multi_output_forms``, the same
    one the constructor's local synthesiser uses, applied to the two row
    structures of the joint; each output is then expressed over the five
    parameters and matched against the label it is supposed to equal.
    """
    structs = _row_structures()
    outs, _phys = ftc.multi_output_forms(JOINT_LABELS, structs, False)
    names = list(JOINT_LABELS)
    # the output names, in the order multi_output_forms emits them
    out_names = ["owner0", "r0a0e0", "r0a0term", "s0out",
                 "owner1", "r1a0e0", "r1a0term", "x1out", "x2out"]
    if len(outs) != len(names) or len(out_names) != len(names):
        raise AssertionError("the joint topology does not have |P| = |O|")
    P = _param_vectors()
    report: dict = {"outputs": len(outs), "labels": len(names)}

    # (a) P = O identically, output by output, under the recorded bijection
    ok_forms = True
    for oname, vec in zip(out_names, outs):
        acc = [Q(0)] * len(JOINT_PARAMS)
        for coef, lname in zip(vec, names):
            if coef:
                acc = [a + coef * b for a, b in zip(acc, P[lname])]
        target = P[JOINT_BIJECTION[oname]]
        if acc != target:
            ok_forms = False
            report.setdefault("bad", []).append(oname)
    report["symbolic_P_eq_O"] = ok_forms
    report["bijection_is_a_permutation"] = (
        sorted(JOINT_BIJECTION.values()) == sorted(names))

    # (b) the labels are pairwise distinct, non-antipodal and nonzero as forms
    distinct = True
    for i, a in enumerate(names):
        if all(c == 0 for c in P[a]):
            distinct = False
        for b in names[i + 1:]:
            if P[a] == P[b] or P[a] == [-c for c in P[b]]:
                distinct = False
    report["distinct_nonzero_forms"] = distinct

    # (c) the head is a free parameter, independent of the three inputs
    head = P["g0"]
    nz = [i for i, c in enumerate(head) if c]
    inputs = {JOINT_PARAMS.index(nm) for nm in ("s0", "x1", "x2")}
    report["head_is_free_parameter"] = (len(nz) == 1 and nz[0] not in inputs)

    # (d) every label the joint places moves with the two free parameters
    free_idx = [JOINT_PARAMS.index(nm) for nm in ("y", "u1")]
    placed_names = [nm for nm, kd in zip(JOINT_LABELS, JOINT_KINDS)
                    if kd != "input"]
    report["labels_placed"] = placed_names
    report["labels_determined_by_the_inputs"] = [
        nm for nm in placed_names if all(P[nm][i] == 0 for i in free_idx)]
    report["every_placed_label_moves"] = not report[
        "labels_determined_by_the_inputs"]

    # (e) an integer point of the family: P = O numerically, all nine distinct
    vals = [JOINT_WITNESS_PARAMS[p] for p in JOINT_PARAMS]
    got = {nm: sum(c * x for c, x in zip(JOINT_COEFFS[nm], vals))
           for nm in names}
    num = [sum(int(c) * got[nm] for c, nm in zip(vec, names)) for vec in outs]
    report["point"] = dict(got)
    report["point_P_eq_O"] = sorted(num) == sorted(got[nm] for nm in names)
    report["point_distinct_nonzero"] = (
        len(set(got.values())) == len(names) and 0 not in got.values())

    # (f) cross-checks against the two data files
    report["families_file"] = _check_families_file()
    report["twoinput_reset_json"] = _check_recorded_witness(outs, out_names,
                                                            names)

    report["ok"] = bool(
        report["symbolic_P_eq_O"] and report["bijection_is_a_permutation"]
        and report["distinct_nonzero_forms"] and report["head_is_free_parameter"]
        and report["every_placed_label_moves"]
        and report["point_P_eq_O"] and report["point_distinct_nonzero"]
        and report["families_file"] is not False
        and report["twoinput_reset_json"] is not False)
    return report


def _check_families_file():
    """The chosen bijection and table appear in the enumeration file."""
    try:
        with open(FAMILIES_PATH) as fh:
            doc = json.load(fh)
    except (OSError, ValueError):
        return None
    for e in doc.get("families") or []:
        if e.get("bijection") != JOINT_BIJECTION:
            continue
        tbl = e.get("coefficients_by_label") or {}
        same = all([str(x) for x in JOINT_COEFFS[nm]] == tbl.get(nm)
                   for nm in JOINT_LABELS)
        return {"found": True, "table_agrees": same,
                "n_moving": e.get("n_moving"),
                "dimension": e.get("dimension"),
                "ranked_first": (doc["families"][0].get("bijection")
                                 == JOINT_BIJECTION)} if same else False
    return False


def _check_recorded_witness(outs, out_names, names):
    """``data/twoinput_reset.json``'s own family is a P = O family too.

    A different bijection from the one used here, so this only checks that the
    two agree about the topology: same labels in the same order, and its
    recorded integer point satisfies its own bijection under our output rule.
    """
    try:
        with open(WITNESS_PATH) as fh:
            w = json.load(fh)
    except (OSError, ValueError):
        return None
    if w.get("labels") != names:
        return False
    pt = {k: int(v) for k, v in (w.get("integer_point") or {}).items()}
    if sorted(pt) != sorted(names):
        return False
    ok = True
    for oname, vec in zip(out_names, outs):
        total = sum(int(c) * pt[nm] for c, nm in zip(vec, names))
        if total != pt[w["bijection"][oname]]:
            ok = False
    return {"labels_agree": True, "its_P_eq_O": ok,
            "is_the_family_used": w.get("bijection") == JOINT_BIJECTION}


_VERIFIED = verify_family()
if not _VERIFIED["ok"]:                          # never observed
    raise AssertionError(f"the lem:reset joint family is wrong: {_VERIFIED}")


# ==========================================================================
# 3.  Labels the pinned inputs determine outright
# ==========================================================================
#
# Three of the joint's six new labels have zero coefficient in both free
# parameters:
#
#     g1 = -(x1 + x2),  r0a0x0 = (x1 + x2) - s0,  r0a0x1 = s0 - 2(x1 + x2)
#
# so the joint cannot search for them: the heads of its three input children,
# chosen earlier, fix them.  The same is true of every label of a SINGLE
# (unjoined) reset row, whose rigid family is (-x1-x2; -x2, -x1; x1, x2) --
# the row an odd chain leaves at its top.
#
# The manuscript's parameter-choice rule covers exactly this: "we charge every
# admissibility requirement and every reservation to the step at which the
# last nonzero coordinate of the form concerned is chosen; at that step the
# form is affine in the coordinate being chosen with nonzero slope, whereas at
# every later step it is already numeric.  Each requirement therefore excludes
# at most one value, at exactly one step."  So each determined label is
# charged to whichever of its input children is realised LAST: that child's
# own parameter search rejects the heads that would make the label
# inadmissible, and the value is then RESERVED until the row (or joint) that
# places it arrives and releases it.  Without the charge nothing stops a later
# cell from taking the value, and the joint has no freedom left to dodge it.


def determined_labels(fam, input_names: Sequence[str]):
    """``[(label, deps, {input: coefficient})]`` for the labels of ``fam``
    that the pinned inputs determine outright (zero coefficient in every
    other parameter).  The coefficient is of the input's HEAD VALUE, so the
    family's denominator has already been divided out."""
    pidx = {}
    for nm in input_names:
        spec = ftc.Realiser.single_parameter(fam, nm)
        if spec is None:
            return []
        pidx[nm] = spec
    used = {i for i, _c in pidx.values()}
    if len(used) != len(pidx):
        return []
    out = []
    for lb in fam.labels:
        if lb.kind == "input" or not lb.physical:
            continue
        if any(c for j, c in enumerate(lb.coeffs) if j not in used):
            continue                     # a free parameter moves it
        coefs = {nm: Q(lb.coeffs[i], c) for nm, (i, c) in pidx.items()
                 if lb.coeffs[i]}
        if coefs:
            out.append((lb.name, frozenset(coefs), coefs))
    return out


#: labels of the joint family that the pinned inputs determine outright.
#: EMPTY for the family chosen above -- that is exactly why it was chosen.
JOINT_DETERMINED = determined_labels(JOINT_FAMILY, JOINT_FAMILY.input_labels())


# ==========================================================================
# 4.  The realiser
# ==========================================================================

class ResetJointRealiser(sk.SinkRealiser):
    """``SinkRealiser`` that realises each two-level joint as ONE cell.

    Everything else -- forced-antipode children, free tokens, sinks, blocks,
    the completion -- is inherited unchanged.  The joints come from
    ``context_scheduler.reset_joints`` applied to the plan's own schedule.
    """

    def __init__(self, plan, catalogue, rng, tries: int = 400,
                 allow_fallback: bool = True) -> None:
        super().__init__(plan, catalogue, rng, tries=tries,
                         allow_fallback=allow_fallback)
        self.joint_of: Dict[int, dict] = {}
        self.joint_lower: Set[int] = set()
        self.joints_realised: Set[int] = set()
        self.joints_skipped: List[dict] = []
        self._install_joints(cs.reset_joints(plan.sched["rows"]))
        self.group_of_owner: Dict[int, dict] = {}
        self.group_of_input: Dict[int, List[tuple]] = {}
        self._build_groups()

    # -- plan surgery ----------------------------------------------------
    def _install_joints(self, joints: Sequence[dict]) -> None:
        """Accept a joint only when its two rows really are the two rows of
        Lemma lem:reset and nothing else has claimed them."""
        for j in joints:
            u, w = int(j["upper"]), int(j["lower"])
            why = self._joint_reject(u, w)
            if why is not None:
                self.joints_skipped.append({"upper": u, "lower": w, "why": why})
                continue
            nu = self.plan.nodes[u]
            # the lower row must be kept[0]: _visit folds kept[0] when
            # fold_depth() > 1, and fold_chain_nodes() follows `retained`
            order = [w] + [c for c in nu.kept if c != w]
            roles = dict(zip(nu.kept, nu.kept_roles))
            nu.kept = order
            nu.kept_roles = [roles[c] for c in order]
            nu.retained = order[0]
            self.joint_of[u] = dict(j)
            self.joint_lower.add(w)

    def _joint_reject(self, u: int, w: int) -> Optional[str]:
        nu = self.plan.nodes.get(u)
        nw = self.plan.nodes.get(w)
        if nu is None or nw is None:
            return "vertex missing from the plan"
        if not (nu.is_owner and nw.is_owner):
            return "not both owners"
        if nu.key != cs.RESET_ROW_KEY or nw.key != cs.RESET_ROW_KEY:
            return f"context keys {nu.key} / {nw.key}"
        if u in self.joint_lower or w in self.joint_of:
            return "row already used by another joint"
        if self.plan.parent_core(w) != u:
            return "the lower row is not a core child of the upper one"
        if w not in nu.kept or len(nu.kept) != 2 or len(nw.kept) != 2:
            return "the rows do not keep exactly two active children"
        if len(nu.arms) != 1 or len(nw.arms) != 1:
            return "a row does not have exactly one residual arm"
        if nu.recruited or nw.recruited or nu.ports or nw.ports:
            return "a row has ports"
        for x in (u, w):
            if (self.choice.get(x) or {}).get("fa_case") in ("b", "c"):
                return "a row was joined with a forced-antipode child"
        return None

    # -- input-determined labels (section 3) ------------------------------
    def _add_group(self, owner: int, roles: Dict[str, int], spec) -> None:
        if not spec:
            return
        g = {"owner": owner, "roles": dict(roles), "spec": list(spec)}
        self.group_of_owner[owner] = g
        for role, child in roles.items():
            self.group_of_input.setdefault(child, []).append((g, role))

    def _build_groups(self) -> None:
        """One group per joint and per SINGLE (unjoined) reset row."""
        for u, j in self.joint_of.items():
            lower = self.plan.nodes[int(j["lower"])]
            up_in = [c for c in self.plan.nodes[u].kept if c != lower.vertex]
            self._add_group(u, {"s0": up_in[0], "x1": lower.kept[0],
                                "x2": lower.kept[1]},
                            determined_labels(JOINT_FAMILY,
                                              JOINT_FAMILY.input_labels()))
        for v, nd in sorted(self.plan.nodes.items()):
            if v in self.joint_of or v in self.joint_lower:
                continue
            if not nd.is_owner or nd.key != cs.RESET_ROW_KEY:
                continue
            rec = self.choice.get(v)
            if rec is None:
                continue
            fam = rec["family"]
            try:
                inames = list(fam.input_labels())
            except AttributeError:
                continue
            if len(inames) != len(nd.kept):
                continue
            self._add_group(v, dict(zip(inames, nd.kept)),
                            determined_labels(fam, inames))

    def _group_values(self, g: dict, role: Optional[str] = None,
                      value: Optional[LinForm] = None) -> Dict[str, Q]:
        """The group's determined labels that are known now (with ``role``'s
        head replaced by the candidate ``value``)."""
        heads: Dict[str, Q] = {}
        for r, c in g["roles"].items():
            hv = value if r == role else self.plan.nodes[c].head_value
            if hv is not None and hv.is_num:
                heads[r] = hv.c
        out: Dict[str, Q] = {}
        for name, deps, coefs in g["spec"]:
            if all(d in heads for d in deps):
                out[name] = sum(co * heads[r] for r, co in coefs.items())
        return out

    def cell_ok(self, node, fam, labs, key) -> bool:
        """Also refuse a head that makes a determined label inadmissible."""
        if not super().cell_ok(node, fam, labs, key):
            return False
        entries = self.group_of_input.get(node.vertex)
        if not entries:
            return True
        head_name = fam.head_label()
        head = labs.get(head_name) if head_name else None
        if head is None or not head.is_num:
            return True
        own = {f.c for f in labs.values() if f.is_num}
        for g, role in entries:
            before = self._group_values(g)
            after = self._group_values(g, role, head)
            new = [val for nm, val in after.items() if nm not in before]
            if len(set(new)) != len(new):
                return False
            for val in new:
                if val in own or self.admissible(val) is not None:
                    return False
        return True

    def finish_cell(self, node, fam, key, trial, labs, struct, chain_nodes,
                    assign) -> None:
        """Reserve the determined labels this cell's head has just fixed."""
        super().finish_cell(node, fam, key, trial, labs, struct, chain_nodes,
                            assign)
        for g, _role in self.group_of_input.get(node.vertex, ()):
            for _nm, val in self._group_values(g).items():
                self.reserved.add(val)

    def _release_group(self, v: int) -> None:
        """The row (or joint) that places the labels releases their charge."""
        g = self.group_of_owner.get(v)
        if g is None:
            return
        vals = set(self._group_values(g).values())
        if vals:
            self.reserved -= vals
            self.sink_counters["reset_charges_released"] += len(vals)

    # -- hooks -----------------------------------------------------------
    def fold_depth(self, node) -> int:
        """A joint's upper row folds its lower row in (two rows, one cell)."""
        if node.vertex in self.joint_of:
            return 2
        return super().fold_depth(node)

    def realise_cell(self, node, forced_head) -> None:
        self._release_group(node.vertex)
        joint = self.joint_of.get(node.vertex)
        if joint is None:
            return super().realise_cell(node, forced_head)
        self._release_joint_reservations(node, joint)
        return self._realise_reset_joint(node, joint, forced_head)

    def run(self) -> None:
        super().run()
        self.notes.append(
            f"{JOINT_NOTE}{len(self.joints_realised)} "
            f"of {len(self.joint_of)} planned"
            + (f"; skipped {len(self.joints_skipped)}"
               if self.joints_skipped else ""))
        self.counters["reset_joints_realised"] = len(self.joints_realised)
        self.counters["reset_joints_planned"] = len(self.joint_of)

    # -- the joint cell ---------------------------------------------------
    def _release_joint_reservations(self, node, joint: dict) -> None:
        """The joint is the designated consumer of BOTH rows' reservations.

        ``SinkRealiser.realise_cell`` releases the reservations booked against
        the cell's own family by its kept children; the joint additionally
        owns the lower row's, since the lower row no longer places a cell of
        its own.  (For the rigid ``h0_1_p0_act2`` families this set is empty,
        because they carry no ``forced_forms``, but the release must not
        depend on that.)
        """
        freed = set()
        for v in (node.vertex, int(joint["lower"])):
            nd = self.plan.nodes[v]
            rec = self.choice.get(v)
            if rec is None:
                continue
            heads = [self.plan.nodes[c].head_value for c in nd.kept]
            heads = [h.c for h in heads if h is not None and h.is_num]
            if not heads:
                continue
            for entry in (rec.get("menu") or [rec]):
                for q in ftc.Realiser.forced_ratios(entry["family"]):
                    for h in heads:
                        freed.add(q * h)
        if freed:
            self.reserved -= freed
            self.sink_counters["reservations_released"] += len(freed)

    def _realise_reset_joint(self, node, joint: dict,
                             forced_head: Optional[LinForm]) -> None:
        v = node.vertex
        lower = self.plan.nodes[int(joint["lower"])]
        fam = JOINT_FAMILY
        key = fam.key
        struct = fam.structure()
        chain_nodes = [node, lower]
        if node.retained != lower.vertex:
            raise Failure("cell", "the joint's lower row is not retained",
                          vertex=v, context=key)
        assign = ftc.match_slots([1], [a.reduced for a in node.arms])
        if assign is None:
            raise Failure("cell", "the upper row's arm does not reduce to 1",
                          vertex=v, context=key)
        for target in (node, lower):
            for a in target.arms:
                extra = a.raw_length - a.reduced
                if extra < 0 or extra % 6:
                    raise Failure("faithful",
                                  f"arm {a.raw_length} does not reduce",
                                  vertex=target.vertex, context=key)
                a.mothers = extra // 6

        # the three pinned inputs, read off the already-realised children
        up_in = [c for c in node.kept if c != lower.vertex]
        pins = {"s0": up_in[0], "x1": lower.kept[0], "x2": lower.kept[1]}
        values: List[Optional[LinForm]] = [None] * fam.d
        for nm, src in pins.items():
            xv = self.plan.nodes[src].head_value
            if xv is None or not xv.is_num:
                raise Failure("faithful",
                              f"the pinned input {nm} (child {src}) has no "
                              "numeric head", vertex=v, context=key)
            values[fam.parameters.index(nm)] = xv
        if forced_head is not None:
            values[fam.parameters.index("y")] = ftc.lin(forced_head)
        free_idx = [i for i, x in enumerate(values) if x is None]

        # Any label with zero coefficient in both free parameters would be
        # fixed outright by the pinned inputs, so no point of the enumeration
        # could rescue it: check those once, up front, rather than at each of
        # the ~57000 points.  JOINT_FAMILY is chosen so that this list is
        # EMPTY (see verify_family's "every_placed_label_moves"); the check
        # stays as a guard in case the family is ever changed.
        if JOINT_DETERMINED:
            probe = [x if x is not None else LinForm(0) for x in values]
            fixed = self.label_forms(fam, probe)
            det = [fixed[nm].c for nm, _deps, _co in JOINT_DETERMINED
                   if fixed[nm].is_num]
            bad = None
            if any(x == 0 for x in det):
                bad = "a zero label"
            elif len(set(det)) != len(det):
                bad = "two equal labels"
            else:
                for x in det:
                    if x in self.placed or x in self.reserved:
                        bad = f"{x} is already placed or reserved"
                        break
            if bad is not None:
                raise Failure("cell",
                              f"the lem:reset joint {v}+{lower.vertex} cannot "
                              f"be placed: its input-determined labels "
                              f"{[str(x) for x in det]} are inadmissible "
                              f"({bad})", vertex=v, context=key)

        def accept(vals):
            trial = list(values)
            for i, x in zip(free_idx, vals):
                trial[i] = LinForm(x)
            labs = self.label_forms(fam, trial)
            if any(f.is_num and f.c.denominator != 1 for f in labs.values()):
                return None
            if not self.cell_ok(node, fam, labs, key):
                return None
            return (trial, labs)

        got = self.sample(len(free_idx), accept) if free_idx else accept([])
        if got is None:
            raise Failure("parameters",
                          f"no admissible parameter point for the lem:reset "
                          f"joint {v}+{lower.vertex}", vertex=v, context=key)
        trial, labs = got
        self.finish_cell(node, fam, key, trial, labs, struct, chain_nodes,
                         assign)
        lower.family = fam
        lower.labels = dict(node.labels)
        self.joints_realised.add(v)
        self.counters["reset_joint_cells"] += 1


# ==========================================================================
# 4.  Driving construct_sink with the joint realiser
# ==========================================================================

def construct_reset(parent_in: Sequence[int], catalogue=None, seed: int = 0,
                    tries: int = 800, block_time: float = 20.0,
                    root_candidates: int = 4, restarts: int = 2) -> dict:
    """``sink_constructor.construct_sink`` with the joint realiser installed.

    The swap of the module-level name is scoped to this call and restored
    immediately, exactly like ``sink_constructor``'s own ``complete_blocks``
    swap, so no other mode ever sees it.
    """
    saved = sk.SinkRealiser
    sk.SinkRealiser = ResetJointRealiser
    try:
        return sk.construct_sink(parent_in, catalogue=catalogue, seed=seed,
                                 tries=tries, block_time=block_time,
                                 root_candidates=root_candidates,
                                 restarts=restarts)
    finally:
        sk.SinkRealiser = saved


def joints_used(cert: dict) -> int:
    """The number of joints the successful certificate realised."""
    for note in cert.get("notes") or []:
        if note.startswith(JOINT_NOTE):
            try:
                return int(note[len(JOINT_NOTE):].split("of")[0].strip())
            except (IndexError, ValueError):
                return -1
    return 0


def summarise(cert: dict) -> dict:
    row = sk.summarise(cert)
    row["reset_joints"] = joints_used(cert)
    return row


def run_one(name: str, par: Sequence[int], catalogue, args, mode: str) -> dict:
    t0 = time.time()
    fn = construct_reset if mode == "reset" else sk.construct_sink
    cert = fn(par, catalogue=catalogue, seed=args.seed, tries=args.tries,
              block_time=args.block_time, root_candidates=args.roots)
    cert["tree"] = name
    cert["seconds"] = round(time.time() - t0, 2)
    if args.outdir:
        os.makedirs(args.outdir, exist_ok=True)
        with open(os.path.join(args.outdir, f"cert_{mode}_{name}.json"),
                  "w") as fh:
            json.dump(cert, fh)
    row = summarise(cert)
    row["tree"] = name
    row["mode"] = mode
    row["seconds"] = cert["seconds"]
    row["verified"] = bool((cert.get("verification") or {}).get("ok"))
    print(f"  {mode:5s} {name:22s} n={row['n'] or 0:5d} D={row['D'] or 0:4d} "
          f"joints={row['reset_joints']:2d} ok={row['ok']} "
          f"verify={row['verified']} "
          f"mag/(D+1)={(row['magnitude_over_D1'] or 0):.3f} "
          f"|S|/(D+1)={(row['support_over_D1'] or 0):.3f} "
          f"gaps={row['lemma_gaps']} ({row['seconds']}s)", flush=True)
    if not row["ok"]:
        print(f"      failure: {json.dumps(row.get('failure'))}", flush=True)
    return row


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--verify", action="store_true",
                    help="print the symbolic check of the joint family")
    ap.add_argument("--parent")
    ap.add_argument("--resetcomb", help="comma separated spine lengths")
    ap.add_argument("--bush", type=int, default=None,
                    help="root bush size (default: reset_comb.default_bush)")
    ap.add_argument("--combbush", nargs=2, type=int, metavar=("K", "BUSH"),
                    action="append")
    ap.add_argument("--combbin", nargs=2, type=int, metavar=("DEPTH", "K"),
                    action="append")
    ap.add_argument("--sparse", nargs=2, metavar=("ORDERS", "COUNT"))
    ap.add_argument("--suite", action="store_true",
                    help="the existing sink regression families: comb+bush "
                         "k=5,9; comb+binary d=7,k=5; sparse n=101,201 x3")
    ap.add_argument("--mode", default="reset", choices=("reset", "sink", "both"))
    ap.add_argument("--seed", type=int, default=20260901)
    ap.add_argument("--tries", type=int, default=800)
    ap.add_argument("--block-time", type=float, default=20.0)
    ap.add_argument("--roots", type=int, default=4)
    ap.add_argument("--kd", type=int, default=25)
    ap.add_argument("--outdir", default=None)
    ap.add_argument("--json", default=None)
    a = ap.parse_args(argv)

    if a.verify:
        print(json.dumps(verify_family(), indent=1, default=str))

    trees: List[tuple] = []
    if a.parent:
        trees.append(("parent", [int(x) for x in a.parent.split(",")]))
    if a.resetcomb:
        for k in [int(x) for x in a.resetcomb.split(",")]:
            par, _ = reset_comb(k, a.bush)
            trees.append((f"resetcomb_k{k}", par))
    for k, bush in (a.combbush or []):
        trees.append((f"combbush_k{k}_b{bush}", sk.combbush_tree(k, bush)))
    for d, k in (a.combbin or []):
        trees.append((f"combbin_d{d}_k{k}", sk.combbin_tree(d, k)))
    if a.sparse:
        orders = [int(x) for x in a.sparse[0].split(",")]
        for name, par in ftc.sparse_trees(orders, int(a.sparse[1]), 1, a.kd):
            trees.append((name, par))
    if a.suite:
        for k in (5, 9):
            trees.append((f"combbush_k{k}", sk.combbush_tree(k, 12 * k)))
        trees.append(("combbin_d7_k5", sk.combbin_tree(7, 5)))
        for name, par in ftc.sparse_trees([101, 201], 3, 1, a.kd):
            trees.append((name, par))
    if not trees:
        if not a.verify:
            ap.print_help()
            return 2
        return 0

    catalogue = ftc.load_catalogue()
    modes = ("sink", "reset") if a.mode == "both" else (a.mode,)
    rows: List[dict] = []
    for name, par in trees:
        for mode in modes:
            rows.append(run_one(name, par, catalogue, a, mode))
    ok = sum(1 for r in rows if r["ok"] and r["verified"])
    print(f"\ntotal {len(rows)} runs, ok {ok}, failed {len(rows) - ok}")
    if a.json:
        with open(a.json, "w") as fh:
            json.dump(rows, fh, indent=1)
        print(f"wrote {a.json}")
    return 0 if ok == len(rows) else 1


if __name__ == "__main__":
    sys.exit(main())
