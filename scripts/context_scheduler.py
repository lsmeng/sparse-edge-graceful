#!/usr/bin/env python3
"""Abstract context scheduler for the free-token architecture.

For a given tree this assigns to every CORE OWNER vertex its local context
(cell type) in the finite alphabet of
`SPARSE_FLAGSHIP_FREE_TOKEN_PROOF_DRAFT_20260901.md` Sections 3-4 (Lemma B,
Lemma C).  No numeric labels are produced: the scheduler only performs the
combinatorial case analysis (core decomposition, owner-free neutralization,
active-child cancellation, port absorption/owner decision, and the short-
singleton repairs) and reports the resulting context KEYS, in the exact
string format produced by `key()` in `run_alphabet_batch.py`:

    f"h{head}_{'-'.join(arms) or 'none'}_p{ports}_{tag}"   (nonroot)
    f"root_{'-'.join(arms) or 'none'}_p{ports}_{tag}"      (root)

with tag in {bot, act, L1} (child in {none, free, L1} respectively).

References implemented here:
  * Lemma B (core decomposition, owners) -- proof draft Section 3.
  * Lemma C (context alphabet, full case analysis) -- proof draft Section 4.
  * Owner-free neutralization -- ROUTE_CORE_OWNER_NEUTRALIZATION_REDUCTION.md
    Section 2 (the six-residual-type reduction; the arm-partition routine
    below is a value-based port of the verified regression in
    scripts/check_route_core_owner_neutralization.py).
  * Short-singleton / even-singleton repairs -- Lemma C Step 4, cross
    referenced against ROUTE_CORE_CORRECTED_OWNER_NORMALIZATION.md Section 2
    (which combinations, (1,e,e)/(1,1,1)/(2,o,o)/(2,2,2), are legal repairs).
  * Root single-residual-arm feasibility (parity-restricted recruited-port
    rule, and the (r,o,o)/(r,e,e) fallback) -- per census update from the
    coordinator on 2026-09-01, cross-checked directly against the current
    `residuals` construction in scripts/alphabet_contexts.py.
  * Two-input owners (act2 / V21 / V22) -- coordinator update, 2026-09-01:
    when a vertex's lone short/even residual arm has no feasible p and no
    neutral unit (nonroot: q==0; root: any r), the resolution depends on
    the PARITY of its active-child count k:
      - odd k >= 3: cancel k-1 in pairs and keep exactly ONE active child
        -- always resolves (falls back to the ordinary single-active
        context (h,{r},0,free); reduce6 always lands in 1..6, for any r
        including r==8).  If that kept child is itself a residue-one
        zero-spare owner it becomes this vertex's L1 child as usual.
      - even k >= 2: keep exactly TWO active children uncancelled.
        Nonroot coverage is asymmetric by head: h>=1 has continuing_act2
        for r in {1,2,4,6} (own key h{h}_{r}_p0_act2); h==0 has
        continuing_act2 for r in {4,6,8} (own key h0_{r}_p0_act2 --
        coordinator, 2026-09-01: exact search found an any2-token family
        for this two-input cell), but for r in {1,2} at h==0 there is no
        act2 entry at all -- v emits no key of its own and is instead
        recorded as its parent's child TYPE "V21" (r==1) / "V22" (r==2)
        (kind continuing_*/continuing_empty_V2 on the parent).  r==8 thus
        only ever resolves at h==0.  Root's own act2 covers any r in 1..6
        directly as root_{r}_p{p}_act2.
    Cross-checked against the regenerated scripts/alphabet_contexts.py
    (width extras V21=5, V22=6, act2=2, and the explicit continuing_act2 /
    continuing_empty_V2 / V21,V22 loops).
  * Undone four-short-unit residual, (1,1,1,3)/(1,3,3,3) with p in 0..2 and
    child in {none,free,L1} (kinds bottom_fourshort/continuing_fourshort),
    and the matching root residuals, are in the alphabet -- the R-empty
    fallback that undoes a four-short unit (used when no plain same-parity
    pair is available) targets these directly.
  * Genuinely UNCOVERED vertices report full local diagnostic data
    (coordinator request, 2026-09-01): h_raw/h, the arm lengths BEFORE
    neutralization, ports, k (active-child count), the post-neutralization
    residual, and which repairs were tried and why each failed.
  * Coordinator, 2026-09-02 (normalised-gate/schedule() audit, four fixes):
    (1) a residue-one zero-spare owner (arms [1], no ports, ONE FREE
        active child) is NEVER its own cell -- like V21/V22/L12 it is a
        passthrough, folded into its parent as child tag "L1" (this
        corrects an earlier misreading of Section 7: only when its own
        active child is itself L1/L11/L12/V21/V22, not free, does it keep
        its own key -- tracked in l1_nonfree_child_events).
    (2) an odd lone arm reducing to 3 or 5 (wide range) with a subdivided
        parent edge (h>=1) has no direct family ("rays only, token
        needed") -- it now always retains a neutral unit too (h==0, or
        wide==7 at any h, are unaffected).
    (3) root's opposite-parity residual (1,2) with q==0 is infeasible --
        it now retains a neutral unit instead (q>=1 already worked via the
        general recruit_ports(q,2)).
    (4) root's lone residual arm with an active child and q==0 is
        infeasible (recruit_ports(q,2) already gives p>=1 whenever q>=1,
        so q==0 is the only gap) -- it now retains a neutral unit too,
        reusing the same pair/four-short repair as the child=='none' case.

Diagnostic fallbacks: when the case analysis needs to "retain a neutral
unit" and no plain pair is available, a four-short unit ((1,1,1,3) or
(1,3,3,3)) is also a valid neutral unit to undo (Section 1 of the
neutralization note) and is used instead, even though the resulting
(wider) residual may not yet have an entry in alphabet_contexts.json --
this is reported via missing_from_alphabet, not silently forced.  A
genuinely UNCOVERED vertex (no neutral unit of any kind available, and no
cancelled active-child group to absorb a lone port into) is recorded in
the "uncovered" list with its local (arms, ports, child) data and still
receives a placeholder context so processing continues; these reflect the
proof draft's own acknowledged open gaps (Section 10), not scheduler bugs.

schedule() output schema (for the constructor)
------------------------------------------------
`schedule(parent_array) -> dict` runs the same case analysis as the CLI on
one explicit tree and returns everything in machine-readable form, keyed by
ORIGINAL TREE VERTEX ids throughout (never by abstract lengths alone), so a
downstream numeric-label constructor can read off exactly which tree edge
plays which role.  Top level:

    {
      "n": int, "is_path": bool, "root": int | None,
      "core_vertices": [v, ...],                  # sorted core vertex ids
      "owners": [{"vertex": v, "context_key": str}, ...],   # v's WITH a key
      "rows": {v: <family row>, ...},              # every CORE vertex, owner or not
      "uncovered": [...], "l1_pair_events": [...], # same as the CLI report
    }

`is_path` True means the whole tree is a path (Lemma A); everything else is
empty/None.  `owners` lists only vertices that emit their OWN context key
(excludes V21/V22 passthrough vertices, which fold into their parent's key
-- see "passthrough" below).  `rows` covers every core vertex (owners,
passthrough vertices, AND stationary vertices, since a stationary vertex can
still have a helper_absorption or be the parent of cancelled_active_groups).

Each family row (one per core vertex v) is:

    {
      "vertex": v, "is_owner": bool, "is_root": bool,
      "context_key": str | None,   # None if not owner, or a V21/V22 passthrough
      "passthrough": "V21" | "V22" | None,  # set iff v folds into its parent's key
      "head_chain_edges": [(u1,u2), (u2,u3), ..., (uk,v)],  # top(parent)->v;
                                                              # [] if root or direct
      "arms": [
        {"child": c, "length": ell, "edges": [(u1,u2), ...],  # v->...->c
         "role": "residual" | "repair_retained" | "neutral_pair" | "neutral_fourshort",
         "group_id": int}         # present for every role except "residual"
        , ...
      ],
      "neutral_units": [           # owner-free units NOT used for a repair
        {"group_id": int, "type": "pair" | "fourshort",
         "children": [c, ...], "lengths": [ell, ...]}, ...
      ],
      "repair": {"group_id": int, "type": "pair" | "fourshort", "children": [c, ...]} | None,
                                    # the ONE neutral unit "undone" and folded
                                    # into the residual, if the singleton/
                                    # empty-residual case needed a repair
      "ports": [c, ...],           # every direct non-owner child (a "port")
      "recruited_ports": int | None,  # how many of `ports` the context uses
                                       # (the rest form v's own zero-sum
                                       # ordinary block); None if not owner
      "active_edges": [
        {"child": c, "edges": [(v,...,c)],
         "child_is_owner": bool,          # child emits its OWN context_key
         "child_context_key": str | None,
         "child_passthrough": "V21"|"V22"|None,  # set iff the child folds into v
         "role": "kept_free" | "kept_L1" | "kept_V21" | "kept_V22" |
                 "kept_act2_1" | "kept_act2_2" | "cancelled",
         "group_id": int}   # present iff role == "cancelled"
        , ...
      ],
      "cancelled_active_groups": [   # active children whose heads are set
        {"group_id": int, "type": "pair" | "triple", "children": [c, ...]}, ...
      ],                            # to sum to zero (Lemma C Step 2) and
                                     # contribute nothing to v's own context
      "helper_absorption": {         # only when v is STATIONARY (not owner)
        "technique": "single_port" | "two_port" | "cancelled_group_rebalance",
        "ports": [c, ...],
        "active_child": c,                    # single_port / two_port only
        "cancelled_group_children": [c, ...], # cancelled_group_rebalance only
      } | None,
      "carrier": [param, ...] | None,   # data/alphabet_carriers.json[context_key],
                                         # or None if absent from that file or v has
                                         # no context_key (not owner, or passthrough)
      "input_carried": bool,            # True iff carrier contains "x"/"x1"/"x2"
      "keep_head_symbolic": bool,       # coordinator, 2026-09-02: True iff SOME
                                         # parent's carrier names v as the child
                                         # carrying its "x" (single-input families)
                                         # or "x1"/"x2" (act2's two kept children,
                                         # matching the kept_act2_1/kept_act2_2
                                         # active_edges roles) -- the constructor
                                         # must leave v's OWN head as a symbolic
                                         # parameter rather than assigning it a
                                         # number immediately.  Set on v's row by
                                         # its PARENT's _build_row call, so it can
                                         # flip True after v's own row was built
                                         # (bottom-up); defaults False.
    }

Every `"edges"` / `"head_chain_edges"` list is the literal sequence of
ORIGINAL TREE EDGES (as (upper_vertex, lower_vertex) pairs, parent to child)
making up that chain -- length `ell+1`, one slot per label the constructor
must place, matching Lemma D's charge count exactly.  A `neutral_unit`'s or
`repair`'s "children" are the LOWER endpoint of each of its member arms (use
`row["arms"]` to get each member's own "edges").  Root vertices have no
"head_chain_edges" (empty list) and no incoming edge at all: per Lemma A/
Section 1, `lambda(e_root) := 0` is a bookkeeping convention, not a real
edge, so the constructor originates the whole labelling at `root`.

Python 3 standard library only.  Run with the project venv:
    .venv/bin/python research/antimagic/scripts/context_scheduler.py --all 7
"""
from __future__ import annotations

