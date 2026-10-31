"""Orchestration: parse -> run every check -> summarise."""
from __future__ import annotations

import bisect
import math
from dataclasses import dataclass

from . import checks as C
from . import parser as P


@dataclass
class Options:
    alpha: float = 0.05
    items_per_scale: int = 1          # items averaged into each reported mean
    integer_data: bool = True         # GRIM/GRIMMER assume integer-valued data

    def validate(self) -> "Options":
        if not (0 < self.alpha < 1):
            raise ValueError("alpha must be between 0 and 1")
        if not (1 <= self.items_per_scale <= 200):
            raise ValueError("items_per_scale must be between 1 and 200")
        return self


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def _utf16_offsets(text: str):
    """JS indexes strings by UTF-16 units; Python by code points."""
    astral = [i for i, ch in enumerate(text) if ord(ch) > 0xFFFF]

    def conv(i: int) -> int:
        return i + bisect.bisect_left(astral, i)
    return conv


def analyze(text: str, options: Options | None = None) -> dict:
    opt = (options or Options()).validate()
    parsed = P.parse(text)
    findings: list[C.Finding] = []

    for r in parsed.results:
        findings.append(C.check_pvalue(r, opt.alpha))
        if parsed.max_total_n:
            f = C.check_df_n(r, parsed.max_total_n)
            if f:
                findings.append(f)
    for m in parsed.means:
        findings.extend(C.check_mean(m, opt.items_per_scale, opt.integer_data))
    for pc in parsed.pcts:
        findings.append(C.check_pct(pc))
    for c in parsed.cis:
        findings.append(C.check_ci(c, opt.alpha))

    findings.sort(key=lambda f: (f.start, f.kind))
    conv = _utf16_offsets(text)
    out = []
    for i, f in enumerate(findings, 1):
        f.id = i
        d = f.to_dict()
        d["start"], d["end"] = conv(f.start), conv(f.end)
        out.append(d)

    return {"findings": out, "summary": summarise(out, len(text)), "options": opt.__dict__}


def summarise(findings: list[dict], n_chars: int) -> dict:
    by_status: dict[str, int] = {}
    by_kind: dict[str, dict[str, int]] = {}
    for f in findings:
        by_status[f["status"]] = by_status.get(f["status"], 0) + 1
        k = by_kind.setdefault(f["kind"], {})
        k[f["status"]] = k.get(f["status"], 0) + 1
    checked = sum(v for s, v in by_status.items() if s not in ("na", "unverifiable"))
    flagged = by_status.get("minor", 0) + by_status.get("gross", 0)
    lo, hi = wilson(flagged, checked)
    return {
        "n_chars": n_chars,
        "n_findings": len(findings),
        "by_status": by_status,
        "by_kind": by_kind,
        "checked": checked,
        "flagged": flagged,
        "gross": by_status.get("gross", 0),
        "flag_rate": (flagged / checked) if checked else None,
        "flag_rate_ci95": [lo, hi] if checked else None,
        "verdict": verdict(by_status, checked),
    }


def verdict(by_status: dict[str, int], checked: int) -> str:
    g, m = by_status.get("gross", 0), by_status.get("minor", 0)
    if checked == 0:
        return "No checkable statistics were found."
    if g:
        return (f"{g} serious inconsistenc{'y' if g == 1 else 'ies'} found. These are numerical contradictions that need "
                "an explanation; they are not evidence of misconduct.")
    if m:
        return f"{m} minor inconsistenc{'y' if m == 1 else 'ies'} found; conclusions are unaffected."
    return "No inconsistencies found among the statistics that could be checked."
