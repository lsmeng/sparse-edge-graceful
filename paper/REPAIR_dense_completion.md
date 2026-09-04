# Repair of Lemma `lem:dense` (Section `sec:dense`)

Target: `paper/sparse_edge_graceful.tex`, lines 637-684.
Sources checked: `research/antimagic/ROBUST_PARTITION.md` (all sections),
`research/antimagic/LINEAR_DENSE_ZERO_SUM_TRIPLES.md`,
`research/antimagic/tmp/pdfs/muyesser_pokrovskiy_random_hall_paige_v3.txt` (quoted verbatim below).

---

## 0. Executive summary

1. The audit's finding is correct, and the gap is **worse than reported**. Besides the
   unjustified "triples may be taken in pairs `T`, `-T`" step, the proof paragraph violates the
   *perturbation hypothesis* of Muyesser-Pokrovskiy (MP) Lemma 6.24. With `p=1` that lemma
   demands that the set handed to it be **all but `o(n)` of `Z_n`**. The union of the triples
   has size `3o`, which is a small fraction of `n` as soon as a constant fraction of the blocks
   have even size. So the cited lemma is inapplicable in exactly the regime the paper needs.

2. The `ROBUST_PARTITION.md` "reserve inverse pairs first" ordering **does not repair
   `lem:dense` as stated**. The counting identity `2(K-L)=2P+3o` is correct and the reserve step
   is well defined, but after reserving `P` pairs the residue `X'` has size `3o` and
   `|Z_n\X'| = 1+2L+2P`. The note controls that quantity only by the *branch hypothesis*
   `P < h = M-L` of its own dichotomy, which bounds `P` by the core radius `M`. `lem:dense`
   carries no such hypothesis, and in the paper's actual application `P` is typically linear in
   `n` (every stationary vertex of degree three contributes a block of size two, and those are
   the majority in most trees). The note's complementary branch `P >= h` is a *deterministic
   interval-packing* argument that, as the note itself records, "still uses that all special
   magnitudes lie in a prefix `[1,M]`". `lem:dense` has no prefix geometry either. So the note
   is internally coherent for its own theorem but is not a proof of the manuscript's lemma.

3. **The gap does close.** `lem:dense` is true and provable exactly as stated, but by a
   different route: MP's own Lemma 6.27 shows how to accommodate zero-sum parts of size two,
   by choosing the reserved inverse pairs *at random* and applying Lemma 6.25 to two random
   halves (Lemma 6.26 is the coupling that makes this legitimate). Running that deduction in
   `Z_n` with `n` odd and with the deleted pairs excluded gives `lem:dense` whenever the blocks
   of size at least three carry a constant fraction of the labels; the complementary regime is
   elementary (twin triples `{a,b,-a-b}`, `{-a,-b,a+b}` plus inverse pairs) and needs no
   external input at all. LaTeX for the corrected proof is in Section 5 below.

4. **Both theorems survive, with the same dependence on the two readings as before.** The
   corrected proof invokes MP Lemma 6.25 with a *constant* `p >= 1/100`, never with `p=1`.
   Under the printed radius this gives `lem:dense` with `eta n` replaced by `c\,n/(\log n)^{10^{24}}`,
   hence Theorem `thm:main`; under the Section 7.4 abelian reading it gives the lemma as stated,
   hence Theorem `thm:linear`. Nothing in the repair shifts a result from one theorem to the
   other. The hedging in the manuscript about the Section 7.4 reading should however be
   sharpened; see Section 6.

---

## 1. What the manuscript currently says

```
This is the symmetric completion of \cite[Section~3]{ProjectNotes}: inverse
pairs fill the even parts, one zero-sum triple is assigned to each odd part,
and the triples come from Lemma~6.24 of \cite{MuyesserPokrovskiy2025} (the
case $k=3$) applied with $p=1$.  The number of odd parts is even, because
$|X|$ is even and congruent to that number modulo two, so the triples may be
taken in pairs $T$, $-T$ and the residue set left after removing them is again
symmetric and is filled by inverse pairs.
```