import argparse
import heapq
import itertools
import json
import os
import random
import sys
from collections import Counter
from typing import Dict, List, Optional, Sequence, Tuple

ODD = (1, 3, 5)
EVEN = (2, 4, 6)

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.normpath(os.path.join(HERE, "..", "data"))
ALPHABET_PATH = os.path.join(DATA_DIR, "alphabet_contexts.json")
ALPHABET_CARRIERS_PATH = os.path.join(DATA_DIR, "alphabet_carriers.json")


# --------------------------------------------------------------------------
# Residue reduction helpers (six-edge mothers: a chain reduces to the
# representative of its length's residue class, never below its own length).
# --------------------------------------------------------------------------

def reduce6(ell: int) -> int:
    """Reduce a positive chain length to its representative in 1..6."""
    return 1 + (ell - 1) % 6


def reduce_wide(ell: int) -> int:
    """Reduce ell (>=3) to the portless-singleton representative in 3..8."""
    return 3 + (ell - 3) % 6


def reduce_head(h_raw: int) -> int:
    """Head residue in 0..5.  h = 0 for a direct parent edge (ell == 0);
    for a subdivided edge, reduce length mod 6 -- a six-edge mother makes a
    length-6k chain behave exactly like a direct edge (same head, only
    inverse pairs added), so raw length 6, 12, ... also reduces to 0, matching
    the alphabet's head range {0,...,5} (NOT {1,...,6}: unlike arms, a head
    can legitimately be 0, so the minimal representative of residue class 0
    is 0 itself, not 6)."""
    return h_raw % 6


def recruit_ports(q: int, cap: int) -> int:
    """Recruited-port count p <= cap with q - p != 1 always (ordinary block
    of the unrecruited ports must have size 0 or >= 2)."""
    if q <= cap:
        return q
    if q == cap + 1:
        return cap - 1
    return cap


def root_singleton_p(q: int, r: int) -> Optional[int]:
    """Feasible recruited-port count for a LONE root residual arm of
    residue r (1..6).

    Per the 2026-09-01 census update: a lone root residual arm needs either
    p = 2, or p = 0 for an odd residue / p = 1 for an even residue
    (root_1_p1, root_3_p1, root_2_p0, root_4_p0 are infeasible).  Returns
    None if no feasible p exists for the given port count q (caller must
    then retain a neutral pair, or -- coordinator, 2026-09-02, for the
    q==0/no-unit/k>=2-active-children case specifically -- spend active
    children on it instead).

    r == 6 is an exact-search exception (coordinator, 2026-09-02): unlike
    every other even residue, root_6_p0_bot IS feasible, behaving like an
    odd residue at p == 0 specifically (q == 0 only -- q >= 1 is
    unaffected, already using p in {1,2} same as residues 2,4, since there
    is no evidence r==6 differs from them there)."""
    is_odd = r % 2 == 1
    candidates = (2, 0) if is_odd else (2, 1)
    for p in candidates:
        if q >= p and (q - p) != 1:
            return p
    if r == 6 and q == 0:
        return 0
    return None


# --------------------------------------------------------------------------
# Owner-free neutralization (ROUTE_CORE_OWNER_NEUTRALIZATION_REDUCTION.md).
# Value-based port of the verified index-based routine in
# check_route_core_owner_neutralization.py.  Operates on raw arm lengths
# (not yet reduced to representatives); returns (neutral_groups, residual)
# where each group is a tuple of 2 raw lengths (same parity, not {1,3}) or 4
# raw lengths (the four-short units (1,1,1,3) / (1,3,3,3)), and residual is
# a list of 0-3 raw lengths of one of the six structural types: empty, a
# single odd length, a single even length, {1,3}, one odd + one even, or
# {1,3,even}.
# --------------------------------------------------------------------------

def _plan_even_odd_block(lengths: Sequence[int], indices: Sequence[int]) -> Optional[Tuple[Tuple[int, ...], ...]]:
    """Partition an even number of odd-arm indices into neutral pairs / a
    four-short unit.  Returns None if the block is the literal pair {1,3}
    (the one odd combination that cannot be neutralized)."""
    indices = list(indices)
    if len(indices) % 2:
        raise ValueError("odd block size")
    # 2026-09-02 (Fable): neutral units are verified by RESIDUE modulo six
    # (the six-edge insertion extends them), so the impossible pair is any
    # pair with residues {1, 3}, e.g. (3, 7) or (1, 9), not only the literal
    # lengths (1, 3); buckets are therefore taken modulo six.
    if sorted(lengths[i] % 6 for i in indices) == [1, 3]:
        return None

    ones = [i for i in indices if lengths[i] % 6 == 1]
    threes = [i for i in indices if lengths[i] % 6 == 3]
    long = [i for i in indices if lengths[i] % 6 == 5]
    groups: List[Tuple[int, ...]] = []

    odd_buckets = tuple(name for name, bucket in (("one", ones), ("three", threes), ("long", long)) if len(bucket) % 2)
    if odd_buckets == ("one", "long"):
        groups.append((ones.pop(), long.pop()))
    elif odd_buckets == ("three", "long"):
        groups.append((threes.pop(), long.pop()))
    elif odd_buckets == ("one", "three"):
        if long:
            groups.append((ones.pop(), long.pop()))
            groups.append((threes.pop(), long.pop()))
        elif len(ones) >= 3:
            groups.append((ones.pop(), ones.pop(), ones.pop(), threes.pop()))
        else:
            if len(ones) != 1 or len(threes) < 3:
                return None
            groups.append((ones.pop(), threes.pop(), threes.pop(), threes.pop()))
    elif odd_buckets:
        return None

    for bucket in (ones, threes, long):
        if len(bucket) % 2:
            return None
        groups.extend((bucket[p], bucket[p + 1]) for p in range(0, len(bucket), 2))

    return tuple(groups)


def reduce_owner_arms_idx(lengths: Sequence[int]) -> Tuple[List[Tuple[int, ...]], List[int]]:
    """Partition raw arm lengths into (neutral groups of INDICES into
    `lengths`, residual list of INDICES).  Index-preserving core of
    reduce_owner_arms(), used by the Scheduler to map neutralization
    decisions back to the actual tree edges (for schedule())."""
    lengths = list(lengths)
    odd = [i for i, v in enumerate(lengths) if v % 2]
    even = [i for i, v in enumerate(lengths) if not v % 2]
    groups: List[Tuple[int, ...]] = []
    residual: List[int] = []

    if len(even) % 2:
        residual.append(even.pop())
    groups.extend((even[p], even[p + 1]) for p in range(0, len(even), 2))

    if len(odd) % 2:
        placed = False
        for survivor in odd:
            remainder = [i for i in odd if i != survivor]
            sub = _plan_even_odd_block(lengths, remainder)
            if sub is not None:
                residual.append(survivor)
                groups.extend(sub)
                placed = True
                break
        if not placed:
            raise AssertionError(f"no legal odd survivor for {lengths}")
    elif sorted(lengths[i] % 6 for i in odd) == [1, 3] and len(odd) == 2:
        residual.extend(odd)
    else:
        sub = _plan_even_odd_block(lengths, odd)
        if sub is None:
            raise AssertionError(f"odd arms not neutralizable: {lengths}")
        groups.extend(sub)

    return groups, residual


def reduce_owner_arms(lengths: Sequence[int]) -> Tuple[List[Tuple[int, ...]], List[int]]:
    """Partition raw arm lengths into (neutral groups of raw lengths,
    residual list of raw lengths).  Value-based wrapper around
    reduce_owner_arms_idx(); see module docstring."""
    lengths = list(lengths)
    groups_idx, residual_idx = reduce_owner_arms_idx(lengths)
    value_groups = [tuple(sorted(lengths[i] for i in g)) for g in groups_idx]
    value_residual = [lengths[i] for i in residual_idx]
    return value_groups, value_residual


# --------------------------------------------------------------------------
# Repair helpers on already-formed neutral groups (raw-length tuples).
# --------------------------------------------------------------------------

