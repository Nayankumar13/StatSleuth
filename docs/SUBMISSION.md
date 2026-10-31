# StatSleuth: Hackathon Submission Document

**Event:** THREWS ODYSSEY 2026 · **Track:** DeepTech & Scientific Computing

> Evidence labels used throughout: **[Established]** = published research we build on; **[Ours]** = our design; **[Measured]** = a number produced by running code in this repository (re-runnable); **[Not done]** = explicitly not done.

---

## 1. Project name
**StatSleuth**: statistical consistency forensics for scientific manuscripts.

## 2. Selected track
DeepTech & Scientific Computing (also relevant to Open Innovation and Human-AI research tooling).

## 3. Abstract
Published papers contain statistics that cannot all be true: p-values that do not match their test statistic, means that no
set of whole numbers could produce, percentages that do not equal k/n, confidence intervals that contradict their p-value.
Existing detectors each cover one slice (p-values *or* GRIM *or* CI) and often raise false alarms from rounding or from
legitimate corrections. StatSleuth is a web tool and REST API that extracts reported results from pasted text or PDFs and runs
seven rounding-aware consistency checks, including a **correction-aware p-value check** (sphericity-corrected F, one-tailed
tests, multiple-comparison adjustment) and **GRIM/GRIMMER** for integer data, and shows every verdict in the manuscript with
the arithmetic behind it. On a clearly labelled synthetic benchmark of 6,000 results the engine raised 0 false alarms on
3,717 honestly-rounded results (an exact-match baseline raised 43.5%) and detected 96.1% of material injected errors (98.2%
when "needs context" verdicts count). GRIM agrees with exhaustive enumeration on 76,428 cases with 0 mismatches. All 48 tests pass.
We have **not** yet validated on real published papers (see §21).

## 4. Introduction
Peer review rarely recomputes numbers. Researchers such as Brown and Heathers, and the authors of the statcheck project,
showed that simple arithmetic can reveal reporting errors at scale. This project turns those separate ideas into one usable,
explainable tool for reviewers, editors, supervisors and authors checking their own drafts.

## 5. Problem statement
Given the text of a manuscript, decide which reported statistics are mutually inconsistent, *without access to the raw data*,
and explain each finding well enough that a human can verify or dismiss it in seconds.

## 6. Motivation
- [Established] In a sample of over 250,000 p-values from eight psychology journals, statcheck found that about one in eight papers contained a grossly inconsistent p-value that may have affected the conclusion (Nuijten et al., 2016, PMC5101263).
- [Established] Applying GRIM to 260 articles, Brown & Heathers found 71 amenable to the test, 36 of which contained at least one impossible mean (as summarised on the GRIM Wikipedia page citing the paper).
- [Established] Naive checking has a known weakness: it cannot handle corrected p-values such as Greenhouse-Geisser, so legitimate papers get flagged and some wrong ones pass (Schmidt, arXiv:1610.01010). Flagging an honest author unfairly is costly, so false alarms matter as much as misses.

## 7. Existing systems and their limitations
| Existing | What it does | Limitation we address |
|---|---|---|
| statcheck (R) | Extracts APA-style tests, recomputes p | Depends on APA strings; per Schmidt (2017), cannot handle corrected p-values; separate from GRIM and CI checks; needs R |
| GRIM / GRIMMER tools (`scrutiny` R package, `grim` Python package, web calculators) | Test one mean (and SD) at a time | Manual entry; no extraction from text; not linked to other checks |
| Altman-Bland CI↔p conversion (BMJ 2011) | A formula | Not packaged as an automated manuscript check |
| Citation-hallucination checkers (CheckIfExist etc.) | Verify references | Different problem (we considered it, see §18) |

We did not benchmark against statcheck itself (R is not available in our environment); our comparisons use our own simple exact-match baseline and are labelled as such.

## 8. Proposed solution
A pipeline: **extract** (regex parser, length-preserving normalisation so highlights map back to the original text) → **check** (seven rounding-aware checks) → **explain** (plain-language reason, the recomputed range, a suggestion) → **report** (summary, filterable findings, highlighted text, JSON/CSV/Markdown export).