## 2. The two defects, precisely

### 2.1 The negation-invariance step (the audit's finding)

MP Lemma 6.24 reads, verbatim from the v3 text (line 3398):

> **Lemma 6.24.** Let `p >= n^{-1/10^100}` and `k = 3, 4, or 5`. Let `R` be a `p`-random subset
> of an abelian group `G`. With high probability the following holds.
> Let `X ⊆ G` with `|X△R| <= p^{10^10} n / log(n)^{10^18}`, `0 ∉ X`, `ΣX = 0`, and
> `|X| ≡ 0 (mod k)`. Then, `X` can be partitioned into zero-sum sets of size `k`.

The conclusion is a partition of the *whole* of `X`. The lemma offers no control over which
triples occur, so it cannot be asked for a prescribed number of triples, and it certainly does
not return a collection closed under negation. Parity of the number of odd blocks says only
that `o` is even; it is not a matching statement. The audit is right. The note itself flags the
same trap (`LINEAR_DENSE_ZERO_SUM_TRIPLES.md`, Consequence 6): "The triples supplied here are
arbitrary **signed** zero-sum triples. No negation-invariant or twin partition is asserted or
needed", with a `Z_31` example separating the two notions.

### 2.2 The perturbation hypothesis (not previously flagged)

With `p = 1` a `1`-random subset is `R = G` with probability one, so `|X△R| = n - |X|`. The
hypothesis of Lemma 6.24 therefore becomes

```
n - |X| <= n / log(n)^{10^18}.
```

Whatever set the manuscript feeds to the lemma must be **co-`o(n)` in `Z_n`**. The union of the
`o` triples has `3o` elements. Hence the argument as written silently requires `3o >= n(1-o(1))`,
that is, essentially every block has size three. That is false for the trees the paper is about.
This defect is independent of, and more serious than, 2.1: even granting a magic
negation-invariant triple collection, the cited lemma could not produce it.

### 2.3 Minor: the lemma number

Lemma 6.24 is the fixed-size (`k = 3, 4, 5`) statement. The variable-size statement is
Lemma 6.25 (v3 line 3463), and it is 6.25 that the corrected proof needs. `ROBUST_PARTITION.md`
Section 2 already cites 6.25; the manuscript cites 6.24. Both numbers exist, so this is a real
citation slip, not a renumbering artefact.

## 3. Audit of the `ROBUST_PARTITION.md` / `LINEAR_DENSE_ZERO_SUM_TRIPLES.md` ordering

### 3.1 The counting identity is correct

With `n = 2K+1`, `X` symmetric, `0 ∉ X`, `L` deleted inverse pairs, so `|X| = 2(K-L)`; and with
`p(r) = r/2` for even `r`, `p(r) = (r-3)/2` for odd `r >= 3`, `P = Σ_w p(r_w)`, `o = #{w : r_w odd}`:

```
Σ_w r_w = Σ_{r_w even} 2p(r_w) + Σ_{r_w odd} (2p(r_w)+3) = 2P + 3o,
```

so `2(K-L) = 2P + 3o`. Verified. Consequences also verified: `P <= K-L` (so the reserve set `Q`
exists), `3o <= |X|`, and `o` is even because `|X|` is even.

### 3.2 The block bookkeeping is correct

Reserve `P` inverse pairs; the residue `X' = X \ ±Q` is symmetric with `|X'| = 3o`, `0 ∉ X'`,
`ΣX' = 0`, `3 | |X'|`. Give each odd block one triple plus `p(r_w) = (r_w-3)/2` reserved pairs
(non-negative because `r_w >= 2` and odd forces `r_w >= 3`), each even block `p(r_w) = r_w/2`
reserved pairs. Sizes and zero sums are all correct, every size is at least two, and the pair
budget balances exactly. No objection here.