def _find_pair(groups: Sequence[Tuple[int, ...]], parity: Optional[str]) -> Optional[Tuple[int, ...]]:
    for g in groups:
        if len(g) == 2:
            is_odd = g[0] % 2 == 1
            if parity is None or (parity == "odd" and is_odd) or (parity == "even" and not is_odd):
                return g
    return None


def _find_same_value_pair(groups: Sequence[Tuple[int, ...]], value: int) -> Optional[Tuple[int, ...]]:
    for g in groups:
        if len(g) == 2 and g[0] == value and g[1] == value:
            return g
    return None


def _find_any_group(groups: Sequence[Tuple[int, ...]]) -> Optional[Tuple[int, ...]]:
    return groups[0] if groups else None


def _find_pair_position(groups: Sequence[Tuple[int, ...]], parity: Optional[str]) -> Optional[int]:
    """Position-returning twin of _find_pair(), for reconstructing which
    group (by index into groups_idx) a repair actually used (schedule())."""
    for i, g in enumerate(groups):
        if len(g) == 2:
            is_odd = g[0] % 2 == 1
            if parity is None or (parity == "odd" and is_odd) or (parity == "even" and not is_odd):
                return i
    return None


def _find_any_group_position(groups: Sequence[Tuple[int, ...]]) -> Optional[int]:
    """Position-returning twin of _find_any_group()."""
    return 0 if groups else None


def repair_singleton_any_unit(r: int, groups: Sequence[Tuple[int, ...]]) -> Optional[List[int]]:
    """R reduces to a single value r in {1,2,4,6,8}, portless, no active
    child: alphabet_contexts.py's generalized `bottom_repair` loop (r in
    (1,2,4,6,8), any unit in `units`) now allows retaining ANY neutral unit
    -- any same-parity pair other than {1,3}, or a four-short unit
    ((1,1,1,3)/(1,3,3,3)) -- not just a parity-matched one.  Convention:
    residual r first, then the unit's own values in nondecreasing order
    (`(r,) + u` in alphabet_contexts.py), e.g. (1,3,3), (2,4,4), (4,1,1,1,3).
    A pair's values still need reduce6; a four-short unit's raw values
    (literal 1s and 3s) are already canonical."""
    g = _find_any_group(groups)
    if g is None:
        return None
    vals = sorted(reduce6(x) for x in g) if len(g) == 2 else sorted(g)
    return [r] + vals


def v2_marker(ctx: Optional[dict]) -> Optional[str]:
    """'V21'/'V22'/'L12' if ctx is a passthrough marker left by a child
    that emits no key of its own and is instead recorded as this special
    child TYPE of its parent (coordinator rule, 2026-09-01): V21/V22 from
    the two-input mechanism with a direct (h==0) parent edge (_process),
    L12 from the forced-antipode (h==0, arms (1,2), no ports, no active
    child) bottom context (_decide's n==2 branch)."""
    return ctx.get("passthrough") if ctx else None


def is_L12_candidate(ctx: Optional[dict]) -> bool:
    """The forced-antipode bottom context (coordinator, 2026-09-02, from the
    normalised gate audit): a NONROOT owner with a direct parent edge
    (h==0), residual arms exactly (1,2), no ports, no active child, and (by
    construction -- see the widening preference in _decide) no neutral
    units retained.  Every family for this exact context contains the
    antipode of its OWN head, so like L11 it is folded into its parent as
    child type "L12" instead of emitting its own key.

    2026-09-02 (Fable): the (1,2) bottom now has a non-forced-antipode
    family (batch fa12b, token rank any2), so it is an ordinary owner
    again and is NOT folded; the predicate always returns False."""
    return False


def is_L11_candidate(ctx: Optional[dict]) -> bool:
    """The (1; one port) forced-antipode bottom (proof draft 8b; catalogue
    census 2026-09-02: its unique family has head 3y and port -3y): a
    NONROOT owner with a direct parent edge (h==0), residual arms exactly
    (1), exactly one recruited port and no active child.  Folded into its
    parent as child type "L11" instead of emitting its own key."""
    return bool(ctx) and not ctx.get("is_root") and ctx.get("h") == 0 \
        and ctx.get("arms") == [1] and ctx.get("ports") == 1 and ctx.get("child") == "none"


def is_zero_spare(ctx: Optional[dict]) -> bool:
    """A 'residue-one zero-spare owner': its OWN context is a single
    residual arm of residue 1, zero ports, and its own active-child slot is
    exactly "free" -- coordinator, 2026-09-02: "If the residue-one owner's
    own active child is itself of type L1/L11/L12/V2 (not free), keep
    emitting it as a separate key."  Regardless of head otherwise.  Its
    only family forces its output head to -x, so it cannot be a free
    active-child head itself (Lemma C Step 2 / Section 7) -- see the
    passthrough conversion in _process, which is why this predicate now
    determines whether v gets its OWN key at all, not just its parent's
    child tag.

    2026-09-02 (Fable): the forced head is a property of the DIRECT parent
    edge only.  The joint row spec of the L1 child type carries no head chain
    ("arms=1;active;input"), so folding a letter whose own head chain is
    nonzero would apply a family to a topology it does not describe, and the
    letter contexts h1_1_p0_act ... h5_1_p0_act do have families with a free
    head and without the antipode of their head.  Hence h == 0 is required."""
    return bool(ctx) and ctx.get("h", 0) == 0 \
        and ctx.get("arms") == [1] and ctx.get("ports") == 0 and ctx.get("child") == "free"


def _is_l1_ish(ctx: Optional[dict]) -> bool:
    """is_zero_spare(ctx), generalized to also recognize an already-
    converted L1 passthrough marker (a zero-spare child is now ALWAYS a
    passthrough by the time it reaches a sibling-grouping check, per the
    coordinator's 2026-09-02 correction, so is_zero_spare alone would never
    fire here in practice; kept as a defensive OR)."""
    return is_zero_spare(ctx) or v2_marker(ctx) == "L1"


# --------------------------------------------------------------------------
# Context key / width, matching run_alphabet_batch.py's key() and
# alphabet_contexts.py's width() exactly.
# --------------------------------------------------------------------------

_TAG_MAP = {"none": "bot", "free": "act", "L1": "L1", "L11": "L11", "L12": "L12", "V21": "V21", "V22": "V22", "act2": "act2", "A2": "A2", "L1A2": "L1A2"}
_WIDTH_EXTRA = {"none": 0, "free": 1, "L1": 4, "L11": 4, "L12": 6, "V21": 5, "V22": 6, "act2": 2, "A2": 7, "L1A2": 11}


def context_key(ctx: dict) -> str:
    tag = _TAG_MAP.get(ctx["child"], str(ctx["child"]))
    pre = "root" if ctx.get("is_root") else f"h{ctx['h']}"
    arms_str = "-".join(str(a) for a in ctx["arms"]) or "none"
    return f"{pre}_{arms_str}_p{ctx['ports']}_{tag}"


def context_width(ctx: dict) -> int:
    extra = _WIDTH_EXTRA.get(ctx["child"], 4)
    base = sum(a + 1 for a in ctx["arms"]) + ctx["ports"] + extra
    if ctx.get("is_root"):
        return base
    return base + (ctx["h"] + 1)


def alphabet_entry_key(entry: dict) -> str:
    tag_map = {False: "bot", "none": "bot", True: "act", "free": "act", "L1": "L1", "L11": "L11"}
    tag = tag_map.get(entry["active"], str(entry["active"]))
    pre = "root" if entry.get("kind") == "root" else f"h{entry.get('head', 0)}"
    arms_str = "-".join(str(a) for a in entry["arms"]) or "none"
    return f"{pre}_{arms_str}_p{entry['ports']}_{tag}"


def load_alphabet_keys(path: str = ALPHABET_PATH) -> set:
    try:
        with open(path) as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return set()
    return {alphabet_entry_key(e) for e in data}


def load_alphabet_carriers(path: str = ALPHABET_CARRIERS_PATH) -> Dict[str, Optional[list]]:
    """context key -> list of token-carrier parameter names, or None.
    Keys absent from the file are treated as None by callers (dict.get)."""
    try:
        with open(path) as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return {}


# --------------------------------------------------------------------------
# Tree construction: explicit parent array, or Prufer-sequence trees
# (random or exhaustive).
# --------------------------------------------------------------------------

def tree_from_parent(parent_in: Sequence[int]) -> Tuple[int, List[int], List[List[int]]]:
    """parent_in[0] is ignored (vertex 0 is the root); parent_in[i] (i>=1)
    is the parent of vertex i.  Returns (n, parent, children)."""
    n = len(parent_in)
    parent = [-1] + list(parent_in[1:])
    children: List[List[int]] = [[] for _ in range(n)]
    for v in range(1, n):
        children[parent[v]].append(v)
    return n, parent, children


def prufer_decode(seq: Sequence[int], n: int) -> List[Tuple[int, int]]:
    if n == 1:
        return []
    if n == 2:
        return [(0, 1)]
    degree = [1] * n
    for x in seq:
        degree[x] += 1
    leaves = [i for i in range(n) if degree[i] == 1]
    heapq.heapify(leaves)
    edges = []
    for x in seq:
        leaf = heapq.heappop(leaves)
        edges.append((leaf, x))
        degree[leaf] -= 1
        degree[x] -= 1
        if degree[x] == 1:
            heapq.heappush(leaves, x)
    remaining = [i for i in range(n) if degree[i] == 1]
    edges.append((remaining[0], remaining[1]))
    return edges


