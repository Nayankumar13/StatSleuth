"""Extraction of reported statistics from free text.

Everything here is deterministic regular-expression parsing. The text is first
passed through a *length-preserving* character translation (unicode minus,
chi, superscript 2 ...), so character offsets found here are valid offsets into
the user's original text and the UI can highlight them.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

_TRANS = str.maketrans({
    "−": "-", "–": "-", "—": "-", "‐": "-", "‑": "-",
    " ": " ", " ": " ", " ": " ", " ": " ",
    "²": "2", "χ": "x", "Χ": "x",
    "ｐ": "p", "＝": "=", "＜": "<", "＞": ">",
    "≤": "<", "≥": ">",
})


def normalise(text: str) -> str:
    out = text.translate(_TRANS)
    assert len(out) == len(text)
    return out


NUM = r"-?(?:\d+\.\d+|\.\d+|\d+)"
UNUM = r"(?:\d+\.\d+|\.\d+|\d+)"

RE_T = re.compile(rf"(?<![A-Za-z])t\s*\(\s*(?P<df>\d+(?:\.\d+)?)\s*\)\s*=\s*(?P<stat>{NUM})", re.I)
RE_F = re.compile(rf"(?<![A-Za-z])F\s*\(\s*(?P<df1>\d+(?:\.\d+)?)\s*,\s*(?P<df2>\d+(?:\.\d+)?)\s*\)\s*=\s*(?P<stat>{NUM})")
RE_CHI = re.compile(
    rf"(?<![A-Za-z])(?:x2|chi-?\s?squared?|chi2)\s*\(\s*(?P<df>\d+)\s*(?:,\s*N\s*=\s*(?P<N>\d[\d,]*)\s*)?\)\s*=\s*(?P<stat>{NUM})",
    re.I)
RE_R = re.compile(rf"(?<![A-Za-z])r\s*\(\s*(?P<df>\d+)\s*\)\s*=\s*(?P<stat>{NUM})")
RE_Z = re.compile(rf"(?<![A-Za-z])z\s*=\s*(?P<stat>{NUM})", re.I)
RE_P = re.compile(rf"(?<![A-Za-z])p\s*(?P<rel><=|>=|=|<|>)\s*(?P<p>{UNUM})", re.I)

TEST_RES = [("t", RE_T), ("F", RE_F), ("chi2", RE_CHI), ("r", RE_R), ("z", RE_Z)]

RE_MSD = re.compile(
    rf"(?<![A-Za-z])(?:M|mean)\s*=\s*(?P<m>{NUM})\s*(?:,|;|\()?\s*SD\s*=\s*(?P<sd>{NUM})", re.I)
RE_N = re.compile(r"(?<![A-Za-z])n\s*=\s*(?P<n>\d[\d,]*)", re.I)
RE_BIGN = re.compile(r"(?<![A-Za-z])N\s*=\s*(?P<n>\d[\d,]*)")
RE_PCT1 = re.compile(rf"(?P<k>\d+)\s*(?:/|of|out of)\s*(?P<n>\d+)\s*\(\s*(?P<pct>{UNUM})\s*%\s*\)", re.I)
RE_PCT2 = re.compile(rf"(?P<pct>{UNUM})\s*%\s*\(\s*n\s*=\s*(?P<k>\d+)\s*(?:/|of|out of)\s*(?P<n>\d+)\s*\)", re.I)
RE_CI = re.compile(
    rf"(?<![A-Za-z])(?P<name>aOR|aRR|aHR|OR|RR|HR|IRR|PR|MD|SMD|b|B|beta|β|d|g|diff)\s*=\s*(?P<est>{NUM})\s*[,;(]?\s*"
    rf"(?P<lvl>\d{{2}})\s*%\s*(?:CI|confidence\s+interval)\s*(?:=|:)?\s*[\[(]?\s*(?P<lo>{NUM})\s*(?:,|;|to|-)\s*(?P<hi>{NUM})\s*[\])]?",
    re.I)

RATIO_NAMES = {"or", "rr", "hr", "irr", "pr", "aor", "arr", "ahr"}
NONLINEAR_CI = {"d", "g", "smd"}  # effect-size CIs are not exactly symmetric

KW_CORRECTION = re.compile(r"greenhouse|geisser|huynh|feldt|sphericity|epsilon|ε|mauchly", re.I)
KW_ADJUST = re.compile(r"bonferroni|holm|sidak|šidák|benjamini|hochberg|\bfdr\b|adjusted|corrected for multiple|tukey|scheff", re.I)
KW_ONETAIL = re.compile(r"one-?\s?tailed|one-?\s?sided|1-?tailed|directional hypothesis", re.I)
KW_CONTINUOUS = re.compile(
    r"\b(ms|msec|milliseconds?|seconds?|sec|reaction time|rt|kg|cm|mm|mg|db|hz|°c|percent|proportion)\b|µv|μv|%",
    re.I)


@dataclass
class Result:
    """A complete null-hypothesis-test result: statistic, df and p."""
    kind: str
    start: int
    end: int
    raw: str
    stat: str
    df1: Optional[str]
    df2: Optional[str]
    p_rel: str
    p: str
    N: Optional[int]
    ctx: str                 # the sentence containing the result
    doc_correction: bool = False   # sphericity-correction keyword anywhere in the document
    doc_adjust: bool = False       # multiple-comparison keyword anywhere in the document


@dataclass
class MeanSD:
    start: int
    end: int
    raw: str
    mean: str
    sd: str
    n: Optional[int]
    n_source: str
    unit_hint: bool


@dataclass
class Pct:
    start: int
    end: int
    raw: str
    k: int
    n: int
    pct: str


@dataclass
class CIResult:
    start: int
    end: int
    raw: str
    name: str
    est: str
    lo: str
    hi: str
    level: int
    p_rel: Optional[str]
    p: Optional[str]


@dataclass
class Parsed:
    results: list[Result] = field(default_factory=list)
    means: list[MeanSD] = field(default_factory=list)
    pcts: list[Pct] = field(default_factory=list)
    cis: list[CIResult] = field(default_factory=list)
    max_total_n: Optional[int] = None


def _int(s: str) -> int:
    return int(s.replace(",", ""))


def _p_after(text: str, end: int, stops: list[int]):
    seg_end = min(len(text), end + 90)
    for s in stops:
        if end < s < seg_end:
            seg_end = s
    seg = text[end:seg_end]
    cut = re.search(r"\.\s+[A-Z]|\n\s*\n", seg)
    if cut:
        seg = seg[:cut.start()]
    m = RE_P.search(seg)
    if not m:
        return None
    return m.group("rel"), m.group("p"), end + m.end()


def _sentence_bounds(text: str, a: int, b: int) -> tuple[int, int]:
    left = max(text.rfind(". ", 0, a), text.rfind("\n", 0, a))
    left = 0 if left < 0 else left + 1
    cands = [i for i in (text.find(". ", b), text.find("\n", b)) if i >= 0]
    right = min(cands) if cands else len(text)
    return left, right


def parse(raw_text: str) -> Parsed:
    text = normalise(raw_text)
    out = Parsed()

    # ---- NHST results -----------------------------------------------------
    starts: list[int] = []
    found = []
    for kind, rx in TEST_RES:
        for m in rx.finditer(text):
            found.append((kind, m))
            starts.append(m.start())
    starts.sort()
    seen_spans: list[tuple[int, int]] = []
    for kind, m in sorted(found, key=lambda km: km[1].start()):
        pm = _p_after(text, m.end(), starts)
        if not pm:
            continue
        rel, p, pend = pm
        if any(s <= m.start() < e for s, e in seen_spans):
            continue
        seen_spans.append((m.start(), pend))
        g = m.groupdict()
        sl, sr = _sentence_bounds(text, m.start(), pend)
        ctx = text[sl:sr]
        out.results.append(Result(
            kind=kind, start=m.start(), end=pend, raw=raw_text[m.start():pend],
            stat=g["stat"],
            df1=g.get("df1") or g.get("df"),
            df2=g.get("df2"),
            p_rel=rel, p=p,
            N=_int(g["N"]) if g.get("N") else None,
            ctx=ctx,
            doc_correction=bool(KW_CORRECTION.search(text)),
            doc_adjust=bool(KW_ADJUST.search(text))))

    # ---- total N mentions -------------------------------------------------
    ns = [_int(m.group("n")) for m in RE_BIGN.finditer(text)]
    ns += [r.N for r in out.results if r.N]
    out.max_total_n = max(ns) if ns else None

    # ---- mean / SD with nearest n ----------------------------------------
    for m in RE_MSD.finditer(text):
        left, right = _sentence_bounds(text, m.start(), m.end())
        centre = (m.start() + m.end()) // 2
        n_val, src = None, "none found"
        best = None
        for nm in RE_N.finditer(text, left, right):
            d = abs((nm.start() + nm.end()) // 2 - centre)
            if best is None or d < best[0]:
                best = (d, _int(nm.group("n")))
        if best:
            n_val, src = best[1], "same sentence"
        else:
            pl, pr = _sentence_bounds(text, max(0, left - 2), max(0, left - 1))
            for nm in RE_N.finditer(text, pl, pr):
                n_val, src = _int(nm.group("n")), "previous sentence"
        # unit hints only count right next to the numbers, never in a neighbouring sentence
        win = text[max(0, m.start() - 12): m.end() + 14]
        win = re.split(r"\.\s+[A-Z]|\n", win)[0]
        out.means.append(MeanSD(m.start(), m.end(), raw_text[m.start():m.end()],
                                m.group("m"), m.group("sd"), n_val, src,
                                bool(KW_CONTINUOUS.search(win))))

    # ---- k/n (pct) --------------------------------------------------------
    for rx in (RE_PCT1, RE_PCT2):
        for m in rx.finditer(text):
            out.pcts.append(Pct(m.start(), m.end(), raw_text[m.start():m.end()],
                                int(m.group("k")), int(m.group("n")), m.group("pct")))

    # ---- effect + CI (+ p) -----------------------------------------------
    for m in RE_CI.finditer(text):
        pm = _p_after(text, m.end(), starts)
        out.cis.append(CIResult(
            m.start(), pm[2] if pm else m.end(),
            raw_text[m.start(): pm[2] if pm else m.end()],
            m.group("name"), m.group("est"), m.group("lo"), m.group("hi"),
            int(m.group("lvl")), pm[0] if pm else None, pm[1] if pm else None))
    return out
