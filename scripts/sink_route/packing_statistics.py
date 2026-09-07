#!/usr/bin/env python3
"""Self-contained counting task on rooted trees: degree-two skeleton, owner
tokens (upper bound t), direct absorption capacity of blocks (Change 1 rule:
a block at every vertex that is not degree-two and not an arm leaf, including
owners and owner-adjacent helper vertices), and disjoint vertical 5-chains of
gadget-usable ordinary vertices (r in {2,4}), packed greedily bottom-up.
See task spec in the conversation for full definitions.
"""
import sys, os, json

HERE = os.path.dirname(os.path.abspath(__file__))
SCRATCH_FRESH = os.path.normpath(os.path.join(HERE, "..", "..", "data", "sink_route"))
ANTIMAGIC_SCRIPTS = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, SCRATCH_FRESH)
sys.path.insert(0, ANTIMAGIC_SCRIPTS)

from combbush import combbush          # noqa: E402
import context_scheduler as cs          # noqa: E402
import free_token_constructor as ftc    # noqa: E402


# --------------------------------------------------------------------------
# Tree utilities
# --------------------------------------------------------------------------

def build_tree(parent):
    """parent[0] is ignored (root); parent[v] for v>=1 is v's parent."""
    n = len(parent)
    children = [[] for _ in range(n)]
    for v in range(1, n):
        children[parent[v]].append(v)
    deg = [0] * n
    for v in range(1, n):
        p = parent[v]
        deg[v] += 1
        deg[p] += 1
    return n, children, deg


def capacity(r):
    """0 if r in {0,1,2,4}; else largest k with r-3k in {0} or >=2."""
    if r < 0:
        return 0
    k0 = r // 3
    rem0 = r - 3 * k0
    if rem0 != 1:
        return k0
    return k0 - 1 if k0 >= 1 else 0


def classify(n, children, parent, deg, owner_vertices):
    """Change-1 block rule.

    A block exists at every vertex that is not degree-two and not an arm
    leaf (a leaf whose parent is degree-two) -- this includes owners and
    vertices with an owner child.  Block size r = number of children that
    are leaves/ordinary vertices (not owners, not degree-two, not arm
    leaves), minus 3 if the vertex is an owner, minus 2 if it has an owner
    child but is not itself an owner, floored at 0.

    Chain-usable vertices are unchanged: ordinary (not degree-two, not an
    arm leaf, not an owner), with no owner child, and r in {2,4}.
    """
    is_owner = [False] * n
    for v in owner_vertices:
        is_owner[v] = True

    is_arm_leaf = [False] * n
    for v in range(n):
        if deg[v] == 1 and v != 0 and deg[parent[v]] == 2:
            is_arm_leaf[v] = True

    # "skeleton_like": excluded from the leaf/ordinary qualifying-child set.
    skeleton_like = [deg[v] == 2 or is_arm_leaf[v] or is_owner[v] for v in range(n)]

    has_block = [(deg[v] != 2) and not is_arm_leaf[v] for v in range(n)]

    has_owner_child = [any(is_owner[c] for c in children[v]) for v in range(n)]

    ordinary_final = [(not skeleton_like[v]) and (not has_owner_child[v]) for v in range(n)]

    r = [0] * n
    for v in range(n):
        if has_block[v]:
            raw = sum(1 for c in children[v] if not skeleton_like[c])
            if is_owner[v]:
                raw -= 3
            elif has_owner_child[v]:
                raw -= 2
            r[v] = max(raw, 0)
    return has_block, ordinary_final, r


def pack_chains(n, children, parent, ordinary_final, r):
    """Greedy bottom-up packing of disjoint vertical 5-chains of
    gadget-usable (r in {2,4}) ordinary vertices.  Returns chain count."""
    eligible = [ordinary_final[v] and r[v] in (2, 4) for v in range(n)]
    used = [False] * n
    chain_len = [0] * n
    witness = [-1] * n

    # post-order (children before parents) via explicit stack
    order = []
    stack = [(0, False)]
    while stack:
        v, processed = stack.pop()
        if processed:
            order.append(v)
        else:
            stack.append((v, True))
            for c in children[v]:
                stack.append((c, False))

    count = 0
    for v in order:
        if not eligible[v]:
            chain_len[v] = 0
            continue
        best_len, best_child = 0, -1
        for c in children[v]:
            if eligible[c] and not used[c] and chain_len[c] > best_len:
                best_len, best_child = chain_len[c], c
        chain_len[v] = 1 + best_len
        witness[v] = best_child
        if chain_len[v] >= 5:
            count += 1
            cur = v
            used[cur] = True
            for _ in range(4):
                cur = witness[cur]
                used[cur] = True
                chain_len[cur] = 0
            chain_len[v] = 0
    return count


