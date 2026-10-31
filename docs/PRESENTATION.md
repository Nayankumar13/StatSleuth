# StatSleuth: Presentation, Demo Script and Judge Q&A

## A. Slide outline (8 slides, ~5 min talk)
1. **Title.** StatSleuth: finds the numbers in a paper that cannot all be true. (Track: DeepTech & Scientific Computing)
2. **Problem.** Peer review rarely recomputes numbers. About 1 in 8 psychology papers had a grossly inconsistent p-value in a 250k-p-value study (Nuijten 2016). Show: `t(58) = 1.40, p = .012`, true p = .167.
3. **Why existing tools aren't enough.** statcheck is APA-string based and mis-handles corrected p-values (Schmidt 2017); GRIM/GRIMMER/CI tools are separate manual calculators; naive comparison raises false alarms from rounding.
4. **Our idea.** Interval arithmetic everywhere + correction-aware logic + seven checks in one explainable pipeline. Diagram: parser → checks → explanation (README architecture).
5. **How the hard checks work.** (a) rounding interval → p-range; (b) GRIM: mean = integer/n; (c) GRIMMER: sum of squares parity; (d) adjustments can only raise p.
6. **Live demo** (script below).
7. **Evidence.** 76,428 GRIM cases 0 mismatches vs exhaustive; 0 false alarms in 3,717 honest synthetic results (baseline 43.5%); 96.1% material-error recall (98.2% incl. needs-context); 48 tests pass. Label the benchmark *synthetic*.
8. **Limits and next steps.** Not yet validated on real papers; APA-style text only; flags ≠ misconduct. Next: tables, more tests, real-corpus validation.

## B. Demo script (3–5 minutes)
| Time | Action | What the audience sees (from the real implementation) |
|---|---|---|
| 0:00 | Open app → **Quick checks** → GRIM `5.19`, n `28`, **Test** | Red: "mean 5.19 is NOT possible with n = 28. Nearest reachable means: 5.14, 5.18, 5.21". Change n to 32 → green. |
| 0:40 | Back to **Analyse**, click demo **B**, **Check statistics** | Banner "6 serious inconsistencies found…", tiles 11 checked / 6 serious / 1 minor / 4 consistent |
| 1:15 | Point at highlighted text | Red/amber/green underlines; green ones were left alone |
| 1:35 | Click `t(58) = 1.40, p = .012` | Range bar: recomputed p ≈ .167 vs reported .012; explanation says significance flips |
| 2:00 | Click the GRIMMER item (`M = 3.50, SD = 1.00, n = 30`) | "mean possible, but no set of 30 whole numbers has this mean AND this SD" |
| 2:25 | Click the CI item (`OR = 1.80, 95% CI [0.95, 3.41], p = .03`) | "CI contains the null value (1) but p is reported as significant" |
| 2:50 | Load demo **C** | Greenhouse-Geisser, Bonferroni and one-tailed results → blue "needs context"; the unexplained copy → blue with "text does not say one-tailed". Say: *legitimate corrections are not false alarms* |
| 3:30 | Click **CSV / MD** export; open **Method & limits** | Honest limitations page |
| 4:00 | Optional: upload a text-layer PDF | Same report from a file |

Fallbacks: if the network or browser misbehaves, the same flow is in `docs/screens/` and every claim can be re-run with `python -m pytest tests -q` and `python -m eval.synthetic_benchmark 6000 2026`.

## C. Plain-language explanations (so you can defend every part)
- **Why intervals?** A printed 2.20 could be 2.195 to 2.205. That small uncertainty moves p. A checker that ignores it accuses honest authors.
- **GRIM in one line.** The mean of 28 whole numbers must be (a whole number) ÷ 28. 5.19 × 28 = 145.3, and neither 145 (5.18) nor 146 (5.21) rounds to 5.19.
- **GRIMMER in one line.** Same idea for the SD: given the sum S, the sum of squares Q must be a whole number with the same parity as S, and at least as big as the "most equal" arrangement.
- **Why Greenhouse-Geisser matters.** The correction shrinks the degrees of freedom by ε (between 1/df₁ and 1), which raises p. So a reported p *above* the uncorrected p can be legitimate, but *below* it never is.
- **Why no machine learning?** Every check has an exact mathematical ground truth. An ML model would be less accurate and could not show its arithmetic.

## D. Questions judges may ask, with accurate answers
1. **Isn't this just statcheck?** statcheck covers p-value recomputation for APA strings. We add GRIM/GRIMMER, percentage, CI and df-vs-N checks in one pipeline, rounding-interval logic for both the statistic and the reported p, and direction-aware handling of corrections. We have not benchmarked head-to-head with statcheck (R was not available to us), so we make no accuracy claim against it.
2. **Where is the AI?** There is deliberately none in the checks: deterministic mathematics is exact and explainable. Parsing is regex-based. An LLM or learned extractor is a sensible future addition for messy text and tables, with the deterministic checks still making the verdicts.
3. **How accurate is it on real papers?** Unknown, and we say so. We validated the mathematics exhaustively and the pipeline on a synthetic benchmark. Real-paper validation is the first next step; `scripts/scan_dir.py` is built for it.
4. **Your benchmark is synthetic, so isn't it circular?** Partly, and we label it so. It measures that honestly rounded numbers pass, that planted errors are caught, and what the exact-match alternative costs. It does not estimate real error prevalence. The GRIM and p-value mathematics are checked independently (exhaustive enumeration, a second implementation, scipy tables).
5. **What about false positives that damage an author's reputation?** Verdict wording is "numerical contradiction needing an explanation, not evidence of misconduct". Five verdict classes include "needs context". The recomputation is shown so the author can rebut it in seconds.
6. **Why does your baseline have 43.5% false positives, that sounds like a strawman?** It is a simple exact-match baseline of our own making, not statcheck, and it is labelled that way. It shows what happens if rounding is ignored, which is what the interval logic fixes. We make no claim about how statcheck would score.
7. **Can it be gamed?** Yes: an author can write numbers that are internally consistent but wrong, or omit statistics. It checks consistency, not truth.
8. **What does GRIMMER not catch?** It tests necessary conditions only, so some impossible SDs pass (power 92–97% in exhaustive tests on small bounded scales) but it never flags a feasible pair (0 false alarms in 60,000 real integer datasets).
9. **How do you handle one-tailed tests?** If the two-sided p does not match but p/2 does, we call it "consistent as one-tailed" when the sentence says one-tailed, otherwise "needs context".
10. **What about privacy of unpublished manuscripts?** Nothing leaves the server (no third-party calls); the "Save report" toggle off stores nothing; reports can be deleted.
11. **Can it scale?** The engine is lightweight: the benchmark analysed 6,000 short results in about 4 seconds on one core. It is stateless apart from SQLite, so it should scale horizontally, but the in-memory rate limiter would need a shared store in production. No load test was performed.
12. **What would you do with another month?** Validate on a corpus of open-access papers, add table extraction, scale bounds for GRIMMER, more test families, authenticated batch API.
13. **Why Python + React rather than your usual Node/Express?** SciPy gives trustworthy t/F/χ² tail probabilities and exact `Fraction` arithmetic; React keeps the UI interactive. The API contract is plain JSON, so Express could front it if needed.
14. **How do you know the p-values are right?** Tests compare against scipy and known table values (t(10)=2.228→.05, χ²(1)=3.841→.05); scipy is the reference implementation used by the research community. We did not cross-check against R in this environment.
15. **What is the GRIM test's well-known caveat?** Data must be integers (single items/counts). We expose "assume integer data" and "items per scale", and skip values with units like ms or kg.
