"""Tests for backend/storage.py - persistent JSON file storage."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

from backend.models import (
    Article,
    Claim,
    Event,
    SourcePool,
    articles_store,
    claims_store,
    events_store,
)
from backend.storage import (
    STORAGE_DIR_ENV,
    _articles_path,
    _claims_path,
    _events_path,
    _load_json,
    _make_datetime,
    _serialise,
    _storage_dir,
    archive_stores,
    clear_persisted_data,
    restore_stores,
    storage_summary,
)


@pytest.fixture(autouse=True)
def _temp_storage_dir(monkeypatch):
    """Redirect the persistent storage directory to a temporary location
    so tests don't interfere with real data and are cleaned up automatically."""
    with tempfile.TemporaryDirectory() as tmp:
        monkeypatch.setenv(STORAGE_DIR_ENV, tmp)
        yield


@pytest.fixture(autouse=True)
def _clear_stores():
    """Clear the in-memory stores before and after each test."""
    articles_store.clear()
    claims_store.clear()
    events_store.clear()
    yield
    articles_store.clear()
    claims_store.clear()
    events_store.clear()


# ---------------------------------------------------------------------------
# _storage_dir
# ---------------------------------------------------------------------------

class TestStorageDir:
    def test_default_dir(self, monkeypatch):
        monkeypatch.delenv(STORAGE_DIR_ENV, raising=False)
        d = _storage_dir()
        # Compare by path parts so this passes on both POSIX and Windows.
        assert d.is_absolute()
        parts = d.parts
        assert ".killprop" in parts
        assert "data" in parts
        assert parts[-2:] == (".killprop", "data")
        assert d.is_absolute()

    def test_env_override(self):
        assert _storage_dir() == Path(os.environ[STORAGE_DIR_ENV])


# ---------------------------------------------------------------------------
# _serialise / _make_datetime helpers
# ---------------------------------------------------------------------------

class TestSerialise:
    def test_model_dump_delegation(self):
        article = Article(
            canonical_url="https://example.com",
            title="Test",
            source_name="Src",
            source_pool=SourcePool.WESTERN_MAINSTREAM,
            source_country="US",
            full_text="Some text.",
        )
        result = _serialise(article)
        assert result["title"] == "Test"
        assert result["source_pool"] == "western_mainstream"

    def test_set_to_sorted_list(self):
        assert _serialise({"b", "a", "c"}) == ["a", "b", "c"]


class TestMakeDatetime:
    def test_none_returns_none(self):
        assert _make_datetime(None) is None

    def test_datetime_passthrough(self):
        from datetime import datetime
        dt = datetime(2026, 6, 5, 3, 10)
        assert _make_datetime(dt) is dt

    def test_iso_string_parsed(self):
        from datetime import datetime
        result = _make_datetime("2026-06-05T03:10:00")
        assert isinstance(result, datetime)
        assert result.year == 2026


# ---------------------------------------------------------------------------
# archive / restore round-trip
# ---------------------------------------------------------------------------

