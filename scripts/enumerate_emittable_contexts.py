#!/usr/bin/env python3
"""Abstract enumeration of every context key the scheduler can emit.

For every abstract local state of a core vertex v -- head-chain length h
(0 = direct parent edge), multiset of arm lengths, number of ports, and a
multiset of active-child TYPES -- a concrete tree fragment realising that
state is built and ``context_scheduler.schedule`` is run on it; the key
emitted at v (or the passthrough marker) is recorded.  The union over all
states is the emittable set E.  Root states are enumerated with v = root.

Child types and the subtrees realising them (all bottom-up decisions of the
child depend only on its own subtree, so the realisation is faithful):

  free3     owner child with a free head: one arm of length 3 and one leaf
            port (h0_3_p1_bot); a branch vertex, so it is not suppressed
  freeH     owner child reached by a subdivided edge of length 2 (its head
            chain), with one arm of length 3 and one leaf (h2_3_p1_bot)
  L1        arm 1, no port, one free active grandchild (zero-spare letter)
  L11       arm 1 and one leaf port ((1; one port) bottom)
  L12       arms 1 and 2, no ports (the (1,2) bottom)
  V21/V22   arm 1 (resp. 2), no ports, two free active grandchildren
  act2      subdivided edge of length 1, arm 1, two free active grandchildren
            (h1_1_p0_act2, an owner with two kept inputs)
  stat      a stationary internal child (two leaf children) -- a port
  statarm   a subdivided edge of length ell ending at a stationary vertex --
            an arm of v (enumerated through the arm lengths with a flag)

usage: enumerate_emittable_contexts.py [--max-arms 3] [--max-children 2]
                                       [--out data/alphabet_contexts_emittable.json]
"""
import argparse
import itertools
import json
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import context_scheduler as cs  # noqa: E402

DATA = os.path.normpath(os.path.join(HERE, "..", "data"))


class Builder:
    def __init__(self):
        self.parent = [-1]

    def add(self, p):
        self.parent.append(p)
        return len(self.parent) - 1

    def chain(self, p, length):
        """subdivide: returns the lower endpoint after `length` degree-2 vertices"""
        for _ in range(length):
            p = self.add(p)
        return p

    def leaf(self, p):
        return self.add(p)

    def arm(self, p, length, stationary_end=False):
        q = self.chain(p, length)
        end = self.add(q)
        if stationary_end:
            self.leaf(end)
            self.leaf(end)
        return end

    def child(self, p, kind):
        if kind == "free":
            c = self.add(p); self.arm(c, 3); self.leaf(c); self.leaf(c)
        elif kind == "free3":
            # a branch vertex with one arm of length 3 and one leaf port
            c = self.add(p); self.arm(c, 3); self.leaf(c)
        elif kind == "freeH":
            c = self.chain(p, 2); c = self.add(c); self.arm(c, 3); self.leaf(c)
        elif kind == "L1":
            c = self.add(p); self.arm(c, 1); self.child(c, "free3")
        elif kind == "L11":
            c = self.add(p); self.arm(c, 1); self.leaf(c)
        elif kind == "L12":
            c = self.add(p); self.arm(c, 1); self.arm(c, 2)
        elif kind == "V21":
            c = self.add(p); self.arm(c, 1); self.child(c, "free3"); self.child(c, "free3")
        elif kind == "V22":
            c = self.add(p); self.arm(c, 2); self.child(c, "free3"); self.child(c, "free3")
        elif kind == "act2":
            c = self.chain(p, 1); c = self.add(c); self.arm(c, 1); self.child(c, "free3"); self.child(c, "free3")
        elif kind == "act2h2":
            # the forced-antipode two-input owner h2_1_p0_act2 (head chain 2)
            c = self.chain(p, 2); c = self.add(c); self.arm(c, 1); self.child(c, "free3"); self.child(c, "free3")
        elif kind == "stat":
            c = self.add(p); self.leaf(c); self.leaf(c)
        else:
            raise ValueError(kind)
        return c