def analyze_tree(name, parent):
    n = len(parent)
    par = list(parent)
    par[0] = 0  # schedule() ignores index 0; vertex 0 is root by convention
    sched = cs.schedule(par)
    owners = [o["vertex"] for o in sched["owners"]]
    t = len(owners)

    n2, children, deg = build_tree(parent)
    assert n2 == n
    has_block, ordinary_final, r = classify(n, children, parent, deg, owners)
    D = sum(1 for v in range(n) if deg[v] == 2)
    direct_total = sum(capacity(r[v]) for v in range(n) if has_block[v])
    chains = pack_chains(n, children, parent, ordinary_final, r)
    capacity_total = direct_total + 2 * chains
    holds = capacity_total >= t
    ratio = (capacity_total / t) if t > 0 else float("inf")
    denom = D + 1
    n_over_Dp1 = n / denom if denom > 0 else float("inf")
    return {
        "name": name, "n": n, "D": D, "t": t,
        "direct": direct_total, "chains": chains,
        "capacity_total": capacity_total, "holds": holds,
        "ratio": ratio, "n_over_Dp1": n_over_Dp1,
    }


# --------------------------------------------------------------------------
# Families
# --------------------------------------------------------------------------

def gen_combbush():
    out = []
    for k in (5, 9, 15):
        bush = 12 * k
        par = combbush(k, arm=3, sub=0, bush=bush)
        if len(par) % 2 == 0:
            par = combbush(k, arm=3, sub=0, bush=bush + 1)
        out.append((f"combbush_k{k}", par))
    return out


def _add_complete_binary_subtree(par, parent_of_root, d):
    """Append a complete binary tree of depth d (root at depth 0, leaves at
    depth d, every internal vertex exactly two children) as a new subtree
    whose root is a child of parent_of_root.  Returns nothing; mutates par."""
    def add(p):
        par.append(p)
        return len(par) - 1
    root = add(parent_of_root)
    frontier = [root]
    for _level in range(d):
        new_frontier = []
        for v in frontier:
            new_frontier.append(add(v))
            new_frontier.append(add(v))
        frontier = new_frontier


def _add_comb(par, root, k, arm=3):
    """Comb part copied from combbush.py: a spine of k vertices joined by
    direct edges, the first spine vertex a child of `root`, each spine
    vertex carrying one arm of `arm` suppressed degree-two vertices plus a
    leaf."""
    def add(p):
        par.append(p)
        return len(par) - 1
    prev = root
    for _i in range(k):
        v = add(prev)
        prev = v
        c = v
        for _ in range(arm + 1):
            c = add(c)


def gen_comb_binary():
    """Root 0 has two children heading complete binary subtrees of depth d,
    plus a third child that is the top of a comb (spine of k teeth, each
    with a 3-vertex suppressed arm and a leaf).  If n ends up even, add one
    more leaf to the root."""
    out = []
    for d in (7, 8, 9):
        for k in (5, 9, 15):
            par = [-1]
            _add_complete_binary_subtree(par, 0, d)
            _add_complete_binary_subtree(par, 0, d)
            _add_comb(par, 0, k, arm=3)
            if len(par) % 2 == 0:
                par.append(0)
            out.append((f"combbin_d{d}_k{k}", par))
    return out


def gen_sparse_trees():
    return list(ftc.sparse_trees([101, 201, 401], 3, 1, 25))


def main():
    families = [
        ("combbush", gen_combbush()),
        ("comb_binary", gen_comb_binary()),
        ("sparse_trees", gen_sparse_trees()),
    ]

    all_rows = []
    lines = []
    summary = {}
    for fam_name, trees in families:
        fam_rows = []
        for name, par in trees:
            row = analyze_tree(name, par)
            fam_rows.append(row)
            all_rows.append(row)
            lines.append(
                f"{row['name']:24s} n={row['n']:4d} D={row['D']:4d} t={row['t']:3d} "
                f"direct={row['direct']:3d} chains={row['chains']:3d} "
                f"cap={row['capacity_total']:3d} holds={row['holds']}"
            )
        ratios = [row["ratio"] for row in fam_rows if row["t"] > 0]
        min_ratio = min(ratios) if ratios else None
        holding_n_over = [row["n_over_Dp1"] for row in fam_rows if row["holds"]]
        min_n_over_Dp1 = min(holding_n_over) if holding_n_over else None
        summary[fam_name] = {
            "min_ratio_cap_over_t": min_ratio,
            "min_n_over_Dp1_where_holds": min_n_over_Dp1,
            "all_hold": all(row["holds"] for row in fam_rows),
        }

    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results2.json")
    with open(out_path, "w") as f:
        json.dump({"rows": all_rows, "summary": summary}, f, indent=2)

    print("\n".join(lines))
    print()
    print("Summary (per family):")
    for fam_name, _ in families:
        s = summary[fam_name]
        mr = f"{s['min_ratio_cap_over_t']:.3f}" if s["min_ratio_cap_over_t"] is not None else "n/a"
        mn = f"{s['min_n_over_Dp1_where_holds']:.3f}" if s["min_n_over_Dp1_where_holds"] is not None else "none held"
        print(f"  {fam_name:14s} min(cap/t)={mr}  min n/(D+1) where holds={mn}  all_hold={s['all_hold']}")
    print(f"\nJSON: {out_path}")


if __name__ == "__main__":
    main()
