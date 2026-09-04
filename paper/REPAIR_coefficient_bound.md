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
tokens examined                                   7962
tokens with no admissible carrier                    0
minimum |det| over admissible carriers, histogram:
    |det| = 1    5490      |det| = 9     145
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

So a unimodular carrier is available for 69% of the tokens but **not** for all;
the largest minimum determinant in the catalogue is

```text
Dmax = 144 ,      G = max |r . adj(M)| = 216 .
```

Both are finite and computed from the catalogue, which is what the repair needs.

### (i) Integrality

At the resolution step choose `Λ ∈ (d M Z)^{|Λ|}` where `d = |det M_F|` is the
determinant of the chosen carrier, rather than `Λ ∈ (M Z)^{|Λ|}`.  Then
`rhs(Λ)` is divisible by `d`, hence `K = adj(M) rhs / d` is integral and lies in
`M Z` as before.  Since `d <= Dmax = 144`, the refined lattice is contained in
`M' Z` with

```text
M' = M * Dmax = 24 * 144 = 3456 .
```

The only cost is that the box in which `Λ` is chosen grows by the factor `d`,
because a lattice point avoiding `|Φ|` proper affine conditions still exists in
a box of side `M'(|Φ|+1)`.

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
A                      1.15e8  -> 2e8        7.158e12 -> 1e13
```

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

## What remains before Appendix B is sound

1. Write (i)-(iii) into Appendix B, and state the carrier choice rule ("choose
   a carrier of minimal `|det|`") in the choice rule of the appendix, since the
   constant now depends on it.
2. Discharge (iv): check over the catalogue that `r_ℓ adj(M) N ≠ 0` for every
   label that depends on the carrier, or record the finitely many exceptions.
   This is a pair check over (family, pending family) and is the one part of
   this repair not yet computed.
3. Repair the separate contradiction in the state invariant: the appendix
   declares "at most one pending token ... at most three symbolic parameters"
   and later allows two pending tokens and four carrier parameters.  The
   executable realiser stores two.  The invariant should be stated with two and
   four throughout, and the `|Φ|` and box bounds re-derived accordingly, which
   changes `3W` to `4W` in the counting.
4. Regenerate `numbers.tex` so that `G`, `Dmax`, `K'` and `M'` are computed from
   the catalogue rather than written in by hand.
