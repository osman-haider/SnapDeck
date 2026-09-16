"""Generate one short, data-grounded headline insight sentence.

Two modes:
  1. If OPENAI_API_KEY is set in the environment (and the `openai` package is
     installed), call an OpenAI-compatible chat completion with a
     tightly-scoped prompt that only ever sees the actual field values
     supplied — it's explicitly told never to invent numbers. The API key,
     base URL, and model name are all read from the environment (populated
     from backend/.env — see .env.example), so this also works against any
     OpenAI-compatible endpoint (Azure OpenAI, a local proxy, OpenRouter,
     etc.) by pointing OPENAI_BASE_URL at it.
  2. Otherwise, fall back to a deterministic, rule-based sentence built from
     whichever recognizable fields are present.

The fallback exists so the demo is 100% reliable with zero external
dependencies, zero API cost, and zero network requirement — a live demo
should never be at the mercy of a flaky API call.
"""

from __future__ import annotations

import os
from typing import Any


def _find(fields: dict[str, str], *candidate_keys: str) -> str | None:
    lowered = {k.lower(): v for k, v in fields.items()}
    for key in candidate_keys:
        if key in lowered and lowered[key]:
            return lowered[key]
    return None


def _fallback_insight(fields: dict[str, str], chart: list[dict[str, Any]]) -> str:
    revenue = _find(fields, "revenue")
    growth = _find(fields, "growth", "growth_rate")
    region = _find(fields, "top_region", "region")
    churn = _find(fields, "churn", "churn_rate")
    nps = _find(fields, "nps")

    lead_parts = []
    if revenue and growth:
        lead_parts.append(f"Revenue reached {revenue}, up {growth} versus the prior period")
    elif revenue:
        lead_parts.append(f"Revenue reached {revenue}")
    elif growth:
        lead_parts.append(f"Growth came in at {growth} versus the prior period")

    if region and lead_parts:
        lead_parts.append(f"led by {region}")
    elif region:
        lead_parts.append(f"{region} was the top-performing segment this period")

    lead = " ".join(lead_parts) if lead_parts else "This period's results are summarized above"

    tail_bits = []
    if churn:
        tail_bits.append(f"churn stands at {churn}")
    if nps:
        tail_bits.append(f"NPS is {nps}")
    if chart:
        top = max(chart, key=lambda point: point["value"])
        tail_bits.append(f"{top['label']} was the top contributor in the chart above")

    text = lead.strip().rstrip(".")
    if tail_bits:
        tail = "; ".join(tail_bits)
        text += f". {tail[0].upper() + tail[1:]}."
    else:
        text += "."
    return text


def _build_prompt(fields: dict[str, str], chart: list[dict[str, Any]]) -> str:
    data_lines = "\n".join(f"- {k}: {v}" for k, v in fields.items() if k != "ai_insight")
    chart_lines = "\n".join(f"- {point['label']}: {point['value']}" for point in chart)
    return (
        "You are writing ONE short headline insight for a business report slide "
        "(one or two sentences, max ~35 words total). Use ONLY the facts listed "
        "below. Never invent a number, name, or cause that isn't present in this "
        "data. Be specific and concrete, not generic filler.\n\n"
        f"Metrics:\n{data_lines or '(none provided)'}\n\n"
        f"Chart data:\n{chart_lines or '(none provided)'}\n\n"
        "Write the insight now. No preamble, no quotation marks, no markdown — "
        "just the sentence(s)."
    )


def generate_insight(fields: dict[str, str], chart: list[dict[str, Any]]) -> str:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        return _fallback_insight(fields, chart)

    try:
        from openai import OpenAI  # imported lazily so the package is fully optional
    except ImportError:
        return _fallback_insight(fields, chart)

    base_url = os.environ.get("OPENAI_BASE_URL", "").strip() or None
    model = os.environ.get("OPENAI_MODEL_NAME", "gpt-4o-mini").strip() or "gpt-4o-mini"

    try:
        client = OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            max_tokens=120,
            temperature=0.3,
            messages=[{"role": "user", "content": _build_prompt(fields, chart)}],
        )
        text = (response.choices[0].message.content or "").strip()
        return text or _fallback_insight(fields, chart)
    except Exception:
        # Any API/network/quota issue: never let insight generation break the demo.
        return _fallback_insight(fields, chart)
