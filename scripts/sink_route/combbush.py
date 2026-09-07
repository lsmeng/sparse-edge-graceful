#!/usr/bin/env python3
"""Comb attached to a bushy dense part: root has `bush` children each with two
leaves (stationary size-2 blocks), plus the comb's top spine vertex as a child.
Spine edges direct (or subdivided by `sub`), each spine vertex one arm of `arm`
suppressed vertices.  Returns the parent array (root = -1 at index 0)."""
import sys, subprocess, json, os
from collections import Counter
PY = sys.executable
def combbush(k, arm=3, sub=0, bush=20, bushleaves=2):
    par = [-1]
    def add(p):
        par.append(p); return len(par)-1
    for _ in range(bush):
        b = add(0)
        for _ in range(bushleaves):
            add(b)
    prev = 0
    for i in range(k):
        cur = prev
        for _ in range(sub):
            cur = add(cur)
        v = add(cur); prev = v
        c = v
        for _ in range(arm+1):
            c = add(c)
    return par
def run(par, tries=200, bt=10, tmo=1500, label=""):
    P = ",".join(map(str, par)); n = len(par)
    try:
        r = subprocess.run(["nice", "-n", "15", PY, "scripts/free_token_constructor.py", "--parent", P,
                            "--tries", str(tries), "--block-time", str(bt)], capture_output=True, text=True, timeout=tmo)
    except subprocess.TimeoutExpired:
        print(f"{label} n={n}: TIMEOUT"); return None
    try:
        d = json.loads(r.stdout)
    except Exception:
        print(f"{label} n={n}: unparsable\n{r.stdout[:600]}\n{r.stderr[-600:]}"); return None
    st = d.get("statistics") or {}
    keys = ["degree_two", "max_magnitude", "magnitude_over_D1", "special_labels", "T1_symbolic_tokens",
            "T2_pairings", "T2_solve_failed", "T1_downgraded", "max_live_parameters", "max_pending_tokens",
            "lattice_M", "fallback_cells", "lemma_gaps", "subtree_retries", "family_second_choice", "third_pending_token"]
    print(f"{label} n={n}: ok={d.get('ok')} " + " ".join(f"{kk}={st.get(kk)}" for kk in keys if kk in st))
    if not d.get("ok"): print("   failure:", d.get("failure"))
    notes = d.get("notes") or []
    if notes: print("   notes:", Counter(notes).most_common(8))
    toks = d.get("tokens") or []
    if toks: print("   tokens:", [(t.get("vertex"), t.get("values")) for t in toks][:14])
    return d
if __name__ == "__main__":
    arm, sub = int(sys.argv[1]), int(sys.argv[2])
    for k in [int(x) for x in sys.argv[3].split(",")]:
        bush = int(sys.argv[4]) * k if len(sys.argv) > 4 else 20 * k
        par = combbush(k, arm, sub, bush)
        if len(par) % 2 == 0:
            par = combbush(k, arm, sub, bush + 1)
        d = run(par, label=f"comb+bush arm={arm} sub={sub} k={k} bush={bush}")
        if d and d.get("ok"):
            json.dump(d, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), f"cert_arm{arm}_sub{sub}_k{k}.json"), "w"))