## 9. Objectives
1. Zero tolerance for false alarms caused by rounding or by *documented* corrections.
2. Every flag explains itself with the actual arithmetic.
3. One tool for p-value, GRIM/GRIMMER, percentage, CI and df-vs-N checks.
4. Honest uncertainty: "needs context", "not applicable" and "unverifiable" are first-class outcomes.
5. Measurable, reproducible evaluation.

## 10. Key features
- Rounding-interval p-value recomputation for t, F, χ², r, z (including `p < .05` style inequalities).
- Correction awareness: one-tailed match, sphericity correction (ε search between 1/df₁ and 1), adjustment can only *raise* p.
- GRIM (means, multi-item scales) and GRIMMER (SDs) with "nearest possible mean" suggestions.
- Percentage-vs-counts, CI-vs-estimate-vs-p (Altman & Bland), df-vs-N cross-check.
- PDF/TXT/MD upload, highlighted text with click-through, log-scale p-range bar, exports, saved history, quick calculators.
- Privacy switch: analyse without storing anything.

## 11. System architecture
```
Browser (React + Vite)                         FastAPI (Python)                               SQLite
 ┌────────────────────────┐   JSON/multipart    ┌──────────────────────────────────┐          ┌──────────┐
 │ Analyse · Report ·     │ ──────────────────▶ │ validation · rate limit          │          │ reports  │
 │ Quick checks · History │ ◀────────────────── │  └▶ engine.analyze(text, options)│ ───────▶ │ (id,text,│
 └────────────────────────┘                     │      parser → checks → summary   │          │ findings)│
                                                └──────────────────────────────────┘          └──────────┘
 engine: parser.py ─▶ checks.py (pvalue, correction, ci, percent, df_n) + grim.py (GRIM, GRIMMER) ─▶ analyzer.py
```
Offsets are converted to UTF-16 code units in the API so the browser highlights the right characters even with emoji.

## 12. Technology stack
Python 3.13, FastAPI, Pydantic v2, SciPy (t/F/χ²/normal distributions), `fractions.Fraction` (exact rounding arithmetic), pypdf, SQLite (stdlib). React 18, Vite 5, React Router, hand-written CSS and SVG (no UI or chart library). pytest, Playwright (UI test). No paid services, no API keys.

*Why Python for the engine rather than Node:* correct t/F/χ² tail probabilities need SciPy-quality numerics; JavaScript has no equally trustworthy standard library for this.

## 13. Implementation methodology
1. **Normalise** text with a 1-to-1 character map (unicode minus → `-`, χ → `x`, ² → `2`) so offsets are preserved.
2. **Parse** with regular expressions: t, F, χ², r, z results *with* a p-value; `M = , SD =` with the nearest `n =` (same sentence, else previous); `k/n (x%)`; `OR/b/d = , 95% CI [a, b]` with optional p.
3. **Check** each item (details in §15).
4. **Summarise**: counts by status/check, flag rate with a Wilson 95% interval, a verdict sentence worded to avoid accusing anyone.

## 14. Dataset and external resources
- **No external dataset is required** and none is downloaded. The engine is pure mathematics.
- **Synthetic manuscripts** A, B, C (`backend/app/samples.py`) were written for this project; B contains seven seeded errors listed in the API (`/api/samples`).
- **Published worked examples** used as test oracles: GRIM `5.19` impossible for n = 28 but possible for n = 32, and `5.27` impossible for n = 43 (from the `scrutiny` R package documentation); the Altman-Bland BMJ worked example (difference 17.0, SE 7.94 → CI 1.4–32.6, p = .032).
- **Independent implementation for cross-checking:** the `grim` package on PyPI (`pip install grim`).
- **Real-paper validation:** *[Not done]* in this environment (network allow-list blocked scholarly sites). `scripts/scan_dir.py` lets you run the tool on open-access papers you download.

