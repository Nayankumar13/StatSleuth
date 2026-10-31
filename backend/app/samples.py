"""Demo manuscripts. ALL SYNTHETIC: written for this project, not taken from any
real paper. Numbers in 'clean' were generated from real integer data /
real distributions so they are consistent by construction; 'flawed' contains
deliberately seeded errors listed in `seeded`."""

CLEAN = """\
Synthetic demo manuscript A (consistent reporting)

Method. Sixty students (N = 60) were randomly assigned to a spaced-practice group (n = 30) or a massed-practice group (n = 30). A further 28 students (n = 28) completed a delayed follow-up in each arm.

Results. Self-rated confidence on a 7-point scale was higher in the spaced group (M = 4.43, SD = 1.19) than in the massed group (M = 4.33, SD = 1.27, n = 30). Confidence at follow-up (n = 28 per arm) was M = 4.96, SD = 1.04 for the spaced group and M = 4.61, SD = 1.47 for the massed group.

Exam scores differed between groups, t(58) = 2.84, p = .006, and the effect was present in the follow-up sample, t(54) = 3.12, p = .003. A three-level condition effect was significant, F(2, 57) = 4.71, p = .013. Passing the exam did not depend on gender, χ²(2, N = 60) = 7.31, p = .026. Study time correlated with the score, r(58) = .41, p = .001, but not with confidence, r(58) = .19, p = .146.

Of the spaced group, 14/30 (46.7%) passed with distinction, compared with 9/30 (30%) of the massed group. The odds of distinction were higher after spaced practice, OR = 2.10, 95% CI [1.20, 3.70], p = .008.
"""

FLAWED = """\
Synthetic demo manuscript B (seeded errors)

Method. Sixty participants (N = 60) were assigned to a treatment group (n = 30) or a control group (n = 30).

Results. Anxiety scores (1-5 scale) were lower after treatment, M = 3.48, SD = 0.90 (n = 30), than in controls, M = 3.50, SD = 1.00 (n = 30). The groups differed on the primary outcome, t(58) = 1.40, p = .012. A secondary outcome also differed, t(98) = 2.20, p = .030.

An exploratory F test was significant, F(2, 57) = 2.10, p = .031. Group membership was related to attendance, χ²(1, N = 60) = 5.02, p = .025.

Adherence was higher in the treatment group, 14/30 (43%) vs 9/30 (30%). Treatment raised the odds of response, OR = 1.80, 95% CI [0.95, 3.41], p = .03.

"""

CORRECTIONS = """\
Synthetic demo manuscript C (legitimate corrections that naive checkers flag)

Method. Participants (N = 60) completed three repeated sessions. We applied a Greenhouse-Geisser correction because Mauchly's test indicated a violation of sphericity. Pairwise comparisons were Bonferroni-adjusted. The directional hypothesis was tested with a one-tailed test.

Results. The session effect was significant after correction, F(2, 58) = 3.60, p = .059 (uncorrected degrees of freedom shown). Post-hoc, session 1 vs 2 was significant after Bonferroni adjustment, t(30) = 2.10, p = .13. The directional hypothesis was supported with a one-tailed test, t(30) = 2.10, p = .022.

A separate result is reported without any such explanation: t(30) = 2.10, p = .022.
"""

SEEDED = {
    "flawed": [
        "t(58) = 1.40 reported with p = .012 (true p = .167)",
        "M = 3.48 is impossible for n = 30 (GRIM)",
        "M = 3.50 with SD = 1.00 is impossible for n = 30 (GRIMMER)",
        "t(98) needs at least 99 participants but N = 60 (df vs N)",
        "F(2, 57) = 2.10 reported with p = .031 (true p = .132)",
        "14/30 reported as 43% (true 46.7%)",
        "OR = 1.80, 95% CI [0.95, 3.41] contains 1 but p = .03 is reported as significant",
    ]}

SAMPLES = [
    {"id": "clean", "title": "A – Consistent reporting (synthetic)",
     "description": "Everything checks out; shows how the tool avoids false alarms.", "text": CLEAN},
    {"id": "flawed", "title": "B – Seeded errors (synthetic)",
     "description": "Seven deliberately planted errors across all check types.", "text": FLAWED},
    {"id": "corrections", "title": "C – Corrections & one-tailed tests (synthetic)",
     "description": "Legitimate corrections are recognised; the unexplained copy at the end is flagged.", "text": CORRECTIONS},
]
