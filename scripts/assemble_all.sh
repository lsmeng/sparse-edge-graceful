#!/bin/bash
# Re-assemble the free-token catalogue from every batch file, verify it with
# the independent checker, run the menu gate, and reconcile with the
# emittable context set.  Usage: scripts/assemble_all.sh [SCRATCH_DIR]
set -u
cd "$(dirname "$0")/.."
S=${1:-/tmp}
python3 - <<'EOF' > "$S/assemble_all.txt" 2>&1
import glob, os, subprocess, sys
b='data/batches/'
order=[]
def add(pat):
    for f in sorted(glob.glob(b+pat)):
        if f not in order and os.path.getsize(f)>0: order.append(f)
add('alphabet_manual.jsonl'); add('alphabet_units.jsonl'); add('alphabet_special.jsonl'); add('alphabet_rigid.jsonl'); add('alphabet_act2twonofa_any2.jsonl')
add('alphabet_gatefixp_*.jsonl'); add('alphabet_clean*_r3.jsonl'); add('alphabet_fa12b_*.jsonl')
add('alphabet_*_r3.jsonl'); add('alphabet_r3.jsonl')
add('alphabet_clean*_any2.jsonl'); add('alphabet_act2two_any2.jsonl'); add('alphabet_*_any2.jsonl'); add('alphabet_any2.jsonl')
add('alphabet_*_r2.jsonl'); add('alphabet_r2.jsonl'); add('alphabet_*.jsonl')
add('local_*.jsonl'); add('ws_*.jsonl'); add('h2_*.jsonl'); add('insert_*.jsonl'); add('neutral_*.jsonl')
print(len(order),'files')
r=subprocess.run(['python3','scripts/assemble_alphabet_catalogue.py',*order,'--out','data/alphabet_families.json.tmp'],capture_output=True,text=True)
print(r.stdout[-4000:]); print(r.stderr[-2000:])
sys.exit(r.returncode)
EOF
if [ $? -ne 0 ]; then echo "assembly failed"; tail -20 "$S/assemble_all.txt"; exit 1; fi
python3 scripts/check_alphabet_families.py data/alphabet_families.json.tmp > "$S/check_all.txt" 2>&1
tail -1 "$S/check_all.txt"
if grep -q " 0 FAIL" "$S/check_all.txt"; then
  mv data/alphabet_families.json.tmp data/alphabet_families.json
  echo "catalogue replaced"
else
  echo "checker reported failures; catalogue NOT replaced"; exit 1
fi
python3 scripts/check_lookahead_gate.py data/alphabet_families.json --menu --json "$S/gate_menu_all.json" > "$S/gate_menu_all.txt" 2>&1
grep -E "families:|chosen-family gate|EVERY|menu gate" "$S/gate_menu_all.txt"
python3 scripts/build_variant_catalogues.py
python3 scripts/check_alphabet_families.py data/alphabet_families_xtok.json 2>/dev/null | tail -1
if [ -f data/alphabet_contexts_emittable.json ]; then
  python3 scripts/reconcile_emittable.py --gate "$S/gate_menu_all.json" | head -40
fi
