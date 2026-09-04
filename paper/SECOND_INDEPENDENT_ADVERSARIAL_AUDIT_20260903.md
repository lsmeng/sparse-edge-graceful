# Second independent adversarial audit

Date: 2026-09-03  
Role: adversarial referee  
Verdict standard: whether the manuscript *as written* proves each stated theorem,
not whether the proposed theorem is likely true.

## Executive verdict

The four advertised repairs are not all closed.

- The expanded catalogue and the enlarged cap-3/cap-4 enumeration are real
  improvements.  The current local-family checker, menu gate, closure checker,
  and generated numerical tables reproduce.
- Nevertheless, Appendix A still omits a local owner configuration that the
  current scheduler actually emits on a concrete 19-vertex tree.
- The new carrier-elimination repair contains a false divisibility step.  An
  explicit catalogue family with determinant 5 gives a right-hand side for
  which the proposed lattice choice does not produce an integral carrier.
- The repaired dense-completion proof spends the entire perturbation allowance
  on the first correction and then adds two further positive errors before
  invoking the theorem.
- Several further seams remain: the pending triple is not removed from the set
  sent to the symmetric completion lemma, the `3W` symbolic-support invariant
  contradicts the manuscript's own rigid-chain exception, and the newly
  generated carrier certificate is not consumed by the constructor or checked
  by the advertised E4 audit.

I found no counterexample to either graph-theoretic theorem.  I did find
multiple gaps on the only proof chain offered.  Therefore:

| statement | does this manuscript prove it? |
|---|---|
| Theorem 1.1, unconditional polylogarithmic threshold | **No** |
| Theorem 1.2, conditional linear threshold | **No** |
| Theorem 1.2's external abelian assumption, taken literally as an assumption | not objected to here; the failure is in the paper's local realization and dense-completion deductions |

There is no `FATAL` finding in the sense of a demonstrated false theorem.  The
`SEVERE` findings below are proof-breaking gaps.

## Audited snapshot

The working tree is not clean, so the audit is pinned to file contents rather
than merely to Git `HEAD` (`3b4f6f55d529f58ae86071b8b2664705ce302278`).

```text
bf5141d99e7688b261765e253b6369d6f701a5d53f14e4291f433866927a29d9  paper/sparse_edge_graceful.tex
273018e9da02d69ccb59a157bf6829150d4f1415b1e35c31efa30da6866b5c3a  paper/numbers.tex
17545232807d2e38d451df67568ef019d9b54cdd1372cbf0b56c87b69443b26f  paper/REPAIR_coefficient_bound.md
bc172eb90df144e75780471c964f2e7210d89e829cd66d755de114282b2632d6  paper/REPAIR_dense_completion.md
59570ca3744c4f765d6ac6c8a717cef85544fd5be30012326f8db9f241daf1cc  paper/APPENDIX_A_ENUMERATION_20260903.md
19dc33faa1d9654e555316cdea7cc3865df530644ed0633bf715e2988ad2cbbd  research/antimagic/data/alphabet_families.json
1f67212639ddb71432aad3381cad5c895a59877eedebff1dc2b90ff0db7319a4  research/antimagic/data/alphabet_carriers.json
99ea00a27e546a5dea13a0d7bc411120ad4d87a0fadfde842ae3d173a8d202c4  research/antimagic/data/closure_report.md
```

## SEVERE findings

### S1. Appendix A still omits a genuine two-input owner

**Location.** `paper/sparse_edge_graceful.tex`, Appendix A, lines 1020--1040
and 1095--1104; compare `scripts/context_scheduler.py`, especially
`_act2_trigger` and `_resolve_act2`.

**Claim made.** Step 2 cancels active children to at most one, except when the
portless residual is `{1}` or `{2}` and exactly two active children must be
kept.  A joined/forced-head child is said to be cancelled against a sibling
with a free head.

**Why it does not follow.** The current scheduler emits a different case on the
following tree, rooted at vertex 3:

```text
(0,6) (1,17) (2,13) (6,15) (7,4) (9,3) (10,16)
(14,4) (4,3) (3,8) (15,11) (11,12) (12,8)
(17,16) (16,8) (8,13) (13,5) (5,18)
```

At vertex 8 the current scheduler returns

```text
context          h0_4_p0_act2
residual         {4}
ports            0
neutral units    none
active children  two, both L11 pass-through children
roles            kept_act2_1, kept_act2_2
```

Thus neither child is the free-head sibling required by Step 2.  Cancelling
both would leave the Step 4 residual `{4}` with no neutral unit; keeping both
produces the genuine context `h0_4_p0_act2`, outside the written `{1},{2}`
exception.  This was the concrete first-audit example, and the revised prose
still does not contain it.

The cap-3 and cap-4 enumeration does not repair a missing mathematical case
split.  Its own note says that the implementation contains the additional
procedures `_act2_trigger`, `_reduce_odd_k_to_one`, and `_resolve_act2`.
Stationarity of program output between two finite caps is evidence about this
program, not an induction for arbitrary `k` and not a proof that the prose and
program agree.

**Severity.** `SEVERE`.  Lemma C is the bridge from an arbitrary tree to the
finite catalogue.

**Smallest credible repair.** State the actual parity-dependent fallback used
by the scheduler, including every residual for which two active children are
kept, and prove that the cancellation/retention rule works when several
children have forced heads.  Then prove a reduction from arbitrary `k` to at
most two retained inputs.  Re-run the abstract enumerator as regression, but do
not use cap-3/cap-4 stationarity as the proof of the arbitrary-`k` statement.

### S2. The coefficient repair's divisibility step is false

**Location.** `paper/sparse_edge_graceful.tex` lines 1220--1232 and
1300--1309; `paper/REPAIR_coefficient_bound.md` lines 69--83;
`scripts/paper_numbers.py` in the definitions of `DMAX`, `MEFF`, and `KEFF`.

**Claim made.** For

```text
M K = N Lambda + c,      d = |det M|,
```

choosing `Lambda` in `(d*24 Z)^r` makes `N Lambda + c` divisible by `d`, so
`K` is integral and in `24 Z`.  The proof then replaces the varying lattice by
`M' Z` with `M' = 24*Dmax = 3456`.

**Concrete failure.** Take context `h2_2-6_p2_act`, menu 3, token 1.  Its
parameters are `[y,x,t1,u1]`, denominator 1, and the chosen minimum-determinant
carrier is `(y,u1)`.  On the first two token coordinates,

```text
M = [[-3, 2], [1, 1]],    det M = -5.
```

The noncarrier columns for `x` and `t1` are respectively `(3,-3)` and
`(1,-3)`.  The algorithm permits numerical noncarrier choices in `24 Z`.
Taking `x=t1=24` gives

```text
c = (96,-144),
adj(M)c = (384,336),
```

and neither coordinate is divisible by 5.  The term `N Lambda` is divisible by
5 when `Lambda` is chosen in `120 Z`, but that does nothing to the residue of
`c`.  Hence the displayed choice does not make `K` integral.

This is not an isolated determinant bookkeeping typo.  The current determinant
census has 33 tokens whose selected determinant does not divide 144:

```text
det 5: 20, det 7: 4, det 27: 5, det 30: 1, det 45: 1, det 81: 2.
```

In particular `3456` is not divisible by 5 or 7.  The sentence that follows
from `d <= Dmax` to a common lattice is invalid: an upper bound on integers does
not imply divisibility.  There are also 485 token contexts with no
unimodular option anywhere in their menu, so simply selecting a determinant-1
alternative is not available globally.

There is a second omitted factor in the coefficient formula.  Catalogue forms
are numerator vectors divided by family denominators.  If the resolving and
pending families have denominators `L_v` and `L_A`, the equation after clearing
the resolver's denominator contains `(L_v/L_A)N`, not merely `N`.  The current
catalogue uses denominators `1,2,3,4,6,12`; `carrier_determinants.py` and the
`KEFF=2*G*KMAX` calculation use raw numerator matrices and omit this ratio.