CHILD_TYPES = ["free3", "freeH", "L1", "L11", "L12", "V21", "V22", "act2", "act2h2"]


def state_fragment(is_root, h, arms, statarms, q, kids):
    """Build the fragment; return (parent_array, v)."""
    b = Builder()
    if is_root:
        v = 0
    else:
        # root 0 is a branch vertex: two leaves plus the edge towards v
        b.leaf(0); b.leaf(0)
        v = b.chain(0, h)
        v = b.add(v)
    for ell in arms:
        b.arm(v, ell)
    for ell in statarms:
        b.arm(v, ell, stationary_end=True)
    for _ in range(q):
        b.leaf(v)
    kid_roots = []
    for k in kids:
        first = len(b.parent)
        b.child(v, k)
        kid_roots.append(first)
    return b.parent, v, kid_roots


def run_state(is_root, h, arms, statarms, q, kids):
    if is_root and len(arms) + len(statarms) + q + len(kids) < 3:
        return None, None, []      # the root must be a branch vertex
    parent, v, kid_roots = state_fragment(is_root, h, arms, statarms, q, kids)
    n = len(parent)
    deg = Counter()
    for u in range(1, n):
        deg[u] += 1; deg[parent[u]] += 1
    if not deg or max(deg.values()) < 3:
        return None, None, []
    res = cs.schedule(parent)
    rows = res["rows"] if isinstance(res["rows"], dict) else {}
    row = rows.get(v)
    if row is None:
        # rows may be keyed by str
        row = rows.get(str(v))
    keys = {o["context_key"] for o in res["owners"]}
    if row is None:
        return None, keys, []
    vkey = row.get("context_key")
    # the owner nearest to v inside each child subtree, read off by descending
    # from the subtree root until a vertex that owns a context is met
    owner_of = {}
    for o in res["owners"]:
        u = o.get("vertex")
        if u is not None:
            owner_of[u] = o["context_key"]
    children = {}
    for u in range(1, len(parent)):
        children.setdefault(parent[u], []).append(u)
    pairs = []
    if vkey:
        for r in kid_roots:
            stack, seen = [r], set()
            while stack:
                u = stack.pop()
                if u in seen:
                    continue
                seen.add(u)
                if u in owner_of:
                    pairs.append((owner_of[u], vkey))
                    continue
                stack.extend(children.get(u, ()))
    return (vkey, row.get("passthrough")), keys, pairs


