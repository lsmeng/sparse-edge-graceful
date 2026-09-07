#!/usr/bin/env python3
r"""End-to-end constructor for the free-token programme.

Reference documents
-------------------
``research/antimagic/SPEC_free_token_constructor.md`` (the specification this
file implements), ``ROUTE_CORE_FREE_TOKEN_PROGRAM_20260901.md`` sections 4-7
(architecture, rigid letters, deferred tokens) and
``SPARSE_FLAGSHIP_FREE_TOKEN_PROOF_DRAFT_20260901.md`` sections 3-8b
(Lemmas B-F).

Input:  an odd-order tree given by a parent array.
Output: an edge-graceful labelling ``lambda : E -> Z_n \ {0}`` (vertex sums a
bijection onto ``Z_n``) together with a *certificate* recording every local
decision, or a precise failure report naming the first vertex / context /
step that failed.

Pipeline
--------
1. ``choose_root``      -- a branch vertex (Lemma A); paths are handled by a
                           dedicated solver-free routine.
2. ``context_scheduler.schedule`` -- the authoritative decomposition (Lemma B
                           and Lemma C).  ``Plan`` only translates its
                           per-vertex rows (owner / passthrough / stationary,
                           context key, which tree edges are the head chain,
                           the residual arms, the neutral units, the repair,
                           the ports and recruited ports, the cancelled active
                           groups, the kept inputs and the helper absorption)
                           into the constructor's own records.  The scheduler
                           always roots at vertex 0, so the tree is relabelled
                           and the answer translated back.
3. ``Realiser.run``     -- bottom-up over the plan.  Each cell takes a family
                           from the per-context menu of
                           ``data/alphabet_families.json`` (``clean`` families
                           first, then the ones whose head-only labels avoid
                           the ratios the parent must force) and chooses its
                           free parameters; arms are lengthened by six-edge
                           mothers and head chains by endpoint-preserving
                           insertions; neutral units come from the proved
                           integer bases of ``mixed_chain_pairs`` /
                           ``mixed_chain_pairs_triple2``, or are re-derived.
   Three fallbacks, all solver-free, cover what the catalogue cannot:
   ``synth_topology``   re-derives a family for one context by enumerating the
                        output bijections with incremental exact elimination
                        (the catalogue is still missing small root contexts);
   ``synth_joint``      does the same for a *whole-parent reopen*: a parent and
                        its kept active child as one multi-row macro, which is
                        what proof draft 8b requires for the forced-antipode
                        types (the residue-one letter and the ``(1;1 port)``
                        bottom);
   ``synth_group``      does it for a whole *cancelled active group*: the two
                        or three children of a stationary vertex are realised
                        as one macro whose union is ``P = O`` with head sum
                        zero, instead of separately.
   The sweep also backtracks: a failing subtree is restored and retried, and
   the whole tree is retried over several roots and seeds.
4. ``complete_blocks``  -- the only solver use: CP-SAT splits the remaining
                           labels into the ordinary blocks.  Blocks carry a
                           *target sum*: a stationary vertex that absorbs an
                           active head ``x`` simply needs its ports to sum to
                           ``-x``, which subsumes the helper ``-x`` (q = 1, 3+)
                           and the two-port pair ``a, -x-a`` (q = 2) of
                           ROUTE_CORE section 4 without spending a special
                           label on them.
5. ``free_token_lib.verify_edge_graceful`` -- final whole-tree check.

Arithmetic
----------
The specification writes the algorithm over the integers with a global lattice
constant ``M`` and a final reduction mod ``n``.  This implementation performs
the *same* algorithm directly in ``Z_n`` (``n`` odd, so ``2`` is invertible;
a family whose denominator ``L`` shares a factor with ``n`` is skipped and
reported).  The two agree whenever all special magnitudes stay below ``n/2``
-- the asymptotic regime of the theorem -- and working in ``Z_n`` is strictly
better for the small test trees, where distinctness *mod n* is the real
constraint and integer distinctness is not sufficient.  Every identity used
(``P = O``, six-edge mother, endpoint-preserving insertion, neutral units) is
homogeneous with rational coefficients, hence valid over ``Z_n``.

Local identities
----------------
* six-edge mother ``((T-A)/2, -T, (A+T)/2, (A-T)/2, -(A+T)/2, T)`` -- extends
  an arm by six labels (three inverse pairs added to both ``P`` and ``O``);
* the flexible twelve-label endpoint-preserving insertion of
  ``ROUTE_CORE_FLEXIBLE_TWELVE_INSERTION_20260901.md`` -- extends a head chain
  by twelve;
* the six rigid six-label endpoint-preserving insertions in
  ``SIX_INSERTIONS`` -- extend a head chain by six.  They were derived here by
  exact linear algebra over all 5040 output bijections; there are exactly six
  nondegenerate ones (and none of size 3, 4 or 5), and ``SIX_INSERTIONS[0]``
  (``(-(2L+R)/3, (L-R)/3, (L+2R)/3, (2L+R)/3, (R-L)/3, -(L+2R)/3)``) is the
  only mirror-closed one.  Together with the twelve-insertion they realise any
  head chain whose raw length is congruent to the family's mod six, provided
  the family's chain has at least one gap.
* the residue-two rigid row ``(-3x/2; -x/2, -x, x/2; x)`` (``RESIDUE2_RIGID_*``)
  and the four-layer joint ``data/family_r2222_L12.json`` are both available;
  ``synth_topology`` finds a strictly larger two-parameter family for
  ``h*_2_p0_act`` (with the head still free once ``x`` is pinned), which the
  constructor prefers, so the four-layer reset is not needed.
  ``statistics.residue2_rigid_rows`` reports how often the rigid row was used.

Certificate format
------------------
``build_certificate`` returns a JSON-serialisable dict::

    {
      "n": int,                     # order of the tree
      "parent": [int, ...],         # parent array, root marked -1
      "root": int,
      "ok": bool,
      "route": "cells" | "path",    # which construction was used
      "labels": {"<child vertex>": int},   # label of the edge (v, parent[v])
      "special_support": [int, ...],       # labels placed by cells/units
      "ordinary_blocks": [                 # target-sum blocks at stationary
          {"vertex": int, "edges": [int],  # slots (target 0 unless the vertex
           "target": int, "values": [int]}, ...],   # absorbs an active head)
      "statistics": {"owners", "catalogue_cells", "synthesised_cells",
                     "neutral_units", "residue2_rigid_rows",
                     "whole_parent_joints", "cancelled_group_macros",
                     "subtree_retries", "special_labels"},
      "vertices": [ per-vertex records, see below ],
      "tokens": [ {"vertex": int, "values": [int,int,int],
                   "paired_with": int | null} ],
      "verification": { ... free_token_lib.verify_edge_graceful report ... },
      "notes": [str, ...]           # every deviation from the ideal route
    }

A per-vertex record (only core vertices appear) is::

    {
      "vertex": int,
      "role": "owner" | "stationary" | "folded" | "leaf",
      "context": "h0_1-1_p1_bot",          # context key, null for stationary
      "context_spec": {"head": 0, "arms": [1, 1], "ports": 1, "tag": "bot"},
      "passthrough": "V21" | "V22" | null, # folded into the parent's macro
      "family": {                          # null unless the vertex owns a macro
         "source": "catalogue" | "synthesised",
         "menu_index": int | null,         # index in the context menu
         "denominator": int,
         "parameters": {"y": int, ...},    # catalogue families only
         "topology": {...}, "basis": [[int]],   # synthesised families only
         "labels": {"g0": int, ...},       # label name -> value in Z_n
         "provenance": str | null},
      "head_chain": {"raw": int, "reduced": int,
                     "six_insertions": int, "twelve_insertions": int,
                     "edges": [int, ...], "values": [int, ...]},
      "arms": [{"slot": int, "core_child": int, "raw_length": int,
                "reduced": int, "mothers": int, "edges": [...],
                "values": [...]}],
      "ports": {"recruited": [int, ...], "ordinary": [int, ...]},
      "active": {"child_type": "none"|"free"|"L1"|"V21"|"V22"|"act2",
                 "cancelled_groups": [[int, ...], ...],
                 "retained": int | null, "folded": int | null},
      "neutral_units": [{"kind": "pair"|"four_short", "base": [ints],
                         "scale": int, "arms": [{...}]}],
      "absorption": null | {"type": "port_block", "ports": [int, ...]}
                         | {"type": "port_into_group", "port": int,
                            "value": int},
      "token": null | {"labels": ["a","b","c"], "values": [int,int,int],
                       "absorbed": int | null}
    }

On failure the dict is ``{"ok": false, "failure": {"step": ..., "vertex": ...,
"context": ..., "detail": ...}, ...}`` with the partial certificate attached.

Usage
-----
    .venv/bin/python research/antimagic/scripts/free_token_constructor.py --demo
    ... --parent 0,0,0,1,1,2,2                 # explicit parent array
    ... --census 7,9,11,13                     # all free trees of those orders
    ... --random 21,31,51 --count 200
    ... --sparse 51,101,201 --count 40         # the sparse regime n > C(D+1)
    ... --stress                               # the rigid-module families
    ... --selftest                             # re-derive every local identity
    ... --all                                  # the full test programme
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
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from fractions import Fraction as Q
from typing import (Any, Dict, Iterable, List, Mapping, Optional, Sequence,
                    Tuple)

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import free_token_lib as ftl                      # noqa: E402
import context_scheduler as cs                    # noqa: E402

try:
    import mixed_chain_pairs as pair_bases        # noqa: E402
    import mixed_chain_pairs_triple2 as short_bases  # noqa: E402
    HAVE_UNIT_BASES = True
except Exception as _exc:                          # pragma: no cover
    pair_bases = None
    short_bases = None
    HAVE_UNIT_BASES = False

DATA = os.path.normpath(os.path.join(HERE, "..", "data"))
DEFAULT_CATALOGUE = os.path.join(DATA, "alphabet_families.json")


# ==========================================================================
# 0.  Modular arithmetic in Z_n  (n odd, possibly composite)
# ==========================================================================

def egcd(a: int, b: int) -> Tuple[int, int, int]:
    if b == 0:
        return (a, 1, 0)
    g, x, y = egcd(b, a % b)
    return (g, y, x - (a // b) * y)


def inv_mod(a: int, n: int) -> int:
    """Inverse of ``a`` in ``Z_n``; raises ``ValueError`` when not a unit."""
    a %= n
    g, x, _ = egcd(a, n)
    if g != 1:
        raise ValueError(f"{a} is not invertible mod {n}")
    return x % n


def is_unit(a: int, n: int) -> bool:
    return math.gcd(a % n, n) == 1


class Failure(Exception):
    """A construction step failed; carries the precise report."""

    def __init__(self, step: str, detail: str, vertex: Optional[int] = None,
                 context: Optional[str] = None, **extra: Any) -> None:
        super().__init__(f"{step}: {detail}")
        self.report = {"step": step, "detail": detail, "vertex": vertex,
                       "context": context}
        self.report.update(extra)


# ==========================================================================
# 1.  Tree utilities
# ==========================================================================

def normalise_parent(parent_in: Sequence[int]) -> Tuple[int, List[int], List[List[int]], int]:
    """``(n, parent, children, root)``; the root is marked ``-1``."""
    n = len(parent_in)
    parent = list(parent_in)
    roots = [v for v in range(n)
             if parent[v] is None or parent[v] == -1 or parent[v] == v]
    if len(roots) != 1:
        raise Failure("input", f"expected exactly one root, found {roots}")
    root = roots[0]
    parent[root] = -1
    children: List[List[int]] = [[] for _ in range(n)]
    for v in range(n):
        if v != root:
            children[parent[v]].append(v)
    return n, parent, children, root


def edges_of(parent: Sequence[int]) -> List[Tuple[int, int]]:
    return [(v, parent[v]) for v in range(len(parent)) if parent[v] != -1]


def reroot(parent: Sequence[int], new_root: int) -> List[int]:
    """Re-root the tree given by ``parent`` at ``new_root``."""
    n = len(parent)
    adj: List[List[int]] = [[] for _ in range(n)]
    for v in range(n):
        p = parent[v]
        if p is not None and p != -1 and p != v:
            adj[v].append(p)
            adj[p].append(v)
    out = [-1] * n
    seen = [False] * n
    stack = [new_root]
    seen[new_root] = True
    while stack:
        v = stack.pop()
        for w in adj[v]:
            if not seen[w]:
                seen[w] = True
                out[w] = v
                stack.append(w)
    if not all(seen):
        raise Failure("input", "the parent array is not a tree")
    return out


def degrees(parent: Sequence[int]) -> List[int]:
    n = len(parent)
    deg = [0] * n
    for v in range(n):
        if parent[v] != -1:
            deg[v] += 1
            deg[parent[v]] += 1
    return deg


def adjacency(parent: Sequence[int]) -> List[List[int]]:
    n = len(parent)
    adj: List[List[int]] = [[] for _ in range(n)]
    for v in range(n):
        if parent[v] != -1:
            adj[v].append(parent[v])
            adj[parent[v]].append(v)
    return adj


def is_path(parent: Sequence[int]) -> bool:
    return max(degrees(parent), default=0) <= 2


def choose_root_candidates(parent: Sequence[int]) -> List[int]:
    """Branch vertices, best first: most leaf neighbours, then highest degree."""
    deg = degrees(parent)
    adj = adjacency(parent)
    cands = [v for v in range(len(parent)) if deg[v] >= 3]
    def score(v: int) -> Tuple[int, int]:
        leaves = sum(1 for w in adj[v] if deg[w] == 1)
        return (-leaves, -deg[v])
    cands.sort(key=score)
    return cands


# -- free-tree enumeration (isomorph-free, by leaf augmentation) ------------

def _canonical_rooted(v: int, p: int, adj: Sequence[Sequence[int]]) -> str:
    """AHU canonical string of the subtree rooted at ``v`` with parent ``p``."""
    subs = sorted(_canonical_rooted(w, v, adj) for w in adj[v] if w != p)
    return "(" + "".join(subs) + ")"


def canonical_free_tree(n: int, edge_list: Sequence[Tuple[int, int]]) -> str:
    """AHU canonical form of a free tree (rooted at its centre(s))."""
    adj: List[List[int]] = [[] for _ in range(n)]
    for u, v in edge_list:
        adj[u].append(v)
        adj[v].append(u)
    if n == 1:
        return "()"
    deg = [len(a) for a in adj]
    layer = [v for v in range(n) if deg[v] <= 1]
    removed = len(layer)
    cur = layer
    while removed < n:
        nxt = []
        for v in cur:
            for w in adj[v]:
                deg[w] -= 1
                if deg[w] == 1:
                    nxt.append(w)
        if removed + len(nxt) >= n:
            cur = nxt if nxt else cur
            break
        removed += len(nxt)
        cur = nxt
    centres = cur if cur else [0]
    forms = sorted(_canonical_rooted(c, -1, adj) for c in centres)
    return "|".join(forms)


def all_free_trees(n: int) -> List[List[int]]:
    """Every free tree on ``n`` vertices, as a parent array rooted at 0."""
    if n <= 0:
        return []
    if n == 1:
        return [[-1]]
    trees: Dict[str, List[Tuple[int, int]]] = {"": [(0, 1)]} if n >= 2 else {}
    current = {canonical_free_tree(2, [(0, 1)]): [(0, 1)]}
    size = 2
    while size < n:
        nxt: Dict[str, List[Tuple[int, int]]] = {}
        for edge_list in current.values():
            for attach in range(size):
                cand = list(edge_list) + [(attach, size)]
                key = canonical_free_tree(size + 1, cand)
                if key not in nxt:
                    nxt[key] = cand
        current = nxt
        size += 1
    out = []
    for edge_list in current.values():
        adj: List[List[int]] = [[] for _ in range(n)]
        for u, v in edge_list:
            adj[u].append(v)
            adj[v].append(u)
        par = [-1] * n
        seen = [False] * n
        seen[0] = True
        stack = [0]
        while stack:
            v = stack.pop()
            for w in adj[v]:
                if not seen[w]:
                    seen[w] = True
                    par[w] = v
                    stack.append(w)
        out.append(par)
    return out


def random_tree(n: int, rng: random.Random) -> List[int]:
    """A uniform labelled tree via a random Prufer sequence, rooted at 0."""
    if n == 1:
        return [-1]
    if n == 2:
        return [-1, 0]
    seq = [rng.randrange(n) for _ in range(n - 2)]
    degree = [1] * n
    for v in seq:
        degree[v] += 1
    import heapq
    leaves = [v for v in range(n) if degree[v] == 1]
    heapq.heapify(leaves)
    edge_list = []
    for v in seq:
        leaf = heapq.heappop(leaves)
        edge_list.append((leaf, v))
        degree[v] -= 1
        if degree[v] == 1:
            heapq.heappush(leaves, v)
    u = heapq.heappop(leaves)
    w = heapq.heappop(leaves)
    edge_list.append((u, w))
    adj: List[List[int]] = [[] for _ in range(n)]
    for a, b in edge_list:
        adj[a].append(b)
        adj[b].append(a)
    par = [-1] * n
    seen = [False] * n
    seen[0] = True
    stack = [0]
    while stack:
        v = stack.pop()
        for x in adj[v]:
            if not seen[x]:
                seen[x] = True
                par[x] = v
                stack.append(x)
    return par


# ==========================================================================
# 2.  Local identities in Z_n
# ==========================================================================

def mother_extension_mod(old_terminal: int, new_terminal: int, n: int) -> List[int]:
    """``((T-A)/2, -T, (A+T)/2, (A-T)/2, -(A+T)/2, T)`` in ``Z_n``.

    Six-edge mother of ``ROUTE_CORE_FINITE_RESIDUAL_CELLS.md`` (see
    ``free_token_lib.mother_extension``); ``n`` odd makes ``2`` invertible, so
    the integer parity condition disappears.
    """
    h = inv_mod(2, n)
    a, t = old_terminal % n, new_terminal % n
    return [(t - a) * h % n, (-t) % n, (a + t) * h % n,
            (a - t) * h % n, (-(a + t)) * h % n, t]


#: The six rigid endpoint-preserving six-label insertions.  Each entry is the
#: list of the six inserted labels as ``(alpha, beta)`` with the label equal to
#: ``alpha*L + beta*R``.  Derived by exact linear algebra over all 5040
#: output bijections (see the module notes); ``SIX_INSERTIONS[0]`` is the one
#: whose six labels are mirror closed.
SIX_INSERTIONS: List[List[Tuple[Q, Q]]] = [
    [(Q(-2, 3), Q(-1, 3)), (Q(1, 3), Q(-1, 3)), (Q(1, 3), Q(2, 3)),
     (Q(2, 3), Q(1, 3)), (Q(-1, 3), Q(1, 3)), (Q(-1, 3), Q(-2, 3))],
    [(Q(1), Q(-1)), (Q(-1), Q(0)), (Q(2), Q(-1)),
     (Q(-1), Q(2)), (Q(0), Q(-1)), (Q(-1), Q(1))],
    [(Q(-1, 3), Q(1, 3)), (Q(-1, 3), Q(-2, 3)), (Q(2, 3), Q(1, 3)),
     (Q(1, 3), Q(2, 3)), (Q(-2, 3), Q(-1, 3)), (Q(1, 3), Q(-1, 3))],
    [(Q(1, 3), Q(1)), (Q(-2, 3), Q(-1)), (Q(-1, 3), Q(0)),
     (Q(4, 3), Q(1)), (Q(-1), Q(-1)), (Q(1, 3), Q(0))],
    [(Q(-1, 5), Q(1, 5)), (Q(-2, 5), Q(-3, 5)), (Q(1, 5), Q(4, 5)),
     (Q(4, 5), Q(1, 5)), (Q(-3, 5), Q(-2, 5)), (Q(1, 5), Q(-1, 5))],
    [(Q(0), Q(1, 3)), (Q(-1), Q(-1)), (Q(1), Q(4, 3)),
     (Q(0), Q(-1, 3)), (Q(-1), Q(-2, 3)), (Q(1), Q(1, 3))],
]


def _apply_form(form: Sequence[Tuple[Q, Q]], left: int, right: int, n: int) -> Optional[List[int]]:
    out = []
    for a, b in form:
        try:
            va = a.numerator * inv_mod(a.denominator, n) % n if a.denominator != 1 else a.numerator % n
            vb = b.numerator * inv_mod(b.denominator, n) % n if b.denominator != 1 else b.numerator % n
        except ValueError:
            return None
        out.append((va * left + vb * right) % n)
    return out


def six_insertions_mod(left: int, right: int, n: int) -> List[List[int]]:
    """All admissible six-label endpoint-preserving insertions in ``Z_n``."""
    out = []
    for form in SIX_INSERTIONS:
        block = _apply_form(form, left, right, n)
        if block is None:
            continue
        if check_insertion(left, right, block, n):
            out.append(block)
    return out


def twelve_insertion_mod(left: int, right: int, t: int, n: int) -> List[int]:
    """``ROUTE_CORE_FLEXIBLE_TWELVE_INSERTION_20260901.md`` section 1, in Z_n."""
    u0 = (2 * left + right - 2 * t) % n
    u1 = (t - left) % n
    u2 = (left + right - t) % n
    u3 = (3 * t - 2 * left - right) % n
    u4 = t % n
    u5 = (2 * t - left) % n
    return [u1, (-u5) % n, u4, (-u0) % n, (-u1) % n, u2,
            u3, (-u4) % n, u0, u5, (-u3) % n, (-u2) % n]


def check_insertion(left: int, right: int, block: Sequence[int], n: int) -> bool:
    """The inserted block keeps ``P = O`` at the two enclosing vertices."""
    path = [left] + list(block) + [right]
    sums = Counter((path[i] + path[i + 1]) % n for i in range(len(path) - 1))
    target = Counter(list(block) + [(left + right) % n])
    return sums == target


# ==========================================================================
# 3.  The physical scheduler (Lemma B / Lemma C with edge bookkeeping)
# ==========================================================================

@dataclass
class ArmPlan:
    """A residual arm or a neutral-unit arm: the concrete path below an owner."""
    core_child: int
    raw_length: int              # number of degree-two vertices on the arm
    reduced: int                 # alphabet representative (1..6 or 1..8)
    edges: List[int]             # child vertices of the arm edges, top first
    slot: Optional[int] = None   # family arm index once assigned
    mothers: int = 0
    values: List[int] = field(default_factory=list)


@dataclass
class UnitPlan:
    kind: str                    # "pair" | "four_short"
    arms: List[ArmPlan]
    base: List[List[int]] = field(default_factory=list)
    scale: int = 0
    source: Optional[str] = None


@dataclass
class NodePlan:
    vertex: int
    is_root: bool
    is_owner: bool = False
    folded: bool = False         # an L1 child folded into its parent's cell
    ctx: Optional[dict] = None
    key: Optional[str] = None
    h_raw: int = 0
    head_edges: List[int] = field(default_factory=list)   # top first
    arms: List[ArmPlan] = field(default_factory=list)
    units: List[UnitPlan] = field(default_factory=list)
    ports: List[int] = field(default_factory=list)        # port edge children
    recruited: List[int] = field(default_factory=list)
    ordinary: List[int] = field(default_factory=list)
    active: List[int] = field(default_factory=list)       # active core children
    cancelled: List[List[int]] = field(default_factory=list)
    retained: Optional[int] = None
    kept: List[int] = field(default_factory=list)
    kept_roles: List[str] = field(default_factory=list)
    passthrough: Optional[str] = None
    child_type: str = "none"
    absorption: Optional[dict] = None
    notes: List[str] = field(default_factory=list)
    # realisation results
    family_index: Optional[int] = None
    family: Optional[ftl.Family] = None
    params: Optional[Dict[str, int]] = None
    labels: Optional[Dict[str, int]] = None
    head_value: Optional[int] = None
    token: Optional[dict] = None
    synth: Optional[dict] = None



def relabel_to_root(parent: Sequence[int], root: int) -> Tuple[List[int], List[int]]:
    """``(old_of, new_of)`` with the chosen root renumbered to vertex 0."""
    n = len(parent)
    order = [root] + [v for v in range(n) if v != root]
    new_of = [0] * n
    for i, v in enumerate(order):
        new_of[v] = i
    return order, new_of


def translate_schedule(sched: dict, old_of: Sequence[int]) -> dict:
    """Renumber every vertex in a ``schedule()`` result back to the input ids."""
    def tv(x):
        return int(old_of[int(x)])

    def tedges(seq):
        return [[tv(a), tv(b)] for a, b in seq]

    rows = {}
    for k, row in sched["rows"].items():
        r = dict(row)
        r["vertex"] = tv(row["vertex"])
        r["head_chain_edges"] = tedges(row.get("head_chain_edges") or [])
        r["arms"] = [dict(a, child=tv(a["child"]), edges=tedges(a["edges"]))
                     for a in row.get("arms") or []]
        r["neutral_units"] = [dict(u, children=[tv(c) for c in u["children"]])
                              for u in row.get("neutral_units") or []]
        rep = row.get("repair")
        r["repair"] = (dict(rep, children=[tv(c) for c in rep["children"]])
                       if rep else None)
        r["ports"] = [tv(c) for c in row.get("ports") or []]
        r["active_edges"] = [dict(a, child=tv(a["child"]),
                                  edges=tedges(a["edges"]))
                             for a in row.get("active_edges") or []]
        r["cancelled_active_groups"] = [
            dict(g, children=[tv(c) for c in g["children"]])
            for g in row.get("cancelled_active_groups") or []]
        ha = row.get("helper_absorption")
        if ha:
            ha = dict(ha)
            ha["ports"] = [tv(c) for c in ha.get("ports") or []]
            if ha.get("active_child") is not None:
                ha["active_child"] = tv(ha["active_child"])
            if ha.get("cancelled_group_children"):
                ha["cancelled_group_children"] = [
                    tv(c) for c in ha["cancelled_group_children"]]
        r["helper_absorption"] = ha
        rows[tv(k)] = r
    return {"n": sched["n"], "is_path": sched["is_path"],
            "root": tv(sched["root"]),
            "core_vertices": [tv(v) for v in sched["core_vertices"]],
            "owners": [{"vertex": tv(o["vertex"]),
                        "context_key": o["context_key"]}
                       for o in sched["owners"]],
            "rows": rows, "uncovered": sched.get("uncovered") or [],
            "l1_pair_events": sched.get("l1_pair_events") or []}


ARMS_CELL_ROLES = ("residual", "repair_retained")
KEPT_ROLES = ("kept_free", "kept_L1", "kept_V21", "kept_V22",
              "kept_act2_1", "kept_act2_2")


def parse_context_key(key: str) -> dict:
    """``h0_1-3-2_p1_act`` -> ``{"head":0,"arms":[1,3,2],"ports":1,"tag":"act"}``.

    Raises ``ValueError`` for anything that is not an alphabet context key
    (the constructor also mints synthetic keys such as
    ``joint(stationary|h0_1_p1_bot)``); use :func:`safe_context_key` when the
    key may be one of those.
    """
    parts = key.split("_", 3)
    if len(parts) != 4:
        raise ValueError(f"not a context key: {key!r}")
    head, arms, ports, tag = parts
    if head != "root" and not (head.startswith("h") and head[1:].isdigit()):
        raise ValueError(f"not a context key: {key!r}")
    if not (ports.startswith("p") and ports[1:].isdigit()):
        raise ValueError(f"not a context key: {key!r}")
    return {"root": head == "root",
            "head": 0 if head == "root" else int(head[1:]),
            "arms": [] if arms == "none" else [int(x) for x in arms.split("-")],
            "ports": int(ports[1:]), "tag": tag}


def safe_context_key(key: Optional[str]) -> Optional[dict]:
    """:func:`parse_context_key`, or ``None`` for a synthetic/absent key."""
    if not key:
        return None
    try:
        return parse_context_key(key)
    except ValueError:
        return None


def assign_arm_values(arms: List[ArmPlan], values: Sequence[int]) -> Optional[List[ArmPlan]]:
    """Order the concrete arms so that arm ``i`` reduces to ``values[i]``."""
    if len(arms) != len(values):
        return None
    for perm in itertools.permutations(range(len(arms))):
        ok = True
        for slot, ai in enumerate(perm):
            raw, val = arms[ai].raw_length, values[slot]
            if raw < val or (raw - val) % 6:
                ok = False
                break
        if ok:
            out = []
            for slot, ai in enumerate(perm):
                arms[ai].reduced = values[slot]
                out.append(arms[ai])
            return out
    return None


class Plan:
    """The physical decomposition, read from ``context_scheduler.schedule``.

    The scheduler is the authority for Lemma B/C: which vertices are owners,
    their context keys, which tree edges form each head chain, arm, neutral
    unit and port, which active children are cancelled and which is kept, and
    where a helper / two-port absorption sits.  This class only translates
    that record into the constructor's :class:`NodePlan` objects.
    """

    def __init__(self, n: int, parent: List[int], children: List[List[int]],
                 root: int, sched: dict) -> None:
        self.n = n
        self.parent = parent
        self.children = children
        self.root = root
        self.sched = sched
        self.nodes: Dict[int, NodePlan] = {}
        self._children_of: Dict[int, List[int]] = {}
        self._parent_core: Dict[int, int] = {}
        self.notes: List[str] = []
        self._build()

    # -- accessors used by the realiser ----------------------------------
    def children_of(self, v: int) -> List[int]:
        return self._children_of.get(v, [])

    def parent_core(self, v: int) -> Optional[int]:
        return self._parent_core.get(v)

    # -- translation ------------------------------------------------------
    def _build(self) -> None:
        rows = {int(k): row for k, row in self.sched["rows"].items()}
        for v, row in rows.items():
            node = NodePlan(vertex=v, is_root=bool(row.get("is_root")))
            node.key = row.get("context_key")
            # a V21/V22 passthrough vertex is marked is_owner by the scheduler
            # but emits no key of its own: its cell is a row of its parent's
            # macro, so the constructor does not realise it separately
            node.is_owner = bool(row.get("is_owner")) and node.key is not None
            node.passthrough = row.get("passthrough")
            node.head_edges = [int(e[1]) for e in row.get("head_chain_edges") or []]
            node.h_raw = max(0, len(node.head_edges) - 1)
            node.ports = [int(c) for c in row.get("ports") or []]
            p = row.get("recruited_ports")
            p = 0 if p is None else int(p)
            node.recruited = node.ports[:p]
            node.ordinary = node.ports[p:]

            cell_arms: List[ArmPlan] = []
            groups: Dict[int, List[ArmPlan]] = {}
            group_kind: Dict[int, str] = {}
            for a in row.get("arms") or []:
                arm = ArmPlan(core_child=int(a["child"]), raw_length=int(a["length"]),
                              reduced=cs.reduce6(int(a["length"])),
                              edges=[int(e[1]) for e in a["edges"]])
                if a.get("role") in ARMS_CELL_ROLES:
                    cell_arms.append(arm)
                else:
                    gid = int(a.get("group_id", -1))
                    groups.setdefault(gid, []).append(arm)
                    group_kind[gid] = ("pair" if a.get("role") == "neutral_pair"
                                       else "four_short")
            node.arms = cell_arms
            node.units = [UnitPlan(kind=group_kind[g], arms=groups[g])
                          for g in sorted(groups)]

            kept: List[int] = []
            kept_roles: List[str] = []
            for ae in row.get("active_edges") or []:
                c = int(ae["child"])
                if ae.get("role") in KEPT_ROLES:
                    kept.append(c)
                    kept_roles.append(str(ae["role"]))
                node.active.append(c)
            node.cancelled = [[int(c) for c in g["children"]]
                              for g in row.get("cancelled_active_groups") or []]
            node.kept = kept
            node.kept_roles = kept_roles
            node.retained = kept[0] if kept else None
            if kept_roles:
                node.child_type = {"kept_free": "free", "kept_L1": "L1",
                                   "kept_V21": "V21", "kept_V22": "V22",
                                   "kept_act2_1": "act2", "kept_act2_2": "act2"
                                   }.get(kept_roles[0], "free")
            else:
                node.child_type = "none"

            ha = row.get("helper_absorption")
            if ha:
                tech = ha.get("technique")
                if tech == "cancelled_group_rebalance":
                    node.absorption = {"type": "port_into_group",
                                       "port": int(ha["ports"][0])}
                    node.ordinary = [c for c in node.ordinary
                                     if c != int(ha["ports"][0])]
                else:
                    node.absorption = {"type": "port_block",
                                       "ports": [int(c) for c in ha.get("ports") or []]}
            spec = safe_context_key(node.key) if node.is_owner else None
            if spec is not None:
                ordered = assign_arm_values(node.arms, spec["arms"])
                if ordered is None:
                    raise Failure("scheduler",
                                  f"cell arms {[a.raw_length for a in node.arms]} do "
                                  f"not reduce to the context arms {spec['arms']}",
                                  vertex=v, context=node.key)
                node.arms = ordered
            self.nodes[v] = node

        # core adjacency
        for v, node in self.nodes.items():
            kids = [a.core_child for a in node.arms]
            for u in node.units:
                kids += [a.core_child for a in u.arms]
            kids += list(node.active)
            kids += list(node.ports)
            kids = [c for c in kids if c in self.nodes]
            self._children_of[v] = kids
            for c in kids:
                self._parent_core[c] = v

    def cross_check(self) -> List[str]:
        """The schedule is the authority; only its own gaps are reported."""
        problems = []
        for u in self.sched.get("uncovered") or []:
            problems.append(f"scheduler uncovered: {u}")
        return problems


# ==========================================================================
# 3b.  Local cell synthesis (fallback when the catalogue has no family)
# ==========================================================================
#
# The assembled catalogue ``data/alphabet_families.json`` is incomplete: the
# dedicated root pass had not finished when it was written, so several small
# root contexts (``root_1_p0_bot``, ``root_1_p2_bot``, ...) carry no family.
# For a *constructor* the missing entry can simply be re-derived: a cell of
# width ``w`` has exactly ``w`` outputs, and ``P' = O`` is the statement that
# some bijection from outputs to labels holds identically.  Enumerating those
# bijections with incremental Gaussian elimination (pruning as soon as the
# nullspace collapses) produces the same objects the symbolic CP-SAT search
# produces, without a solver.  The rational nullspace is cached per topology
# signature and reduced mod ``n`` on use.

SYNTH_CAP = 10          # maximum width for the bijection enumeration
SYNTH_NODES = 400_000   # search-node budget per topology
_SYNTH_CACHE: Dict[tuple, List[Tuple[List[str], List[List[Q]]]]] = {}



def row_kept(rs) -> List[str]:
    """Kept child labels of a row, across free_token_lib layouts."""
    kept = getattr(rs, "kept", None)
    if kept is not None:
        return list(kept)
    return [rs.child] if getattr(rs, "child_kind", None) in ("input", "active") else []


def row_children(rs) -> List[str]:
    """Physical children inside the owner output (shared edge plus kept)."""
    shared = getattr(rs, "shared", None)
    return ([shared] if shared else []) + row_kept(rs)


def multi_label_names(rows: Sequence[dict]) -> Tuple[List[str], List]:
    """Label names and row structures of a multi-row joint macro.

    ``rows[k]`` is ``{"root": bool, "head": int, "arms": [int], "ports": int,
    "input": bool}``; row ``k < len-1`` shares its child edge with row ``k+1``
    (the "whole-parent reopen" of ROUTE_CORE section 0 / proof draft 8b: a
    forced-antipode child is not composed as a black box but joined with its
    parent into one macro).
    """
    names: List[str] = []
    structs = []
    for k, row in enumerate(rows):
        last = k == len(rows) - 1
        chain: List[str] = []
        if not row.get("root"):
            chain.append(f"g{k}")
            chain += [f"r{k}h{i}" for i in range(1, int(row.get("head") or 0) + 1)]
        arm_names = [[f"r{k}a{a}x{i}" for i in range(ell + 1)]
                     for a, ell in enumerate(row.get("arms") or [])]
        port_names = [f"r{k}p{i}" for i in range(int(row.get("ports") or 0))]
        names += chain
        for arm in arm_names:
            names += arm
        names += port_names
        has_input = bool(row.get("input")) and last
        if has_input:
            names.append("x")
        spec = {"head": int(row.get("head") or 0), "arms": list(row.get("arms") or []),
                "ports": int(row.get("ports") or 0), "root": bool(row.get("root")),
                "input": int(has_input), "active": int(has_input or not last)}
        kept = ["x"] if has_input else []
        shared = None if last else f"g{k + 1}"
        try:
            rs = ftl.RowStructure(index=k, is_root=bool(row.get("root")),
                                  chain=chain, arms=arm_names, ports=port_names,
                                  shared=shared, kept=kept,
                                  kept_kinds=(["input"] if has_input else []),
                                  inputs=list(kept), spec=spec)
        except TypeError:
            rs = ftl.RowStructure(index=k, is_root=bool(row.get("root")),
                                  chain=chain, arms=arm_names, ports=port_names,
                                  shared=shared,
                                  child=(shared or (kept[0] if kept else None)),
                                  child_kind=("shared" if shared else
                                              ("input" if kept else None)),
                                  input=(kept[0] if kept else None),
                                  active=None, spec=spec)
        structs.append(rs)
    return names, structs


def multi_output_forms(names: Sequence[str], structs: Sequence,
                       has_zero: bool) -> Tuple[List[List[Q]], List[List[Q]]]:
    idx = {nm: i for i, nm in enumerate(names)}
    w = len(names)

    def unit(nm: str) -> List[Q]:
        v = [Q(0)] * w
        v[idx[nm]] = Q(1)
        return v

    def add(*vs):
        out = [Q(0)] * w
        for v in vs:
            out = [a + b for a, b in zip(out, v)]
        return out

    outs: List[List[Q]] = []
    for rs in structs:
        for i in range(len(rs.chain) - 1):
            outs.append(add(unit(rs.chain[i]), unit(rs.chain[i + 1])))
        terms = []
        if rs.chain:
            terms.append(unit(rs.chain[-1]))
        for arm in rs.arms:
            terms.append(unit(arm[0]))
        for pnm in rs.ports:
            terms.append(unit(pnm))
        for nm in row_children(rs):
            terms.append(unit(nm))
        outs.append(add(*terms))
        for arm in rs.arms:
            for i in range(len(arm) - 1):
                outs.append(add(unit(arm[i]), unit(arm[i + 1])))
            outs.append(unit(arm[-1]))
        for pnm in rs.ports:
            outs.append(unit(pnm))
        for nm in row_kept(rs):
            outs.append(unit(nm))
    phys = [unit(nm) for nm in names]
    if has_zero:
        phys.append([Q(0)] * w)
    return outs, phys


_GROUP_CACHE: Dict[tuple, List[Tuple[List[str], List[List[int]]]]] = {}


def synth_group(specs: Sequence[dict], cap: int = SYNTH_CAP
                ) -> List[Tuple[List[str], List[List[int]]]]:
    """Joint realisation of a *cancelled active group* as one macro.

    A stationary vertex with two (or three) active owner children forces their
    heads to sum to zero (Lemma C step 2).  Composing the children as separate
    black boxes then fails exactly for the forced-antipode types of proof
    draft 8b -- a child whose family contains the antipode of its own head
    collides with its sibling's head.  Dropping the requirement that each
    child is individually ``P = O`` and asking only that the *union* is (with
    the head sum still zero) is the group version of the whole-parent reopen,
    and it has solutions where the separate composition has none.
    """
    sig = tuple((int(sp.get("head") or 0), tuple(sp.get("arms") or []),
                 int(sp.get("ports") or 0), int(sp.get("inputs") or 0))
                for sp in specs) + (cap,)
    hit = _GROUP_CACHE.get(sig)
    if hit is not None:
        return hit
    names: List[str] = []
    structs = []
    for k, sp in enumerate(specs):
        chain = [f"g{k}"] + [f"r{k}h{i}" for i in range(1, int(sp.get("head") or 0) + 1)]
        arm_names = [[f"r{k}a{a}x{i}" for i in range(ell + 1)]
                     for a, ell in enumerate(sp.get("arms") or [])]
        port_names = [f"r{k}p{i}" for i in range(int(sp.get("ports") or 0))]
        in_names = [f"x{k}_{j}" for j in range(int(sp.get("inputs") or 0))]
        names += chain
        for arm in arm_names:
            names += arm
        names += port_names + in_names
        structs.append((chain, arm_names, port_names, in_names))
    w = len(names)
    if w > cap:
        _GROUP_CACHE[sig] = []
        return []
    idx = {nm: i for i, nm in enumerate(names)}

    def unit(nm):
        v = [Q(0)] * w
        v[idx[nm]] = Q(1)
        return v

    def add(*vs):
        out = [Q(0)] * w
        for v in vs:
            out = [a + b for a, b in zip(out, v)]
        return out

    outs: List[List[Q]] = []
    for chain, arm_names, port_names, in_names in structs:
        for i in range(len(chain) - 1):
            outs.append(add(unit(chain[i]), unit(chain[i + 1])))
        terms = [unit(chain[-1])]
        terms += [unit(a[0]) for a in arm_names]
        terms += [unit(pn) for pn in port_names]
        terms += [unit(xn) for xn in in_names]
        outs.append(add(*terms))
        for arm in arm_names:
            for i in range(len(arm) - 1):
                outs.append(add(unit(arm[i]), unit(arm[i + 1])))
            outs.append(unit(arm[-1]))
        for pn in port_names:
            outs.append(unit(pn))
        for xn in in_names:
            outs.append(unit(xn))
    phys = [unit(nm) for nm in names]
    if len(outs) != len(phys):
        _GROUP_CACHE[sig] = []
        return []
    head_eq = add(*[unit(st[0][0]) for st in structs])

    nodes_budget, want = synth_budget(w)
    found: List[Tuple[List[str], List[List[int]]]] = []
    seen: set = set()
    rng = random.Random(31337)
    budget = [max(nodes_budget, 120_000)]

    def nondegenerate(basis):
        if not basis:
            return False
        for _ in range(12):
            coef = [Q(rng.randint(-20, 20)) for _ in basis]
            vals = [sum((c * b[i] for c, b in zip(coef, basis)), Q(0))
                    for i in range(w)]
            if any(v == 0 for v in vals) or len(set(vals)) != w:
                continue
            return True
        return False

    def rec(k: int, used: int, elim: _Elim) -> None:
        if len(found) >= want or budget[0] <= 0:
            return
        budget[0] -= 1
        if k == len(outs):
            basis = elim.nullspace()
            if not nondegenerate(basis):
                return
            ib = _integralise(basis)
            key = tuple(tuple(r) for r in ib)
            if key in seen:
                return
            seen.add(key)
            found.append((list(names), ib))
            return
        for j in range(len(phys)):
            if used >> j & 1:
                continue
            child = elim.copy()
            if not child.add([a - b for a, b in zip(outs[k], phys[j])]):
                continue
            rec(k + 1, used | (1 << j), child)
            if len(found) >= want:
                return

    start = _Elim(w)
    if start.add(head_eq):
        rec(0, 0, start)
    _GROUP_CACHE[sig] = found
    return found


_JOINT_CACHE: Dict[tuple, List[Tuple[List[str], List[List[int]]]]] = {}


def synth_joint(rows: Sequence[dict], cap: int = SYNTH_CAP
                ) -> List[Tuple[List[str], List[List[int]]]]:
    """Nondegenerate ``P' = O`` families for a multi-row joint macro."""
    sig = tuple((bool(r.get("root")), int(r.get("head") or 0),
                 tuple(r.get("arms") or []), int(r.get("ports") or 0),
                 bool(r.get("input"))) for r in rows) + (cap,)
    hit = _JOINT_CACHE.get(sig)
    if hit is not None:
        return hit
    names, structs = multi_label_names(rows)
    w = len(names)
    if w > cap:
        _JOINT_CACHE[sig] = []
        return []
    is_root = bool(rows[0].get("root"))
    outs, phys = multi_output_forms(names, structs, has_zero=is_root)
    if len(outs) != len(phys):
        _JOINT_CACHE[sig] = []
        return []
    nodes_budget, want = synth_budget(w)
    found: List[Tuple[List[str], List[List[int]]]] = []
    seen: set = set()
    rng = random.Random(4242)
    budget = [nodes_budget]

    def nondegenerate(basis):
        if not basis:
            return False
        for _ in range(12):
            coef = [Q(rng.randint(-20, 20)) for _ in basis]
            vals = [sum((c * b[i] for c, b in zip(coef, basis)), Q(0))
                    for i in range(w)]
            if any(v == 0 for v in vals) or len(set(vals)) != w:
                continue
            return True
        return False

    def rec(k: int, used: int, elim: _Elim) -> None:
        if len(found) >= want or budget[0] <= 0:
            return
        budget[0] -= 1
        if k == len(outs):
            basis = elim.nullspace()
            if not nondegenerate(basis):
                return
            ib = _integralise(basis)
            key = tuple(tuple(r) for r in ib)
            if key in seen:
                return
            seen.add(key)
            found.append((list(names), ib))
            return
        for j in range(len(phys)):
            if used >> j & 1:
                continue
            child = elim.copy()
            if not child.add([a - b for a, b in zip(outs[k], phys[j])]):
                continue
            rec(k + 1, used | (1 << j), child)
            if len(found) >= want:
                return

    rec(0, 0, _Elim(w))
    _JOINT_CACHE[sig] = found
    return found


