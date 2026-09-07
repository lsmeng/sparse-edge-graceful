#!/usr/bin/env python3
r"""Sink-route realisation of the free-token constructor.

This module replaces the *symbolic carrier* mechanism of
``free_token_constructor.FaithfulRealiser`` (``emit_symbolic_token`` /
``absorb_pending`` / ``register_token``) by the **sink route**:

* a token is FREE unless its family is forced-antipode
  (``free_token_constructor.family_is_fa``).  A forced-antipode family keeps
  the existing treatment (the ``fa_case_*`` paths) for its FIRST token; its
  second token, if it has one, is an ordinary unit and gets a sink;
* what a family owes a sink is its **units**, not its tokens.  Two token
  labels may be negatives of each other (an input ``x`` in one token and
  ``-x`` in the other is the common case), and such a pair needs no sink at
  all: negating it would place ``x`` and ``-x`` a second time.  Removing every
  antipodal pair of forms from the multiset of token labels leaves six labels
  (two triples), three (one triple), four (one zero-sum QUAD), or two/zero
  (nothing to do).  ``family_units`` reads this off the coefficient vectors;
* every unit's values are chosen numerically together with the rest of its
  cell (the ordinary ``numeric_cell`` path), and the NEGATIVES of the unit are
  placed at a **sink** in the ordinary part of the tree:

  1. DIRECT sink -- an ordinary block of size ``r = 3`` or ``r >= 5`` receives
     ``-a, -b, -c`` as prescribed members; the block stays zero-sum and its
     remainder ``r - 3`` is ``0`` or ``>= 2``.  A block may take several
     triples while the remainder stays admissible (``capacity`` below, imported
     from :mod:`packing_statistics`).
  2. ABSORBER -- two free tokens ``T = (a, b, -a-b)`` and ``U = (c, d, -c-d)``
     are placed on a vertical path ``v0 > v1 > v2 > v3 > v4`` of five plain
     stationary vertices with block size 2 or 4::

         e(v0 v1) =  a+b+d      e(v0 w0)  = -a-b-d
         e(v1 v2) =  a          e(v1 w1)  = -c-d
         e(v2 v3) =  b          e(v2 w2)  =  d
         e(v3 v4) =  2a+b-c     e(v3 w3)  =  c-2a-b
         e(v4 w4) =  c          e(v4 w4') = -a-b

     ``v0`` and ``v3`` stay stationary (their special children sum to zero);
     ``v1, v2, v4`` become non-stationary with sums ``2a+b-c``, ``a+b+d``, ``a``
     -- a 3-cycle of the labels on their own parent edges -- so the global
     "vertex sum = parent label" bijection survives.  The sign convention is
     that a cell whose token values are ``(t1, t2, t3)`` contributes
     ``a = -t1, b = -t2`` (hence ``-a-b = -t3``): the absorber's ``T`` is the
     negated cell token.
  3. an odd number of free triples leaves one over; it goes to a direct sink
     (an odd ordinary block of size >= 3 is exactly the ``r = 3`` /
     ``r >= 5`` odd case of rule 1).
  4. a QUAD ``Q = (q1, q2, q3, q4)``, ``q4 = -q1-q2-q3``, goes either to a
     direct block of size ``r = 4`` or ``r >= 6`` (remainder ``r - 4`` is
     ``0`` or ``>= 2``), or to a QUAD GADGET on a vertical path
     ``v0 > v1 > v2 > v3`` of four stationary vertices with the same
     eligibility as the absorber's::

         e(v0 v1) =  f - q1 - q2      e(v0 w0)  = -(f - q1 - q2)
         e(v1 v2) =  q1               e(v1 w1)  =  q2
         e(v2 v3) =  f                e(v2 w2)  = -f
         e(v3 w3) =  q3               e(v3 w3') =  q4

     with ``f`` a FRESH integer parameter chosen at filling time (like a
     head: nonzero, admissible, all eight labels distinct from everything
     placed).  ``v0`` stays stationary and ``v1, v2, v3`` have sums ``f``,
     ``q1``, ``f - q1 - q2`` -- a permutation of their own parent labels, so
     the global "vertex sum = parent label" bijection survives.  A quad
     gadget may use the top four vertices of a packed five-chain (the fifth
     vertex then simply becomes one of ``v3``'s hanging children).
     Blocks may take mixtures of triples and quads as long as the remainder
     stays ``0`` or ``>= 2``.

A third rule concerns the family CHOICE rather than the sinks: when a cell's
active child is the residue-two rigid row ``(-3x/2; -x/2, -x, x/2; x)``, that
child already places ``x_P/3, 2x_P/3, -x_P/3, -2x_P/3`` for the head ``x_P``
it hands up, so the parent's family must not contain a label identically
``c * x_P`` for one of those ``c``.  ``SinkRealiser.exclude_residue2_ratios``
drops the offending menu entries before placement and records a named gap
when the menu empties.

The four absorber-only labels ``+-(a+b+d)``, ``+-(2a+b-c)`` are checked for
admissibility inside the *second* source cell's parameter search (all 36 role
orders are tried), so a colliding parameter point is rejected by the same
retry/box loop ``numeric_cell`` uses.

``free_token_lib.verify_edge_graceful`` remains the final judge.

Usage
-----
    .venv/bin/python scripts/sink_route/sink_constructor.py --parent 0,0,0,1,1,2,2
    ... --combbush 5 60          # k = 5, bush = 60
    ... --combbin 7 5            # two depth-7 binary subtrees + a 5-tooth comb
    ... --sparse 101,201 5
    ... --census 7,9,11
    ... --json OUT.json
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import os
import random
import sys
import time
from collections import Counter
from fractions import Fraction as Q
from typing import Dict, List, Optional, Sequence

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.normpath(os.path.join(HERE, ".."))
for _p in (HERE, SCRIPTS):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import free_token_constructor as ftc              # noqa: E402
import free_token_lib as ftl                      # noqa: E402
import context_scheduler as cs                    # noqa: E402
import packing_statistics as ps                   # noqa: E402  (capacity, builders)
from combbush import combbush                     # noqa: E402

LinForm = ftc.LinForm
Failure = ftc.Failure

#: the six ordered pairs (i, j), i != j, of the three token slots
ORDERED_PAIRS = list(itertools.permutations(range(3), 2))


# ==========================================================================
# 1.  Structure of the ordinary part (blocks, chains) read off the Plan
# ==========================================================================

def core_postorder(plan: "ftc.Plan") -> List[int]:
    """Post-order of the core tree (children before parents)."""
    out: List[int] = []
    stack = [(plan.root, False)]
    while stack:
        v, done = stack.pop()
        if done:
            out.append(v)
            continue
        stack.append((v, True))
        for c in plan.children_of(v):
            stack.append((c, False))
    if len(out) != len(plan.nodes):          # defensive: never observed
        seen = set(out)
        out.extend(v for v in sorted(plan.nodes) if v not in seen)
    return out


def plain_stationary(plan: "ftc.Plan", v: int) -> bool:
    """A stationary vertex whose whole child set is an ordinary block.

    Not an owner, not folded into a macro, not a helper (no active head to
    absorb, no absorption record), no arms / neutral units / head rows of its
    own, and a port child of its parent -- so it is not on an arm, a head chain
    or a unit, and its ``ordinary`` list can no longer change during
    realisation.
    """
    nd = plan.nodes.get(v)
    if nd is None or v == plan.root:
        return False
    if nd.is_owner or nd.folded or nd.passthrough:
        return False
    if nd.arms or nd.units or nd.active or nd.kept or nd.cancelled:
        return False
    if nd.absorption is not None or nd.retained is not None:
        return False
    if nd.recruited:
        return False
    p = plan.parent_core(v)
    if p is None or v not in plan.nodes[p].ports:
        return False
    return True


def stable_block(plan: "ftc.Plan", v: int) -> bool:
    """The vertex's ordinary block can only shrink by its own absorption."""
    nd = plan.nodes.get(v)
    if nd is None or nd.folded or nd.passthrough:
        return False
    p = plan.parent_core(v)
    if p is not None and v not in plan.nodes[p].ports:
        return False       # an active child: its row may be folded into a macro
    return True


def block_size_hint(plan: "ftc.Plan", v: int) -> int:
    """Conservative final size of the ordinary block at ``v``."""
    nd = plan.nodes[v]
    size = len(nd.ordinary)
    info = nd.absorption or {}
    if info.get("type") == "port_block":
        size -= 2          # helper spends one port, a two-port absorption two
    return max(0, size)


def pack_chains(plan: "ftc.Plan", length: int = 5,
                exclude: Optional[set] = None) -> List[List[int]]:
    """Greedy bottom-up packing of disjoint vertical chains of usable
    vertices (plain stationary, block size 2 or 4).

    ``length`` is 5 for an absorber and 4 for a quad gadget; ``exclude``
    removes vertices already spent by a longer chain.  With the defaults the
    function is exactly the 5-chain packer of the first version.
    """
    banned = exclude or set()
    eligible = {v for v in plan.nodes
                if plain_stationary(plan, v)
                and len(plan.nodes[v].ordinary) in (2, 4)
                and v not in banned}
    chain_len: Dict[int, int] = {}
    witness: Dict[int, Optional[int]] = {}
    used: set = set()
    chains: List[List[int]] = []
    for v in core_postorder(plan):
        if v not in eligible:
            chain_len[v] = 0
            continue
        best, bc = 0, None
        for c in plan.nodes[v].ordinary:
            if c in eligible and c not in used and chain_len.get(c, 0) > best:
                best, bc = chain_len[c], c
        chain_len[v] = 1 + best
        witness[v] = bc
        if chain_len[v] >= length:
            seq = [v]
            cur = v
            for _ in range(length - 1):
                cur = witness[cur]
                seq.append(cur)
            for u in seq:
                used.add(u)
                chain_len[u] = 0
            chains.append(seq)
    return chains


