"""SnapDeck API — turn a spreadsheet into a finished, narrated slide deck or
one-pager document in seconds.

Endpoints:
  GET  /api/health            liveness check
  GET  /api/sample            bundled sample dataset, pre-parsed
  POST /api/parse             parse an uploaded CSV or a public Google Sheet URL
  POST /api/render            fill a template + generate the AI insight + (optional) chart
  GET  /api/download/{id}     download a previously generated file
  GET  /                      the frontend UI itself (see the static mount at the bottom
                              of this file) — running just this backend is enough to use
                              SnapDeck; there's no separate frontend server to start.

See backend/README.md for full request/response shapes.
"""

from __future__ import annotations

import base64
import json
import tempfile
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import charts, parsing, storage, templating
from . import insight as insight_module
from .sample_bootstrap import ensure_sample_templates

BASE_DIR = Path(__file__).resolve().parent  # .../backend/app
BACKEND_DIR = BASE_DIR.parent  # .../backend
PROJECT_DIR = BACKEND_DIR.parent  # .../SnapDeck
SAMPLE_DIR = BASE_DIR / "sample_data"
FRONTEND_DIR = PROJECT_DIR / "frontend"

# The bundled sample templates are gitignored and generated on first run (see
# sample_bootstrap.py). The deployed source tree is read-only on Vercel, so
# they're generated into the system temp dir instead of SAMPLE_DIR itself.
TEMPLATE_DIR = Path(tempfile.gettempdir()) / "snapdeck-templates"

# Load backend/.env (OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL_NAME) regardless of
# the current working directory the server happens to be started from.
load_dotenv(dotenv_path=BACKEND_DIR / ".env")