def root_from_edges(n: int, edges: Sequence[Tuple[int, int]]) -> Tuple[Optional[int], List[int], List[List[int]]]:
    """Build adjacency, detect the path case, choose a root of degree >= 3
    (smallest index), and BFS to a rooted parent/children representation.
    Returns (root_or_None, parent, children); root is None iff the tree is
    a path (Lemma A)."""
    adj: List[List[int]] = [[] for _ in range(n)]
    for a, b in edges:
        adj[a].append(b)
        adj[b].append(a)
    deg = [len(a) for a in adj]
    candidates = [v for v in range(n) if deg[v] >= 3]
    if not candidates:
        return None, [], []
    root = min(candidates)
    parent = [-1] * n
    children: List[List[int]] = [[] for _ in range(n)]
    seen = [False] * n
    seen[root] = True
    stack = [root]
    while stack:
        u = stack.pop()
        for w in adj[u]:
            if not seen[w]:
                seen[w] = True
                parent[w] = u
                children[u].append(w)
                stack.append(w)
    return root, parent, children


def random_prufer_tree(n: int, rng: random.Random) -> List[Tuple[int, int]]:
    if n <= 2:
        return prufer_decode([], n)
    seq = [rng.randrange(n) for _ in range(n - 2)]
    return prufer_decode(seq, n)


def all_prufer_sequences(n: int):
    if n <= 2:
        yield ()
        return
    for seq in itertools.product(range(n), repeat=n - 2):
        yield seq


# --------------------------------------------------------------------------
# Core decomposition (Lemma B): suppress degree-2 vertices.
# --------------------------------------------------------------------------

class Core:
    __slots__ = ("n", "root", "parent", "degree", "core_set", "children", "ell", "chain")

    def __init__(self, n: int, parent: List[int], children: List[List[int]], root: int):
        self.n = n
        self.root = root
        self.parent = parent
        degree = [(1 if parent[v] != -1 else 0) + len(children[v]) for v in range(n)]
        self.degree = degree
        core_set = set(v for v in range(n) if v == root or degree[v] != 2)
        self.core_set = core_set
        core_children: Dict[int, List[Tuple[int, int]]] = {v: [] for v in core_set}
        ell: Dict[int, int] = {}
        # chain[v]: the suppressed vertices between v's core parent and v (in
        # order, parent-to-child), followed by v itself -- i.e. the ell+1
        # tree edges (core_parent(v), chain[v][0]), (chain[v][0], chain[v][1]),
        # ..., (chain[v][-2], v) that make up v's parent core edge.  Used by
        # schedule() to report actual tree edges, not just abstract lengths.
        chain: Dict[int, List[int]] = {}
        for v in sorted(core_set):
            if v == root:
                continue
            u = parent[v]
            suppressed: List[int] = []
            while u not in core_set:
                suppressed.append(u)
                u = parent[u]
            suppressed.reverse()  # collected bottom-up; store top-down (parent side first)
            ell[v] = len(suppressed)
            chain[v] = suppressed + [v]
            core_children[u].append((v, len(suppressed)))
        self.children = core_children
        self.ell = ell
        self.chain = chain

    def chain_edges(self, v: int) -> List[Tuple[int, int]]:
        """The ell+1 tree edges making up v's parent core edge, top (core
        parent) to bottom (v), as (upper, lower) vertex pairs."""
        if v not in self.chain:
            return []
        nodes = [self.parent[self.chain[v][0]]] + self.chain[v]
        return list(zip(nodes, nodes[1:]))


# --------------------------------------------------------------------------
# Owner assignment (Lemma C): bottom-up recursion over the core.
# --------------------------------------------------------------------------

