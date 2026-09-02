# Reproducing the computations of the sparse edge-graceful paper

Everything below runs from `research/antimagic`.  Only the certificate search
needs `ortools`; the checker, the scheduler, the enumeration and the closure
check are plain Python 3.

    python3 -m venv venv && ./venv/bin/pip install ortools

## 1. The context list (Lemma C)

    python3 scripts/alphabet_contexts.py data/alphabet_contexts.json

Writes the finite list of contexts, including the A2 joint of every
free-child context and the port joint of every two-input context.

## 2. The certificate search

    ./venv/bin/python scripts/run_alphabet_batch.py \
        --contexts data/alphabet_contexts.json \
        --out out/alphabet.jsonl \
        --max-width 29 --parallel 4 --workers 6 --time 300 --token-rank 3

Nine settings of (denominator, internal parameters, coefficient bound) are
tried per context.  Flags used for the variant tables:

    --input-in-token          the shared edge must be a token member
    --all-inputs-in-token     both shared edges must be token members
    --two-tokens              a second, free token (even non-head counts)
    --port-in-token           a port label must be a token member
    --forbid-antipode-port    no label is minus a port label
    --forbid-antipode-x       no label is minus an input
    --forbid-antipode-y       no label is minus the head (non-FA families)
    --no-head-only            no label is a rational multiple of the head
    --free-head               the head is not an independent parameter

## 2b. The two construction identities

Most wide contexts are not searched at all.  Two identities build their
families from narrower ones, and both write the batch JSONL the ordinary
assembler and checker consume, so nothing here is trusted.

The six-edge insertion lengthens one arm by six:

    scripts/six_edge_insertion.py --kind arm     # and --kind port
    scripts/extend_by_insertion.py --targets data/alphabet_contexts_missing_vN.json \
        --out data/batches/insert_extended.jsonl

The neutral adjunction adjoins a set of arms and ports that pays for itself:

    scripts/neutral_block_search.py --ports 1 --arms 5,4 --params 1 --coef 8 \
        --json data/neutral/nb_p1_a5-4.json
    scripts/build_neutral_blocks.py          # collects and re-verifies them
    scripts/neutral_closure.py               # which targets are reachable
    scripts/extend_by_neutral_block.py --out data/batches/neutral_extended.jsonl
    scripts/extend_by_neutral_block.py --catalogue data/alphabet_families_xtok.json \
        --targets data/alphabet_contexts_c2_open.json \
        --out data/batches/neutral_xtok.jsonl

A block whose arms have opposite parity carries an odd number of labels and so
cannot be all mirror pairs; it is searched instead as a *token block*, three of
whose labels sum to zero and span a plane:

    scripts/neutral_block_search.py --arms 5,4 --params 2 --coef 6 --token \
        --json data/neutral_token/tb_5-4.json
    scripts/build_neutral_blocks.py --extra-dir data/neutral_token \
        --out data/neutral_blocks_all.json
    scripts/extend_by_neutral_block.py --token-blocks data/neutral_blocks_all.json \
        --targets data/alphabet_contexts_token_targets.json \
        --out data/batches/neutral_tok1.jsonl

A token block needs two parameters, since the checker requires a token to span
a plane, and it may be adjoined only to a host with at most one token.

`build_neutral_blocks.py` re-derives each block's outputs from its labels and
rejects any block that fails (N1)-(N4), so a bad search result cannot enter the
catalogue.  The equal-length pair and the pair of ports are closed forms and are
added without a search.

When a target context is too wide for the solver, search its *stripped* context
instead and adjoin the block: `h5_none_p0_A2` (width 13) decides in minutes,
where the width-25 joints it generates do not.

Note that re-running an extender after its families are already in the
catalogue writes an empty batch file, since the extender skips targets it finds
covered.  Rebuild against a catalogue with those keys removed.

## 3. Assembly, the independent checker, the gate, the variant tables

    scripts/assemble_all.sh /tmp

assembles every batch file into `data/alphabet_families.json`, runs
`scripts/check_alphabet_families.py` (which shares no code with the search),
replaces the catalogue only if every family passes, runs the menu gate
`scripts/check_lookahead_gate.py --menu`, builds the variant tables with
`scripts/build_variant_catalogues.py`, and reconciles with the emittable set.

## 4. The scheduler and its regressions

    python3 scripts/context_scheduler.py --all 9
    python3 scripts/context_scheduler.py --random 101 --count 500 --seed 7

`--all 9` enumerates all 4,782,969 labelled trees on at most nine vertices.
Both report `uncovered_count` and `missing_from_alphabet_count`, which must
be zero.

## 5. The abstract enumeration (which contexts occur)

    python3 scripts/enumerate_emittable_contexts.py --extra

Enumerates every abstract local state (head chain, arm multiset, ports,
active-child types), realises each by a concrete fragment, runs the scheduler
on it, and records the context emitted at the target vertex together with the
(child, parent) owner pairs.  Writes
`data/alphabet_contexts_emittable.json`, `data/emittable_pairs.json` and
`data/emittable_report.md`.

## 6. The closure check

    python3 scripts/closure_check.py --gate /tmp/gate_menu_all.json

Reports the six conditions C1 to C6 of the absorption rule and prints
`ALL CONDITIONS PASS` or `CLOSURE INCOMPLETE`, with the open contexts listed
by width.

## 7. The manuscript's numbers

    python3 scripts/paper_numbers.py --gate /tmp/gate_menu_all.json

Writes `paper/numbers.tex` and `paper/catalogue_table.tex`.  Every number the
manuscript quotes about the computation comes from here, including the
constant `A` of the realization lemma, so the manuscript cannot drift from the
catalogue.

## 8. The constructor

    ./venv/bin/python scripts/free_token_constructor.py --faithful \
        --sparse 51,101,201 --count 40 --block-time 12 --tries 300

The proof-faithful mode follows the realization lemma step by step and reports
every departure from it as a named gap.  Its purpose is to confirm the
bookkeeping, not the theorem: at these orders the asymptotic dense completion
does not apply, and a modular collision between two special labels is exactly
the event that the hypothesis `n > C(D+1)` excludes.
