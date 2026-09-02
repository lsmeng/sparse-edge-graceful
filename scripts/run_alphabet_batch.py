#!/usr/bin/env python3
"""Batch driver: run symbolic_free_token_cpsat.py over the context alphabet.

For every context in data/alphabet_contexts.json try, in order, a list of
(denominator, internal-parameter count, coefficient bound) settings until a
family is found or the list is exhausted.  Results are appended to a JSONL
file so the batch can be resumed.
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable

SETTINGS = [
    # (denominator, internal params, coef bound)
    (1, 1, 3), (2, 1, 3), (3, 1, 3), (1, 2, 4), (2, 2, 4), (3, 2, 4), (4, 2, 4), (6, 2, 6), (12, 2, 12),
]


def row_specs(ctx):
    """Return the list of --rows arguments (top row first)."""
    parts = []
    if ctx.get("kind") == "root":
        parts.append("root")
    if ctx.get("head", 0):
        parts.append(f"head={ctx['head']}")
    if ctx["arms"]:
        parts.append("arms=" + ",".join(str(a) for a in ctx["arms"]))
    if ctx["ports"]:
        parts.append(f"ports={ctx['ports']}")
    child = ctx["active"]
    if child in (True, "free"):
        parts += ["active", "input"]
        return [";".join(parts)]
    if child == "L1":
        parts.append("active")
        return [";".join(parts), "arms=1;active;input"]
    if child == "L11":
        parts.append("active")
        return [";".join(parts), "arms=1;ports=1"]
    if child == "L12":
        parts.append("active")
        return [";".join(parts), "arms=1,2"]
    if child == "V21":
        parts.append("active")
        return [";".join(parts), "arms=1;active2;input2"]
    if child == "V22":
        parts.append("active")
        return [";".join(parts), "arms=2;active2;input2"]
    if child == "act2":
        parts += ["active2", "input2"]
        return [";".join(parts)]
    if child == "A2":
        # the forced-antipode two-input owner h2_1_p0_act2 joined into its parent
        parts.append("active")
        return [";".join(parts), "head=2;arms=1;active2;input2"]
    if child == "L1A2":
        # three rows: parent, the residue-one letter, the two-input owner
        parts.append("active")
        return [";".join(parts), "arms=1;active", "head=2;arms=1;active2;input2"]
    return [";".join(parts) if parts else "ports=0"]


def key(ctx):
    child = ctx["active"]
    tag = {False: "bot", "none": "bot", True: "act", "free": "act", "L1": "L1", "L11": "L11", "L12": "L12", "V21": "V21", "V22": "V22", "act2": "act2", "A2": "A2", "L1A2": "L1A2"}[child]
    pre = "root" if ctx.get("kind") == "root" else f"h{ctx.get('head', 0)}"
    return f"{pre}_{'-'.join(map(str, ctx['arms'])) or 'none'}_p{ctx['ports']}_{tag}"


a_token_rank = 3
a_clean = False
a_forbid_y = False
a_input_in_token = False
a_two_tokens = False
a_all_inputs = False
a_port_in_token = False
a_forbid_port = False
a_no_head_only = False
a_forced_only_antipode = False
a_settings_parallel = False


def _run_setting(ctx, setting, time_limit, workers, forbid_antipode_x):
    """One (denominator, internal, coefficient bound) run; returns (attempt, payload)."""
    L, u, K = setting
    specs = row_specs(ctx)
    cmd = [PY, os.path.join(HERE, "symbolic_free_token_cpsat.py")]
    for spec in specs:
        cmd += ["--rows", spec]
    fd, tmp = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    cmd += ["--denominator", str(L), "--internal", str(u),
           "--coef-bound", str(K), "--time-limit", str(time_limit), "--workers", str(workers),
           "--head-mult-free", "--json", tmp]
    if a_two_tokens:
        cmd += ["--token-rank", "any2", "--two-tokens"]
    elif not ctx["needs_token"]:
        cmd.append("--no-token")
    else:
        cmd += ["--token-rank", str(a_token_rank)]
    if forbid_antipode_x and ctx["active"] not in (False, "none", "L11", "L12"):
        cmd.append("--forbid-antipode-x")
    if a_clean:
        cmd += ["--no-head-only", "--forced-only-antipode"]
    if a_no_head_only and not a_clean:
        cmd.append("--no-head-only")
    if a_forced_only_antipode and not a_clean:
        cmd.append("--forced-only-antipode")
    if a_forbid_y:
        cmd.append("--forbid-antipode-y")
    if a_input_in_token:
        cmd.append("--input-in-token")
    if a_all_inputs:
        cmd.append("--all-inputs-in-token")
    if a_port_in_token:
        cmd.append("--port-in-token")
    if a_forbid_port:
        cmd.append("--forbid-antipode-port")
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=time_limit + 120)
        err = (res.stderr or "")[-400:]
    except subprocess.TimeoutExpired:
        err = "timeout"
    status = "ERROR"
    payload = None
    try:
        if os.path.getsize(tmp) > 0:
            payload = json.load(open(tmp))
            status = payload.get("status", "?")
    except Exception:
        payload = None
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass
    if status == "ERROR":
        payload = {"stderr": err}
    return {"denominator": L, "internal": u, "coef": K, "status": status}, payload


def run_one(ctx, time_limit, workers, forbid_antipode_x):
    """Try the nine settings in order and return the first family found.

    With ``--settings-parallel`` the nine are run concurrently and the one of
    lowest index that succeeded is returned, which is the same answer and is
    up to nine times faster on contexts where most settings are infeasible.
    """
    if a_settings_parallel:
        with ThreadPoolExecutor(len(SETTINGS)) as ex:
            futs = [ex.submit(_run_setting, ctx, st, time_limit, workers, forbid_antipode_x)
                    for st in SETTINGS]
            res = [f.result() for f in futs]
        attempts = [r[0] for r in res]
        for st, (att, payload) in zip(SETTINGS, res):
            if att["status"] in ("OPTIMAL", "FEASIBLE"):
                return {"key": key(ctx), "ctx": ctx, "found": True,
                        "attempts": attempts, "family": payload}
        return {"key": key(ctx), "ctx": ctx, "found": False, "attempts": attempts, "family": None}
    specs = row_specs(ctx)
    attempts = []
    for L, u, K in SETTINGS:
        cmd = [PY, os.path.join(HERE, "symbolic_free_token_cpsat.py")]
        for spec in specs:
            cmd += ["--rows", spec]
        fd, tmp = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        cmd += ["--denominator", str(L), "--internal", str(u),
               "--coef-bound", str(K), "--time-limit", str(time_limit), "--workers", str(workers),
               "--head-mult-free", "--json", tmp]
        if a_two_tokens:
            cmd += ["--token-rank", "any2", "--two-tokens"]
        elif not ctx["needs_token"]:
            cmd.append("--no-token")
        else:
            cmd += ["--token-rank", str(a_token_rank)]
        if forbid_antipode_x and ctx["active"] not in (False, "none", "L11", "L12"):
            cmd.append("--forbid-antipode-x")
        if a_clean:
            cmd += ["--no-head-only", "--forced-only-antipode"]
        if a_no_head_only and not a_clean:
            cmd.append("--no-head-only")
        if a_forced_only_antipode and not a_clean:
            cmd.append("--forced-only-antipode")
        if a_forbid_y:
            cmd.append("--forbid-antipode-y")
        if a_input_in_token:
            cmd.append("--input-in-token")
        if a_all_inputs:
            cmd.append("--all-inputs-in-token")
        if a_port_in_token:
            cmd.append("--port-in-token")
        if a_forbid_port:
            cmd.append("--forbid-antipode-port")
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=time_limit + 120)
            err = (res.stderr or "")[-400:]
        except subprocess.TimeoutExpired:
            err = "timeout"
        status = "ERROR"
        payload = None
        try:
            if os.path.getsize(tmp) > 0:
                payload = json.load(open(tmp))
                status = payload.get("status", "?")
        except Exception:
            payload = None
        finally:
            try:
                os.remove(tmp)
            except OSError:
                pass
        if status == "ERROR":
            payload = {"stderr": err}
        attempts.append({"denominator": L, "internal": u, "coef": K, "status": status})
        if status in ("OPTIMAL", "FEASIBLE"):
            return {"key": key(ctx), "ctx": ctx, "found": True, "attempts": attempts, "family": payload}
    return {"key": key(ctx), "ctx": ctx, "found": False, "attempts": attempts, "family": None}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--contexts", default=os.path.join(HERE, "..", "data", "alphabet_contexts.json"))
    ap.add_argument("--out", default=os.path.join(HERE, "..", "data", "alphabet_batch.jsonl"))
    ap.add_argument("--time", type=float, default=300)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--parallel", type=int, default=6)
    ap.add_argument("--max-width", type=int, default=99)
    ap.add_argument("--kinds", default="")
    ap.add_argument("--forbid-antipode-x", action="store_true")
    ap.add_argument("--token-rank", default="3", help="3, 2 or any2")
    ap.add_argument("--clean", action="store_true", help="require no head-only labels and forced labels limited to -x")
    ap.add_argument("--forbid-antipode-y", action="store_true", help="forbid any label identically equal to minus the exposed head")
    ap.add_argument("--input-in-token", action="store_true", help="require the pinned input label to be a token member (any2 rank)")
    ap.add_argument("--no-head-only", action="store_true", help="child-side cleanliness only")
    ap.add_argument("--forced-only-antipode", action="store_true", help="parent-side cleanliness only")
    ap.add_argument("--settings-parallel", action="store_true",
                    help="run the nine settings of one context concurrently")
    ap.add_argument("--port-in-token", action="store_true",
                    help="a port label must be a token member (port standing for a pinned child)")
    ap.add_argument("--forbid-antipode-port", action="store_true",
                    help="no label is identically minus a port label")
    ap.add_argument("--all-inputs-in-token", action="store_true", help="every pinned input must be a token member")
    ap.add_argument("--reverse", action="store_true", help="process the widest contexts first (to run a second driver from the other end)")
    ap.add_argument("--two-tokens", action="store_true", help="mirrors + two any2 tokens; runs only contexts with needs_token False (even non-head count)")
    a = ap.parse_args()
    global a_token_rank, a_clean, a_forbid_y, a_input_in_token, a_two_tokens, a_no_head_only, a_forced_only_antipode, a_all_inputs
    global a_port_in_token, a_forbid_port, a_settings_parallel
    a_token_rank = a.token_rank
    a_clean = a.clean
    a_forbid_y = a.forbid_antipode_y
    a_input_in_token = a.input_in_token
    a_two_tokens = a.two_tokens
    a_all_inputs = a.all_inputs_in_token
    a_no_head_only = a.no_head_only
    a_forced_only_antipode = a.forced_only_antipode
    a_port_in_token = a.port_in_token
    a_forbid_port = a.forbid_antipode_port
    a_settings_parallel = a.settings_parallel
    ctxs = json.load(open(a.contexts))
    done = set()
    if os.path.exists(a.out):
        for line in open(a.out):
            try:
                done.add(json.loads(line)["key"])
            except Exception:
                pass
    todo = [c for c in ctxs if key(c) not in done and c["width"] <= a.max_width
            and (not a.kinds or c["kind"] in a.kinds.split(","))
            and (not a.two_tokens or not c["needs_token"])]
    todo.sort(key=lambda c: c["width"], reverse=a.reverse)
    print(f"{len(todo)} contexts to run ({len(done)} already done)")
    with ThreadPoolExecutor(a.parallel) as ex, open(a.out, "a") as fh:
        futs = {ex.submit(run_one, c, a.time, a.workers, a.forbid_antipode_x): c for c in todo}
        for fut in as_completed(futs):
            r = fut.result()
            fh.write(json.dumps(r) + "\n")
            fh.flush()
            print(r["key"], "FOUND" if r["found"] else "none", [x["status"] for x in r["attempts"]], flush=True)


if __name__ == "__main__":
    main()