Finally, the assertion that the loss cannot compound requires a stable lattice
invariant for numerical outputs passed upward as later inputs.  Closing one
pending pair does not by itself put every resulting numeric input into a
lattice divisible by the determinant of an unrelated future resolving cell.

**Severity.** `SEVERE`.  Appendix B does not establish integrality or the
linear magnitude bound, and the printed `A=8*10^12` is not proved.

**Smallest credible repair.** Replace the scalar `Dmax` argument by an exact
Smith/Hermite-normal-form transition audit.  For every allowed
(pending-token, resolving-family, matching) transition, certify solvability of
the affine congruences, denominator clearing, and preservation of one common
lattice invariant under values passed to parents.  Derive the magnitude bound
from those transition matrices.  A simple `lcm` may help, but it is not enough
unless the invariant is shown to survive the division and later reuse of the
resolved values.

### S3. The repaired dense-completion proof exceeds MP's perturbation radius

**Location.** `paper/sparse_edge_graceful.tex` lines 738--750, copied from
`paper/REPAIR_dense_completion.md` lines 273--290.

**Claim made.** Put

```text
delta = (p/2)^(10^10) / log(n)^(10^24),
epsilon = delta/6.
```

Lemma 6.23 gives `|Q' triangle Q| <= 6 epsilon n`, after which Lemma 6.25 is
applied to both `Q'` and `R'=Z\Q'`.

**Broken inequality.** The first bound is already

```text
|Q' triangle Q| <= 6 epsilon n = delta n,
```

which uses the full Lemma 6.25 allowance.  But the manuscript's bound for the
second set is

```text
|R' triangle R|
  <= 6 epsilon n + |Z_n \ X| + |J*|
  =  delta n     + |Z_n \ X| + |J*|.
```

The last two terms are positive in the intended punctured application.
Therefore the conclusion “Lemma 6.25 applies to `R'`” does not follow.  The
hypothesis `|Z_n\X| <= epsilon n/2` makes the violation smaller, not zero.

**Severity.** `SEVERE` as written, because this is the global lemma used by
both theorems.  The underlying route appears locally repairable.

**Smallest credible repair.** Reserve explicit slack: take the Lemma 6.23
parameter at most `delta/12` (or smaller), and require the puncture plus
`|J*|=O(sqrt(n) log n)` to fit inside the remaining allowance.  Re-check the
lower and upper admissible range for Lemma 6.23 and propagate the smaller
constant to both theorem thresholds.

### S4. The `3W` invariant is incompatible with the stated rigid-chain branch

**Location.** `paper/sparse_edge_graceful.tex` lines 1162--1185,
1206--1218, 1261--1265, and 1287--1309.

**Claim made.** All symbolic labels lie in only three cells: the pending cell,
its active child, and its parent.  Hence there are at most `3W` symbolic forms,
which drives the bound on `|Phi|` and the printed constant.

**Why it does not follow.** Four lines later the proof admits that a symbolic
head can propagate through as many as three residue-two rigid rows before a
four-layer reset, and that a two-input rigid row can pass the live parameter
on.  Each such row contains labels depending on the symbolic input.  Thus the
symbolic support is not confined to the pending cell, one child, and one
parent.  The claimed four-layer reset is itself only asserted in this
manuscript; no lemma here proves the maximum chain length or incorporates its
cells into the invariant.

Even if the reset bound is correct, the numerical constant must count all
cells in the maximal propagation window, not `3W`.

**Severity.** `SEVERE` for the present realization proof and explicit bound;
probably repairable by a finite enlargement if the reset lemma is supplied.

**Smallest credible repair.** State and prove the reset lemma in the paper,
define the symbolic-support window to include every rigid layer and the reset
cell, replace `3W` by the resulting correct constant, and regenerate `Phi`,
box-size, and `A` bounds.  The constructor should then report and check that
same window.

## MODERATE findings

### M1. The pending triple is counted twice unless the dense instance is changed