class Scheduler:
    def __init__(self, core: Core, track_rows: bool = True, carriers: Optional[Dict[str, list]] = None):
        self.core = core
        self.owners: List[Tuple[int, dict]] = []
        self.uncovered: List[dict] = []
        self.l1_pair_events: List[dict] = []
        self.l1_nonfree_child_events: List[dict] = []
        self.rows: Dict[int, dict] = {}
        # carriers: context_key -> list of token-carrier parameter names
        # (alphabet_carriers.json), or None to skip carrier/keep_head_symbolic
        # bookkeeping (the bulk CLI paths never read it).
        self.carriers = carriers
        # track_rows=False skips _build_row's bookkeeping entirely (chain
        # edges, per-arm role tagging, ...) for callers that only need the
        # (owner, context_key) decision -- e.g. the bulk --all/--random CLI
        # modes, which never read self.rows.  schedule() leaves it True.
        self.track_rows = track_rows

    def run(self) -> List[Tuple[int, dict]]:
        self._process(self.core.root)
        return self.owners

    def _uncovered_ctx(self, is_root: bool, h: int, arms: List[int], ports: int, child: str) -> dict:
        return {"h": h, "arms": sorted(arms), "ports": ports, "child": child, "kind": "UNCOVERED", "is_root": is_root}

    def _process(self, v: int) -> Tuple[bool, Optional[dict]]:
        core = self.core
        arms: List[int] = []
        arm_children: List[int] = []
        ports = 0
        port_children: List[int] = []
        active: List[Tuple[int, int, dict]] = []  # (child_vertex, ell, ctx)
        for (u, e) in core.children.get(v, []):
            owner_u, ctx_u = self._process(u)
            if owner_u:
                active.append((u, e, ctx_u))
            elif e == 0:
                ports += 1
                port_children.append(u)
            else:
                arms.append(e)
                arm_children.append(u)

        groups_idx, residual_idx = reduce_owner_arms_idx(arms)
        groups = [tuple(sorted(arms[i] for i in g)) for g in groups_idx]
        residual_raw = [arms[i] for i in residual_idx]
        is_root = v == core.root
        h_raw = core.ell.get(v, 0)
        q = ports
        k_orig = len(active)

        # Coordinator, 2026-09-01 (both messages): if v's single-residual-arm
        # case would otherwise be UNCOVERED (no feasible p / no neutral
        # unit) using only arms and ports, and v has active children to
        # spend on it, the resolution depends on the PARITY of k_orig:
        #   * odd k_orig >= 3: cancel k_orig-1 in pairs (always possible)
        #     and keep exactly ONE active child -- this ALWAYS resolves the
        #     problem (falls back to the ordinary single-active context,
        #     reduce6 always lands in 1..6), for ANY r including r == 8.
        #   * even k_orig >= 2: keep exactly TWO active children uncancelled
        #     (act2/V21/V22).  Root's own act2 covers any r in 1..6
        #     (alphabet_contexts.py's root loop uses the unrestricted
        #     residuals list).  Nonroot's continuing_act2 alphabet coverage
        #     is asymmetric by head (alphabet_contexts.py):
        #       h >= 1: r in {1,2,4,6}            (own key h{h}_{r}_p0_act2)
        #       h == 0, r in {1,2}: no act2 entry -- V21/V22 parent marker
        #       h == 0, r in {4,6,8}: own key h0_{r}_p0_act2 (coordinator,
        #         2026-09-01: exact search found an any2-token family)
        #     so r == 8 only ever resolves at h == 0.
        cancelled_groups: List[List[Tuple[int, int, dict]]] = []  # for the row: [(child,ell,ctx), ...] per group
        kept_active: List[Tuple[int, int, dict]] = []  # active items actually kept (1 or 2), with role tags
        kept_roles: List[str] = []

        r_trigger = self._act2_trigger(is_root, h_raw, residual_raw, q, groups)
        if r_trigger is not None and is_root and len(r_trigger) == 1:
            # Coordinator, 2026-09-02: root's lone residual arm with q==0,
            # no neutral unit, and k_orig TRUE active children -- by
            # construction only r in {2,4} ever reaches this branch now
            # (root_singleton_p already succeeds directly for r in
            # {1,3,5,6}, so _act2_trigger returns None for those).  k==1
            # cannot occur here (T-degree(root) = 1 [this lone original
            # arm, since groups is empty] + k_orig, so T-degree>=3 forces
            # k_orig>=2).  Exact search: k==2 can't spare a pair (k-1==1)
            # -- keep BOTH (act2); every other k_orig>=2 (odd or even)
            # keeps exactly ONE and cancels the rest in pairs/one-triple
            # (act) -- unlike the generic odd/even-k split below, which
            # would wrongly use act2 for every even k_orig, not just 2.
            if k_orig == 2:
                owner, ctx, kept_active, kept_roles, cancelled_groups = self._resolve_act2(
                    v, is_root, h_raw, r_trigger, q, active)
                if self.track_rows:
                    self._build_row(v, is_root, h_raw, arms, arm_children, groups_idx, groups, residual_idx,
                                     port_children, active, owner, ctx, kept_active, kept_roles, cancelled_groups,
                                     helper=None)
                return owner, ctx
            # k_orig >= 3 (odd or even): keep ONE active child and cancel
            # the rest -- root_{r}_p0_act is feasible DIRECTLY here (exact
            # search, coordinator 2026-09-02), independent of the separate
            # (more conservative) q==0 check _decide's generic child_type
            # != "none" branch applies elsewhere (rule 4, 2026-09-01,
            # e.g. a NATURALLY single active child with other arms that
            # got neutralized away) -- so this is resolved directly here,
            # not by falling through to _decide.
            kept, cancelled_groups = self._reduce_odd_k_to_one(v, active)
            _child, _ell, child_ctx = kept[0]
            marker = v2_marker(child_ctx)
            if marker is not None:
                kept_child_type, kept_role = marker, f"kept_{marker}"
            elif is_zero_spare(child_ctx):
                kept_child_type, kept_role = "L1", "kept_L1"
            else:
                kept_child_type, kept_role = "free", "kept_free"
            # NOTE: _act2_trigger's root branch fires whenever
            # root_singleton_p(q, r) fails, which can happen at q >= 1 too
            # (e.g. an odd residue at q==1) -- not only the q==0 case the
            # coordinator's exact search names.  Use the actual recruited
            # port count (0 when q==0, matching root_{r}_p0_act; the
            # general recruit_ports(q,2) otherwise, matching the
            # already-correct behavior recruit_ports gives elsewhere for
            # a single active child, e.g. root_1_p1_act at q==1) rather
            # than assuming p==0 unconditionally.
            act_p = recruit_ports(q, 2)
            ctx = {"h": 0, "arms": r_trigger, "ports": act_p, "child": kept_child_type, "kind": "root", "is_root": True}
            self.owners.append((v, ctx))
            if self.track_rows:
                self._build_row(v, is_root, h_raw, arms, arm_children, groups_idx, groups, residual_idx,
                                 port_children, active, True, ctx, kept, [kept_role], cancelled_groups,
                                 helper=None)
            return True, ctx
        elif r_trigger is not None and k_orig >= 3 and k_orig % 2 == 1:
            active, cancelled_groups = self._reduce_odd_k_to_one(v, active)
            k_orig = 1
        elif r_trigger is not None and k_orig >= 2 and k_orig % 2 == 0:
            if is_root:
                resolvable = True  # root's act2 is unrestricted (general residuals list)
            elif len(r_trigger) == 2:
                resolvable = False  # the (1,2) shape is root-only
            else:
                # r_trigger[0] is always a reduce6 value (1..6); every one of
                # them is now resolvable at every head -- h>=1 via direct
                # continuing_act2 for all of 1..6 (coordinator, 2026-09-01
                # for 1,2,4,6; 2026-09-02 for 3,5); h==0 via direct
                # continuing_act2 for 3,4,5,6 (2026-09-01 for 4,6;
                # 2026-09-02 for 3,5) or the V21/V22 parent marker for 1,2
                # -- _resolve_act2 picks between them.
                resolvable = True
            if resolvable:
                owner, ctx, kept_active, kept_roles, cancelled_groups = self._resolve_act2(
                    v, is_root, h_raw, r_trigger, q, active)
                if self.track_rows:
                    self._build_row(v, is_root, h_raw, arms, arm_children, groups_idx, groups, residual_idx,
                                     port_children, active, owner, ctx, kept_active, kept_roles, cancelled_groups,
                                     helper=None)
                return owner, ctx

        k = k_orig
        if k >= 2:
            if all(_is_l1_ish(c) for (_u, _e, c) in active):
                self.l1_pair_events.append({"vertex": v, "k": k})
            child_type = "none"
            cancelled_groups = self._partition_cancel_groups(active)
        elif k == 1:
            kept_active = list(active)
            marker = v2_marker(active[0][2])
            if marker is not None:
                child_type = marker
                kept_roles = [f"kept_{marker}"]
            else:
                if is_zero_spare(active[0][2]):
                    child_type = "L1"
                    kept_roles = ["kept_L1"]
                else:
                    child_type = "free"
                    kept_roles = ["kept_free"]
        else:
            child_type = "none"

        had_cancelled_group = k >= 2
        owner, ctx = self._decide(v, is_root, h_raw, residual_raw, ports, child_type, groups, had_cancelled_group,
                                   arms, k_orig)
        if owner and is_zero_spare(ctx):
            # Coordinator, 2026-09-02: a residue-one zero-spare owner
            # (arms [1], no ports, one FREE active child) is NEVER a cell
            # by itself (Section 7) -- it emits no key of its own; its
            # parent's key gets the "L1" child tag instead, exactly like
            # the V21/V22/L12 passthrough (this corrects an earlier
            # misreading of Lemma C: the child does NOT keep a separate key).
            ctx = {"passthrough": "L1"}
        elif owner and is_L11_candidate(ctx):
            # (1; one port) forced-antipode bottom: folded into the parent as
            # child type "L11" (2026-09-02), exactly like L12.
            ctx = {"passthrough": "L11"}
        elif owner and is_L12_candidate(ctx):
            # Forced-antipode bottom context with no neutral unit available
            # to widen away from it (_decide already tried): v emits no key
            # of its own -- it is recorded as its parent's "L12" child type
            # instead, exactly like the V21/V22 passthrough.
            ctx = {"passthrough": "L12"}
        elif owner:
            if ctx and ctx.get("arms") == [1] and ctx.get("ports") == 0 and ctx.get("child") in (
                    "L1", "L11", "L12", "V21", "V22"):
                # Coordinator, 2026-09-02: a residue-one owner whose own
                # active child is itself L1/L11/L12/V21/V22 (not free) is
                # NOT forced-antipode in the same way -- it keeps its own
                # key.  Tracked for the count the coordinator asked for.
                self.l1_nonfree_child_events.append({"vertex": v, "context_key": context_key(ctx),
                                                       "child_tag": ctx.get("child")})
            self.owners.append((v, ctx))
        helper = None
        if not owner and (q >= 1 or cancelled_groups):
            # v is stationary but absorbed something: a lone active child via
            # helper port(s), or a lone leftover port rebalanced into a
            # cancelled active-child group (Lemma C Step 3).
            if k_orig == 1 and q >= 1:
                helper = {"technique": "single_port" if q != 2 else "two_port",
                          "ports": list(port_children), "active_child": active[0][0]}
            elif cancelled_groups and q == 1 and len(residual_idx) == 0:
                helper = {"technique": "cancelled_group_rebalance", "ports": list(port_children),
                          "cancelled_group_children": [c for (c, _e, _ctx) in cancelled_groups[0]]}
        if self.track_rows:
            self._build_row(v, is_root, h_raw, arms, arm_children, groups_idx, groups, residual_idx,
                             port_children, active, owner, ctx, kept_active, kept_roles, cancelled_groups, helper)
        return owner, ctx

    def _partition_cancel_groups(self, items: List[Tuple[int, int, dict]]) -> List[List[Tuple[int, int, dict]]]:
        """Partition k>=2 active items into cancelled groups per Lemma C
        Step 2: a mirror pair for even counts, one free zero-sum triple
        plus pairs for odd counts."""
        items = list(items)
        groups: List[List[Tuple[int, int, dict]]] = []
        if len(items) % 2 == 1:
            groups.append(items[:3])
            items = items[3:]
        for i in range(0, len(items), 2):
            groups.append(items[i:i + 2])
        return groups

    def _repair_group_id(self, ctx: Optional[dict], is_passthrough: bool,
                          groups_val: List[Tuple[int, ...]], n0: int) -> Optional[int]:
        """Which group (position in groups_idx/groups_val) was "undone" and
        folded into the final residual arms, if any -- reconstructed from
        ctx (kind, final arm count) by replaying the SAME deterministic
        lookup _decide used (both _find_pair_position/_find_any_group_position
        and _decide's own _find_pair/_find_any_group scan `groups` in the
        same order, so they agree).  None if no repair happened (direct
        success) or ctx is UNCOVERED/passthrough (no reliable group)."""
        if is_passthrough or not ctx or ctx.get("kind") in ("UNCOVERED", None):
            return None
        final_n = len(ctx.get("arms", []))
        added = final_n - n0
        kind = ctx.get("kind", "")
        if added == 0:
            return None  # direct success, no unit retained
        if kind == "bottom_repair":
            return _find_any_group_position(groups_val)
        if kind in ("bottom_samepar", "continuing_samepar"):
            return _find_pair_position(groups_val, None)
        if kind in ("bottom_fourshort", "continuing_fourshort"):
            return _find_any_group_position(groups_val)
        if kind == "root":
            if added == 2:
                return _find_pair_position(groups_val, None)
            if added == 4:
                return _find_any_group_position(groups_val)
            return None
        if kind == "bottom_oe_widened":
            # The (h=0, arms (1,2), no ports, no active child) forced-
            # antipode widening always uses _find_any_group directly (no
            # pair preference) -- coordinator, 2026-09-02.
            return _find_any_group_position(groups_val)
        return None

    def _build_row(self, v: int, is_root: bool, h_raw: int, arms: List[int], arm_children: List[int],
                    groups_idx: List[Tuple[int, ...]], groups_val: List[Tuple[int, ...]], residual_idx: List[int],
                    port_children: List[int], active: List[Tuple[int, int, dict]], owner: bool, ctx: Optional[dict],
                    kept_active: List[Tuple[int, int, dict]], kept_roles: List[str],
                    cancelled_groups: List[List[Tuple[int, int, dict]]], helper: Optional[dict]) -> None:
        """Build the machine-readable family row for vertex v and store it
        in self.rows[v] -- see schedule()'s docstring for the schema."""
        core = self.core
        is_passthrough = bool(owner and ctx and "passthrough" in ctx)
        row: dict = {
            "vertex": v,
            "is_owner": owner,
            "context_key": context_key(ctx) if (owner and not is_passthrough) else None,
            "passthrough": ctx.get("passthrough") if is_passthrough else None,
            "is_root": is_root,
            "head_chain_edges": [] if is_root else core.chain_edges(v),
        }

        group_of_arm: Dict[int, int] = {}
        for gid, g in enumerate(groups_idx):
            for i in g:
                group_of_arm[i] = gid
        retained_gid = self._repair_group_id(ctx, is_passthrough, groups_val, len(residual_idx))

        arms_out = []
        for i, (child, ell) in enumerate(zip(arm_children, arms)):
            entry = {"child": child, "length": ell, "edges": core.chain_edges(child)}
            if i in residual_idx:
                entry["role"] = "residual"
            elif group_of_arm.get(i) == retained_gid:
                entry["role"] = "repair_retained"
                entry["group_id"] = retained_gid
            else:
                gid = group_of_arm[i]
                entry["role"] = "neutral_pair" if len(groups_idx[gid]) == 2 else "neutral_fourshort"
                entry["group_id"] = gid
            arms_out.append(entry)
        row["arms"] = arms_out

        row["neutral_units"] = [
            {"group_id": gid, "type": "pair" if len(g) == 2 else "fourshort",
             "children": [arm_children[i] for i in g], "lengths": [arms[i] for i in g]}
            for gid, g in enumerate(groups_idx) if gid != retained_gid
        ]
        row["repair"] = None
        if retained_gid is not None:
            g = groups_idx[retained_gid]
            row["repair"] = {"group_id": retained_gid, "type": "pair" if len(g) == 2 else "fourshort",
                              "children": [arm_children[i] for i in g]}

        row["ports"] = list(port_children)
        row["recruited_ports"] = ctx.get("ports") if (owner and not is_passthrough) else None

        role_by_id = {id(item): role for item, role in zip(kept_active, kept_roles)}
        group_by_id: Dict[int, int] = {}
        for gid, grp in enumerate(cancelled_groups):
            for item in grp:
                group_by_id[id(item)] = gid
        active_edges = []
        for item in active:
            child, ell, child_ctx = item
            entry = {
                "child": child, "edges": core.chain_edges(child),
                "child_is_owner": bool(child_ctx and "passthrough" not in child_ctx),
                "child_context_key": context_key(child_ctx) if (child_ctx and "passthrough" not in child_ctx) else None,
                "child_passthrough": child_ctx.get("passthrough") if child_ctx else None,
            }
            if id(item) in role_by_id:
                entry["role"] = role_by_id[id(item)]
            elif id(item) in group_by_id:
                entry["role"] = "cancelled"
                entry["group_id"] = group_by_id[id(item)]
            else:
                entry["role"] = "cancelled"
            active_edges.append(entry)
        row["active_edges"] = active_edges

        row["cancelled_active_groups"] = [
            {"group_id": gid, "type": "triple" if len(grp) == 3 else "pair",
             "children": [c for (c, _e, _ctx) in grp]}
            for gid, grp in enumerate(cancelled_groups)
        ]
        row["helper_absorption"] = helper
        row["keep_head_symbolic"] = False  # may be flipped True below by a LATER-processed parent
        self.rows[v] = row

        if self.carriers is not None:
            self._mark_carrier(row)

    def _mark_carrier(self, row: dict) -> None:
        """carrier / input_carried on this owner row, and keep_head_symbolic
        on the active child(ren) that carry it (coordinator, 2026-09-02):
        read data/alphabet_carriers.json's parameter list for this row's
        context_key; if it contains "x" (single-input families: free/L1/
        L12/V21/V22's sole active child) or "x1"/"x2" (act2's two kept
        children, matching the kept_act2_1/kept_act2_2 roles already on
        active_edges), mark this row input_carried and the named child(ren)
        keep_head_symbolic.  Passthrough/non-owner rows have no key to look
        up (carrier stays None)."""
        key = row.get("context_key")
        carrier = self.carriers.get(key) if key else None
        row["carrier"] = carrier
        if not carrier:
            row["input_carried"] = False
            return
        wants_x = "x" in carrier
        wants_x1 = "x1" in carrier
        wants_x2 = "x2" in carrier
        row["input_carried"] = wants_x or wants_x1 or wants_x2
        if not row["input_carried"]:
            return
        single_input_roles = ("kept_free", "kept_L1", "kept_L12", "kept_V21", "kept_V22")
        for ae in row["active_edges"]:
            role = ae.get("role")
            child = ae["child"]
            if (wants_x and role in single_input_roles) or \
               (wants_x1 and role == "kept_act2_1") or \
               (wants_x2 and role == "kept_act2_2"):
                if child in self.rows:
                    self.rows[child]["keep_head_symbolic"] = True

    def _act2_trigger(self, is_root: bool, h_raw: int, residual_raw: List[int], q: int,
                       groups: List[Tuple[int, ...]]) -> Optional[List[int]]:
        """Return the residual ARMS (a 1- or 2-element list) if this
        vertex's case would be UNCOVERED using only arms (groups) and
        ports (q) -- i.e. before considering active children -- so
        _process can fall back to the odd-k (keep-one) or even-k
        (keep-two) mechanism when active children exist.  None if the
        ordinary case already succeeds, or if the residual doesn't match
        one of the recognized shapes.

        Two residual shapes trigger:
          * n == 1 (single residual arm): the r VALUE returned is always
            the 1..6 representative (coordinator, 2026-09-01: "an arm of
            length 8 with an active child is the context with r=2"; the
            4/6/8 wide representatives are only for the portless bottom
            singleton, which never reaches this function with a nonempty
            active list to spend).  The parity check (is a repair even
            needed) is done on the WIDE representative -- reduce6 and
            reduce_wide always agree on parity.  Odd wide values 3 and 5
            ALSO need a repair when h>=1 (coordinator, 2026-09-02: "h1_3_p0_bot
            ... has no family, rays only, token needed"); h==0 and wide==7
            are unaffected.
          * root's opposite-parity residual (1,2) with q==0 (n == 2,
            root only -- coordinator, 2026-09-02): checked first since it
            is a different residual size from everything else here."""
        if is_root and len(residual_raw) == 2:
            a, b = residual_raw
            if (a % 2) == (b % 2):
                return None  # literal {1,3}, not opposite-parity
            ro, re_ = (reduce6(a), reduce6(b)) if a % 2 else (reduce6(b), reduce6(a))
            if (ro, re_) != (1, 2) or q != 0:
                return None
            if _find_pair(groups, None) is not None or _find_any_group(groups) is not None:
                return None  # widening (rule 3) already succeeds directly
            return [1, 2]
        if len(residual_raw) != 1:
            return None
        ell = residual_raw[0]
        if is_root:
            if root_singleton_p(q, reduce6(ell)) is not None:
                return None
            if _find_pair(groups, None) is not None:
                return None
            if _find_any_group(groups) is not None:  # a four-short unit also now repairs root
                return None
            return [reduce6(ell)]
        if q != 0:
            return None
        h = reduce_head(h_raw)
        if ell not in (1, 2):
            wide = reduce_wide(ell)
            if wide % 2 == 1 and (h == 0 or wide == 7):
                return None  # odd wide-reduced value: bottom_singleton succeeds directly
        if _find_any_group(groups) is not None:
            return None  # a neutral-unit repair already succeeds
        return [reduce6(ell)]  # 1..6 -- never 7 or 8

    def _reduce_odd_k_to_one(self, v: int, active: List[Tuple[int, int, dict]]
                              ) -> Tuple[List[Tuple[int, int, dict]], List[List[Tuple[int, int, dict]]]]:
        """Cancel k_orig-1 (even, always pairable) active children and keep
        exactly one -- coordinator, 2026-09-01: "when the short-residual
        rule applies and k is odd, cancel k-1 heads in pairs and keep one
        active child."  The kept child then flows through the ordinary
        k==1 classification (zero-spare -> L1, else free) below.  Returns
        ([kept], [cancelled groups]) for both the classification and the
        family row."""
        kept, rest = active[0], active[1:]
        if rest and all(_is_l1_ish(c) for (_u, _e, c) in rest):
            self.l1_pair_events.append({"vertex": v, "k": len(rest), "note": "odd-k-rest-cancelled"})
        cancelled = self._partition_cancel_groups(rest) if rest else []
        return [kept], cancelled

    def _resolve_act2(self, v: int, is_root: bool, h_raw: int, arms: List[int], q: int,
                       active: List[Tuple[int, int, dict]]
                       ) -> Tuple[bool, Optional[dict], List[Tuple[int, int, dict]], List[str],
                                  List[List[Tuple[int, int, dict]]]]:
        """arms is [r] (nonroot, or root's lone-arm case) or [1, 2] (root's
        opposite-parity (1,2) case, coordinator 2026-09-02)."""
        # Prefer non-zero-spare children as the two kept free inputs.
        ordered = sorted(active, key=lambda item: _is_l1_ish(item[2]))
        kept, rest = ordered[:2], ordered[2:]
        if rest and all(_is_l1_ish(c) for (_u, _e, c) in rest):
            self.l1_pair_events.append({"vertex": v, "k": len(rest), "note": "act2-rest-cancelled"})
        cancelled = self._partition_cancel_groups(rest) if rest else []
        if is_root:
            p = recruit_ports(q, 2)
            ctx = {"h": 0, "arms": arms, "ports": p, "child": "act2", "kind": "root", "is_root": True}
            self.owners.append((v, ctx))
            return True, ctx, kept, ["kept_act2_1", "kept_act2_2"], cancelled
        r = arms[0]  # nonroot only ever reaches here with the 1-element [r] shape
        h = reduce_head(h_raw)
        # Every (h, r) is a direct continuing_act2 owner with its own key.
        # 2026-09-02 (Fable): h == 0 with r in {1, 2} used to be a V21/V22
        # passthrough because no free-head family exists; the RIGID rows
        # (-x1-x2; -x2, -x1; x1, x2) and (-3(x1+x2)/2; -(x1+x2)/2, -(x1+x2),
        # (x1+x2)/2; x1, x2) (batch alphabet_rigid.jsonl, head forced by the
        # two inputs, handled like the residue-two ray) make v an owner.
        ctx = {"h": h, "arms": [r], "ports": 0, "child": "act2", "kind": "continuing_act2", "is_root": False}
        self.owners.append((v, ctx))
        return True, ctx, kept, ["kept_act2_1", "kept_act2_2"], cancelled

    def _decide(self, v: int, is_root: bool, h_raw: int, residual_raw: List[int], q: int,
                child_type: str, groups: List[Tuple[int, ...]], had_cancelled_group: bool,
                arms_raw: List[int], k_orig: int) -> Tuple[bool, Optional[dict]]:
        h = 0 if is_root else reduce_head(h_raw)
        n = len(residual_raw)
        cap = 2 if (is_root or child_type != "none") else 3

        def _uncovered(reason: str, repairs_tried: List[str]) -> dict:
            # Full local data for diagnosing the gap, per coordinator
            # request 2026-09-01: h (raw and reduced), the arm lengths
            # BEFORE neutralization, ports, k (active-child count), the
            # post-neutralization residual, and which repairs were tried.
            return {"vertex": v, "reason": reason, "is_root": is_root,
                    "h_raw": h_raw, "h": h, "arms_before_neutralization": sorted(arms_raw),
                    "ports": q, "k": k_orig, "residual": list(residual_raw),
                    "repairs_tried": repairs_tried}

        if n == 0:
            if child_type == "none":
                if q != 1:
                    return False, None
                g = _find_pair(groups, None)
                kind = "root" if is_root else "bottom_samepar"
                if g is not None:
                    vals = sorted(reduce6(x) for x in g)
                    return True, {"h": h, "arms": vals, "ports": 1, "child": "none", "kind": kind, "is_root": is_root}
                # No plain pair: a four-short unit is also a "neutral unit"
                # (ROUTE_CORE_OWNER_NEUTRALIZATION_REDUCTION.md Section 1)
                # and may be undone instead, giving a 4-element residual.
                g = _find_any_group(groups)
                if g is not None:
                    vals = sorted(reduce6(x) for x in g)
                    return True, {"h": h, "arms": vals, "ports": 1, "child": "none",
                                   "kind": "bottom_fourshort", "is_root": is_root}
                if had_cancelled_group:
                    # Lemma C Step 3: "use the port as a helper against one
                    # cancelled group by re-balancing that group's heads to
                    # sum to -lambda(port)" -- v stays stationary, the lone
                    # port is absorbed into one of the >=2 cancelled
                    # active-child heads instead of an undone arm unit.
                    return False, None
                self.uncovered.append(_uncovered(
                    "R-empty,k=0,q=1: no neutral unit or cancelled group to undo",
                    ["undo one plain neutral pair (none available)",
                     "undo a four-short unit (1,1,1,3)/(1,3,3,3) (none available)",
                     "rebalance the port into a >=2 cancelled active-child group (k_orig < 2, none available)"]))
                return True, self._uncovered_ctx(is_root, h, [], q, child_type)
            else:
                if q == 0:
                    g = _find_pair(groups, None)
                    kind = "root" if is_root else "continuing_samepar"
                    if g is not None:
                        vals = sorted(reduce6(x) for x in g)
                        return True, {"h": h, "arms": vals, "ports": 0, "child": child_type, "kind": kind, "is_root": is_root}
                    g = _find_any_group(groups)
                    if g is not None:
                        vals = sorted(reduce6(x) for x in g)
                        return True, {"h": h, "arms": vals, "ports": 0, "child": child_type,
                                       "kind": "continuing_fourshort", "is_root": is_root}
                    self.uncovered.append(_uncovered(
                        "R-empty,k=1,q=0: no neutral unit to undo",
                        ["undo one plain neutral pair (none available)",
                         "undo a four-short unit (1,1,1,3)/(1,3,3,3) (none available)"]))
                    return True, self._uncovered_ctx(is_root, h, [], q, child_type)
                if child_type == "free":
                    return False, None  # port(s) absorb the active child via a helper; v stays stationary
                # continuing_empty_L1 / continuing_empty_L12 / continuing_empty_V2
                # are the active-child contexts with the WIDER port cap of 3
                # (alphabet_contexts.py: `for p in (0,1,2,3): add((), p,
                # "L1"/"L12", "continuing_empty_L1"/"continuing_empty_L12")`;
                # `for p in (1,2,3): add((), p, child, "continuing_empty_V2")`
                # for child in V21, V22), unlike every other continuing_*
                # kind (cap 2).  Root still caps at 2 uniformly.
                p = recruit_ports(q, 2 if is_root else 3)
                if is_root:
                    kind = "root"
                elif child_type == "L1":
                    kind = "continuing_empty_L1"
                elif child_type == "L12":
                    kind = "continuing_empty_L12"
                else:
                    kind = "continuing_empty_V2"
                return True, {"h": h, "arms": [], "ports": p, "child": child_type, "kind": kind, "is_root": is_root}

        if n == 1:
            ell = residual_raw[0]
            if is_root:
                # The parity-restricted feasibility rule (odd residue needs
                # p in {0,2}, even residue needs p in {1,2}; root_1_p1,
                # root_3_p1, root_2_p0, root_4_p0 infeasible) is specific to
                # the BARE single-arm root cell (no active child): its width
                # parity differs once a 'free'/'L1' active child is present
                # (Lemma E's width/needs_token computation shifts by the
                # active-child extra), so the general q-p!=1 recruitment
                # applies there instead.
                if child_type == "none":
                    p = root_singleton_p(q, reduce6(ell))
                    infeasible_reason = (f"root_singleton_p(q={q}, r={reduce6(ell)}) (infeasible: p in "
                                          f"{{0,2}} for odd / {{1,2}} for even residues except r==6, "
                                          f"none satisfy q-p != 1 here)")
                else:
                    # Coordinator, 2026-09-02: root_{r}_p0_act etc. is
                    # infeasible with an active child and q==0 (no port at
                    # all to recruit) -- recruit_ports(q,2) is fine for
                    # q>=1 (always gives p>=1 there), so q==0 is the only
                    # gap.
                    p = recruit_ports(q, 2) if q >= 1 else None
                    infeasible_reason = "q==0: no port available to recruit with an active child present"
                if p is not None:
                    return True, {"h": 0, "arms": [reduce6(ell)], "ports": p, "child": child_type,
                                   "kind": "root", "is_root": True}
                # No direct feasible p: retain one plain neutral pair
                # (rule 4, root's 3-tuple repair: full sort of
                # (r,)+pair -- alphabet_contexts.py `pairs`).  Failing that,
                # a four-short unit may be retained instead (rule 3,
                # 2026-09-01: root keys root_{r}-1-1-1-3_p{p}_{tag} /
                # root_{r}-1-3-3-3_..., residual FIRST then the unit as-is,
                # NOT sorted -- alphabet_contexts.py's `(r,) + u`).  If both
                # fail, _process's act2 fallback would already have
                # resolved a k_orig>=2 case before reaching here, so this is
                # a genuine gap (k_orig<2, or the invalid k_orig==3 split).
                g = _find_pair(groups, None)
                if g is not None:
                    vals = sorted(reduce6(x) for x in g)
                    arms_ = sorted([reduce6(ell)] + vals)
                else:
                    g = _find_any_group(groups)
                    if g is None:
                        self.uncovered.append(_uncovered(
                            "root singleton: no feasible p and no neutral unit",
                            [infeasible_reason,
                             "retain one plain neutral pair (none available)",
                             "retain a four-short unit (1,1,1,3)/(1,3,3,3) (none available)",
                             f"two-input act2 fallback (k_orig={k_orig}, needs >=2 active children)"]))
                        return True, self._uncovered_ctx(True, 0, residual_raw, q, child_type)
                    # Four-short unit: residual FIRST, unit values as-is (not sorted).
                    arms_ = [reduce6(ell)] + sorted(g)
                p2 = recruit_ports(q, 2)
                return True, {"h": 0, "arms": arms_, "ports": p2, "child": child_type, "kind": "root", "is_root": True}

            if child_type == "none" and q == 0:
                if ell in (1, 2):
                    r = ell
                elif reduce_wide(ell) % 2 == 1 and (h == 0 or reduce_wide(ell) == 7):
                    # Coordinator, 2026-09-02: odd wide r in {3,5} has NO
                    # family when h>=1 ("rays only, token needed") -- only
                    # h==0, or wide==7 at any h, succeed directly.
                    return True, {"h": h, "arms": [reduce_wide(ell)], "ports": 0, "child": "none",
                                   "kind": "bottom_singleton", "is_root": False}
                else:
                    r = reduce_wide(ell)
                # r in {1,2,3,4,5,6,8} (h>=1 adds 3,5 to the repair set):
                # retain ANY neutral unit (generalized bottom_repair, rule
                # 3) -- such a vertex necessarily has one (else T-degree
                # two).  A k_orig>=2 failure would already have been
                # resolved by _process's act2 fallback (for r in
                # {1,2,4,6}), so reaching UNCOVERED here means either no
                # active children were available or r == 8 at h>=1.
                arms_ = repair_singleton_any_unit(r, groups)
                if arms_ is None:
                    self.uncovered.append(_uncovered(
                        f"singleton {r}: no neutral unit to repair with",
                        [f"retain any same-parity neutral unit or four-short unit for residual r={r} (none available)",
                         f"two-input act2/V21/V22 fallback (k_orig={k_orig}, needs odd k>=3 or even k>=2 with r in "
                         f"(1,2,4,6); r=={r})"]))
                    return True, self._uncovered_ctx(False, h, residual_raw, q, child_type)
                return True, {"h": h, "arms": arms_, "ports": 0, "child": "none", "kind": "bottom_repair", "is_root": False}

            r = reduce6(ell)
            p = recruit_ports(q, cap)
            kind = "continuing_singleton" if child_type != "none" else "bottom_singleton_ports"
            return True, {"h": h, "arms": [r], "ports": p, "child": child_type, "kind": kind, "is_root": False}

        p = recruit_ports(q, cap)
        if n == 2:
            a, b = residual_raw
            if (a % 2) != (b % 2):
                # Alphabet convention (alphabet_contexts.py): odd value
                # first, even value second -- NOT numerically sorted.
                odd_val, even_val = (a, b) if a % 2 else (b, a)
                ro, re_ = reduce6(odd_val), reduce6(even_val)
                if (not is_root and h == 0 and (ro, re_) == (1, 2) and p == 0
                        and child_type == "none" and groups):
                    # Coordinator, 2026-09-02 (normalised gate audit): the
                    # bottom context (h=0, arms (1,2), no ports, no active
                    # child) is forced-antipode -- every family for it
                    # contains the antipode of its own head.  Prefer
                    # retaining a neutral unit instead, widening the
                    # residual so this exact profile is avoided whenever
                    # there is spare freedom to spend on it.
                    g = _find_any_group(groups)
                    if g is not None:
                        vals = sorted(reduce6(x) for x in g) if len(g) == 2 else sorted(g)
                        arms_ = sorted([ro, re_] + vals)
                        return True, {"h": h, "arms": arms_, "ports": p, "child": "none",
                                       "kind": "bottom_oe_widened", "is_root": False}
                if is_root and (ro, re_) == (1, 2) and q == 0 and child_type == "none":
                    # Coordinator, 2026-09-02: root_1-2_p0_bot is infeasible
                    # (q==0, child==none only -- root_1-2_p0_act/_p0_act2,
                    # with a natural or rescued active child, are fine via
                    # the generic path below; q>=1 with child==none already
                    # works via the general recruit_ports(q,2)): retain a
                    # unit instead (p stays 0, since q==0).  A k_orig>=2
                    # failure would already have been resolved by
                    # _process's act2/odd-k fallback before reaching here.
                    g = _find_any_group(groups)
                    if g is not None:
                        vals = sorted(reduce6(x) for x in g) if len(g) == 2 else sorted(g)
                        arms_ = sorted([1, 2] + vals)
                        return True, {"h": 0, "arms": arms_, "ports": 0, "child": "none",
                                       "kind": "root", "is_root": True}
                    self.uncovered.append(_uncovered(
                        "root (1,2): p=0 infeasible, q==0, no neutral unit",
                        ["recruit two ports (q==0, none available)",
                         "retain a neutral unit (none available)",
                         f"two-input act2/odd-k fallback (k_orig={k_orig}, needs active children)"]))
                    return True, self._uncovered_ctx(True, 0, residual_raw, q, "none")
                kind = "root" if is_root else ("continuing_oe" if child_type != "none" else "bottom_oe")
                return True, {"h": h, "arms": [ro, re_], "ports": p, "child": child_type, "kind": kind, "is_root": is_root}
            kind = "root" if is_root else ("continuing_pair13" if child_type != "none" else "bottom_pair13")
            return True, {"h": h, "arms": [1, 3], "ports": p, "child": child_type, "kind": kind, "is_root": is_root}

        # n == 3: {1,3,even}
        evens = [x for x in residual_raw if x % 2 == 0]
        re = reduce6(evens[0])
        kind = "root" if is_root else ("continuing_13e" if child_type != "none" else "bottom_13e")
        return True, {"h": h, "arms": [1, 3, re], "ports": p, "child": child_type, "kind": kind, "is_root": is_root}


