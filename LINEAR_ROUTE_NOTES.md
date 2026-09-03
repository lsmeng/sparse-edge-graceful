# Programme: an elementary linear dense completion (2026-09-03)

**Goal.**  Prove the linear punctured-interval conjecture of
`ROBUST_PARTITION.md` Section 5 with an explicit constant, so that
Lemma dense (and hence Theorem 1.1 of `paper/sparse_edge_graceful.tex`) no
longer depends on Müyesser--Pokrovskiy at all and the constant `C` becomes
effective.

**Statement to prove.**  There is an absolute `C_0` such that for every
`M`, every `I subseteq [1,M]` and every `K >= C_0 M`, with `n = 2K+1`, the set
`[1,K] \ I` contains `floor((K-|I|)/3)` pairwise disjoint triples, each of
type B (`a+b=c`) or type A (`a+b+c=n`).

**Unified form.**  Both types are `{a, b, ||a+b||}` with `||x|| = min(x, n-x)`
the fold of `Z_n` onto `[0,K]`: type B when `a+b <= K`, type A when
`a+b >= K+1`.  So the problem is a Schur-triple packing in the folded group.

**Reflection.**  Under `x -> x' = K+1-x`, a type-A triple becomes a triple of
positive integers with `a'+b'+c' = K+2`.  Hence at `K = 3M+1` a perfect
type-A packing of the clean tail `[M+1,K]` is exactly an equal-sum partition
of `[1,2M+1]` into triples of sum `3M+3`, the classical magic-triple problem.

**Evidence so far** (`ROBUST_PARTITION.md` Sections 7-8): the last failing `K`
for the hardest witness `I=[1,M]` is `~3M` for all `M <= 20`; random `I`
never fails at `K = 3M, 4M`; at the boundary the packings are almost entirely
type A with one to three type-B triples.

## Plan

1. Pin the boundary structure: is the `K=3M+1` packing an equal-sum partition
   after reflection?  Which `M` admit a type-A-only perfect packing?
2. Clean-tail theorem: for `K >= 3M + c`, `[M+1,K]` packs perfectly (leftover
   `(K-M) mod 3`).  Explicit construction from equal-sum partitions plus a
   bounded number of type-B repairs.
3. Holes: an inner element `j <= M` is absorbed by the type-B triple
   `{j, b, b+j}` with `b, b+j` in a reserved buffer sub-interval of the tail;
   the buffer's leftover is packed by the clean-tail theorem again.
4. Count and divisibility bookkeeping; write the proof; audit numerically for
   all `M <= 12`, all `I`, all `K <= 6M`.

## Log

### 2026-09-03, first results

* **Boundary is type-A only, for every M.**  At `K=3M+1` the clean tail
  `[M+1,K]` (length `2M+1`) has a perfect type-A packing (leftover
  `(2M+1) mod 3`) for all `4<=M<=40`, with type B forbidden.  After the
  reflection this is an equal-sum triple partition of `[1,2M+1]` (sum
  `3M+3`) with at most two elements left over.  When `3 | 2M+1` the number of
  triples `t=(2M+1)/3` is automatically odd, which is the classical
  integrality condition for equal-sum partitions of `[1,3t]`.
* **Clean tail packs for all K in [3M,3M+12]**, `M` up to 40, no UNKNOWN.
* **The equal-sum partition is a consecutive-sum pairing.**  Take the `t`
  smallest tail elements as the "small block" and pair the remaining `2t`
  (the "top block") so that the pair sums run through `t` consecutive values;
  a pair with sum `s` together with the small element `2K+1-s` is a type-A
  triple.  Pairings of `[1,2t]` with consecutive sums `sigma+1..sigma+t` are a
  Skolem/Langford-type object (reflecting one coordinate turns consecutive
  sums into consecutive differences): call them **sigma-sequences**.  Their
  existence spectrum in `(t, sigma)` is being computed.
* **General K reduces to sigma-sequences with a shifted window.**  A small
  block `[r+1-delta, 2r-delta]` and the top block `[K-2r+1,K]` are packed by
  `r` type-A triples exactly when a sigma-sequence with `sigma=2r+delta`
  exists; for `delta>=1` this is Simpson's Langford theorem (defect `delta`,
  order `r`, needs `r>=2delta-1`).  The boundary `K=3M+1` is the centred case
  `delta<0`, the case `K=4M+3` is a plain Skolem sequence (`delta=1`).
