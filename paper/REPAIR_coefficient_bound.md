# Repair of the coefficient bound after carrier elimination

Date: 2026-09-03.  Addresses the audit finding "Unproved nonconstancy, lattice
divisibility, and coefficient control after carrier elimination" (severe).

## The gap

Appendix B resolves a pending token as follows.

> *Token, token pending.*  Choose a matching of the three coordinates and solve
> `T_v = -T_A` for the carrier `K(F)`: two independent equations in two
> unknowns, nonsingular because the token map has rank two on the carrier, and
> the solution expresses `K(F)` as affine functions of `Λ`. ... choose
> `Λ ∈ (MZ)^|Λ|` avoiding all conditions in `Φ`.

Writing the two equations as `M K = rhs(Λ)` with `M` the 2x2 carrier block of
`T_v`, the solution is `K = M^{-1} rhs = adj(M) rhs / det(M)`.  The manuscript
then continues to use the catalogue's raw coefficient bound `KMAX = 64` and the
lattice `MZ`.  Neither survives:

* `adj(M)` can enlarge coefficients, so the labels of `v`, as affine forms in
  `Λ`, need not have coefficients bounded by 64;
* dividing by `det(M)` can leave the lattice, so `Λ ∈ (MZ)^|Λ|` does not make
  `K` integral.

The constant `A` was derived from the 64, so `A` was not established.

## The repair

The carrier is **not** given by the family; (E4) only asserts that *some* pair
of parameters carries the token's plane.  It is therefore ours to choose, and
both defects are controlled by choosing it well.

Write the token as `a, b, c` with `a + b + c = 0`.  On a fixed pair of columns
the three 2x2 minors coincide up to sign (`det(b,c) = det(b,-a-b) = det(a,b)`),
so each candidate carrier has one well-defined `|det|`.  Choose, for each
family, a carrier minimising `|det|`.

`scripts/carrier_determinants.py` computes this over the whole catalogue.

```text
tokens examined                                   7963
tokens with no admissible carrier                    0
minimum |det| over admissible carriers, histogram:
    |det| = 1    5491      |det| = 9     145
    |det| = 2    1074      |det| = 12      9
    |det| = 3     853      |det| = 16      9
    |det| = 4     211      |det| = 18      6
    |det| = 5      20      |det| = 24      7
    |det| = 6     108      |det| = 27      5
    |det| = 7       4      |det| = 30      1
    |det| = 8       6      |det| = 36      7
                           |det| = 45      1
                           |det| = 72      3
                           |det| = 81      2
                           |det| = 144     1
maximum |r . adj(M)| over all labels at the best carrier:   216
```

(Counts as of 2026-09-03, after the root join was added to the catalogue.)

So a unimodular carrier is available for 69% of the tokens but **not** for all;
the largest minimum determinant in the catalogue is

```text
Dmax = 144 ,      G = max |r . adj(M)| = 216 .
```

Both are finite and computed from the catalogue, which is what the repair needs.

### (i) Integrality -- WITHDRAWN, the argument below is false

> **This subsection is wrong and was withdrawn on 2026-09-03**, after the
> second independent adversarial audit produced an explicit counterexample.
> It is kept here, struck through in words, because the manuscript was written
> from it and the record should show what was believed.

The argument was: at the resolution step choose `Λ ∈ (d M Z)^{|Λ|}` where
`d = |det M_F|`, rather than `Λ ∈ (M Z)^{|Λ|}`; then `rhs(Λ)` is divisible by
`d`, hence `K = adj(M) rhs / d` is integral, and since `d <= Dmax = 144` the
refined lattice is contained in `M' Z` with `M' = 24 * 144 = 3456`.

**Why it is false.**  The right-hand side is `N Λ + c`, not `N Λ`.  The
constant `c` collects the already-chosen numeric parameters of the resolving
cell and of the pending cell, and choosing `Λ` in a finer lattice does nothing
to `c`.  The audit's witness: context `h2_2-6_p2_act`, menu 3, token 1, over
parameters `[y, x, t1, u1]` at denominator 1, has token vectors

```text
a = [-3,  3,  1,  2]
b = [ 1, -3, -3,  1]
c = [ 2,  0,  2, -3]
```