### 3.3 The hypothesis check is where it fails

`|Z_n \ X'| = 1 + 2L + 2P`. The note bounds this by `2M+1` using `P < h = M - L`, which is the
*defining hypothesis of the branch it is in*. `lem:dense` has no `M` and no such branch: `P` is
determined by the prescribed sizes and can be as large as `(K-L)`, in which case
`|Z_n \ X'| = n - 3o` and the lemma's radius is exceeded by a linear amount. Concretely, take
`n` large, `X = Z_n \ {0}`, two blocks of size three and `(n-7)/2` blocks of size two: then
`o = 2`, `P = (n-7)/2`, `|X'| = 6`, and MP Lemma 6.24 is nowhere near applicable, whether the
radius is `n/(\log n)^A` or `\eta n`.

This regime is not exotic. In the manuscript, blocks are the child-label sets of stationary
vertices, so a stationary vertex of degree `d` gives a block of size `d-1`. Every stationary
degree-three vertex therefore gives a block of size two, and a tree may have linearly many of
them. So the failing regime is the generic one.

### 3.4 What the note's other branch costs

The note's `P >= h` branch is deterministic ("prefix-saturation plus maximum mixed
interval-packing lemma", numerical hypothesis `K >= 7M+3`) and, by the note's own Consequence 3,
"still uses that all special magnitudes lie in a prefix `[1,M]`". I did not attempt to verify
that branch; the repair below does not use it, so its status is not on the critical path for the
manuscript. Note also that the note's Section 5 conjecture (linear punctured-interval packing)
is explicitly open, and its Section 6 obstruction (`n=9`, `X = ±{1,2,4}`, no zero-sum triple at
all) shows why no naive greedy can be pushed to the tight case.

**Verdict on task 2: the Section 3 / Section 2A ordering does not repair `lem:dense`.**

## 4. The repair that does work

The missing ingredient is already in MP: **Lemma 6.27** (v3 line 3612) is precisely the lemma
that admits zero-sum parts of size two,

> **Lemma 6.27.** Let `G` be a sufficiently large abelian group with `|I(G)| >= 3`, and
> `M ⊆ {2,3,4,5,...}` a multiset with `ΣM = n-1` and `m_2(M) <= f(G) - 0.0001n`. Then `G \ {0}`
> has a zero-sum `M`-partition.

and its proof explains how: rather than deleting a deterministic set of inverse pairs (which
destroys near-fullness), choose the reserved pairs **at random** and never invoke `p = 1` at all.
The key device is Lemma 6.26 (v3 line 3539), a coupling that writes a random union of inverse
pairs as a disjoint union of two genuinely `p/2`-random subsets of `G`:

> **Lemma 6.26.** Let `G` be a size `n` set and suppose `G` is partitioned as
> `G = {g_1,h_1} ∪ ... ∪ {g_m,h_m} ∪ I`. Let `Y` be a `p`-random subset of `[m]` and set
> `X = I ∪ ⋃_{i∈Y}{g_i,h_i}`. Then, we can partition `X = Q ∪ R ∪ S` where `Q, R` are disjoint
> and `p/2`-random subsets of `G`, and `S` is a `(1-p)`-random subset of `I`.

This matters because a union of inverse pairs is *never* close to a `p`-random set for
`0 < p < 1` (their symmetric difference is `Θ(p(1-p)n)`), so the naive "choose the reserved pairs
randomly" does not by itself satisfy MP's hypothesis. Lemma 6.26 is exactly the fix.

Lemma 6.27 itself cannot be cited: it assumes `|I(G)| >= 3` (so even order) and treats the full
group `G \ {0}` rather than a punctured set. However its *proof* uses only Lemmas 6.23, 6.25 and
6.26, each of which is stated for an arbitrary abelian group (6.26 for an arbitrary finite set),
and each of which applies verbatim to `Z_n` with `n` odd. Re-running that deduction with
`I(G) = ∅` and with the deleted pairs held out is routine, and it is what Section 5 below writes
out.