## 15. Algorithms and models used
No machine-learning model is used. That is a deliberate choice, not an omission: each check has an exact mathematical ground truth, so a learned model could only make it less trustworthy and less explainable.

**p-value check [Ours, building on Nuijten et al.].** A printed statistic `x` with *d* decimals means `x ∈ [x − ½·10⁻ᵈ, x + ½·10⁻ᵈ]`. Because p decreases monotonically in |x|, the p-range is `[p(x_hi), p(x_lo)]`. The reported p becomes an interval too (`= .036` → [.0355, .0365]; `< .001` → [0, .001]). The result is *consistent* iff the intervals overlap. If not, in order: (1) t/z/r: does p/2 overlap → "one-tailed" (OK if the sentence says so, otherwise *needs context*); (2) F with df₁ > 1 and a sphericity keyword: is the reported p inside `[p(F; df), p(F; df/df₁)]`, i.e. ε between 1/df₁ and 1 → *needs context* and the fitted ε is shown; (3) adjustment keyword and reported p ≥ raw p → *needs context* (an adjustment can raise p, never lower it); else *inconsistent*. It is **serious** ("gross") if significance at α flips, otherwise **minor**.

**GRIM [Established: Brown & Heathers 2017].** For n integers (× k items), the mean is S/(n·k) for integer S. The test asks whether an integer S lies in the closed rounding interval. Closed ends make it charitable to both round-half-up and half-even.

**GRIMMER [Established idea: Anaya 2016; our necessary-condition implementation].** For integer data with sum S and sum of squares Q: `Var = (Q − S²/n)/(n−1)`, `Q ≡ S (mod 2)` (since x² ≡ x mod 2), and `Q ≥ Q_min(S)` where `Q_min` is attained by values as equal as possible. For every S allowed by the mean we ask whether an integer Q with these properties yields an SD in the rounding interval. These are necessary conditions, so it **never** flags a feasible pair; it may miss some impossible ones.

**CI check [Established: Altman & Bland 2011; ours: automation + rounding corners].** Estimate inside its interval; duality (a 95% CI containing the null ↔ p ≥ .05) tested over all rounding corners; implied p from SE = (u − l)/(2·1.96) (log scale for ratios) must be within a factor of 5 of the reported p; symmetry on the natural scale.

**Percent, df-vs-N.** Exact fractions; df requires N ≥ df + 1 (df + 2 for r).

## 16. Testing and evaluation
All commands in the README. All below were **actually executed**.

**Automated tests: 48 passed** (`python -m pytest tests -q`): 31 engine tests (rounding boundaries, inequalities, one-tailed, Greenhouse-Geisser, adjustment, impossible values, GRIM exhaustive and cross-package checks, GRIMMER property tests, parser formats and offsets, CI duality, Altman-Bland example, options validation) and 17 API tests (round trip, persistence on/off, export formats, validation errors, upload rejection by type/size/empty/corrupt, a real text-layer PDF, tools endpoints, rate limit, samples).

**UI end-to-end:** `eval/ui_smoke.py` drives a real Chromium through analysis, highlights, finding detail, exports, quick checks, history/delete, unsaved reports, error page, and a 390-px mobile viewport; all steps passed.

## 17. Results and observations

### 17.1 GRIM / GRIMMER validation [Measured] (`docs/eval_grim.json`)
| Test | Result |
|---|---|
| GRIM vs exhaustive enumeration, n = 2…100, 1 and 2 decimals | 76,428 cases, **0 mismatches** |
| GRIM vs independent `grim` package, 20,000 random cases | 19,766 agree; the other 234 are exact rounding ties where we are deliberately more charitable; **0 unexplained** |
| GRIMMER soundness on 60,000 real random integer datasets | **0 false alarms** |
| GRIMMER power vs exhaustive enumeration (all unreachable mean/SD pairs at 2 d.p. on a bounded scale) | 92.2%–96.6% flagged (n = 5–8, scales 1–5 and 1–7). Conservative, because the checker does not know the scale limits |

