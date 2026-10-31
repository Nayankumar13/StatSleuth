"""StatSleuth REST API (FastAPI)."""
from __future__ import annotations

import io
import os
from contextlib import asynccontextmanager
import time
from collections import defaultdict, deque
from typing import Literal, Optional

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field, field_validator

from . import db, export
from .engine import Options, analyze
from .engine import checks as C
from .engine.grim import grim, grimmer
from .engine.numeric import n_decimals
from .samples import SAMPLES, SEEDED

MAX_CHARS = 300_000
MAX_UPLOAD = 5 * 1024 * 1024
MAX_PDF_PAGES = 150
NUM_RE = r"^-?\d{1,12}(\.\d{1,10})?$"

@asynccontextmanager
async def lifespan(_: FastAPI):
    db.init()
    yield


app = FastAPI(title="StatSleuth API", version="1.0.0", lifespan=lifespan,
              description="Consistency checks for statistics reported in scientific text.")
app.add_middleware(CORSMiddleware,
                   allow_origins=os.environ.get("STATSLEUTH_CORS", "http://localhost:5173,http://127.0.0.1:5173").split(","),
                   allow_methods=["*"], allow_headers=["*"])


# ---- tiny in-memory rate limiter (per client IP) ---------------------------
_hits: dict[str, deque] = defaultdict(deque)
RATE = int(os.environ.get("STATSLEUTH_RATE", "60"))  # requests per minute on heavy endpoints


@app.middleware("http")
async def rate_limit(request: Request, call_next):
    if request.method == "POST" and RATE > 0:
        ip = request.client.host if request.client else "?"
        now, q = time.time(), _hits[ip]
        while q and now - q[0] > 60:
            q.popleft()
        if len(q) >= RATE:
            return JSONResponse({"detail": "Too many requests, slow down."}, status_code=429)
        q.append(now)
    return await call_next(request)


# ---- schemas ----------------------------------------------------------------
class OptionsIn(BaseModel):
    alpha: float = Field(0.05, gt=0, lt=1)
    items_per_scale: int = Field(1, ge=1, le=200)
    integer_data: bool = True


class AnalyzeIn(BaseModel):
    text: str = Field(..., min_length=1, max_length=MAX_CHARS)
    title: str = Field("Pasted text", max_length=200)
    options: OptionsIn = OptionsIn()
    persist: bool = True

    @field_validator("text")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("text is empty")
        return v


class GrimIn(BaseModel):
    mean: str = Field(..., pattern=NUM_RE)
    n: int = Field(..., ge=1, le=1_000_000)
    items: int = Field(1, ge=1, le=200)
    sd: Optional[str] = Field(None, pattern=NUM_RE)


class PValueIn(BaseModel):
    kind: Literal["t", "F", "chi2", "r", "z"]
    stat: str = Field(..., pattern=NUM_RE)
    df1: Optional[float] = Field(None, gt=0, le=1e7)
    df2: Optional[float] = Field(None, gt=0, le=1e7)
    p_rel: Literal["=", "<", ">"] = "="
    p: str = Field(..., pattern=r"^\d?\.?\d{1,10}$")


# ---- helpers ----------------------------------------------------------------
def _run(text: str, opts: OptionsIn, title: str, source: str, persist: bool) -> dict:
    result = analyze(text, Options(**opts.model_dump()))
    report = {"id": None, "title": title, "source": source, "text": text, **result}
    if persist:
        report["id"] = db.save(title, source, text, result)
    return report


def _pdf_text(data: bytes) -> str:
    from pypdf import PdfReader
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            raise HTTPException(422, "Encrypted PDFs are not supported.")
        pages = reader.pages[:MAX_PDF_PAGES]
        return "\n".join((pg.extract_text() or "") for pg in pages)
    except HTTPException:
        raise
    except Exception as e:  # corrupted file etc.
        raise HTTPException(422, f"Could not read PDF: {type(e).__name__}") from e


# ---- routes -----------------------------------------------------------------
@app.get("/api/health")
def health():
    return {"status": "ok", "version": app.version}


@app.get("/api/samples")
def samples():
    return [{k: v for k, v in s.items() if k != "text"} | {"seeded": SEEDED.get(s["id"], [])} for s in SAMPLES]


@app.get("/api/samples/{sid}")
def sample(sid: str):
    for s in SAMPLES:
        if s["id"] == sid:
            return s
    raise HTTPException(404, "Unknown sample")


@app.post("/api/analyze")
def analyze_text(body: AnalyzeIn):
    return _run(body.text, body.options, body.title, "paste", body.persist)