def chain_slots(plan: "ftc.Plan", seq: Sequence[int]) -> Optional[dict]:
    """Pick the hanging children of a 5-chain ``[v0, ..., v4]``."""
    v0, v1, v2, v3, v4 = seq
    hang: List[int] = []
    for vi, path_child in ((v0, v1), (v1, v2), (v2, v3), (v3, v4)):
        rest = [c for c in plan.nodes[vi].ordinary if c != path_child]
        if not rest:
            return None
        hang.append(rest[0])
    tail = list(plan.nodes[v4].ordinary)
    if len(tail) < 2:
        return None
    w4, w4p = tail[0], tail[1]
    # every chain vertex spends two of its children; the rest must be 0 or >= 2
    for vi in seq:
        left = len(plan.nodes[vi].ordinary) - 2
        if left != 0 and left < 2:
            return None
    return {"chain": list(seq), "hang": hang, "w4": w4, "w4p": w4p,
            "edges": {"v0v1": v1, "v0w0": hang[0], "v1v2": v2,
                      "v1w1": hang[1], "v2v3": v3, "v2w2": hang[2],
                      "v3v4": v4, "v3w3": hang[3], "v4w4": w4,
                      "v4w4p": w4p}}


def quad_slots(plan: "ftc.Plan", seq: Sequence[int]) -> Optional[dict]:
    """Pick the hanging children of a quad gadget ``[v0, v1, v2, v3]``.

    ``seq`` may be longer (the top four vertices of a packed five-chain are a
    legal quad gadget); the fifth vertex is *not* spent -- it simply becomes
    one of the two hanging children of ``v3``, and stays stationary because
    its own ordinary block is still zero-sum.
    """
    if len(seq) < 4:
        return None
    v0, v1, v2, v3 = seq[:4]
    hang: List[int] = []
    for vi, path_child in ((v0, v1), (v1, v2), (v2, v3)):
        rest = [c for c in plan.nodes[vi].ordinary if c != path_child]
        if not rest:
            return None
        hang.append(rest[0])
    tail = list(plan.nodes[v3].ordinary)
    if len(tail) < 2:
        return None
    w3, w3p = tail[0], tail[1]
    for vi in (v0, v1, v2, v3):
        left = len(plan.nodes[vi].ordinary) - 2
        if left != 0 and left < 2:
            return None
    return {"chain": [v0, v1, v2, v3], "hang": hang, "w3": w3, "w3p": w3p,
            "edges": {"v0v1": v1, "v0w0": hang[0], "v1v2": v2,
                      "v1w1": hang[1], "v2v3": v3, "v2w2": hang[2],
                      "v3w3": w3, "v3w3p": w3p}}


def block_takes(r: int, s: int) -> bool:
    """A block of ``r`` free edges can host a unit of ``s`` prescribed members
    when the remainder is ``0`` or ``>= 2``."""
    return r >= s and (r - s == 0 or r - s >= 2)


def greedy_direct_fit(caps: Sequence[int], sizes: Sequence[int]) -> bool:
    """Can the blocks of sizes ``caps`` host units of sizes ``sizes``?

    First fit, largest unit first, exactly what :func:`place_sinks` does, so
    a plan that passes here is a plan the placement can carry out.  For an
    all-triple demand this reproduces :func:`packing_statistics.capacity`.
    """
    free = sorted(caps, reverse=True)
    for s in sorted(sizes, reverse=True):
        hit = None
        for i, r in enumerate(free):
            if block_takes(r, s):
                hit = i
                break
        if hit is None:
            return False
        free[hit] -= s
        free.sort(reverse=True)
    return True


def direct_capacity(plan: "ftc.Plan", forbidden: set) -> int:
    """Number of triples the stable ordinary blocks can host."""
    total = 0
    for v in plan.nodes:
        if v in forbidden or not stable_block(plan, v):
            continue
        total += ps.capacity(block_size_hint(plan, v))
    return total


def direct_block_sizes(plan: "ftc.Plan", forbidden: set) -> List[int]:
    """Sizes of the stable ordinary blocks a direct sink may use."""
    return [block_size_hint(plan, v) for v in plan.nodes
            if v not in forbidden and stable_block(plan, v)]


# ==========================================================================
# 1b.  UNITS -- what a family really has to send to a sink
# ==========================================================================
#
# A family's tokens are zero-sum triples, but two token labels may be
# NEGATIVES of each other (an input ``x`` in one token and ``-x`` in the
# other is the common case, e.g. ``h1_3_p0_act``).  Negating such a pair
# places ``x`` and ``-x`` a second time, so no parameter point is ever
# admissible.  The forms that cancel need no sink at all; what is left is
# the family's UNITS: two triples, one triple, or one zero-sum QUAD.


def label_vector(fam, name) -> tuple:
    """The label's form as a coefficient vector over the family parameters."""
    lab = fam.by_name[name]
    L = getattr(fam, "L", 1) or 1
    return tuple(Q(c, L) for c in lab.coeffs)


def token_form_list(fam) -> List[tuple]:
    """``[(token index, label name, coefficient vector), ...]``."""
    out: List[tuple] = []
    toks = []
    try:
        first = fam.token_labels()
    except Exception:
        first = None
    if first:
        toks.append(first)
    second = ftc.family_two_tokens(fam)
    if second:
        toks.append(second)
    for ti, tk in enumerate(toks):
        for r in "abc":
            nm = tk.get(r)
            if nm is None or nm not in getattr(fam, "by_name", {}):
                return []
            out.append((ti, nm, label_vector(fam, nm)))
    return out


def antipodal_reduce(items: Sequence[tuple]):
    """Remove every antipodal pair of forms (pairs may straddle the tokens)."""
    n = len(items)
    used = [False] * n
    pairs: List[tuple] = []
    for i in range(n):
        if used[i]:
            continue
        for j in range(i + 1, n):
            if used[j]:
                continue
            if all(a + b == 0 for a, b in zip(items[i][2], items[j][2])):
                used[i] = used[j] = True
                pairs.append((items[i][1], items[j][1]))
                break
    return [items[i] for i in range(n) if not used[i]], pairs


def _zero_sum(items: Sequence[tuple]) -> bool:
    if not items:
        return True
    width = len(items[0][2])
    return all(sum(it[2][k] for it in items) == 0 for k in range(width))


def family_units(fam) -> dict:
    """The family's units, read off the coefficient vectors.

    ``{"units": [{"names": [...], "size": 3 | 4, "tokens": [...]}, ...],
       "pairs": [(name, name), ...], "fa": bool, "fallback": bool,
       "dropped": int}``

    A remainder of six forms is the two intact tokens, three is one triple,
    four is one QUAD, and two or zero needs no sink at all.  For a
    forced-antipode family the FIRST token keeps the existing ``a = -b``
    treatment with the parent, so only the units that live entirely inside
    the SECOND token are sunk; if the antipodal reduction mixes the two
    tokens, ``fallback`` asks the caller for the pre-existing route.
    """
    fa = ftc.family_is_fa(fam)
    items = token_form_list(fam)
    if not items:
        return {"units": [], "pairs": [], "fa": fa, "fallback": False,
                "dropped": 0}
    rest, pairs = antipodal_reduce(items)
    groups: List[List[tuple]] = []
    if len(rest) == 6:
        groups = [rest[:3], rest[3:]]
    elif len(rest) in (3, 4):
        groups = [rest]
    elif len(rest) in (0, 1, 2):
        groups = []
    else:                                    # never observed
        return {"units": [], "pairs": pairs, "fa": fa, "fallback": True,
                "dropped": 0}
    units = []
    dropped = 0
    fallback = False
    for grp in groups:
        if not _zero_sum(grp):               # never observed
            fallback = True
            continue
        if fa and any(it[0] != 1 for it in grp):
            dropped += 1                     # the first token's own business
            continue
        units.append({"names": [it[1] for it in grp], "size": len(grp),
                      "tokens": sorted({it[0] for it in grp})})
    if fa and dropped and not units:
        fallback = True                      # nothing clean to sink
    return {"units": units, "pairs": pairs, "fa": fa, "fallback": fallback,
            "dropped": dropped}


# ==========================================================================
# 1c.  Residue-two rigid rows below an owner
# ==========================================================================

#: the residue-two rigid row places ``x_P/3, 2x_P/3, -x_P/3, -2x_P/3`` for the
#: head ``x_P`` it exposes, so a parent whose input is that head must not
#: place ``c * x_P`` for any of these ``c``
RESIDUE2_RATIOS = frozenset({Q(1, 3), Q(2, 3), Q(-1, 3), Q(-2, 3)})


def head_ratio(fam, name) -> Optional[Q]:
    """``q`` when the label is identically ``q *`` the exposed head."""
    hn = fam.head_label()
    if hn is None or name == hn:
        return None
    hv = fam.by_name[hn].coeffs
    if not any(hv):
        return None
    q = None
    for a, b in zip(fam.by_name[name].coeffs, hv):
        if b == 0:
            if a:
                return None
            continue
        r = Q(a, b)
        if q is None:
            q = r
        elif q != r:
            return None
    return q


