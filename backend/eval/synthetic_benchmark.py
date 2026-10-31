"""Seeded-error benchmark for the p-value check.   *** SYNTHETIC DATA ***

What it measures: can the engine (a) leave honestly-rounded results alone and
(b) catch results we deliberately corrupted, and how does it compare with a
naive "recompute p from the printed statistic and compare exactly" baseline
(our own baseline; it is NOT the statcheck package).

What it does NOT measure: how common errors are in real papers, or accuracy on
real PDFs. The corruption sizes below are our choice.

Run:  python -m eval.synthetic_benchmark [N] [seed]
"""
from __future__ import annotations

import json
import math
import random
import sys
from collections import defaultdict
from pathlib import Path

from scipy import stats

from app.engine import analyze, checks as C

N = int(sys.argv[1]) if len(sys.argv) > 1 else 6000
SEED = int(sys.argv[2]) if len(sys.argv) > 2 else 2026
ERR_RATE = 0.40
rnd = random.Random(SEED)


def draw_clean():
    """One honest result: p computed from the UNROUNDED statistic, then both printed rounded."""
    kind = rnd.choice(["t", "F", "chi2", "r", "z"])
    if kind == "t":
        df = rnd.randint(8, 200)
        x = abs(rnd.gauss(0, 1)) * rnd.uniform(0.8, 4.0)
        return dict(kind=kind, df1=df, df2=None, x=x)
    if kind == "F":
        d1, d2 = rnd.randint(1, 5), rnd.randint(12, 250)
        x = rnd.uniform(0.3, 1) * stats.f.isf(rnd.choice([0.5, 0.2, 0.05, 0.01, 0.001]), d1, d2)
        return dict(kind=kind, df1=d1, df2=d2, x=x)
    if kind == "chi2":
        d = rnd.randint(1, 6)
        x = rnd.uniform(0.3, 1) * stats.chi2.isf(rnd.choice([0.5, 0.2, 0.05, 0.01, 0.001]), d)
        return dict(kind=kind, df1=d, df2=None, x=x)
    if kind == "r":
        df = rnd.randint(15, 300)
        return dict(kind=kind, df1=df, df2=None, x=rnd.uniform(0.05, 0.6))
    return dict(kind=kind, df1=None, df2=None, x=abs(rnd.gauss(0, 1)) * rnd.uniform(0.8, 3.5))


def p_of(c, x=None, df1=None, df2=None):
    return C.p_from_stat(c["kind"], c["x"] if x is None else x, c["df1"] if df1 is None else df1,
                         c["df2"] if df2 is None else df2)


def fmt_p(p, style):
    if p < 0.001:
        return "p < .001"
    s = f"{p:.3f}"
    if s == "1.000":           # APA: never print a leading-zero-stripped 1.000 as ".000"
        return "p = 1.00"
    return f"p = {s[1:]}" if style % 2 == 0 else f"p = {s}"


def fmt_stat(c, stat_s, df1, df2, style):
    k = c["kind"]
    sp = " " if style < 2 else ""
    if k == "t":
        return f"t{sp}({df1}) = {stat_s}"
    if k == "F":
        return f"F{sp}({df1}, {df2}) = {stat_s}"
    if k == "chi2":
        return ("\u03c7\u00b2" if style == 2 else "chi-square") + f"({df1}) = {stat_s}"
    if k == "r":
        rs = stat_s[1:] if style % 2 == 0 and stat_s.startswith("0.") else stat_s   # .32 vs 0.32
        return f"r({df1}) = {rs}"
    return f"z = {stat_s}"


def render(c, stat_x, df1, df2, p_value, style):
    """Print a result the way an author would (stat 2 d.p., p 3 d.p.)."""
    stat_s = f"{stat_x:.2f}"
    minus = "\u2212" if (style == 2 and c["kind"] == "t" and rnd.random() < 0.5) else ""
    text = f"{fmt_stat(c, minus + stat_s, df1, df2, style)}, {fmt_p(p_value, style)}"
    return text, stat_s


def naive_flag(kind, stat_s, df1, df2, p_text):
    """Baseline: recompute p from the printed statistic; require exact equality at 3 d.p. (<.001 rule)."""
    p = C.p_from_stat(kind, float(stat_s), df1, df2)
    if "<" in p_text:
        return p >= 0.001
    given = float(p_text.split("=")[1])
    return round(p, 3) != given


