# SnapDeck backend (FastAPI)

## Setup

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

On first startup, `app/sample_bootstrap.py` auto-generates two bundled sample templates into `app/sample_data/` if they don't already exist:

- `template_deck.pptx` — a 3-slide deck (title, key metrics, headline insight)
- `template_onepager.docx` — a one-page Word document with the same tags

Both use plain `{{tag}}` placeholders (see below), so you never have to hand-build a template to see the demo work.

## API

All endpoints are also documented interactively at `http://127.0.0.1:8000/docs`.

### `GET /api/sample`
Returns the bundled sample dataset (`app/sample_data/sample.csv`), already parsed:
```json
{ "fields": {"title": "...", "revenue": "$2.4M", ...}, "chart": [{"label": "North America", "value": 120}, ...], "warnings": [] }
```

### `POST /api/parse`  (multipart/form-data)
Parses a data source into the same `{fields, chart, warnings}` shape, without generating anything.

| field | type | notes |
|---|---|---|
| `source_type` | `"csv"` \| `"sheet"` | required |
| `file` | file | required if `source_type=csv` |
| `sheet_url` | string | required if `source_type=sheet`; the sheet must be shared as "Anyone with the link can view" |

### `POST /api/render`  (multipart/form-data)
Generates the actual output file.

| field | type | notes |
|---|---|---|
| `fields` | string | JSON-encoded object, e.g. `{"title": "Q3 Business Review", "revenue": "$2.4M"}` |
| `chart` | string | JSON-encoded array, e.g. `[{"label": "APAC", "value": 60}]`; default `"[]"` |
| `template_type` | `"deck"` \| `"onepager"` | which bundled template to use; ignored if `template_file` is supplied |
| `include_chart` | `"true"` \| `"false"` | whether to render and embed a bar chart |
| `chart_title` | string | optional caption for the chart slide/section |
| `template_file` | file | optional — upload your own `.pptx` or `.docx` with `{{tag}}` placeholders instead of using the bundled sample |

Returns:
```json
{
  "file_id": "…",
  "download_url": "/api/download/…",
  "filename": "snapdeck-deck.pptx",
  "preview": { "title": "...", "subtitle": "...", "metrics": [...], "insight": "...", "chart_image_base64": "..." },
  "warnings": []
}
```

### `GET /api/download/{file_id}`
Streams back the generated `.pptx` / `.docx` file. Generated files live in-memory + on disk under `backend/generated/` for the life of the server process (there is no database or persistence beyond that — regenerate if the server restarts).

## Template tag convention

Any text placeholder written as `{{field_name}}` inside a `.pptx` or `.docx` file (in a text box, a table cell, or a body paragraph) will be replaced with the matching key from the `fields` you send. One special field, `ai_insight`, is always computed automatically and injected — you don't need to supply it yourself; just place `{{ai_insight}}` somewhere in your template if you want the generated insight sentence to appear.

## AI insight generation

`app/insight.py` first checks for `OPENAI_API_KEY` in the environment. All three settings — `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL` — are read from `backend/.env` (copy `.env.example` to get started; `python-dotenv` loads it automatically on startup, regardless of which directory you launch `uvicorn` from). If a key is present and the `openai` package is installed, SnapDeck sends a tightly-scoped prompt containing *only* the actual field values you provided, explicitly instructing the model not to invent numbers. `OPENAI_BASE_URL` is optional — leave it unset to hit OpenAI's default API, or point it at any OpenAI-compatible endpoint (Azure OpenAI, a self-hosted proxy, OpenRouter, etc.); `OPENAI_MODEL` defaults to `gpt-4o-mini` if not set. If no key is set (the default), a deterministic, rule-based sentence is generated instead from the same data — this keeps the demo 100% reliable even with no external API calls, no cost, and no network dependency.

## Design notes / known simplifications

- The in-browser "preview" is a structured summary reconstructed from the same data (title, metrics, insight, chart image) rather than a pixel-perfect render of the actual `.pptx`/`.docx` — full Office-document rendering to an image typically requires a heavy dependency like LibreOffice headless, which is deliberately out of scope for this demo (see the project's "Do Not Build" list).
- Tag replacement works at the paragraph level (joining all runs, replacing, then rewriting into the first run) specifically so it's robust even when PowerPoint/Word have split a single `{{tag}}` across multiple text runs, which is a common real-world quirk of hand-edited Office documents.
- There is no authentication, multi-tenancy, or persistent database — this is intentional; see the project's MVP scope for the reasoning.
