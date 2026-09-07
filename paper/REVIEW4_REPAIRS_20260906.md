# Repairs after the fourth review (2026-09-06)

Reviewed PDF: SHA-256 8c76709...4e6a3b, 30 pages, 06:33 EDT.
Backup of the tex before this round: scratchpad `fresh/sparse_edge_graceful.tex.bak_before_review4`.

## Severe item 1: cancelling triples were outside the sink ledger (accepted, repaired)

Section 3 lets a vertex cancel an odd number of active heads with a free
zero-sum triple.  A mirror pair is closed under negation; such a triple is not,
so its negatives need a sink, and Appendix B counted only the units of the
families.  Both places now say so, and the packing lemma counts these triples:
each consumes three owners, triples at different vertices consume disjoint sets
of them, and there are at most $2q\le 2D$ owners, so there are at most $2D/3$
of them.

## Severe item 2: the call to MP Lemma 6.23 did not meet its hypotheses (accepted, repaired)

With $\varepsilon=\delta/24$ and the deletion radius $\eta=\delta/8$, the bound
actually proved was $|Q\setminus Z|\le\delta n/8=3\varepsilon n$, three times
what the lemma admits, and the same for $|\sum M^Q-pn/2|$.  The two budgets are
now separated: the deletion radius is $\eta=\delta/48$, which gives
$|Q\setminus Z|\le\varepsilon n/2$ and
$|\sum M^Q-pn/2|\le\varepsilon n/2+O(\sqrt n\log n)\le\varepsilon n$ on the
input side, while the output perturbation is unchanged at $6\varepsilon
n=\delta n/4$ and the sum $\delta n/4+\delta n/48+O(\sqrt n\log n)$ still sits
under $\delta n$.  Only the constant moves; $\eta$ is existential in the lemma.

## Severe item 3: the packing capacity counted triples only (accepted, repaired)

A block of size three or five has capacity one and cannot hold a quad, so
"total capacity at least $t$" did not give a sink for an arbitrary mixture.
Repaired by a splitting that removes the distinction rather than by a
two-dimensional count: the negatives $Q=(q_1,q_2,q_3,q_4)$ of a quad go to two
triple sinks as $\{q_1,q_2,-q_1-q_2\}$ and $\{q_3,q_4,-q_3-q_4\}$; both are
zero-sum, and because $Q$ is zero-sum the two labels introduced are
$\pm(q_1+q_2)$, an inverse pair, so nothing new enters the ledger.  Every quad
is therefore counted as two triples, which makes cap the right capacity on both
routes.  New remark rem:quadsplit.

## Consequences

$t\le 8D+2D/3\le 9D$ (was $4D$); $7t\le 63D$; $m\ge n/8$ once $n\ge 286D+10$;
at most $127D+4$ components; $H\ge m/2730$ once $n\ge 7.0\cdot10^5(D+1)$;
paths $\ge t$ once $n\ge 982800D$; all still implied by $n\ge 10^6(D+1)$.
$|S|\le 30D+3$ (was $20D+3$), placed-coefficient bound $60$ (was $50$),
$A=1.9\cdot10^8$ (was $1.7\cdot10^8$).  `paper_numbers.py` regenerated.

## Smaller items

- Quad gadget: the three sums are the parent-edge labels of $v_3,v_2,v_1$, not
  $v_2,v_1,v_0$.  Corrected.
- Five-point absorber: the ten labels are distinct and nonzero *as forms*;
  distinctness of the values is a finite list of proper conditions added to
  $\Phi$.  Said explicitly.
- Absorber gate: the run covers one family per context, the preferred one.  The
  text now says so.  A full-menu run is still to be done.

## Still open before the paper goes out

1. `sink_route/sink_constructor.py` does not yet register cancelling triples as
   sink units, and the regressions have not been rerun against the new count.
2. The full-menu absorber gate (about 6.9 million pairs) has not been run here.
3. GitHub repository still private (404), cited in Section 10.
4. Theorem 1.2: whether to mark it conditional again pending the authors' reply.

## Code work, later on 2026-09-06

### Full-menu absorber gate (was open item 2): done, and it passes

`sink_route/full_menu_absorber_gate.py` enumerates every menu entry of every
context in sorted order, records the catalogue's SHA-256, and writes
`data/sink_route/full_menu_gate.json`.  Run: 2,175 parent families, 4,431 child
families, 9,637,425 ordered pairs, no pair without a collision-free role order,
minimum 6 of the 36.  `sink_route/verify_full_menu_gate.py` recomputes the same
quantities from scratch (Fraction vectors over an explicit joint coordinate
list, pools rebuilt, collision test rewritten; no code shared with
`absorber_gate.py`) and now agrees on everything: the pair count, the minimum
of six, the empty list of failing pairs and every bucket of the histogram
(`data/sink_route/full_menu_gate_verified.json`, shards in
`full_menu_shards/`).

Its first run did not agree, on 23 of the 9.6 million pairs, and the fault was
the verifier's: 59 catalogue families list the same parameter name twice, for
instance `[y, t1, t2, u1, t1]`, and those are two independent unknowns.  The
verifier built its joint coordinate map by parameter name and so merged the two
columns, which manufactured collisions; the gate embeds by position and was
right.  The verifier now embeds by position too.  Worth knowing when writing any
further check against this catalogue.

The reviewer's own 6,853,140-pair run was an inline script with no archived
artefact, so it is not citable; the number above is the project's own.

### Cancelling triples in the constructor (was open item 1): wired, NOT validated

`FaithfulRealiser` gained a no-op hook `after_cancel_group`, called once a
cancelled group's heads are numeric; `SinkRealiser` overrides it to register a
three-element group as a free unit bound for a direct sink, and
`free_token_slots` now reserves capacity for it.  The full regression
(`data/sink_route/regression_v3/`) gives 270/320, identical to the previous run.

It is exercised, and it works.  A first attempt to test it used a
hand-built plan that skipped the constructor's own root selection; that plan was
degenerate and the numbers it produced (heads not summing to zero, a group never
visited) were artefacts of the test, not of the constructor.  Retracted.

Under the constructor's own pipeline the picture is this.

1. Whether a tree has a three-element cancelled group depends on the root.  Of
   the regression trees, the sparse tree of order 201 has one at root 17, but
   the constructor succeeds at its first root candidate, which has none, so the
   320-tree run never reaches a triple.  That is why the rerun is unchanged.
2. Pinning that tree to root 17 does reach one.  With seed 7 the group at vertex
   17 has heads 360, -4320 and 3960, which sum to zero; the triple is registered
   as a free unit, its negatives -360, 4320 and -3960 are placed in one direct
   sink at vertex 0, and the finished labelling verifies with no errors.  The
   certificate is archived at
   `data/sink_route/regression_cancel_triple/cert_sparse_n201_root17_seed7.json`.
3. The same tree and root with seed 20260902 fails the new check: the last
   member of the group falls back to another family, so its head is not the
   value the cancellation forced and the three heads do not sum to zero.  This
   is a real defect of the fallback path, not of the sink route.  It never
   produced a wrong labelling, because every certificate is verified, but before
   this change it was silent; it now stops the attempt with an explicit failure
   and the constructor retries.