# --------------------------------------------------------------------------
# Per-tree driver and aggregate reporting.
# --------------------------------------------------------------------------

class RunStats:
    def __init__(self):
        self.trees = 0
        self.paths = 0
        self.counter: Counter = Counter()
        self.max_width = 0
        self.uncovered: List[dict] = []
        self.l1_pair_events: List[dict] = []
        self.l1_nonfree_child_events: List[dict] = []
        self.owner_total = 0

    def add_tree(self, owners: List[Tuple[int, dict]], sched: Scheduler):
        self.trees += 1
        self.owner_total += len(owners)
        for _v, ctx in owners:
            key = context_key(ctx)
            self.counter[key] += 1
            self.max_width = max(self.max_width, context_width(ctx))
        self.uncovered.extend(sched.uncovered)
        self.l1_pair_events.extend(sched.l1_pair_events)
        self.l1_nonfree_child_events.extend(sched.l1_nonfree_child_events)

    def add_path(self):
        self.trees += 1
        self.paths += 1

    def report(self, alphabet_keys: set) -> dict:
        missing = sorted(k for k in self.counter if k not in alphabet_keys)
        missing_repeated = sorted(((k, self.counter[k]) for k in missing if self.counter[k] > 1),
                                   key=lambda kv: (-kv[1], kv[0]))
        return {
            "trees_processed": self.trees,
            "path_trees": self.paths,
            "owner_total": self.owner_total,
            "distinct_context_keys": len(self.counter),
            "context_counter": dict(sorted(self.counter.items(), key=lambda kv: (-kv[1], kv[0]))),
            "max_width": self.max_width,
            "uncovered_count": len(self.uncovered),
            "uncovered": self.uncovered[:50],
            "l1_pair_event_count": len(self.l1_pair_events),
            "l1_pair_events": self.l1_pair_events[:50],
            "l1_nonfree_child_event_count": len(self.l1_nonfree_child_events),
            "l1_nonfree_child_events": self.l1_nonfree_child_events[:50],
            "missing_from_alphabet_count": len(missing),
            "missing_from_alphabet": missing,
            "missing_from_alphabet_repeated": missing_repeated,
        }