Two further points make the repair clean.

* **The involution-free case is simpler, not harder.** With `n` odd, `I(G) = ∅`, so the set `S`
  of Lemma 6.26 is empty, MP's `M^S` branch disappears, and the set handed to Lemma 6.23 is a
  union of inverse pairs and hence automatically has sum zero.
* **The one regime Lemma 6.27 excludes is elementary here.** MP need `m_2(M) <= f(G) - 0.0001n`,
  i.e. the parts of size at least three must carry a constant fraction of the group. In the
  complementary regime the number of blocks of size at least three is `O(n/100)`, so only `O(n)`
  magnitudes are ever consumed by non-pair blocks, and the explicit twin construction
  `T = {a, b, -(a+b)}`, `-T = {-a, -b, a+b}` with `a + b = c` in the available magnitude set
  settles it by a counting greedy. No external input at all.

### 4.1 Hypothesis check for the repaired argument

Set `N = Σ_{r_w >= 3} r_w`, `m_2 = #{w : r_w = 2}`, so `|X| = N + 2m_2`, and
`p := N/|X| = 1 - 2m_2/|X|`.

* `0 ∉ X'`: the sets handed to Lemma 6.25 are subsets of `X`, and `0 ∉ X`. OK.
* `ΣX' = 0`: arranged by Lemma 6.23 (`g = 0`), which is applicable because the ambient set
  `X_Y ∪ J^*` is a union of inverse pairs and so already has sum zero. OK.
* `|X'| = ΣM'`: arranged by Lemma 6.23 (exact target size `m`). OK.
* Sizes: the multiset handed to Lemma 6.25 is `{r_w : r_w >= 3} ⊆ {3,4,5,...}`, which is exactly
  the admissible class. OK.
* **Perturbation radius.** This is the only quantitative condition. Lemma 6.25 requires
  `|X' △ R| <= p'^{10^{10}} n / \log(n)^{10^{24}}` with `R` the `p' = p/2`-random reference set.
  Here `p >= 1/100`, so `p'^{10^{10}}` is an absolute constant, and the perturbation to absorb is
  `|Z_n \ X| + 6\varepsilon n` where `\varepsilon` is the Lemma 6.23 parameter. So the condition
  is `|Z_n \ X| <= c\,n/(\log n)^{10^{24}}` under the printed reading and `|Z_n \ X| <= \eta n`
  under the Section 7.4 abelian reading.

**Which radius is needed: the constant-`p` one, and only there.** The repaired proof never sets
`p = 1`. That is a genuine improvement over the manuscript's route, because the `p = 1` reading
is the one MP flag as a separate open problem (v3 line 3980, Problem 7.4).

---

## 5. Corrected LaTeX