def is_residue2_rigid_row(fam) -> bool:
    """The child is the residue-two rigid row ``(-3x/2; -x/2, -x, x/2; x)``.

    Every physical label except the head and the pinned inputs is a forced
    third of the head, and the ratios are the rigid row's.
    """
    hn = fam.head_label()
    if hn is None:
        return False
    try:
        inputs = set(fam.input_labels())
    except AttributeError:
        inputs = {fam.input_label()} - {None}
    ratios = set()
    for lb in fam.labels:
        if lb.name == hn or lb.name in inputs or not lb.physical:
            continue
        q = head_ratio(fam, lb.name)
        if q is None or q not in RESIDUE2_RATIOS:
            return False
        ratios.add(q)
    return len(ratios) >= 2


def input_ratio_labels(fam, pos: int) -> set:
    """Ratios ``q`` such that the family places ``q * x`` for input ``pos``."""
    try:
        names = list(fam.input_labels())
    except AttributeError:
        one = fam.input_label()
        names = [one] if one else []
    if pos >= len(names):
        return set()
    spec = ftc.Realiser.single_parameter(fam, names[pos])
    if spec is None:
        return set()
    i, c = spec
    out = set()
    for lb in fam.labels:
        if lb.name == names[pos] or not lb.physical:
            continue
        if any(x for j, x in enumerate(lb.coeffs) if j != i):
            continue
        if lb.coeffs[i]:
            out.add(Q(lb.coeffs[i], c))
    return out


def fold_chain_vertices(plan: "ftc.Plan", v: int, rows: int) -> List[int]:
    """``fold_chain_nodes`` without a realiser (the plan already knows)."""
    out = [v]
    cur = plan.nodes[v]
    while len(out) < rows and cur.retained is not None:
        cur = plan.nodes[cur.retained]
        out.append(cur.vertex)
    return out


# ==========================================================================
# 2.  The sink plan (which token goes where), fixed before realisation
# ==========================================================================

#: slot number of the token a two-port absorption emits at a helper vertex
TWO_PORT_SLOT = -1

#: slot numbers of the free zero-sum triples that cancel an odd number of
#: active heads at a vertex (Section 3 of the manuscript).  Group ``gi`` at a
#: vertex gets slot ``CANCEL_SLOT_BASE - gi``.  Like the two-port token these
#: are triples that always go to a DIRECT sink, never to an absorber: their
#: three labels are the heads of three different children, so they are not
#: labels of one cell and the absorber gate does not cover them.
CANCEL_SLOT_BASE = -1000


def cancel_triples(plan: "ftc.Plan") -> List[tuple]:
    """``[(vertex, slot), ...]`` for every cancelled group of three.

    A group of two is a mirror pair, closed under negation and owing no sink;
    a group of three is a free zero-sum triple and owes one.
    """
    out = []
    for v in sorted(plan.nodes):
        node = plan.nodes[v]
        for gi, group in enumerate(getattr(node, "cancelled", []) or []):
            if len(group) == 3:
                out.append((v, CANCEL_SLOT_BASE - gi))
    return out


def folded_owner(plan: "ftc.Plan", choice: dict, v: int) -> bool:
    """``v``'s own cell never runs: its parent's macro folds it in.

    ``FaithfulRealiser._visit`` folds ``kept[0]`` whenever the parent's family
    has more than one row (an ``A2`` joint, an ``L1`` letter), and a
    passthrough child is always folded.  Such an owner places no labels of its
    own, so it owes no sink.
    """
    node = plan.nodes.get(v)
    if node is None:
        return False
    if node.folded or node.passthrough is not None:
        return True
    u = plan.parent_core(v)
    pnode = plan.nodes.get(u) if u is not None else None
    if pnode is None or not pnode.kept or pnode.kept[0] != v:
        return False
    prec = choice.get(u)
    if prec is None:
        return False
    try:
        return len(prec["family"].structure()) > 1
    except Exception:
        return False


def free_token_slots(plan: "ftc.Plan", choice: dict) -> tuple:
    """``([(owner vertex, unit slot), ...], [(helper vertex, -1), ...], sizes)``.

    The slots are the *units* of :func:`family_units`, not the raw tokens: a
    family whose two tokens share an antipodal pair of forms has one quad (or
    nothing) to sink rather than two triples.  A forced-antipode family keeps
    the existing treatment of its FIRST token and contributes its SECOND one
    here.

    The second list is the tokens ``{x, a, -x-a}`` a *two-port* absorption
    emits at a stationary helper with exactly two ports (ROUTE_CORE section 4
    case 2).  They are free tokens too, and the sink route sends their
    negatives to a direct sink instead of the pending queue.
    """
    owner_units = []
    two_port = []
    sizes: Dict[tuple, int] = {}
    for key in cancel_triples(plan):
        two_port.append(key)
        sizes[key] = 3
    for v in core_postorder(plan):
        node = plan.nodes.get(v)
        if node is None:
            continue
        if node.is_owner:
            rec = choice.get(v)
            if rec is None or folded_owner(plan, choice, v):
                continue
            info = family_units(rec["family"])
            if info["fallback"]:
                continue                   # the pre-existing route takes over
            for slot, unit in enumerate(info["units"]):
                owner_units.append((v, slot))
                sizes[(v, slot)] = unit["size"]
            continue
        info2 = node.absorption or {}
        if (info2.get("type") == "port_block" and node.retained is not None
                and len(node.ports) == 2):
            two_port.append((v, TWO_PORT_SLOT))
            sizes[(v, TWO_PORT_SLOT)] = 3
    return owner_units, two_port, sizes