@app.post("/api/analyze/file")
async def analyze_file(file: UploadFile = File(...), alpha: float = Form(0.05), items_per_scale: int = Form(1),
                       integer_data: bool = Form(True), persist: bool = Form(True)):
    name = (file.filename or "upload").lower()
    if not name.endswith((".txt", ".md", ".pdf")):
        raise HTTPException(415, "Only .txt, .md and .pdf files are accepted.")
    data = await file.read(MAX_UPLOAD + 1)
    if len(data) > MAX_UPLOAD:
        raise HTTPException(413, "File is larger than 5 MB.")
    text = _pdf_text(data) if name.endswith(".pdf") else data.decode("utf-8", errors="replace")
    if not text.strip():
        raise HTTPException(422, "No text could be extracted (scanned PDFs need OCR first).")
    if len(text) > MAX_CHARS:
        raise HTTPException(413, f"Text is longer than {MAX_CHARS:,} characters.")
    try:
        opts = OptionsIn(alpha=alpha, items_per_scale=items_per_scale, integer_data=integer_data)
    except ValueError as e:
        raise HTTPException(422, str(e)) from e
    return _run(text, opts, file.filename or "upload", f"file:{file.filename}", persist)


@app.get("/api/reports")
def reports():
    return db.list_reports()


@app.get("/api/reports/{rid}")
def report(rid: str):
    r = db.get(rid)
    if not r:
        raise HTTPException(404, "Report not found")
    return r


@app.delete("/api/reports/{rid}")
def delete_report(rid: str):
    if not db.delete(rid):
        raise HTTPException(404, "Report not found")
    return {"deleted": rid}


@app.get("/api/reports/{rid}/export")
def export_report(rid: str, format: Literal["json", "csv", "md"] = "json"):
    r = db.get(rid)
    if not r:
        raise HTTPException(404, "Report not found")
    if format == "csv":
        return PlainTextResponse(export.to_csv(r), media_type="text/csv",
                                 headers={"Content-Disposition": f'attachment; filename="statsleuth-{rid}.csv"'})
    if format == "md":
        return PlainTextResponse(export.to_markdown(r), media_type="text/markdown",
                                 headers={"Content-Disposition": f'attachment; filename="statsleuth-{rid}.md"'})
    return PlainTextResponse(export.to_json(r), media_type="application/json",
                             headers={"Content-Disposition": f'attachment; filename="statsleuth-{rid}.json"'})


@app.post("/api/tools/grim")
def tool_grim(body: GrimIn):
    g = grim(body.mean, body.n, body.items)
    out = {"mean": body.mean, "n": body.n, "items": body.items, "informative": g.informative,
           "grim_consistent": g.consistent, "nearest_possible_means": g.nearest_possible,
           "candidate_sums": g.candidate_sums[:5]}
    if body.sd is not None:
        if body.items != 1:
            raise HTTPException(422, "GRIMMER is only implemented for single-item data (items = 1).")
        if body.n < 2:
            raise HTTPException(422, "SD needs n >= 2.")
        gm = grimmer(body.mean, body.sd, body.n)
        out |= {"sd": body.sd, "grimmer_consistent": gm.consistent, "grimmer_informative": gm.informative}
    return out


@app.post("/api/tools/pvalue")
def tool_pvalue(body: PValueIn):
    k = body.kind
    if k == "F" and (body.df1 is None or body.df2 is None):
        raise HTTPException(422, "F needs df1 and df2.")
    if k in ("t", "chi2", "r") and body.df1 is None:
        raise HTTPException(422, f"{k} needs df1.")
    stat = float(body.stat)
    if k in ("F", "chi2") and stat < 0:
        raise HTTPException(422, f"{k} cannot be negative.")
    if k == "r" and abs(stat) >= 1:
        raise HTTPException(422, "|r| must be < 1.")
    lo, hi, pt = C.p_range(k, body.stat, body.df1, body.df2)
    rlo, rhi, rpt = C.reported_range(body.p_rel, body.p)
    return {"computed_p": pt, "computed_p_range": [lo, hi], "reported_p_range": [rlo, rhi],
            "consistent": C.overlap((lo, hi), (rlo, rhi)),
            "one_tailed_p": pt / 2 if k in ("t", "z", "r") else None,
            "statistic_decimals": n_decimals(body.stat)}


# ---- optional: serve the built React app from the same process (single-service deploy) -------------
from pathlib import Path  # noqa: E402

from fastapi.staticfiles import StaticFiles  # noqa: E402
from fastapi.responses import FileResponse  # noqa: E402

_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if _DIST.is_dir():
    app.mount("/assets", StaticFiles(directory=_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(404, "Not found")
        f = (_DIST / full_path).resolve()
        if full_path and f.is_file() and _DIST in f.parents:
            return FileResponse(f)
        return FileResponse(_DIST / "index.html")