* **Correction of the sigma bookkeeping.**  The equal-sum partition of
  `[1,3t]` corresponds to the sigma-sequence with `sigma=(3t+1)/2`, whose
  window `[(3t+3)/2,(5t+1)/2]` is centred at `2t+1`: it is the *centred*
  case, not a Langford sequence.  As a `3 x t` array with rows (small, b, c)
  it is a **3 x t magic rectangle** (entries `1..3t`, constant column sums),
  classical: exists iff `t` odd (Harmuth 1881; Bier--Rogers).  CP-SAT confirms
  existence for all odd `t<=41`.
* **The whole clean-tail range as one ansatz.**  For `K-M=3t` the small block
  `[M+1,M+t]` plus the top block `[M+t+1,K]` is packed by `t` type-A triples
  iff a sigma-sequence with `sigma=3t-M` exists.  As `K` runs from `3M+1` to
  `7M+3`, `sigma` slides from the centre `(3t+1)/2` to Simpson's extreme
  `(5t+1)/2` (defect `(t+1)/2`).  So the clean-tail theorem for the whole
  linear range is the statement that sigma-sequences exist for every window
  between the centre and the Langford extreme (with hooked/near variants for
  the bad congruence classes, absorbed by the `<=2` leftover).

### 2026-09-03, second pass: the problem is Heffter's difference problem with holes

* Two structural ansaetze failed cleanly: consecutive-sum pairings of a single
  interval exist **only** at the centred value (t odd), i.e. only as the
  `3 x t` magic rectangle (exact spectrum for `t<=13`); and a pure type-A
  packing whose third elements form an interval exists only at `K=3M+1`.
  So the packings for `3M+1 < K < 7M+3` have a genuinely mixed structure.
* **Identification.**  A type-B triple `{a,b,a+b}` is a pair `{b, a+b}` at
  distance `a`; a type-A triple `{a,b,c}`, `a+b+c=n`, is the pair `{b,-c}` at
  cyclic distance `a` in `Z_n`.  So a packing of `[1,K]` (`n=2K+1`) into
  type-A/B triples is exactly **Heffter's difference problem**: for `n=6t+1`
  (first problem) partition `[1,3t]` into triples with `a+b=c` or
  `a+b+c=n`; for `n=6t+3` (second problem) the same for `[1,3t+1]\{2t+1}`.
  Peltesohn (1939) solved both explicitly for every `t` (except the second
  for `t=1`), which is the classical construction of cyclic Steiner triple
  systems.  Our conjecture is therefore: *Heffter's difference problem is
  robust to deleting any set `I` of at most `M` small differences, once
  `n >= C M`.*  The unpunctured case is Peltesohn's theorem; `n = 5 mod 6`
  is the cyclic maximum-packing case with two leftovers.
* Next: obtain Peltesohn's explicit formulas, count how many of its triples
  meet `[1,M]`, and re-route those through a reserved absorbing region using
  the proved three- and six-hole absorbers.
* **Difference/position view.**  Writing each triple as (d; p, q) with d its
  smallest element, a clean-tail packing is a set of differences `D` (roughly
  the lower third of the tail, with gaps) and a pairing of the remaining
  elements ("positions") into pairs at distance `d` in `Z_n`, folded by
  sign.  Stacking magic-rectangle units, or one magic unit plus a magic
  middle, is arithmetically impossible except at `K=3M+1` (the block
  positions are over-determined), so the general packing is a genuinely
  irregular cyclic Skolem-type object.  Current hypothesis under test: the
  difference set can always be taken to be the interval `[M+1,M+t]` (a
  *cyclic Langford sequence* of defect `M+1` and order `t` with folded
  positions in `[M+t+1,K]`); if so, the theorem is a cyclic analogue of
  Simpson's theorem with threshold `t >= (2M+1)/3` instead of `t >= 2M+1`.

### 2026-09-03, the object is a folded cyclic Langford sequence

**Confirmed hypothesis.**  For the clean tail `[M+1,K]`, `K-M=3t`, `n=2K+1`,
the `t` smallest elements `[M+1,M+t]` can always be taken as the
differences and the remaining `2t` elements `[M+t+1,K]` paired so that the
pair for `d` has `q-p=d` or `p+q=n-d`.  Exact CP-SAT: feasible for every
`M in [6,14]` and every `K` from the first admissible value `>=3M+1` up to
`7M+6` (one timeout at `M=14`); `M=5` fails only at `K=17`.