**Location.** `paper/sparse_edge_graceful.tex` lines 671--682 and 784--788.

The realization lemma leaves `S` mirror-closed up to a pending token `T`; hence
`X=Z_n\({0} union S)` contains `-T` and is not symmetric.  Lines 673--675 say
that `-T` is placed into an odd ordinary block and then immediately say that it
remains to partition `X`.  If `-T` has been placed, those three labels must be
removed from `X`; if they remain in `X`, they are used twice.  Moreover the
chosen block's requested size must be reduced by 3.

**Smallest repair.** Define `X'=X\(-T)`, replace the chosen odd size `r` by
`r-3` (drop it if zero), and apply the dense lemma to `X'` and the adjusted
list.  Since `r` is odd and at least 3, the remainder is zero or at least 2.
Update the complement bound by 3.

### M2. “Halving each multiplicity” is undefined for odd multiplicities

**Location.** `paper/sparse_edge_graceful.tex` lines 734--742.

After reducing to parts of sizes 3, 4, and 5, the proof says to split the
multiset into `M^Q` and `M^R` “by halving the multiplicity of each of 3,4,5.”
The multiplicities need not be even.  For example a list containing one
3-block and one 5-block (plus any needed 2-blocks) has even total size but odd
multiplicity of both 3 and 5.

**Smallest repair.** Use floors/ceilings as in the actual proof of MP Lemma
6.27 and show that the two target sums differ from half by `O(1)`, which is
absorbed by the already needed slack in S3.

### M3. The carrier certificate pipeline is internally disconnected

**Locations.** `scripts/audit_e4_e6.py` lines 49--66;
`scripts/free_token_constructor.py` lines 3281--3290 and 4397--4404;
`data/alphabet_carriers.json`.

The E4 audit checks a carrier only if it is embedded as `carrier` or
`carrier_named` inside a family.  None of the 12,742 current families embeds
either field, so the advertised “recorded carrier” portion is silently skipped.
The actual carriers are in a separate file.

That separate file now maps a context to a list of records such as

```json
[{"menu": 1, "token_indices": {"carrier": ["t1","t2"], ...}}]
```

but `free_token_constructor.py` still documents and consumes the old schema
`context -> [parameter names]`.  It iterates the record dictionaries as though
they were parameter names, obtains an empty carrier, and downgrades the token.

A fresh ten-tree proof-faithful smoke run with Python 3.12/OR-Tools produced

```text
8/10 successful,
carrier_rank_below_two = 4,
T1_symbolic_tokens = 0,
T2_pairings = 0.
```

Thus the revised carrier file (timestamp 21:34) is newer than the reported
120-tree certificate run (18:36), and the current code no longer reproduces the
claimed live-carrier experiment.  This does not by itself refute the theorem,
but it removes the advertised executable validation of the repaired Appendix B.

**Smallest repair.** Give the carrier file a versioned schema; select by
`(context, menu, token tag)` in both audit and constructor; require exactly one
valid rank-two carrier for every token; and rerun the full faithful suite,
retaining the JSON certificates.

### M4. The blanket E1--E6 assertion contradicts the certified data

**Location.** `paper/sparse_edge_graceful.tex` line 1134 versus lines 576--589.

Line 1134 says “Every family carries (E1)--(E6).”  The paper elsewhere correctly
says only E1--E5 are universal and that some contexts require a gate.  The
literal current audit gives 4,427 E6-violating families over 2,514 contexts;
141 emittable family-bearing contexts have no E6 choice.  The later gate may
handle those cases, but the blanket premise used to open Appendix B is false.

**Smallest repair.** Replace the sentence by the exact E1--E5 statement and
state the family-selection/gate invariant before it is used.

### M5. E3 does not justify coordinate-by-coordinate nonzero slopes

**Location.** `paper/sparse_edge_graceful.tex` lines 1196--1204.

