"""Validation of GRIM / GRIMMER against exhaustive enumeration and an independent package.
Everything here is computed, nothing is quoted from papers.   Run: python -m eval.grim_validation
"""
from __future__ import annotations

import json
import random
from fractions import Fraction
from pathlib import Path

from app.engine.grim import brute_force_pairs, grim, grimmer

out: dict = {}

# 1) GRIM vs exhaustive enumeration (exact: reachable means are S/n) -------------------------------
mism = checked = 0
for n in range(2, 101):
    for d in (1, 2):
        reach = set()
        for S in range(0, 7 * n + 1):
            fr = Fraction(S, n)
            for cand in (int(fr * 10 ** d), int(fr * 10 ** d) + 1):
                if abs(Fraction(cand, 10 ** d) - fr) <= Fraction(1, 2 * 10 ** d):
                    reach.add(f"{cand / 10 ** d:.{d}f}")
        for v in range(0, 7 * 10 ** d + 1):
            s = f"{v / 10 ** d:.{d}f}"
            checked += 1
            mism += grim(s, n).consistent != (s in reach)
out["grim_vs_exhaustive"] = {"cases": checked, "mismatches": mism, "n_range": "2-100", "decimals": "1,2"}

# 2) GRIM vs the independent `grim` PyPI package (round-half-up) ----------------------------------
from grim.mean_tester import consistency_check

rnd = random.Random(5)
agree = tot = tie_only = 0
for _ in range(20000):
    n = rnd.randint(5, 80)
    s = rnd.randint(n, 6 * n)
    v = (s + (rnd.random() - 0.5) * rnd.choice([0, 0, 1.5])) / n
    rep = f"{v:.2f}"
    ours = grim(rep, n).consistent
    theirs = bool(consistency_check(rep, n, "ROUND_HALF_UP"))
    tot += 1
    if ours == theirs:
        agree += 1
    elif ours and not theirs:
        # allowed difference: ours also accepts exact .5 ties (round-half-even)
        tie_only += any(abs(Fraction(k, n) - Fraction(rep)) == Fraction(1, 200) for k in range(0, 7 * n + 1))
out["grim_vs_pypi_grim_package"] = {"cases": tot, "agree": agree, "ours_accepts_theirs_rejects_only_on_exact_ties": tie_only,
                                    "unexplained_disagreements": tot - agree - tie_only}

# 3) GRIMMER soundness on real integer data -------------------------------------------------------
rnd = random.Random(11)
fa = tot = 0
for _ in range(60000):
    n = rnd.randint(2, 60)
    hi = rnd.choice([5, 7, 10, 100])
    data = [rnd.randint(0, hi) for _ in range(n)]
    mean = sum(data) / n
    sd = (sum((x - mean) ** 2 for x in data) / (n - 1)) ** 0.5
    d = rnd.choice([1, 2, 3])
    tot += 1
    fa += not grimmer(f"{mean:.{d}f}", f"{sd:.{d}f}", n).consistent
out["grimmer_soundness_real_integer_data"] = {"datasets": tot, "false_alarms": fa}

# 4) GRIMMER power vs exhaustive enumeration -------------------------------------------------------
power = {}
for n, hi in [(5, 5), (6, 5), (8, 5), (6, 7)]:
    pairs = brute_force_pairs(n, 1, hi, 2, 2)
    means = sorted({m for m, _ in pairs})
    unreachable = flagged = 0
    for m in means:
        for sd in range(0, 301):
            sds = f"{sd / 100:.2f}"
            if (m, sds) in pairs:
                assert grimmer(m, sds, n).consistent        # soundness inside the loop
                continue
            unreachable += 1
            flagged += not grimmer(m, sds, n).consistent
    power[f"n={n}, scale 1-{hi}"] = {"reachable_pairs": len(pairs), "unreachable_pairs_tested": unreachable,
                                      "share_flagged": flagged / unreachable}
out["grimmer_power_vs_exhaustive"] = {
    "note": "Unreachable = no integer data on the stated scale gives this (mean, SD) at 2 d.p. The checker does not know the scale bounds, so some "
            "of these pairs are reachable with integers outside the scale and cannot be flagged; share_flagged is therefore a conservative power estimate.",
    **power}

Path(__file__).resolve().parents[2].joinpath("docs", "eval_grim.json").write_text(json.dumps(out, indent=2))
print(json.dumps(out, indent=2))