Replace the paragraph at `sparse_edge_graceful.tex` lines 653-663 (the "This is the symmetric
completion of ..." paragraph) by the following. The lemma statement itself is unchanged.

```latex
\begin{proof}[Proof of Lemma~\ref{lem:dense}]
Write $n=2K+1$.  Since $n$ is odd and $X$ is symmetric with $0\notin X$, the set
$X$ is a disjoint union of inverse pairs $\{j,-j\}$; let $J\subseteq[1,K]$ be
the set of magnitudes occurring, so that $|X|=2|J|$ and
$|\Z_n\setminus X|=1+2(K-|J|)$.  In particular $|X|$ is even, so the number
$o$ of odd block sizes is even.  Let $m_2$ be the number of blocks of size two
and put $N=\sum_{r_w\ge3}r_w$, so that $|X|=N+2m_2$.  We fix
$\eta\le1/20$ and argue by cases according to the size of $N$.

\emph{Case 1: $N\le n/100$.}  In this case we use no external input.  A
\emph{twin} is a pair of magnitudes $a<b$ in $J$ with $a+b\in J$; it yields the
two zero-sum triples $\{a,b,-(a+b)\}$ and $\{-a,-b,a+b\}$, which are disjoint
and whose union $\pm\{a,b,a+b\}$ is symmetric.  We choose $o/2$ twins with
pairwise disjoint magnitude sets, greedily.  At the start of step $s$ the
forbidden magnitudes are those outside $J$, of which there are at most
$\eta n/2$, together with the $3(s-1)\le 3o/2\le N/2\le n/200$ already used.
Hence at most $(\eta+1/100)K+2$ magnitudes are forbidden.  On the other hand
the number of triples $\{a,b,a+b\}\subseteq[1,K]$ with $a<b$ is
$\sum_{c=3}^{K}\lfloor(c-1)/2\rfloor\ge K^2/5$ for $K$ large, whereas a single
magnitude lies in at most $2K+K/2+3$ of them.  Since
$(\eta+1/100)\cdot(5/2)<1/5$ for $\eta\le1/20$, a permissible twin survives at
every step once $n$ is large, although the margin is not optimised.  Now pair
the odd blocks arbitrarily, give the two triples of the $s$-th twin to the two
blocks of the $s$-th pair, and distribute the remaining magnitudes as inverse
pairs, $p(r_w)=\lfloor r_w/2\rfloor-[r_w\text{ odd}]$ of them to the block
$w$.  The count is exact, because
$\sum_w p(r_w)=(|X|-3o)/2=|J|-3o/2$ is precisely the number of magnitudes left
over.  Every block then has its prescribed size and sum zero.

\emph{Case 2: $N>n/100$.}  Here we run the argument of
\cite[Lemma~6.27]{MuyesserPokrovskiy2025} in $\Z_n$, which has no involutions,
and with the missing pairs held out.  Put $p=N/(2|J|)$, so
$1/100\le p\le1$ because $2|J|=|X|\le n$.  Enumerate all $K$ inverse pairs of
$\Z_n$ and let $Y$ be a $p$-random set of indices; by
\cite[Lemma~6.26]{MuyesserPokrovskiy2025} applied to the partition of $\Z_n$
into these pairs together with $\{0\}$, the union of the selected pairs splits
as $Q\sqcup R\sqcup S$ with $Q,R$ disjoint $p/2$-random subsets of $\Z_n$ and
$S\subseteq\{0\}$.  Let $Y_J$ be the set of selected indices whose magnitude
lies in $J$; it is $p$-random on $|J|$ indices with integral mean
$p|J|=|J|-m_2$, so its median equals its mean and, with probability at least
one half, $|Y_J|\le|J|-m_2$, while Chernoff's bound gives
$|Y_J|\ge|J|-m_2-\sqrt{n}\log n$ with high probability.  Fix an outcome in
which both hold and in which $Q$ and $R$ satisfy the conclusions of
\cite[Lemmas~6.23 and~6.25]{MuyesserPokrovskiy2025}.  Reserve $m_2$ of the
$|J|-|Y_J|$ unselected available pairs for the blocks of size two, let $J^{*}$
be the union of the at most $\sqrt n\log n$ remaining unselected available
pairs, and put $Z=J^{*}\cup\bigcup_{i\in Y_J}\{i,-i\}$, a union of inverse
pairs with $|Z|=2|J|-2m_2=N$ and $\sum Z=0$.

Reduce the multiset $\{r_w:r_w\ge3\}$ to a multiset $M'\subseteq\{3,4,5\}$ as
in the first paragraph of the proof of
\cite[Lemma~6.25]{MuyesserPokrovskiy2025}, recombining at the end, and split
$M'=M^{Q}\sqcup M^{R}$ by halving the multiplicity of each of $3,4,5$.  Let
$\varepsilon=(p/2)^{10^{10}}/(6\log(n)^{10^{24}})$, which lies in the range
permitted by \cite[Lemma~6.23]{MuyesserPokrovskiy2025} once $n$ is large.  Both
$Q\setminus Z$ and $R\setminus Z$ are contained in $\{0\}\cup(\Z_n\setminus X)$
and hence have size at most $|\Z_n\setminus X|$, and
$\bigl|\sum M^{Q}-pn/2\bigr|\le|\Z_n\setminus X|+O(\sqrt n\log n)$; so if
$|\Z_n\setminus X|\le\varepsilon n/2$ then
\cite[Lemma~6.23]{MuyesserPokrovskiy2025}, applied with $R=Q$, $Z$ as above,
$m=\sum M^{Q}$ and $g=0$, returns $Q'\subseteq Z$ with $|Q'|=\sum M^{Q}$,
$\sum Q'=0$ and $|Q'\triangle Q|\le6\varepsilon n$.  Put $R'=Z\setminus Q'$;
then $|R'|=\sum M^{R}$, and $\sum R'=\sum Z-\sum Q'=0$, and
$|R'\triangle R|\le6\varepsilon n+|\Z_n\setminus X|+|J^{*}|$.  Therefore
\cite[Lemma~6.25]{MuyesserPokrovskiy2025} applies to $Q'$ with the reference
set $Q$ and the multiset $M^{Q}$, and to $R'$ with $R$ and $M^{R}$, and returns
zero-sum partitions of $Q'$ and of $R'$ of the prescribed sizes.  Together with
the $m_2$ reserved inverse pairs these fill every block, since
$Z\sqcup(\text{reserved pairs})=X$.  Thus $X$ has the required partition
whenever $|\Z_n\setminus X|\le\varepsilon n/2$, and $\varepsilon$ depends only
on $p\ge1/100$ and on $n$ through the logarithm.
\end{proof}
```

and replace the following paragraph ("Two readings of ...") by:

```latex
Two readings of \cite{MuyesserPokrovskiy2025} enter through the parameter
$\varepsilon$ of the last proof, and they give the two thresholds of
Section~\ref{sec:intro}.  The printed perturbation radius of their
Theorems~4.3--4.7, and hence of their Lemmas~6.23 and~6.25, is
$p^{A}n/(\log n)^{A}$; since the proof above uses those lemmas only with
$p\ge1/200$, this gives Lemma~\ref{lem:dense} with $\eta n$ replaced by
$n/(\log n)^{A}$, and hence Theorem~\ref{thm:main}.  Their Section~7, under
\emph{Bounds in the main theorem}, records that $\log n$ may be replaced by
$\log|G'|$ throughout the proof, the only source of logarithms being their
short commutator-product theorem, and for an abelian group the commutator
subgroup is trivial and the commutator product is empty; the authors record
the consequence $g(n)=\Omega(n)$ for cyclic groups in their Problem~7.4.  One
should read their commutator length as bounded by $\max(1,\log_4|G'|)$ rather
than divide by $\log1$.  Their Lemmas~6.23 and~6.25 are deduced from
Theorems~4.4--4.6 with no further logarithmic loss, the auxiliary error terms
being of order $\sqrt n\log n$, so at every fixed reservoir density this
reading leaves a positive constant perturbation radius and gives
Lemma~\ref{lem:dense} as stated, which is the hypothesis of
Theorem~\ref{thm:linear}.  This improvement is described by the authors as
requiring essentially no modification of their proof, although neither it nor
its consequence for their Section~6.3 is a printed theorem.  The constant
$\eta$ is in either case inherited from their argument and is not effective.
```

Notes on the LaTeX:

* No em dashes; the connectives are `However`/`Thus`/`although`/`Therefore`/`Hence` in the
  manuscript's register; the hedge "although the margin is not optimised" matches the existing
  "we have made no attempt to optimise it".
* `p(r_w)` is written as `\lfloor r_w/2\rfloor-[r_w\text{ odd}]`; if the manuscript prefers, define
  `p(r)` once before the proof.
* Case 2 as written assumes `m_2 >= 1` implicitly only through `p <= 1`; when `m_2 = 0` one has
  `p = 1`, `Y_J` is everything, `J^* = ∅`, and the argument degenerates gracefully to a direct
  application of Lemma 6.25 to `X`. Worth one sentence if a referee is fussy.
* The bibliography item `\cite[Section~3]{ProjectNotes}` is no longer cited by this proof and can
  be dropped from the paragraph.

## 6. Residual caveats, stated plainly

1. **Theorem `thm:main` is not affected by the repair's dependencies.** Case 1 is
   self-contained. Case 2 uses only MP Lemmas 6.23, 6.25 and 6.26 as printed, with a constant
   `p`, so `thm:main` stands on printed statements.

2. **Theorem `thm:linear` still needs the unprinted reading, and needs slightly more of it than
   the manuscript currently claims.** The manuscript's hypothesis is phrased as "their zero-sum
   matching theorems hold in `Z_n` with a linear number of deleted residues", i.e. at the level
   of Theorems 4.3-4.7. The lemma actually consumes Lemmas 6.23 and 6.25, which are *deductions*
   from those theorems. The deduction introduces no new logarithm (the only other error terms in
   6.23-6.25 are Chernoff terms of order `√n log n`), so the extension is mechanical, but the
   constants must be re-derived and MP do not do it. The revised paragraph above says this. I
   would not go further than "no printed theorem", which is what the manuscript already says.

3. **MP themselves pose the `p = 1` non-partite question as open** (v3, Problem 7.4: "what is the
   smallest subset `S ⊆ Z_n` with `|S|` divisible by 3, `ΣS = 0`, and `S` cannot be partitioned
   into triples with zero-sum?"). The manuscript's original route ran straight through that
   question; the repaired route does not, which is a strict improvement in citation hygiene.

4. **`n_1` and `\eta` remain ineffective**, unchanged.

5. **Case 1's constants are crude but safe.** `\eta <= 1/20` and the split at `N = n/100` were
   chosen to make the counting transparent; MP's own threshold in Lemma 6.27 is `0.0001n`, so
   there is a wide corridor and no tuning is needed. If the manuscript prefers a single named
   constant, take `\eta = 1/20` and split at `N = n/100` as written.

6. **One thing I did not verify**, because the repair does not use it: the note's `P >= h`
   deterministic branch ("saturating-holes corollary", "maximum mixed interval-packing lemma",
   `K >= 7M+3`). If that branch is ever wanted for an effective or constructive version, it
   should be audited separately, and note that it needs the prefix hypothesis `I ⊆ [1,M]` which
   `lem:dense` does not carry.

## 7. Literature note (task 4)

Since the gap closes, the search for a substitute theorem is not needed. For the record, the
relevant landscape is:

* **Odd-order abelian groups, full group, sizes `>= 2`:** Tannenbaum [56 in MP] gives necessary
  and sufficient conditions (`M ⊆ {2,3,...}` and `ΣM = n-1`), and this is what the `D = 0` case
  of the paper uses via Kaplan-Lev-Roditty. It is the *unpunctured* statement, so it does not
  apply here.
* **Cyclic groups, sizes `>= 3`:** Friedlander, Gordon and Tannenbaum (1981), complete solution.
* **Cichacz's conjecture** (MP Conjecture 1.6) and Tannenbaum's problem for even order are
  settled by MP Section 6.3 (Theorem 6.36 and Lemmas 6.27-6.30).
* I found **no** theorem in this literature asserting a *negation-invariant* or *twin* zero-sum
  triple partition, and the note's `Z_31` example plus its `n = 9` obstruction
  (`X = ±{1,2,4}` has no zero-sum triple at all) indicate that the signed and magnitude versions
  genuinely differ. The corrected proof avoids needing one: twins are used only in Case 1, where
  they are constructed by hand with a linear amount of slack, and Case 2 uses arbitrary signed
  sets.