### 17.2 Seeded-error benchmark [Measured, SYNTHETIC] (`docs/eval_synthetic.json`; seed 2026, 6,000 results, 40% corrupted)
Honest results: p computed from the *unrounded* statistic, then statistic (2 d.p.) and p (3 d.p.) rounded. Corruptions (p typo, statistic typo, df typo) are our choice.

| Metric | StatSleuth | Exact-match baseline (ours, **not** statcheck) |
|---|---|---|
| False-positive rate on 3,717 honest results | **0.0%** | 43.5% |
| Recall on 1,622 *material* injected errors (|Δp| ≥ .002) | 96.1% (98.2% counting "needs context") | 99.9% |
| Precision of all flags | **100%** | 54.8% |
| Material errors that flip significance (n = 263): flagged / labelled serious | 98.9% / 98.5% | n/a |
| Parse rate over 4 text formatting styles | 100% | n/a |

Robustness: seeds 2026/7/99 gave 0 engine false positives each; material recall 94.6–96.1% (98.1–98.7% incl. needs-context).
*Interpretation:* the baseline's high recall comes from flagging almost everything; it cannot be used by a reviewer. The 29 material errors still missed are mostly correlations (22) where rounding a small r leaves a wide p-range: an inherent limit, not a bug. A df typo is caught only 43% of the time overall because many df changes barely move p (not "material").
*Caveat:* the benchmark shows internal soundness, not real-world accuracy. A first version of the generator had a bug (printing p = 1.000 as ".000") that appeared as the engine's only false positive; the engine was right and the generator was fixed.

### 17.3 Correction-awareness experiment [Measured, SYNTHETIC] (`docs/eval_correction.json`)
2,000 repeated-measures F tests with ε-scaled (Greenhouse-Geisser-style) p-values printed with uncorrected df.
| Case | n | Exact-match baseline flags | StatSleuth |
|---|---|---|---|
| Legitimate correction, text mentions it | 1,311 | 100% | 99.5% accepted as consistent / needs-context |
| Legitimate correction, **not** mentioned | 294 | 100% | 100% flagged (by design; asks author to state the correction) |
| Impossible: p *below* the uncorrected p, correction mentioned | 135 | 100% | 100% flagged (no correction can lower p) |

### 17.4 Demonstration manuscripts [Measured]
A (consistent): 17 checks, 0 flags. B (seeded): all 7 planted errors found (6 serious, 1 minor), 4 consistent results left alone. C: legitimate corrections accepted as "needs context"; an identical result with no explanation is flagged.

## 18. Innovation and originality
1. **Interval semantics everywhere** instead of point comparison, including for the reported p.
2. **Correction-aware logic with direction awareness** (adjustments only raise p; sphericity correction has a bounded ε range). Addresses the documented statcheck blind spot.
3. **One explainable pipeline** combining p-value, GRIM, GRIMMER, percentage, CI and df-vs-N checks with UI that shows the arithmetic.
4. **Honest-by-design outputs**: five verdict classes, a verdict sentence that avoids accusations, Wilson interval on the flag rate, and an explicit privacy mode.

*Ideas considered and rejected:* a package-typosquat detector (well covered by SpellBound, arXiv:2003.03471 and ConfuGuard, arXiv:2502.20528; little public labelled attack data) and a hallucinated-citation checker (crowded: CheckIfExist arXiv:2602.15871 and others; a July 2026 study, arXiv:2607.22693, found none of five tools reliable enough to run unsupervised; and verifying references needs live Crossref calls we could not test).

## 19. Real-world applications
Pre-submission self-check by authors; triage by journal editors and peer reviewers; research-integrity officers screening flagged papers; supervisors and teachers checking theses; meta-researchers scanning open-access corpora (via `scripts/scan_dir.py` or the API).

## 20. Future scope
Table extraction; more test families (Welch/ANOVA effect sizes, regression coefficients, odds-ratio tables); scale bounds for stronger GRIMMER; Benford and SPRITE-style analyses; validation against a corpus of corrected-erratum papers; browser extension; batch API with authentication.

