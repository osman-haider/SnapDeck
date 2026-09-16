# SnapDeck frontend

A plain HTML/CSS/JS single-page app — no build step, no framework, no npm install.

## Normal usage: you don't run this separately

The FastAPI backend mounts this entire folder as static files and serves it at `/` (see the bottom of `backend/app/main.py`). So the normal way to use SnapDeck is just to run the backend (`../backend/README.md`) and open `http://127.0.0.1:8000` — that request is served by the same origin, so `index.html` calls the API with relative paths (`window.SNAPDECK_API_BASE = ""`, set in `index.html`) and everything just works. There is nothing to start here.

## Optional: serving this folder on its own

You'd only do this if you're actively editing frontend files and want a separate dev server (e.g. one with live-reload) instead of restarting `uvicorn` each time — `uvicorn --reload` already picks up backend changes, but static files are just files, so any static server works fine too:

```powershell
cd frontend
python -m http.server 5500
```

Then open `http://127.0.0.1:5500`. Because the frontend is now on a *different* origin than the backend (`8000` vs `5500`), point it at the backend explicitly by changing the constant at the bottom of `index.html`:

```html
<script>window.SNAPDECK_API_BASE = "http://127.0.0.1:8000";</script>
```

(The backend's CORS middleware already allows all origins, so this cross-origin setup works out of the box.)

## Files

- `index.html` — page structure and layout (Tailwind via CDN for styling)
- `styles.css` — the handful of custom rules Tailwind's utility classes don't cover (tabs, buttons, row layout)
- `app.js` — all app logic: loading the sample dataset, uploading a CSV, fetching a Google Sheet, the editable fields/chart tables, calling `/api/render`, and rendering the preview + download link

## How the "prove the freshness" moment works

1. On load, the app calls `GET /api/sample` and renders the result into editable rows.
2. Every field/chart value lives in a small in-memory `state` object (see the top of `app.js`), edited live as you type.
3. Clicking **Generate** (later relabeled **Regenerate**) serializes the current `state` and posts it to `POST /api/render`.
4. Because generation always reads the *current* state rather than the original upload, editing one number and clicking Regenerate reproduces, at small scale, the "your report is always current" idea the whole demo is built around.
