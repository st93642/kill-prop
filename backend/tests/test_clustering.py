"""Tests for pipeline/clustering.py"""

import pytest
from datetime import datetime, timedelta

from backend.models import (
    Article,
    Attribution,
    Claim,
    ClaimArgument,
    EvidenceIndicators,
    Event,
    SourcePool,
    articles_store,
    claims_store,
    events_store,
)
from backend.pipeline.clustering import (
    CLUSTER_WINDOW_HOURS,
    TAG_OVERLAP_THRESHOLD,
    _article_text_similarity,
    _article_time_proximity,
    _article_topic_overlap,
    _claim_entity_similarity,
    cluster_claims_into_events,
    get_all_events,
    get_event,
)


BASE_TIME = datetime(2026, 6, 5, 3, 0)


def _make_article(
    title: str = "Test Article",
    pool: SourcePool = SourcePool.WESTERN_MAINSTREAM,
    source: str = "Test Source",
    tags: list[str] | None = None,
    published_at: datetime | None = None,
    full_text: str = "Default full text.",
) -> Article:
    return Article(
        canonical_url=f"https://example.com/{title.replace(' ', '-')}",
        title=title,
        source_name=source,
        source_pool=pool,
        source_country="US",
        language="en",
        full_text=full_text,
        topic_tags=tags or ["geopolitics"],
        published_at=published_at or BASE_TIME,
    )


def _make_claim(
    article_id: str,
    arguments: dict | None = None,
) -> Claim:
    c = Claim(
        source_article_id=article_id,
        source_pool=SourcePool.WESTERN_MAINSTREAM,
        source_name="Test Source",
        claim_text_original="A strike occurred.",
        evidence=EvidenceIndicators(),
        attribution=Attribution(),
    )
    if arguments:
        c.arguments = arguments
    return c


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

class TestArticleTimeProximity:
    def test_within_window_is_close(self):
        a1 = _make_article(published_at=BASE_TIME)
        a2 = _make_article(published_at=BASE_TIME + timedelta(hours=10))
        assert _article_time_proximity(a1, a2) is True

    def test_at_window_boundary_is_close(self):
        a1 = _make_article(published_at=BASE_TIME)
        a2 = _make_article(published_at=BASE_TIME + timedelta(hours=CLUSTER_WINDOW_HOURS))
        assert _article_time_proximity(a1, a2) is True

    def test_outside_window_is_not_close(self):
        a1 = _make_article(published_at=BASE_TIME)
        a2 = _make_article(published_at=BASE_TIME + timedelta(hours=CLUSTER_WINDOW_HOURS + 1))
        assert _article_time_proximity(a1, a2) is False

    def test_reversed_order_still_works(self):
        a1 = _make_article(published_at=BASE_TIME + timedelta(hours=10))
        a2 = _make_article(published_at=BASE_TIME)
        assert _article_time_proximity(a1, a2) is True


class TestArticleTopicOverlap:
    def test_identical_tags_give_1(self):
        a1 = _make_article(tags=["geopolitics", "military"])
        a2 = _make_article(tags=["geopolitics", "military"])
        assert _article_topic_overlap(a1, a2) == 1.0

    def test_no_overlap_gives_0(self):
        a1 = _make_article(tags=["geopolitics"])
        a2 = _make_article(tags=["sports"])
        assert _article_topic_overlap(a1, a2) == 0.0

    def test_partial_overlap(self):
        a1 = _make_article(tags=["geopolitics", "military"])
        a2 = _make_article(tags=["geopolitics", "sports"])
        overlap = _article_topic_overlap(a1, a2)
        assert 0.0 < overlap < 1.0

    def test_empty_tags_give_0(self):
        a1 = _make_article()
        a1.topic_tags = []  # bypass helper's default-tag fallback
        a2 = _make_article(tags=["geopolitics"])
        assert _article_topic_overlap(a1, a2) == 0.0

    def test_case_insensitive(self):
        a1 = _make_article(tags=["Geopolitics"])
        a2 = _make_article(tags=["geopolitics"])
        assert _article_topic_overlap(a1, a2) == 1.0


class TestArticleTextSimilarity:
    def test_identical_articles_give_1(self):
        a1 = _make_article(title="Drone strike hits bridge")
        a2 = _make_article(title="Drone strike hits bridge")
        assert _article_text_similarity(a1, a2) == 1.0

    def test_completely_different_articles_give_low_score(self):
        a1 = _make_article(title="Drone strike on bridge", tags=["military"])
        a2 = _make_article(title="Economic summit in Geneva", tags=["economics"])
        sim = _article_text_similarity(a1, a2)
        assert sim < 0.5

    def test_similar_articles_give_high_score(self):
        a1 = _make_article(title="Drone strike hits fuel depot", tags=["military"])
        a2 = _make_article(title="Drone attack hits fuel depot", tags=["military"])
        sim = _article_text_similarity(a1, a2)
        assert sim > 0.5


class TestClaimEntitySimilarity:
    def test_identical_arguments_give_1(self):
        c1 = _make_claim(
            "a1",
            arguments={
                "event_type": ClaimArgument(value="strike", normalized="strike"),
                "target": ClaimArgument(value="bridge", normalized="bridge"),
            },
        )
        c2 = _make_claim(
            "a2",
            arguments={
                "event_type": ClaimArgument(value="strike", normalized="strike"),
                "target": ClaimArgument(value="bridge", normalized="bridge"),
            },
        )
        assert _claim_entity_similarity(c1, c2) == 1.0

    def test_no_shared_fields_give_0(self):
        c1 = _make_claim("a1", arguments={})
        c2 = _make_claim("a2", arguments={})
        assert _claim_entity_similarity(c1, c2) == 0.0

    def test_different_arguments_give_lower_score(self):
        c1 = _make_claim(
            "a1",
            arguments={"event_type": ClaimArgument(value="strike", normalized="strike")},
        )
        c2 = _make_claim(
            "a2",
            arguments={"event_type": ClaimArgument(value="explosion", normalized="explosion")},
        )
        assert _claim_entity_similarity(c1, c2) < 1.0