def schedule(parent_array: Sequence[int]) -> dict:
    """Machine-readable per-vertex schedule for the constructor.  See the
    module docstring ("schedule() output schema") for the full field-by-
    field description; summary here:

        {"n", "is_path", "root", "core_vertices",
         "owners": [{"vertex", "context_key"}, ...],
         "rows": {vertex: <family row>, ...},
         "uncovered": [...], "l1_pair_events": [...]}

    parent_array[0] is ignored (vertex 0 is the root, as in --parent)."""
    n, parent, children = tree_from_parent(parent_array)
    edges = [(v, parent[v]) for v in range(1, n)]
    deg = [0] * n
    for a, b in edges:
        deg[a] += 1
        deg[b] += 1
    if n >= 1 and max(deg, default=0) < 3:
        return {"n": n, "is_path": True, "root": None, "core_vertices": [],
                "owners": [], "rows": {}, "uncovered": [], "l1_pair_events": []}
    core = Core(n, parent, children, 0)
    carriers = load_alphabet_carriers()
    sched = Scheduler(core, carriers=carriers)
    owners = sched.run()
    return {
        "n": n,
        "is_path": False,
        "root": core.root,
        "core_vertices": sorted(core.core_set),
        "owners": [{"vertex": v, "context_key": context_key(ctx)} for v, ctx in owners],
        "rows": sched.rows,
        "uncovered": sched.uncovered,
        "l1_pair_events": sched.l1_pair_events,
        "l1_nonfree_child_events": sched.l1_nonfree_child_events,
    }