**Definition.**  A *folded cyclic Langford sequence* `FCL(d,t)` is a
partition of `[d+t, d+3t-1]` into `t` pairs, the pair assigned to `d+i-1`
(`i=1..t`) having difference `d+i-1` or sum `n-(d+i-1)`, `n=2(d+3t-1)+1`.
Simpson's theorem is the case with no folded pairs and needs `t>=2d-1`;
the evidence says `FCL(d,t)` exists for `t>=(2d-1)/3` (i.e. `K>=3M+1`),
one third of Simpson's bound, with the `3 x t` magic rectangle at the
boundary (all pairs folded).

**Shift invariance.**  Shifting every position by `3` and `n` by `6`
preserves both pair types.  So `FCL(d,t) -> FCL(d,t+1)` needs only a local
switch that inserts the new difference `d+t` and the two new lowest
positions `d+t+1, d+t+2` while re-pairing `O(1)` old pairs.  If a uniform
switch exists, the existence theorem follows by induction on `t` from the
boundary cases, exactly as the hooked/extended Skolem theorems are proved.
* **An explicit family at K ~ 4M.**  For `M in {t-1, t}` (`K=4M+3` or
  `4M`) the solver returns the rigid pattern: the pair for `d_i=M+1+i` uses
  `p_i=M+t+1+i` (lower positions in natural order), type B for
  `i < t/2` giving `q_i = 2M+t+2+2i` (the even upper positions) and type A
  for `i >= t/2` giving `q_i = 5t-1-2i` (the odd upper positions, descending).
  The two progressions tile the upper half `[M+2t+1,K]` exactly when
  `M in {t-1,t}`, so this family is confined to `K ~ 4M`.
* **Small local switches do not give the induction step.**  From arbitrary
  solutions of `FCL(M,t)`, shifting by 3 and re-pairing at most three old
  pairs succeeds only sporadically; any induction must carry a structural
  invariant.  Under test now: the *bipartite* form (every pair has its `p`
  in the lower half `[M+t+1,M+2t]` and its `q` in the upper half), which
  would reduce the theorem to a permutation of the lower half.

### 2026-09-03, reduction to folded sum permutations

**Bipartite form holds** on the whole range `3M+1 <= K <= 7M+3` for
`M=5..16` (exact): every pair has its `p` in the lower half
`L=[M+t+1,M+2t]` and its `q` in the upper half `U=[M+2t+1,K]`.

**Reduction.**  Write `d=M+1+i`, `p=M+t+1+j`, `q=M+2t+1+k` with
`i,j,k in [0,t-1]` and put `s = M+1-t`.  Then

    type B  (q-p=d)      <=>  k = i+j+s,
    type A  (p+q=n-d)    <=>  k = (2t-1) - (i+j+s).

So a bipartite `FCL(M,t)` is exactly a permutation `pi` of `[0,t-1]`
(`j=pi(i)`) such that `u_i = i+pi(i)+s` lies in `[0,2t-1]` and its fold
`min(u_i, 2t-1-u_i)` is again a permutation of `[0,t-1]`: a **folded sum
permutation** of order `t` and shift `s`.  The range `3M+1<=K<=7M+3`
is `s in [(1-t)/2, (t+1)/2]`.  At `s=-(t-1)/2` no fold is needed and this
is a Langford sequence (Simpson); at `s=(t+1)/2`, `t` odd, every `u_i` is
folded and this is the `3 x t` magic rectangle.  The exact feasibility region
in `(t,s)` is being computed; the theorem to prove is existence for all
`s` in the window, and the natural proof is an explicit arithmetic
construction as in Simpson's paper.
* **Explicit solutions.**  For `s in {0,1}` the identity permutation works:
  `u_i=2i+s`, type B while `2i+s<=t-1` (giving the `k` of parity `s` in
  increasing order) and type A afterwards (giving the other parity in
  decreasing order); the two runs tile `[0,t-1]`.  This is the `K ~ 4M`
  family.  For other `s` the solver's permutations are the identity with
  3-cycles on consecutive blocks `{i,i+1,i+2} -> {i+1,i+2,i}`, which replace
  the sums `2i,2i+2,2i+4` by `2i+1,2i+2,2i+3` and so repair the parity
  count; a construction from identity segments and 3-cycle segments, in
  the manner of Simpson's proof, looks within reach.
* **Leftovers.**  When `K-M=3t+e`, `e in {1,2}`, leave the `e` largest
  elements unused; the type-A relation becomes `k=(2t-1+2e)-u`, a shifted
  fold.  The feasibility tables for `e=0,1,2` are being computed.

### 2026-09-03, evening: the exact theorem, and the transversal form