class TestArchiveRestoreRoundTrip:
    def test_archive_persists_articles(self):
        a = Article(
            canonical_url="https://example.com",
            title="Test Article",
            source_name="Src",
            source_pool=SourcePool.WESTERN_MAINSTREAM,
            source_country="US",
            full_text="Full text content.",
        )
        articles_store[a.article_id] = a

        archive_stores()

        # Verify the JSON file was written
        path = _articles_path()
        assert path.exists()
        with open(path) as fh:
            data = json.load(fh)
        assert a.article_id in data
        assert data[a.article_id]["title"] == "Test Article"

    def test_archive_persists_claims(self):
        c = Claim(
            source_article_id="a1",
            source_pool=SourcePool.NEUTRAL_WIRE,
            source_name="Wire",
            claim_text_original="A strike occurred.",
        )
        claims_store[c.claim_id] = c
        archive_stores()

        path = _claims_path()
        assert path.exists()
        with open(path) as fh:
            data = json.load(fh)
        assert c.claim_id in data

    def test_archive_persists_events(self):
        e = Event(title="Test Event")
        events_store[e.event_id] = e
        archive_stores()

        path = _events_path()
        assert path.exists()
        with open(path) as fh:
            data = json.load(fh)
        assert e.event_id in data

    def test_restore_populates_articles(self):
        a = Article(
            canonical_url="https://example.com",
            title="Persisted Article",
            source_name="Src",
            source_pool=SourcePool.RUSSIAN_STATE,
            source_country="RU",
            full_text="Body.",
        )
        articles_store[a.article_id] = a
        archive_stores()
        articles_store.clear()

        restore_stores()

        assert a.article_id in articles_store
        restored = articles_store[a.article_id]
        assert restored.title == "Persisted Article"
        assert restored.source_pool == SourcePool.RUSSIAN_STATE

    def test_restore_populates_claims(self):
        c = Claim(
            source_article_id="a1",
            source_pool=SourcePool.RUSSIAN_INDEPENDENT,
            source_name="Gazette",
            claim_text_original="Claim text.",
        )
        claims_store[c.claim_id] = c
        archive_stores()
        claims_store.clear()

        restore_stores()

        restored = claims_store[c.claim_id]
        assert restored.claim_text_original == "Claim text."
        assert restored.source_pool == SourcePool.RUSSIAN_INDEPENDENT

    def test_restore_populates_events(self):
        e = Event(title="Persisted Event")
        e.fact_layer.summary = "A test event."
        events_store[e.event_id] = e
        archive_stores()
        events_store.clear()

        restore_stores()

        restored = events_store[e.event_id]
        assert restored.title == "Persisted Event"
        assert restored.fact_layer.summary == "A test event."

    def test_full_pipeline_round_trip(self):
        """Simulate a mini pipeline run and verify data survives restart."""
        from backend.pipeline.ingestion import ingest_articles
        from backend.pipeline.clustering import cluster_claims_into_events
        from backend.pipeline.consensus import resolve_all_events

        ingest_articles(seed=True)
        cluster_claims_into_events()
        resolve_all_events()
        archive_stores()

        # Simulate process restart
        articles_store.clear()
        claims_store.clear()
        events_store.clear()

        restore_stores()

        assert len(articles_store) > 0, "Articles not restored"
        assert len(claims_store) > 0, "Claims not restored"
        assert len(events_store) > 0, "Events not restored"

    def test_restore_on_already_populated_store_skips_duplicates(self):
        a = Article(
            canonical_url="https://example.com",
            title="Original",
            source_name="Src",
            source_pool=SourcePool.WESTERN_MAINSTREAM,
            source_country="US",
            full_text="Body.",
        )
        articles_store[a.article_id] = a
        original_count = len(articles_store)

        archive_stores()

        # Create a *different* article for the same key (should not replace)
        articles_store[a.article_id] = Article(
            canonical_url="https://example.com/updated",
            title="Updated",
            source_name="Src",
            source_pool=SourcePool.WESTERN_MAINSTREAM,
            source_country="US",
            full_text="Different.",
        )

        restore_stores()

        # Original should NOT be replaced (only missing keys are added)
        assert len(articles_store) == original_count
        assert articles_store[a.article_id].title == "Updated"


# ---------------------------------------------------------------------------
# _load_json edge cases
# ---------------------------------------------------------------------------

class TestLoadJson:
    def test_missing_file_returns_empty(self):
        assert _load_json(Path("/nonexistent/file.json")) == {}

    def test_corrupt_file_returns_empty(self):
        path = Path(os.environ[STORAGE_DIR_ENV]) / "corrupt.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{invalid json")
        assert _load_json(path) == {}


# ---------------------------------------------------------------------------
# clear_persisted_data
# ---------------------------------------------------------------------------

class TestClearPersistedData:
    def test_clears_all_files(self):
        articles_store["a1"] = Article(
            canonical_url="https://x.com",
            title="T",
            source_name="S",
            source_pool=SourcePool.WESTERN_MAINSTREAM,
            source_country="US",
            full_text="F",
        )
        archive_stores()

        assert _articles_path().exists()
        clear_persisted_data()
        assert not _articles_path().exists()
        assert not _claims_path().exists()
        assert not _events_path().exists()

    def test_clear_empty_dir_does_not_raise(self):
        clear_persisted_data()  # Should just be a no-op


# ---------------------------------------------------------------------------
# storage_summary
# ---------------------------------------------------------------------------

class TestStorageSummary:
    def test_empty_returns_zeroes(self):
        summary = storage_summary()
        assert summary["articles"] == 0
        assert summary["claims"] == 0
        assert summary["events"] == 0

    def test_with_data(self):
        articles_store["a1"] = Article(
            canonical_url="https://x.com",
            title="T",
            source_name="S",
            source_pool=SourcePool.WESTERN_MAINSTREAM,
            source_country="US",
            full_text="F",
        )
        archive_stores()
        summary = storage_summary()
        assert summary["articles"] == 1
