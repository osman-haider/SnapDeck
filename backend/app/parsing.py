"""Turn a CSV (uploaded or pulled from a public Google Sheet) into the simple
data shape SnapDeck works with everywhere else: a flat dict of scalar
``fields`` (for text-tag replacement) plus an optional list of ``chart``
{label, value} points (for the bar-chart nice-to-have).

Expected CSV shape (extra/blank cells are fine):

    field,value,chart_label,chart_value
    title,Q3 Business Review,,
    revenue,$2.4M,,
    ,,North America,120
    ,,EMEA,95

A row can set a scalar field, a chart point, both, or neither — whatever is
present in that row is used.
"""

from __future__ import annotations

import csv
import io
import re
from typing import Any

import requests

REQUIRED_COLUMNS = {"field", "value"}
CHART_COLUMNS = {"chart_label", "chart_value"}


def _clean_number(raw: str) -> float:
    """Best-effort strip of $, %, and thousands separators before float()."""
    cleaned = raw.strip().replace(",", "").replace("$", "").replace("%", "")
    return float(cleaned)


def parse_csv_text(text: str) -> tuple[dict[str, str], list[dict[str, Any]], list[str]]:
    """Parse raw CSV text into (fields, chart, warnings)."""
    warnings: list[str] = []
    reader = csv.DictReader(io.StringIO(text))

    if reader.fieldnames is None:
        raise ValueError("That CSV appears to be empty.")

    columns = {c.strip().lower() for c in reader.fieldnames if c}
    if not REQUIRED_COLUMNS.issubset(columns):
        raise ValueError(
            "CSV must include at least a 'field' column and a 'value' column "
            "(chart_label/chart_value are optional)."
        )
    has_chart_columns = CHART_COLUMNS.issubset(columns)

    fields: dict[str, str] = {}
    chart: list[dict[str, Any]] = []

    for i, row in enumerate(reader, start=2):  # row 1 is the header
        # Normalize keys to lowercase so header casing (Field, FIELD, field, ...)
        # never silently drops a column — only the *values* are case-sensitive.
        row_lower = {(k or "").strip().lower(): v for k, v in row.items() if k is not None}

        field_name = (row_lower.get("field") or "").strip()
        field_value = (row_lower.get("value") or "").strip()
        if field_name:
            fields[field_name] = field_value

        if has_chart_columns:
            chart_label = (row_lower.get("chart_label") or "").strip()
            chart_value_raw = (row_lower.get("chart_value") or "").strip()
            if chart_label:
                if not chart_value_raw:
                    warnings.append(f"Row {i}: '{chart_label}' has no chart_value — skipped.")
                    continue
                try:
                    chart.append({"label": chart_label, "value": _clean_number(chart_value_raw)})
                except ValueError:
                    warnings.append(
                        f"Row {i}: could not read chart_value '{chart_value_raw}' for "
                        f"'{chart_label}' as a number — skipped."
                    )

    if not fields:
        warnings.append("No scalar fields were found — check that your 'field'/'value' columns are filled in.")

    return fields, chart, warnings


def _extract_sheet_id(sheet_url: str) -> str:
    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", sheet_url)
    if not match:
        raise ValueError(
            "That doesn't look like a Google Sheets URL. Expected something like "
            "https://docs.google.com/spreadsheets/d/.../edit"
        )
    return match.group(1)


def _extract_gid(sheet_url: str) -> str | None:
    gid_match = re.search(r"[?#&]gid=(\d+)", sheet_url)
    return gid_match.group(1) if gid_match else None


def to_csv_export_url(sheet_url: str, gid: str | None = None) -> str:
    """Build a Google Sheets CSV-export URL.

    If ``gid`` is omitted, no gid parameter is added at all (rather than
    guessing "0") — Google's /export endpoint returns its default/first sheet
    when gid is absent, but returns an HTTP 400 for a gid that doesn't exist.
    Guessing "0" is wrong often enough (reordered/duplicated/deleted tabs
    all shift which gid is really first) that omitting it is the safer default.
    """
    sheet_id = _extract_sheet_id(sheet_url)
    base = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    return f"{base}&gid={gid}" if gid else base


def _looks_like_html(text: str) -> bool:
    stripped = text.lstrip()
    return stripped.startswith("<") or "<html" in stripped[:200].lower()


def _fetch_csv(url: str) -> str:
    """Fetch one export URL, raising ValueError with a clear reason on any failure."""
    try:
        response = requests.get(url, timeout=10)
    except requests.RequestException as exc:
        raise ValueError(f"Could not reach that Google Sheet: {exc}") from exc

    if response.status_code != 200:
        raise ValueError(f"Google responded with HTTP {response.status_code} for that sheet.")

    # A private/misconfigured sheet usually redirects to an HTML sign-in page
    # instead of returning CSV — 200 OK, but not actually the data we want.
    if _looks_like_html(response.text):
        raise ValueError(
            "That Google Sheet doesn't look publicly readable. Set sharing to "
            "'Anyone with the link can view' and try again."
        )

    return response.text


def parse_google_sheet(sheet_url: str) -> tuple[dict[str, str], list[dict[str, Any]], list[str]]:
    """Fetch a public Google Sheet as CSV and parse it the same way as an upload.

    Tries the specific tab from the URL's gid (if present) first, since that's
    the exact tab the person is looking at; falls back to the sheet's default
    export (no gid) if that attempt fails, since a stale or mismatched gid is a
    common cause of an otherwise-correctly-shared sheet failing to load.
    """
    gid = _extract_gid(sheet_url)
    urls_to_try = []
    if gid:
        urls_to_try.append(to_csv_export_url(sheet_url, gid=gid))
    urls_to_try.append(to_csv_export_url(sheet_url))  # default/first sheet, no gid

    last_error = "Could not read that Google Sheet."
    for url in urls_to_try:
        try:
            csv_text = _fetch_csv(url)
        except ValueError as exc:
            last_error = str(exc)
            continue
        return parse_csv_text(csv_text)

    raise ValueError(
        f"{last_error} Make sure sharing is set to 'Anyone with the link can view', then try again."
    )
