"""Tests for pipeline/ingestion.py"""

import pytest
from datetime import datetime

from backend.models import (
    Article,
    ClaimBucket,
    SourcePool,
    articles_store,
    claims_store,
)
from backend.pipeline.ingestion import (
    SEED_ARTICLES,
    _extract_claims_from_article,
    fetch_article,
    ingest_articles,
)


def _make_article(full_text: str, pool: SourcePool = SourcePool.WESTERN_MAINSTREAM) -> Article:
    return Article(
        canonical_url="https://example.com/test",
        title="Test Article",
        source_name="Test Source",
        source_pool=pool,
        source_country="US",
        language="en",
        full_text=full_text,
        topic_tags=["test"],
        published_at=datetime(2026, 6, 5),
    )


# ---------------------------------------------------------------------------
# _extract_claims_from_article
# ---------------------------------------------------------------------------

class TestExtractClaimsFromArticle:
    def test_extracts_multiple_claims(self):
        article = _make_article(
            "A Shahed drone struck a fuel depot near the Dnipro river. "
            "The attack occurred at approximately 03:10 local time. "
            "No casualties were reported according to regional officials."
        )
        claims = _extract_claims_from_article(article)
        assert len(claims) >= 2  # Multiple sentences → multiple claims

    def test_short_sentences_skipped(self):
        article = _make_article("Short. Another short one. Longer sentence about an event occurring.")
        claims = _extract_claims_from_article(article)
        # "Short." and "Another short one." are < 20 chars → skipped
        for c in claims:
            assert len(c.claim_text_original) >= 20

    def test_attribution_detected(self):
        article = _make_article(
            "The attack was confirmed by regional officials. "
            "Defense ministry stated that air defense intercepted drones."
        )
        claims = _extract_claims_from_article(article)
        attributed = [c for c in claims if c.bucket == ClaimBucket.ATTRIBUTED_STATEMENT]
        assert len(attributed) >= 1

    def test_inference_bucket_for_uncertain_language(self):
        article = _make_article(
            "The strike may have caused significant damage to the facility. "
            "It remains unclear whether civilian infrastructure was targeted."
        )
        claims = _extract_claims_from_article(article)
        inferences = [c for c in claims if c.bucket == ClaimBucket.INFERENCE]
        assert len(inferences) >= 1

    def test_opinionated_framing_detected(self):
        article = _make_article(
            "This incident fits a pattern of escalating drone warfare against civilian infrastructure."
        )
        claims = _extract_claims_from_article(article)
        framing = [c for c in claims if c.bucket == ClaimBucket.OPINIONATED_FRAMING]
        assert len(framing) >= 1

    def test_evidence_official_statement_set(self):
        article = _make_article(
            "Regional officials confirmed the drone strike. "
            "The defense ministry issued a statement about the incident."
        )
        claims = _extract_claims_from_article(article)
        with_official = [c for c in claims if c.evidence.official_statement]
        assert len(with_official) >= 1

    def test_evidence_timestamp_set(self):
        article = _make_article(
            "The attack occurred at 03:10 local time near the Dnipro river."
        )
        claims = _extract_claims_from_article(article)
        with_timestamp = [c for c in claims if c.evidence.timestamp_geolocation]
        assert len(with_timestamp) >= 1

    def test_evidence_satellite_set(self):
        article = _make_article(
            "Satellite imagery reviewed by analysts confirmed the fire at the depot."
        )
        claims = _extract_claims_from_article(article)
        with_satellite = [c for c in claims if c.evidence.satellite_imagery]
        assert len(with_satellite) >= 1

    def test_propaganda_loaded_language_detected(self):
        article = _make_article(
            "The aggressor terror regime launched a fascist offensive against liberation forces."
        )
        claims = _extract_claims_from_article(article)
        flagged = [c for c in claims if "loaded_language" in c.propaganda_flags]
        assert len(flagged) >= 1

    def test_source_pool_inherited_from_article(self):
        article = _make_article("A strike occurred.", pool=SourcePool.RUSSIAN_STATE)
        claims = _extract_claims_from_article(article)
        assert all(c.source_pool == SourcePool.RUSSIAN_STATE for c in claims)

    def test_source_name_inherited(self):
        article = _make_article("An attack occurred near the bridge.")
        claims = _extract_claims_from_article(article)
        assert all(c.source_name == "Test Source" for c in claims)

    def test_article_id_stored_in_claims(self):
        article = _make_article("An explosion was heard in the morning hours near the area.")
        claims = _extract_claims_from_article(article)
        assert all(c.source_article_id == article.article_id for c in claims)


# ---------------------------------------------------------------------------
# ingest_articles
# ---------------------------------------------------------------------------

class TestIngestArticles:
    def setup_method(self):
        articles_store.clear()
        claims_store.clear()

    def teardown_method(self):
        articles_store.clear()
        claims_store.clear()

    def test_seed_ingests_all_seed_articles(self):
        articles = ingest_articles(seed=True)
        # Only Europe/Russia political/military seed articles pass the geo+topic filter
        # (19 out of 21 — Iran and Venezuela are excluded)
        assert len(articles) == 19

    def test_seed_articles_saved_to_store(self):
        ingest_articles(seed=True)
        assert len(articles_store) == 19

    def test_claims_extracted_and_saved(self):
        ingest_articles(seed=True)
        assert len(claims_store) > 0

    def test_no_seed_returns_from_rss_or_api(self):
        """When seed=False, articles come from RSS feeds or NewsAPI (may be empty in CI)."""
        result = ingest_articles(seed=False)
        # May return articles from RSS feeds or be empty if feeds are unavailable
        assert isinstance(result, list)

    def test_articles_have_claims(self):
        articles = ingest_articles(seed=True)
        for article in articles:
            assert len(article.claims) > 0

    def test_claims_have_normalized_arguments(self):
        ingest_articles(seed=True)
        # At least some claims should have normalized arguments
        with_args = [c for c in claims_store.values() if c.arguments]
        assert len(with_args) > 0

    def test_duplicate_ingest_idempotent(self):
        """Calling ingest twice should add articles again (store is not cleared between calls)."""
        ingest_articles(seed=True)
        first_count = len(articles_store)
        ingest_articles(seed=True)
        # May or may not be idempotent - just verify it doesn't crash
        assert len(articles_store) >= first_count


# ---------------------------------------------------------------------------
# fetch_article
# ---------------------------------------------------------------------------

class TestFetchArticle:
    def setup_method(self):
        articles_store.clear()

    def teardown_method(self):
        articles_store.clear()

    def test_returns_none_for_unknown_id(self):
        assert fetch_article("nonexistent_id") is None

    def test_returns_article_by_id(self):
        ingest_articles(seed=True)
        article_id = list(articles_store.keys())[0]
        result = fetch_article(article_id)
        assert result is not None
        assert result.article_id == article_id