**Exact region.**  Folded sum permutations of order `t` and shift `s` exist
for every integer `s` with `(1-t)/2 <= s <= (t+1)/2` and for no `s`
outside it, for all `3 <= t <= 22` except `t=4` (`s=-1,2` fail).  Unlike
Simpson's theorem there are **no congruence exceptions** inside the window:
the folding removes them.  So the clean-tail theorem is sharp:
`[M+1,K]` packs iff `3M+1 <= K` (up to the `<=2` leftovers), for the whole
range up to `7M+3`, after which Simpson takes over.

**Transversal form.**  With `tau_i = i + pi(i)` the conditions are: the
`tau_i` are distinct, lie in the window `W=[-s, 2t-1-s]`, and no two of them
sum to `c = 2t-1-2s` (the reflection constant of `W`).  So an `FSP(t,s)` is
a permutation whose sum sequence is a *transversal of the reflection of W*.
The identity has all sums even while `c` is odd, so it is reflection-free
for every `s`, and it fails outside `s in {0,1}` only because its sums leave
`W`; the general construction must compress the sums into the shifted
window.  A plain rotation `pi(i)=i+a` is reflection-free for `t` even but
collides in parity; the explicit construction will need two or three
interleaved families, as in Simpson's proof.

**Induction remark.**  Shifting `pi` by `2` shifts all sums by `2` and
keeps reflection-freeness for the window of `t+2` (its constant is `c+4`),
so `FSP(t,s) -> FSP(t+2,s)` reduces to placing the two new rows on the freed
columns `0,1`, which needs the old sum set to avoid four specific values;
this is a candidate invariant for an inductive proof.

**Holes.**  The punctured case is the same object with a sparse set `J` of
extra small differences: `D = J u [M+1,M+t']`, positions `[M+t'+1,K]`,
`K-M-2|J| = 3t'`.  Random `J` of every size is feasible for `M in {8,10,12}`
and `K` from `3M+4` to `6M+1`.
* **Leftovers settled (modulo explicit near-magic rectangles).**  The
  shifted-fold model (omit the `e` largest) is badly behaved (sparse
  feasibility), so instead omit the `e` smallest: `M -> M+e`, a clean `e=0`
  instance whenever `K >= 3(M+e)+1`.  The only remaining cases
  `K in [3M+1, 3M+3e]` are all feasible for `M <= 30`, even with type-A
  triples alone, i.e. as a `3 x t` magic rectangle with one or two empty
  cells (the unused element sits near the middle of the tail); this is the
  object of "magic rectangles with empty cells" (arXiv 1809.08605).
* **Two more shape classes ruled out** (exact, `t<=24`): permutations with
  at most four distinct values of `pi(i)-i` fail at several `s` for most
  `t`; transversals of the form "lower half with one interval flipped up"
  fail almost everywhere (they are not even the identity's shape, which is a
  parity class).  The genuine solutions mix a parity-class skeleton with
  irregular adjustments, so an explicit construction will need Simpson-style
  interleaved arithmetic families indexed by residue classes, or an
  induction carrying an invariant.  **This is where the programme stands:
  everything is reduced to proving `FSP(t,s)` for all `s` in the window; the
  statement is sharp and verified exactly to `t=30`, but not yet proved.**

**Sum invariant worth recording.**  `sum_i tau_i = t(t-1)` for every
permutation, so a transversal `T` of `W` must have total `t(t-1)`: its mean
exceeds the window centre by `s-1/2`.  Interval transversals (lower or upper
half) occur exactly at the two endpoints of the window; parity-class
transversals exactly at `s in {0,1}`.

## 2026-09-04: template search for an explicit construction

**Forced sums.**  Since `tau_i = i+pi(i) <= 2t-2`, for `s>=1` the `s`
largest values of the window, `2t-2s..2t-1-s`, have no reachable
reflection partner, and as `|T|=t` they must all be attained; for `s<=-1`
the `|s|+1` smallest reachable values `|s|..2|s|` must all be attained.
The remainder of `T` is a transversal of the reflection on `[0,2t-1-2s]`
(resp. `[2|s|+1,2t-2]`).  With the sum invariant this pins the shape: for
`s=2`, `T` is the identity transversal of order `t-2` with one bump plus
the two forced top sums, and the solutions are "identity plus local surgery
at the ends" of size growing with `|s|`, ending in the magic rectangle at
`s=(t+1)/2`.

