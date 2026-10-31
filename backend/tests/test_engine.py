"""Engine tests. Every expected value is either (a) analytically known,
(b) a documented published example, or (c) cross-checked against an
independent implementation / exhaustive enumeration."""
import itertools
import random

import pytest
from scipy import stats

from app.engine import analyze, Options
from app.engine.grim import grim, grimmer, brute_force_pairs
from app.engine.parser import parse, normalise
from app.engine import checks as C


def one(text, **kw):
    r = analyze(text, Options(**kw) if kw else None)
    return r["findings"]


def statuses(text, **kw):
    return [f["status"] for f in one(text, **kw)]


# ---------------------------------------------------------------- p-values
def test_consistent_t():
    assert statuses("t(28) = 2.20, p = .036") == ["ok"]


def test_minor_vs_gross():
    assert statuses("t(28) = 2.20, p = .010") == ["minor"]          # both significant
    assert statuses("t(28) = 2.20, p = .200") == ["gross"]          # significance flips
    assert statuses("t(28) = 1.50, p = .020") == ["gross"]


def test_rounding_interval_avoids_false_positive():
    # t=2.045 on df=29 gives p=.0500 (two-sided). 2.04 -> p=.0506; 2.05 -> .0497.
    assert statuses("t(29) = 2.04, p = .05") == ["ok"]
    assert statuses("t(29) = 2.05, p = .05") == ["ok"]


def test_inequality_p():
    assert statuses("t(28) = 6.00, p < .001") == ["ok"]
    assert statuses("t(28) = 2.20, p < .001") != ["ok"]
    assert statuses("t(28) = 0.50, p > .05") == ["ok"]


def test_unicode_and_format_variants():
    for s in ["t(28) = −2.20, p = .036", "t (28)=-2.20,p=.036", "T(28) = 2.20, P = 0.036",
              "t(28) = 2.20 , p = .036."]:
        assert statuses(s) == ["ok"], s
    assert statuses("χ²(1, N = 120) = 4.50, p = .034") == ["ok"]
    assert statuses("chi-square(2) = 6.00, p = .0498") == ["ok"]
    assert statuses("F(2, 45) = 3.40, p = .042") == ["ok"]
    assert statuses("z = 1.96, p = .05") == ["ok"]
    assert statuses("r(98) = .32, p = .001") == ["ok"]


def test_p_matches_scipy_independently():
    for df, t in [(5, 2.57), (10, 2.23), (100, 1.98), (1000, 1.96)]:
        expected = 2 * stats.t.sf(t, df)
        got = C.p_from_stat("t", t, df, None)
        assert got == pytest.approx(expected, rel=1e-12)
    # known table value: t(10)=2.228 -> p=.05
    assert C.p_from_stat("t", 2.228, 10, None) == pytest.approx(0.05, abs=2e-4)
    # chi2(1)=3.841 -> p=.05 ; F(1,infinity-ish)=3.84
    assert C.p_from_stat("chi2", 3.841, 1, None) == pytest.approx(0.05, abs=2e-4)
    assert C.p_from_stat("z", 1.96, None, None) == pytest.approx(0.05, abs=1e-3)


def test_one_tailed():
    # two-sided p = .036 ; one-tailed .018
    f = one("t(28) = 2.20, p = .018")[0]
    assert f["status"] == "caveat"
    f = one("We used a one-tailed test, t(28) = 2.20, p = .018")[0]
    assert f["status"] == "ok"


def test_greenhouse_geisser():
    # uncorrected p = .042 ; corrected p can be larger. Without the keyword: inconsistent.
    assert statuses("F(2, 45) = 3.40, p = .060")[0] in ("minor", "gross")
    txt = "Greenhouse-Geisser corrected: F(2, 45) = 3.40, p = .060"
    assert statuses(txt) == ["caveat"]
    # a corrected p below the uncorrected one is impossible even with the keyword
    txt = "Greenhouse-Geisser corrected: F(2, 45) = 3.40, p = .010"
    assert statuses(txt)[0] in ("minor", "gross")


def test_multiple_comparison_adjustment():
    txt = "After Bonferroni adjustment t(28) = 2.20, p = .20"
    assert statuses(txt) == ["caveat"]
    # adjusted p cannot be SMALLER than the raw p
    txt = "After Bonferroni adjustment t(28) = 2.20, p = .001"
    assert statuses(txt)[0] in ("minor", "gross")