app = FastAPI(
    title="SnapDeck API",
    description=(
        "Turn a spreadsheet into a finished, narrated slide deck or one-pager "
        "document in seconds — a small demo of what a self-serve trial for a "
        "reports-automation product could feel like."
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _on_startup() -> None:
    ensure_sample_templates(TEMPLATE_DIR)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/sample")
def get_sample():
    """Return the bundled sample QBR dataset, already parsed — used to populate
    the frontend with zero setup on first load."""
    csv_path = SAMPLE_DIR / "sample.csv"
    if not csv_path.exists():
        raise HTTPException(500, "Sample dataset is missing from the server.")
    fields, chart, warnings = parsing.parse_csv_text(csv_path.read_text(encoding="utf-8-sig"))
    return {"fields": fields, "chart": chart, "warnings": warnings}


@app.post("/api/parse")
async def parse_source(
    source_type: str = Form(..., description="'csv' or 'sheet'"),
    file: Optional[UploadFile] = File(None),
    sheet_url: Optional[str] = Form(None),
):
    try:
        if source_type == "csv":
            if file is None:
                raise HTTPException(400, "No CSV file was uploaded.")
            raw = await file.read()
            fields, chart, warnings = parsing.parse_csv_text(raw.decode("utf-8-sig"))
        elif source_type == "sheet":
            if not sheet_url:
                raise HTTPException(400, "No Google Sheet URL was provided.")
            fields, chart, warnings = parsing.parse_google_sheet(sheet_url)
        else:
            raise HTTPException(400, "source_type must be 'csv' or 'sheet'.")
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    return {"fields": fields, "chart": chart, "warnings": warnings}


@app.post("/api/render")
async def render(
    fields: str = Form(..., description="JSON-encoded object of field name -> value"),
    chart: str = Form("[]", description="JSON-encoded array of {label, value}"),
    template_type: str = Form("deck", description="'deck' or 'onepager' (ignored if template_file is set)"),
    include_chart: str = Form("false"),
    chart_title: str = Form("Regional Breakdown"),
    template_file: Optional[UploadFile] = File(None, description="Optional custom .pptx/.docx template"),
):
    try:
        fields_dict: dict[str, str] = json.loads(fields)
        chart_list: list[dict] = json.loads(chart)
    except json.JSONDecodeError as exc:
        raise HTTPException(400, "'fields' and 'chart' must be valid JSON.") from exc

    if not isinstance(fields_dict, dict):
        raise HTTPException(400, "'fields' must be a JSON object.")
    if not isinstance(chart_list, list):
        raise HTTPException(400, "'chart' must be a JSON array.")

    include_chart_bool = str(include_chart).strip().lower() in ("1", "true", "yes", "on")
    warnings: list[str] = []

    # 1. Generate the AI (or fallback) insight and fold it into the fields
    #    used for tag replacement, so it's treated just like any other tag.
    insight_text = insight_module.generate_insight(fields_dict, chart_list)
    fields_for_template = dict(fields_dict)
    fields_for_template["ai_insight"] = insight_text

    # 2. Load the template: a user-supplied file, or one of the bundled samples.
    if template_file is not None:
        raw_template_bytes = await template_file.read()
        filename_lower = (template_file.filename or "").lower()
        is_pptx = filename_lower.endswith(".pptx")
        is_docx = filename_lower.endswith(".docx")
        if not (is_pptx or is_docx):
            raise HTTPException(400, "Custom templates must be a .pptx or .docx file.")
    else:
        is_pptx = template_type == "deck"
        is_docx = template_type == "onepager"
        if not (is_pptx or is_docx):
            raise HTTPException(400, "template_type must be 'deck' or 'onepager'.")
        template_path = TEMPLATE_DIR / ("template_deck.pptx" if is_pptx else "template_onepager.docx")
        if not template_path.exists():
            # Serverless platforms don't reliably run ASGI startup events, so
            # fall back to generating it here on first use.
            ensure_sample_templates(TEMPLATE_DIR)
        if not template_path.exists():
            raise HTTPException(500, "Sample template is missing — restart the server to regenerate it.")
        raw_template_bytes = template_path.read_bytes()

    # 3. Optionally render the chart image once, reused for embed + preview.
    chart_png_b64: Optional[str] = None
    if include_chart_bool:
        if not chart_list:
            warnings.append("Chart was requested but no chart data was supplied — skipped.")
        else:
            try:
                chart_png_bytes = charts.render_bar_chart(chart_list, chart_title)
                chart_png_b64 = base64.b64encode(chart_png_bytes).decode("ascii")
            except Exception as exc:  # noqa: BLE001 - surface as a warning, don't fail the whole render
                warnings.append(f"Could not render the chart: {exc}")

    # 4. Fill the template and (optionally) append the chart.
    if is_pptx:
        filled_bytes, _used_tags, missing = templating.fill_pptx(raw_template_bytes, fields_for_template)
        if chart_png_b64:
            filled_bytes = templating.add_chart_slide_pptx(
                filled_bytes, base64.b64decode(chart_png_b64), chart_title
            )
        media_type = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        out_filename = "snapdeck-deck.pptx"
    else:
        filled_bytes, _used_tags, missing = templating.fill_docx(raw_template_bytes, fields_for_template)
        if chart_png_b64:
            filled_bytes = templating.add_chart_image_docx(
                filled_bytes, base64.b64decode(chart_png_b64), chart_title
            )
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        out_filename = "snapdeck-onepager.docx"

    if missing:
        warnings.append(
            "These fields had no matching {{tag}} anywhere in the template, so they were "
            "ignored: " + ", ".join(sorted(missing))
        )

    file_id = storage.save_generated_file(filled_bytes, out_filename, media_type)

    preview = {
        "title": fields_dict.get("title", ""),
        "subtitle": fields_dict.get("subtitle", ""),
        "metrics": [
            {"label": key.replace("_", " ").title(), "value": value}
            for key, value in fields_dict.items()
            if key not in ("title", "subtitle")
        ],
        "insight": insight_text,
        "chart_image_base64": chart_png_b64,
    }

    return {
        "file_id": file_id,
        "download_url": f"/api/download/{file_id}",
        "filename": out_filename,
        "preview": preview,
        "warnings": warnings,
    }


@app.get("/api/download/{file_id}")
def download(file_id: str):
    record = storage.get_generated_file(file_id)
    if not record:
        raise HTTPException(
            404,
            "That generated file wasn't found — it may have expired after a server restart. "
            "Click Generate again.",
        )
    return FileResponse(path=record["path"], filename=record["filename"], media_type=record["media_type"])


# --------------------------------------------------------------------------- #
# Serve the frontend
# --------------------------------------------------------------------------- #
# Mounted LAST and deliberately at "/" so it acts as a catch-all: every /api/*
# route and FastAPI's own /docs, /redoc, /openapi.json are matched first
# because they were registered above this point. html=True makes StaticFiles
# serve frontend/index.html for "/" itself, so opening this backend's own URL
# in a browser is the entire app — no separate frontend server required.
if FRONTEND_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