def build_sink_plan(plan: "ftc.Plan", choice: dict) -> dict:
    """Pair the free units and allocate direct sinks / absorbers / gadgets.

    Triples go to a direct block, or in pairs to a five-vertex absorber;
    quads go to a direct block of size ``4`` or ``>= 6``, or to a four-vertex
    quad gadget.  A quad gadget may take the top four vertices of a packed
    five-chain, so the absorbers are allocated first and the spare chains are
    offered to the quads.
    """
    units, two_port, sizes = free_token_slots(plan, choice)
    triples = [k for k in units if sizes[k] == 3]
    quads = [k for k in units if sizes[k] == 4]

    chains5 = pack_chains(plan, 5)
    absorbers = []
    for seq in chains5:
        slots = chain_slots(plan, seq)
        if slots is not None:
            absorbers.append(slots)
    spent5 = {v for seq in chains5 for v in seq}
    quad_pool4 = []
    for seq in pack_chains(plan, 4, exclude=spent5):
        slots = quad_slots(plan, seq)
        if slots is not None:
            quad_pool4.append(slots)

    picked = None
    for n_abs in range(0, min(len(absorbers), len(triples) // 2) + 1):
        spare = []
        for g in absorbers[n_abs:]:
            got = quad_slots(plan, g["chain"])
            if got is not None:
                spare.append(got)
        pool = quad_pool4 + spare
        for n_gad in range(0, min(len(pool), len(quads)) + 1):
            forbidden = set()
            for g in absorbers[:n_abs]:
                forbidden |= set(g["chain"])
            for g in pool[:n_gad]:
                forbidden |= set(g["chain"])
            demand = ([3] * len(two_port) + [3] * (len(triples) - 2 * n_abs)
                      + [4] * (len(quads) - n_gad))
            if greedy_direct_fit(direct_block_sizes(plan, forbidden), demand):
                picked = (n_abs, n_gad, pool)
                break
        if picked is not None:
            break
    if picked is None:
        cap_all = direct_capacity(plan, set())
        return {"tokens": units, "two_port": two_port, "sizes": sizes,
                "jobs": [], "ok": False, "quads": len(quads),
                "absorbers": 0, "direct": 0, "quad_gadgets": 0,
                "gadgets": len(absorbers),
                "gap": {"step": "sink_capacity",
                        "detail": f"{len(triples)} free triples, "
                                  f"{len(quads)} quads and "
                                  f"{len(two_port)} two-port tokens but only "
                                  f"{cap_all} direct triple slots, "
                                  f"{len(absorbers)} absorber chains and "
                                  f"{len(quad_pool4)} spare quad chains"}}
    n_abs, n_gad, pool = picked

    jobs: List[dict] = []
    assign: Dict[tuple, int] = {}
    keep_tri = len(triples) - 2 * n_abs
    keep_quad = len(quads) - n_gad
    # direct sinks first, for the earliest units in post-order
    for key in list(two_port) + list(triples[:keep_tri]) + list(quads[:keep_quad]):
        jobs.append({"kind": "direct", "slots": [key],
                     "size": sizes.get(key, 3)})
        assign[key] = len(jobs) - 1
    rest = triples[keep_tri:]
    for i in range(n_abs):
        pair = rest[2 * i:2 * i + 2]
        job = dict(absorbers[i])
        job["kind"] = "absorber"
        job["slots"] = list(pair)
        job["size"] = 3
        jobs.append(job)
        for key in pair:
            assign[key] = len(jobs) - 1
    for i, key in enumerate(quads[keep_quad:]):
        job = dict(pool[i])
        job["kind"] = "quad"
        job["slots"] = [key]
        job["size"] = 4
        jobs.append(job)
        assign[key] = len(jobs) - 1
    return {"tokens": units, "two_port": two_port, "sizes": sizes,
            "jobs": jobs, "assign": assign, "ok": True, "absorbers": n_abs,
            "quad_gadgets": n_gad, "quads": len(quads),
            "direct": keep_tri + keep_quad + len(two_port),
            "gadgets": len(absorbers), "gap": None}


# ==========================================================================
# 3.  The realiser
# ==========================================================================

class SinkRealiser(ftc.FaithfulRealiser):
    """``FaithfulRealiser`` with the sink route in place of pending tokens."""

    def __init__(self, plan, catalogue, rng, tries: int = 400,
                 allow_fallback: bool = True) -> None:
        super().__init__(plan, catalogue, rng, tries=tries,
                         allow_fallback=allow_fallback)
        self.sink_jobs: List[dict] = []
        self.sink_assign: Dict[tuple, int] = {}
        self.free_tokens: List[dict] = []
        self.sink_counters: Counter = Counter()
        self._unit_cache: Dict[int, dict] = {}
        self.exclude_residue2_ratios()

    # -- cancelling triples: their negatives owe a direct sink -------------
    def after_cancel_group(self, node, gi: int, group) -> None:
        """Register a cancelled group of three as a free unit.

        The three heads sum to zero by construction (the last is forced to the
        negative of the sum of the first two), but they are not closed under
        negation, so the sink route owes their negatives a sink exactly as it
        owes one to a token.  The three labels belong to three different
        children, not to one cell, so the pair is never sent to an absorber:
        the record carries ``absorber: None`` and ``place_sinks`` gives it a
        direct block.
        """
        if len(group) != 3:
            return None                      # a mirror pair owes nothing
        vals = []
        for u in group:
            hv = self.plan.nodes[u].head_value
            if hv is None or not hv.is_num or hv.c.denominator != 1:
                raise Failure("sink_cancel",
                              f"cancelled head at {u} is not an integer",
                              vertex=node.vertex)
            vals.append(int(hv.c))
        if sum(vals) != 0:
            raise Failure("sink_cancel", "a cancelling triple is not zero-sum",
                          vertex=node.vertex)
        negs = [LinForm(-x) for x in vals]
        if not self._try_batch(negs, f"cancelling triple at {node.vertex}"):
            raise Failure("sink_cancel",
                          "the negatives of a cancelling triple are not free",
                          vertex=node.vertex)
        self._reserve(negs, f"cancelling triple sink at {node.vertex}")
        self.free_tokens.append(
            {"vertex": node.vertex, "slot": CANCEL_SLOT_BASE - gi,
             "context": "cancel_triple", "size": 3, "values": list(vals),
             "negs": [-x for x in vals], "absorber": None})
        self.sink_counters["cancel_triples"] += 1
        return None

    # -- family choice: a residue-two rigid row below the cell --------------
    def exclude_residue2_ratios(self) -> None:
        """Drop the menu entries a residue-two rigid child makes impossible.

        The rigid row ``(-3x/2; -x/2, -x, x/2; x)`` places ``x_P/3``,
        ``2x_P/3``, ``-x_P/3`` and ``-2x_P/3`` for the head ``x_P`` it hands
        up, so a parent family with a label identically ``c * x_P`` for one of
        those ``c`` collides at every parameter point.  The collision is
        structural, so it belongs in the family choice, not in the retry loop.
        """
        plan = self.plan
        for v, node in sorted(plan.nodes.items()):
            rec = self.choice.get(v)
            if rec is None or not node.is_owner:
                continue
            menu = rec.get("menu") or [rec]
            keep = []
            hit = False
            for entry in menu:
                fam = entry["family"]
                try:
                    rows = len(fam.structure())
                except Exception:
                    rows = 1
                bottom = plan.nodes[fold_chain_vertices(plan, v, rows)[-1]]
                bad = False
                for pos, child in enumerate(bottom.kept):
                    crec = self.choice.get(child)
                    if crec is None:
                        continue
                    if not is_residue2_rigid_row(crec["family"]):
                        continue
                    if input_ratio_labels(fam, pos) & RESIDUE2_RATIOS:
                        bad = True
                        break
                if bad:
                    hit = True
                else:
                    keep.append(entry)
            if not hit:
                continue
            self.sink_counters["residue2_menu_entries_dropped"] += (
                len(menu) - len(keep))
            if not keep:
                self.gaps.append({
                    "vertex": v, "context": node.key,
                    "reason": "residue2_rigid_ratio: every family for this "
                              "context places a third of the rigid child's "
                              "head"})
                self.sink_counters["residue2_rigid_gaps"] += 1
                continue
            self.sink_counters["residue2_rigid_parents"] += 1
            rec["menu"] = keep
            rec.update({k: val for k, val in keep[0].items()
                        if k in ("key", "index", "family", "e6", "fa",
                                 "rigid_head", "case")})

    # -- units of a family, cached -----------------------------------------
    def cell_units(self, fam) -> dict:
        # the cache keeps its own reference to the family, so the key can
        # never be recycled while the entry is alive
        got = self._unit_cache.get(id(fam))
        if got is None:
            got = (fam, family_units(fam))
            self._unit_cache[id(fam)] = got
        return got[1]

    # -- ledger bookkeeping (must ride along with every snapshot) ---------
    def snapshot(self) -> dict:
        snap = super().snapshot()
        snap["free_tokens"] = [dict(t) for t in self.free_tokens]
        return snap

    def restore(self, snap: dict) -> None:
        super().restore(snap)
        self.free_tokens = [dict(t) for t in snap.get("free_tokens", [])]

    # -- the token branch --------------------------------------------------
    def emit_symbolic_token(self, node, fam, key, values, free_idx, carrier_idx,
                            tokens, struct, chain_nodes, assign) -> bool:
        """Free tokens never stay symbolic; forced-antipode ones still do."""
        if not ftc.family_is_fa(fam):
            # the caller counts a downgrade right after a False return
            self.counters["T1_downgraded_to_numeric"] -= 1
            return False
        return super().emit_symbolic_token(node, fam, key, values, free_idx,
                                           carrier_idx, tokens, struct,
                                           chain_nodes, assign)

    def absorb_pending(self, node, fam, key, values, free_idx, carrier_idx,
                       tokens, struct, chain_nodes, assign) -> bool:
        """Free tokens are never paired against a pending one."""
        if not ftc.family_is_fa(fam):
            self.counters["T2_solve_failed"] -= 1
            return False
        return super().absorb_pending(node, fam, key, values, free_idx,
                                      carrier_idx, tokens, struct,
                                      chain_nodes, assign)

    def two_port_absorbs(self, node, x, ports) -> bool:
        """Keep the unused ports of a two-port absorption as a block.

        ``FaithfulRealiser.two_port_absorbs`` sets ``node.ordinary = []``, while
        the plain two-port branch of ``realise_absorption`` keeps
        ``ports[2:]``; the sink route needs those ports, so the subclass
        restores them.  (Existing modes are untouched.)
        """
        ok = super().two_port_absorbs(node, x, ports)
        if ok:
            node.ordinary = list(ports[2:])
        return ok

    # -- helper / two-port absorption, sink flavour ------------------------
    def realise_absorption(self, node) -> None:
        """``-x`` on one port when ``q = 1`` or ``q >= 3``; the two-port
        triple only when ``q = 2``, and then as a sink token.

        ``FaithfulRealiser.realise_absorption`` takes the two-port branch for
        every ``q >= 2``, which spends a token (and, through
        ``two_port_absorbs``, the whole port block) at a helper that could
        simply carry ``-x`` and keep ``q - 1 >= 2`` ports as a zero-sum block.
        The documented rule (ROUTE_CORE section 4) is helper for ``q = 1`` or
        ``q >= 3`` and the two-port pair only for ``q = 2``; the sink route
        follows it, so the only token a helper can emit is the ``q = 2`` one,
        whose negatives get a direct sink like every other free token.
        """
        info = node.absorption
        if not info or info["type"] != "port_block" or node.retained is None:
            return super().realise_absorption(node)
        v = node.vertex
        x = self.plan.nodes[node.retained].head_value
        if x is None:
            raise Failure("faithful",
                          f"active child {node.retained} has no head", vertex=v)
        ports = list(node.ports)
        if len(ports) == 2:
            if not x.is_num or self.pending:
                return super().realise_absorption(node)

            def accept(vals):
                a = LinForm(vals[0])
                b = -x - a
                if a == b:
                    return None
                forms = [a, b]
                if any((not f.is_num) or f.c.denominator != 1 for f in forms):
                    return None
                negs = [-x, -a, -b]
                if not self._try_batch(forms + negs, f"two-port sink at {v}"):
                    return None
                return (a, b, negs)

            got = self.sample(1, accept)
            if got is None:
                raise Failure("faithful",
                              "no two-port absorption whose negatives are free",
                              vertex=v)
            a, b, negs = got
            self.commit(ports[0], a, f"two-port at {v}")
            self.commit(ports[1], b, f"two-port at {v}")
            self.close_batch([a, b])
            self._reserve(negs, f"two-port sink at {v}")
            node.ordinary = []
            info["type"] = "two_port"
            info["values"] = [int(a.c), int(b.c)]
            self.free_tokens.append(
                {"vertex": v, "slot": TWO_PORT_SLOT, "context": "two_port",
                 "size": 3, "values": [int(x.c), int(a.c), int(b.c)],
                 "negs": [int(f.c) for f in negs], "absorber": None})
            self.tokens.append({"vertex": v,
                                "values": [str(x), str(a), str(b)],
                                "paired_with": None, "sink": "direct"})
            self.sink_counters["two_port_tokens"] += 1
            return
        # q = 1 or q >= 3: a plain helper, no token at all
        helper = -x
        if helper.is_num:
            if helper.c in self.placed:
                raise Failure("faithful",
                              f"helper {helper.c} = -x is already placed",
                              vertex=v)
            self.check_batch([helper], f"helper at {v}")
        self.commit(ports[0], helper, f"helper at {v}")
        if helper.is_num:
            self.close_batch([helper])
        node.ordinary = ports[1:]
        info["type"] = "helper"
        info["port"] = ports[0]
        info["value"] = str(helper)

    #: the one- and two-parameter searches of ``FaithfulRealiser.sample`` are
    #: exhaustive enumerations in order of increasing magnitude, capped at 400
    #: magnitudes / radius 25.  The sink route makes every label numeric and
    #: adds three more per token, so the support grows about twice as fast and
    #: those caps are reached on the long comb spines (the ninth ``h0_3_p0_act``
    #: cell starves and every retry repeats the same exhausted enumeration).
    #: Raising the caps only *extends* the same ordered search: the point found
    #: is still the smallest admissible one, so magnitudes stay minimal.
    RAY_MAGNITUDES = 2000
    PLANE_RADIUS = 120

    def sample(self, count: int, accept):
        if count == 1:
            for mag in range(1, self.RAY_MAGNITUDES):
                for sgn in (1, -1):
                    got = accept([sgn * mag * self.M])
                    if got is not None:
                        return got
            return None
        if count == 2:
            for radius in range(1, self.PLANE_RADIUS):
                for a in range(-radius, radius + 1):
                    for b in range(-radius, radius + 1):
                        if max(abs(a), abs(b)) != radius or a == 0 or b == 0:
                            continue
                        got = accept([a * self.M, b * self.M])
                        if got is not None:
                            return got
            return None
        return super().sample(count, accept)

    # -- helpers -----------------------------------------------------------
    def _try_batch(self, forms, who: str) -> bool:
        try:
            self.check_batch(forms, who)
        except Failure:
            return False
        return True

    def _reserve(self, forms, who: str) -> None:
        """Book the sink values into ``placed`` without fixing their edges."""
        self.check_batch(forms, who)
        for f in forms:
            self.placed.add(f.c)
            self.max_magnitude = max(self.max_magnitude, abs(int(f.c)))
        self.close_batch(forms)

    def _jobs_for(self, vertex: int, units: Sequence[dict]
                  ) -> List[Optional[dict]]:
        """The planned job of every unit, dropped when the sizes disagree.

        The plan is made from the FIRST menu entry; a cell that falls back to
        another family may have units of different sizes, and such a unit is
        simply unplanned -- ``place_sinks`` gives it a direct block.
        """
        out: List[Optional[dict]] = []
        for slot, unit in enumerate(units):
            idx = self.sink_assign.get((vertex, slot))
            job = self.sink_jobs[idx] if idx is not None else None
            if job is not None and job.get("size", 3) != unit["size"]:
                job = None
                self.sink_counters["job_size_mismatch"] += 1
            out.append(job)
        return out

    def _partner_negs(self, job: dict, vertex: int, slot: int, local=None):
        """The negated token of the absorber's other source, if already fixed.

        ``local`` carries the tokens of the *same* cell that this parameter
        point has already fixed, which is what pairs the two tokens of a
        two-token family with each other.
        """
        local = local or {}
        for key in job["slots"]:
            if key == (vertex, slot):
                continue
            if key in local:
                return local[key]
            for rec in self.free_tokens:
                if (rec["vertex"], rec["slot"]) == key:
                    return rec["negs"]
        return None

    def _sink_probe(self, node, fam, key, labs, units, jobs):
        """Admissibility of the sink labels this parameter point implies.

        Returns ``(infos, extra_forms)`` or ``None``.  ``extra_forms`` are the
        sink labels (negated units, and the four absorber-only labels of every
        triple that closes an absorber) which must be booked on acceptance.
        The quad gadget's own parameter ``f`` is chosen at filling time, so a
        quad contributes only its four negated members here.
        """
        try:
            input_names = set(fam.input_labels())
        except AttributeError:
            input_names = {fam.input_label()} - {None}
        base = [f for nm, f in labs.items() if nm not in input_names]
        infos = []
        negs_all = []
        for slot, unit in enumerate(units):
            tv = [labs[nm] for nm in unit["names"]]
            if any((not f.is_num) or f.c.denominator != 1 for f in tv):
                return None
            if sum(int(f.c) for f in tv) != 0:
                return None                   # a unit must stay zero-sum
            negs = [-f for f in tv]
            negs_all += negs
            infos.append({"slot": slot, "size": unit["size"],
                          "names": list(unit["names"]),
                          "values": [int(f.c) for f in tv],
                          "negs": [int(f.c) for f in negs],
                          "absorber": None})
        batch = base + negs_all
        if not self._try_batch(batch, f"sink negatives at {node.vertex}"):
            return None
        extra: List[LinForm] = []
        local = {}
        for slot, _unit in enumerate(units):
            job = jobs[slot] if slot < len(jobs) else None
            if job is None or job["kind"] != "absorber":
                local[(node.vertex, slot)] = infos[slot]["negs"]
                continue
            partner = self._partner_negs(job, node.vertex, slot, local)
            local[(node.vertex, slot)] = infos[slot]["negs"]
            if partner is None:
                continue                      # this cell is the first source
            negs = infos[slot]["negs"]
            chosen = None
            for i, j in ORDERED_PAIRS:        # 36 role orders
                a, b = partner[i], partner[j]
                for k, l in ORDERED_PAIRS:
                    c, d = negs[k], negs[l]
                    f1, f3 = a + b + d, 2 * a + b - c
                    cand = [LinForm(f1), LinForm(-f1),
                            LinForm(f3), LinForm(-f3)]
                    if self._try_batch(batch + extra + cand,
                                       f"absorber forms at {node.vertex}"):
                        chosen = {"order_first": [i, j], "order_second": [k, l],
                                  "F1": f1, "F3": f3}
                        extra += cand
                        break
                if chosen:
                    break
            if chosen is None:
                return None
            infos[slot]["absorber"] = chosen
        return infos, negs_all + extra

    # -- reservations are consumable in the sink route ----------------------
    def reservation(self, node, head):
        """The second member of a cancelled pair has nothing left to reserve.

        ``FaithfulRealiser.reservation`` returns ``[-head]`` for *either*
        member of a two-element cancelled group.  For the member whose head is
        forced (the last one) that value is its partner's head, which is
        already placed, so ``cell_ok``'s ``r in self.placed`` test rejects every
        parameter point.  Again the symbolic route hides it because the
        partner's head is usually not numeric yet.
        """
        u = self.plan.parent_core(node.vertex)
        pnode = self.plan.nodes.get(u) if u is not None else None
        if pnode is not None and head is not None and head.is_num:
            for group in pnode.cancelled:
                if len(group) == 2 and node.vertex == group[-1]:
                    return []
        return super().reservation(node, head)

    def realise_cell(self, node, forced_head) -> None:
        """Release the reservations this cell is the designated consumer of.

        ``FaithfulRealiser.reservation`` books ``-x`` for the sibling of a
        two-element cancelled group and ``q*x`` for every ratio the parent's
        family forces, and ``admissible`` / ``check_batch`` then refuse *any*
        value in ``reserved`` -- including the very cell that is supposed to
        place it.  With the symbolic-carrier route those heads are usually not
        numeric yet, so the clash rarely shows; the sink route makes every head
        numeric and the clash becomes systematic (a forced head is always its
        own reservation).  A reservation is a promise to a named consumer, so
        the consumer releases it on arrival.
        """
        freed = set()
        if forced_head is not None and forced_head.is_num:
            freed.add(forced_head.c)
        rec = self.choice.get(node.vertex)
        if rec is not None:
            heads = []
            for c in node.kept:
                hv = self.plan.nodes[c].head_value
                if hv is not None and hv.is_num:
                    heads.append(hv.c)
            if heads:
                fams = [e["family"] for e in (rec.get("menu") or [rec])]
                for fam in fams:
                    for q in ftc.Realiser.forced_ratios(fam):
                        for h in heads:
                            freed.add(q * h)
        if freed:
            self.reserved -= freed
            self.sink_counters["reservations_released"] += len(freed)
        return super().realise_cell(node, forced_head)

    # -- T0: everything numeric, with the sink labels checked along ---------
    def numeric_cell(self, node, fam, key, values, free_idx, tokens,
                     struct, chain_nodes, assign) -> None:
        if not tokens:
            return super().numeric_cell(node, fam, key, values, free_idx,
                                        tokens, struct, chain_nodes, assign)
        uinfo = self.cell_units(fam)
        if uinfo["fallback"]:
            self.sink_counters["unit_rule_fallback"] += 1
            return super().numeric_cell(node, fam, key, values, free_idx,
                                        tokens, struct, chain_nodes, assign)
        units = uinfo["units"]
        fa = uinfo["fa"]
        v = node.vertex
        jobs = self._jobs_for(v, units)

        def accept(vals):
            trial = list(values)
            for i, x in zip(free_idx, vals):
                trial[i] = LinForm(x)
            labs = self.label_forms(fam, trial)
            if any(f.is_num and f.c.denominator != 1 for f in labs.values()):
                return None
            if not self.cell_ok(node, fam, labs, key):
                return None
            probe = self._sink_probe(node, fam, key, labs, units, jobs)
            if probe is None:
                return None
            return (trial, labs, probe[0], probe[1])

        got = self.sample(len(free_idx), accept) if free_idx else accept([])
        if got is None:
            raise Failure("parameters",
                          f"no admissible parameter point for {key} "
                          "(cell + sink labels)", vertex=v, context=key)
        trial, labs, infos, extra = got
        self.finish_cell(node, fam, key, trial, labs, struct, chain_nodes,
                         assign)
        self._reserve(extra, f"sink reservation at {v}")
        for info in infos:
            rec = dict(info)
            rec["vertex"] = v
            rec["context"] = key
            self.free_tokens.append(rec)
            self.sink_counters["free_tokens"] += 1
            if rec["size"] == 4:
                self.sink_counters["quad_units"] += 1
            if fa:
                self.sink_counters["fa_second_token_units"] += 1
        if uinfo["pairs"]:
            self.sink_counters["antipodal_pairs_removed"] += len(uinfo["pairs"])
        if fa:
            # the FIRST token of a forced-antipode family keeps the existing
            # ``a = -b`` treatment with the parent (the pending queue); only
            # the second one is a unit and gets a sink
            self.register_token(v, [labs[tokens[0][r]] for r in "abc"],
                                absorbed=None)
        # the certificate keeps the same shape as the faithful mode
        for slot, unit in enumerate(units):
            self.tokens.append({"vertex": v,
                                "values": [str(labs[nm]) for nm in unit["names"]],
                                "paired_with": None,
                                "sink": ((jobs[slot] or {}).get("kind")
                                         or "direct")})


# ==========================================================================
# 4.  Placing the sinks once the sweep is over
# ==========================================================================

def quad_gadget_parameter(real: SinkRealiser, negs: Sequence[int]):
    """Choose the gadget's fresh parameter ``f`` and the split of the quad.

    ``f`` is picked like a head: the smallest admissible multiple of the
    lattice for which the eight gadget labels are distinct and free.  The
    quad is unordered, so the three ways of splitting it into ``{q1, q2}``
    and ``{q3, q4}`` are tried.
    """
    splits = [(0, 1, 2, 3), (0, 2, 1, 3), (0, 3, 1, 2)]
    for mag in range(1, real.RAY_MAGNITUDES):
        for sgn in (1, -1):
            f = sgn * mag * real.M
            for i, j, k, l in splits:
                q1, q2, q3, q4 = negs[i], negs[j], negs[k], negs[l]
                top = f - q1 - q2
                fresh = [LinForm(top), LinForm(-top), LinForm(f), LinForm(-f)]
                if not real._try_batch(fresh, "quad gadget parameter"):
                    continue
                return f, (q1, q2, q3, q4), fresh
    return None


def place_sinks(real: SinkRealiser, plan: "ftc.Plan") -> dict:
    """Commit the sink labels on their edges.  Returns a placement report."""
    stats = {"absorbers": 0, "direct": 0, "quad_gadgets": 0,
             "absorber_records": [], "direct_records": [],
             "quad_records": []}
    ledger = {(r["vertex"], r["slot"]): r for r in real.free_tokens}
    leftover: List[dict] = []
    consumed_vertices: set = set()
    done: set = set()

    # -- absorbers first ---------------------------------------------------
    for job in real.sink_jobs:
        if job["kind"] != "absorber":
            continue
        recs = [ledger.get(k) for k in job["slots"]]
        present = [r for r in recs if r is not None and len(r["negs"]) == 3]
        if len(present) < 2:
            leftover.extend(present)          # the family choice changed
            continue
        first, second = present[0], present[1]
        info = second.get("absorber")
        if info is None:
            info = first.get("absorber")
            first, second = second, first
        if info is None:
            leftover.extend(present)
            continue
        i, j = info["order_first"]
        k, l = info["order_second"]
        negA, negB = first["negs"], second["negs"]
        a, b = negA[i], negA[j]
        third_a = negA[3 - i - j]
        c, d = negB[k], negB[l]
        third_b = negB[3 - k - l]
        if a + b + third_a != 0 or c + d + third_b != 0:
            raise Failure("sink_absorber", "the negated token is not zero-sum")
        f1, f3 = a + b + d, 2 * a + b - c
        if f1 != info["F1"] or f3 != info["F3"]:
            raise Failure("sink_absorber", "absorber forms drifted")
        e = job["edges"]
        values = {e["v0v1"]: f1, e["v0w0"]: -f1,
                  e["v1v2"]: a, e["v1w1"]: third_b,
                  e["v2v3"]: b, e["v2w2"]: d,
                  e["v3v4"]: f3, e["v3w3"]: -f3,
                  e["v4w4"]: c, e["v4w4p"]: third_a}
        if len(set(values)) != 10:
            raise Failure("sink_absorber", "absorber edges are not distinct")
        for edge, val in values.items():
            real.commit(edge, LinForm(val), f"absorber {job['chain'][0]}")
        consumed_vertices |= set(job["chain"])
        done.add((first["vertex"], first["slot"]))
        done.add((second["vertex"], second["slot"]))
        stats["absorbers"] += 1
        stats["absorber_records"].append(
            {"chain": job["chain"], "edges": {k2: int(v2) for k2, v2 in
                                              values.items()},
             "sources": [[first["vertex"], first["slot"]],
                         [second["vertex"], second["slot"]]]})

    # -- quad gadgets ------------------------------------------------------
    for job in real.sink_jobs:
        if job["kind"] != "quad":
            continue
        rec = ledger.get(job["slots"][0])
        if rec is None:
            continue
        if len(rec["negs"]) != 4:             # the family choice changed
            leftover.append(rec)
            continue
        got = quad_gadget_parameter(real, rec["negs"])
        if got is None:
            raise Failure("sink_quad",
                          "no fresh parameter for the quad gadget of owner "
                          f"{rec['vertex']} (slot {rec['slot']})",
                          vertex=rec["vertex"])
        f, (q1, q2, q3, q4), fresh = got
        top = f - q1 - q2
        e = job["edges"]
        values = {e["v0v1"]: top, e["v0w0"]: -top,
                  e["v1v2"]: q1, e["v1w1"]: q2,
                  e["v2v3"]: f, e["v2w2"]: -f,
                  e["v3w3"]: q3, e["v3w3p"]: q4}
        if len(set(values)) != 8:
            raise Failure("sink_quad", "quad gadget edges are not distinct")
        if len(set(values.values())) != 8:
            raise Failure("sink_quad", "quad gadget labels are not distinct")
        if q1 + q2 + q3 + q4 != 0:
            raise Failure("sink_quad", "the negated unit is not zero-sum")
        for edge, val in values.items():
            real.commit(edge, LinForm(val), f"quad gadget {job['chain'][0]}")
        real.close_batch(fresh)
        consumed_vertices |= set(job["chain"])
        done.add((rec["vertex"], rec["slot"]))
        stats["quad_gadgets"] += 1
        stats["quad_records"].append(
            {"chain": job["chain"], "f": int(f),
             "edges": {k2: int(v2) for k2, v2 in values.items()},
             "source": [rec["vertex"], rec["slot"]]})

    # -- direct sinks ------------------------------------------------------
    direct_jobs = [j for j in real.sink_jobs if j["kind"] == "direct"]
    wanted: List[dict] = []
    seen: set = set()
    for job in direct_jobs:
        rec = ledger.get(job["slots"][0])
        if rec is not None and (rec["vertex"], rec["slot"]) not in seen:
            wanted.append(rec)
            seen.add((rec["vertex"], rec["slot"]))
    for r in leftover:
        if (r["vertex"], r["slot"]) not in seen:
            wanted.append(r)
            seen.add((r["vertex"], r["slot"]))
    for rec in real.free_tokens:               # units with no usable job
        key = (rec["vertex"], rec["slot"])
        if key in seen or key in done:
            continue
        wanted.append(rec)
        seen.add(key)

    blocks = []
    for v, nd in plan.nodes.items():
        if v in consumed_vertices:
            continue
        edges = [x for x in nd.ordinary if x not in real.labels]
        if len(edges) >= 3:
            blocks.append({"vertex": v, "edges": edges})
    blocks.sort(key=lambda b: -len(b["edges"]))

    # the largest units first, so a quad is not starved by a triple that
    # would have fitted in a smaller block (``greedy_direct_fit`` plans it
    # in exactly this order)
    for rec in sorted(wanted, key=lambda r: -len(r["negs"])):
        size = len(rec["negs"])
        placed = False
        for blk in blocks:
            if not block_takes(len(blk["edges"]), size):
                continue
            edges = blk["edges"][:size]
            blk["edges"] = blk["edges"][size:]
            for edge, val in zip(edges, rec["negs"]):
                real.commit(edge, LinForm(val), f"direct sink at {blk['vertex']}")
            stats["direct"] += 1
            stats["direct_records"].append({"vertex": blk["vertex"],
                                            "edges": edges,
                                            "values": list(rec["negs"]),
                                            "source": [rec["vertex"],
                                                       rec["slot"]]})
            placed = True
            break
        if not placed:
            raise Failure("sink_place",
                          f"no ordinary block can host the negated unit of "
                          f"owner {rec['vertex']} (slot {rec['slot']}, "
                          f"size {size})",
                          vertex=rec["vertex"])
        blocks.sort(key=lambda b: -len(b["edges"]))
    return stats


# ==========================================================================
# 4b.  Solver-free zero-sum completion (a fast path in front of complete_blocks)
# ==========================================================================
#
# The sink route makes the special support closed under negation, so the
# remaining labels are closed under negation too and every zero-sum block can
# be built out of antipodal pairs ``{x, n-x}`` plus, for the odd blocks, one
# zero-sum triple each.  CP-SAT solves the same problem but the instances of
# the comb+bush / comb+binary families have hundreds of interchangeable
# size-two blocks, and the symmetry makes it time out at any sane budget.  The
# greedy below is tried first and ``complete_blocks`` remains the fallback, so
# nothing is weakened: ``verify_edge_graceful`` still judges the result.

def greedy_zero_sum_completion(n: int, blocks: Sequence[dict],
                               used) -> Optional[Dict[int, int]]:
    """Split the remaining labels into zero-sum blocks without a solver.

    The remaining labels fall into antipodal pairs ``{x, n-x}`` plus a set
    ``U`` of labels whose antipode is a special one.  ``sum(U) = -sum(S) = 0``
    whenever the instance is feasible at all, so the whole of ``U`` goes into
    one (the largest) block and every other block is built from pairs, with
    one zero-sum triple added to each odd block.  Triples are produced in
    mirror couples, so the leftover always stays pairable.  Returns ``None``
    whenever this shape does not fit -- the caller then falls back to CP-SAT.
    """
    used_mod = {int(x) % n for x in used}
    remaining = sorted(set(range(1, n)) - used_mod)
    blocks = list(blocks)
    if sum(len(b["edges"]) for b in blocks) != len(remaining):
        return None
    if any(int(b.get("target", 0)) % n for b in blocks):
        return None
    if not blocks:
        return {} if not remaining else None
    if any(len(b["edges"]) < 2 for b in blocks):
        return None

    rem = set(remaining)
    odd_out = [x for x in remaining if (n - x) not in rem]
    if sum(odd_out) % n:
        return None
    free_reps = {x for x in remaining if x < n - x and (n - x) in rem}

    host = max(range(len(blocks)), key=lambda i: len(blocks[i]["edges"]))
    if len(blocks[host]["edges"]) < len(odd_out):
        return None
    need_triple = {}
    for i, b in enumerate(blocks):
        size = len(b["edges"]) - (len(odd_out) if i == host else 0)
        if size < 0:
            return None
        need_triple[i] = bool(size % 2)
        if size % 2 and size < 3:
            return None
    ntri = sum(1 for v in need_triple.values() if v)
    if ntri % 2:
        return None

    triples: List[List[int]] = []
    while len(triples) < ntri:
        pool = sorted(free_reps)
        found = None
        for ai, a in enumerate(pool):
            for b in pool[ai + 1:]:
                c = (-(a + b)) % n
                if c == 0:
                    continue
                crep = min(c, n - c)
                if crep not in free_reps or crep == a or crep == b:
                    continue
                found = (a, b, c, crep)
                break
            if found:
                break
        if not found:
            return None
        a, b, c, crep = found
        free_reps -= {a, b, crep}
        triples.append([a, b, c])
        triples.append([n - a, n - b, (n - c) % n])
    pairs = [[x, n - x] for x in sorted(free_reps)]

    out: Dict[int, int] = {}
    ti = pi = 0
    for i, blk in enumerate(blocks):
        vals: List[int] = list(odd_out) if i == host else []
        size = len(blk["edges"]) - len(vals)
        if need_triple[i]:
            vals += triples[ti]
            ti += 1
            size -= 3
        for _ in range(size // 2):
            vals += pairs[pi]
            pi += 1
        if len(vals) != len(blk["edges"]) or sum(vals) % n:
            return None
        for edge, val in zip(blk["edges"], vals):
            out[edge] = val
    if pi != len(pairs) or ti != len(triples):
        return None
    if len(set(out.values())) != len(remaining):
        return None
    return out


#: bound once, so the scoped swap below can never recurse into itself
_CPSAT_COMPLETE_BLOCKS = ftc.complete_blocks


def _sink_complete_blocks(n, blocks, used, time_limit: float = 30.0,
                          workers: int = 4, seed: int = 0):
    """``complete_blocks`` with the greedy fast path in front of it."""
    blocks = list(blocks)
    used = list(used)
    got = greedy_zero_sum_completion(n, blocks, used)
    if got is not None:
        return got
    return _CPSAT_COMPLETE_BLOCKS(n, blocks, used, time_limit=time_limit,
                                  workers=workers, seed=seed)


# ==========================================================================
# 5.  Driver
# ==========================================================================

def _construct_rooted_sink(n: int, parent: List[int], children: List[List[int]],
                           root: int, catalogue, rng: random.Random,
                           tries: int, block_time: float, seed: int,
                           allow_fallback: bool = True) -> dict:
    old_of, new_of = ftc.relabel_to_root(parent, root)
    sched_parent = [-1] * n
    for v in range(n):
        if parent[v] != -1:
            sched_parent[new_of[v]] = new_of[parent[v]]
    sched_parent[0] = 0
    sched = cs.schedule(sched_parent)
    if sched.get("is_path"):
        raise Failure("path", "the scheduler reports a path")
    sched = ftc.translate_schedule(sched, old_of)
    plan = ftc.Plan(n, parent, children, root, sched)

    real = SinkRealiser(plan, catalogue, rng, tries=tries,
                        allow_fallback=allow_fallback)
    sink_plan = build_sink_plan(plan, real.choice)
    if not sink_plan["ok"]:
        real.gaps.append({"vertex": root, "context": "sink_route",
                          "reason": sink_plan["gap"]["detail"]})
        raise Failure(sink_plan["gap"]["step"], sink_plan["gap"]["detail"])
    real.sink_jobs = sink_plan["jobs"]
    real.sink_assign = sink_plan["assign"]

    real.run()
    placement = place_sinks(real, plan)
    # ``finalise`` looks ``complete_blocks`` up in its own module at call time;
    # the swap is scoped to this call and restored immediately, so no other
    # mode ever sees it (see section 4b for why the fast path is needed).
    _saved = ftc.complete_blocks
    ftc.complete_blocks = _sink_complete_blocks
    try:
        out = real.finalise(block_time, seed)
    finally:
        ftc.complete_blocks = _saved

    missing = [v for v in range(n) if v != root and v not in out["labels"]]
    if missing:
        raise Failure("coverage", f"{len(missing)} edges never labelled: "
                      f"{missing[:8]}")
    report = ftl.verify_edge_graceful(parent, out["labels"])
    D = ftc.degree_two_count(parent)
    support = sorted(set(out["integers"].values()))
    mag = real.max_magnitude
    stats = {
        "n": n,
        "degree_two": D,
        "owners": sum(1 for x in plan.nodes.values() if x.is_owner),
        "free_tokens": len(real.free_tokens),
        "planned_free_tokens": len(sink_plan["tokens"]) + len(sink_plan["two_port"]),
        "planned_owner_tokens": len(sink_plan["tokens"]),
        "planned_two_port_tokens": len(sink_plan["two_port"]),
        "two_port_tokens": real.sink_counters.get("two_port_tokens", 0),
        "planned_direct": sink_plan["direct"],
        "planned_absorbers": sink_plan["absorbers"],
        "planned_quad_gadgets": sink_plan.get("quad_gadgets", 0),
        "planned_quads": sink_plan.get("quads", 0),
        "absorber_chains_available": sink_plan["gadgets"],
        "direct_sinks_used": placement["direct"],
        "absorbers_used": placement["absorbers"],
        "quad_gadgets_used": placement["quad_gadgets"],
        "quad_units": real.sink_counters.get("quad_units", 0),
        "fa_second_token_units":
            real.sink_counters.get("fa_second_token_units", 0),
        "antipodal_pairs_removed":
            real.sink_counters.get("antipodal_pairs_removed", 0),
        "residue2_rigid_parents":
            real.sink_counters.get("residue2_rigid_parents", 0),
        "residue2_menu_entries_dropped":
            real.sink_counters.get("residue2_menu_entries_dropped", 0),
        "residue2_rigid_gaps": real.sink_counters.get("residue2_rigid_gaps", 0),
        "unit_rule_fallback": real.sink_counters.get("unit_rule_fallback", 0),
        "job_size_mismatch": real.sink_counters.get("job_size_mismatch", 0),
        "max_magnitude": mag,
        "magnitude_over_D1": float(Q(mag, max(1, D + 1))) if mag else 0.0,
        "special_labels": len(real.labels),
        "special_support": len(support),
        "support_over_D1": float(Q(len(support), max(1, D + 1))),
        "lemma_gaps": len(real.gaps),
        "fallback_cells": real.counters.get("fallback_synth_cells", 0),
        "family_second_choice": real.counters.get("family_second_choice", 0),
        "subtree_retries": real.counters.get("subtree_retries", 0),
        "forced_antipode_families":
            real.counters.get("forced_antipode_family_used", 0),
        "fa_case_a_port_block": real.counters.get("fa_case_a", 0),
        "fa_case_b_input_in_token": real.counters.get("fa_case_b", 0),
        "fa_case_c_joint": real.counters.get("fa_case_c", 0),
        "T1_symbolic_tokens": real.counters.get("T1_symbolic_tokens", 0),
        "T2_pairings": real.counters.get("T2_pairings", 0),
        "singleton_bridge": len(out.get("bridges") or []),
        "lattice_M": real.M,
        "two_token_cells": real.counters.get("two_token_cells", 0),
    }
    cert = {
        "ok": bool(report["ok"]),
        "mode": "sink",
        "statistics": stats,
        "n": n,
        "parent": list(parent),
        "root": root,
        "route": "cells",
        "labels": {str(k): v for k, v in sorted(out["labels"].items())},
        "integer_labels": {str(k): v for k, v in sorted(out["integers"].items())},
        "special_support": support,
        "ordinary_blocks": [{"vertex": b["vertex"], "edges": b["edges"],
                             "target": 0,
                             "values": [out["labels"].get(e) for e in b["edges"]]}
                            for b in out["blocks"]],
        "sinks": {"direct": placement["direct_records"],
                  "absorbers": placement["absorber_records"],
                  "quad_gadgets": placement["quad_records"]},
        "singleton_bridge": out.get("bridges"),
        "lemma_gaps": real.gaps,
        "tokens": real.tokens,
        "notes": list(real.notes),
        "verification": {"ok": report["ok"], "errors": report["errors"]},
    }
    if not report["ok"]:
        cert["failure"] = {"step": "verify",
                           "detail": "; ".join(report["errors"]),
                           "vertex": None, "context": None}
    return cert


def construct_sink(parent_in: Sequence[int], catalogue=None, seed: int = 0,
                   tries: int = 800, block_time: float = 30.0,
                   root_candidates: int = 4, restarts: int = 2) -> dict:
    """Build an edge-graceful labelling by the sink route, or report a failure."""
    n, parent, children, root0 = ftc.normalise_parent(parent_in)
    if n % 2 == 0:
        return {"ok": False, "n": n, "mode": "sink",
                "failure": {"step": "input", "detail": "the order must be odd",
                            "vertex": None, "context": None}}
    catalogue = catalogue if catalogue is not None else ftc.load_catalogue()

    if ftc.is_path(parent):
        labels = ftc.label_path(n, parent, random.Random(seed))
        if labels is None:
            return {"ok": False, "n": n, "mode": "sink", "route": "path",
                    "failure": {"step": "path",
                                "detail": "no path labelling found",
                                "vertex": None, "context": None}}
        report = ftl.verify_edge_graceful(parent, labels)
        return {"ok": bool(report["ok"]), "n": n, "mode": "sink",
                "route": "path", "parent": list(parent), "root": root0,
                "labels": {str(k): v for k, v in sorted(labels.items())},
                "statistics": {"n": n, "degree_two": ftc.degree_two_count(parent),
                               "free_tokens": 0, "direct_sinks_used": 0,
                               "absorbers_used": 0, "max_magnitude": 0,
                               "magnitude_over_D1": 0.0, "special_support": 0,
                               "support_over_D1": 0.0, "lemma_gaps": 0},
                "ordinary_blocks": [], "tokens": [], "special_support": [],
                "sinks": {"direct": [], "absorbers": [], "quad_gadgets": []},
                "lemma_gaps": [],
                "notes": ["path route"],
                "verification": {"ok": report["ok"], "errors": report["errors"]}}

    attempts = []
    for ri, root in enumerate(ftc.choose_root_candidates(parent)[:root_candidates]):
        rooted = ftc.reroot(parent, root)
        _n, par, ch, rt = ftc.normalise_parent(rooted)
        for restart in range(restarts):
            sd = seed * 1000 + ri * 10 + restart
            rng = random.Random(sd)
            try:
                cert = _construct_rooted_sink(_n, par, ch, rt, catalogue, rng,
                                              tries, block_time, seed=sd)
            except Failure as exc:
                attempts.append({"root": root, "restart": restart,
                                 "failure": exc.report})
                continue
            if cert.get("ok"):
                cert["attempts"] = attempts
                return cert
            attempts.append({"root": root, "restart": restart,
                             "failure": cert.get("failure")})
    return {"ok": False, "n": n, "mode": "sink", "route": "cells",
            "parent": list(parent),
            "failure": (attempts[0]["failure"] if attempts else
                        {"step": "root", "detail": "no branch vertex",
                         "vertex": None, "context": None}),
            "attempts": attempts}


# ==========================================================================
# 6.  Tree families and the CLI
# ==========================================================================

def combbush_tree(k: int, bush: int, arm: int = 3) -> List[int]:
    par = combbush(k, arm=arm, sub=0, bush=bush)
    if len(par) % 2 == 0:
        par = combbush(k, arm=arm, sub=0, bush=bush + 1)
    return par


def combbin_tree(depth: int, k: int, arm: int = 3) -> List[int]:
    par = [-1]
    ps._add_complete_binary_subtree(par, 0, depth)
    ps._add_complete_binary_subtree(par, 0, depth)
    ps._add_comb(par, 0, k, arm=arm)
    if len(par) % 2 == 0:
        par.append(0)
    return par


def summarise(cert: dict) -> dict:
    st = cert.get("statistics") or {}
    out = {"ok": bool(cert.get("ok")), "n": cert.get("n"),
           "D": st.get("degree_two"),
           "free_tokens": st.get("free_tokens"),
           "direct": st.get("direct_sinks_used"),
           "absorbers": st.get("absorbers_used"),
           "quad_gadgets": st.get("quad_gadgets_used"),
           "quads": st.get("quad_units"),
           "fa_second_tokens": st.get("fa_second_token_units"),
           "residue2_parents": st.get("residue2_rigid_parents"),
           "max_magnitude": st.get("max_magnitude"),
           "magnitude_over_D1": st.get("magnitude_over_D1"),
           "special_support": st.get("special_support"),
           "support_over_D1": st.get("support_over_D1"),
           "lemma_gaps": st.get("lemma_gaps")}
    if not cert.get("ok"):
        out["failure"] = cert.get("failure")
    return out


def run_one(name: str, par: Sequence[int], catalogue, args) -> dict:
    t0 = time.time()
    cert = construct_sink(par, catalogue=catalogue, seed=args.seed,
                          tries=args.tries, block_time=args.block_time,
                          root_candidates=args.roots)
    cert["tree"] = name
    cert["seconds"] = round(time.time() - t0, 2)
    if args.outdir:
        os.makedirs(args.outdir, exist_ok=True)
        with open(os.path.join(args.outdir, f"cert_{name}.json"), "w") as fh:
            json.dump(cert, fh)
    row = summarise(cert)
    row["tree"] = name
    row["seconds"] = cert["seconds"]
    print(f"  {name:26s} n={row['n']:5d} D={row['D']} ok={row['ok']} "
          f"t={row['free_tokens']} direct={row['direct']} "
          f"abs={row['absorbers']} mag/(D+1)="
          f"{(row['magnitude_over_D1'] or 0):.3f} |S|/(D+1)="
          f"{(row['support_over_D1'] or 0):.3f} ({row['seconds']}s)",
          flush=True)
    if not row["ok"]:
        print(f"      failure: {json.dumps(row.get('failure'))}", flush=True)
    return row


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--parent", help="comma separated parent array (root = -1)")
    ap.add_argument("--combbush", nargs=2, type=int, metavar=("K", "BUSH"))
    ap.add_argument("--combbin", nargs=2, type=int, metavar=("DEPTH", "K"))
    ap.add_argument("--sparse", nargs=2, metavar=("ORDERS", "COUNT"))
    ap.add_argument("--census", help="comma separated orders")
    ap.add_argument("--seed", type=int, default=20260901)
    ap.add_argument("--tries", type=int, default=800)
    ap.add_argument("--block-time", type=float, default=20.0)
    ap.add_argument("--roots", type=int, default=4)
    ap.add_argument("--kd", type=int, default=25, help="sparse density divisor")
    ap.add_argument("--outdir", default=None, help="save every certificate here")
    ap.add_argument("--json", default=None)
    a = ap.parse_args(argv)

    catalogue = ftc.load_catalogue()
    rows: List[dict] = []
    did = False

    if a.parent:
        did = True
        par = [int(x) for x in a.parent.split(",")]
        rows.append(run_one("parent", par, catalogue, a))
    if a.combbush:
        did = True
        k, bush = a.combbush
        rows.append(run_one(f"combbush_k{k}_b{bush}", combbush_tree(k, bush),
                            catalogue, a))
    if a.combbin:
        did = True
        d, k = a.combbin
        rows.append(run_one(f"combbin_d{d}_k{k}", combbin_tree(d, k),
                            catalogue, a))
    if a.sparse:
        did = True
        orders = [int(x) for x in a.sparse[0].split(",")]
        count = int(a.sparse[1])
        for name, par in ftc.sparse_trees(orders, count, 1, a.kd):
            rows.append(run_one(name, par, catalogue, a))
    if a.census:
        did = True
        orders = [int(x) for x in a.census.split(",")]
        for name, par in ftc.census_trees(orders):
            rows.append(run_one(name, par, catalogue, a))

    if not did:
        ap.print_help()
        return 2
    ok = sum(1 for r in rows if r["ok"])
    print(f"\ntotal {len(rows)} trees, ok {ok}, failed {len(rows) - ok}")
    if a.json:
        with open(a.json, "w") as fh:
            json.dump(rows, fh, indent=1)
        print(f"wrote {a.json}")
    return 0 if ok == len(rows) else 1


if __name__ == "__main__":
    sys.exit(main())
