"""GRIM and GRIMMER consistency tests for integer-valued data.

GRIM  (Brown & Heathers, 2017): the mean of N integers is a multiple of 1/N.
GRIMMER (Anaya, 2016): the SD of N integers with sum S must also be reachable.

Both tests are *necessary-condition* tests. They never flag a (mean, SD) pair
that some set of integers could produce, so a flag means "mathematically
impossible for integer data of this size", not "fraudulent".
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from fractions import Fraction

from .numeric import interval, n_decimals


@dataclass
class GrimResult:
    consistent: bool
    informative: bool          # False when n is so large the test cannot fail
    candidate_sums: list[int] = field(default_factory=list)
    nearest_possible: list[str] = field(default_factory=list)
    note: str = ""


def _sum_range(mean_s: str, n: int, items: int) -> tuple[int, int]:
    lo, hi = interval(mean_s)
    total = n * items
    return math.ceil(lo * total), math.floor(hi * total)


def grim(mean_s: str, n: int, items: int = 1) -> GrimResult:
    """Is the reported mean reachable as (integer sum) / (n * items)?

    The rounding interval is closed on both ends, so the test is charitable to
    both round-half-up and round-half-even conventions.
    """
    if n < 1:
        raise ValueError("n must be >= 1")
    total = n * items
    d = n_decimals(mean_s)
    informative = Fraction(total, 1) < 10 ** d       # grid coarser than rounding
    smin, smax = _sum_range(mean_s, n, items)
    sums = list(range(smin, smax + 1))
    if sums:
        return GrimResult(True, informative, sums)
    # not reachable: report the closest reachable means to help the user fix it
    lo, hi = interval(mean_s)
    centre = (lo + hi) / 2
    k = round(centre * total)
    near = sorted({k - 1, k, k + 1})
    nearest = [f"{float(Fraction(s, total)):.{d}f}" for s in near]
    return GrimResult(False, informative, [], nearest,
                      f"No integer sum S gives S/{total} rounding to {mean_s}.")


@dataclass
class GrimmerResult:
    consistent: bool
    informative: bool
    note: str = ""


def grimmer(mean_s: str, sd_s: str, n: int) -> GrimmerResult:
    """Necessary-condition GRIMMER for single-item integer data (sample SD, n-1).

    For integer data with sum S and sum of squares Q:
        Var = (Q - S^2/n) / (n-1),   Q = S (mod 2),   Q >= Qmin(S)
    where Qmin(S) is the smallest Q any n integers with sum S can reach (values
    as equal as possible). We search the sums allowed by the mean and ask
    whether some integer Q with these properties yields the reported SD.
    """
    if n < 2:
        return GrimmerResult(True, False, "SD undefined for n < 2")
    g = grim(mean_s, n)
    if not g.consistent:
        return GrimmerResult(False, True, "Mean itself fails GRIM")
    s_lo, s_hi = interval(sd_s)
    s_lo = max(s_lo, Fraction(0))
    var_lo, var_hi = s_lo * s_lo, s_hi * s_hi
    informative = False
    for S in g.candidate_sums:
        base = Fraction(S * S, n)
        q_lo = base + (n - 1) * var_lo
        q_hi = base + (n - 1) * var_hi
        r = S % n
        q = S // n
        q_min = (n - r) * q * q + r * (q + 1) ** 2
        a = max(math.ceil(q_lo), q_min)
        b = math.floor(q_hi)
        if a > b:
            informative = True
            continue
        if b - a >= 1:           # two consecutive integers => both parities
            return GrimmerResult(True, True)
        if a % 2 == S % 2:
            return GrimmerResult(True, True)
        informative = True
    return GrimmerResult(False, True,
                         "No integer data set of this size can give this mean and SD.")


def brute_force_pairs(n: int, lo: int, hi: int, d_mean: int, d_sd: int) -> set[tuple[str, str]]:
    """Exhaustive ground truth used only in evaluation: every (mean, SD) pair
    reachable by n integers on [lo, hi], rounded to the given decimals."""
    from itertools import combinations_with_replacement
    from decimal import Decimal, ROUND_HALF_UP

    out: set[tuple[str, str]] = set()
    qm = Decimal(1).scaleb(-d_mean)
    qs = Decimal(1).scaleb(-d_sd)
    for combo in combinations_with_replacement(range(lo, hi + 1), n):
        S = sum(combo)
        Q = sum(x * x for x in combo)
        mean = Decimal(S) / Decimal(n)
        var = (Decimal(Q) - Decimal(S * S) / Decimal(n)) / Decimal(n - 1)
        sd = var.sqrt() if var > 0 else Decimal(0)
        out.add((str(mean.quantize(qm, ROUND_HALF_UP)), str(sd.quantize(qs, ROUND_HALF_UP))))
    return out
