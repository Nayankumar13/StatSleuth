"""Report export formats: JSON, CSV, Markdown."""
from __future__ import annotations

import csv
import io
import json


def to_csv(report: dict) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["id", "check", "status", "severity", "result", "explanation", "suggestion"])
    for f in report["findings"]:
        w.writerow([f["id"], f["kind"], f["status"], f["severity"], f["title"], f["explanation"], f["suggestion"]])
    return buf.getvalue()


def to_markdown(report: dict) -> str:
    s = report["summary"]
    lines = [f"# StatSleuth report: {report.get('title', 'Untitled')}", "",
             f"**Verdict.** {s['verdict']}", "",
             f"Checked {s['checked']} statistics; {s['flagged']} flagged ({s['gross']} serious).", "",
             "> Automated consistency checks only. A flag is a numerical contradiction to be explained, "
             "not an accusation of misconduct. Always verify against the source analysis.", "",
             "| # | Check | Status | Result | Explanation |", "|---|---|---|---|---|"]
    for f in report["findings"]:
        if f["status"] in ("ok", "na"):
            continue
        ex = f["explanation"].replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {f['id']} | {f['kind']} | {f['status']} | {f['title'].replace('|', '/')} | {ex} |")
    ok = sum(1 for f in report["findings"] if f["status"] == "ok")
    lines += ["", f"{ok} further statistics were verified as consistent."]
    return "\n".join(lines) + "\n"


def to_json(report: dict) -> str:
    return json.dumps(report, indent=2, ensure_ascii=False)