rows = []
for i in range(N):
    c = draw_clean()
    style = rnd.randint(0, 3)
    p_true = p_of(c)
    df1, df2, x = c["df1"], c["df2"], c["x"]
    err = None
    material = False
    p_rep = p_true
    x_print, d1_print, d2_print = x, df1, df2
    if rnd.random() < ERR_RATE:
        err = rnd.choice(["p_typo", "stat_typo", "df_typo"])
        if err == "p_typo":
            f = rnd.choice([0.2, 0.35, 0.5, 0.7, 1.4, 2, 3, 5])
            p_rep = min(max(p_true * f, 0.001), 0.999)
            material = abs(p_rep - p_true) >= 0.002
        elif err == "stat_typo":
            if c["kind"] in ("F", "chi2"):
                x_print = x * rnd.choice([0.6, 0.75, 1.3, 1.6])
            elif c["kind"] == "r":
                x_print = min(max(x + rnd.choice([-1, 1]) * rnd.uniform(0.04, 0.2), 0.01), 0.95)
            else:
                x_print = max(x + rnd.choice([-1, 1]) * rnd.uniform(0.2, 1.5), 0.05)
            material = abs(p_of(c, x=x_print) - p_true) >= 0.002
        else:
            if c["kind"] == "z":
                err = None
            elif c["kind"] == "F":
                d2_print = max(3, df2 + rnd.choice([-1, 1]) * rnd.randint(4, 40))
                material = abs(p_of(c, df2=d2_print) - p_true) >= 0.002
            else:
                d1_print = max(2, df1 + rnd.choice([-1, 1]) * rnd.randint(3, 15)) if c["kind"] != "chi2" else max(1, df1 + rnd.choice([-1, 1]))
                material = abs(p_of(c, df1=d1_print) - p_true) >= 0.002
    if err == "stat_typo" or err == "df_typo" or err is None:
        p_print = p_true       # p stays as the honest author's value; the *other* numbers were mistyped
    else:
        p_print = p_rep
    text, stat_s = render(c, x_print if err == "stat_typo" else x, d1_print, d2_print, p_print, style)
    # honest p is printed with 3 d.p. from the true (unrounded) stat; corrupted ones keep that p
    p_from_printed = p_of(c, x=float(stat_s), df1=d1_print, df2=d2_print)
    rows.append(dict(text=text, kind=c["kind"], err=err, material=material, p_true=p_true, p_print=p_print,
                     stat_s=stat_s, d1=d1_print, d2=d2_print, style=style,
                     flips=(p_print < .05) != (p_from_printed < .05)))

# ---- evaluate -----------------------------------------------------------------
# "strict" = engine says minor/gross.  "review" = strict OR caveat (e.g. 'matches a one-tailed test').
parse_ok = 0
for r in rows:
    res = analyze(r["text"])
    pv = [f for f in res["findings"] if f["kind"] == "pvalue"]
    r["parsed"] = len(pv) == 1
    parse_ok += r["parsed"]
    st = pv[0]["status"] if r["parsed"] else None
    r["strict"] = st in ("minor", "gross")
    r["review"] = st in ("minor", "gross", "caveat")
    r["gross"] = st == "gross"
    r["naive"] = naive_flag(r["kind"], r["stat_s"], r["d1"], r["d2"], r["text"].split(", ")[-1])


def rate(sel, key):
    sel = list(sel)
    return sum(1 for r in sel if r[key]) / len(sel) if sel else None


clean = [r for r in rows if r["err"] is None]
inj = [r for r in rows if r["err"]]
mat = [r for r in inj if r["material"]]
matflip = [r for r in mat if r["flips"]]
flagged = lambda key: [r for r in rows if r[key]]
prec = lambda key: sum(1 for r in flagged(key) if r["err"]) / len(flagged(key))
missed = [r for r in mat if not r["review"]]
out = {
    "seed": SEED, "N": N, "error_rate": ERR_RATE, "parse_rate": parse_ok / N,
    "clean_results": {"n": len(clean),
                      "false_positive_rate": {"engine_strict": rate(clean, "strict"), "engine_incl_caveat": rate(clean, "review"),
                                              "naive_exact_match": rate(clean, "naive")}},
    "injected_all_recall": {g: {"n": len([r for r in inj if r["err"] == g]),
                                "engine_strict": rate([r for r in inj if r["err"] == g], "strict"),
                                "engine_incl_caveat": rate([r for r in inj if r["err"] == g], "review"),
                                "naive_exact_match": rate([r for r in inj if r["err"] == g], "naive")}
                            for g in ("p_typo", "stat_typo", "df_typo")},
    "material_errors": {"n": len(mat), "definition": "|corrupted p - true p| >= 0.002 after the injected change",
                        "engine_strict": rate(mat, "strict"), "engine_incl_caveat": rate(mat, "review"),
                        "naive_exact_match": rate(mat, "naive")},
    "precision_any_injected_error": {"engine_strict": prec("strict"), "engine_incl_caveat": prec("review"), "naive_exact_match": prec("naive")},
    "material_errors_that_flip_significance": {"n": len(matflip), "engine_strict": rate(matflip, "strict"),
                                               "engine_labelled_gross": rate(matflip, "gross")},
    "still_missed_material_errors": {"n": len(missed),
                                     "by_kind": {k: sum(1 for r in missed if r["kind"] == k) for k in ("t", "F", "chi2", "r", "z")}},
    "notes": ("Synthetic benchmark. Honest results: p from the unrounded statistic, both rounded for printing (stat 2 d.p., p 3 d.p.). "
              "Corruptions chosen by us (p_typo includes a x0.5 factor, which coincides with a one-tailed p: the engine reports "
              "that as 'caveat', hence the two engine columns). Not a claim about real-paper error rates, and the 'naive_exact_match' "
              "column is our own simple baseline, NOT the statcheck package."),
}
Path(__file__).resolve().parents[2].joinpath("docs").mkdir(exist_ok=True)
Path(__file__).resolve().parents[2].joinpath("docs", "eval_synthetic.json").write_text(json.dumps(out, indent=2))
print(json.dumps(out, indent=2))
