# SnapDeck

*From spreadsheet to slide, before your coffee gets cold.*

SnapDeck is a small demo project built to prove a specific point about [Rollstack](https://www.rollstack.com/): there's currently no self-serve way to experience the "connect your data, get a live slide deck" magic moment without booking a sales call. SnapDeck is a tiny, honest reconstruction of that core mechanic — upload a spreadsheet, pick a template, and get a finished, narrated deck or one-pager back in seconds, with zero login and zero setup.

This is **not** a Rollstack product, integration, or affiliate — it's an independent portfolio project referencing the reports-automation category, built to accompany the *Competitive Gap Analysis and Demo Project Document*.

## What it does

1. Loads a realistic sample "quarterly business review" dataset automatically (or accepts your own CSV, or a public Google Sheet link).
2. Lets you edit any value inline (e.g. bump revenue growth from 18% to 25%).
3. Fills a slide-deck (.pptx) or one-pager (.docx) template by matching `{{tag}}` placeholders to your data.
4. Generates one AI-written, data-grounded headline insight sentence and drops it onto its own slide/section.
5. Optionally renders a bar chart from your data and embeds it as an image.
6. Lets you click **Regenerate** after editing a value, to prove the "always current" idea live, in seconds.
7. Gives you a real, downloadable `.pptx` or `.docx` file at the end.

## Project structure

```
SnapDeck/
├── backend/     FastAPI service — data parsing, template filling, chart rendering, AI insight
└── frontend/    A plain HTML/CSS/JS single-page app (no build step) that talks to the backend
```

The backend serves the frontend itself, so there's only one thing to run — see `backend/README.md` for endpoint details, or `frontend/README.md` for the rare case you want to serve the frontend separately.

## Quick start (Windows / PowerShell)

**Run the backend — this is the only command you need**

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Then open **`http://127.0.0.1:8000`** in your browser — that's the full app UI, served directly by the backend (no separate frontend server, no second terminal, no build step). Interactive API docs are at `http://127.0.0.1:8000/docs`. Sample template files (`.pptx` / `.docx`) are generated automatically on first startup — there's nothing to download or configure.

*(Advanced/optional: `frontend/README.md` explains how to serve the frontend from its own static server instead, for a separate frontend-only dev workflow — not needed for normal use.)*

**(Optional) Turn on real AI insight generation**

By default, SnapDeck writes headline insights with a deterministic, data-grounded fallback (no API key required — it always works). To use a real LLM instead, copy `backend/.env.example` to `backend/.env`, add your OpenAI API key, and restart the backend:

```
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=
OPENAI_MODEL=gpt-4o-mini
```

`.env` is loaded automatically on startup. `OPENAI_BASE_URL` is optional — leave it blank to use OpenAI's default endpoint, or point it at any OpenAI-compatible endpoint (Azure OpenAI, a self-hosted proxy, OpenRouter, etc.).

## Why this exists

Full reasoning, competitor research, and the case for this specific demo project live in the accompanying document: `Rollstack_Gap_Analysis_and_Demo_Project.md`. In short: every competitor studied (think-cell, Zebra BI, and to some extent Slideform) offers a free trial or transparent self-serve entry point — Rollstack currently does not. SnapDeck is a small, safe, fast-to-build proof of what a self-serve "try it yourself" front door could feel like.