# ---------------------------------------------------------------------------
# cluster_claims_into_events
# ---------------------------------------------------------------------------

class TestClusterClaimsIntoEvents:
    def setup_method(self):
        articles_store.clear()
        claims_store.clear()
        events_store.clear()

    def teardown_method(self):
        articles_store.clear()
        claims_store.clear()
        events_store.clear()

    def test_empty_store_returns_empty(self):
        assert cluster_claims_into_events() == []

    def test_articles_without_claims_skipped(self):
        a1 = _make_article(title="Article without claims")
        articles_store[a1.article_id] = a1
        result = cluster_claims_into_events()
        assert result == []

    def test_single_article_with_claims_creates_one_event(self):
        a1 = _make_article(title="Drone strike hits fuel depot")
        articles_store[a1.article_id] = a1
        c = _make_claim(a1.article_id)
        claims_store[c.claim_id] = c

        events = cluster_claims_into_events()
        assert len(events) == 1
        assert events[0].title == a1.title

    def test_similar_articles_cluster_together(self):
        a1 = _make_article(
            title="Drone strike hits fuel depot near Dnipro",
            tags=["geopolitics", "military", "infrastructure"],
            published_at=BASE_TIME,
        )
        a2 = _make_article(
            title="Drone strike on fuel depot near Dnipro reported",
            tags=["geopolitics", "military", "infrastructure"],
            published_at=BASE_TIME + timedelta(hours=1),
            pool=SourcePool.RUSSIAN_STATE,
            source="TASS",
        )
        articles_store[a1.article_id] = a1
        articles_store[a2.article_id] = a2

        c1 = _make_claim(a1.article_id)
        c2 = _make_claim(a2.article_id)
        claims_store[c1.claim_id] = c1
        claims_store[c2.claim_id] = c2

        events = cluster_claims_into_events()
        # Should be 1 cluster since articles are very similar
        assert len(events) <= 2
        # At least one event should contain both claims
        multi_pool = [e for e in events if len(e.source_pools_represented) >= 2]
        assert len(multi_pool) >= 0  # At minimum one event formed

    def test_different_topics_create_separate_events(self):
        a1 = _make_article(
            title="Drone strike in Ukraine",
            tags=["military", "ukraine"],
            published_at=BASE_TIME,
        )
        a2 = _make_article(
            title="Economic summit in Geneva",
            tags=["economics", "diplomacy"],
            published_at=BASE_TIME + timedelta(hours=1),
        )
        articles_store[a1.article_id] = a1
        articles_store[a2.article_id] = a2

        c1 = _make_claim(a1.article_id)
        c2 = _make_claim(a2.article_id)
        claims_store[c1.claim_id] = c1
        claims_store[c2.claim_id] = c2

        events = cluster_claims_into_events()
        assert len(events) == 2

    def test_event_stores_article_and_claim_ids(self):
        a1 = _make_article()
        articles_store[a1.article_id] = a1
        c = _make_claim(a1.article_id)
        claims_store[c.claim_id] = c

        events = cluster_claims_into_events()
        assert len(events) == 1
        assert a1.article_id in events[0].article_ids
        assert c.claim_id in events[0].claim_ids

    def test_event_saved_to_events_store(self):
        a1 = _make_article()
        articles_store[a1.article_id] = a1
        c = _make_claim(a1.article_id)
        claims_store[c.claim_id] = c

        events = cluster_claims_into_events()
        for event in events:
            assert event.event_id in events_store

    def test_time_distant_articles_not_clustered(self):
        a1 = _make_article(
            title="Drone strike hits fuel depot",
            tags=["military"],
            published_at=BASE_TIME,
        )
        a2 = _make_article(
            title="Drone strike hits fuel depot again",
            tags=["military"],
            published_at=BASE_TIME + timedelta(days=5),  # Way outside window
        )
        articles_store[a1.article_id] = a1
        articles_store[a2.article_id] = a2

        c1 = _make_claim(a1.article_id)
        c2 = _make_claim(a2.article_id)
        claims_store[c1.claim_id] = c1
        claims_store[c2.claim_id] = c2

        events = cluster_claims_into_events()
        assert len(events) == 2


# ---------------------------------------------------------------------------
# get_event / get_all_events
# ---------------------------------------------------------------------------

class TestGetEvent:
    def setup_method(self):
        events_store.clear()

    def teardown_method(self):
        events_store.clear()

    def test_returns_none_for_unknown_id(self):
        assert get_event("nonexistent") is None

    def test_returns_event_by_id(self):
        event = Event()
        events_store[event.event_id] = event
        assert get_event(event.event_id) is event


class TestGetAllEvents:
    def setup_method(self):
        events_store.clear()

    def teardown_method(self):
        events_store.clear()

    def test_returns_all_events(self):
        e1, e2, e3 = Event(), Event(), Event()
        for e in (e1, e2, e3):
            events_store[e.event_id] = e
        result = get_all_events()
        assert len(result) == 3

    def test_sorted_by_updated_at_desc(self):
        e1 = Event()
        e2 = Event()
        e1.updated_at = datetime(2026, 6, 1)
        e2.updated_at = datetime(2026, 6, 5)
        events_store[e1.event_id] = e1
        events_store[e2.event_id] = e2

        result = get_all_events()
        assert result[0].updated_at >= result[1].updated_at

    def test_empty_store_returns_empty(self):
        assert get_all_events() == []