def cell_label_names(is_root: bool, h: int, arms: Sequence[int], ports: int,
                     has_input: bool) -> Tuple[List[str], ftl.RowStructure]:
    """Label names and the row structure of a one-row cell topology."""
    chain: List[str] = []
    if not is_root:
        chain.append("g0")
        chain += [f"r0h{i}" for i in range(1, h + 1)]
    arm_names = [[f"r0a{a}x{i}" for i in range(ell + 1)]
                 for a, ell in enumerate(arms)]
    port_names = [f"r0p{i}" for i in range(ports)]
    names = list(chain)
    for arm in arm_names:
        names += arm
    names += port_names
    if has_input:
        names.append("x")
    spec = {"head": h, "arms": list(arms), "ports": ports,
            "root": is_root, "input": int(has_input), "active": int(has_input)}
    kept = ["x"] if has_input else []
    try:                       # current free_token_lib (kept / kept_kinds)
        rs = ftl.RowStructure(
            index=0, is_root=is_root, chain=chain, arms=arm_names,
            ports=port_names, shared=None, kept=kept,
            kept_kinds=(["input"] if has_input else []),
            inputs=list(kept), spec=spec)
    except TypeError:          # older layout (child / child_kind)
        rs = ftl.RowStructure(
            index=0, is_root=is_root, chain=chain, arms=arm_names,
            ports=port_names, shared=None,
            child=("x" if has_input else None),
            child_kind=("input" if has_input else None),
            input=("x" if has_input else None), active=None, spec=spec)
    return names, rs


def cell_output_forms(names: Sequence[str], rs: ftl.RowStructure,
                      has_zero: bool) -> Tuple[List[List[Q]], List[List[Q]]]:
    """``(output forms, physical forms)`` as coefficient vectors over ``names``."""
    idx = {nm: i for i, nm in enumerate(names)}
    w = len(names)

    def unit(nm: str) -> List[Q]:
        v = [Q(0)] * w
        v[idx[nm]] = Q(1)
        return v

    def add(*vs: Sequence[Q]) -> List[Q]:
        out = [Q(0)] * w
        for v in vs:
            out = [a + b for a, b in zip(out, v)]
        return out

    outs: List[List[Q]] = []
    for i in range(len(rs.chain) - 1):
        outs.append(add(unit(rs.chain[i]), unit(rs.chain[i + 1])))
    terms = []
    if rs.chain:
        terms.append(unit(rs.chain[-1]))
    for arm in rs.arms:
        terms.append(unit(arm[0]))
    for p in rs.ports:
        terms.append(unit(p))
    for nm in row_children(rs):
        terms.append(unit(nm))
    outs.append(add(*terms))
    for arm in rs.arms:
        for i in range(len(arm) - 1):
            outs.append(add(unit(arm[i]), unit(arm[i + 1])))
        outs.append(unit(arm[-1]))
    for p in rs.ports:
        outs.append(unit(p))
    for nm in row_kept(rs):
        outs.append(unit(nm))
    phys = [unit(nm) for nm in names]
    if has_zero:
        phys.append([Q(0)] * w)
    return outs, phys


class _Elim:
    """Incremental Gaussian elimination over Q (rows kept in reduced form)."""

    def __init__(self, w: int) -> None:
        self.w = w
        self.rows: List[List[Q]] = []
        self.pivots: List[int] = []

    def copy(self) -> "_Elim":
        e = _Elim(self.w)
        e.rows = [list(r) for r in self.rows]
        e.pivots = list(self.pivots)
        return e

    def add(self, row: Sequence[Q]) -> bool:
        """Add an equation ``row . z = 0``; ``False`` if the system dies."""
        r = list(row)
        for piv, prow in zip(self.pivots, self.rows):
            if r[piv]:
                f = r[piv]
                r = [a - f * b for a, b in zip(r, prow)]
        nz = next((i for i in range(self.w) if r[i]), None)
        if nz is None:
            return True
        f = r[nz]
        r = [a / f for a in r]
        self.rows = [[a - row2[nz] * b for a, b in zip(row2, r)]
                     for row2 in self.rows]
        self.rows.append(r)
        self.pivots.append(nz)
        return len(self.pivots) < self.w

    def nullspace(self) -> List[List[Q]]:
        free = [i for i in range(self.w) if i not in self.pivots]
        basis = []
        for fc in free:
            v = [Q(0)] * self.w
            v[fc] = Q(1)
            for piv, prow in zip(self.pivots, self.rows):
                v[piv] = -prow[fc]
            basis.append(v)
        return basis


