# SnapDeck frontend

A plain HTML/CSS/JS single-page app — no build step, no framework, no npm install.

## Run it

```powershell
cd frontend
python -m http.server 5500
```

Then open `http://127.0.0.1:5500` in your browser. Make sure the backend is running first (see `../backend/README.md`) — by default the frontend expects it at `http://127.0.0.1:8000`.

If you serve the backend from a different host/port, change the constant at the bottom of `index.html`:

```html
<script>window.SNAPDECK_API_BASE = "http://127.0.0.1:8000";</script>
```

## Files

- `index.html` — page structure and layout (Tailwind via CDN for styling)
- `styles.css` — the handful of custom rules Tailwind's utility classes don't cover (tabs, buttons, row layout)
- `app.js` — all app logic: loading the sample dataset, uploading a CSV, fetching a Google Sheet, the editable fields/chart tables, calling `/api/render`, and rendering the preview + download link

## How the "prove the freshness" moment works

1. On load, the app calls `GET /api/sample` and renders the result into editable rows.
2. Every field/chart value lives in a small in-memory `state` object (see the top of `app.js`), edited live as you type.
3. Clicking **Generate** (later relabeled **Regenerate**) serializes the current `state` and posts it to `POST /api/render`.
4. Because generation always reads the *current* state rather than the original upload, editing one number and clicking Regenerate reproduces, at small scale, the "your report is always current" idea the whole demo is built around.
