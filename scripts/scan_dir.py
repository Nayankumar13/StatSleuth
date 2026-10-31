"""Batch-scan a folder of .txt / .md / .pdf files and write a one-row-per-file CSV.

Use this to test StatSleuth on YOUR OWN open-access papers (e.g. PubMed Central OA articles saved as PDF/txt).
    python scripts/scan_dir.py path/to/papers  out.csv
"""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.engine import analyze  # noqa: E402


def read(p: Path) -> str:
    if p.suffix.lower() == ".pdf":
        from pypdf import PdfReader
        return "\n".join((pg.extract_text() or "") for pg in PdfReader(str(p)).pages)
    return p.read_text(encoding="utf-8", errors="replace")


def main(folder: str, out: str) -> None:
    rows = []
    for p in sorted(Path(folder).iterdir()):
        if p.suffix.lower() not in (".txt", ".md", ".pdf"):
            continue
        try:
            s = analyze(read(p))["summary"]
        except Exception as e:  # keep going on a bad file
            print(f"skip {p.name}: {e}")
            continue
        b = s["by_status"]
        rows.append([p.name, s["checked"], b.get("gross", 0), b.get("minor", 0), b.get("caveat", 0), b.get("ok", 0), s["verdict"]])
    with open(out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["file", "checked", "serious", "minor", "needs_context", "consistent", "verdict"])
        w.writerows(rows)
    print(f"wrote {out} ({len(rows)} files)")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(*sys.argv[1:])