def multisets(items, maxsize):
    out = [()]
    for k in range(1, maxsize + 1):
        out.extend(itertools.combinations_with_replacement(items, k))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-arms", type=int, default=3)
    ap.add_argument("--arm-lengths", default="1,2,3,4,5,6,7,8")
    ap.add_argument("--max-children", type=int, default=2)
    ap.add_argument("--max-ports", type=int, default=3)
    ap.add_argument("--max-head", type=int, default=6)
    ap.add_argument("--out", default=os.path.join(DATA, "alphabet_contexts_emittable.json"))
    ap.add_argument("--report", default=os.path.join(DATA, "emittable_report.md"))
    ap.add_argument("--extra", action="store_true",
                    help="also enumerate large arm multisets (size 4-6 over lengths 1..4) with <=1 child")
    a = ap.parse_args()
    lengths = [int(x) for x in a.arm_lengths.split(",")]
    emitted = Counter()          # key -> count of states
    passthrough = Counter()
    all_keys = Counter()
    where = {}
    states = 0
    pairs = set()
    arm_sets = multisets(lengths, a.max_arms)
    kid_sets = multisets(CHILD_TYPES, a.max_children)
    plan = []
    for is_root in (False, True):
        heads = [0] if is_root else list(range(0, a.max_head + 1))
        for h in heads:
            for arms in arm_sets:
                for q in range(0, a.max_ports + 1):
                    for kids in kid_sets:
                        plan.append((is_root, h, arms, (), q, kids))
    # arms ending at stationary vertices: one such arm, few other arms
    for is_root in (False, True):
        heads = [0] if is_root else [0, 1, 2]
        for h in heads:
            for ell in lengths:
                for arms in multisets(lengths, 2):
                    for q in range(0, 3):
                        for kids in multisets(CHILD_TYPES, 1):
                            plan.append((is_root, h, arms, (ell,), q, kids))
    if a.extra:
        small = [1, 2, 3, 4]
        for is_root in (False, True):
            heads = [0] if is_root else list(range(0, a.max_head + 1))
            for h in heads:
                for k in (4, 5, 6):
                    for arms in itertools.combinations_with_replacement(small, k):
                        for q in range(0, 3):
                            for kids in multisets(CHILD_TYPES, 1):
                                plan.append((is_root, h, arms, (), q, kids))
    print(len(plan), "abstract states", flush=True)
    crashes = []
    for st in plan:
        try:
            r, keys, prs = run_state(*st)
            pairs.update(prs)
        except Exception as exc:  # scheduler robustness bug: record and go on
            crashes.append((st, f"{type(exc).__name__}: {exc}"))
            r, keys = None, None
        states += 1
        if keys:
            all_keys.update(keys)
        if r is None:
            continue
        key, pt = r
        if key:
            emitted[key] += 1
            where.setdefault(key, st)
        if pt:
            passthrough[pt] += 1
        if states % 20000 == 0:
            print(states, "states;", len(emitted), "distinct keys", flush=True)
    E = set(emitted) | {k for k in all_keys if k}
    # compare with the generated alphabet and the catalogue
    from run_alphabet_batch import key as ctx_key
    alphabet = json.load(open(os.path.join(DATA, "alphabet_contexts.json")))
    alpha = {ctx_key(c): c for c in alphabet}
    cat = json.load(open(os.path.join(DATA, "alphabet_families.json")))
    not_in_alpha = sorted(k for k in E if k not in alpha)
    no_family = sorted(k for k in E if k in alpha and k not in cat)
    out = [alpha[k] for k in sorted(E) if k in alpha]
    json.dump(out, open(a.out, "w"))
    lines = []
    lines.append(f"# Emittable contexts (abstract enumeration, {states} states)\n")
    lines.append(f"* distinct keys emitted at the target vertex: {len(emitted)}; "
                 f"all keys seen in fragments: {len(E)}")
    lines.append(f"* passthrough markers seen at the target: {dict(passthrough)}")
    lines.append(f"* keys NOT in data/alphabet_contexts.json: {len(not_in_alpha)}")
    for k in not_in_alpha:
        lines.append(f"    - {k}  (state {where.get(k)})")
    lines.append(f"* emittable keys WITHOUT a family in data/alphabet_families.json: {len(no_family)}")
    wc = Counter(alpha[k]['width'] for k in no_family)
    lines.append(f"    widths: {sorted(wc.items())}")
    kc = Counter((alpha[k]['kind'], str(alpha[k]['active'])) for k in no_family)
    lines.append(f"    by kind/active: {kc.most_common()}")
    for k in no_family:
        lines.append(f"    - {k}  width {alpha[k]['width']}  (state {where.get(k)})")
    lines.append(f"* alphabet keys never emitted (slack): {sum(1 for k in alpha if k not in E)} of {len(alpha)}")
    lines.append(f"* scheduler crashes: {len(crashes)}")
    seen = Counter(msg for _, msg in crashes)
    for msg, cnt in seen.most_common(10):
        st = next(st for st, m in crashes if m == msg)
        lines.append(f"    - {cnt}x {msg}  e.g. state {st}")
    json.dump(sorted(pairs), open(os.path.join(DATA, "emittable_pairs.json"), "w"))
    lines.append(f"* realizable (child, parent) owner pairs recorded: {len(pairs)}")
    open(a.report, "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