## 21. Limitations
- Not validated on real published papers (environment restriction); real-world precision/recall are unknown. The synthetic benchmark uses our own corruption model.
- Pattern-based extraction: APA-like inline reports only; PDF text extraction can lose symbols; scanned PDFs unsupported.
- GRIM/GRIMMER only apply to integer data; multi-item scales need the *items* setting; GRIMMER misses some impossible SDs.
- Corrections are recognised from keywords; an unmentioned correction is flagged.
- df-vs-N uses the largest stated N, so multi-study papers can be over-flagged (hence "minor").
- No authentication; the in-memory rate limiter is per-process. A flag is never proof of misconduct.

## 22. Conclusion
StatSleuth shows that careful interval arithmetic plus a few exact number-theoretic tests can screen manuscripts quickly, with
explanations a reviewer can verify. Its main contributions are the correction-aware, rounding-aware p-value logic and the
unified, explainable interface. The decisive remaining work is validation on real papers.

## 23. Research references
Links were retrieved via web search while building this project unless marked otherwise.
1. Nuijten, M. B., Hartgerink, C. H. J., van Assen, M. A. L. M., Epskamp, S., Wicherts, J. M. (2016). *The prevalence of statistical reporting errors in psychology (1985–2013).* Behavior Research Methods. https://pmc.ncbi.nlm.nih.gov/articles/PMC5101263
2. Schmidt, T. (2017). *Sources of false positives and false negatives in the STATCHECK algorithm: Reply to Nuijten et al. (2016).* arXiv:1610.01010. https://arxiv.org/abs/1610.01010
3. Brown, N. J. L., & Heathers, J. A. J. (2017). *The GRIM test: A simple technique detects numerous anomalies in the reporting of results in psychology.* Social Psychological and Personality Science, 8(4), 363–369. https://doi.org/10.1177/1948550616673876
4. Anaya, J. (2016). *The GRIMMER test: A method for testing the validity of reported measures of variability.* PeerJ Preprints 4:e2400v1. https://peerj.com/preprints/2400
5. Anaya, J., van der Zee, T., & Brown, N. (2017). *Statistical infarction: A postmortem of the Cornell Food and Brand Lab pizza publications.* PeerJ Preprints (as cited on the GRIM Wikipedia page).
6. Altman, D. G., & Bland, J. M. (2011). *How to obtain the P value from a confidence interval.* BMJ 343:d2304, https://doi.org/10.1136/bmj.d2304; and *How to obtain the confidence interval from a P value.* BMJ 343:d2090, https://doi.org/10.1136/bmj.d2090
7. Tilburg University working paper, *The validity of the tool "statcheck" in discovering statistical reporting inconsistencies* (sensitivity 85.3–100%, specificity 96.0–100%). https://research.tilburguniversity.edu/
8. `scrutiny` R package, GRIM documentation. https://rdrr.io/cran/scrutiny/man/grim.html ; `grim` Python package https://github.com/phoughton/grim_test
9. Considered alternatives: Taylor et al. (2020) *SpellBound* arXiv:2003.03471; *ConfuGuard* arXiv:2502.20528; *CheckIfExist* arXiv:2602.15871; Badalova & Mayr (2026) arXiv:2607.22693.
10. Classical references for sphericity corrections (not retrieved here, cited from general knowledge): Greenhouse & Geisser (1959), Psychometrika; Huynh & Feldt (1976), J. Educational Statistics.

## 24. GitHub repository information
**[Not done]** No remote repository has been created from this session. Suggested: `git init && git add . && git commit -m "StatSleuth"` then push to a new public GitHub repo; the `.gitignore` already excludes the database, `node_modules` and build output. Add the URL here before submitting.

## 25. Working demonstration information
**Local demo: verified** (README quick start; UI smoke test passed against the built app). **Public live demo: [Not done]**: deployment instructions are in the README but no deployment was performed, so do not claim a live URL. Demo script: `docs/PRESENTATION.md`.