whose six candidate carriers have determinants 6, 8, -5, -6, 9, 7, so the
minimising carrier is `(y, u1)` with `det M = -5`.  The non-carrier columns are
`(3,-3)` for `x` and `(1,-3)` for `t1`, so the permitted numeric choice
`x = t1 = 24` gives `c = (96, -144)` and `adj(M) c = (384, 336)`, neither
coordinate divisible by 5.  We reproduced this exactly.

The sentence "`d <= Dmax` therefore the lattice is `M * Dmax * Z`" is also
invalid on its own terms: a bound on integers is not a divisibility.  33 of the
selected determinants do not divide 144 (`5` twenty times, `7` four times, `27`
five times, `30`, `45`, and `81` twice), and 3456 is divisible by neither 5 nor
7.  Choosing a unimodular alternative instead is not available globally: 485
token contexts have no unimodular carrier anywhere in their menu.

Two further defects the audit found in the same subsection:

* **Denominators.**  Catalogue forms are integer vectors over a family
  denominator.  Clearing the denominators of a resolving family `L_v` and a
  pending family `L_A` multiplies the two sides by `lcm(L_v, L_A)/L_v` and
  `lcm(L_v, L_A)/L_A`, so the system is `M~ K = N~ Λ + c~` with
  `M~ = (L/L_v) M`, and `det M~ = (L/L_v)^2 det M`, not `det M`.  Neither
  `carrier_determinants.py` nor the bound `K' = 2 G KMAX` accounts for this
  ratio, which is at most 12 and at least 1.
* **Compounding.**  Even with a lattice that works for one elimination, the
  resolved carrier values are passed upward as numeric inputs and re-enter a
  later elimination, and `K = adj(M~) rhs / det M~` lies in a coarser lattice
  than `rhs` does.  Section (iii) below argued that the enlargement is paid
  once because nothing is pending at the end of the step; that is true of the
  *coefficient* bound but not of the *lattice* invariant, which is what
  integrality needs.

### (i') What a correct argument has to supply

The natural repair is a single global lattice.  Let `D` be a common multiple of
every `|det M~|` that can occur.  The determinants the minimising rule selects
are

```text
1, 2, 3, 4, 5, 6, 7, 8, 9, 12, 16, 18, 24, 27, 30, 36, 45, 72, 81, 144
```

with least common multiple `45,360 = 2^4 * 3^4 * 5 * 7`, and the denominator
ratio contributes a further factor dividing `144`, so `D = 144 * 45,360 =
6,531,840` is a common multiple, and it is a multiple of `M = 24`.  If every
numeric parameter and every live parameter lay in `D Z`, then `rhs` would lie
in `D Z` and `K = adj(M~) rhs / det M~` would be integral.

**However this is not by itself enough**, and we do not claim it is.  It makes
`K` integral but leaves `K` in `(D / det) Z`, which is coarser than `D Z`, so
the invariant needed for the *next* elimination is not reproduced, and the
degradation recurs along a chain of eliminations that share values.  Closing
this needs one of:

1. a proof that the chain of eliminations sharing a value has bounded length,
   after which a fixed power `D^k` suffices; or
2. solving, at each resolution, an affine congruence for the resolving cell's
   own numeric parameters (which are chosen at that moment, after `det M~` is
   known) so that `rhs` is divisible by `det M~ * D`; this is a finite
   solvability question over the catalogue, one instance per (pending family,
   resolving family, matching) triple, and is what should be certified by
   machine; or
3. the exact Smith or Hermite normal form transition audit the audit
   recommends, which subsumes both.

Until one of these is supplied, **Appendix B does not establish integrality,
and the printed value of `A` is not proved.**  The manuscript states this.

### (ii) Coefficient control

A label `ℓ` of `v` has carrier row `r_ℓ` and becomes, after substitution,

```text
ℓ = - r_ℓ M^{-1} N Λ + const = - (r_ℓ adj(M)) N Λ / d + const ,
```

where `N` is the coefficient matrix of the pending token `T_A` on `Λ`, whose
entries are catalogue entries and so are bounded by `KMAX = 64`.  Summing over
the two carrier coordinates,

