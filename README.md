# StatSleuth

**Statistical consistency forensics for scientific manuscripts.** Paste a results section (or upload a PDF) and StatSleuth
re-computes every reported p-value, tests means/SDs for mathematical possibility (GRIM / GRIMMER), and cross-checks
percentages, confidence intervals and degrees of freedom, all *allowing for rounding* and *for legitimate corrections*
(one-tailed tests, Greenhouse-Geisser, multiple-comparison adjustment).

Built for **THREWS ODYSSEY 2026**, track **DeepTech & Scientific Computing**.

> A flag is a numerical contradiction that needs an explanation (typo, undescribed correction, different test). It is
> **not** evidence of misconduct.

## What is in the box

| Path | What |
|---|---|
| `backend/app/engine/` | The checking engine: `parser.py` (extraction), `checks.py` (p-value, CI, percent, df/N), `grim.py` (GRIM + GRIMMER), `analyzer.py` |
| `backend/app/main.py` | FastAPI REST API, rate limiting, upload validation, optional static hosting of the UI |
| `backend/app/db.py` | SQLite persistence for saved reports |
| `backend/tests/` | 48 pytest tests (engine + API) |
| `backend/eval/` | Reproducible evaluation: seeded-error benchmark, GRIM/GRIMMER validation, correction experiment, UI smoke test |
| `frontend/` | React + Vite UI |
| `docs/` | `SUBMISSION.md` (hackathon write-up), `PRESENTATION.md` (slides outline, demo script, judge Q&A), evaluation JSON, screenshots |
| `data/sample_manuscripts/` | Three **synthetic** demo manuscripts (also served by the API) |
| `scripts/scan_dir.py` | Batch-scan a folder of papers into a CSV (for validating on your own real papers) |

## Quick start (about 3 minutes)

Requirements: Python 3.10+ and Node 18+. No API keys, no external services, no dataset download.

```bash
# 1) backend
cd backend
python -m venv .venv && source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
python -m pytest tests -q                                # expect: 48 passed
uvicorn app.main:app --port 8000

# 2) frontend (new terminal)
cd frontend
npm install
npm run dev                                              # open http://localhost:5173
```

The database file is created automatically on first start (`backend/data/statsleuth.db`); there is nothing to
initialise. To run as **one process** instead (UI served by FastAPI): `cd frontend && npm run build`, then start
uvicorn and open `http://localhost:8000`.

## Try it

1. Open the app, click the **B** demo chip, press **Check statistics**.
2. Expected: *6 serious inconsistencies*, 1 minor, 4 consistent, 11 statistics checked.
3. Click the **A** demo (all consistent) and **C** (corrections recognised; the last, unexplained result is flagged as needing context).
4. **Quick checks** page: GRIM `5.19`, n = 28 is impossible, n = 32 is possible (a documented example from the `scrutiny` R package docs).

## REST API

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/analyze` | `{text, title?, options?{alpha, items_per_scale, integer_data}, persist?}` → report |
| POST | `/api/analyze/file` | multipart `.txt/.md/.pdf` (≤ 5 MB) → report |
| GET | `/api/reports`, `/api/reports/{id}` | saved reports |
| DELETE | `/api/reports/{id}` | delete a saved report |
| GET | `/api/reports/{id}/export?format=json\|csv\|md` | downloads |
| POST | `/api/tools/grim` | `{mean:"5.19", n:28, items?, sd?}` (mean/SD are strings to keep trailing zeros) |
| POST | `/api/tools/pvalue` | `{kind, stat, df1?, df2?, p_rel, p}` |
| GET | `/api/samples`, `/api/samples/{id}` | synthetic demo manuscripts |
| GET | `/api/health` | liveness |

Interactive docs: `http://localhost:8000/docs`.

```bash
curl -s localhost:8000/api/tools/grim -H 'content-type: application/json' -d '{"mean":"5.19","n":28}'
# {"mean":"5.19","n":28,"items":1,"informative":true,"grim_consistent":false,"nearest_possible_means":["5.14","5.18","5.21"],...}
```

## Testing & evaluation

```bash
cd backend
python -m pytest tests -q                    # 48 tests, ~2 s
python -m eval.grim_validation               # exhaustive + cross-package validation of GRIM/GRIMMER
python -m eval.synthetic_benchmark 6000 2026 # seeded-error benchmark (SYNTHETIC)
python -m eval.correction_experiment         # Greenhouse-Geisser experiment (SYNTHETIC)
# UI end-to-end (needs: pip install playwright && playwright install chromium; server on :8000 with frontend built)
python -m eval.ui_smoke
```

Results are written to `docs/eval_*.json` and discussed honestly in `docs/SUBMISSION.md` (what they do and do not show).

## Deploying on a free tier (not done for this submission)

A single web service is enough: build command `pip install -r backend/requirements.txt && cd frontend && npm install && npm run build`,
start command `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT`. Free tiers have ephemeral disks, so saved
reports reset on redeploy (or mount a persistent disk and set `STATSLEUTH_DB`). No live deployment exists yet.

## Troubleshooting

| Symptom | Fix |
|---|---|
| UI says "Cannot reach the StatSleuth server" | Start the backend on port 8000 (dev mode proxies `/api` there) |
| `ModuleNotFoundError: app` | Run commands from the `backend/` directory |
| Port 8000 busy | `uvicorn app.main:app --port 8001` and change the proxy target in `frontend/vite.config.js` |
| PDF upload says "No text could be extracted" | The PDF is scanned images; run OCR first |
| Symbols (χ², minus signs) missing after PDF upload | PDF text layer lost them; paste the text or fix in a .txt file |
| `429 Too many requests` | Rate limit (60 POST/min/IP). Set `STATSLEUTH_RATE=0` for local bulk use |
| Playwright smoke test cannot launch a browser | `playwright install chromium` |