**Method.**  For each `(t,s)` minimise the number of changes of the shift
`pi(i)-i` along each parity class of `i` (`i -> i+2`); a bounded minimum
with parameters affine in `(t,s)` on residue classes is a Simpson-style
construction.  Sweeps: `template_discovery.py`.

**Template sweep result.**  Minimising the number of shift changes along
each parity class, the optimum is between 4 and 8 for every `(t,s)` with
`t in [10,24]` (all proved optimal), independent of `t`: a Simpson-style
construction with a bounded number of interleaved arithmetic families exists.

**Symmetry.**  `i -> t-1-i`, `pi -> t-1-pi` maps `FSP(t,s)` to
`FSP(t,1-s)`, so it suffices to treat `s >= 1`.

**An explicit scheme (s >= 1, t' = t-s).**
* top rows `t'+r -> t'+s-1-2r` (`r=0..s-1`): sums `2t'+s-1-r`, exactly the
  forced set `[2t', 2t'+s-1]`;
* band rows `t'-s+m -> t'+s-2m` (`m=1..s-1`): sums `2t'-m`, the run
  `[2t'-s+1, 2t'-1]`; together with the top rows these use every column of
  the band `[t'-s+1, t'+s-1]`;
* identity on `[0, t'-s]`: sums the evens `[0, 2t'-2s]`.
The total is `t'(t'-1)+s(s-1)/2` exactly as required.  At the upper endpoint
`s=(t+1)/2` the identity part is empty and `T` is the upper half of `W`, an
explicit magic rectangle.  The only defect is that the even sums
`x <= s-2` of the identity part are reflections (`x + (2t'-1-x)`) of
elements of the run; the number of such conflicts equals the number of
fully absent pairs `{x', 2t'-1-x'}` with `x'` odd in `[s-1, 2s-2]`, so a
repair confined to the first `O(s)` rows should exist, with residue cases.
`scheme_test.py` tests repair regions `R in {s, s+2, 2s}`.

**Why the scheme's repair failed, and what works.**  Any square sub-block
(rows `[0,R]` onto columns `[0,R]`) has a fixed sum total, so a repair
confined to it cannot trade a conflicting even sum for an absent odd one;
repairs must be non-square (exchange with the band).  The closest-to-identity
solutions confirm this: for `s>=3` about `s+2` rows move, typically as one
cycle through the band, while for `s=2` the number of moved rows grows with
`t`.

**Rotations are the endpoint objects.**  A block `[a,a+L-1]`, `L` odd,
rotated by `(L-1)/2` has sums forming the interval
`[2a+(L-1)/2, 2a+(3L-3)/2]`; for `a=0`, `L=t` this is the lower half of `W`
at `s=(1-t)/2` and the upper half at `s=(t+1)/2`: one explicit permutation
is both the hooked-Langford endpoint and the magic rectangle.  Gluing a
rotated Langford-type block below a rotated magic-type block is
reflection-free exactly when `s ~ t/4`, which is where the solver returned
its most regular solutions.  So the natural template is block-diagonal:
identity blocks (even sums) and rotated odd blocks (interval sums), with
affine block parameters; `block_rotation_test.py` tests `B<=5` blocks.
* **Block-diagonal rotation templates fail** almost everywhere (only the
  endpoints, `s in {0,1}`, and isolated gluing points), confirming that the
  constructions must interleave the two parity classes of rows.  Restricting
  each parity class to at most four constant-shift runs is infeasible at
  `t=16`, `s in {-4,-3,-2}`, so five runs per class are needed in general,
  matching the sweep's minimum of up to eight changes.  Minimum-`sum|shift|`
  solutions are not canonical across `(t,s)`, so parameter fitting from
  solver output needs a fixed template shape first.
* Primary sources (Peltesohn 1939, the Heffter-array survey, Meszka's notes,
  Skolem circles) are being extracted to text under `tmp/pdfs/` since the
  fetch tool cannot read PDFs; Peltesohn's explicit mixed families are the
  closest published analogue of what is needed.

**Published explicit families for the case M=0.**  The columns of a Heffter
array `H(3,n)` are a solution of Heffter's first problem, and Dinitz--Mattern
(AJC 67 (2017), arXiv 1505.04070; text at `tmp/pdfs/dinitz_mattern_H3n_1505.04070.txt`,
lines 247--648) reproduce the Archdeacon--Boothby--Dinitz construction case by
case modulo 8: a fixed block `A` of four to six columns plus families `A_r`,
`0<=r<=2m`, whose entries are `(-1)^r` times affine functions of `m` and `r`
(e.g. for `n = 8m+8`, `v = 48m+49`, the column
`((8m+r+10), (8m-2r+5), (-16m+r-15))` and three siblings).  The small
elements `1..4m+1` enter through single families such as `-4m+2r-1`, paired
with two large entries, so in the `M=0` solution the columns meeting `[1,M]`
form prefixes of explicit families and their large partners form explicit
arithmetic progressions.  Two routes for general `M`: (a) delete those
columns and re-pack the orphaned large entries, which are unions of a few
APs; (b) design the families directly in the FSP language (differences
`[M+1,M+t]`, positions above), where the interval structure is built in.
Route (b) is cleaner; route (a) has the published template to copy.

### 2026-09-04, late: a composition theorem

**Theorem (composition).**  Let `a` be odd and let `sigma` be an
`FSP(b, s')`.  Then `pi(a*u+w) = a*sigma(u) + ((w + (a-1)/2) mod a)` is an
`FSP(a*b, s)` with `s = a*(s'-1) + (a+1)/2`.

*Proof.*  The inner rotation by `(a-1)/2` sends the block `[0,a-1]` to
itself with sums `w + rho(w)` forming the interval `I=[(a-1)/2,(3a-3)/2]`,
which is symmetric about `a-1`.  The sums of `pi` are `a*(u+sigma(u)) + I`.
With `s = (a+1)/2 + a*q`, the window condition `T subseteq [-s, 2ab-1-s]`
becomes `u+sigma(u) in [-(q+1), 2b-q-2]`, the window of `FSP(b, q+1)`, and
the reflection constant `c = 2ab-1-2s = a(2b-2q-1)-2` sends
`a*S + x` to `a*(2b-2q-3-S) + (2a-2-x)`, i.e. reflects `I` onto itself and
the block index by the constant `2b-1-2(q+1)` of `FSP(b, q+1)`.  Hence
`T` is a transversal iff `{u+sigma(u)}` is one, and `s' = q+1`.  QED.

Computationally the block-product test had found exactly these `s`
(e.g. `t=15, a=3`: `s = 3s'-1`), and `composition_check.py` verifies the
construction exactly on every `(a,b,s')` with `a<=9`, `b<=13`.
Products alone do not cover prime `t` or every residue of `s`, so an
additive extension is still needed; `mixed_block_test.py` tests blocks of
sizes `a` and `a+1` with a size-preserving block permutation.

## 2026-09-05: day 3

* Overnight: from arbitrary solutions, the steps `(t,s)->(t+1,s+1)` and
  `(t,s)->(t+2,s)` (columns shifted by two) succeed with at most four
  changed rows only sporadically; induction needs structured solutions.
* **Odd-block interval designs.**  A block of odd size `a` on rows
  `[p,p+a-1]` mapped by the half-rotation onto columns `[p',p'+a-1]` has
  sums forming the interval of length `a` centred at
  `(row centre)+(column centre)`.  So a permutation built from odd blocks
  (any odd composition of `t`, size-one blocks allowed, column intervals a
  rearrangement of the row intervals) has a sum set that is a union of
  intervals, and validity is a statement about intervals only: disjoint,
  inside `W`, no interval meeting the reflection of another.  The product
  theorem is the case of equal blocks with the outer structure an `FSP(b,s')`.
  `odd_block_design.py` searches all odd compositions for `t<=16`.
* **Odd-block designs exist for every `(t,s)` tested** (`t<=16`, all `s`
  in the window; the few `NONE` at `s in {0,1}` are being checked, since
  the identity is itself an all-singleton design).  The designs found are
  mostly "many singletons plus one odd block", sometimes pure products
  (`(3,3,3,3,3)`, `(5,5,5)`, `(7,7)`), and at the endpoints the single
  block.  So the problem may reduce to placing one odd block and choosing
  a sum-distinct assignment of the remaining singletons; that template is
  being tested (`one_block_template.py`).
* **Few large blocks do not suffice.**  With at most three or four odd
  half-rotated blocks the only reachable `(t,s)` are the products and the
  endpoints; the exhaustive odd-block designs use five to nine blocks
  including many singletons, i.e. they are essentially unstructured
  permutations.  A "singletons plus one block" template degenerates to an
  arbitrary permutation (a size-one block is free) and was discarded.
* Now testing structured induction from **product** solutions
  (`product_switch_test.py`): neighbours `(t,s+-1)`, `(t+1,s)`, `(t+2,s)`
  within small Hamming distance of a product solution.