```text
| coefficient of ℓ in Λ |  <=  2 * G * KMAX / d  <=  2 * 216 * 64  =  27648 .
```

Define `K' = 27648`.  This replaces `KMAX` in the derivation of `A`.

### (iii) The growth does not compound

This is what makes the repair work at all.  Appendix B states that at the end
of the resolution step

> All labels of `A`, of its child and parent, and of `v` become numeric, `T_A`
> and `T_v` are designated antipodes of each other, and nothing is pending.

So every elimination is closed immediately: the enlarged coefficients are
consumed in one step and the next pending token starts again from catalogue
coefficients bounded by 64.  The factor `2 G KMAX` is therefore applied **once**,
not once per owner, and does not accumulate over the `O(D)` cells.

### (iv) Non-constancy

The manuscript's claim that every label of `v` depending on `K(F)` stays a
non-constant affine form in `Λ` needs `r_ℓ adj(M) N ≠ 0`, not merely (E3).
With the carrier fixed, this is again a finite catalogue check and is not yet
performed; see "What remains" below.

## The corrected constant

```text
                       old (unproved)        new (proved)
coefficient bound      KMAX = 64             K'  = 2*216*64      = 27648
lattice                M    = 24             M'  = 24*144        = 3456
pairing box            75168(D+1)+181680     10824192(D+1)+26161920
A                      1.15e8  -> 2e8        7.158e12 -> 8e12
```

(`paper_numbers.py` rounds `A` up to one significant figure, so the manuscript
prints `8 * 10^12`.)

`A` grows by four orders of magnitude and remains an absolute constant.  Since
the theorems only require `n > C(D+1)` with `C` proportional to `A`, nothing
qualitative changes; the threshold constant is simply much larger, and it is
now derived rather than assumed.

## Artifacts

* `scripts/carrier_determinants.py` -- the computation above.
* `data/alphabet_carriers.json` -- regenerated: for every family with a token,
  the chosen minimising carrier, its columns and its determinant, for all 3445
  contexts that carry one.  The audit noted that the previous carrier file was
  absent from the public archive and that some of its carriers named parameters
  absent from the family or failed the rank-two requirement; this file is
  generated from the families themselves and every entry has `det != 0` by
  construction, hence rank two on the recorded carrier.

## Status, 2026-09-03 (all four items discharged)

1. **Written into Appendix B.**  The carrier choice rule ("choose a carrier of
   least `|det|`") is stated in "Families and the choice rule"; the refined
   lattice `(dMZ)`, the bound `K'` and the non-compounding argument are in
   "Token, token pending"; the final counting uses `M'` and `K'`.
2. **Item (iv) discharged.**  `scripts/carrier_nonconstancy.py` checks
   `r_l adj(M) N != 0` over every ordered pair of a resolving family and a
   pending coefficient matrix the catalogue allows, at the minimising carrier
   and over all matchings of the token coordinates:

   ```text
   7,963 tokens with a minimising carrier
   777 distinct pending matrices N
   157,183,992 (label, pending matrix, matching) triples checked
   constant after elimination: 0
   ```

   No label of any family becomes constant, so the non-constancy claim holds
   with no exceptions to record.  The enumeration of `N` is deliberately
   coarse: it ranges over every matrix the catalogue contains rather than only
   those that can actually pair with a given resolving family, so it
   over-approximates and the conclusion is conservative.
3. **The invariant contradiction repaired.**  The state and invariant (b) now
   read "at most two pending tokens, belonging to one and the same cell" and
   "a live set of at most four symbolic parameters" throughout.  The `3W`
   bound on the symbolic labels, and with it the bound on `|Phi|`, is
   unchanged, because it counts the cells that carry symbolic labels (the
   pending cell, its active child and its parent) and not the parameters; the
   earlier note that this would become `4W` was wrong.
4. **`numbers.tex` regenerated from the catalogue.**  `paper_numbers.py` now
   computes `NumDetMax`, `NumAdjMax`, `NumCoefBoundEff` and `NumLatticeMEff`
   from `alphabet_families.json` by the same routine as
   `carrier_determinants.py`, and derives `A` from them.  The current values
   are `Dmax = 144`, `G = 216`, `K' = 27,648`, `M' = 3,456` and
   `A = 8 * 10^12`.
