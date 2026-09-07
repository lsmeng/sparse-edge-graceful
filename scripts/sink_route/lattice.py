"""Exact integer linear algebra primitives: integer kernel basis (via column
reduction / unimodular column operations) and exact determinant (Bareiss).
No external dependencies (sympy not available in the target venv)."""
from math import gcd
from functools import reduce


def igcd(vals):
    vals = [abs(v) for v in vals]
    vals = [v for v in vals if v != 0] and vals  # keep zeros too, gcd(0,x)=x
    if not vals:
        return 0
    return reduce(gcd, vals)


def integer_kernel_basis(M):
    """M: m x n integer matrix (list of lists, rows). Returns list of basis
    vectors (each length n) spanning {x in Z^n : Mx = 0} as a FULL lattice
    (not merely a sublattice) -- this is exact for all inputs.

    Method: unimodular column operations reduce M to a column-echelon-like
    form while accumulating V (n x n, initially identity) via the same
    operations. A column of the transformed M that never becomes a pivot is,
    at the end, identically zero across every row; the corresponding column
    of V is then a valid kernel-basis vector, and the full set of such
    columns is a Z-basis of the kernel (standard unimodular-transform fact).
    """
    m = len(M)
    n = len(M[0]) if m else (len(M[0]) if M else 0)
    if m == 0:
        # no constraints: kernel is all of Z^n
        return [[1 if i == j else 0 for i in range(n)] for j in range(n)]
    n = len(M[0])
    A = [row[:] for row in M]
    V = [[1 if i == j else 0 for j in range(n)] for i in range(n)]

    def sub_col(target, src, q):
        if q == 0:
            return
        for r in range(m):
            A[r][target] -= q * A[r][src]
        for r in range(n):
            V[r][target] -= q * V[r][src]

    active = list(range(n))
    for row in range(m):
        if not active:
            break
        while True:
            nz = [c for c in active if A[row][c] != 0]
            if len(nz) <= 1:
                break
            nz.sort(key=lambda c: abs(A[row][c]))
            c1, c2 = nz[0], nz[1]
            q = A[row][c2] // A[row][c1]
            sub_col(c2, c1, q)
        nz = [c for c in active if A[row][c] != 0]
        if nz:
            piv = nz[0]
            active.remove(piv)
        # verify invariant cheaply in debug only (skipped for speed)
    # remaining `active` columns are identically zero in A -> kernel basis in V
    kernel_vecs = []
    for c in active:
        kernel_vecs.append([V[r][c] for r in range(n)])
    return kernel_vecs


def determinant(mat):
    """Exact integer determinant via Bareiss fraction-free elimination."""
    n = len(mat)
    if n == 0:
        return 1
    M = [row[:] for row in mat]
    sign = 1
    prev = 1
    for i in range(n - 1):
        if M[i][i] == 0:
            swap_row = None
            for r in range(i + 1, n):
                if M[r][i] != 0:
                    swap_row = r
                    break
            if swap_row is None:
                return 0
            M[i], M[swap_row] = M[swap_row], M[i]
            sign = -sign
        for j in range(i + 1, n):
            for k2 in range(i + 1, n):
                M[j][k2] = (M[j][k2] * M[i][i] - M[j][i] * M[i][k2]) // prev
            M[j][i] = 0
        prev = M[i][i]
    return sign * M[n - 1][n - 1]


def lattice_basis_and_index(C, L, k):
    """C: m x k integer matrix (rows = label coefficient vectors), L: denominator.
    Returns (B, det) where B is a k x k integer matrix (list of rows) whose
    COLUMNS are a Z-basis of Lambda_F = {p in Z^k : C p in L Z^m}, and det is
    det(B) (signed); |det| is the lattice index [Z^k : Lambda_F]."""
    m = len(C)
    # augmented matrix M = [C | -L I_m], size m x (k+m)
    Maug = []
    for i in range(m):
        row = list(C[i]) + [(-L if j == i else 0) for j in range(m)]
        Maug.append(row)
    kernel_vecs = integer_kernel_basis(Maug)
    assert len(kernel_vecs) == k, f"expected kernel rank {k}, got {len(kernel_vecs)}"
    # B columns = p-part (first k coords) of each kernel vector
    B = [[kernel_vecs[c][r] for c in range(k)] for r in range(k)]
    det = determinant(B)
    assert det != 0, "lattice basis matrix is singular (should not happen)"
    return B, det


def token_image_index(a, b, B, L, k):
    """a, b: length-k integer coefficient rows (of token labels). B: k x k
    lattice basis (columns = basis vectors), L: denominator. Returns the
    image index (gcd of 2x2 minors of T = [aB/L; bB/L], 0 if rank < 2)."""
    def row_times_B(vec):
        out = []
        for col in range(k):
            s = sum(vec[i] * B[i][col] for i in range(k))
            assert s % L == 0, f"non-exact division: {s} not divisible by {L}"
            out.append(s // L)
        return out

    TA = row_times_B(a)
    TB = row_times_B(b)
    minors = []
    for i in range(k):
        for j in range(i + 1, k):
            minors.append(TA[i] * TB[j] - TA[j] * TB[i])
    return igcd(minors), TA, TB


def naive_min_abs_minor(a, b, k):
    """Minimum |2x2 minor| of [a;b] taken over ALL pairs of the k ORIGINAL
    parameter columns (no basis change, no division by L). None if k < 2."""
    if k < 2:
        return None
    vals = []
    for i in range(k):
        for j in range(i + 1, k):
            vals.append(abs(a[i] * b[j] - a[j] * b[i]))
    return min(vals)
