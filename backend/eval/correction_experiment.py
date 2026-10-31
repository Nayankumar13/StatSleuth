"""Correction-awareness experiment.   *** SYNTHETIC ***

Repeated-measures F tests where the author applied a Greenhouse-Geisser (GG) style correction
(p from epsilon-scaled df) but printed the UNcorrected df, the pattern Schmidt (arXiv:1610.01010)
shows string-matching checkers mis-flag.  We compare:
   naive   : recompute p with the printed df, exact-match at 3 d.p.   (our baseline, not statcheck)
   engine  : StatSleuth.
Also: "impossible corrections" (printed p SMALLER than the uncorrected p), which no correction can cause.
Run: python -m eval.correction_experiment
"""
from __future__ import annotations

import json
import random
from pathlib import Path

from scipy import stats

from app.engine import analyze, checks as C

rnd = random.Random(31)
N = 2000
rows = []
for _ in range(N):
    k = rnd.randint(3, 5)
    subj = rnd.randint(15, 60)
    d1, d2 = k - 1, (k - 1) * (subj - 1)
    F = rnd.uniform(1.5, 9.0)
    eps = rnd.uniform(1 / d1 + 0.02, 0.95)
    p_corr = float(stats.f.sf(F, eps * d1, eps * d2))
    p_unc = float(stats.f.sf(F, d1, d2))
    fake = rnd.random() < 0.25 and p_unc >= 0.01   # below .01 the printed p would hit the .001 floor: nothing to detect
    p_print = p_unc * rnd.uniform(0.2, 0.6) if fake else p_corr
    p_print = max(p_print, 0.001)
    mention = rnd.random() < 0.8
    body = f"F({d1}, {d2}) = {F:.2f}, p = {p_print:.3f}"
    text = ("Sphericity was violated and a Greenhouse-Geisser correction was applied. " if mention else "") + f"The effect was significant, {body}."
    rows.append(dict(text=text, fake=fake, mention=mention, p_corr=p_corr, p_unc=p_unc, p_print=p_print,
                     F=f"{F:.2f}", d1=d1, d2=d2))


def naive(r):
    return round(C.p_from_stat("F", float(r["F"]), r["d1"], r["d2"]), 3) != round(r["p_print"], 3)


res = {"n": N, "groups": {}}
for name, sel in [("legit correction, keyword in text", lambda r: not r["fake"] and r["mention"]),
                  ("legit correction, NO keyword in text", lambda r: not r["fake"] and not r["mention"]),
                  ("impossible (p below uncorrected p), keyword in text", lambda r: r["fake"] and r["mention"])]:
    g = [r for r in rows if sel(r)]
    # skip cases where the corrected and uncorrected p coincide at 3 dp (nothing to detect)
    g = [r for r in g if round(r["p_corr"], 3) != round(r["p_unc"], 3) or r["fake"]]
    statuses = [analyze(r["text"])["findings"][0]["status"] for r in g]
    res["groups"][name] = {"n": len(g),
                           "naive_flags": sum(naive(r) for r in g) / len(g),
                           "engine_ok_or_caveat": sum(s in ("ok", "caveat") for s in statuses) / len(g),
                           "engine_minor_or_gross": sum(s in ("minor", "gross") for s in statuses) / len(g),
                           "engine_caveat": sum(s == "caveat" for s in statuses) / len(g)}
res["notes"] = ("Synthetic. 'legit correction' p-values come from epsilon-scaled df with epsilon drawn in (1/df1, .95). Without the keyword the "
                "engine (by design) does not assume a correction, so those are flagged: this is the intended trade-off, and the explanation tells "
                "the author to state the correction.")
Path(__file__).resolve().parents[2].joinpath("docs", "eval_correction.json").write_text(json.dumps(res, indent=2))
print(json.dumps(res, indent=2))
