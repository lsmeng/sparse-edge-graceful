# Adversarial review prompt: the sink route (Appendix B and its use)

Attach `sparse_edge_graceful.pdf` (or the `.tex`) to the request.  The prompt
below is self-contained enough to be answered from the PDF alone.

---

You are asked for an ADVERSARIAL review of one part of a mathematics paper on
edge-graceful labellings of trees: the new Appendix "Proof of the realization
lemma" (Appendix B) and the places that use it.  The rest of the paper has
already had three adversarial audits and their findings are repaired or
recorded; do not re-audit the decomposition (Section 4 and Appendix A), the
catalogue and its checker (Section 6), or the dense completion (Section 7)
except where they interact with the new appendix.  Your job is to find errors,
gaps, wrong quantifiers, silently excluded cases, and claims that are asserted
but not proved.  Try to break each statement.  Report only what you can back
with a specific reason; label each finding as ERROR (the statement is false or
the proof is invalid), GAP (true but unproved), or NIT (presentation).

WHAT THE APPENDIX CLAIMS.  Every tree of odd order n with D vertices of degree
two is decomposed into cells; each cell carries a family of integer linear
forms (labels) in a few parameters with P = O (the cell's labels permute its
vertex sums).  Labels other than the head come in mirror pairs plus at most
two "tokens", zero-sum triples.  Formerly a token was cancelled against
another token up the root path; the appendix now sends the NEGATIVES of every
free token to a SINK in the ordinary (stationary) part of the tree, and claims:

  Lemma (five-point absorber).  Five stationary vertices v0 > v1 > v2 > v3 > v4
  on a vertical path, each with a further stationary child (v4 with two),
  labelled e(v0v1)=a+b+d, e(v0w0)=-a-b-d, e(v1v2)=a, e(v1w1)=-c-d, e(v2v3)=b,
  e(v2w2)=d, e(v3v4)=2a+b-c, e(v3w3)=c-2a-b, e(v4w4)=c, e(v4w4')=-a-b, absorb
  the two zero-sum triples T=(a,b,-a-b) and U=(c,d,-c-d): v0, v3 stay
  stationary, v1, v2, v4 become non-stationary with sums 2a+b-c, a+b+d, a (a
  permutation of their parent labels), the ten labels are T, U, ±(a+b+d),
  ±(2a+b-c), pairwise distinct as forms.  Three vertices cannot do it, and
  the appendix now also argues that four cannot (check that argument).

  Lemma (sinks exist).  If n >= 10^6 (D+1) then the direct capacities of the
  ordinary blocks (a block of size r takes floor triples while the remainder
  is 0 or >= 2) plus twice the number of disjoint vertical 5-paths of usable
  vertices (stationary, not owner/helper/arm/unit, block size 2 or 4) is at
  least the number t of free tokens.  Proof by counting: at most 2D owners
  (Lemma charge), t <= 4D, skeleton <= 16D+1 vertices, blocks with positive
  capacity have < 7t children, hence >= n/8 usable vertices; the forest on
  usable vertices has <= 92D+4 components and out-degree <= 4, so at least
  m/2730 vertices of height >= 5; vertices of height ≡ 0 mod 5 start disjoint
  5-paths; hence >= n/109200 paths.

  Lemma (compatibility).  Any pairing of free tokens works; for a dependent
  pair (same cell, or a cell and its active child, which share a parameter)
  a role order of the two tokens exists with no identical collision of the
  four absorber forms with either cell's labels, their negatives, each other
  or zero (verified over 1,320,625 + 4,242,904 + 574,907 pairs and 401
  two-token families); then every avoidance condition is a proper affine
  condition and the charging argument of Lemma charge gives boxes of side
  O(|S|), |S| <= 20D+3, magnitudes <= A(D+1) with A = 1.5·10^8.

  The realization lemma then chooses every parameter numerically in
  post-order; forced-antipode children and two-input residual-{1} rows keep
  their earlier treatment (single equation a = -b; Lemma lem:reset).

WHERE TO ATTACK (in descending order of what would matter).

 1. The multiset identity.  Does the absorber really preserve the identity of
    Lemma lem:sigma once the five vertices sit inside a larger tree?  Check the
    role of the parent edge of v0, of hanging children that are themselves
    internal (their subtrees), of extra children at a path vertex, and of a
    hanging child that is the top of ANOTHER absorber or a direct-sink vertex.
 2. Double placement.  A free token may contain the input x (the head edge of
    the active child); its negative -x is then placed at the sink.  Is there
    any other place -x is placed (a parent family containing -x as the mirror
    of x; a helper)?  Is the exclusion of forced-antipode tokens exactly the
    right exclusion, and are two-token cells with one forced and one free
    token handled?
 3. The counting in "sinks exist".  Check every inequality: the owner bound
    via Lemma charge (2q with q the subdivided core edges), the skeleton list
    (does it include every vertex that is not a child in an ordinary block?),
    "every vertex outside the skeleton is a child in exactly one block", the
    bound 3k+4 on a block of capacity k, the out-degree bound 4 for usable
    vertices, the component count, the height argument (341, 1365, 2730), the
    disjointness of the 5-paths, and the final arithmetic.  Is "block size 2
    or 4" the right usability condition (what about a usable vertex whose two
    extra children must form an inverse pair the completion supplies)?
 4. Compatibility.  The proof says every collision condition is a proper
    affine condition because labels are homogeneous linear forms and the
    absorber forms have a nonzero coefficient in a parameter of the cell being
    processed.  Check the dependent case carefully: the child is processed
    before the parent, the child's head is the parent's input; which cell is
    "first" and "second", what is numeric when, and can a condition become
    constant (hence unavoidable) after the earlier cell is fixed?  Is the
    finite check (identical coincidence over the joint parameter space) really
    the right criterion for this?
 5. The leftover token (odd t) and the parity argument for an odd block;
    the interaction with the root cell's zero label; two-input cells whose
    tokens involve both inputs.
 6. The constant.  |S| <= 20D+3 (12D+3 from Lemma charge plus 2t <= 8D from
    absorbers), the forbidden-condition count, the box side, and
    A = 4·7·64·(box) = 1.5·10^8.  Is the factor 4 for absorber labels right
    (a+b+d, 2a+b-c are sums of at most four token coordinates)?
 7. Whether the certificates section overclaims: the sink-route constructor
    succeeded on 27 large trees and on 243 of 293 free trees of order <= 11;
    do the stated reasons for the fifty failures follow from the text?

RULES.  Quote the sentence you attack.  Distinguish ERROR / GAP / NIT.  If
you believe a statement is false, give a concrete counterexample (a small tree
or a small family) or a precise reason.  Do not propose rewrites of the
architecture; the question is whether THIS argument is correct as written.
If you find nothing wrong in a section, say so explicitly rather than
inventing a finding.  Finish with a one-paragraph verdict: is the linear
threshold n > C(D+1) established by this appendix together with the rest of
the paper, and if not, what exactly is missing.