def test_impossible_values():
    assert statuses("F(2, 45) = -3.40, p = .042") == ["gross"]
    assert statuses("r(48) = 1.20, p = .01") == ["gross"]


def test_p_zero_note():
    f = one("t(100) = 9.00, p = .000")[0]
    assert f["status"] == "ok" and "p < .001" in f["explanation"]


def test_alpha_option():
    # p = .036 reported "significant" vs alpha=.01 recomputed same; use mismatching case
    assert statuses("t(28) = 2.20, p = .020", alpha=0.05) == ["minor"]
    assert statuses("t(28) = 2.20, p = .020", alpha=0.03) == ["gross"]  # .020 sig, recomputed .036 not sig at .03


# --------------------------------------------------------------------- GRIM
def test_grim_documented_examples():
    # scrutiny package docs: 5.19 is not consistent with n=28 but is with n=32 ; 5.27 with n=43 is not
    assert not grim("5.19", 28).consistent
    assert grim("5.19", 32).consistent
    assert not grim("5.27", 43).consistent
    # Brown & Heathers style example: mean of 20 integers can only end .00/.05/.10 ... never .08
    assert not grim("3.08", 20).consistent
    assert grim("3.05", 20).consistent


def test_grim_matches_exhaustive_enumeration():
    for n in range(2, 41):
        possible = {f"{s / n:.2f}" for s in range(0, 7 * n + 1)}  # exact enough for 2dp via Fraction below
        from fractions import Fraction
        possible = set()
        for s in range(0, 7 * n + 1):
            lo = Fraction(s, n)
            # all 2-decimal strings that this exact mean may be printed as (half up AND half even)
            base = int(lo * 100)
            for cand in (base, base + 1):
                if abs(Fraction(cand, 100) - lo) <= Fraction(1, 200):
                    possible.add(f"{cand / 100:.2f}")
        for v in range(0, 7 * 100 + 1):
            s = f"{v / 100:.2f}"
            assert grim(s, n).consistent == (s in possible), (n, s)


def test_grim_agrees_with_independent_package():
    from grim.mean_tester import consistency_check
    rnd = random.Random(1)
    for _ in range(300):
        n = rnd.randint(5, 60)
        s = rnd.randint(n, 6 * n)
        reported = f"{s / n:.2f}"
        if rnd.random() < 0.5:
            reported = f"{(s + rnd.choice([-1, 1]) * rnd.random()) / n:.2f}"
        ours = grim(reported, n).consistent
        theirs = bool(consistency_check(reported, n, 'ROUND_HALF_UP'))
        # the third-party package uses ROUND_HALF_UP only; ours is charitable to half-even too
        if theirs:
            assert ours
        else:
            # if ours is True while theirs is False it must be a pure tie case
            if ours:
                from fractions import Fraction
                assert any(abs(Fraction(k, n) - Fraction(reported)) == Fraction(1, 200) for k in range(0, 8 * n + 1))


def test_grimmer_never_false_alarms_on_real_integer_data():
    rnd = random.Random(7)
    for _ in range(3000):
        n = rnd.randint(2, 40)
        data = [rnd.randint(1, 7) for _ in range(n)]
        mean = sum(data) / n
        mu = mean
        sd = (sum((x - mu) ** 2 for x in data) / (n - 1)) ** 0.5
        for dm, ds in [(2, 2), (1, 2), (2, 1)]:
            m_s, s_s = f"{mean:.{dm}f}", f"{sd:.{ds}f}"
            assert grimmer(m_s, s_s, n).consistent, (data, m_s, s_s)


def test_grimmer_vs_exhaustive_small():
    # n=6, scale 1..5, exhaustively enumerate every reachable (mean, SD) pair (2 dp)
    n = 6
    pairs = brute_force_pairs(n, 1, 5, 2, 2)
    # every reachable pair passes (soundness)
    for m, s in pairs:
        assert grimmer(m, s, n).consistent
    # many unreachable pairs are caught (power) and none of the flagged ones is reachable
    flagged = 0
    total = 0
    for m in sorted({m for m, _ in pairs}):
        for sd in range(0, 250):
            s = f"{sd / 100:.2f}"
            if (m, s) in pairs:
                continue
            total += 1
            if not grimmer(m, s, n).consistent:
                flagged += 1
    assert flagged > 0.5 * total      # most unreachable SDs are detected at n=6


