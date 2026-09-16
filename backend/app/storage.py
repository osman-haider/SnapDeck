"""Very small in-memory + on-disk registry for generated output files.

This is intentionally not a database: SnapDeck is a stateless demo, and a
generated file only needs to live long enough for the user to click
Download in the same session. If the server restarts, generated files are
gone and can simply be regenerated (this is called out explicitly in the
project's "Do Not Build" list).
"""

from __future__ import annotations

import tempfile
import uuid
from pathlib import Path
from typing import TypedDict

# Written to the system temp dir (Vercel functions only allow writes under
# /tmp — the deployed source tree itself is read-only), not the repo.
GENERATED_DIR = Path(tempfile.gettempdir()) / "snapdeck-generated"
GENERATED_DIR.mkdir(parents=True, exist_ok=True)


class GeneratedFile(TypedDict):
    path: Path
    filename: str
    media_type: str


_registry: dict[str, GeneratedFile] = {}


def save_generated_file(content: bytes, filename: str, media_type: str) -> str:
    file_id = uuid.uuid4().hex
    path = GENERATED_DIR / f"{file_id}_{filename}"
    path.write_bytes(content)
    _registry[file_id] = {"path": path, "filename": filename, "media_type": media_type}
    return file_id


def get_generated_file(file_id: str) -> GeneratedFile | None:
    return _registry.get(file_id)