def run_one_tree(n: int, parent: List[int], children: List[List[int]], root: int, stats: RunStats,
                  print_tree: bool = False):
    core = Core(n, parent, children, root)
    sched = Scheduler(core, track_rows=False)  # CLI reporting never reads .rows
    owners = sched.run()
    stats.add_tree(owners, sched)
    if print_tree:
        print(f"  root={root} owners=" + ", ".join(f"({v}:{context_key(c)})" for v, c in sorted(owners)))


def run_parent_mode(parent_in: Sequence[int], stats: RunStats, print_tree: bool = True):
    n, parent, children = tree_from_parent(parent_in)
    edges = [(v, parent[v]) for v in range(1, n)]
    deg = [0] * n
    for a, b in edges:
        deg[a] += 1
        deg[b] += 1
    if n >= 1 and max(deg, default=0) < 3:
        stats.add_path()
        print("path")
        return
    run_one_tree(n, parent, children, 0, stats, print_tree=print_tree)


def run_random_mode(n: int, count: int, seed: int, stats: RunStats, print_tree: bool = False):
    rng = random.Random(seed)
    for _ in range(count):
        edges = random_prufer_tree(n, rng)
        root, parent, children = root_from_edges(n, edges)
        if root is None:
            stats.add_path()
            continue
        run_one_tree(n, parent, children, root, stats, print_tree=print_tree)


def run_all_mode(n: int, stats: RunStats, print_tree: bool = False):
    for seq in all_prufer_sequences(n):
        edges = prufer_decode(list(seq), n)
        root, parent, children = root_from_edges(n, edges)
        if root is None:
            stats.add_path()
            continue
        run_one_tree(n, parent, children, root, stats, print_tree=print_tree)


def main():
    ap = argparse.ArgumentParser(description="Abstract context scheduler for the free-token architecture.")
    ap.add_argument("--parent", type=int, nargs="+", help="parent array, vertex 0 is the root (parent[0] ignored)")
    ap.add_argument("--random", type=int, metavar="N", help="N vertices, random Prufer trees")
    ap.add_argument("--count", type=int, default=1, help="number of random trees (with --random)")
    ap.add_argument("--seed", type=int, default=0, help="RNG seed (with --random)")
    ap.add_argument("--all", type=int, metavar="N", help="exhaustive Prufer enumeration, N <= 9")
    ap.add_argument("--print-trees", action="store_true", help="print the per-tree owner list even in bulk modes")
    ap.add_argument("--alphabet", default=ALPHABET_PATH, help="path to alphabet_contexts.json")
    args = ap.parse_args()

    alphabet_keys = load_alphabet_keys(args.alphabet)
    stats = RunStats()

    modes = sum(x is not None for x in (args.parent, args.random, args.all))
    if modes != 1:
        ap.error("give exactly one of --parent, --random, --all")

    if args.parent is not None:
        run_parent_mode(args.parent, stats, print_tree=True)
    elif args.random is not None:
        run_random_mode(args.random, args.count, args.seed, stats, print_tree=args.print_trees)
    elif args.all is not None:
        if args.all > 9:
            ap.error("--all only supports N <= 9 (Prufer enumeration)")
        run_all_mode(args.all, stats, print_tree=args.print_trees)

    print(json.dumps(stats.report(alphabet_keys), indent=2))


if __name__ == "__main__":
    main()