def _integralise(basis: List[List[Q]]) -> List[List[int]]:
    out = []
    for v in basis:
        den = 1
        for x in v:
            den = den * x.denominator // math.gcd(den, x.denominator)
        row = [int(x * den) for x in v]
        g = 0
        for x in row:
            g = math.gcd(g, abs(x))
        if g > 1:
            row = [x // g for x in row]
        out.append(row)
    return out


def synth_budget(w: int) -> Tuple[int, int]:
    """``(node budget, families wanted)`` for a topology of width ``w``."""
    if w <= 8:
        return SYNTH_NODES, 6
    if w == 9:
        return 20_000, 3
    return 12_000, 2


def synth_topology(is_root: bool, h: int, arms: Tuple[int, ...], ports: int,
                   has_input: bool, cap: int = SYNTH_CAP,
                   max_families: int = 0) -> List[Tuple[List[str], List[List[int]]]]:
    """Nondegenerate ``P' = O`` families for a topology, as integer nullspaces."""
    sig = (is_root, h, tuple(arms), ports, has_input, cap, max_families)
    hit = _SYNTH_CACHE.get(sig)
    if hit is not None:
        return hit
    names, rs = cell_label_names(is_root, h, arms, ports, has_input)
    w = len(names)
    if w > cap:
        _SYNTH_CACHE[sig] = []
        return []
    nodes_budget, want = synth_budget(w)
    if max_families <= 0:
        max_families = want
    outs, phys = cell_output_forms(names, rs, has_zero=is_root)
    if len(outs) != len(phys):
        _SYNTH_CACHE[sig] = []
        return []
    found: List[Tuple[List[str], List[List[int]]]] = []
    seen: set = set()
    m = len(outs)
    rng = random.Random(12345)
    budget = [nodes_budget]

    def nondegenerate(basis: List[List[Q]]) -> bool:
        if not basis:
            return False
        for _ in range(12):
            coef = [Q(rng.randint(-20, 20)) for _ in basis]
            vals = [sum((c * b[i] for c, b in zip(coef, basis)), Q(0))
                    for i in range(w)]
            if any(v == 0 for v in vals):
                continue
            if len(set(vals)) != w:
                continue
            return True
        return False

    def rec(k: int, used: int, elim: _Elim) -> None:
        if len(found) >= max_families or budget[0] <= 0:
            return
        budget[0] -= 1
        if k == m:
            basis = elim.nullspace()
            if not nondegenerate(basis):
                return
            ib = _integralise(basis)
            key = tuple(tuple(r) for r in ib)
            if key in seen:
                return
            seen.add(key)
            found.append((list(names), ib))
            return
        for j in range(len(phys)):
            if used >> j & 1:
                continue
            eq = [a - b for a, b in zip(outs[k], phys[j])]
            child = elim.copy()
            if not child.add(eq):
                continue
            rec(k + 1, used | (1 << j), child)
            if len(found) >= max_families:
                return

    rec(0, 0, _Elim(w))
    _SYNTH_CACHE[sig] = found
    return found




#: Rigid residue-two row of ``ROUTE_CORE_FREE_TOKEN_PROGRAM_20260901.md``
#: section 6 / the coordinator's note: ``(-3x/2; -x/2, -x, x/2; x)``.  With
#: ``t = x/2`` the labels are ``(-3t; -t, -2t, t; 2t)``, so the whole row is
#: the one-parameter sublattice below.  ``synth_topology`` finds a strictly
#: larger two-parameter family for the same context (the head stays free once
#: ``x`` is pinned), which the constructor prefers; the rigid row is kept as an
#: explicit fallback and is what gets reported when it is used.
RESIDUE2_RIGID_NAMES = ["g0", "r0a0x0", "r0a0x1", "r0a0x2", "x"]
RESIDUE2_RIGID_BASIS = [[-3, -1, -2, 1, 2]]

FOUR_LAYER_PATH = os.path.join(DATA, "family_r2222_L12.json")


def four_layer_family() -> Optional[ftl.Family]:
    """The residue-two four-layer reset joint, verified through free_token_lib."""
    try:
        with open(FOUR_LAYER_PATH) as fh:
            payload = json.load(fh)
        fam = ftl.Family(payload, key="r2222_L12")
        report = fam.verify_symbolic()
        return fam if report.get("ok") else None
    except Exception:
        return None


_UNIT_CACHE: Dict[tuple, List[Tuple[List[str], List[List[int]]]]] = {}


def synth_unit(lengths: Tuple[int, ...], cap: int = SYNTH_CAP,
               max_families: int = 0) -> List[Tuple[List[str], List[List[int]]]]:
    """Owner-free neutral unit of the given arm lengths, derived directly.

    A neutral unit is a set of arms hanging at one vertex whose head labels
    sum to zero and whose outputs (adjacent sums plus the terminals) permute
    its labels; ``ROUTE_CORE_OWNER_NEUTRALIZATION_REDUCTION.md`` section 1 and
    ``ODD_CHAIN_PAIRS.md`` section 2 give the proved integer bases, which this
    routine reproduces (and generalises to any small shape) by enumerating the
    output bijections.
    """
    sig = (tuple(lengths), cap, max_families)
    hit = _UNIT_CACHE.get(sig)
    if hit is not None:
        return hit
    names: List[str] = []
    arms: List[List[str]] = []
    for a, ell in enumerate(lengths):
        arm = [f"u{a}x{i}" for i in range(ell + 1)]
        arms.append(arm)
        names += arm
    w = len(names)
    if w > cap:
        _UNIT_CACHE[sig] = []
        return []
    nodes_budget, want = synth_budget(w)
    if max_families <= 0:
        max_families = max(want, 4)
    idx = {nm: i for i, nm in enumerate(names)}

    def unit(nm: str) -> List[Q]:
        v = [Q(0)] * w
        v[idx[nm]] = Q(1)
        return v

    def add(*vs):
        out = [Q(0)] * w
        for v in vs:
            out = [x + y for x, y in zip(out, v)]
        return out

    outs: List[List[Q]] = []
    for arm in arms:
        for i in range(len(arm) - 1):
            outs.append(add(unit(arm[i]), unit(arm[i + 1])))
        outs.append(unit(arm[-1]))
    phys = [unit(nm) for nm in names]
    head_eq = add(*[unit(arm[0]) for arm in arms])

    found: List[Tuple[List[str], List[List[int]]]] = []
    seen: set = set()
    rng = random.Random(999)
    budget = [nodes_budget]

    def nondegenerate(basis):
        if not basis:
            return False
        for _ in range(12):
            coef = [Q(rng.randint(-20, 20)) for _ in basis]
            vals = [sum((c * b[i] for c, b in zip(coef, basis)), Q(0))
                    for i in range(w)]
            if any(v == 0 for v in vals) or len(set(vals)) != w:
                continue
            return True
        return False

    def rec(k: int, used: int, elim: _Elim) -> None:
        if len(found) >= max_families or budget[0] <= 0:
            return
        budget[0] -= 1
        if k == len(outs):
            basis = elim.nullspace()
            if not nondegenerate(basis):
                return
            ib = _integralise(basis)
            key = tuple(tuple(r) for r in ib)
            if key in seen:
                return
            seen.add(key)
            found.append((list(names), ib))
            return
        for j in range(len(phys)):
            if used >> j & 1:
                continue
            child = elim.copy()
            if not child.add([a - b for a, b in zip(outs[k], phys[j])]):
                continue
            rec(k + 1, used | (1 << j), child)
            if len(found) >= max_families:
                return

    start = _Elim(w)
    if start.add(head_eq):
        rec(0, 0, start)
    _UNIT_CACHE[sig] = found
    return found



def basis_forced_ratios(names: Sequence[str], basis: Sequence[Sequence[int]]) -> set:
    """Ratios ``q`` with a label identically equal to ``q * x`` on the family."""
    if "x" not in names:
        return set()
    xi = list(names).index("x")
    out = set()
    for i, nm in enumerate(names):
        if nm == "x":
            continue
        q = None
        ok = True
        for b in basis:
            if b[xi] == 0:
                if b[i] != 0:
                    ok = False
                    break
                continue
            r = Q(b[i], b[xi])
            if q is None:
                q = r
            elif q != r:
                ok = False
                break
        if ok and q is not None:
            out.add(q)
    return out


def gauss_mod(rows: Sequence[Sequence[int]], rhs: Sequence[int], k: int,
              n: int) -> Optional[Tuple[List[int], List[int], List[List[int]], List[int]]]:
    """Reduce ``rows . c = rhs`` over ``Z_n`` using unit pivots only.

    Returns ``(pivots, free, expr, const)`` with
    ``c[pivots[i]] = const[i] - sum_j expr[i][j] * c[free[j]]``.
    """
    mat = [[int(x) % n for x in row] + [int(r) % n] for row, r in zip(rows, rhs)]
    pivots: List[int] = []
    r = 0
    for col in range(k):
        pick = None
        for i in range(r, len(mat)):
            if is_unit(mat[i][col], n):
                pick = i
                break
        if pick is None:
            continue
        mat[r], mat[pick] = mat[pick], mat[r]
        iv = inv_mod(mat[r][col], n)
        mat[r] = [x * iv % n for x in mat[r]]
        for i in range(len(mat)):
            if i != r and mat[i][col]:
                f = mat[i][col]
                mat[i] = [(a - f * b) % n for a, b in zip(mat[i], mat[r])]
        pivots.append(col)
        r += 1
        if r == len(mat):
            break
    for i in range(r, len(mat)):
        if all(x == 0 for x in mat[i][:k]) and mat[i][k]:
            return None
        if any(x for x in mat[i][:k]):
            return None
    free = [c for c in range(k) if c not in pivots]
    expr = [[mat[i][c] for c in free] for i in range(len(pivots))]
    const = [mat[i][k] for i in range(len(pivots))]
    return pivots, free, expr, const


# ==========================================================================
# 4.  The realiser
# ==========================================================================

class Realiser:
    def __init__(self, plan: "Plan", catalogue: Dict[str, List[ftl.Family]],
                 rng: random.Random, tries: int = 800,
                 pair_tokens: bool = True, synthesise: bool = True):
        self.plan = plan
        self.n = plan.n
        self.cat = catalogue
        self.rng = rng
        self.tries = tries
        self.pair_tokens = pair_tokens
        self.synthesise = synthesise
        self.labels: Dict[int, int] = {}         # edge (child vertex) -> value
        self.used: Dict[int, str] = {}           # value -> description
        self.notes: List[str] = []
        self.pending: Optional[dict] = None      # pending token
        self.tokens: List[dict] = []
        self.special: List[int] = []
        self.residue2 = 0
        self.retries = 0
        self.budget = 40
        self.subtree_retries = 2
        self.joints = True
        self.joints_used = 0
        self.groups_used = 0

    # -- placement bookkeeping -------------------------------------------
    def place(self, edge: int, value: int, who: str) -> None:
        value %= self.n
        if value == 0:
            raise Failure("placement", f"zero label on edge {edge} ({who})")
        if value in self.used:
            raise Failure("placement",
                          f"label {value} on edge {edge} ({who}) is already used "
                          f"by {self.used[value]}")
        if edge in self.labels:
            raise Failure("placement", f"edge {edge} already labelled")
        self.labels[edge] = value
        self.used[value] = who
        if who != "ordinary block":
            self.special.append(value)

    def fresh(self, value: int) -> bool:
        value %= self.n
        return value != 0 and value not in self.used

    # -- family selection -------------------------------------------------
    @staticmethod
    def forced_ratios(fam: ftl.Family) -> set:
        """Ratios ``q`` such that the family places ``q * x`` for its input."""
        out = set()
        for f in (fam.meta.get("forced_forms") or []):
            if not isinstance(f, dict) or f.get("kind") == "input":
                continue
            try:
                out.add(Q(str(f.get("ratio"))))
            except Exception:
                continue
        return out

    def parent_forced_ratios(self, node: NodePlan) -> List[Q]:
        """One-step lookahead: ratios the parent *must* force from this head.

        Only ratios forced by **every** family the parent could still use are
        reserved (the catalogue menu and, since the constructor may fall back
        to it, the synthesised families of the parent's topology); avoidable
        ones are left to the parent's own menu search.
        """
        v = node.vertex
        if node.is_root:
            return []
        u = self.plan.parent_core(v)
        pnode = self.plan.nodes.get(u) if u is not None else None
        if pnode is None:
            return []
        # a cancelled pair: the sibling's head is the antipode of this one
        for group in pnode.cancelled:
            if v in group and len(group) == 2:
                return [Q(-1)]
        if pnode.retained != v:
            return []
        if not pnode.is_owner:
            info = pnode.absorption or {}
            if info.get("type") == "helper":
                return [Q(-1)]
            return []
        common = None
        pmenu: List[ftl.Family] = []
        for k in self.candidate_keys(pnode.key or "_bot"):
            got = self.cat.get(k)
            if got:
                pmenu.extend(got)
        for fam in pmenu:
            rs = self.forced_ratios(fam)
            common = rs if common is None else (common & rs)
            if not common:
                return []
        if self.synthesise:
            arms = tuple(a.reduced for a in pnode.arms)
            h = 0 if pnode.is_root else cs.reduce_head(pnode.h_raw)
            for _names, _basis in synth_topology(pnode.is_root, h, arms,
                                                 len(pnode.recruited), True):
                rs = basis_forced_ratios(_names, _basis)
                common = rs if common is None else (common & rs)
                if not common:
                    return []
        return sorted(common or set())

    @staticmethod
    def head_only_ratios(fam: ftl.Family) -> List[Q]:
        out = []
        for f in (fam.meta.get("head_only_forms") or []):
            if not isinstance(f, dict):
                continue
            try:
                out.append(Q(str(f.get("ratio"))))
            except Exception:
                continue
        return out

    @staticmethod
    def head_multiplier(fam: ftl.Family) -> Q:
        try:
            return Q(str(fam.meta.get("head_ratio")))
        except Exception:
            return Q(1)

    #: contexts whose child folds in; the catalogue names them L1/L11
    KEY_ALIASES = {"V21": ("L1", "L11", "L12"), "V22": ("L11", "L12", "L1"),
                   "L1": ("L11", "L12"), "L11": ("L1", "L12"),
                   "L12": ("L11", "L1")}

    def candidate_keys(self, key: str) -> List[str]:
        """The context key plus the catalogue aliases for its child type."""
        out = [key]
        head, tag = key.rsplit("_", 1)
        for alt in self.KEY_ALIASES.get(tag, ()):  # V21/V22 are two-row joints
            out.append(f"{head}_{alt}")
        return out

    def order_menu(self, key: str, node: NodePlan) -> List[Tuple[int, ftl.Family]]:
        """Menu in preference order (Lemma F / the one-step lookahead gate).

        ``clean`` families (universally gate compatible) come first, then the
        ones whose head-only labels do not meet a ratio the parent must force.
        """
        menu: List[ftl.Family] = []
        for k in self.candidate_keys(key):
            got = self.cat.get(k)
            if got:
                menu.extend(got)
        if not menu:
            raise Failure("missing_family", f"no family for context {key}",
                          vertex=node.vertex, context=key)
        forced = set(self.parent_forced_ratios(node))
        scored = []
        for i, fam in enumerate(menu):
            if not is_unit(fam.L, self.n):
                continue
            ho = self.head_only_ratios(fam)
            hm = self.head_multiplier(fam)
            blocked = 0
            if hm != 0:
                normalised = {q / hm for q in ho}
                blocked = len(normalised & forced)
            clean = 0 if fam.meta.get("clean") else 1
            # proof draft 8.0: prefer Phi(F) subseteq {-1} and -1 not in H(F)
            phi = self.forced_ratios(fam)
            e6 = 0 if (phi <= {Q(-1)}
                       and (hm == 0 or Q(-1) not in {q / hm for q in ho})) else 1
            scored.append((blocked, e6, clean, len(ho), i, fam))
        scored.sort(key=lambda t: t[:5])
        return [(i, fam) for _b, _e, _c, _h, i, fam in scored[:4]]

    # -- parameter choice -------------------------------------------------
    @staticmethod
    def single_parameter(fam: ftl.Family, name: str) -> Optional[Tuple[int, int]]:
        """``(parameter index, coefficient)`` when the label is ``c * p / L``."""
        lab = fam.by_name.get(name)
        if lab is None:
            return None
        nz = [(i, c) for i, c in enumerate(lab.coeffs) if c]
        if len(nz) != 1:
            return None
        return nz[0]

    def label_values(self, fam: ftl.Family, vals: Sequence[int]) -> Dict[str, int]:
        n = self.n
        Linv = inv_mod(fam.L, n)
        out = {}
        for lab in fam.labels:
            if not lab.physical:
                continue
            tot = 0
            for c, x in zip(lab.coeffs, vals):
                if c:
                    tot += c * x
            out[lab.name] = tot % n * Linv % n
        return out

    def choose_parameters(self, fam: ftl.Family, node: NodePlan,
                          fixed: Dict[int, int],
                          reserve: Sequence[Q],
                          extra_forbidden: Iterable[int] = ()) -> Optional[Tuple[List[int], Dict[str, int]]]:
        """Sequential parameter choice avoiding every collision (Lemma F)."""
        n = self.n
        d = fam.d
        free_idx = [i for i in range(d) if i not in fixed]
        input_name = fam.input_label()
        head_name = fam.head_label()
        forbidden = set(int(x) % n for x in extra_forbidden)
        base = [0] * d
        for i, x in fixed.items():
            base[i] = x % n

        def attempt(vals: List[int]) -> Optional[Dict[str, int]]:
            labs = self.label_values(fam, vals)
            new = [v for name, v in labs.items() if name != input_name]
            if any(v == 0 for v in new):
                return None
            if len(set(new)) != len(new):
                return None
            for v in new:
                if v in self.used or v in forbidden:
                    return None
            if input_name is not None and fixed_input is not None:
                if labs[input_name] != fixed_input:
                    return None
            if head_name is not None and reserve:
                head = labs[head_name]
                blocked = set(new)
                for qratio in reserve:
                    try:
                        rv = (qratio.numerator * head
                              * inv_mod(qratio.denominator, n)) % n
                    except ValueError:
                        continue
                    if rv == 0:
                        return None
                    if rv in self.used or rv in forbidden:
                        return None
                    if rv in blocked and rv != head:
                        return None
            return labs

        # the input label's value is pinned through ``fixed`` already
        fixed_input = None
        if input_name is not None:
            spec = self.single_parameter(fam, input_name)
            if spec is not None and spec[0] in fixed:
                fixed_input = (spec[1] * fixed[spec[0]]) % n * inv_mod(fam.L, n) % n

        if not free_idx:
            labs = attempt(list(base))
            return (list(base), labs) if labs else None

        # deterministic small box first (mirrors the bounded-radius search),
        # then randomised sampling over Z_n
        if len(free_idx) == 1:
            box = list(range(1, n))
            self.rng.shuffle(box)
            for x in box:
                vals = list(base)
                vals[free_idx[0]] = x % n
                labs = attempt(vals)
                if labs:
                    return vals, labs
            return None
        for _ in range(self.tries):
            vals = list(base)
            for i in free_idx:
                vals[i] = self.rng.randrange(1, n)
            labs = attempt(vals)
            if labs:
                return vals, labs
        return None

    # -- cells ------------------------------------------------------------
    def realise_owner(self, node: NodePlan, forced_head: Optional[int] = None) -> None:
        key = node.key
        assert key is not None
        errors = []
        menu: List[Tuple[int, ftl.Family]] = []
        try:
            menu = self.order_menu(key, node)
        except Failure as exc:
            errors.append(exc.report["detail"])
        for idx, fam in menu:
            try:
                self._realise_with(node, fam, idx, forced_head)
                return
            except Failure as exc:
                errors.append(f"menu[{idx}]: {exc.report['detail']}")
                self._rollback(node)
        if self.synthesise:
            try:
                self._realise_synth(node, forced_head)
                return
            except Failure as exc:
                errors.append(f"synth: {exc.report['detail']}")
                self._rollback(node)
        step = "missing_family" if not menu and not self.synthesise else "cell"
        raise Failure(step, "; ".join(errors) or "no usable family",
                      vertex=node.vertex, context=key,
                      labels_used=len(self.used), n=self.n)

    def _realise_synth(self, node: NodePlan, forced_head: Optional[int]) -> None:
        """Re-derive a family for this context directly (no catalogue, no solver)."""
        n = self.n
        v = node.vertex
        key = node.key
        has_input = node.child_type in ("free", "L1") and node.retained is not None
        xval = None
        if has_input:
            xval = self.plan.nodes[node.retained].head_value
            if xval is None:
                raise Failure("cell", f"active child {node.retained} has no head",
                              vertex=v, context=key)
        reserve = self.parent_forced_ratios(node) if not node.is_root else []
        heads = ([0] if node.is_root
                 else sorted({node.h_raw, cs.reduce_head(node.h_raw)}))
        arm_options = []
        for opt in ([a.raw_length for a in node.arms],
                    [a.reduced for a in node.arms]):
            if opt not in arm_options:
                arm_options.append(opt)
        errors = []
        saved_recruited, saved_ordinary = list(node.recruited), list(node.ordinary)
        for p in self.port_options(node):
            node.recruited = node.ports[:p]
            node.ordinary = node.ports[p:]
            if self._synth_try(node, forced_head, has_input, xval, reserve,
                               heads, arm_options, errors):
                return
        node.recruited, node.ordinary = saved_recruited, saved_ordinary
        raise Failure("cell", "; ".join(errors[:6]) or "synthesis failed",
                      vertex=v, context=key)

    def port_options(self, node: NodePlan) -> List[int]:
        """Admissible recruited-port counts, the planned one first."""
        q = len(node.ports)
        cap = 3 if (not node.is_root and node.child_type == "none") else 2
        planned = len(node.recruited)
        out = [planned]
        for p in range(min(q, cap), -1, -1):
            if p != planned and (q - p) != 1:
                out.append(p)
        return out[:3]

    def _synth_try(self, node: NodePlan, forced_head, has_input, xval, reserve,
                   heads, arm_options, errors) -> bool:
        n = self.n
        v = node.vertex
        key = node.key
        for h in heads:
            if not node.is_root:
                extra = node.h_raw - h
                if extra < 0 or extra % 6 or (extra > 0 and h < 1):
                    continue
            for arms in arm_options:
                if any(a.raw_length - ell < 0 or (a.raw_length - ell) % 6
                       for a, ell in zip(node.arms, arms)):
                    continue
                fams = list(synth_topology(node.is_root, h, tuple(arms),
                                           len(node.recruited), has_input))
                if (not node.is_root and h == 0 and tuple(arms) == (2,)
                        and not node.recruited and has_input):
                    fams.append((list(RESIDUE2_RIGID_NAMES),
                                 [list(RESIDUE2_RIGID_BASIS[0])]))
                    self.residue2 += 1
                if not fams:
                    errors.append(f"h={h} arms={arms}: no synthesised family")
                    continue
                for names, basis in fams:
                    got = self._synth_point(node, names, basis, xval,
                                            forced_head, reserve)
                    if got is None:
                        continue
                    labs = got
                    _, rs = cell_label_names(node.is_root, h, arms,
                                             len(node.recruited), has_input)
                    for a, ell in zip(node.arms, arms):
                        a.reduced = ell
                        a.mothers = (a.raw_length - ell) // 6
                    assign = list(range(len(node.arms)))
                    for slot, ai in enumerate(assign):
                        node.arms[ai].slot = slot
                    node.family = None
                    node.family_index = -1
                    node.params = None
                    node.labels = dict(labs)
                    node.synth = {"head": h, "arms": list(arms),
                                  "ports": len(node.recruited),
                                  "input": has_input, "basis": basis}
                    self.place_cell(node, None, [rs], labs, assign)
                    self.notes.append(
                        f"vertex {v}: context {key} synthesised on the fly "
                        f"(h={h}, arms={arms}, ports={len(node.recruited)})")
                    return True
                errors.append(f"h={h} arms={arms} p={len(node.recruited)}: "
                              "no fresh point")
        return False

    def _synth_point(self, node: NodePlan, names: Sequence[str],
                     basis: Sequence[Sequence[int]], xval: Optional[int],
                     forced_head: Optional[int],
                     reserve: Sequence[Q]) -> Optional[Dict[str, int]]:
        n = self.n
        k = len(basis)
        w = len(names)
        idx = {nm: i for i, nm in enumerate(names)}
        rows: List[List[int]] = []
        rhs: List[int] = []
        if xval is not None:
            rows.append([b[idx["x"]] for b in basis])
            rhs.append(xval % n)
        if forced_head is not None:
            if "g0" not in idx:
                return None
            rows.append([b[idx["g0"]] for b in basis])
            rhs.append(forced_head % n)
        if rows:
            red = gauss_mod(rows, rhs, k, n)
            if red is None:
                return None
            pivots, free, expr, const = red
        else:
            pivots, free, expr, const = [], list(range(k)), [], []

        def build(freevals: Sequence[int]) -> Optional[Dict[str, int]]:
            c = [0] * k
            for j, fc in enumerate(free):
                c[fc] = freevals[j] % n
            for i, pc in enumerate(pivots):
                acc = const[i]
                for j, fc in enumerate(free):
                    acc -= expr[i][j] * c[fc]
                c[pc] = acc % n
            vals = [sum(c[j] * basis[j][i] for j in range(k)) % n
                    for i in range(w)]
            new = [vals[i] for i, nm in enumerate(names) if nm != "x"]
            if any(x == 0 for x in new):
                return None
            if len(set(new)) != len(new):
                return None
            if any(x in self.used for x in new):
                return None
            if xval is not None and vals[idx["x"]] != xval % n:
                return None
            if "g0" in idx and reserve:
                head = vals[idx["g0"]]
                for qr in reserve:
                    try:
                        rv = (qr.numerator * head
                              * inv_mod(qr.denominator, n)) % n
                    except ValueError:
                        continue
                    if rv == 0 or rv in self.used:
                        return None
                    if rv in set(new) and rv != head:
                        return None
            return {nm: vals[i] for i, nm in enumerate(names)}

        nf = len(free)
        if nf == 0:
            return build([])
        if nf == 1:
            order = list(range(1, n))
            self.rng.shuffle(order)
            for c in order:
                got = build([c])
                if got:
                    return got
            return None
        for _ in range(self.tries):
            got = build([self.rng.randrange(1, n) for _ in range(nf)])
            if got:
                return got
        return None

    def _rollback(self, node: NodePlan) -> None:
        for edge in list(node_edges(node)):
            if edge in self.labels:
                value = self.labels.pop(edge)
                self.used.pop(value, None)
                try:
                    self.special.remove(value)
                except ValueError:
                    pass
        node.family = None
        node.params = None
        node.labels = None
        node.head_value = None
        node.token = None
        node.synth = None

    def _realise_with(self, node: NodePlan, fam: ftl.Family, idx: int,
                      forced_head: Optional[int]) -> None:
        n = self.n
        struct = fam.structure()
        v = node.vertex
        key = node.key

        # ---- topology compatibility: rows 1.. are folded descendants
        chain_nodes = self.fold_chain(node, len(struct))
        if len(chain_nodes) != len(struct):
            raise Failure("cell",
                          f"family has {len(struct)} rows but only "
                          f"{len(chain_nodes)} vertices fold into this cell",
                          vertex=v, context=key)
        row0 = struct[0]
        if len(row0.arms) != len(node.arms):
            raise Failure("cell",
                          f"family expects {len(row0.arms)} arms, plan has "
                          f"{len(node.arms)}", vertex=v, context=key)
        if len(row0.ports) != len(node.recruited):
            raise Failure("cell",
                          f"family expects {len(row0.ports)} ports, plan has "
                          f"{len(node.recruited)}", vertex=v, context=key)
        want_head = int(row0.spec.get("head") or 0)
        if not node.is_root:
            if want_head != cs.reduce_head(node.h_raw) % 6 and want_head != node.h_raw:
                raise Failure("cell",
                              f"family head chain {want_head} does not match "
                              f"the plan ({node.h_raw})", vertex=v, context=key)
            extra = node.h_raw - want_head
            if extra < 0 or extra % 6:
                raise Failure("head_chain",
                              f"head chain of length {node.h_raw} cannot be "
                              f"reduced to the family length {want_head}",
                              vertex=v, context=key)
            if extra > 0 and want_head < 1:
                raise Failure("head_chain",
                              f"head chain of raw length {node.h_raw} needs an "
                              "endpoint-preserving insertion but the family has "
                              "no chain gap (h = 0)", vertex=v, context=key)

        # ---- arm slot assignment
        slots = [len(a) - 1 for a in row0.arms]
        assign = match_slots(slots, [a.reduced for a in node.arms])
        if assign is None:
            raise Failure("cell",
                          f"arm lengths {[a.reduced for a in node.arms]} do not "
                          f"match the family slots {slots}", vertex=v, context=key)
        for slot, ai in enumerate(assign):
            node.arms[ai].slot = slot
        for a in node.arms:
            extra = a.raw_length - a.reduced
            if extra < 0 or extra % 6:
                raise Failure("arm",
                              f"arm of raw length {a.raw_length} cannot be "
                              f"reduced to {a.reduced}", vertex=v, context=key)
            a.mothers = extra // 6

        # ---- fixed parameters: the pinned input heads and a forced head
        fixed: Dict[int, int] = {}
        try:
            input_names = list(fam.input_labels())
        except AttributeError:
            one = fam.input_label()
            input_names = [one] if one else []
        if input_names:
            bottom = chain_nodes[-1]
            sources = list(bottom.kept)
            if len(sources) < len(input_names):
                raise Failure("cell",
                              f"family has {len(input_names)} input heads but "
                              f"vertex {bottom.vertex} keeps {len(sources)}",
                              vertex=v, context=key)
            for input_name, src in zip(input_names, sources):
                xval = self.plan.nodes[src].head_value
                if xval is None:
                    raise Failure("cell", f"active child {src} has no head value",
                                  vertex=v, context=key)
                spec = self.single_parameter(fam, input_name)
                if spec is None:
                    raise Failure("cell",
                                  f"input label {input_name} is not a single "
                                  "parameter", vertex=v, context=key)
                i, c = spec
                if not is_unit(c, n):
                    raise Failure("cell", f"input coefficient {c} is not "
                                  f"invertible mod {n}", vertex=v, context=key)
                want = xval * fam.L % n * inv_mod(c, n) % n
                if i in fixed and fixed[i] != want:
                    raise Failure("cell", "two input heads share a parameter",
                                  vertex=v, context=key)
                fixed[i] = want

        head_name = fam.head_label()
        if forced_head is not None:
            if head_name is None:
                raise Failure("cell", "a forced head was requested for a root "
                              "family", vertex=v, context=key)
            spec = self.single_parameter(fam, head_name)
            if spec is None or not is_unit(spec[1], n):
                raise Failure("cell", "the head label is not an invertible "
                              "single parameter", vertex=v, context=key)
            i, c = spec
            if i in fixed:
                raise Failure("cell", "head and input share a parameter",
                              vertex=v, context=key)
            fixed[i] = forced_head * fam.L % n * inv_mod(c, n) % n

        # ---- token absorption
        token_names = fam.token_labels()
        extra_fixed_from_token: Dict[int, int] = {}
        absorbed = None
        if (self.pair_tokens and self.pending is not None and token_names):
            solved = self.absorb_token(fam, fixed, token_names)
            if solved is not None:
                extra_fixed_from_token = solved
                absorbed = self.pending["vertex"]
        fixed.update(extra_fixed_from_token)

        reserve = self.parent_forced_ratios(node) if not node.is_root else []
        chosen = self.choose_parameters(fam, node, fixed, reserve)
        if chosen is None:
            if absorbed is not None:
                # retry without token pairing
                fixed = {k: val for k, val in fixed.items()
                         if k not in extra_fixed_from_token}
                chosen = self.choose_parameters(fam, node, fixed, reserve)
                absorbed = None
                if chosen is not None:
                    self.notes.append(f"vertex {v}: token pairing abandoned "
                                      f"(context {key})")
            if chosen is None:
                raise Failure("parameters",
                              f"no fresh parameter point for {key} after "
                              f"{self.tries} tries", vertex=v, context=key)
        vals, labs = chosen
        node.family = fam
        node.family_index = idx
        node.params = {p: vals[i] for i, p in enumerate(fam.parameters)}
        node.labels = dict(labs)

        # ---- place the labels on the concrete edges
        self.place_cell(node, fam, struct, labs, assign, chain_nodes)

        # ---- token bookkeeping
        if token_names:
            tvals = [labs[token_names[r]] for r in "abc"]
            node.token = {"labels": [token_names[r] for r in "abc"],
                          "values": tvals, "absorbed": absorbed}
            self.tokens.append({"vertex": v, "values": tvals,
                                "paired_with": absorbed})
            if absorbed is not None:
                self.pending = None
            else:
                if self.pending is not None:
                    self.notes.append(
                        f"vertex {v}: a second token became pending while "
                        f"{self.pending['vertex']} was still open")
                self.pending = {"vertex": v, "values": tvals}

    def absorb_token(self, fam: ftl.Family, fixed: Dict[int, int],
                     token_names: Dict[str, str]) -> Optional[Dict[int, int]]:
        """Try to pin the family's token to minus the pending triple.

        Solves ``T_cell = -T_pending`` as sets (all six matchings) over
        ``Z_n``.  Only unit pivots are used, so a system that needs a
        non-invertible pivot is reported as unsolvable and the caller falls
        back to an unpaired token.
        """
        assert self.pending is not None
        n = self.n
        target = [(-x) % n for x in self.pending["values"]]
        names = [token_names[r] for r in "abc"]
        rows = [fam.by_name[nm].coeffs for nm in names]
        for perm in itertools.permutations(range(3)):
            # two independent equations suffice (the third is their sum)
            eqs = []
            for j in range(2):
                coeffs = list(rows[j])
                rhs = target[perm[j]] * fam.L % n
                eqs.append((coeffs, rhs))
            sol = solve_mod(eqs, fam.d, fixed, n)
            if sol is not None:
                return sol
        return None

    # -- edge placement ---------------------------------------------------
    def fold_chain(self, node: NodePlan, rows: int) -> List[NodePlan]:
        """``[node, folded child, folded grandchild, ...]`` for a joint macro."""
        out = [node]
        cur = node
        while len(out) < rows:
            if cur.retained is None:
                break
            cur = self.plan.nodes[cur.retained]
            out.append(cur)
        return out

    def place_cell(self, node: NodePlan, fam: Optional[ftl.Family],
                   struct: Sequence, labs: Dict[str, int],
                   assign: Sequence[int],
                   chain_nodes: Optional[Sequence[NodePlan]] = None) -> None:
        """Write a macro's labels onto the concrete tree edges."""
        v = node.vertex
        key = node.key
        if chain_nodes is None:
            chain_nodes = self.fold_chain(node, len(struct))
        if len(chain_nodes) != len(struct):
            raise Failure("cell", "fold chain does not match the family rows",
                          vertex=v, context=key)
        for k, (rs, target) in enumerate(zip(struct, chain_nodes)):
            if k == 0 and node.is_root:
                node.head_value = None
            else:
                chain_vals = [labs[nm] for nm in rs.chain]
                if k == 0:
                    chain_vals = self.extend_chain(chain_vals, node.h_raw,
                                                   node, key)
                elif len(chain_vals) - 1 != target.h_raw:
                    chain_vals = self.extend_chain(chain_vals, target.h_raw,
                                                   target, key)
                if len(chain_vals) != len(target.head_edges):
                    raise Failure("head_chain",
                                  f"row {k} chain has {len(chain_vals)} labels "
                                  f"for {len(target.head_edges)} edges",
                                  vertex=target.vertex, context=key)
                for edge, value in zip(target.head_edges, chain_vals):
                    self.place(edge, value, f"cell {v} row {k} head chain")
                target.head_value = chain_vals[0]
            if k == 0:
                slots = list(assign)
            else:
                slots = match_slots([len(a) - 1 for a in rs.arms],
                                    [a.reduced for a in target.arms])
                if slots is None:
                    raise Failure("cell",
                                  f"row {k} arms do not match vertex "
                                  f"{target.vertex}", vertex=target.vertex,
                                  context=key)
            for slot, ai in enumerate(slots):
                arm = target.arms[ai]
                arm.slot = slot
                arm.mothers = (arm.raw_length - arm.reduced) // 6
                vals = [labs[nm] for nm in rs.arms[slot]]
                vals = self.extend_arm(vals, arm.mothers,
                                       f"cell {v} row {k} arm {slot}")
                if len(vals) != len(arm.edges):
                    raise Failure("arm",
                                  f"row {k} arm {slot} has {len(vals)} labels "
                                  f"for {len(arm.edges)} edges",
                                  vertex=target.vertex, context=key)
                arm.values = vals
                for edge, value in zip(arm.edges, vals):
                    self.place(edge, value, f"cell {v} row {k} arm {slot}")
            if k > 0:
                # a folded row recruits exactly the ports its family row wants
                want = len(rs.ports)
                if want > len(target.ports) or (len(target.ports) - want) == 1:
                    raise Failure("cell",
                                  f"row {k} wants {want} ports but vertex "
                                  f"{target.vertex} has {len(target.ports)}",
                                  vertex=target.vertex, context=key)
                target.recruited = target.ports[:want]
                target.ordinary = target.ports[want:]
            elif len(rs.ports) != len(target.recruited):
                raise Failure("cell",
                              f"row {k} has {len(rs.ports)} ports but vertex "
                              f"{target.vertex} recruits {len(target.recruited)}",
                              vertex=target.vertex, context=key)
            for edge, nm in zip(target.recruited, rs.ports):
                self.place(edge, labs[nm], f"cell {v} row {k} port")

    def extend_arm(self, values: List[int], mothers: int, who: str) -> List[int]:
        out = list(values)
        for _ in range(mothers):
            block = self.fresh_mother(out[-1], who)
            out.extend(block)
        return out

    def fresh_mother(self, terminal: int, who: str) -> List[int]:
        n = self.n
        order = list(range(1, n))
        self.rng.shuffle(order)
        for t in order:
            block = mother_extension_mod(terminal, t, n)
            if any(x == 0 for x in block):
                continue
            if len(set(block)) != 6:
                continue
            if any(x in self.used for x in block):
                continue
            return block
        raise Failure("mother", f"no fresh six-edge mother terminal ({who})")

    def extend_chain(self, values: List[int], raw: int, node: NodePlan,
                     key: Optional[str]) -> List[int]:
        """Lengthen a head chain to ``raw`` degree-two vertices."""
        n = self.n
        out = list(values)
        need = raw - (len(values) - 1)
        if need == 0:
            return out
        if need < 0 or need % 6:
            raise Failure("head_chain", f"cannot extend a chain by {need}",
                          vertex=node.vertex, context=key)
        while need > 0:
            if len(out) < 2:
                raise Failure("head_chain", "no chain gap for an insertion",
                              vertex=node.vertex, context=key)
            done = False
            if need >= 12:
                block = self.fresh_twelve(out)
                if block is not None:
                    gap, values12 = block
                    out[gap + 1:gap + 1] = values12
                    need -= 12
                    done = True
            if not done:
                block = self.fresh_six(out)
                if block is None:
                    raise Failure("head_chain",
                                  "no fresh endpoint-preserving insertion",
                                  vertex=node.vertex, context=key)
                gap, values6 = block
                out[gap + 1:gap + 1] = values6
                need -= 6
        return out

    def fresh_six(self, chain: List[int]) -> Optional[Tuple[int, List[int]]]:
        n = self.n
        current = set(chain)
        for gap in range(len(chain) - 1):
            for block in six_insertions_mod(chain[gap], chain[gap + 1], n):
                if any(x == 0 for x in block):
                    continue
                if len(set(block)) != 6:
                    continue
                if any(x in self.used or x in current for x in block):
                    continue
                return gap, block
        return None

    def fresh_twelve(self, chain: List[int]) -> Optional[Tuple[int, List[int]]]:
        n = self.n
        current = set(chain)
        for gap in range(len(chain) - 1):
            left, right = chain[gap], chain[gap + 1]
            if left == 0 or right == 0 or (left + right) % n == 0:
                continue
            order = list(range(1, n))
            self.rng.shuffle(order)
            for t in order:
                block = twelve_insertion_mod(left, right, t, n)
                if any(x == 0 for x in block):
                    continue
                if len(set(block)) != 12:
                    continue
                if any(x in self.used or x in current for x in block):
                    continue
                if not check_insertion(left, right, block, n):
                    continue
                return gap, block
        return None

    # -- neutral units ----------------------------------------------------
    def realise_units(self, node: NodePlan) -> None:
        for unit in node.units:
            self.realise_unit(node, unit)

    def realise_unit(self, node: NodePlan, unit: UnitPlan) -> None:
        v = node.vertex
        if self._catalogue_unit(node, unit):
            return
        if self.synthesise and self._synth_unit(node, unit):
            return
        if not HAVE_UNIT_BASES:
            raise Failure("neutral_unit",
                          "mixed_chain_pairs is unavailable", vertex=v)
        lengths = [a.raw_length for a in unit.arms]
        if unit.kind == "pair":
            try:
                rows = pair_bases.catalog_pair_rows(lengths[0], lengths[1])
            except Exception as exc:
                raise Failure("neutral_unit",
                              f"no base for the same-parity pair {lengths}: {exc}",
                              vertex=v)
            base_lengths = [len(r) - 1 for r in rows]
        else:
            residues = tuple(sorted(1 if a.raw_length % 6 == 1 else 3
                                    for a in unit.arms))
            key = (1, 1, 1, 3) if residues.count(1) == 3 else (1, 3, 3, 3)
            table = short_bases.FOUR_SHORT_ROWS.get(key)
            if table is None:
                raise Failure("neutral_unit",
                              f"no four-short base for residues {residues}",
                              vertex=v)
            rows = list(table)
            # order the concrete arms so that the residues line up
            ones = [a for a in unit.arms if a.raw_length % 6 == 1]
            threes = [a for a in unit.arms if a.raw_length % 6 == 3]
            unit.arms = ones + threes if key == (1, 1, 1, 3) else ones + threes
            base_lengths = [len(r) - 1 for r in rows]
        unit.base = [list(r) for r in rows]

        for a, bl in zip(unit.arms, base_lengths):
            extra = a.raw_length - bl
            if extra < 0 or extra % 6:
                raise Failure("neutral_unit",
                              f"arm of length {a.raw_length} does not reduce to "
                              f"the base length {bl}", vertex=v)
            a.mothers = extra // 6
            a.reduced = bl

        scale = self.fresh_scale(rows)
        unit.scale = scale
        n = self.n
        for a, row in zip(unit.arms, rows):
            vals = [x * scale % n for x in row]
            vals = self.extend_arm(vals, a.mothers, f"unit at {v}")
            if len(vals) != len(a.edges):
                raise Failure("neutral_unit",
                              f"unit arm has {len(vals)} labels for "
                              f"{len(a.edges)} edges", vertex=v)
            a.values = vals
            for edge, value in zip(a.edges, vals):
                self.place(edge, value, f"neutral unit at {v}")

    def _catalogue_unit(self, node: NodePlan, unit: UnitPlan) -> bool:
        """Instantiate the neutral unit from ``data/batches/alphabet_units.jsonl``."""
        n = self.n
        fams = unit_families()
        if not fams:
            return False
        reduced = sorted(cs.reduce6(a.raw_length) for a in unit.arms)
        fam = fams.get("unit_" + "-".join(str(x) for x in reduced))
        if fam is None or not is_unit(fam.L, n):
            return False
        rs = fam.structure()[0]
        slots = [len(a) - 1 for a in rs.arms]
        order = match_slots(slots, [cs.reduce6(a.raw_length) for a in unit.arms])
        if order is None:
            return False
        Linv = inv_mod(fam.L, n)
        names = [lb.name for lb in fam.labels if lb.physical]
        for _ in range(max(400, self.tries)):
            vals = [self.rng.randrange(1, n) for _ in fam.parameters]
            labs = {}
            for lb in fam.labels:
                if not lb.physical:
                    continue
                tot = 0
                for c, x in zip(lb.coeffs, vals):
                    if c:
                        tot += c * x
                labs[lb.name] = tot % n * Linv % n
            got = list(labs.values())
            if any(x == 0 for x in got) or len(set(got)) != len(got):
                continue
            if any(x in self.used for x in got):
                continue
            ok = True
            rows = []
            for slot, ai in enumerate(order):
                arm = unit.arms[ai]
                base = [labs[nm] for nm in rs.arms[slot]]
                arm.reduced = len(base) - 1
                extra = arm.raw_length - arm.reduced
                if extra < 0 or extra % 6:
                    ok = False
                    break
                arm.mothers = extra // 6
                rows.append((arm, base))
            if not ok:
                continue
            try:
                placed = []
                for arm, base in rows:
                    full = self.extend_arm(base, arm.mothers,
                                           f"unit at {node.vertex}")
                    if len(full) != len(arm.edges):
                        raise Failure("neutral_unit", "unit arm length mismatch",
                                      vertex=node.vertex)
                    placed.append((arm, full))
            except Failure:
                continue
            for arm, full in placed:
                arm.values = full
                for edge, value in zip(arm.edges, full):
                    self.place(edge, value, f"neutral unit at {node.vertex}")
            unit.base = [list(b) for _a, b in rows]
            unit.scale = 1
            unit.source = fam.key
            return True
        return False

    def _synth_unit(self, node: NodePlan, unit: UnitPlan) -> bool:
        """Try a directly derived neutral unit (raw lengths, no mother needed)."""
        n = self.n
        lengths = tuple(a.raw_length for a in unit.arms)
        fams = synth_unit(lengths)
        if not fams:
            return False
        for names, basis in fams:
            k = len(basis)
            w = len(names)
            for _ in range(max(200, self.tries // 4)):
                c = [self.rng.randrange(1, n) for _ in range(k)]
                vals = [sum(c[j] * basis[j][i] for j in range(k)) % n
                        for i in range(w)]
                if any(x == 0 for x in vals) or len(set(vals)) != w:
                    continue
                if any(x in self.used for x in vals):
                    continue
                pos = 0
                rows = []
                for a in unit.arms:
                    rows.append(vals[pos:pos + a.raw_length + 1])
                    pos += a.raw_length + 1
                unit.base = [list(r) for r in rows]
                unit.scale = 1
                for a, row in zip(unit.arms, rows):
                    a.reduced = a.raw_length
                    a.mothers = 0
                    a.values = list(row)
                    for edge, value in zip(a.edges, row):
                        self.place(edge, value, f"neutral unit at {node.vertex}")
                self.notes.append(
                    f"vertex {node.vertex}: neutral unit {list(lengths)} "
                    "synthesised on the fly")
                return True
        return False

    def fresh_scale(self, rows: Sequence[Sequence[int]]) -> int:
        n = self.n
        support = sorted({abs(x) for row in rows for x in row})
        order = list(range(1, n))
        self.rng.shuffle(order)
        for scale in order:
            if not is_unit(scale, n):
                continue
            vals = [x * scale % n for row in rows for x in row]
            if any(x == 0 for x in vals):
                continue
            if len(set(vals)) != len(vals):
                continue
            if any(x in self.used for x in vals):
                continue
            return scale
        raise Failure("neutral_unit", f"no fresh scale for support {support}")

    # -- absorptions ------------------------------------------------------
    def realise_absorption(self, node: NodePlan) -> None:
        """Place the one label a stationary vertex still owns (if any).

        With target-sum ordinary blocks the helper `-x` and the two-port pair
        `a, -x-a` are no longer special labels: the port block simply carries
        target `-x` (see ``block_target``).  The single remaining case is the
        lone port of a vertex whose only absorbable structure is a cancelled
        active-child group (Lemma C step 3): that port is a free special label
        and the group's last head compensates for it.
        """
        info = node.absorption
        if not info or info["type"] != "port_into_group":
            return
        v = node.vertex
        n = self.n
        order = list(range(1, n))
        self.rng.shuffle(order)
        for value in order:
            if value in self.used:
                continue
            self.place(info["port"], value, f"lone port at {v}")
            info["value"] = value
            return
        raise Failure("absorption", "no fresh label for the lone port", vertex=v)

    def block_target(self, node: NodePlan) -> int:
        """Required sum of the vertex's ordinary block."""
        n = self.n
        if node.is_owner or node.folded:
            return 0
        total = 0
        if node.retained is not None:
            hv = self.plan.nodes[node.retained].head_value
            if hv is None:
                raise Failure("blocks", f"active child {node.retained} of the "
                              f"stationary vertex {node.vertex} has no head",
                              vertex=node.vertex)
            total += hv
        return (-total) % n

    # -- the bottom-up sweep ----------------------------------------------
    # -- checkpoints (subtree backtracking) --------------------------------
    def subtree(self, v: int) -> List[int]:
        out = [v]
        for u in self.plan.children_of(v):
            out.extend(self.subtree(u))
        return out

    def checkpoint(self, vs: Sequence[int]) -> dict:
        snap_nodes = {}
        for v in vs:
            node = self.plan.nodes[v]
            arms = [(a, a.slot, a.mothers, list(a.values), a.reduced)
                    for a in node.arms]
            units = [(u, u.kind, list(u.arms), [list(b) for b in u.base],
                      u.scale,
                      [(a, a.slot, a.mothers, list(a.values), a.reduced)
                       for a in u.arms])
                     for u in node.units]
            snap_nodes[v] = (node.is_owner, node.folded, node.key,
                             dict(node.ctx) if node.ctx else None,
                             node.child_type, list(node.recruited),
                             list(node.ordinary), node.family,
                             node.family_index,
                             dict(node.params) if node.params else None,
                             dict(node.labels) if node.labels else None,
                             node.head_value,
                             dict(node.token) if node.token else None,
                             node.synth,
                             dict(node.absorption) if node.absorption else None,
                             arms, units)
        return {"labels": dict(self.labels), "used": dict(self.used),
                "special": list(self.special),
                "pending": dict(self.pending) if self.pending else None,
                "tokens": [dict(t) for t in self.tokens],
                "nodes": snap_nodes}

    def restore(self, cp: dict) -> None:
        self.labels = dict(cp["labels"])
        self.used = dict(cp["used"])
        self.special = list(cp["special"])
        self.pending = dict(cp["pending"]) if cp["pending"] else None
        self.tokens = [dict(t) for t in cp["tokens"]]
        for v, snap in cp["nodes"].items():
            node = self.plan.nodes[v]
            (node.is_owner, node.folded, node.key, node.ctx, node.child_type, rec, ordn,
             node.family, node.family_index, node.params, node.labels,
             node.head_value, node.token, node.synth, node.absorption,
             arms, units) = snap
            node.recruited = list(rec)
            node.ordinary = list(ordn)
            for a, slot, mothers, values, reduced in arms:
                a.slot, a.mothers, a.values, a.reduced = slot, mothers, list(values), reduced
            node.units = []
            for u, kind, uarms, base, scale, arminfo in units:
                u.kind, u.arms, u.base, u.scale = kind, list(uarms), [list(b) for b in base], scale
                for a, slot, mothers, values, reduced in arminfo:
                    a.slot, a.mothers, a.values, a.reduced = slot, mothers, list(values), reduced
                node.units.append(u)

    def run(self) -> None:
        self._visit_retry(self.plan.root, None, False)

    def _visit_retry(self, v: int, forced_head: Optional[int],
                     skip_cell: bool) -> None:
        """Realise the subtree at ``v``; retry it wholesale on failure."""
        if self.budget <= 0:
            self._visit(v, forced_head, skip_cell)
            return
        vs = self.subtree(v)
        cp = self.checkpoint(vs)
        last: Optional[Failure] = None
        for attempt in range(self.subtree_retries + 1):
            try:
                self._visit(v, forced_head, skip_cell)
                return
            except Failure as exc:
                last = exc
                if attempt == self.subtree_retries or self.budget <= 0:
                    break
                self.budget -= 1
                self.retries += 1
                self.restore(cp)
        assert last is not None
        raise last

    def _visit(self, v: int, forced_head: Optional[int] = None,
               skip_cell: bool = False) -> None:
        node = self.plan.nodes[v]
        core_children = self.plan.children_of(v)
        # process non-active children first, then the active ones in the order
        # dictated by the cancellation groups (the last of each group has its
        # head forced)
        active = set(node.active)
        for u in core_children:
            if u not in active:
                self._visit_retry(u, None, False)
        if (node.absorption or {}).get("type") == "port_into_group":
            self.realise_absorption(node)
        for gi, group in enumerate(node.cancelled):
            offset = 0
            if gi == 0 and (node.absorption or {}).get("type") == "port_into_group":
                offset = node.absorption.get("value", 0)

            def sequential() -> None:
                for u in group[:-1]:
                    self._visit_retry(u, None, False)
                total = offset
                for u in group[:-1]:
                    hv = self.plan.nodes[u].head_value
                    if hv is None:
                        raise Failure("cancellation",
                                      f"active child {u} has no head value",
                                      vertex=v)
                    total += hv
                self._visit_retry(group[-1], (-total) % self.n, False)

            forced_macro = any(self.plan.nodes[u].passthrough is not None
                               for u in group)
            if not self.joints or offset:
                sequential()
                continue
            if forced_macro:
                for u in group:
                    self._visit_retry(u, None, True)
                self._realise_group(node, group)
                continue
            gcp = self.checkpoint([x for u in group for x in self.subtree(u)])
            try:
                sequential()
                continue
            except Failure as exc:
                first = exc
            self.restore(gcp)
            try:
                for u in group:
                    self._visit_retry(u, None, True)
                self._realise_group(node, group)
            except Failure:
                self.restore(gcp)
                raise first
        def tail(joint: bool) -> None:
            depth = 1 if skip_cell else self.fold_depth(node)
            if joint:
                depth = 2
            for i, c in enumerate(node.kept):
                cnode = self.plan.nodes[c]
                fold_it = (joint and i == 0) or (i == 0 and depth > 1) \
                    or cnode.passthrough is not None
                if fold_it:
                    cnode.folded = True
                    self._visit_retry(c, None, True)
                else:
                    self._visit_retry(c, None, False)

            # the vertex itself: forced absorptions first, then the neutral
            # units (least freedom), then the cell (most freedom)
            if not node.is_owner and not joint:
                if forced_head is not None:
                    raise Failure("cancellation",
                                  "a cancelled active child is not an owner",
                                  vertex=v)
                self.realise_absorption(node)
            self.realise_units(node)
            if joint:
                self._realise_joint(node, node.retained, forced_head)
            elif node.is_owner and not skip_cell:
                self.realise_owner(node, forced_head=forced_head)

        if not self.joints or skip_cell or not self._joinable(node):
            tail(False)
            return
        cp = self.checkpoint(self.subtree(v))
        try:
            tail(False)
            return
        except Failure as exc:
            first = exc
        self.restore(cp)
        try:
            tail(True)
        except Failure:
            raise first

    def _realise_group(self, node: NodePlan, group: Sequence[int]) -> None:
        """Realise a whole cancelled active group as one macro (see synth_group)."""
        n = self.n
        v = node.vertex
        children = [self.plan.nodes[c] for c in group]
        heads = []
        for c in children:
            h = cs.reduce_head(c.h_raw)
            if (c.h_raw - h) % 6 or (c.h_raw > h and h < 1):
                raise Failure("group", f"child {c.vertex} head chain "
                              f"{c.h_raw} does not reduce", vertex=v)
            heads.append(h)
        port_choices = []
        for c in children:
            opts = [len(c.recruited)]
            for p in (len(c.ports), 0):
                if p not in opts and (len(c.ports) - p) != 1:
                    opts.append(p)
            port_choices.append(opts[:2])
        errors = []
        for combo in itertools.product(*port_choices):
            specs = [{"head": h, "arms": [a.reduced for a in c.arms],
                      "ports": p, "inputs": len(c.kept)}
                     for c, h, p in zip(children, heads, combo)]
            fams = synth_group(specs)
            if not fams:
                errors.append(f"ports={list(combo)}: no group family")
                continue
            for names, basis in fams:
                got = self._group_point(children, names, basis, specs)
                if got is None:
                    continue
                self._place_group(node, children, specs, names, got, combo)
                self.groups_used += 1
                self.notes.append(
                    f"vertex {v}: cancelled group {list(group)} realised as one "
                    f"macro (contexts {[c.key for c in children]})")
                return
            errors.append(f"ports={list(combo)}: no fresh point")
        raise Failure("group", "; ".join(errors[:4]) or "no group family",
                      vertex=v)

    def _group_point(self, children, names, basis, specs):
        n = self.n
        k = len(basis)
        w = len(names)
        idx = {nm: i for i, nm in enumerate(names)}
        rows, rhs = [], []
        for ci, c in enumerate(children):
            for j, src in enumerate(c.kept):
                nm = f"x{ci}_{j}"
                if nm not in idx:
                    return None
                hv = self.plan.nodes[src].head_value
                if hv is None:
                    return None
                rows.append([b[idx[nm]] for b in basis])
                rhs.append(hv % n)
        if rows:
            red = gauss_mod(rows, rhs, k, n)
            if red is None:
                return None
            pivots, free, expr, const = red
        else:
            pivots, free, expr, const = [], list(range(k)), [], []
        inputs = {f"x{ci}_{j}" for ci, c in enumerate(children)
                  for j in range(len(c.kept))}

        def build(freevals):
            cvec = [0] * k
            for j, fc in enumerate(free):
                cvec[fc] = freevals[j] % n
            for i, pc in enumerate(pivots):
                acc = const[i]
                for j, fc in enumerate(free):
                    acc -= expr[i][j] * cvec[fc]
                cvec[pc] = acc % n
            vals = [sum(cvec[j] * basis[j][i] for j in range(k)) % n
                    for i in range(w)]
            new = [vals[i] for i, nm in enumerate(names) if nm not in inputs]
            if any(x == 0 for x in new) or len(set(new)) != len(new):
                return None
            if any(x in self.used for x in new):
                return None
            return {nm: vals[i] for i, nm in enumerate(names)}

        nf = len(free)
        if nf == 0:
            return build([])
        if nf == 1:
            order = list(range(1, n))
            self.rng.shuffle(order)
            for c in order:
                got = build([c])
                if got:
                    return got
            return None
        for _ in range(self.tries):
            got = build([self.rng.randrange(1, n) for _ in range(nf)])
            if got:
                return got
        return None

    def _place_group(self, node, children, specs, names, labs, combo):
        for ci, (c, sp, p) in enumerate(zip(children, specs, combo)):
            chain = [labs[f"g{ci}"]] + [labs[f"r{ci}h{i}"]
                                        for i in range(1, sp["head"] + 1)]
            chain = self.extend_chain(chain, c.h_raw, c, c.key)
            if len(chain) != len(c.head_edges):
                raise Failure("group", f"child {c.vertex} chain mismatch",
                              vertex=c.vertex)
            for edge, value in zip(c.head_edges, chain):
                self.place(edge, value, f"group macro at {node.vertex}")
            c.head_value = chain[0]
            for a_i, arm in enumerate(c.arms):
                arm.slot = a_i
                arm.mothers = (arm.raw_length - arm.reduced) // 6
                vals = [labs[f"r{ci}a{a_i}x{i}"] for i in range(arm.reduced + 1)]
                vals = self.extend_arm(vals, arm.mothers,
                                       f"group macro at {node.vertex}")
                if len(vals) != len(arm.edges):
                    raise Failure("group", f"child {c.vertex} arm mismatch",
                                  vertex=c.vertex)
                arm.values = vals
                for edge, value in zip(arm.edges, vals):
                    self.place(edge, value, f"group macro at {node.vertex}")
            c.recruited = c.ports[:p]
            c.ordinary = c.ports[p:]
            for j, edge in enumerate(c.recruited):
                self.place(edge, labs[f"r{ci}p{j}"],
                           f"group macro at {node.vertex}")
            c.labels = {nm: val for nm, val in labs.items()
                        if nm.startswith(f"r{ci}") or nm == f"g{ci}"}
            c.synth = {"group_of": node.vertex, "spec": sp}
            c.folded = True

    def _joinable(self, node: NodePlan) -> bool:
        """Whether the retained active child may be joined into this vertex.

        This is the *whole-parent reopen* of the proof draft (sections 0 and
        8b): a child whose every family forces the antipode of its own head
        (the residue-one letter and the ``(1; 1 port)`` bottom) cannot be
        composed as a black box under a mirror parent, so the two vertices are
        realised as a single multi-row macro.
        """
        if node.retained is None or node.folded:
            return False
        child = self.plan.nodes[node.retained]
        if not child.is_owner or child.folded:
            return False
        if child.child_type == "L1":
            return False
        return True

    def _realise_joint(self, node: NodePlan, child_v: int,
                       forced_head: Optional[int]) -> None:
        """Realise ``node`` and its active child as one joint macro."""
        n = self.n
        child = self.plan.nodes[child_v]
        v = node.vertex
        key = f"joint({node.key or 'stationary'}|{child.key})"
        has_input = child.retained is not None
        xval = None
        if has_input:
            xval = self.plan.nodes[child.retained].head_value
            if xval is None:
                raise Failure("joint", f"active child {child.retained} of the "
                              f"letter {child_v} has no head", vertex=v,
                              context=key)
        reserve = self.parent_forced_ratios(node) if not node.is_root else []
        h0 = 0 if node.is_root else cs.reduce_head(node.h_raw)
        h1 = cs.reduce_head(child.h_raw)
        if (node.h_raw - h0) % 6 or (child.h_raw - h1) % 6:
            raise Failure("joint", "head chains do not reduce", vertex=v,
                          context=key)
        if (node.h_raw > h0 and h0 < 1) or (child.h_raw > h1 and h1 < 1):
            raise Failure("joint", "a head chain needs an insertion but the "
                          "macro has no chain gap", vertex=v, context=key)
        arms0 = [a.reduced for a in node.arms]
        arms1 = [a.reduced for a in child.arms]
        errors = []
        saved = (list(node.recruited), list(node.ordinary))
        for p0 in self.port_options(node):
            node.recruited = node.ports[:p0]
            node.ordinary = node.ports[p0:]
            rows = [{"root": node.is_root, "head": h0, "arms": arms0,
                     "ports": p0, "input": False},
                    {"root": False, "head": h1, "arms": arms1,
                     "ports": len(child.ports) if len(child.ports) != 1 else 1,
                     "input": has_input}]
            fams = synth_joint(rows)
            if not fams:
                errors.append(f"p0={p0}: no joint family")
                continue
            for names, basis in fams:
                labs = self._synth_point(node, names, basis, xval,
                                         forced_head, reserve)
                if labs is None:
                    continue
                _nm, structs = multi_label_names(rows)
                for a, ell in zip(node.arms, arms0):
                    a.reduced = ell
                    a.mothers = (a.raw_length - ell) // 6
                for a, ell in zip(child.arms, arms1):
                    a.reduced = ell
                    a.mothers = (a.raw_length - ell) // 6
                node.is_owner = True
                node.key = key
                node.ctx = dict(node.ctx or {})
                node.ctx["kind"] = "joint"
                node.family = None
                node.family_index = -1
                node.params = None
                node.labels = dict(labs)
                node.synth = {"head": h0, "arms": list(arms0), "ports": p0,
                              "input": has_input, "basis": basis,
                              "joint_child": child_v, "rows": rows}
                child.folded = True
                child.recruited = list(child.ports)
                child.ordinary = []
                assign = list(range(len(node.arms)))
                for slot, ai in enumerate(assign):
                    node.arms[ai].slot = slot
                self.place_cell(node, None, structs, labs, assign)
                self.joints_used += 1
                self.notes.append(
                    f"vertex {v}: whole-parent joint with {child_v} "
                    f"({child.key}) synthesised on the fly")
                return
            errors.append(f"p0={p0}: no fresh point")
        node.recruited, node.ordinary = saved
        raise Failure("joint", "; ".join(errors[:4]) or "no joint family",
                      vertex=v, context=key)

    #: context tags whose family folds the kept child into the parent's macro
    FOLDING_TAGS = ("L1", "L11", "L12", "A2", "V21", "V22")

    def fold_depth(self, node: NodePlan) -> int:
        """Number of vertices (including ``node``) the macro spans."""
        if not node.key:
            return 1
        tag = node.key.rsplit("_", 1)[-1]
        return 2 if tag in self.FOLDING_TAGS else 1


def node_edges(node: NodePlan) -> List[int]:
    out = list(node.head_edges)
    for a in node.arms:
        out.extend(a.edges)
    out.extend(node.recruited)
    return out


def match_slots(slots: Sequence[int], lengths: Sequence[int]) -> Optional[List[int]]:
    """Assign plan arms to family slots: ``result[slot] = index into lengths``."""
    if len(slots) != len(lengths):
        return None
    for perm in itertools.permutations(range(len(lengths))):
        if all(lengths[perm[s]] == slots[s] for s in range(len(slots))):
            return list(perm)
    return None


def solve_mod(eqs: Sequence[Tuple[Sequence[int], int]], d: int,
              fixed: Dict[int, int], n: int) -> Optional[Dict[int, int]]:
    """Solve a small linear system over ``Z_n`` using unit pivots only.

    ``eqs`` is a list of ``(coefficients, rhs)``; parameters listed in
    ``fixed`` are substituted.  Returns the values of the parameters that had
    to be pinned, or ``None`` when no unit pivot is available.
    """
    rows = []
    for coeffs, rhs in eqs:
        c = [int(x) % n for x in coeffs]
        r = rhs % n
        for i, val in fixed.items():
            r = (r - c[i] * val) % n
            c[i] = 0
        rows.append((c, r))
    pinned: Dict[int, int] = {}
    used_cols: List[int] = []
    for c, r in rows:
        # eliminate the already pinned columns
        for col, val in pinned.items():
            r = (r - c[col] * val) % n
            c = list(c)
            c[col] = 0
        cand = [i for i in range(d) if i not in fixed and i not in pinned
                and c[i] and is_unit(c[i], n)]
        if not cand:
            if all(x % n == 0 for x in c) and r % n == 0:
                continue
            return None
        col = cand[0]
        others = [i for i in cand[1:] if c[i]]
        if others:
            # under-determined: fix the other unknowns to zero for a solution
            for i in others:
                pinned[i] = 0
                r = (r - c[i] * 0) % n
        pinned[col] = r * inv_mod(c[col], n) % n
        used_cols.append(col)
    return pinned



# ==========================================================================
# 4b.  Faithful mode: proof draft section 8 executed literally
# ==========================================================================
#
# ``--faithful`` runs the construction exactly as Lemma F (proof draft
# ``SPARSE_FLAGSHIP_FREE_TOKEN_PROOF_DRAFT_20260901.md`` section 8) states it,
# so that a run in the theorem's regime tests the lemma rather than the
# constructor's mod-n shortcuts:
#
#   * integer labels chosen in boxes ``M*Z cap [-B,B]`` (8.3), reduced mod n
#     only at the very end;
#   * admissibility with the antipode clause (8.2): ``v != 0``,
#     ``v notin Placed u Reserved`` and ``-v notin Placed u Reserved`` unless
#     ``-v`` is Open and ``v`` is its designated antipode -- so the special
#     support is mirror closed up to one pending token;
#   * helper ``-x`` and two-port ``a, -x-a`` absorptions are special labels and
#     the ordinary blocks are zero-sum (no target sums);
#   * deferred token pairing with live symbolic parameters: the carrier sets of
#     ``data/alphabet_carriers.json`` and the scheduler's ``keep_head_symbolic``
#     marks drive cases T0-T3; symbolic labels are affine forms
#     (:class:`LinForm`), collisions are recorded as forbidden affine
#     conditions and the live parameters are chosen at the absorbing cell;
#   * the family of every owner is fixed BEFORE placement (8.0) and the
#     reservation is ``{q*y : q in Phi(F_parent)}`` of that chosen family;
#   * a still-pending token at the end goes to three unused root leaves or to
#     an odd ordinary block of size at least three (the singleton bridge).
#
# Every fallback stays available but each use is recorded as a *lemma gap*
# with its context key, because it is a step the lemma does not license.


class LinForm:
    """An affine form ``c + sum(t[k] * k)`` over the live symbolic parameters."""

    __slots__ = ("c", "t")

    def __init__(self, c=0, t: Optional[Mapping] = None) -> None:
        self.c = Q(c)
        self.t = {k: Q(v) for k, v in (t or {}).items() if Q(v) != 0}

    @property
    def is_num(self) -> bool:
        return not self.t

    def __add__(self, other):
        if not isinstance(other, LinForm):
            other = LinForm(other)
        t = dict(self.t)
        for k, v in other.t.items():
            nv = t.get(k, Q(0)) + v
            if nv:
                t[k] = nv
            else:
                t.pop(k, None)
        return LinForm(self.c + other.c, t)

    __radd__ = __add__

    def __neg__(self):
        return LinForm(-self.c, {k: -v for k, v in self.t.items()})

    def __sub__(self, other):
        return self + (-(other if isinstance(other, LinForm) else LinForm(other)))

    def __mul__(self, k):
        k = Q(k)
        if k == 0:
            return LinForm(0)
        return LinForm(self.c * k, {a: b * k for a, b in self.t.items()})

    __rmul__ = __mul__

    def __eq__(self, other):
        if not isinstance(other, LinForm):
            return self.is_num and self.c == Q(other)
        return self.c == other.c and self.t == other.t

    def __hash__(self):
        return hash((self.c, tuple(sorted(self.t.items()))))

    def __bool__(self):
        return bool(self.c) or bool(self.t)

    def subst(self, assign: Mapping) -> "LinForm":
        out = LinForm(self.c)
        for k, v in self.t.items():
            if k in assign:
                val = assign[k]
                out = out + (val * v if isinstance(val, LinForm) else LinForm(Q(val) * v))
            else:
                out = out + LinForm(0, {k: v})
        return out

    def vars(self) -> set:
        return set(self.t)

    def __repr__(self):
        if self.is_num:
            return f"{self.c}"
        body = " + ".join(f"{v}*{k}" for k, v in sorted(self.t.items()))
        return f"({self.c} + {body})" if self.c else f"({body})"


def lin(x) -> LinForm:
    return x if isinstance(x, LinForm) else LinForm(x)


def as_int(form: LinForm) -> int:
    if not form.is_num or form.c.denominator != 1:
        raise Failure("faithful", f"{form!r} is not an integer")
    return int(form.c)


class LemmaGap(Exception):
    """A step the lemma does not license had to be used."""


CARRIERS_PATH = os.path.join(DATA, "alphabet_carriers.json")
_CARRIERS: Optional[Dict[str, Optional[list]]] = None


def load_carriers(path: str = CARRIERS_PATH) -> Dict[str, Optional[list]]:
    """``context key -> token carrier parameter names`` (proof draft E4).

    Kept only for diagnostics.  The constructor no longer reads it, because the
    file's schema and this reader disagreed for a while without either failing
    loudly: the file now maps a context to a list of records
    ``[{"menu": i, "token_indices": {"carrier": [...]}}]`` while this function
    was documented as returning parameter names, so iterating the value gave
    dictionaries, no carrier was ever found, and every token was silently
    downgraded.  :func:`carrier_indices_of` computes the carrier from the
    family itself instead, which cannot go out of sync.
    """
    global _CARRIERS
    if _CARRIERS is None:
        try:
            with open(path) as fh:
                _CARRIERS = json.load(fh)
        except Exception:
            _CARRIERS = {}
    return _CARRIERS


def carrier_indices_of(fam, token_names: Mapping, free_only: Sequence[int] = ()) -> List[int]:
    """(E4) a carrier for this token, computed from the family.

    The three token forms sum to zero, so on a fixed pair of parameters their
    three 2x2 minors agree up to sign and each candidate pair has one
    well-defined determinant.  Among the pairs on which the token has rank two
    we prefer, in order: a unimodular pair, then a pair avoiding the head, then
    the least absolute determinant.  The first preference matters because a
    unimodular carrier needs no division when the pairing equations are solved;
    the second because the head is what a cell passes to its parent.
    """
    params = list(getattr(fam, "parameters", []))
    if len(params) < 2 or not token_names:
        return []
    try:
        rows = [fam.by_name[token_names[r]].coeffs for r in "ab"]
    except Exception:
        return []
    allowed = set(free_only) if free_only else set(range(len(params)))
    iy = params.index("y") if "y" in params else None
    best = None
    for i in range(len(params)):
        for j in range(i + 1, len(params)):
            if i not in allowed or j not in allowed:
                continue
            det = rows[0][i] * rows[1][j] - rows[0][j] * rows[1][i]
            if det == 0:
                continue
            rank = (abs(det) != 1, iy is not None and iy in (i, j), abs(det))
            if best is None or rank < best[0]:
                best = (rank, [i, j])
    return best[1] if best else []


#: residue-two rigid row as a family-free integer template, in the order
#: ``g0, r0a0x0, r0a0x1, r0a0x2, x`` -- ``(-3x/2; -x/2, -x, x/2; x)`` with
#: ``t = x/2`` (proof draft section 7 / 8.5(4)).  The reservation for a rigid
#: row is ``{-x/2, -x, x/2}``.
RESIDUE2_RIGID_ROW = [-3, -1, -2, 1, 2]


def lcm(a: int, b: int) -> int:
    return a * b // math.gcd(a, b)


def family_is_fa(fam: ftl.Family) -> bool:
    """Forced-antipode: some non-head label is identically minus the head (8c)."""
    hm = Realiser.head_multiplier(fam)
    if hm == 0:
        return False
    return Q(-1) in {q / hm for q in Realiser.head_only_ratios(fam)}


def family_token_rank(fam: ftl.Family) -> int:
    """Rank of the token map recorded by the assembler (E4)."""
    for key in ("token_rank_value", "token_rank"):
        val = fam.meta.get(key)
        if val is None:
            val = fam.payload.get(key)
        try:
            return int(val)
        except (TypeError, ValueError):
            continue
    return 0


RIGID_PATH = os.path.join(DATA, "batches", "alphabet_rigid.jsonl")
_RIGID: Optional[Dict[str, List[ftl.Family]]] = None


def rigid_families(path: str = RIGID_PATH) -> Dict[str, List[ftl.Family]]:
    """Rigid-head families of ``data/batches/alphabet_rigid.jsonl``.

    The direct-edge two-input owners ``h0_1_p0_act2`` and ``h0_2_p0_act2``
    have no free head: their head is a form in the two pinned inputs
    (``(-x1-x2)`` and ``-3(x1+x2)/2``), exactly like the residue-two rigid
    ray.  They live in this batch until the assembler folds them into
    ``data/alphabet_families.json``.
    """
    global _RIGID
    if _RIGID is None:
        out: Dict[str, List[ftl.Family]] = {}
        try:
            with open(path) as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    row = json.loads(line)
                    key = row.get("key")
                    payload = row.get("family") if "family" in row else row
                    try:
                        out.setdefault(key, []).append(
                            ftl.Family(payload, key=key))
                    except Exception:
                        continue
        except OSError:
            out = {}
        _RIGID = out
    return _RIGID


XTOK_PATH = os.path.join(DATA, "alphabet_families_xtok.json")
XALL_PATH = os.path.join(DATA, "alphabet_families_xall.json")
A2_GLOB = os.path.join(DATA, "batches")
_XTOK = None
_XALL = None
_A2: Optional[Dict[str, List[ftl.Family]]] = None


def xall_catalogue(path: str = XALL_PATH):
    """Input-in-token families with *both* input slots in tokens."""
    global _XALL
    if _XALL is None:
        try:
            _XALL = LazyCatalogue(path)
        except Exception:
            _XALL = False
    return _XALL or None


def xtok_catalogue(path: str = XTOK_PATH):
    """Input-in-token families (case (b) for a forced-antipode child).

    Their first token is ``{x, b, -x-b}``: pairing it with the FA child's
    token ``{-x, a, x-a}`` sets ``a = -b`` and closes the child's token, which
    a helper port or a mirror sibling cannot do (working note 13.10).
    """
    global _XTOK
    if _XTOK is None:
        try:
            _XTOK = LazyCatalogue(path)
        except Exception:
            _XTOK = None
    return _XTOK


def a2_families(directory: str = A2_GLOB) -> Dict[str, List[ftl.Family]]:
    """``_A2`` joint macros (parent row + ``h2_1_p0_act2`` child row)."""
    global _A2
    if _A2 is None:
        out: Dict[str, List[ftl.Family]] = {}
        try:
            names = [f for f in os.listdir(directory)
                     if f.startswith("alphabet_A2_") and f.endswith(".jsonl")]
        except OSError:
            names = []
        for name in sorted(names):
            try:
                with open(os.path.join(directory, name)) as fh:
                    for line in fh:
                        line = line.strip()
                        if not line:
                            continue
                        row = json.loads(line)
                        key = row.get("key")
                        payload = row.get("family") if "family" in row else row
                        if not key or not payload:
                            continue
                        try:
                            out.setdefault(key, []).append(
                                ftl.Family(payload, key=key))
                        except Exception:
                            continue
            except OSError:
                continue
        _A2 = out
    return _A2


def family_input_in_token(fam: ftl.Family) -> bool:
    if fam.meta.get("input_in_token") or fam.payload.get("input_in_token"):
        return True
    tok = fam.token_labels()
    if not tok:
        return False
    try:
        inputs = set(fam.input_labels())
    except AttributeError:
        inputs = {fam.input_label()} - {None}
    return bool(inputs & {tok[r] for r in "abc"})


#: The one context that ever occurs with only forced-antipode families
#: (coordinator, catalogue v9).  The ``(1; one port)`` bottom is the other
#: FA-only context but the scheduler always folds it into its parent as child
#: type ``L11``, so it never becomes an owner.
FA_CONTEXTS = ("h2_1_p0_act2",)


def a2_join_key(key: str, extra_ports: int = 0) -> Optional[str]:
    """``v``'s context with child type ``A2`` (and one more port per pinned
    second forced-antipode child)."""
    spec = safe_context_key(key)
    if spec is None:
        return None
    head = "root" if spec["root"] else "h%d" % spec["head"]
    arms = "-".join(str(a) for a in spec["arms"]) or "none"
    return "%s_%s_p%d_A2" % (head, arms, spec["ports"] + extra_ports)


def family_rigid_head(fam: ftl.Family) -> bool:
    """True when the exposed head is a form in the inputs, not a free parameter."""
    name = fam.head_label()
    if name is None:
        return False
    try:
        inputs = set(fam.input_labels())
    except AttributeError:
        inputs = {fam.input_label()} - {None}
    input_idx = set()
    for nm in inputs:
        spec = Realiser.single_parameter(fam, nm)
        if spec is not None:
            input_idx.add(spec[0])
    coeffs = fam.by_name[name].coeffs
    nz = [i for i, c in enumerate(coeffs) if c]
    if len(nz) == 1 and nz[0] not in input_idx:
        return False
    return True


def family_two_tokens(fam: ftl.Family) -> Optional[Dict[str, str]]:
    """The second token of a two-token family (8c), by label name."""
    named = fam.payload.get("token2_named")
    if isinstance(named, dict) and set(named) >= {"a", "b", "c"}:
        return {r: named[r] for r in "abc"}
    idx = fam.payload.get("token2_indices")
    if isinstance(idx, dict) and set(idx) >= {"a", "b", "c"}:
        try:
            return {r: fam.by_index[idx[r]].name for r in "abc"}
        except KeyError:
            return None
    return None


def family_rank(fam: ftl.Family, pos: int) -> tuple:
    """Ranking key of proof draft 8.0, refined by 8c and the coordinator.

    Non-forced-antipode first, then ``Phi(F) subseteq {-1}``, then ``clean``,
    then a token of rank at least two, then *more* effective freedom (a ray
    has almost none and is what starves the box search), then the menu order.
    """
    phi = Realiser.forced_ratios(fam)
    e6 = phi <= {Q(-1)}
    has_token = fam.token_labels() is not None
    rank_bad = 1 if (has_token and family_token_rank(fam) < 2) else 0
    try:
        freedom = int(fam.meta.get("effective_freedom")
                      or fam.payload.get("effective_freedom") or 0)
    except (TypeError, ValueError):
        freedom = 0
    return (1 if family_is_fa(fam) else 0, 0 if e6 else 1,
            0 if fam.meta.get("clean") else 1, rank_bad, -freedom, pos)


def choose_families(plan: "Plan", cat) -> Tuple[Dict[int, dict], List[dict]]:
    """Fix the family menu of every owner *before* placement (8.0 and 8c).

    Each owner gets an ordered shortlist; the realiser uses the first entry
    and may fall back to the next ones (recorded, since 8.0 fixes one family).
    """
    chosen: Dict[int, dict] = {}
    missing: List[dict] = []
    for v, node in sorted(plan.nodes.items()):
        if not node.is_owner or not node.key:
            continue
        cands = []
        pos = 0
        for k in Realiser.candidate_keys(Realiser, node.key):
            for fam in list(cat.get(k) or []) + rigid_families().get(k, []):
                cands.append((family_rank(fam, pos),
                              {"key": k, "index": pos, "family": fam,
                               "e6": Realiser.forced_ratios(fam) <= {Q(-1)},
                               "fa": family_is_fa(fam),
                               "rigid_head": family_rigid_head(fam)}))
                pos += 1
        if not cands:
            missing.append({"vertex": v, "context": node.key})
            continue
        cands.sort(key=lambda t: t[0])
        rec = dict(cands[0][1])
        rec["menu"] = [c[1] for c in cands[:6]]
        rec["cands"] = cands
        chosen[v] = rec

    # second pass (coordinator 2026-09-02): a cell with a forced-antipode
    # child JOINS one of them -- the joint context is the cell's context with
    # child type A2, which is never forced-antipode, so the absorption stops
    # after one step.  A second FA child stays pinned and is written as one
    # more port of the joint.  Input-in-token families are the alternative but
    # joining is preferred because it keeps the induction valid.
    for v, node in sorted(plan.nodes.items()):
        rec = chosen.get(v)
        if rec is None or not node.kept:
            continue
        tag = (node.key or "").rsplit("_", 1)[-1]
        if tag in ("L1", "L11", "L12", "A2"):
            rec["fa_case"] = "c"
            continue
        fa_kids = [c for c in node.kept
                   if (plan.nodes.get(c) is not None
                       and plan.nodes[c].key in FA_CONTEXTS)]
        if not fa_kids:
            continue
        extra = []
        pos = 10_000
        jkey = a2_join_key(node.key, max(0, len(fa_kids) - 1))
        if jkey:
            for src in (a2_families().get(jkey, []), (cat.get(jkey) or [])):
                for fam in src:
                    extra.append((family_rank(fam, pos),
                                  {"key": jkey, "index": pos, "family": fam,
                                   "e6": True, "fa": family_is_fa(fam),
                                   "rigid_head": family_rigid_head(fam),
                                   "case": "c"}))
                    pos += 1
        pos = 20_000                     # only if no joint family exists
        for table in (xall_catalogue(), xtok_catalogue()):
            if table is None:
                continue
            for fam in (table.get(node.key) or []):
                if family_input_in_token(fam):
                    extra.append((family_rank(fam, pos),
                                  {"key": node.key, "index": pos,
                                   "family": fam, "e6": True, "fa": False,
                                   "rigid_head": family_rigid_head(fam),
                                   "case": "b"}))
                    pos += 1
        if not extra:
            rec["fa_case"] = "none"
            continue
        # the joined child must be the first kept child (fold_depth folds kept[0])
        node.kept = fa_kids[:1] + [c for c in node.kept if c != fa_kids[0]]
        node.retained = node.kept[0]
        merged = sorted(extra + rec["cands"], key=lambda t: t[0])
        rec.update(merged[0][1])
        rec["menu"] = [c[1] for c in merged[:6]]
        rec["fa_case"] = merged[0][1].get("case", "c")
    return chosen, missing


class FaithfulRealiser:
    """Lemma F (proof draft section 8) executed literally over the integers."""

    def __init__(self, plan: "Plan", catalogue, rng: random.Random,
                 tries: int = 400, allow_fallback: bool = True) -> None:
        self.plan = plan
        self.n = plan.n
        self.cat = catalogue
        self.rng = rng
        self.tries = tries
        self.allow_fallback = allow_fallback
        self.choice, missing = choose_families(plan, catalogue)
        self.gaps: List[dict] = [dict(m, reason="no catalogue family")
                                 for m in missing]
        self.M = 24 * 15
        for rec in self.choice.values():
            self.M = lcm(self.M, rec["family"].L)
        self.labels: Dict[int, LinForm] = {}
        self.placed: set = set()          # numeric special values
        self.reserved: set = set()
        self.open: set = set()            # placed values whose antipode is due
        self.symbolic: Dict[int, LinForm] = {}
        self.conditions: List[LinForm] = []
        self.live: List[str] = []
        self.pending: List[dict] = []      # 8c: at most two pending tokens
        self.max_pending = 0
        self.budget = 60
        self.subtree_retries = 2
        self.tokens: List[dict] = []
        self.notes: List[str] = []
        self.max_live = 0
        self.max_symbolic = 0
        self.max_magnitude = 0
        self.counters: Counter = Counter()

    # -- state ------------------------------------------------------------
    def admissible(self, value: Q) -> Optional[str]:
        """The admissibility rule of 8.2 for one numeric label."""
        if value == 0:
            return "zero label"
        if value in self.placed or value in self.reserved:
            return f"{value} already placed/reserved"
        if -value in self.reserved:
            return f"antipode {-value} is reserved"
        if -value in self.placed and -value not in self.open:
            return f"antipode {-value} is placed and not open"
        return None

    def check_batch(self, forms: Sequence[LinForm], who: str) -> None:
        """Validate a set of labels placed simultaneously (mirror pairs allowed)."""
        nums = [f.c for f in forms if f.is_num]
        if any(x == 0 for x in nums):
            raise Failure("faithful", f"zero label in {who}")
        if len(set(nums)) != len(nums):
            raise Failure("faithful", f"repeated label in {who}")
        inside = set(nums)
        for x in nums:
            if x in self.placed or x in self.reserved:
                raise Failure("faithful", f"{who}: {x} already placed/reserved")
            if -x in inside:
                continue                      # a mirror pair inside the batch
            if -x in self.reserved:
                raise Failure("faithful", f"{who}: antipode of {x} is reserved")
            if -x in self.placed and -x not in self.open:
                raise Failure("faithful",
                              f"{who}: antipode of {x} is placed and not open")

    def commit(self, edge: int, form: LinForm, who: str) -> None:
        if edge in self.labels:
            raise Failure("faithful", f"edge {edge} already labelled ({who})")
        self.labels[edge] = form
        if form.is_num:
            self.placed.add(form.c)
            self.max_magnitude = max(self.max_magnitude, abs(int(form.c)))
        else:
            self.symbolic[edge] = form
            self.max_symbolic = max(self.max_symbolic, len(self.symbolic))
            self.record_conditions(form)

    def close_batch(self, forms: Sequence[LinForm]) -> None:
        """Update ``Open``: a label is open until its antipode is placed."""
        nums = {f.c for f in forms if f.is_num}
        for x in nums:
            if -x in self.open:
                self.open.discard(-x)
            elif -x not in nums:
                self.open.add(x)

    def record_conditions(self, form: LinForm) -> None:
        """Every collision of a symbolic label becomes a forbidden condition."""
        if form.is_num:
            return
        self.conditions.append(form)                       # != 0
        for x in self.placed:
            self.conditions.append(form - LinForm(x))
            self.conditions.append(form + LinForm(x))
        for other in list(self.symbolic.values()):
            if other is form:
                continue
            d1, d2 = form - other, form + other
            if d1:
                self.conditions.append(d1)
            if d2:
                self.conditions.append(d2)

    # -- parameter boxes ---------------------------------------------------
    def box_values(self, count: int, stage: int) -> List[int]:
        radius = self.M * (4 << stage)
        return [self.rng.randrange(-radius // self.M, radius // self.M + 1) * self.M
                for _ in range(count)]

    def sample(self, count: int, accept) -> Optional[List[int]]:
        """Choose ``count`` lattice values in a growing box (8.3).

        With one or two free coordinates the box is *enumerated* in order of
        increasing magnitude: those cells are rays (effective freedom 1) and a
        random walk misses the few admissible points (this is what starved
        ``root_2_p2_act``, ``h1_1_p2_act`` and ``h0_2_p2_act``).
        """
        if count == 1:
            for mag in range(1, 400):
                for sgn in (1, -1):
                    got = accept([sgn * mag * self.M])
                    if got is not None:
                        return got
            return None
        if count == 2:
            for radius in range(1, 26):
                for a in range(-radius, radius + 1):
                    for b in range(-radius, radius + 1):
                        if max(abs(a), abs(b)) != radius or a == 0 or b == 0:
                            continue
                        got = accept([a * self.M, b * self.M])
                        if got is not None:
                            return got
            return None
        for stage in range(9):
            for _ in range(max(60, self.tries // 2)):
                vals = self.box_values(count, stage)
                if any(x == 0 for x in vals):
                    continue
                got = accept(vals)
                if got is not None:
                    return got
        return None

    # -- helpers -----------------------------------------------------------
    @staticmethod
    def label_forms(fam: ftl.Family, values: Sequence[LinForm]) -> Dict[str, LinForm]:
        out: Dict[str, LinForm] = {}
        inv = Q(1, fam.L)
        for lb in fam.labels:
            if not lb.physical:
                continue
            acc = LinForm(0)
            for c, val in zip(lb.coeffs, values):
                if c:
                    acc = acc + val * c
            out[lb.name] = acc * inv
        return out

    def head_value(self, v: int) -> Optional[LinForm]:
        node = self.plan.nodes[v]
        return node.head_value

    def reservation(self, node: NodePlan, head: LinForm) -> List[Q]:
        """``{q*y : q in Phi(F_parent)}`` for the *chosen* parent family (8.3)."""
        if node.is_root or not head.is_num:
            return []
        u = self.plan.parent_core(node.vertex)
        if u is None:
            return []
        pnode = self.plan.nodes.get(u)
        if pnode is None:
            return []
        for group in pnode.cancelled:
            if node.vertex in group and len(group) == 2:
                return [-head.c]
        if pnode.retained != node.vertex:
            return []
        rec = self.choice.get(u)
        if rec is None:
            if not pnode.is_owner and (pnode.absorption or {}).get("type") == "helper":
                return [-head.c]
            return []
        return [q * head.c for q in Realiser.forced_ratios(rec["family"])]

    # -- subtree checkpoints (a rigid-head owner must be able to re-choose
    #    the heads of its two inputs, 8c / coordinator 2026-09-02) ----------
    def subtree(self, v: int) -> List[int]:
        out = [v]
        for u in self.plan.children_of(v):
            out.extend(self.subtree(u))
        return out

    def full_checkpoint(self, vs: Sequence[int]) -> dict:
        nodes = {}
        for v in vs:
            nd = self.plan.nodes[v]
            arms = [(a, a.slot, a.mothers, list(a.values), a.reduced)
                    for a in nd.arms]
            units = [(u, list(u.arms), [list(b) for b in u.base], u.scale,
                      [(a, a.slot, a.mothers, list(a.values), a.reduced)
                       for a in u.arms]) for u in nd.units]
            nodes[v] = (nd.is_owner, nd.folded, nd.key, list(nd.recruited),
                        list(nd.ordinary), nd.family, nd.labels, nd.params,
                        nd.head_value, nd.synth,
                        dict(nd.absorption) if nd.absorption else None,
                        arms, units)
        return {"state": self.snapshot(), "nodes": nodes,
                "gaps": list(self.gaps), "counters": Counter(self.counters)}

    def full_restore(self, cp: dict) -> None:
        self.restore(cp["state"])
        self.gaps = list(cp["gaps"])
        self.counters = Counter(cp["counters"])
        for v, snap in cp["nodes"].items():
            nd = self.plan.nodes[v]
            (nd.is_owner, nd.folded, nd.key, rec, ordn, nd.family, nd.labels,
             nd.params, nd.head_value, nd.synth, nd.absorption,
             arms, units) = snap
            nd.recruited, nd.ordinary = list(rec), list(ordn)
            for a, slot, mothers, values, reduced in arms:
                a.slot, a.mothers, a.values, a.reduced = slot, mothers, list(values), reduced
            nd.units = []
            for u, uarms, base, scale, arminfo in units:
                u.arms, u.base, u.scale = list(uarms), [list(b) for b in base], scale
                for a, slot, mothers, values, reduced in arminfo:
                    a.slot, a.mothers, a.values, a.reduced = slot, mothers, list(values), reduced
                nd.units.append(u)

    # -- the bottom-up sweep ----------------------------------------------
    def run(self) -> None:
        self._visit_retry(self.plan.root, None, False)

    def _visit_retry(self, v: int, forced_head, skip_cell: bool) -> None:
        if self.budget <= 0:
            self._visit(v, forced_head, skip_cell)
            return
        cp = self.full_checkpoint(self.subtree(v))
        last: Optional[Failure] = None
        for attempt in range(self.subtree_retries + 1):
            try:
                self._visit(v, forced_head, skip_cell)
                return
            except Failure as exc:
                last = exc
                if attempt == self.subtree_retries or self.budget <= 0:
                    break
                self.budget -= 1
                self.counters["subtree_retries"] += 1
                self.full_restore(cp)
        assert last is not None
        raise last

    def _visit(self, v: int, forced_head: Optional["LinForm"],
               skip_cell: bool) -> None:
        node = self.plan.nodes[v]
        active = set(node.active)
        for u in self.plan.children_of(v):
            if u not in active:
                self._visit_retry(u, None, False)
        if (node.absorption or {}).get("type") == "port_into_group":
            self.realise_lone_port(node)
        for gi, group in enumerate(node.cancelled):
            for u in group[:-1]:
                self._visit_retry(u, None, False)
            total = LinForm(0)
            if gi == 0 and (node.absorption or {}).get("type") == "port_into_group":
                total = total + LinForm(node.absorption.get("value", 0))
            for u in group[:-1]:
                hv = self.plan.nodes[u].head_value
                if hv is None:
                    raise Failure("faithful",
                                  f"cancelled child {u} has no head", vertex=v)
                total = total + hv
            self._visit_retry(group[-1], -total, False)
            self.after_cancel_group(node, gi, group)
        depth = 1 if skip_cell else self.fold_depth(node)
        for i, c in enumerate(node.kept):
            cnode = self.plan.nodes[c]
            fold_it = (i == 0 and depth > 1) or cnode.passthrough is not None
            if fold_it:
                cnode.folded = True
                self._visit_retry(c, None, True)
            else:
                self._visit_retry(c, None, False)
        if not node.is_owner:
            self.realise_absorption(node)
        self.realise_units(node)
        if node.is_owner and not skip_cell:
            self.realise_cell(node, forced_head)

    def after_cancel_group(self, node: NodePlan, gi: int, group) -> None:
        """Hook run once a cancelled group's heads are all numeric.

        A group of two is a mirror pair and is closed under negation; a group
        of three is a free zero-sum triple, whose negatives the sink route has
        to place.  The base realiser does nothing here.
        """
        return None

    def fold_depth(self, node: NodePlan) -> int:
        rec = self.choice.get(node.vertex)
        if rec is None:
            return 1
        return len(rec["family"].structure())

    # -- absorptions (8.3, stationary vertices) ----------------------------
    def realise_lone_port(self, node: NodePlan) -> None:
        info = node.absorption
        got = self.sample(1, lambda vals: vals
                          if self.admissible(Q(vals[0])) is None else None)
        if got is None:
            raise Failure("faithful", "no fresh label for the lone port",
                          vertex=node.vertex)
        form = LinForm(got[0])
        self.check_batch([form], f"lone port at {node.vertex}")
        self.commit(info["port"], form, f"lone port at {node.vertex}")
        self.close_batch([form])
        info["value"] = got[0]

    def realise_absorption(self, node: NodePlan) -> None:
        """Helper ``-x`` (q = 1 or q >= 3) and two-port ``a, -x-a`` (q = 2)."""
        info = node.absorption
        if not info or info["type"] != "port_block":
            return
        v = node.vertex
        if node.retained is None:
            return
        x = self.plan.nodes[node.retained].head_value
        if x is None:
            raise Failure("faithful", f"active child {node.retained} has no head",
                          vertex=v)
        ports = list(node.ports)
        if len(ports) >= 2:
            if self.pending:
                if self.two_port_absorbs(node, x, ports):
                    return
                if len(self.pending) >= 2:
                    self.gap(node, "two-port absorption with two tokens pending")
            # two-port absorption: a fresh `a`, then `-x-a`; the triple
            # {x, a, -x-a} is a rank-two token (ROUTE_CORE section 4 case 2)
            def accept(vals):
                a = LinForm(vals[0])
                b = -x - a
                if a == b:
                    return None
                nums = [f for f in (a, b) if f.is_num]
                try:
                    self.check_batch(nums, f"two-port at {v}")
                except Failure:
                    return None
                return [a, b]
            got = self.sample(1, accept)
            if got is None:
                raise Failure("faithful", "no fresh two-port absorption", vertex=v)
            a, b = got
            self.commit(ports[0], a, f"two-port at {v}")
            self.commit(ports[1], b, f"two-port at {v}")
            self.close_batch([f for f in (a, b) if f.is_num])
            node.ordinary = list(ports[2:])
            info["type"] = "two_port"
            info["values"] = [str(a), str(b)]
            self.register_token(v, [x, a, b], absorbed=None)
            return
        # helper absorption: -x on one port (symbolic when x is), the rest is
        # a zero-sum block
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

    def two_port_absorbs(self, node: NodePlan, x: LinForm,
                         ports: Sequence[int]) -> bool:
        """Cancel the pending token with the two-port triple ``{x, a, -x-a}``.

        The triple is prescribed to be ``-T_A``: one matching fixes
        ``x = -T_A[s0]`` (a linear condition on the live parameters) and then
        ``a = -T_A[s1]``, ``-x-a = -T_A[s2]`` follow.  This is case T2 with the
        one-coordinate carrier of a two-port absorption.
        """
        v = node.vertex
        if not self.pending:
            return False
        pend = self.pending[0]
        TA = pend["token"]
        for perm in itertools.permutations(range(3)):
            eq = x + TA[perm[0]]                 # must vanish
            a = -TA[perm[1]]
            b = -TA[perm[2]]
            assignment = self.choose_live_with(eq, {"a": a, "b": b})
            if assignment is None:
                continue
            snapshot = self.snapshot()
            try:
                av, bv = a.subst(assignment), b.subst(assignment)
                self.apply_live(assignment)
                self.check_batch([av, bv], f"two-port at {v}")
                self.commit(ports[0], av, f"two-port at {v}")
                self.commit(ports[1], bv, f"two-port at {v}")
                self.close_batch([av, bv])
            except Failure:
                self.restore(snapshot)
                continue
            node.ordinary = []
            info = node.absorption
            info["type"] = "two_port"
            info["values"] = [int(av.c), int(bv.c)]
            self.register_token(v, [x.subst(assignment), av, bv],
                                absorbed=pend["vertex"])
            self.counters["T2_two_port_pairings"] += 1
            self.counters["fa_case_a"] += 1
            return True
        return False

    @staticmethod
    def solve_equalities(equalities: Sequence[LinForm], live: Sequence[str]):
        """Solve ``eq == 0`` for some live variables in terms of the others.

        Returns ``(free vars, {pivot var: (const, {free var: coeff})})`` where
        ``pivot = const + sum(coeff * free)``, or ``None`` if inconsistent.
        The equations of 8c (``T_v = -T_A``, ``T' = -T``) must be *solved*, not
        sampled: two linear conditions are almost never met by a random point.
        """
        live = list(live)
        rows = [[eq.t.get(v, Q(0)) for v in live] + [eq.c] for eq in equalities]
        piv_cols: List[int] = []
        r = 0
        for c in range(len(live)):
            pick = None
            for i in range(r, len(rows)):
                if rows[i][c] != 0:
                    pick = i
                    break
            if pick is None:
                continue
            rows[r], rows[pick] = rows[pick], rows[r]
            f = rows[r][c]
            rows[r] = [x / f for x in rows[r]]
            for i in range(len(rows)):
                if i != r and rows[i][c] != 0:
                    g = rows[i][c]
                    rows[i] = [a - g * b for a, b in zip(rows[i], rows[r])]
            piv_cols.append(c)
            r += 1
            if r == len(rows):
                break
        for i in range(r, len(rows)):
            if all(x == 0 for x in rows[i][:-1]) and rows[i][-1] != 0:
                return None
        free = [c for c in range(len(live)) if c not in piv_cols]
        exprs = {}
        for i, c in enumerate(piv_cols):
            exprs[live[c]] = (-rows[i][-1],
                              {live[f]: -rows[i][f] for f in free})
        return [live[f] for f in free], exprs

    def choose_live_with(self, equalities, extra: Mapping) -> Optional[Dict[str, Q]]:
        """Live parameters solving every equality and avoiding every condition."""
        if isinstance(equalities, LinForm):
            equalities = [equalities]
        live = set()
        for eq in equalities:
            live |= eq.vars()
        for f in self.symbolic.values():
            live |= f.vars()
        for f in extra.values():
            live |= f.vars()
        for pd in self.pending:
            for t in pd["token"]:
                live |= t.vars()
        live = sorted(live)
        if not live:
            return {} if not any(equalities) else None
        self.max_live = max(self.max_live, len(live))
        solved = self.solve_equalities(equalities, live)
        if solved is None:
            return None
        free, exprs = solved
        for stage in range(9):
            for _ in range(max(80, self.tries // 2)):
                assign = {nm: Q(x) for nm, x in
                          zip(free, self.box_values(len(free), stage))}
                if any(x == 0 for x in assign.values()):
                    continue
                ok = True
                for nm, (const, coeffs) in exprs.items():
                    val = const
                    for fv, cf in coeffs.items():
                        val += cf * assign[fv]
                    if val == 0 or val.denominator != 1:
                        ok = False
                        break
                    assign[nm] = val
                if not ok:
                    continue
                if any(eq.subst(assign) for eq in equalities):
                    continue
                bad = False
                for c in self.conditions:
                    cc = c.subst(assign)
                    if cc.is_num and not cc:
                        bad = True
                        break
                if bad:
                    continue
                vals = [f.subst(assign) for f in
                        list(self.symbolic.values()) + list(extra.values())]
                if any(f.is_num and f.c.denominator != 1 for f in vals):
                    continue
                nums = [f.c for f in vals if f.is_num]
                if any(y == 0 for y in nums) or len(set(nums)) != len(nums):
                    continue
                if any(y in self.placed for y in nums):
                    continue
                return assign
        return None

    # -- neutral units ------------------------------------------------------
    def realise_units(self, node: NodePlan) -> None:
        for unit in node.units:
            self.realise_unit(node, unit)

    def realise_unit(self, node: NodePlan, unit: UnitPlan) -> None:
        v = node.vertex
        fams = unit_families()
        reduced = sorted(cs.reduce6(a.raw_length) for a in unit.arms)
        fam = fams.get("unit_" + "-".join(str(x) for x in reduced))
        if fam is None:
            raise Failure("faithful",
                          f"no neutral-unit family for {reduced}", vertex=v)
        rs = fam.structure()[0]
        order = match_slots([len(a) - 1 for a in rs.arms],
                            [cs.reduce6(a.raw_length) for a in unit.arms])
        if order is None:
            raise Failure("faithful", "unit arm lengths do not match", vertex=v)

        def accept(vals):
            labs = self.label_forms(fam, [LinForm(x) for x in vals])
            forms = list(labs.values())
            if any(not f.is_num or f.c.denominator != 1 for f in forms):
                return None
            try:
                self.check_batch(forms, f"neutral unit at {v}")
            except Failure:
                return None
            return labs

        labs = self.sample(len(fam.parameters), accept)
        if labs is None:
            raise Failure("faithful", f"no fresh neutral unit {reduced}", vertex=v)
        batch: List[LinForm] = []
        for slot, ai in enumerate(order):
            arm = unit.arms[ai]
            base = [labs[nm] for nm in rs.arms[slot]]
            arm.reduced = len(base) - 1
            extra = arm.raw_length - arm.reduced
            if extra < 0 or extra % 6:
                raise Failure("faithful", "unit arm does not reduce", vertex=v)
            arm.mothers = extra // 6
            full = self.extend_arm(base, arm.mothers, f"unit at {v}")
            arm.values = [int(f.c) for f in full]
            for edge, form in zip(arm.edges, full):
                self.commit(edge, form, f"neutral unit at {v}")
            batch += full
        unit.base = [[int(labs[nm].c) for nm in rs.arms[slot]]
                     for slot in range(len(rs.arms))]
        unit.scale = 1
        unit.source = fam.key
        self.close_batch(batch)

    # -- integer local moves ------------------------------------------------
    def extend_arm(self, values: Sequence[LinForm], mothers: int,
                   who: str) -> List[LinForm]:
        out = list(values)
        for _ in range(mothers):
            terminal = out[-1]
            if not terminal.is_num:
                raise Failure("faithful",
                              f"{who}: six-edge mother on a symbolic terminal")
            got = self.sample(1, lambda vals, a=terminal: self._mother(a, vals[0]))
            if got is None:
                raise Failure("faithful", f"{who}: no fresh six-edge mother")
            out.extend(got)
            self.close_batch(got)
        return out

    def _mother(self, terminal: LinForm, t: int) -> Optional[List[LinForm]]:
        if t == 0:
            return None
        try:
            block = ftl.mother_extension(int(terminal.c), int(t))
        except ftl.Degenerate:
            return None
        forms = [LinForm(x) for x in block]
        try:
            self.check_batch(forms, "six-edge mother")
        except Failure:
            return None
        return forms

    def extend_chain(self, values: List[LinForm], raw: int,
                     who: str) -> List[LinForm]:
        out = list(values)
        need = raw - (len(values) - 1)
        if need == 0:
            return out
        if need < 0 or need % 6:
            raise Failure("faithful", f"{who}: head chain cannot be extended")
        while need > 0:
            if len(out) < 2:
                raise Failure("faithful", f"{who}: no head-chain gap")
            block = None
            step = 0
            for gap in range(len(out) - 1):
                left, right = out[gap], out[gap + 1]
                if not (left.is_num and right.is_num):
                    continue
                if need >= 12:
                    got = self.sample(
                        1, lambda vals, L=left, R=right: self._twelve(L, R, vals[0]))
                    if got is not None:
                        block, step = (gap, got), 12
                        break
                got = self._six(left, right)
                if got is not None:
                    block, step = (gap, got), 6
                    break
            if block is None:
                raise Failure("faithful",
                              f"{who}: no fresh endpoint-preserving insertion")
            gap, values_new = block
            out[gap + 1:gap + 1] = values_new
            self.close_batch(values_new)
            need -= step
        return out

    def _twelve(self, left: LinForm, right: LinForm, t: int) -> Optional[List[LinForm]]:
        block = ftl.twelve_insertion(int(left.c), int(right.c), int(t))
        forms = [LinForm(x) for x in block]
        if len(set(block)) != 12 or any(x == 0 for x in block):
            return None
        try:
            self.check_batch(forms, "twelve insertion")
        except Failure:
            return None
        return forms

    def _six(self, left: LinForm, right: LinForm) -> Optional[List[LinForm]]:
        L, R = Q(left.c), Q(right.c)
        vals = [a * L + b * R for a, b in SIX_INSERTIONS[0]]
        if any(x.denominator != 1 for x in vals):
            return None
        if any(x == 0 for x in vals) or len(set(vals)) != 6:
            return None
        forms = [LinForm(x) for x in vals]
        path = [L] + vals + [R]
        sums = Counter(path[i] + path[i + 1] for i in range(len(path) - 1))
        if sums != Counter(vals + [L + R]):
            return None
        try:
            self.check_batch(forms, "six insertion")
        except Failure:
            return None
        return forms

    # -- tokens -------------------------------------------------------------
    def register_token(self, vertex: int, token: Sequence[LinForm],
                       absorbed: Optional[int]) -> None:
        """Record a token.  Proof draft 8c allows at most two pending at once."""
        self.tokens.append({"vertex": vertex,
                            "values": [str(t) for t in token],
                            "paired_with": absorbed})
        if absorbed is not None:
            self.pending = [pd for pd in self.pending
                            if pd["vertex"] != absorbed]
            return
        if len(self.pending) >= 2:
            key = self.plan.nodes[vertex].key if vertex in self.plan.nodes else None
            self.gaps.append({"vertex": vertex, "context": key,
                              "reason": "8c: a third token became pending"})
            self.counters["third_pending_token"] += 1
            return
        self.pending.append({"vertex": vertex, "token": list(token)})
        self.max_pending = max(self.max_pending, len(self.pending))

    # -- cells (8.3, cases T0-T3) -------------------------------------------
    def realise_cell(self, node: NodePlan,
                     forced_head: Optional["LinForm"]) -> None:
        v = node.vertex
        rec = self.choice.get(v)
        if rec is None:
            self.gap(node, "no catalogue family; synthesised fallback")
            return self.fallback_cell(node, forced_head)
        shortlist = rec.get("menu") or [rec]
        snapshot = self.snapshot()
        last: Optional[Failure] = None
        for pos, entry in enumerate(shortlist):
            if pos:
                self.restore(snapshot)
            try:
                self._realise_cell_with(node, entry, forced_head)
                if pos:
                    self.counters["family_second_choice"] += 1
                return
            except Failure as exc:
                last = exc
        self.restore(snapshot)
        assert last is not None
        if self.allow_fallback:
            self.gap(node, f"every catalogue family failed "
                           f"({last.report.get('detail')})")
            return self.fallback_cell(node, forced_head)
        raise last

    def _realise_cell_with(self, node: NodePlan, rec: dict,
                           forced_head: Optional["LinForm"]) -> None:
        v = node.vertex
        fam, key = rec["family"], rec["key"]
        if not rec["e6"]:
            self.counters["family_not_forced_only_antipode"] += 1
        if rec.get("fa_case") in ("b", "c"):
            self.counters["fa_case_" + rec["fa_case"]] += 1
        if rec.get("rigid_head"):
            # the head is a form in the pinned inputs: no head freedom, so a
            # collision can only be repaired by re-choosing the children's
            # heads, which the subtree retry does
            self.counters["rigid_head_cells"] += 1
        struct = fam.structure()
        chain_nodes = self.fold_chain_nodes(node, len(struct))
        if len(chain_nodes) != len(struct):
            raise Failure("cell", f"family has {len(struct)} rows but only "
                          f"{len(chain_nodes)} vertices fold in",
                          vertex=v, context=key)
        row0 = struct[0]
        if len(row0.arms) != len(node.arms) or len(row0.ports) != len(node.recruited):
            raise Failure("cell", "family topology does not match the plan",
                          vertex=v, context=key)
        assign = match_slots([len(a) - 1 for a in row0.arms],
                             [a.reduced for a in node.arms])
        if assign is None:
            raise Failure("cell", "arm lengths do not match the family slots",
                          vertex=v, context=key)
        for a in node.arms:
            extra = a.raw_length - a.reduced
            if extra < 0 or extra % 6:
                raise Failure("faithful", f"arm {a.raw_length} does not reduce",
                              vertex=v, context=key)
            a.mothers = extra // 6

        d = fam.d
        values: List[Optional[LinForm]] = [None] * d
        try:
            input_names = list(fam.input_labels())
        except AttributeError:
            one = fam.input_label()
            input_names = [one] if one else []
        bottom = chain_nodes[-1]
        if input_names:
            if len(bottom.kept) < len(input_names):
                raise Failure("cell",
                              "family wants more input heads than the plan keeps",
                              vertex=v, context=key)
            for nm, src in zip(input_names, bottom.kept):
                xv = self.plan.nodes[src].head_value
                if xv is None:
                    raise Failure("faithful", f"active child {src} has no head",
                                  vertex=v, context=key)
                spec = Realiser.single_parameter(fam, nm)
                if spec is None:
                    raise Failure("cell",
                                  "the input label is not a single parameter",
                                  vertex=v, context=key)
                i, c = spec
                values[i] = xv * Q(fam.L, c)
        head_name = fam.head_label()
        if forced_head is not None:
            spec = Realiser.single_parameter(fam, head_name) if head_name else None
            if spec is None:
                raise Failure("cell",
                              "the head label is not a single parameter",
                              vertex=v, context=key)
            i, c = spec
            if values[i] is not None:
                raise Failure("faithful", "head and input share a parameter",
                              vertex=v, context=key)
            values[i] = lin(forced_head) * Q(fam.L, c)

        token_names = fam.token_labels()
        token2_names = family_two_tokens(fam)
        if token2_names:
            self.counters["two_token_cells"] += 1
        tokens = [t for t in (token_names, token2_names) if t]
        if family_is_fa(fam):
            self.counters["forced_antipode_family_used"] += 1
        undetermined = [i for i in range(len(fam.parameters)) if values[i] is None]
        carrier_idx = carrier_indices_of(fam, token_names, undetermined) if token_names else []
        free_idx = [i for i in range(d) if values[i] is None]
        if token_names and not self.carrier_has_rank_two(fam, token_names,
                                                         carrier_idx):
            carrier_idx = []
            self.counters["carrier_rank_below_two"] += 1

        if tokens and self.pending and len(carrier_idx) == 2:
            if self.absorb_pending(node, fam, key, values, free_idx, carrier_idx,
                                   tokens, struct, chain_nodes, assign):
                return
            self.counters["T2_solve_failed"] += 1
        if tokens and len(carrier_idx) == 2 and len(self.pending) < 2:
            # 8c: a token that cannot be paired now is kept symbolic anyway, so
            # that two pending tokens can still be paired with each other at
            # the root (both carriers stay live)
            if self.emit_symbolic_token(node, fam, key, values, free_idx,
                                        carrier_idx, tokens, struct,
                                        chain_nodes, assign):
                return
            self.counters["T1_downgraded_to_numeric"] += 1
        self.numeric_cell(node, fam, key, values, free_idx, tokens,
                          struct, chain_nodes, assign)

    @staticmethod
    def carrier_has_rank_two(fam: ftl.Family, token_names: Mapping,
                             carrier_idx: Sequence[int]) -> bool:
        """(E4) the token map must have rank two on the carrier."""
        if len(carrier_idx) != 2:
            return False
        rows = []
        for r in "abc":
            vec = fam.by_name[token_names[r]].coeffs
            rows.append([Q(vec[i]) for i in carrier_idx])
        for i in range(3):
            for j in range(i + 1, 3):
                if rows[i][0] * rows[j][1] - rows[i][1] * rows[j][0] != 0:
                    return True
        return False

    def gap(self, node: NodePlan, reason: str) -> None:
        self.gaps.append({"vertex": node.vertex, "context": node.key,
                          "reason": reason})

    def fold_chain_nodes(self, node: NodePlan, rows: int) -> List[NodePlan]:
        out = [node]
        cur = node
        while len(out) < rows:
            if cur.retained is None:
                break
            cur = self.plan.nodes[cur.retained]
            out.append(cur)
        return out

    # -- T0 / T3: everything numeric ---------------------------------------
    def numeric_cell(self, node, fam, key, values, free_idx, tokens,
                     struct, chain_nodes, assign) -> None:
        v = node.vertex

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
            raise Failure("parameters", f"no admissible parameter point for {key}",
                          vertex=v, context=key)
        trial, labs = got
        self.finish_cell(node, fam, key, trial, labs, struct, chain_nodes, assign)
        for tk in tokens:
            self.register_token(v, [labs[tk[r]] for r in "abc"], absorbed=None)

    def cell_ok(self, node, fam, labs, key) -> bool:
        """Admissibility of a whole cell (8.2), mirror pairs inside allowed."""
        try:
            input_names = set(fam.input_labels())
        except AttributeError:
            input_names = {fam.input_label()} - {None}
        forms = [f for nm, f in labs.items() if nm not in input_names]
        try:
            self.check_batch(forms, f"cell {node.vertex} ({key})")
        except Failure:
            return False
        head_name = fam.head_label()
        if head_name and labs[head_name].is_num:
            for r in self.reservation(node, labs[head_name]):
                if r == 0 or r in self.placed:
                    return False
                if any(f.is_num and f.c == r for f in forms):
                    return False
        return True

    def finish_cell(self, node, fam, key, trial, labs, struct, chain_nodes,
                    assign) -> None:
        node.family = fam
        node.family_index = None
        node.params = {p: (str(x) if not x.is_num else int(x.c))
                       for p, x in zip(fam.parameters, trial)}
        node.labels = {nm: (int(f.c) if f.is_num else str(f))
                       for nm, f in labs.items()}
        batch = self.place_cell_forms(node, fam, struct, labs, assign, chain_nodes)
        self.close_batch(batch)
        head_name = fam.head_label()
        if head_name and labs[head_name].is_num:
            for r in self.reservation(node, labs[head_name]):
                self.reserved.add(r)

    def place_cell_forms(self, node, fam, struct, labs, assign,
                         chain_nodes) -> List[LinForm]:
        batch: List[LinForm] = []
        v = node.vertex
        for k, (rs, target) in enumerate(zip(struct, chain_nodes)):
            if k == 0 and node.is_root:
                node.head_value = None
            else:
                chain = [labs[nm] for nm in rs.chain]
                chain = self.extend_chain(chain, target.h_raw,
                                          f"cell {v} row {k}")
                if len(chain) != len(target.head_edges):
                    raise Failure("faithful", f"row {k} chain length mismatch",
                                  vertex=target.vertex)
                for edge, form in zip(target.head_edges, chain):
                    self.commit(edge, form, f"cell {v} row {k} chain")
                target.head_value = chain[0]
                batch += chain
            slots = list(assign) if k == 0 else match_slots(
                [len(a) - 1 for a in rs.arms], [a.reduced for a in target.arms])
            if slots is None:
                raise Failure("faithful", f"row {k} arms do not match",
                              vertex=target.vertex)
            for slot, ai in enumerate(slots):
                arm = target.arms[ai]
                arm.slot = slot
                arm.mothers = (arm.raw_length - arm.reduced) // 6
                vals = self.extend_arm([labs[nm] for nm in rs.arms[slot]],
                                       arm.mothers, f"cell {v} row {k}")
                if len(vals) != len(arm.edges):
                    raise Failure("faithful", f"row {k} arm length mismatch",
                                  vertex=target.vertex)
                arm.values = [int(f.c) if f.is_num else None for f in vals]
                for edge, form in zip(arm.edges, vals):
                    self.commit(edge, form, f"cell {v} row {k} arm")
                batch += vals
            if k > 0:
                want = len(rs.ports)
                if want > len(target.ports) or (len(target.ports) - want) == 1:
                    raise Failure("faithful", f"row {k} port count mismatch",
                                  vertex=target.vertex)
                target.recruited = target.ports[:want]
                target.ordinary = target.ports[want:]
            for edge, nm in zip(target.recruited, rs.ports):
                self.commit(edge, labs[nm], f"cell {v} row {k} port")
                batch.append(labs[nm])
        return batch

    # -- T1: keep the carrier symbolic --------------------------------------
    def emit_symbolic_token(self, node, fam, key, values, free_idx, carrier_idx,
                            tokens, struct, chain_nodes, assign) -> bool:
        v = node.vertex
        names = [f"k{v}_{fam.parameters[i]}" for i in carrier_idx]
        numeric_idx = [i for i in free_idx if i not in carrier_idx]
        snapshot = self.snapshot()

        def build(vals):
            trial = list(values)
            for i, nm in zip(carrier_idx, names):
                trial[i] = LinForm(0, {nm: 1})
            for i, x in zip(numeric_idx, vals):
                trial[i] = LinForm(x)
            labs = self.label_forms(fam, trial)
            nums = [f for nm, f in labs.items() if f.is_num]
            if any(f.c.denominator != 1 for f in nums):
                return None
            try:
                self.check_batch(nums, f"cell {v} ({key}) T1")
            except Failure:
                return None
            return (trial, labs)

        got = self.sample(len(numeric_idx), build) if numeric_idx else build([])
        if got is None:
            return False
        trial, labs = got
        try:
            self.finish_cell(node, fam, key, trial, labs, struct, chain_nodes,
                             assign)
        except Failure:
            self.restore(snapshot)
            return False
        live = set()
        for tk in tokens:
            for r in "abc":
                live |= labs[tk[r]].vars()
        self.live = sorted(live)
        self.max_live = max(self.max_live, len(self.live))
        for tk in tokens:
            self.register_token(v, [labs[tk[r]] for r in "abc"], absorbed=None)
        self.counters["T1_symbolic_tokens"] += 1
        return True

    # -- T2: solve T_v = -T_A and resolve the live parameters ---------------
    def absorb_pending(self, node, fam, key, values, free_idx, carrier_idx,
                       tokens, struct, chain_nodes, assign) -> bool:
        """8c: pair the cell's first token with a pending one; the second (if
        the family has two) becomes pending, so the count never grows."""
        v = node.vertex
        if not self.pending:
            return False
        token_names = tokens[0]
        pend = self.pending[0]
        TA = pend["token"]
        numeric_idx = [i for i in free_idx if i not in carrier_idx]
        K = ["__K1", "__K2"]
        for _ in range(max(30, self.tries // 8)):
            vals = self.box_values(len(numeric_idx), 1) if numeric_idx else []
            if any(x == 0 for x in vals):
                continue
            trial = list(values)
            for i, nm in zip(carrier_idx, K):
                trial[i] = LinForm(0, {nm: 1})
            for i, x in zip(numeric_idx, vals):
                trial[i] = LinForm(x)
            labs = self.label_forms(fam, trial)
            Tv = [labs[token_names[r]] for r in "abc"]
            for perm in itertools.permutations(range(3)):
                sol = self.solve_carrier(Tv, [TA[j] for j in perm], K)
                if sol is None:
                    continue
                subst = {K[0]: sol[0], K[1]: sol[1]}
                final = {nm: f.subst(subst) for nm, f in labs.items()}
                if any(x.vars() & set(K) for x in final.values()):
                    continue
                keep = set()
                for other in self.pending[1:]:
                    for t in other["token"]:
                        keep |= t.vars()
                assignment = self.choose_live(node, fam, key, final, keep)
                if assignment is None:
                    continue
                resolved = {nm: f.subst(assignment) for nm, f in final.items()}
                if any(not f.is_num for f in resolved.values()):
                    continue
                trial2 = [t.subst(subst).subst(assignment) for t in trial]
                snapshot = self.snapshot()
                try:
                    self.apply_live(assignment)
                    self.finish_cell(node, fam, key, trial2, resolved, struct,
                                     chain_nodes, assign)
                except Failure:
                    self.restore(snapshot)
                    continue
                self.register_token(v, [resolved[token_names[r]] for r in "abc"],
                                    absorbed=pend["vertex"])
                for tk in tokens[1:]:
                    self.register_token(
                        v, [resolved[tk[r]] for r in "abc"], absorbed=None)
                self.counters["T2_pairings"] += 1
                return True
        return False

    @staticmethod
    def solve_carrier(Tv: Sequence[LinForm], target: Sequence[LinForm],
                      K: Sequence[str]) -> Optional[Tuple[LinForm, LinForm]]:
        """Solve ``T_v = -T_A`` for the two carrier coordinates (8.3 case T2)."""
        rows = []
        for i in range(2):
            f = Tv[i] + target[i]                    # must vanish
            a = f.t.get(K[0], Q(0))
            b = f.t.get(K[1], Q(0))
            rest = LinForm(f.c, {k: val for k, val in f.t.items() if k not in K})
            rows.append((a, b, rest))
        (a0, b0, r0), (a1, b1, r1) = rows
        det = a0 * b1 - a1 * b0
        if det == 0:
            return None
        k1 = (r1 * b0 - r0 * b1) * Q(1, 1) * (Q(1) / det)
        k2 = (r0 * a1 - r1 * a0) * (Q(1) / det)
        f3 = Tv[2] + target[2]
        check = f3.subst({K[0]: k1, K[1]: k2})
        if check:
            return None
        return k1, k2

    def choose_live(self, node, fam, key, final: Dict[str, LinForm],
                    keep: Optional[set] = None) -> Optional[Dict[str, Q]]:
        """Pick the live parameters to resolve, avoiding every condition.

        ``keep`` names variables that must stay symbolic (the carrier of a
        token that is still pending), so the resolution is partial.
        """
        keep = set(keep or ())
        live = set()
        for f in final.values():
            live |= f.vars()
        for f in self.symbolic.values():
            live |= f.vars()
        live = sorted(live - keep)
        if not live:
            return {}
        self.max_live = max(self.max_live, len(live) + len(keep))
        for stage in range(9):
            for _ in range(max(80, self.tries // 2)):
                assign = {nm: Q(x) for nm, x in
                          zip(live, self.box_values(len(live), stage))}
                if any(x == 0 for x in assign.values()):
                    continue
                bad = False
                for c in self.conditions:
                    cc = c.subst(assign)
                    if cc.is_num and not cc:
                        bad = True
                        break
                if bad:
                    continue
                vals = [f.subst(assign) for f in final.values()]
                if any(f.is_num and f.c.denominator != 1 for f in vals):
                    continue
                edge_vals = [f.subst(assign) for f in self.symbolic.values()]
                if any(f.is_num and f.c.denominator != 1 for f in edge_vals):
                    continue
                allnum = [f.c for f in edge_vals if f.is_num]
                if len(set(allnum)) != len(allnum):
                    continue
                if any(x == 0 for x in allnum):
                    continue
                if any(x in self.placed for x in allnum):
                    continue
                if not self.cell_ok(node, fam,
                                    {nm: f.subst(assign)
                                     for nm, f in final.items()}, key):
                    continue
                return assign
        return None

    def apply_live(self, assign: Mapping) -> None:
        """Substitute the *resolved* live parameters (8c: a partial resolution
        keeps the other pending token's carrier symbolic)."""
        resolved: List[LinForm] = []
        for edge, form in list(self.symbolic.items()):
            value = form.subst(assign)
            self.labels[edge] = value
            if value.is_num:
                del self.symbolic[edge]
                if value.c.denominator != 1:
                    raise Failure("faithful", f"edge {edge} is not an integer")
                self.placed.add(value.c)
                self.max_magnitude = max(self.max_magnitude, abs(int(value.c)))
                resolved.append(value)
            else:
                self.symbolic[edge] = value
        self.pending = [dict(pd, token=[t.subst(assign) for t in pd["token"]])
                        for pd in self.pending]
        conds = []
        for c in self.conditions:
            cc = c.subst(assign)
            if cc.is_num:
                if not cc:
                    raise Failure("faithful", "a forbidden condition became true")
            else:
                conds.append(cc)
        self.conditions = conds
        live = set()
        for f in self.symbolic.values():
            live |= f.vars()
        for pd in self.pending:
            for t in pd["token"]:
                live |= t.vars()
        self.live = sorted(live)
        if resolved:
            self.close_batch(resolved)

    def snapshot(self) -> dict:
        return {"labels": dict(self.labels), "placed": set(self.placed),
                "reserved": set(self.reserved), "open": set(self.open),
                "symbolic": dict(self.symbolic),
                "conditions": list(self.conditions), "live": list(self.live),
                "pending": [dict(pd, token=list(pd["token"]))
                            for pd in self.pending],
                "tokens": [dict(t) for t in self.tokens]}

    def restore(self, snap: dict) -> None:
        self.labels = dict(snap["labels"])
        self.placed = set(snap["placed"])
        self.reserved = set(snap["reserved"])
        self.open = set(snap["open"])
        self.symbolic = dict(snap["symbolic"])
        self.conditions = list(snap["conditions"])
        self.live = list(snap["live"])
        self.pending = [dict(pd, token=list(pd["token"]))
                        for pd in snap["pending"]]
        self.tokens = [dict(t) for t in snap["tokens"]]

    # -- fallbacks (each use is a lemma gap) --------------------------------
    def fallback_cell(self, node: NodePlan,
                      forced_head: Optional["LinForm"]) -> None:
        if not self.allow_fallback:
            raise Failure("lemma_gap", "no catalogue family and fallbacks off",
                          vertex=node.vertex, context=node.key)
        self.counters["fallback_synth_cells"] += 1
        v = node.vertex
        has_input = bool(node.kept)
        xv = self.plan.nodes[node.kept[0]].head_value if has_input else None
        if has_input and (xv is None or not xv.is_num):
            raise Failure("lemma_gap", "fallback with a symbolic input",
                          vertex=v, context=node.key)
        h = 0 if node.is_root else cs.reduce_head(node.h_raw)
        arms = [a.reduced for a in node.arms]
        fams = synth_topology(node.is_root, h, tuple(arms),
                              len(node.recruited), has_input)
        if not fams:
            raise Failure("lemma_gap", "no synthesised family either",
                          vertex=v, context=node.key)
        names, basis = fams[0]
        idx = {nm: i for i, nm in enumerate(names)}
        for a in node.arms:
            a.mothers = (a.raw_length - a.reduced) // 6

        def accept(vals):
            labs_vec = [sum(vals[j] * basis[j][i] for j in range(len(basis)))
                        for i in range(len(names))]
            labs = {nm: LinForm(labs_vec[i]) for i, nm in enumerate(names)}
            if has_input and labs["x"].c != xv.c:
                return None
            forms = [f for nm, f in labs.items() if nm != "x"]
            try:
                self.check_batch(forms, f"fallback cell {v}")
            except Failure:
                return None
            return labs

        if has_input:
            xi = [j for j in range(len(basis)) if basis[j][idx["x"]]]
            if not xi:
                raise Failure("lemma_gap", "fallback cannot pin the input",
                              vertex=v, context=node.key)
        labs = None
        for _ in range(max(200, self.tries)):
            vals = [self.rng.randrange(-40, 41) * self.M for _ in basis]
            if has_input:
                j = xi[0]
                rest = sum(vals[t] * basis[t][idx["x"]]
                           for t in range(len(basis)) if t != j)
                num = xv.c - rest
                if num % basis[j][idx["x"]]:
                    continue
                vals[j] = int(num // basis[j][idx["x"]])
            got = accept(vals)
            if got is not None:
                labs = got
                break
        if labs is None:
            raise Failure("lemma_gap", "no admissible fallback point",
                          vertex=v, context=node.key)
        _nm, rs = cell_label_names(node.is_root, h, arms, len(node.recruited),
                                   has_input)
        node.synth = {"head": h, "arms": arms, "ports": len(node.recruited),
                      "input": has_input, "basis": basis}
        node.labels = {nm: int(f.c) for nm, f in labs.items()}
        batch = self.place_cell_forms(node, None, [rs], labs,
                                      list(range(len(node.arms))), [node])
        self.close_batch(batch)

    # -- finishing (8.3 root, singleton bridge, blocks) ---------------------
    def finalise(self, block_time: float, seed: int) -> dict:
        n = self.n
        if len(self.pending) == 2:
            # 8c: impose T' = -T, two independent equations in the four live
            # carrier parameters; afterwards the support is closed under
            # negation and no ordinary block is needed for the bridge
            if self.pair_pending_at_root():
                self.counters["root_two_token_pairing"] += 1
            else:
                shape = "+".join("sym" if any(t.vars() for t in pd["token"])
                                 else "num" for pd in self.pending)
                self.gaps.append({
                    "vertex": self.plan.root,
                    "context": "|".join(str(self.plan.nodes[pd["vertex"]].key)
                                        for pd in self.pending),
                    "reason": "8c: the two pending tokens could not be paired "
                              f"at the root ({shape})"})
        if self.symbolic:
            assignment = self.choose_live_final()
            if assignment is None:
                raise Failure("faithful",
                              "the live parameters could not be resolved at the root")
            self.apply_live(assignment)
        for edge, form in self.labels.items():
            if not form.is_num or form.c.denominator != 1:
                raise Failure("faithful", f"edge {edge} is not an integer label")
        integers = {e: int(f.c) for e, f in self.labels.items()}
        # every identity used is homogeneous, so dividing out the common
        # factor of the lattice is free and keeps the magnitudes minimal
        g = 0
        for x in integers.values():
            g = math.gcd(g, abs(x))
        if g > 1:
            integers = {e: x // g for e, x in integers.items()}
            self.counters["homogeneous_rescale"] = g
        self.max_magnitude = max([abs(x) for x in integers.values()] or [0])
        reduced = {e: x % n for e, x in integers.items()}
        if 0 in reduced.values():
            bad = [e for e, x in reduced.items() if x == 0]
            raise Failure("modular", f"special labels vanish mod {n}: {bad[:5]}")
        if len(set(reduced.values())) != len(reduced):
            raise Failure("modular",
                          f"special labels collide mod {n} "
                          f"(max magnitude {self.max_magnitude})")

        blocks = []
        for v, node in self.plan.nodes.items():
            ordinary = [e for e in node.ordinary if e not in self.labels]
            if node.retained is not None and not node.is_owner and not node.folded:
                info = node.absorption or {}
                if info.get("type") not in ("helper", "two_port"):
                    raise Failure("lemma_gap",
                                  f"stationary vertex {v} absorbs an active head "
                                  "without a helper or two-port", vertex=v)
            if ordinary:
                blocks.append({"vertex": v, "edges": ordinary, "target": 0})

        bridges = []
        for pd in list(self.pending):
            token = [int(t.c) for t in pd["token"]]
            if len(set(token)) != 3 or any(x == 0 for x in token):
                raise Failure("bridge",
                              f"the pending token {token} is degenerate over Z "
                              "(a rank-one token family was used)")
            negs = [(-t) % n for t in token]
            if len(set(negs)) != 3 or any(x == 0 for x in negs):
                raise Failure("modular",
                              f"the pending token {token} degenerates mod {n}")
            if any(x in set(reduced.values()) for x in negs):
                raise Failure("modular",
                              "the negatives of the pending token are already "
                              f"used mod {n}")
            root_blocks = [b for b in blocks if b["vertex"] == self.plan.root]
            cand = ([b for b in root_blocks if len(b["edges"]) == 3]
                    or [b for b in blocks if len(b["edges"]) == 3]
                    or [b for b in blocks
                        if len(b["edges"]) >= 5 and len(b["edges"]) % 2])
            if not cand:
                raise Failure("bridge",
                              f"no odd ordinary block of size >= 3 for the "
                              f"singleton bridge ({len(self.pending)} pending)")
            blk = cand[0]
            edges = blk["edges"][:3]
            for e, val in zip(edges, negs):
                reduced[e] = val
            blk["edges"] = blk["edges"][3:]
            if not blk["edges"]:
                blocks.remove(blk)
            bridges.append({"vertex": blk["vertex"], "edges": edges,
                            "values": negs})
            self.counters["singleton_bridges"] += 1
        self.pending = []
        bridge = bridges[0] if bridges else None

        assignment = complete_blocks(n, blocks, reduced.values(),
                                     time_limit=block_time, seed=seed % 2147483647)
        if assignment is None:
            raise Failure("blocks", "CP-SAT found no zero-sum block completion "
                          f"(|S|={len(reduced)}, n={n})")
        reduced.update(assignment)
        return {"labels": reduced, "blocks": blocks, "bridge": bridge,
                "bridges": bridges, "integers": integers}

    def pair_pending_at_root(self) -> bool:
        """Impose ``T' = -T`` on the two pending tokens (proof draft 8c)."""
        first, second = self.pending[0], self.pending[1]
        T, Tp = first["token"], second["token"]
        for perm in itertools.permutations(range(3)):
            eqs = [Tp[i] + T[perm[i]] for i in range(2)]
            if not any(eq.vars() for eq in eqs) and any(eq for eq in eqs):
                continue
            assign = self.choose_live_with(eqs, {})
            if assign is None:
                continue
            third = (Tp[2] + T[perm[2]]).subst(assign)
            if third:
                continue
            snapshot = self.snapshot()
            try:
                self.apply_live(assign)
            except Failure:
                self.restore(snapshot)
                continue
            self.tokens.append({"vertex": second["vertex"],
                                "values": [str(t.subst(assign)) for t in Tp],
                                "paired_with": first["vertex"]})
            self.pending = []
            return True
        return False

    def choose_live_final(self) -> Optional[Dict[str, Q]]:
        live = set()
        for f in self.symbolic.values():
            live |= f.vars()
        for pd in self.pending:
            for t in pd["token"]:
                live |= t.vars()
        live = sorted(live)
        if not live:
            return {}
        for stage in range(9):
            for _ in range(max(200, self.tries)):
                assign = {nm: Q(x) for nm, x in
                          zip(live, self.box_values(len(live), stage))}
                if any(x == 0 for x in assign.values()):
                    continue
                if any(not c.subst(assign) for c in self.conditions):
                    continue
                vals = [f.subst(assign) for f in self.symbolic.values()]
                if any(not f.is_num or f.c.denominator != 1 for f in vals):
                    continue
                nums = [f.c for f in vals]
                if any(x == 0 for x in nums) or len(set(nums)) != len(nums):
                    continue
                if any(x in self.placed for x in nums):
                    continue
                bad = False
                for pd in self.pending:
                    if any(not t.subst(assign).is_num for t in pd["token"]):
                        bad = True
                if bad:
                    continue
                return assign
        return None


# ==========================================================================
# 5.  Ordinary blocks (the only solver use)
# ==========================================================================

def collect_blocks(plan: "Plan", realiser: Realiser) -> List[dict]:
    blocks = []
    for v, node in plan.nodes.items():
        ordinary = [e for e in node.ordinary if e not in realiser.labels]
        if ordinary:
            blocks.append({"vertex": v, "edges": ordinary,
                           "target": realiser.block_target(node)})
        elif realiser.block_target(node) % plan.n:
            raise Failure("blocks",
                          f"vertex {v} has an empty ordinary block but needs "
                          f"sum {realiser.block_target(node)}", vertex=v)
    return blocks


def complete_blocks(n: int, blocks: Sequence[dict], used: Iterable[int],
                    time_limit: float = 30.0, workers: int = 4,
                    seed: int = 0) -> Optional[Dict[int, int]]:
    """Split the remaining labels into the prescribed zero-sum blocks."""
    remaining = sorted(set(range(1, n)) - set(int(x) % n for x in used))
    sizes = [len(b["edges"]) for b in blocks]
    if sum(sizes) != len(remaining):
        raise Failure("blocks",
                      f"{len(remaining)} labels remain but the ordinary blocks "
                      f"need {sum(sizes)}")
    if not blocks:
        return {}
    for b in blocks:
        if len(b["edges"]) == 1 and int(b.get("target", 0)) % n == 0:
            raise Failure("blocks", f"vertex {b['vertex']} has an ordinary "
                          "block of size one with target zero")
    try:
        from ortools.sat.python import cp_model
    except Exception as exc:                       # pragma: no cover
        raise Failure("blocks", f"CP-SAT is unavailable: {exc}")
    model = cp_model.CpModel()
    nb = len(blocks)
    x = {}
    for i, val in enumerate(remaining):
        for b in range(nb):
            x[(i, b)] = model.NewBoolVar(f"x{i}_{b}")
        model.AddExactlyOne(x[(i, b)] for b in range(nb))
    for b, block in enumerate(blocks):
        size = len(block["edges"])
        model.Add(sum(x[(i, b)] for i in range(len(remaining))) == size)
        k = model.NewIntVar(0, size, f"k{b}")
        target = int(block.get("target", 0)) % n
        model.Add(sum(remaining[i] * x[(i, b)] for i in range(len(remaining)))
                  == n * k + target)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    solver.parameters.num_search_workers = workers
    solver.parameters.random_seed = seed
    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None
    out: Dict[int, int] = {}
    for b, block in enumerate(blocks):
        chosen = [remaining[i] for i in range(len(remaining))
                  if solver.Value(x[(i, b)])]
        for edge, value in zip(block["edges"], chosen):
            out[edge] = value
    return out


# ==========================================================================
# 6.  Paths (Lemma A boundary case)
# ==========================================================================

def label_path(n: int, parent: Sequence[int], rng: random.Random,
               tries: int = 200000) -> Optional[Dict[int, int]]:
    """Edge-graceful labelling of a path, by solver-free backtracking."""
    order = []
    deg = degrees(parent)
    adj = adjacency(parent)
    start = next((v for v in range(n) if deg[v] == 1), 0)
    prev = -1
    cur = start
    while True:
        order.append(cur)
        nxt = [w for w in adj[cur] if w != prev]
        if not nxt:
            break
        prev, cur = cur, nxt[0]
    if len(order) != n:
        return None
    # labels a_1..a_{n-1}; sums a_1, a_1+a_2, ..., a_{n-2}+a_{n-1}, a_{n-1}
    best: List[Optional[List[int]]] = [None]
    counter = [0]

    def rec(i: int, labels: List[int], used_lab: set, used_sum: set) -> bool:
        counter[0] += 1
        if counter[0] > tries:
            return False
        if i == n - 1:
            s = labels[-1] % n
            if s in used_sum:
                return False
            best[0] = list(labels)
            return True
        cands = [a for a in range(1, n) if a not in used_lab]
        rng.shuffle(cands)
        for a in cands:
            s = (a if i == 0 else labels[-1] + a) % n
            if s in used_sum:
                continue
            labels.append(a)
            used_lab.add(a)
            used_sum.add(s)
            if rec(i + 1, labels, used_lab, used_sum):
                return True
            labels.pop()
            used_lab.discard(a)
            used_sum.discard(s)
        return False

    if not rec(0, [], set(), set()):
        return None
    labels = best[0]
    assert labels is not None
    out: Dict[int, int] = {}
    for i in range(n - 1):
        u, w = order[i], order[i + 1]
        child = u if parent[u] == w else w
        out[child] = labels[i]
    return out


# ==========================================================================
# 7.  Driver
# ==========================================================================

class LazyCatalogue:
    """``data/alphabet_families.json`` with per-context lazy ``Family`` building.

    The assembled catalogue is over a hundred megabytes and holds thousands of
    menus; building every :class:`free_token_lib.Family` eagerly costs far more
    than a whole test suite.  This wrapper parses the JSON once and constructs
    the menu of a context the first time it is asked for.
    """

    def __init__(self, path: str = DEFAULT_CATALOGUE) -> None:
        with open(path) as fh:
            self.raw = json.load(fh)
        self.cache: Dict[str, List[ftl.Family]] = {}
        self.errors: List[Tuple[str, int, str]] = []

    def __contains__(self, key: str) -> bool:
        return key in self.raw

    def keys(self):
        return self.raw.keys()

    def get(self, key: str, default=None):
        if key in self.cache:
            return self.cache[key]
        entry = self.raw.get(key)
        if not isinstance(entry, dict):
            return default
        items = entry.get("menu")
        if not isinstance(items, list) or not items:
            items = [entry]
        menu: List[ftl.Family] = []
        for pos, item in enumerate(items):
            merged = dict(item)
            merged.setdefault("ctx", entry.get("ctx"))
            merged.setdefault("kind", entry.get("kind"))
            try:
                menu.append(ftl.Family(merged, key=key))
            except ftl.Malformed as exc:
                self.errors.append((key, pos, str(exc)))
        self.cache[key] = menu
        return menu if menu else default

    def __getitem__(self, key: str):
        out = self.get(key)
        if out is None:
            raise KeyError(key)
        return out


UNITS_PATH = os.path.join(DATA, "batches", "alphabet_units.jsonl")
_UNIT_FAMILIES: Optional[Dict[str, ftl.Family]] = None


def unit_families(path: str = UNITS_PATH) -> Dict[str, ftl.Family]:
    """The owner-free neutral-unit families of ``data/batches/alphabet_units.jsonl``.

    Root-row families with ``root_zero_output`` (the owner output is
    identically zero, i.e. the unit's head sum vanishes) and two internal
    parameters, one per same-parity pair ``(1,1) ... (6,6)`` and for both
    four-short units; proof draft section 8.5(2).
    """
    global _UNIT_FAMILIES
    if _UNIT_FAMILIES is None:
        out: Dict[str, ftl.Family] = {}
        try:
            with open(path) as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    row = json.loads(line)
                    key = row.get("key")
                    payload = row.get("family") if "family" in row else row
                    try:
                        out[key] = ftl.Family(payload, key=key)
                    except Exception:
                        continue
        except OSError:
            out = {}
        _UNIT_FAMILIES = out
    return _UNIT_FAMILIES


_CATALOGUE_CACHE: Dict[str, LazyCatalogue] = {}


def load_catalogue(path: str = DEFAULT_CATALOGUE) -> LazyCatalogue:
    if path not in _CATALOGUE_CACHE:
        _CATALOGUE_CACHE[path] = LazyCatalogue(path)
    return _CATALOGUE_CACHE[path]


def construct(parent_in: Sequence[int], catalogue=None, seed: int = 0,
              tries: int = 800, block_time: float = 30.0,
              root_candidates: int = 4, pair_tokens: bool = True,
              cross_check: bool = True, faithful: bool = False) -> dict:
    """Build an edge-graceful labelling with a certificate, or a failure report."""
    n, parent, children, root0 = normalise_parent(parent_in)
    if n % 2 == 0:
        return {"ok": False, "n": n,
                "failure": {"step": "input", "detail": "the order must be odd",
                            "vertex": None, "context": None}}
    catalogue = catalogue if catalogue is not None else load_catalogue()
    rng = random.Random(seed)

    if is_path(parent):
        labels = label_path(n, parent, rng)
        if labels is None:
            return {"ok": False, "n": n, "route": "path",
                    "failure": {"step": "path", "detail": "no path labelling found",
                                "vertex": None, "context": None}}
        report = ftl.verify_edge_graceful(parent, labels)
        return {"ok": bool(report["ok"]), "n": n, "route": "path",
                "parent": list(parent), "root": root0,
                "labels": {str(k): v for k, v in sorted(labels.items())},
                "vertices": [], "ordinary_blocks": [], "tokens": [],
                "special_support": [], "notes": ["path route"],
                "verification": {"ok": report["ok"], "errors": report["errors"]}}

    attempts = []
    for ri, root in enumerate(choose_root_candidates(parent)[:root_candidates]):
        rooted = reroot(parent, root)
        _n, par, ch, rt = normalise_parent(rooted)
        for restart in range(2):
            rng = random.Random(seed * 1000 + ri * 10 + restart)
            try:
                if faithful:
                    cert = _construct_rooted_faithful(
                        _n, par, ch, rt, catalogue, rng, tries, block_time,
                        seed=seed * 1000 + ri * 10 + restart)
                else:
                    cert = _construct_rooted(_n, par, ch, rt, catalogue, rng,
                                             tries, block_time, pair_tokens,
                                             cross_check,
                                             seed=seed * 1000 + ri * 10 + restart)
            except Failure as exc:
                attempts.append({"root": root, "restart": restart,
                                 "failure": exc.report})
                continue
            if cert.get("ok"):
                cert["attempts"] = attempts
                return cert
            attempts.append({"root": root, "restart": restart,
                             "failure": cert.get("failure")})
    return {"ok": False, "n": n, "route": "cells", "parent": list(parent),
            "failure": (attempts[0]["failure"] if attempts else
                        {"step": "root", "detail": "no branch vertex",
                         "vertex": None, "context": None}),
            "attempts": attempts}


def _construct_rooted(n: int, parent: List[int], children: List[List[int]],
                      root: int, catalogue, rng: random.Random, tries: int,
                      block_time: float, pair_tokens: bool,
                      cross_check: bool, seed: int) -> dict:
    # context_scheduler.schedule() always roots at vertex 0, so relabel
    old_of, new_of = relabel_to_root(parent, root)
    sched_parent = [-1] * n
    for v in range(n):
        if parent[v] != -1:
            sched_parent[new_of[v]] = new_of[parent[v]]
    sched_parent[0] = 0                       # schedule() ignores parent[0]
    sched = cs.schedule(sched_parent)
    if sched.get("is_path"):
        raise Failure("path", "the scheduler reports a path")
    # translate the schedule back to the original vertex numbering
    sched = translate_schedule(sched, old_of)
    plan = Plan(n, parent, children, root, sched)
    notes: List[str] = list(plan.notes)
    if cross_check:
        problems = plan.cross_check()
        if problems:
            notes.append("scheduler: " + "; ".join(problems[:4]))

    real = Realiser(plan, catalogue, rng, tries=tries, pair_tokens=pair_tokens)
    real.run()
    notes.extend(real.notes)

    blocks = collect_blocks(plan, real)
    assignment = complete_blocks(n, blocks, real.used.keys(),
                                 time_limit=block_time, seed=seed % 2147483647)
    if assignment is None:
        raise Failure("blocks", "CP-SAT found no zero-sum block completion "
                      f"(|S|={len(set(real.special))}, n={n}, "
                      f"{len(blocks)} blocks of sizes "
                      f"{sorted(len(b['edges']) for b in blocks)}, "
                      f"{sum(1 for b in blocks if b.get('target'))} with a "
                      "nonzero target)",
                      vertex=None, context=None,
                      block_sizes=[len(b["edges"]) for b in blocks],
                      special=len(set(real.special)),
                      remaining=len(set(range(1, n)) - set(real.used)))
    for edge, value in assignment.items():
        real.place(edge, value, "ordinary block")

    missing = [v for v in range(n) if v != root and v not in real.labels]
    if missing:
        raise Failure("coverage", f"{len(missing)} edges were never labelled: "
                      f"{missing[:8]}")

    report = ftl.verify_edge_graceful(parent, real.labels)
    cert = build_certificate(n, parent, root, plan, real, blocks, assignment,
                             notes, report)
    if not report["ok"]:
        cert["failure"] = {"step": "verify", "detail": "; ".join(report["errors"]),
                           "vertex": None, "context": None}
    return cert


def _construct_rooted_faithful(n: int, parent: List[int], children: List[List[int]],
                               root: int, catalogue, rng: random.Random,
                               tries: int, block_time: float, seed: int,
                               allow_fallback: bool = True) -> dict:
    """One rooted attempt in ``--faithful`` mode (proof draft section 8)."""
    old_of, new_of = relabel_to_root(parent, root)
    sched_parent = [-1] * n
    for v in range(n):
        if parent[v] != -1:
            sched_parent[new_of[v]] = new_of[parent[v]]
    sched_parent[0] = 0
    sched = cs.schedule(sched_parent)
    if sched.get("is_path"):
        raise Failure("path", "the scheduler reports a path")
    sched = translate_schedule(sched, old_of)
    plan = Plan(n, parent, children, root, sched)
    real = FaithfulRealiser(plan, catalogue, rng, tries=tries,
                            allow_fallback=allow_fallback)
    real.run()
    out = real.finalise(block_time, seed)
    missing = [v for v in range(n) if v != root and v not in out["labels"]]
    if missing:
        raise Failure("coverage", f"{len(missing)} edges never labelled: "
                      f"{missing[:8]}")
    report = ftl.verify_edge_graceful(parent, out["labels"])
    D = degree_two_count(parent)
    stats = {
        "owners": sum(1 for x in plan.nodes.values() if x.is_owner),
        "catalogue_cells": len(real.choice),
        "lemma_gaps": len(real.gaps),
        "fallback_cells": real.counters.get("fallback_synth_cells", 0),
        "T1_symbolic_tokens": real.counters.get("T1_symbolic_tokens", 0),
        "T2_pairings": real.counters.get("T2_pairings", 0),
        "T1_downgraded": real.counters.get("T1_downgraded_to_numeric", 0),
        "T2_solve_failed": real.counters.get("T2_solve_failed", 0),
        "max_live_parameters": real.max_live,
        "max_symbolic_labels": real.max_symbolic,
        "special_labels": len(real.labels),
        "max_magnitude": real.max_magnitude,
        "degree_two": D,
        "magnitude_over_D1": (float(Q(real.max_magnitude, max(1, D + 1)))
                              if real.max_magnitude else 0.0),
        "lattice_M": real.M,
        "mirror_open_at_end": len(real.open),
        "max_pending_tokens": real.max_pending,
        "root_two_token_pairings": real.counters.get("root_two_token_pairing", 0),
        "two_token_cells": real.counters.get("two_token_cells", 0),
        "carrier_rank_below_two": real.counters.get("carrier_rank_below_two", 0),
        "forced_antipode_families": real.counters.get("forced_antipode_family_used", 0),
        "family_second_choice": real.counters.get("family_second_choice", 0),
        "subtree_retries": real.counters.get("subtree_retries", 0),
        "rigid_head_cells": real.counters.get("rigid_head_cells", 0),
        "fa_case_a_port_block": real.counters.get("fa_case_a", 0),
        "fa_case_b_input_in_token": real.counters.get("fa_case_b", 0),
        "fa_case_c_joint": real.counters.get("fa_case_c", 0),
        "singleton_bridge": len(out.get("bridges") or []),
        "residue2_owners": sum(
            1 for x in plan.nodes.values()
            if (safe_context_key(x.key) or {}).get("arms", []).count(2)),
    }
    cert = {
        "ok": bool(report["ok"]),
        "mode": "faithful",
        "statistics": stats,
        "n": n,
        "parent": list(parent),
        "root": root,
        "route": "cells",
        "labels": {str(k): v for k, v in sorted(out["labels"].items())},
        "integer_labels": {str(k): v for k, v in sorted(out["integers"].items())},
        "special_support": sorted(set(out["integers"].values())),
        "ordinary_blocks": [{"vertex": b["vertex"], "edges": b["edges"],
                             "target": 0,
                             "values": [out["labels"].get(e) for e in b["edges"]]}
                            for b in out["blocks"]],
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


def build_certificate(n: int, parent: Sequence[int], root: int, plan: "Plan",
                      real: Realiser, blocks: Sequence[dict],
                      assignment: Dict[int, int], notes: Sequence[str],
                      report: dict) -> dict:
    vertices = []
    for v in sorted(plan.nodes):
        node = plan.nodes[v]
        rec: Dict[str, Any] = {
            "vertex": v,
            "role": ("folded" if node.folded else
                     "owner" if node.is_owner else "stationary"),
            "context": node.key,
            "context_spec": safe_context_key(node.key),
            "passthrough": node.passthrough,
        }
        if node.family is not None:
            rec["family"] = {
                "source": "catalogue",
                "menu_index": node.family_index,
                "denominator": node.family.L,
                "parameters": node.params,
                "labels": node.labels,
                "provenance": node.family.meta.get("provenance"),
            }
        elif node.synth is not None:
            rec["family"] = {
                "source": "synthesised",
                "menu_index": None,
                "denominator": 1,
                "topology": {k: node.synth[k] for k in
                             ("head", "arms", "ports", "input", "joint_child",
                              "group_of", "spec", "rows")
                             if k in node.synth},
                "basis": node.synth.get("basis"),
                "labels": node.labels,
                "provenance": "free_token_constructor.synth_topology",
            }
        else:
            rec["family"] = None
        if node.head_edges:
            vals = [real.labels.get(e) for e in node.head_edges]
            rec["head_chain"] = {
                "raw": node.h_raw,
                "reduced": cs.reduce_head(node.h_raw),
                "edges": node.head_edges, "values": vals,
            }
        rec["arms"] = [{"slot": a.slot, "core_child": a.core_child,
                        "raw_length": a.raw_length, "reduced": a.reduced,
                        "mothers": a.mothers, "edges": a.edges,
                        "values": a.values} for a in node.arms]
        rec["ports"] = {"recruited": node.recruited, "ordinary": node.ordinary}
        rec["active"] = {"child_type": node.child_type,
                         "cancelled_groups": node.cancelled,
                         "retained": node.retained,
                         "folded": (node.retained if node.folded else None)}
        rec["neutral_units"] = [
            {"kind": u.kind, "scale": u.scale, "base": u.base,
             "source": u.source,
             "arms": [{"core_child": a.core_child, "raw_length": a.raw_length,
                       "reduced": a.reduced, "mothers": a.mothers,
                       "edges": a.edges, "values": a.values} for a in u.arms]}
            for u in node.units]
        rec["absorption"] = node.absorption
        rec["token"] = node.token
        vertices.append(rec)
    stats = {
        "owners": sum(1 for x in plan.nodes.values() if x.is_owner),
        "synthesised_cells": sum(1 for x in plan.nodes.values()
                                 if x.synth is not None),
        "catalogue_cells": sum(1 for x in plan.nodes.values()
                               if x.family is not None),
        "neutral_units": sum(len(x.units) for x in plan.nodes.values()),
        "residue2_rigid_rows": real.residue2,
        "residue2_owners": sum(
            1 for x in plan.nodes.values()
            if (safe_context_key(x.key) or {}).get("arms", []).count(2)),
        "residue2_act_owners": sum(
            1 for x in plan.nodes.values()
            if (safe_context_key(x.key) or {}).get("arms") == [2]
            and (safe_context_key(x.key) or {}).get("ports") == 0
            and (safe_context_key(x.key) or {}).get("tag") in ("act", "L1", "L11")),
        "whole_parent_joints": real.joints_used,
        "cancelled_group_macros": real.groups_used,
        "subtree_retries": real.retries,
        "special_labels": len(set(real.special)),
    }
    return {
        "ok": bool(report["ok"]),
        "statistics": stats,
        "n": n,
        "parent": list(parent),
        "root": root,
        "route": "cells",
        "labels": {str(k): v for k, v in sorted(real.labels.items())},
        "special_support": sorted(set(real.special)),
        "ordinary_blocks": [{"vertex": b["vertex"], "edges": b["edges"],
                             "target": b.get("target", 0),
                             "values": [assignment.get(e) for e in b["edges"]]}
                            for b in blocks],
        "vertices": vertices,
        "tokens": real.tokens,
        "notes": list(notes),
        "verification": {"ok": report["ok"], "errors": report["errors"]},
    }


# ==========================================================================
# 8.  Test programme
# ==========================================================================

def self_test(n: int = 101) -> dict:
    """Re-derive every local identity used by the constructor in ``Z_n``."""
    out: Dict[str, Any] = {"n": n}
    rng = random.Random(7)

    # six-edge mother: three inverse pairs added to P and to O
    ok = True
    for _ in range(200):
        a, t = rng.randrange(1, n), rng.randrange(1, n)
        block6 = mother_extension_mod(a, t, n)
        arm = [a] + block6
        sums = [(arm[i] + arm[i + 1]) % n for i in range(len(arm) - 1)] + [arm[-1]]
        if Counter(sums) != Counter(block6 + [a]):
            ok = False
            break
    out["mother_identity"] = ok

    # rigid six-label and flexible twelve-label endpoint-preserving insertions
    six_ok, twelve_ok, mirror_ok = True, True, True
    for _ in range(200):
        left, right = rng.randrange(1, n), rng.randrange(1, n)
        for form in SIX_INSERTIONS:
            blk = _apply_form(form, left, right, n)
            if blk is None:
                continue
            if not check_insertion(left, right, blk, n):
                six_ok = False
        blk0 = _apply_form(SIX_INSERTIONS[0], left, right, n)
        if blk0 is not None and Counter(blk0) != Counter((-x) % n for x in blk0):
            mirror_ok = False
        t = rng.randrange(1, n)
        if not check_insertion(left, right, twelve_insertion_mod(left, right, t, n), n):
            twelve_ok = False
    out["six_insertion_identity"] = six_ok
    out["six_insertion_0_is_mirror_closed"] = mirror_ok
    out["twelve_insertion_identity"] = twelve_ok

    # synthesised cells satisfy P' = O identically
    cells_ok = True
    checked = 0
    for sig in [(False, 0, (1,), 1, False), (False, 0, (1,), 0, True),
                (True, 0, (1,), 2, False), (True, 0, (2,), 1, False),
                (False, 0, (2,), 0, True), (False, 1, (1, 2), 1, False),
                (True, 0, (1,), 0, False), (False, 0, (1, 1), 1, False)]:
        names, rs = cell_label_names(sig[0], sig[1], sig[2], sig[3], sig[4])
        outs, phys = cell_output_forms(names, rs, has_zero=sig[0])
        for _nm, basis in synth_topology(*sig):
            checked += 1
            for _ in range(20):
                c = [rng.randrange(1, n) for _ in basis]
                vals = [sum(c[j] * basis[j][i] for j in range(len(basis))) % n
                        for i in range(len(names))]
                po = Counter(sum(int(f[i]) * vals[i] for i in range(len(names))) % n
                             for f in phys)
                oo = Counter(sum(int(f[i]) * vals[i] for i in range(len(names))) % n
                             for f in outs)
                if po != oo:
                    cells_ok = False
    out["synthesised_cells_P_eq_O"] = cells_ok
    out["synthesised_cells_checked"] = checked

    # synthesised neutral units: head sum zero and outputs permute labels
    units_ok = True
    for lengths in [(1, 1), (2, 2), (1, 3), (3, 3), (2, 4), (1, 5)]:
        for names, basis in synth_unit(lengths):
            pos = 0
            for _ in range(20):
                c = [rng.randrange(1, n) for _ in basis]
                vals = [sum(c[j] * basis[j][i] for j in range(len(basis))) % n
                        for i in range(len(names))]
                rows, pos = [], 0
                for ell in lengths:
                    rows.append(vals[pos:pos + ell + 1])
                    pos += ell + 1
                if sum(r[0] for r in rows) % n:
                    units_ok = False
                sums = []
                for r in rows:
                    sums += [(r[i] + r[i + 1]) % n for i in range(len(r) - 1)]
                    sums.append(r[-1])
                if Counter(sums) != Counter(vals):
                    units_ok = False
    out["synthesised_units_ok"] = units_ok

    # catalogue pair bases and the four-layer residue-two joint
    if HAVE_UNIT_BASES:
        base_ok = True
        for a, b in [(1, 1), (3, 3), (5, 5), (5, 7), (2, 2), (4, 4), (2, 6),
                     (1, 9), (7, 9)]:
            try:
                rows = pair_bases.catalog_pair_rows(a, b)
            except Exception:
                base_ok = False
                continue
            labels = [x for r in rows for x in r]
            sums = []
            for r in rows:
                sums += [r[i] + r[i + 1] for i in range(len(r) - 1)]
                sums.append(r[-1])
            if Counter(sums) != Counter(labels) or rows[0][0] + rows[1][0] != 0:
                base_ok = False
        out["catalogue_pair_bases_ok"] = base_ok
    fam = four_layer_family()
    out["four_layer_r2222_verified"] = fam is not None
    out["residue2_rigid_row_ok"] = _residue2_rigid_ok(n)
    out["ok"] = all(v for k, v in out.items()
                    if isinstance(v, bool))
    return out


def _residue2_rigid_ok(n: int) -> bool:
    """``(-3x/2; -x/2, -x, x/2; x)`` satisfies ``P = O`` for the residue-2 letter."""
    names, rs = cell_label_names(False, 0, (2,), 0, True)
    if names != RESIDUE2_RIGID_NAMES:
        return False
    outs, phys = cell_output_forms(names, rs, has_zero=False)
    for t in range(1, min(n, 40)):
        vals = [x * t % n for x in RESIDUE2_RIGID_BASIS[0]]
        po = Counter(sum(int(f[i]) * vals[i] for i in range(len(names))) % n
                     for f in phys)
        oo = Counter(sum(int(f[i]) * vals[i] for i in range(len(names))) % n
                     for f in outs)
        if po != oo:
            return False
    return True


def failure_signature(cert: dict) -> str:
    f = cert.get("failure") or {}
    if not f and cert.get("attempts"):
        f = cert["attempts"][0].get("failure") or {}
    step = f.get("step", "?")
    ctx = f.get("context")
    return f"{step}" + (f" [{ctx}]" if ctx else "")


def run_suite(name: str, trees: Iterable[Tuple[str, Sequence[int]]],
              catalogue, seed: int, tries: int, block_time: float,
              verbose: bool = False, limit: Optional[int] = None,
              faithful: bool = False) -> dict:
    ok = 0
    total = 0
    stats: Counter = Counter()
    gaps: Counter = Counter()
    fails: Counter = Counter()
    detail: List[dict] = []
    t0 = time.time()
    for label, par in trees:
        if limit is not None and total >= limit:
            break
        total += 1
        stats["degree_two_total"] += degree_two_count(par)
        try:
            cert = construct(par, catalogue=catalogue, seed=seed, tries=tries,
                             block_time=block_time, faithful=faithful)
        except Failure as exc:
            cert = {"ok": False, "failure": exc.report}
        except Exception as exc:                    # pragma: no cover
            cert = {"ok": False, "failure": {"step": "exception",
                                             "detail": repr(exc),
                                             "vertex": None, "context": None}}
        if cert.get("ok"):
            ok += 1
            st = cert.get("statistics") or {}
            MAXKEYS = ("max_live_parameters", "max_symbolic_labels",
                       "max_magnitude", "magnitude_over_D1", "lattice_M",
                       "max_pending_tokens")
            for k, val in st.items():
                if k in MAXKEYS:
                    continue
                stats[k] += val
            for k in MAXKEYS:
                if k in st:
                    stats[k] = max(stats.get(k, 0), int(st[k]))
            if st.get("synthesised_cells"):
                stats["trees_with_synthesis"] += 1
            if st.get("residue2_rigid_rows"):
                stats["trees_with_residue2_rigid"] += 1
            if st.get("residue2_owners"):
                stats["trees_with_residue2_context"] += 1
            for g in cert.get("lemma_gaps") or []:
                gaps[(g.get("context"), g.get("reason"))] += 1
        else:
            sig = failure_signature(cert)
            fails[sig] += 1
            if len(detail) < 40:
                f = cert.get("failure") or (
                    cert.get("attempts", [{}])[0].get("failure") or {})
                detail.append({"tree": label, "n": len(par),
                               "degree_two": degree_two_count(par),
                               "labels_used": f.get("labels_used"),
                               "step": f.get("step"), "context": f.get("context"),
                               "vertex": f.get("vertex"),
                               "detail": (f.get("detail") or "")[:200]})
            if verbose:
                print(f"  FAIL {label}: {failure_signature(cert)}")
    return {"suite": name, "trees": total, "ok": ok, "failed": total - ok,
            "seconds": round(time.time() - t0, 1),
            "statistics": dict(stats),
            "lemma_gaps": [{"context": c, "reason": rsn, "count": cnt}
                           for (c, rsn), cnt in gaps.most_common()],
            "failure_signatures": dict(fails.most_common()),
            "examples": detail}


def census_trees(orders: Sequence[int]) -> Iterable[Tuple[str, List[int]]]:
    for n in orders:
        for i, par in enumerate(all_free_trees(n)):
            yield (f"free_n{n}_{i}", par)


def random_trees(orders: Sequence[int], count: int, seed: int) -> Iterable[Tuple[str, List[int]]]:
    for n in orders:
        rng = random.Random(seed * 7919 + n)
        for i in range(count):
            yield (f"rand_n{n}_{i}", random_tree(n, rng))


def sparse_tree(n: int, core: int, rng: random.Random,
                keep: Optional[int] = None) -> List[int]:
    """A tree of order ``n`` with a controlled number of degree-two vertices.

    A random tree on ``core`` vertices; a leaf is attached to all but ``keep``
    of its degree-two vertices (raising them to degree three), and the rest of
    the order is padded with leaves at random branch vertices.  This puts the
    instance inside the sparse regime ``n > C(D+1)`` of the theorem, which is
    where the free-token construction is supposed to work.
    """
    par = list(random_tree(core, rng))
    if keep is None:
        keep = max(1, n // 25)

    def deg_list(pa):
        d = [0] * len(pa)
        for v in range(len(pa)):
            if pa[v] != -1:
                d[v] += 1
                d[pa[v]] += 1
        return d

    deg = deg_list(par)
    twos = [v for v in range(len(par)) if deg[v] == 2]
    rng.shuffle(twos)
    for v in twos[keep:]:
        if len(par) >= n:
            break
        par.append(v)
    deg = deg_list(par)
    branch = [v for v in range(len(par)) if deg[v] >= 3] or [0]
    while len(par) < n:
        par.append(rng.choice(branch))
    return par[:n]


def sparse_trees(orders: Sequence[int], count: int, seed: int,
                 keep_div: int = 25) -> Iterable[Tuple[str, List[int]]]:
    """Sparse instances with ``D`` about ``n / keep_div``."""
    for n in orders:
        rng = random.Random(seed * 104729 + n + 7 * keep_div)
        core = max(5, n // 8)
        for i in range(count):
            yield (f"sparse_n{n}_d{keep_div}_{i}",
                   sparse_tree(n, core, rng, keep=max(1, n // keep_div)))


def degree_two_count(parent: Sequence[int]) -> int:
    return sum(1 for d in degrees(parent) if d == 2)


def stress_trees() -> List[Tuple[str, List[int]]]:
    try:
        import stress_module_family_cpsat as stress
    except Exception as exc:                        # pragma: no cover
        print(f"stress module unavailable: {exc}", file=sys.stderr)
        return []
    out = []
    for m in (2, 3):
        for arm in (4,):
            for leaves in (1, 3, 5):
                for bulk in (0, 3, 7):
                    par, role = stress.build_tree(m, "t222", arm, leaves, bulk,
                                                  extra_ports=0, hang=1)
                    if len(par) % 2 == 0:
                        continue
                    out.append((f"stress_m{m}_arm{arm}_l{leaves}_b{bulk}",
                                par))
    return out


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--parent", help="comma separated parent array (root = -1)")
    ap.add_argument("--census", help="comma separated orders for the free-tree census")
    ap.add_argument("--random", help="comma separated orders for random trees")
    ap.add_argument("--count", type=int, default=200)
    ap.add_argument("--sparse", help="comma separated orders for sparse trees")
    ap.add_argument("--sparse-density", default="25",
                    help="comma separated divisors k with D approx n/k")
    ap.add_argument("--stress", action="store_true")
    ap.add_argument("--all", action="store_true", help="the full test programme")
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--seed", type=int, default=20260901)
    ap.add_argument("--tries", type=int, default=800)
    ap.add_argument("--block-time", type=float, default=20.0)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--roots", type=int, default=4,
                    help="how many branch vertices to try as the root")
    ap.add_argument("--json", default=None)
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--faithful", action="store_true",
                    help="run proof draft section 8 literally")
    a = ap.parse_args(argv)

    if a.selftest:
        rep = self_test()
        print(json.dumps(rep, indent=1))
        return 0 if rep["ok"] else 1

    catalogue = load_catalogue()
    results = []

    if a.parent:
        par = [int(x) for x in a.parent.split(",")]
        cert = construct(par, catalogue=catalogue, seed=a.seed, tries=a.tries,
                         block_time=a.block_time)
        print(json.dumps(cert, indent=1)[:20000])
        return 0 if cert.get("ok") else 1

    if a.demo:
        par = [-1, 0, 0, 0, 1, 1, 2, 2, 3]
        cert = construct(par, catalogue=catalogue, seed=a.seed)
        print(json.dumps({k: cert[k] for k in ("ok", "n", "route", "labels",
                                               "verification", "notes")
                          if k in cert}, indent=1))
        return 0 if cert.get("ok") else 1

    if a.census or a.all:
        orders = ([int(x) for x in a.census.split(",")] if a.census
                  else [7, 9, 11, 13])
        results.append(run_suite(f"free-tree census {orders}",
                                 census_trees(orders), catalogue, a.seed,
                                 a.tries, a.block_time, a.verbose,
                                 a.limit, a.faithful))
    if a.random or a.all:
        orders = ([int(x) for x in a.random.split(",")] if a.random
                  else [21, 31, 51])
        results.append(run_suite(f"random trees {orders} x{a.count}",
                                 random_trees(orders, a.count, a.seed),
                                 catalogue, a.seed, a.tries, a.block_time,
                                 a.verbose, a.limit, a.faithful))
    if a.sparse or a.all:
        orders = ([int(x) for x in a.sparse.split(",")] if a.sparse
                  else [51, 101, 201])
        for kd in [int(x) for x in a.sparse_density.split(",")]:
            results.append(run_suite(
                f"sparse trees {orders} x{a.count} (D~n/{kd})",
                sparse_trees(orders, a.count, a.seed, kd),
                catalogue, a.seed, a.tries, a.block_time, a.verbose,
                a.limit, a.faithful))
    if a.stress or a.all:
        results.append(run_suite("rigid-module stress family", stress_trees(),
                                 catalogue, a.seed, a.tries, a.block_time,
                                 a.verbose, a.limit, a.faithful))

    if not results:
        ap.print_help()
        return 2
    for r in results:
        print(f"\n=== {r['suite']} ===")
        print(f"  trees {r['trees']}  ok {r['ok']}  failed {r['failed']}  "
              f"({r['seconds']}s)")
        st = r.get("statistics") or {}
        if st:
            print("    totals over the successful trees: "
                  + ", ".join(f"{k}={v}" for k, v in sorted(st.items())))
        for g in (r.get("lemma_gaps") or []):
            print(f"    lemma gap x{g['count']}: {g['context']} -- {g['reason']}")
        for sig, cnt in r["failure_signatures"].items():
            print(f"    {cnt:5d}  {sig}")
        for ex in r["examples"][:10]:
            print(f"      e.g. {ex['tree']} n={ex['n']} D={ex.get('degree_two')} "
                  f"used={ex.get('labels_used')} step={ex['step']} "
                  f"ctx={ex['context']} v={ex['vertex']}: {ex['detail']}")
    if a.json:
        with open(a.json, "w") as fh:
            json.dump(results, fh, indent=1)
        print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