def test_grimmer_example_impossible():
    # n=20, mean 3.45 => sum 69; SD 1.20 impossible (derived by hand in docs)
    assert grim("3.45", 20).consistent
    assert not grimmer("3.45", "1.20", 20).consistent


# ------------------------------------------------------------------ parsing
def test_parser_finds_all_types_and_offsets():
    t = "A (n = 20) M = 3.45, SD = 1.20; t(28) = 2.20, p = .036; 9/20 (45%); OR = 2.10, 95% CI [1.20, 3.70], p = .008."
    p = parse(t)
    assert len(p.results) == 1 and len(p.means) == 1 and len(p.pcts) == 1 and len(p.cis) == 1
    r = p.results[0]
    assert t[r.start:r.end] == "t(28) = 2.20, p = .036"
    assert p.means[0].n == 20


def test_parser_does_not_cross_into_next_result():
    t = "t(28) = 2.20; t(30) = 1.00, p = .325"
    p = parse(t)
    assert len(p.results) == 1 and p.results[0].df1 == "30"


def test_offsets_with_emoji_are_utf16():
    text = "\U0001F600 t(28) = 2.20, p = .036"
    f = analyze(text)["findings"][0]
    # JS: "\u{1F600}" occupies 2 UTF-16 units, so the result starts at index 3
    assert f["start"] == 3


def test_unit_hint_skips_grim():
    assert statuses("M = 245.3 ms, SD = 40.1 (n = 30)") == []        # not parsed
    assert statuses("M = 245.31 (SD = 40.1 ms; n = 30)") == ["na"]


def test_items_option():
    # mean of 3 items, n=10: granularity 1/30; 2.37 reachable (71/30=2.3667)
    assert statuses("n = 10, M = 2.37, SD = 0.5", items_per_scale=3)[0] == "ok"
    assert statuses("n = 10, M = 2.37, SD = 0.5", items_per_scale=1)[0] == "gross"


# ------------------------------------------------------------------ percent
def test_percent():
    assert statuses("9/20 (45%)") == ["ok"]
    assert statuses("9/20 (46%)") == ["gross"]
    assert statuses("12 of 40 (30.0%)") == ["ok"]
    assert statuses("30% (n = 12 of 40)") == ["ok"]
    assert statuses("25/20 (125%)") == ["gross"]


# ----------------------------------------------------------------------- CI
def test_ci_consistent_and_duality():
    assert statuses("OR = 2.10, 95% CI [1.20, 3.70], p = .008") == ["ok"]
    assert statuses("OR = 1.50, 95% CI [0.90, 2.50], p = .01") == ["gross"]   # CI contains 1
    assert statuses("b = 0.50, 95% CI [0.10, 0.90], p = .30") == ["gross"]    # CI excludes 0
    assert statuses("b = 0.50, 95% CI [-0.10, 1.10], p = .09") == ["ok"]


def test_ci_estimate_outside_interval():
    assert statuses("OR = 5.00, 95% CI [1.20, 3.70], p = .008") == ["gross"]


def test_ci_p_magnitude():
    # CI [0.1, 0.9] around 0.5 => SE=.204, z=2.45, p=.014 ; reported p=.0001 is far off
    f = one("b = 0.50, 95% CI [0.10, 0.90], p = .0001")[0]
    assert f["status"] == "minor"
    assert "implied" in f["explanation"]


def test_ci_altman_bland_example():
    # BMJ 2011;343:d2304 style: difference 17.0, SE 7.94 -> CI 1.4 to 32.6, p = .032 (from d2090 worked example)
    assert statuses("MD = 17.0, 95% CI [1.4, 32.6], p = .032") == ["ok"]


# --------------------------------------------------------------- cross-check
def test_df_vs_total_n():
    t = "Participants (N = 40) took part. t(98) = 2.20, p = .030"
    assert [f["kind"] for f in one(t)].count("df_n") == 1
    t = "Participants (N = 100) took part. t(98) = 2.20, p = .030"
    assert [f["kind"] for f in one(t)].count("df_n") == 0


def test_summary_and_empty_text():
    r = analyze("Nothing to see here.")
    assert r["findings"] == [] and r["summary"]["checked"] == 0
    r = analyze("t(28) = 2.20, p = .200")
    assert r["summary"]["gross"] == 1 and "serious" in r["summary"]["verdict"]


def test_options_validation():
    with pytest.raises(ValueError):
        analyze("x", Options(alpha=2))
    with pytest.raises(ValueError):
        analyze("x", Options(items_per_scale=0))