E3 says each full affine form is nonzero and distinct from the other full
forms.  It does not imply that every label or every difference has nonzero
slope in the coordinate currently being selected.  Most catalogue forms have
zero coefficients in several parameters; e.g. the head of
`h2_2-6_p2_act`, menu 3 is `[3,0,0,0]` and has zero slope in `x,t1,u1`.
Therefore the one-coordinate exclusion count is not justified as stated.

**Smallest repair.** Choose the remaining parameter vector jointly from a
finite grid and count proper affine hyperplanes, or prescribe an order and
prove that every condition is charged to its last nonzero coordinate.  Recheck
the box-size constant.

## MINOR findings

### N1. The “equivalently” clause of Theorem 1.2 is not equivalent

**Location.** `paper/sparse_edge_graceful.tex` lines 130--134.

From `n>C(D+1)` and `D<=k`, the direct sufficient condition is
`n>C(k+1)`.  The displayed `n>2Ck` is a stronger convenient condition for
`k>=1`, not an equivalent reformulation, and for `k=0` it says only `n>0`.

### N2. A sentence has a duplicated phrase

**Location.** `paper/sparse_edge_graceful.tex` lines 137--140.

“does not depend on the remark of that remark at all” should be corrected.

### N3. The coefficient-repair note has stale catalogue counts

**Location.** `paper/REPAIR_coefficient_bound.md` lines 41--58.

It records 7,962 tokens and 5,490 determinant-1 cases.  The current catalogue
contains 7,963 tokens and 5,491 determinant-1 cases after the added join.

## Reproduced checks and what they do establish

The following current checks passed:

```text
check_alphabet_families.py:        12,742 PASS, 0 FAIL, 0 SKIP
audit_e4_e6.py:                    E4 rank violations 0;
                                     E6 violations 4,427 families / 2,514 contexts
check_lookahead_gate.py --menu:    6,584,634 admissible family pairs;
                                     3,502 blocked chosen-family pairs
closure_check.py with current gate: C1--C6 PASS over 2,790 emittable contexts
                                     and 11,927 realizable context pairs
carrier_determinants.py:           7,963 tokens, no rank-two-carrier failure,
                                     maximum selected determinant 144
paper_numbers.py in a temp dir:    numbers.tex, catalogue_table.tex, and
                                     blocks_table.tex byte-for-byte identical
                                     to the manuscript inputs
```

These are genuine assets.  They certify the local algebra encoded by the
checkers and show that the generated tables match the current data.  They do
not prove that Appendix A's handwritten scheduler specification is exhaustive,
that the family choices form an integral global realization, or that the
dense-completion hypotheses are met.

I also tested the menu-gate relation as a finite path constraint through ten
levels.  Apart from the already encoded root join
`h0_1-2_p0_bot -> root_2_p0_act`, no dead family-choice path was found.  This is
useful negative evidence against a further family-selection bug, but it is not
used to excuse S1--S4.

## What was not checked in this second pass

- I did not re-run the 157,183,992-case nonconstancy sweep.  I inspected its
  source and accepted only the narrow conclusion it actually tests.  S2 is
  independent of nonconstancy: the explicit failure is integrality of the
  constant term.
- I did not repeat the full 120-tree constructor run because the ten-tree smoke
  test already exposes the carrier-schema incompatibility.  The full run should
  be repeated only after that parser is repaired.
- I did not repeat the literature novelty search.  No new theorem-priority
  conclusion is made here.
- I did not attempt to disprove either edge-graceful theorem by exhaustive tree
  search.  The verdict is about the submitted proof.

## Required order of repair

1. Repair Appendix A on the concrete `h0_4_p0_act2` example and prove the
   arbitrary-number-of-children reduction.
2. Replace the carrier integrality argument by a verified stable-lattice/SNF
   transition lemma; only then recompute `A`.
3. Repair the dense-completion error budget and the odd-multiplicity split.
4. Rewrite the pending-triple handoff as an explicit adjusted set and block
   list.
5. Prove the rigid propagation/reset window and recalculate `3W`.
6. Repair the carrier JSON consumer and rerun the faithful certificates.

Until items 1--5 are in the proof, neither theorem should be labelled proved or
submission-ready.
