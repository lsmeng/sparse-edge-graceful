# The abstract enumeration at three and four active children

Date: 2026-09-03.  Addresses the second audit's finding that "the abstract
states with `k >= 3` were never enumerated (the enumeration total is capped at
two), and trees on at most nine vertices contain no owner with `k >= 3`, so
`k >= 3` has only the empirical coverage of the random trees".

## What was capped

`enumerate_emittable_contexts.py` carried `--max-children` with default `2`.
The regression on all $4{,}782{,}969$ labelled trees of order at most nine
cannot supply an owner with three active children, because such an owner needs
at least ten vertices.  The scheduler does contain the three code paths for
this case (`_act2_trigger`, `_reduce_odd_k_to_one`, `_resolve_act2`), and they
were exercised only by the 3,500 random trees.

## What was run

The enumerator was given `--shard/--shards` and run on the workstation at the
caps three and four.

| cap | shards | abstract states | keys emitted | realizable pairs | crashes |
|---|---:|---:|---:|---:|---:|
| 2 (shipped) | 1 | 375,600 | 2,784 | 11,511 | 0 |
| 3 | 512 | 1,204,800 | 2,664 | 11,767 | 0 |
| 4 | 4,096 | 3,818,400 | 2,664 | 11,767 | 0 |

The two runs at caps three and four are not supersets of the shipped run: the
state plan spends its width budget differently, so 126 keys of the cap-two run
(the wide bottom rows, `h0_1-1-1-1-2-3_p0_bot` and its relatives) are absent
from them, and six keys of the cap-three run are absent from the cap-two run.
The union is therefore what the closure check should be run on:

```text
union of caps 2, 3, 4:   2,790 contexts,  11,927 ordered pairs
```

**The cap-four run adds nothing at all.**  It emits exactly the same 2,664 keys
and exactly the same 11,767 ordered pairs as the cap-three run, from three
times as many states.  Thus the emitted set is stationary between three and
four, which is the behaviour the case analysis predicts, since the root and
`act2` rules reduce any number of active children to one or two before a
context is emitted.

## What the enumeration found

*Nothing outside the alphabet.*  Every one of the 2,664 keys is in
`data/alphabet_contexts.json`, at both caps.  This is the statement the
audit asked for and it holds.

*Six new contexts*, all of them roots with a single arm:

```text
root_2_p0_L1  root_2_p0_L11  root_2_p0_act
root_4_p0_L1  root_4_p0_L11  root_4_p0_act
```

All six already had families in the catalogue.  One further key,
`h0_2_p0_act`, has no family and needs none: it is the residue-two rigid ray,
a constructor template, and `closure_check.py` has always exempted it.

*416 new realizable ordered pairs.*

## The closure check on the enlarged set, before the repair

```text
C1 every emittable context has a family     2790 / 2790   PASS
C2 free-child contexts absorb an FA child     544 / 544   PASS
C3 the folded letter                            1 / 1     PASS
C4 two-input contexts                          40 / 40    PASS
C5 L11 joints                                 565         nothing required
C6 menu gate, restricted to the 11,927 realizable pairs:
     1,973 failing ordered pairs, 71 with both contexts emittable,
     70 of those have the child h2_1_p0_act2 (rule 8d), 1 remains  OPEN
```

C1 to C5 are unchanged in substance and now cover six more contexts and two
more free-child contexts.  C6 acquired **one new obstruction**, and it is the
one genuine defect the enumeration uncovered:

```text
child  h0_1-2_p0_bot   under parent  root_2_p0_act
```

## The obstruction, and how it was closed

The parent's forced ratios are `{-1, -1/2, 1/2}` in every family of its menu,
and the child carries the antipode of its own head in every family of its
menu.  In the parent's units the child's label is `-1/h` at head multiplier
`h`, so it collides at `h = 1` with the parent's `-1` and at `h = 2` with the
parent's `-1/2`.  Three symbolic escapes were searched and all three fail:

1. a parent family whose forced ratios avoid `-1` and `-1/2`, over
   denominators 1 to 12, one to four internal parameters, coefficient bounds
   to 36, with and without a token, and under `--forbid-antipode-x`,
   `--forced-only-antipode`, `--no-head-only`: only the one forced set
   `{-1, -1/2, 1/2}` ever occurs;
2. a child family with no head-only label (`--no-head-only`) or without the
   head antipode (`--forbid-antipode-y`): INFEASIBLE in every setting;
3. a child family at head multiplier `h >= 3`: feasible, but the solver then
   places the antipode of the *new* head (`head_only = -3` at `h = 3`), so the
   normalised ratio is `-1` again and the collision returns.

The fix is the fourth route, and it is the device the absorption rule already
uses.  **The gate is a sufficient condition, not a necessary one.**  A pair it
rejects is still admissible if the child is joined into the parent, because
the two label sets are then solved together and no identity between them can
survive.  Solving the two rows

```text
--rows "root;arms=2;active"   --rows "arms=1,2"
```

is OPTIMAL at the first of the nine standard settings (denominator 1, one
internal parameter, coefficient bound 3, token rank 2), gives a family of
width 10, and passes `check_alphabet_families.py`.  It is in the catalogue as
`root_2_p0_J12`.

The join terminates on the spot: the parent is the root, so the enlarged cell
has no parent of its own, and the child is a bottom cell, so it has no active
child.  Nothing else in the decomposition moves.

`closure_check.py` now records this in a table `JOINT` beside `FA_CHILD`, and
the C6 test asks of each realizable failing pair that it either has the
forced-antipode child (rule 8d) or has a joint in the catalogue.

## The closure check after the repair

```text
C1 every emittable context has a family     2790 / 2790   PASS
C2 free-child contexts absorb an FA child     544 / 544   PASS
C3 the folded letter                            1 / 1     PASS
C4 two-input contexts                          40 / 40    PASS
C5 L11 joints                                 565         nothing required
C6 menu gate over the 11,927 realizable pairs:
     1,973 failing ordered pairs, 71 with both contexts emittable,
     70 with the child h2_1_p0_act2 (rule 8d), 1 by joining, 0 remain  PASS

ALL CONDITIONS PASS
```

Catalogue after the repair: 5,717 contexts, 12,742 families, independent
checker 12,742 PASS, 0 FAIL.

## What changed in the paper

* Section~4, the paragraph after Lemma~C: the cap is now four, and a new
  paragraph records the stationarity between three and four.
* Section~6, the gate paragraph: the exception and the join.
* `numbers.tex`: `NumStates` 375,600 -> 5,398,800; `NumEmittable` 2,784 ->
  2,790; `NumPairs` 11,511 -> 11,927; `NumGateFailRealizable` unchanged at 71;
  `NumCatContexts` 5,716 -> 5,717; `NumCatFamilies` 12,740 -> 12,742.

## Artifacts

* `scripts/enumerate_emittable_contexts.py` -- `--shard/--shards/--raw` added.
* `scripts/merge_enum_shards.py` -- merges the shards and compares with the
  alphabet, the catalogue and the rigid templates.
* `scripts/closure_check.py` -- `--emittable` added; `JOINT` added.
* `data/alphabet_contexts_emittable.json`, `data/emittable_pairs.json` --
  replaced by the union over the three caps; the cap-two versions are kept
  beside them as `*_k2.json.bak`.
* `data/emittable_k3.json`, `data/emittable_k4.json`.
* `data/batches/alphabet_gatefixk3_join.jsonl` -- the joint family.
* `data/closure_report.md` -- the report above.
