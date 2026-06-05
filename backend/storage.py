"""Persistent JSON-file storage for the kill-prop pipeline.

Replaces the in-memory dict stores with file-backed persistent storage
so that ingested articles, extracted claims, and clustered events survive
process restarts.  This serves as the "archive of online fetches" for the
MVP – production deployments should swap this out for PostgreSQL.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from backend.models import (
    Article,
    Claim,
    Event,
    articles_store,
    claims_store,
    events_store,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

STORAGE_DIR_ENV = "KILLPROP_STORAGE_DIR"
_DEFAULT_DIR = Path.home() / ".killprop" / "data"


def _storage_dir() -> Path:
    """Return the configured storage directory path."""
    override = os.environ.get(STORAGE_DIR_ENV)
    if override:
        return Path(override)
    return _DEFAULT_DIR


# ---------------------------------------------------------------------------
# Serialisation helpers – Pydantic v2 uses .model_dump()
# ---------------------------------------------------------------------------

def _serialise(obj: Any) -> Any:
    """Recursively convert a Pydantic model (or collection thereof) to a
    JSON-safe dict, handling datetime and Enum fields."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, set):
        return sorted(obj)
    return obj


def _make_datetime(val: str | datetime | None) -> datetime | None:
    """Rebuild a datetime from its ISO string representation."""
    if val is None or isinstance(val, datetime):
        return val
    return datetime.fromisoformat(val)


# ---------------------------------------------------------------------------
# File-level helpers
# ---------------------------------------------------------------------------

def _dump_json(path: Path, records: dict[str, Any]) -> None:
    """Atomically write *records* to *path* as pretty-printed JSON."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(records, fh, indent=2, default=_serialise, ensure_ascii=False)
        tmp.replace(path)
    except (OSError, IOError) as e:
        import logging
        logging.getLogger(__name__).warning(f"Failed to persist data to {path}: {e}")


def _load_json(path: Path) -> dict[str, Any]:
    """Load a JSON file, returning an empty dict if the file doesn't exist
    or is corrupt."""
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (json.JSONDecodeError, OSError):
        return {}


# ---------------------------------------------------------------------------
# Store file paths
# ---------------------------------------------------------------------------

def _articles_path() -> Path:
    return _storage_dir() / "articles.json"


def _claims_path() -> Path:
    return _storage_dir() / "claims.json"


def _events_path() -> Path:
    return _storage_dir() / "events.json"


# ---------------------------------------------------------------------------
# Public API – archive / restore
# ---------------------------------------------------------------------------

def archive_stores() -> None:
    """Persist the current in-memory stores to disk."""
    _dump_json(_articles_path(), {k: v.model_dump(mode="json") for k, v in articles_store.items()})
    _dump_json(_claims_path(), {k: v.model_dump(mode="json") for k, v in claims_store.items()})
    _dump_json(_events_path(), {k: v.model_dump(mode="json") for k, v in events_store.items()})


def restore_stores() -> None:
    """Load persisted data from disk into the in-memory stores.

    This is called at startup so that data survives restarts.
    """
    articles_dict = _load_json(_articles_path())
    claims_dict = _load_json(_claims_path())
    events_dict = _load_json(_events_path())

    for key, val in articles_dict.items():
        if key not in articles_store:
            articles_store[key] = Article.model_validate(val)

    for key, val in claims_dict.items():
        if key not in claims_store:
            claims_store[key] = Claim.model_validate(val)

    for key, val in events_dict.items():
        if key not in events_store:
            events_store[key] = Event.model_validate(val)


def clear_persisted_data() -> None:
    """Remove all persisted JSON files (useful in tests and for reset)."""
    for p in (_articles_path(), _claims_path(), _events_path()):
        if p.exists():
            p.unlink()


def storage_summary() -> dict[str, int]:
    """Return a summary of what is currently persisted on disk."""
    return {
        "articles": len(_load_json(_articles_path())),
        "claims": len(_load_json(_claims_path())),
        "events": len(_load_json(_events_path())),
        "storage_dir": str(_storage_dir()),
    }
