# Adjudication of the third audit (sink route), 2026-09-06

Audit: `the round-3 audit report (not redistributed here)`.
Every finding is accepted or rejected below, with what was changed in
`paper/sparse_edge_graceful.tex` and in `research/antimagic/scripts/sink_route/`.
Backup of the tex before this round: scratchpad `fresh/sparse_edge_graceful.tex.bak_before_round3`.

## ERROR-1 (accepted; fatal as stated; repaired)

The audit is right that Lemma compat never covered the negated unit placed at
a direct sink, and that a token containing $-x$ (the antipode of the input,
allowed by (E6)) is negated into $+x$, the label of an edge that already
exists.  The observation generalises: whenever two token labels of one family
are negatives of each other (the $\{x,-x\}$ case, or any other straddling
pair), those two are already mirrored inside the cell and must not be negated
again.

Repair (PROOF, in the tex).  Tokens are replaced by *units*: remove every
antipodal pair among a family's token labels; what remains is two triples,
one triple, one *quad* (a zero-sum set of four labels, the case of exactly one
straddling pair), a pair (nothing to place) or nothing.  Quads go to a block
of size $4$ or $\ge 6$ or to a new four-vertex *quad gadget* with a fresh
parameter $f$ (Lemma lem:quad: labels $f-q_1-q_2$, $-(f-q_1-q_2)$; $q_1$,
$q_2$; $f$, $-f$; $q_3$, $q_4$; the three lower vertices have sums $f$, $q_1$,
$f-q_1-q_2$, a permutation of their parent labels).  Lemma compat now proves
that a negated unit label is never identically a label of its own cell (the
pairs were removed), of the active child ((E6): no child label is a multiple
of the shared head except the head itself, and $-x$ was removed with $x$) or
of the parent ((E6): the parent's input-only labels are $\pm y$, and a unit
label $\mp y$ would be a multiple of the head).  The gadget's own four labels
are affine in $f$ with slope $\pm1$, so their conditions are proper.  The
packing lemma counts one path per unit (a path takes two triples or one
quad); the threshold $10^6(D+1)$ still covers $t\le 4D$ units.  No catalogue
family is filtered out.  Our own scan finds $54$ families ($53$ contexts) with
$-x$ in a token (the audit's $215$ used a broader criterion), and every one of
them also carries $+x$ in a token, so all are quads and are handled; the
$163$ quad families in all ($159$ contexts) include $136$ whose straddling
pair is not an input pair.  `h4_5_p1_A2` needs no new family.

Code: the sink constructor forms units from the coefficient vectors, sends
quads to direct blocks ($r-4\in\{0\}\cup[2,\infty)$) or quad gadgets (fresh
$f$, three splittings tried), and its regression was rerun
(`data/sink_route/regression_v2/`, `regression_reset_v2/`): identical ok/fail
sets to before (270/320 and the five reset combs), 275/275 certificates
re-verified; four sparse trees now send a quad to a size-four block; the quad
gadget, the FA second-token sink and the residue-two exclusion were each
exercised on a purpose-built small tree (`regression_v2/witness_trees.json`,
`cert_*.json`).

## GAP-2 (accepted; repaired)

The second token of a forced-antipode family ($\{x_1,x_2,-x_1-x_2\}$ on the
two inputs in all four menus of the one forced-antipode context) is a free
unit and goes to a sink; the tex says so, and the constructor no longer skips
forced-antipode families when collecting units.

## ERROR-3 (accepted; repaired)

`\NumPhiMax` is now the maximum number of forced ratios over every family in
the catalogue ($10$, attained at `root_1-6_p0_act`); the per-context minimum
is kept as `\NumPhiMin` ($6$) and is not relied on.  Downstream:
`\NumPlacedCoefSink` $42\to 50$, box $58{,}464\to 69{,}600$, label
$26{,}191{,}872\to 31{,}180{,}800$, $A=163{,}430{,}400\le 1.7\cdot10^8$.  The
sentence in Lemma charge about "a family of the menu with fewest such ratios"
was replaced.

## GAP-4 (accepted; repaired in the text, gate pending)

The passage claiming "(E5) does hold" for the residue-two ray was rewritten:
the constructor uses the one-parameter template $(-3t;\,-t,\,-2t,\,t;\,2t)$
with forced head $-3x/2$; its labels are determined by the input and are
charged to the step at which that input is chosen, like the residual-$\{1\}$
row.  The identical collision the audit describes (a parent label equal to
$\pm x_P/3$ or $\pm 2x_P/3$) is excluded by the choice rule above a residue-two
ray.  Scan (`sink_route/rigid_parent_scan.py`): among the 1,691 single-input
families exactly one (`h4_6-6_p0_act`, first of its menu) carries such a
label (all four values at once) and its context has a clean alternative; among
the 1,265 two-input families one (`h3_1-3-3-3_p0_A2`) carries $\pm 2x_1/3$
and has no alternative, but the ray, if present, is assigned to its other
input, which is clean; no parent context is left without an admissible
family.  A second class of identical collisions was found while repairing
this: the negative of a unit label that is a multiple of the input by a
factor other than $\pm1$ (30 such unit labels in 28 contexts; factors
$\pm2,\pm3,\tfrac12,\tfrac32$) against a child label that is the same
multiple of its head (478 such labels in 166 contexts, the (E6)-violating
families that the existing lookahead gate already handles for the identity
$u=\ell$).  The lookahead gate (`check_lookahead_gate.py`, now default; `--legacy`
reproduces the old run byte for byte) was extended to the identities
$-u=\ell$ in both directions: \NumGateFail $1{,}973\to1{,}974$, the one new
pair (`root_1-2-2-6_p2_act` over `h3_1-1_p1_V21`) is not realizable, and
\NumGateFailRealizable stays $71$ with the same 71 pairs the manuscript
already handles; the compat proof cites this gate.

## GAP-5 (accepted as a gap in the text; no change in the argument)

A hanging child of an absorber can only be the *top* vertex of another
gadget (an internal vertex of another path would make the two paths share a
vertex); a top vertex is stationary, which is all Lemma absorber asks of a
hanging child, and its parent label being one of the first gadget's labels
does not enter the second gadget's identity.  A sentence was added.

## NIT-1, NIT-2, NIT-3, NIT-4

NIT-1: the sentence about the last path vertex was corrected.  NIT-2: the
four-vertex impossibility is a statement about forms; numeric coincidences are
avoided by the choice of parameters, and the text says "when the coordinates
are independent".  NIT-3: the displayed reset family is now identified as the
one with fewest moving labels, distinct from the one the constructor uses.
NIT-4: the reset joints are exercised by their own regression; the stray
"faithful" failure label on one census tree is a classification string only.

## What the audit passed

Absorber algebra, the counting of Lemma packing (all inequalities and the
final arithmetic), Lemma reset and its constructor, the certificates section
against the data files, the parity and root arguments.
