"""Exact-decimal helpers.

Reported numbers are *rounded* numbers. A reported "2.20" means "any value in
[2.195, 2.205]". Every check in StatSleuth works on these rounding intervals
instead of on the printed value, which is what removes most false alarms.
All interval arithmetic is done with Fraction so there is no float noise.
"""
from __future__ import annotations

import math
from decimal import Decimal
from fractions import Fraction


def n_decimals(s: str) -> int:
    """Number of digits after the decimal point in a numeric string."""
    s = s.strip()
    return len(s.split(".")[1]) if "." in s else 0


def to_fraction(s: str) -> Fraction:
    return Fraction(Decimal(s.strip().replace(",", "")))


def half_unit(s: str) -> Fraction:
    """Half of the last printed decimal place: 2.20 -> 0.005."""
    return Fraction(1, 2 * 10 ** n_decimals(s))


def interval(s: str) -> tuple[Fraction, Fraction]:
    """Closed rounding interval of a printed number."""
    v, h = to_fraction(s), half_unit(s)
    return v - h, v + h


def fmt_p(x: float) -> str:
    """APA-style p-value formatting for messages."""
    if x < 0.001:
        return "< .001"
    s = f"{x:.3f}"
    return s.lstrip("0") if x < 1 else "1.000"


def fmt_num(x: float, digits: int = 4) -> str:
    if x == 0:
        return "0"
    if abs(x) < 10 ** -digits:
        return f"{x:.2e}"
    return f"{x:.{digits}f}".rstrip("0").rstrip(".")


def ceil_frac(x: Fraction) -> int:
    return math.ceil(x)


def floor_frac(x: Fraction) -> int:
    return math.floor(x)
