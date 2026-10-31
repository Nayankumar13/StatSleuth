"""The consistency checks. Each returns a Finding (or None).

Status vocabulary
  ok            reported numbers are mutually consistent (given rounding)
  caveat        consistent only under an assumption (one-tailed, correction, adjustment)
  minor         inconsistent, but statistical significance at alpha is unchanged
  gross         inconsistent AND significance at alpha flips, or arithmetic impossibility
  unverifiable  not enough information to check
  na            check does not apply (e.g. continuous measure for GRIM)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, asdict
from fractions import Fraction
from typing import Any, Optional

from scipy import stats
from scipy.optimize import brentq

from . import parser as P
from .grim import grim, grimmer
from .numeric import fmt_num, fmt_p, half_unit, interval, n_decimals, to_fraction

TOL = 1e-12
SEVERITY = {"ok": "ok", "caveat": "info", "minor": "warning", "gross": "error",
            "unverifiable": "info", "na": "info"}


@dataclass
class Finding:
    kind: str                  # pvalue | grim | grimmer | percent | ci | df_n
    status: str
    title: str
    explanation: str
    start: int
    end: int
    raw: str
    details: dict[str, Any] = field(default_factory=dict)
    suggestion: str = ""
    id: int = 0
    severity: str = ""

    def to_dict(self) -> dict:
        self.severity = SEVERITY[self.status]
        return asdict(self)


# --------------------------------------------------------------------------
# p-value recomputation
# --------------------------------------------------------------------------
def p_from_stat(kind: str, stat: float, df1: Optional[float], df2: Optional[float]) -> float:
    x = abs(stat)
    if kind == "t":
        return float(2 * stats.t.sf(x, df1))
    if kind == "F":
        return float(stats.f.sf(stat, df1, df2))
    if kind == "chi2":
        return float(stats.chi2.sf(stat, df1))
    if kind == "r":
        x = min(x, 1 - 1e-12)
        t = x * math.sqrt(df1 / (1 - x * x))
        return float(2 * stats.t.sf(t, df1))
    if kind == "z":
        return float(2 * stats.norm.sf(x))
    raise ValueError(kind)


def p_range(kind, stat_s: str, df1, df2) -> tuple[float, float, float]:
    """(p_low, p_high, p_point) given rounding of the printed statistic.

    p decreases as |statistic| grows, so the largest p comes from the smallest
    |statistic| inside the rounding interval and vice versa.
    """
    lo, hi = (float(v) for v in interval(stat_s))
    point = float(to_fraction(stat_s))
    if kind in ("F", "chi2"):
        s_lo, s_hi, pt = max(lo, 0.0), hi, point
    else:
        s_hi = max(abs(lo), abs(hi))
        s_lo = 0.0 if lo <= 0 <= hi else min(abs(lo), abs(hi))
        pt = abs(point)
    return (p_from_stat(kind, s_hi, df1, df2), p_from_stat(kind, s_lo, df1, df2),
            p_from_stat(kind, pt, df1, df2))


def reported_range(rel: str, p_s: str) -> tuple[float, float, float]:
    p = float(to_fraction(p_s))
    h = float(half_unit(p_s))
    if rel == "=":
        return max(p - h, 0.0), min(p + h, 1.0), p
    if rel == "<":
        return 0.0, p, p
    return p, 1.0, p


def overlap(a: tuple[float, float], b: tuple[float, float]) -> bool:
    return a[0] <= b[1] + TOL and b[0] <= a[1] + TOL


def _sig(rel: str, p: float, alpha: float) -> Optional[bool]:
    if rel in ("=", "<"):
        return p < alpha or (rel == "<" and p <= alpha)
    if rel == ">":
        return False if p >= alpha else None
    return None


def label(r: P.Result) -> str:
    if r.kind == "t":
        return f"t({r.df1}) = {r.stat}"
    if r.kind == "F":
        return f"F({r.df1}, {r.df2}) = {r.stat}"
    if r.kind == "chi2":
        return f"χ²({r.df1}) = {r.stat}"
    if r.kind == "r":
        return f"r({r.df1}) = {r.stat}"
    return f"z = {r.stat}"


def check_pvalue(r: P.Result, alpha: float) -> Finding:
    ttl = f"{label(r)}, p {r.p_rel} {r.p}"
    base = dict(kind="pvalue", start=r.start, end=r.end, raw=r.raw)
    df1 = float(r.df1) if r.df1 else None
    df2 = float(r.df2) if r.df2 else None
    stat = float(to_fraction(r.stat))

    # impossible inputs ----------------------------------------------------
    if r.kind in ("F", "chi2") and stat < 0:
        return Finding(status="gross", title=ttl, explanation=f"A {r.kind} statistic cannot be negative.",
                       suggestion="Check the sign of the statistic.", **base)
    if r.kind == "r" and abs(stat) >= 1:
        return Finding(status="gross", title=ttl, explanation="A correlation must lie strictly between -1 and 1.", **base)
    if (df1 is not None and df1 <= 0) or (df2 is not None and df2 <= 0):
        return Finding(status="gross", title=ttl, explanation="Degrees of freedom must be positive.", **base)

    lo, hi, pt = p_range(r.kind, r.stat, df1, df2)
    rlo, rhi, rpt = reported_range(r.p_rel, r.p)
    ctx = r.ctx
    details: dict[str, Any] = {
        "test": label(r), "reported_p": f"{r.p_rel} {r.p}",
        "computed_p": pt, "computed_p_range": [lo, hi],
        "reported_p_range": [rlo, rhi], "alpha": alpha,
    }

    notes: list[str] = []
    if r.p_rel == "=" and to_fraction(r.p) == 0:
        notes.append("p = .000 is not a valid p-value; report p < .001.")

    if overlap((lo, hi), (rlo, rhi)):
        expl = (f"Recomputed p = {fmt_p(pt)} (range {fmt_num(lo)}–{fmt_num(hi)} given rounding) "
                f"agrees with the reported p {r.p_rel} {r.p}.")
        if notes:
            expl += " " + " ".join(notes)
        return Finding(status="ok", title=ttl, explanation=expl, details=details, **base)

    # not consistent as a plain two-sided test: try the legitimate alternatives
    # 1. stated or plausible one-tailed test
    if r.kind in ("t", "z", "r") and overlap((lo / 2, hi / 2), (rlo, rhi)):
        stated = bool(P.KW_ONETAIL.search(ctx))
        details["one_tailed_p"] = pt / 2
        if stated:
            return Finding(status="ok", title=ttl,
                           explanation=f"Consistent as a one-tailed test (one-tailed p = {fmt_p(pt/2)}); the text says the test is one-tailed.",
                           details=details, **base)
        return Finding(status="caveat", title=ttl,
                       explanation=(f"Two-sided p would be {fmt_p(pt)}, but the reported value matches a ONE-tailed test "
                                    f"(p = {fmt_p(pt/2)}). The text does not say the test is one-tailed."),
                       suggestion="State that the test is one-tailed, or report the two-sided p.",
                       details=details, **base)

    # 2. sphericity (Greenhouse-Geisser / Huynh-Feldt) corrected F
    if r.kind == "F" and df1 and df1 > 1 and (P.KW_CORRECTION.search(ctx) or r.doc_correction):
        eps_min = 1.0 / df1
        c_lo = p_from_stat("F", float(interval(r.stat)[1]), df1, df2)
        c_hi = p_from_stat("F", max(float(interval(r.stat)[0]), 0.0), eps_min * df1, eps_min * df2)
        details["correction_p_range"] = [c_lo, c_hi]
        details["epsilon_bounds"] = [eps_min, 1.0]
        if overlap((c_lo, c_hi), (rlo, rhi)):
            eps = None
            try:
                f = lambda e: p_from_stat("F", stat, e * df1, e * df2) - min(max(rpt, c_lo), c_hi)
                eps = brentq(f, eps_min, 1.0)
            except Exception:
                pass
            details["epsilon_estimate"] = eps
            return Finding(
                status="caveat", title=ttl,
                explanation=("The reported p does not match the UNcorrected degrees of freedom, but it is reachable with a "
                             "sphericity correction (epsilon between %.2f and 1)%s. The text mentions such a correction, "
                             "so this is plausible rather than an error." %
                             (eps_min, f"; fitted epsilon ≈ {eps:.2f}" if eps else "")),
                suggestion="Report the corrected degrees of freedom (or epsilon) next to the F statistic.",
                details=details, **base)
        notes.append("Not reachable even with the strongest sphericity correction.")

    # 3. multiple-comparison adjusted p (adjustment can only increase p)
    if (P.KW_ADJUST.search(ctx) or r.doc_adjust) and rlo >= lo - TOL and r.p_rel in ("=", ">"):
        return Finding(status="caveat", title=ttl,
                       explanation=(f"Reported p is larger than the unadjusted p ({fmt_p(pt)}), which is what a multiple-comparison "
                                    f"adjustment does. The text mentions an adjustment, so this cannot be verified from the numbers alone."),
                       details=details, **base)

    # genuinely inconsistent -------------------------------------------------
    sig_rep = _sig(r.p_rel, rpt, alpha)
    sig_calc = pt < alpha
    gross = sig_rep is not None and sig_rep != sig_calc
    direction = ""
    if r.p_rel == "=":
        direction = " (reported p is too small)" if rpt < pt else " (reported p is too large)"
    expl = (f"Recomputed p = {fmt_p(pt)} (range {fmt_num(lo)}–{fmt_num(hi)} given rounding of the statistic) "
            f"does not match the reported p {r.p_rel} {r.p}{direction}.")
    if gross:
        expl += f" This changes significance at α = {alpha:g}: reported {'significant' if sig_rep else 'non-significant'}, recomputed {'significant' if sig_calc else 'non-significant'}."
    if notes:
        expl += " " + " ".join(notes)
    return Finding(
        status="gross" if gross else "minor", title=ttl, explanation=expl,
        suggestion=("Check the statistic, df and p against the analysis output. If a correction or adjustment was applied, say so "
                    "in the text next to the result."),
        details=details, **base)


# --------------------------------------------------------------------------
# GRIM / GRIMMER
# --------------------------------------------------------------------------
def check_mean(m: P.MeanSD, items: int, integer_data: bool) -> list[Finding]:
    base = dict(start=m.start, end=m.end, raw=m.raw)
    ttl = f"M = {m.mean}, SD = {m.sd}" + (f", n = {m.n}" if m.n else "")
    if not integer_data:
        return [Finding(kind="grim", status="na", title=ttl,
                        explanation="GRIM/GRIMMER skipped: integer-data assumption is switched off.", **base)]
    if m.unit_hint:
        return [Finding(kind="grim", status="na", title=ttl,
                        explanation="Skipped: a unit (ms, kg, %, ...) next to this value suggests a continuous measure, for which GRIM does not apply.", **base)]
    if not m.n:
        return [Finding(kind="grim", status="unverifiable", title=ttl,
                        explanation="No sample size (n = ...) found near this mean, so GRIM cannot be run.", **base)]
    if m.n < 2:
        return [Finding(kind="grim", status="unverifiable", title=ttl, explanation="n < 2.", **base)]
    out: list[Finding] = []
    g = grim(m.mean, m.n, items)
    det = {"mean": m.mean, "sd": m.sd, "n": m.n, "items": items, "n_source": m.n_source}
    if not g.informative:
        out.append(Finding(kind="grim", status="na", title=ttl,
                           explanation=f"n is too large for GRIM to be informative at {n_decimals(m.mean)} decimals (every mean is reachable).",
                           details=det, **base))
    elif g.consistent:
        out.append(Finding(kind="grim", status="ok", title=ttl,
                           explanation=f"Mean {m.mean} is reachable with n = {m.n} (integer sum {g.candidate_sums[0]}).",
                           details=det, **base))
    else:
        det["nearest_possible_means"] = g.nearest_possible
        out.append(Finding(
            kind="grim", status="gross", title=ttl,
            explanation=(f"No set of {m.n} whole numbers has a mean that rounds to {m.mean}. "
                         f"Closest reachable means: {', '.join(g.nearest_possible)}."),
            suggestion=(f"Check n and the mean. This is only valid if the data are integers (single items, counts). "
                        f"For averaged scales set 'items per scale' (currently {items}). n found: {m.n_source}."),
            details=det, **base))
    if items == 1 and g.consistent and g.informative:
        gm = grimmer(m.mean, m.sd, m.n)
        if gm.informative and not gm.consistent:
            out.append(Finding(
                kind="grimmer", status="gross", title=ttl,
                explanation=(f"The mean {m.mean} is possible with n = {m.n}, but no set of {m.n} whole numbers has this mean AND "
                             f"an SD that rounds to {m.sd} (GRIMMER)."),
                suggestion="Check the SD. Valid only for integer data.", details=det, **base))
        elif gm.informative:
            out.append(Finding(kind="grimmer", status="ok", title=ttl,
                               explanation=f"SD {m.sd} is reachable together with mean {m.mean} for n = {m.n}.",
                               details=det, **base))
    return out


# --------------------------------------------------------------------------
# k/n (pct)
# --------------------------------------------------------------------------
def check_pct(pc: P.Pct) -> Finding:
    base = dict(kind="percent", start=pc.start, end=pc.end, raw=pc.raw)
    ttl = f"{pc.k}/{pc.n} ({pc.pct}%)"
    if pc.n == 0 or pc.k > pc.n:
        return Finding(status="gross", title=ttl, explanation=f"{pc.k} cannot be a part of {pc.n}.", **base)
    exact = Fraction(100 * pc.k, pc.n)
    lo, hi = interval(pc.pct)
    det = {"k": pc.k, "n": pc.n, "reported": pc.pct, "computed": float(exact)}
    if lo <= exact <= hi:
        return Finding(status="ok", title=ttl, explanation=f"{pc.k}/{pc.n} = {float(exact):.{n_decimals(pc.pct)+1}f}%, consistent with {pc.pct}%.",
                       details=det, **base)
    return Finding(status="gross", title=ttl,
                   explanation=f"{pc.k}/{pc.n} = {float(exact):.2f}%, which does not round to the reported {pc.pct}%.",
                   suggestion="Check the numerator, denominator or percentage.", details=det, **base)


# --------------------------------------------------------------------------
# Estimate + CI (+ p)   (Altman & Bland 2011)
# --------------------------------------------------------------------------
def _corners(*vals: str):
    out = [[]]
    for v in vals:
        lo, hi = interval(v)
        out = [o + [x] for o in out for x in (float(lo), float(hi))]
    return out


def check_ci(c: P.CIResult, alpha: float) -> Finding:
    base = dict(kind="ci", start=c.start, end=c.end, raw=c.raw)
    ratio = c.name.lower() in P.RATIO_NAMES
    ttl = f"{c.name} = {c.est}, {c.level}% CI [{c.lo}, {c.hi}]" + (f", p {c.p_rel} {c.p}" if c.p else "")
    est, lo, hi = (float(to_fraction(x)) for x in (c.est, c.lo, c.hi))
    he, hl, hh = (float(half_unit(x)) for x in (c.est, c.lo, c.hi))
    det: dict[str, Any] = {"estimate": est, "ci": [lo, hi], "scale": "log" if ratio else "linear"}
    if lo > hi + hl + hh:
        return Finding(status="gross", title=ttl, explanation="Lower confidence limit is above the upper limit.", details=det, **base)
    if ratio and min(est, lo, hi) <= 0:
        return Finding(status="gross", title=ttl, explanation=f"{c.name} is a ratio and must be positive.", details=det, **base)
    if est < lo - (he + hl) or est > hi + (he + hh):
        return Finding(status="gross", title=ttl,
                       explanation=f"The point estimate {c.est} lies outside its own confidence interval [{c.lo}, {c.hi}].",
                       suggestion="Check which numbers belong together.", details=det, **base)
    null = 1.0 if ratio else 0.0
    tf = math.log if ratio else (lambda v: v)

    problems: list[str] = []
    status = "ok"

    # 1. duality: a 95% CI excludes the null  <=>  p < .05 (any method)
    if c.p and abs((1 - c.level / 100) - alpha) < 1e-9:
        rlo, rhi, rpt = reported_range(c.p_rel, c.p)
        sig_rep = _sig(c.p_rel, rpt, alpha)
        excl_surely = (lo - hl > null) or (hi + hh < null)
        incl_surely = (lo + hl < null < hi - hh)
        if sig_rep is True and incl_surely:
            problems.append(f"The {c.level}% CI contains the null value ({null:g}) but p is reported as significant.")
            status = "gross"
        elif sig_rep is False and excl_surely:
            problems.append(f"The {c.level}% CI excludes the null value ({null:g}) but p is reported as non-significant.")
            status = "gross"

        # 2. magnitude: p implied by the CI (normal approximation)
        z_lvl = stats.norm.ppf(0.5 + c.level / 200)
        implied = []
        for e, l, h in _corners(c.est, c.lo, c.hi):
            if ratio and min(e, l, h) <= 0:
                continue
            se = (tf(h) - tf(l)) / (2 * z_lvl)
            if se > 0:
                implied.append(float(2 * stats.norm.sf(abs(tf(e) - tf(null)) / se)))
        if implied:
            ilo, ihi = min(implied), max(implied)
            det["p_implied_range"] = [ilo, ihi]
            if c.p_rel == "=" and rpt > 0 and status == "ok":
                if (rpt > 5 * ihi and ihi > 0) or (rpt < ilo / 5):
                    problems.append(
                        f"p implied by the CI is about {fmt_p((ilo+ihi)/2)}, far from the reported p = {c.p} "
                        f"(small samples and exact methods can cause some difference, but not this much).")
                    status = "minor"

    # 3. symmetry on the natural scale
    if c.name.lower() not in P.NONLINEAR_CI and status == "ok":
        asyms = [abs(2 * tf(e) - tf(l) - tf(h)) for e, l, h in _corners(c.est, c.lo, c.hi)
                 if not ratio or min(e, l, h) > 0]
        width = tf(hi) - tf(lo)
        if asyms and width > 0 and min(asyms) > 0.06 * width:
            problems.append("The interval is clearly asymmetric around the estimate on the "
                            f"{'log' if ratio else 'linear'} scale; this happens with exact or bootstrap intervals, "
                            "otherwise it suggests a mistyped limit or estimate.")
            status = "minor"

    if problems:
        return Finding(status=status, title=ttl, explanation=" ".join(problems),
                       suggestion="Compare with the analysis output.", details=det, **base)
    return Finding(status="ok", title=ttl,
                   explanation="Estimate, confidence limits and p-value are mutually consistent.", details=det, **base)


# --------------------------------------------------------------------------
# degrees of freedom versus total sample size
# --------------------------------------------------------------------------
def check_df_n(r: P.Result, max_n: int) -> Optional[Finding]:
    df2 = float(r.df2) if r.df2 else (float(r.df1) if r.df1 else None)
    if df2 is None or r.kind in ("chi2", "z"):
        return None
    needs = df2 + 2 if r.kind == "r" else df2 + 1
    if needs <= max_n + 1e-9:
        return None
    return Finding(
        kind="df_n", status="minor", title=f"{label(r)} vs N = {max_n}",
        explanation=(f"This test has df = {r.df2 or r.df1}, which needs at least {math.ceil(needs)} participants, but the largest total "
                     f"sample size stated anywhere in the text is N = {max_n}."),
        suggestion="Check the df, or whether a larger sample is described elsewhere (multi-study papers).",
        start=r.start, end=r.end, raw=r.raw,
        details={"df": r.df2 or r.df1, "required_n": math.ceil(needs), "max_stated_N": max_n})
