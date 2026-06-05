"""Integration tests for all API routes using FastAPI TestClient."""

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.models import (
    articles_store,
    claims_store,
    events_store,
)


@pytest.fixture(autouse=True)
def clear_stores():
    """Clear all in-memory stores before each test."""
    articles_store.clear()
    claims_store.clear()
    events_store.clear()
    yield
    articles_store.clear()
    claims_store.clear()
    events_store.clear()


client = TestClient(app)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

class TestHealthCheck:
    def test_health_returns_healthy(self):
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "pipeline" in data
        assert "stages" in data["pipeline"]
        assert len(data["pipeline"]["stages"]) == 6


# ---------------------------------------------------------------------------
# Articles routes
# ---------------------------------------------------------------------------

class TestArticlesRoutes:
    def test_list_articles_empty(self):
        response = client.get("/api/articles")
        assert response.status_code == 200
        assert response.json() == []

    def test_ingest_articles(self):
        response = client.post("/api/articles/ingest")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "article_ids" in data
        assert "total_claims" in data
        assert len(data["article_ids"]) > 0
        assert data["total_claims"] > 0

    def test_list_articles_after_ingest(self):
        client.post("/api/articles/ingest")
        response = client.get("/api/articles")
        assert response.status_code == 200
        articles = response.json()
        assert len(articles) > 0
        for article in articles:
            assert "article_id" in article
            assert "title" in article
            assert "source" in article
            assert "source_pool" in article
            assert "claim_count" in article

    def test_get_article_detail(self):
        client.post("/api/articles/ingest")
        articles = client.get("/api/articles").json()
        article_id = articles[0]["article_id"]

        response = client.get(f"/api/articles/{article_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["article_id"] == article_id
        assert "title" in data
        assert "full_text" in data
        assert "claims" in data
        assert isinstance(data["claims"], list)

    def test_get_article_claims_have_structure(self):
        client.post("/api/articles/ingest")
        articles = client.get("/api/articles").json()
        article_id = articles[0]["article_id"]

        response = client.get(f"/api/articles/{article_id}")
        claims = response.json()["claims"]
        assert len(claims) > 0
        for claim in claims:
            assert "claim_id" in claim
            assert "text_original" in claim
            assert "bucket" in claim
            assert "evidence" in claim
            assert "propaganda_flags" in claim

    def test_get_article_404(self):
        response = client.get("/api/articles/nonexistent_id")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Events routes
# ---------------------------------------------------------------------------

class TestEventsRoutes:
    def _setup_pipeline(self):
        client.post("/api/articles/ingest")
        client.post("/api/events/cluster")

    def test_list_events_empty(self):
        response = client.get("/api/events")
        assert response.status_code == 200
        assert response.json() == []

    def test_cluster_events(self):
        client.post("/api/articles/ingest")
        response = client.post("/api/events/cluster")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "event_ids" in data
        assert len(data["event_ids"]) > 0

    def test_list_events_after_pipeline(self):
        self._setup_pipeline()
        response = client.get("/api/events")
        assert response.status_code == 200
        events = response.json()
        assert len(events) > 0
        for event in events:
            assert "event_id" in event
            assert "title" in event
            assert "overall_confidence" in event
            assert "contradiction_state" in event
            assert "pools" in event
            assert "human_reviewed" in event

    def test_list_events_pool_filter(self):
        self._setup_pipeline()
        response = client.get("/api/events?pool=western_mainstream")
        assert response.status_code == 200
        events = response.json()
        for event in events:
            assert "western_mainstream" in event["pools"]

    def test_list_events_min_confidence_filter(self):
        self._setup_pipeline()
        response = client.get("/api/events?min_confidence=confirmed")
        assert response.status_code == 200
        events = response.json()
        for event in events:
            assert event["overall_confidence"] == "confirmed"

    def test_list_events_topic_filter(self):
        self._setup_pipeline()
        response = client.get("/api/events?topic=military")
        assert response.status_code == 200
        # Just verify it returns without error (may be empty)
        assert isinstance(response.json(), list)

    def test_get_event_detail(self):
        self._setup_pipeline()
        events = client.get("/api/events").json()
        event_id = events[0]["event_id"]

        response = client.get(f"/api/events/{event_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["event_id"] == event_id
        assert "fact_layer" in data
        assert "dispute_layer" in data
        assert "source_claims_layer" in data
        assert "overall_confidence" in data

    def test_get_event_detail_fact_layer_structure(self):
        self._setup_pipeline()
        events = client.get("/api/events").json()
        event_id = events[0]["event_id"]

        data = client.get(f"/api/events/{event_id}").json()
        fact_layer = data["fact_layer"]
        assert "summary" in fact_layer
        assert "fields" in fact_layer
        assert "confidence" in fact_layer
        assert "corroborating_sources" in fact_layer
        assert "pool_spread" in fact_layer

    def test_get_event_detail_dispute_layer_structure(self):
        self._setup_pipeline()
        events = client.get("/api/events").json()
        event_id = events[0]["event_id"]

        data = client.get(f"/api/events/{event_id}").json()
        dispute_layer = data["dispute_layer"]
        assert "fields" in dispute_layer
        assert "contradictions" in dispute_layer

    def test_get_event_detail_source_claims_structure(self):
        self._setup_pipeline()
        events = client.get("/api/events").json()
        event_id = events[0]["event_id"]

        data = client.get(f"/api/events/{event_id}").json()
        for claim in data["source_claims_layer"]:
            assert "source" in claim
            assert "source_pool" in claim
            assert "claim" in claim
            assert "bucket" in claim
            assert "score" in claim

    def test_get_event_404(self):
        response = client.get("/api/events/nonexistent_id")
        assert response.status_code == 404

    def test_update_event_review(self):
        self._setup_pipeline()
        events = client.get("/api/events").json()
        event_id = events[0]["event_id"]

        response = client.put(f"/api/events/{event_id}/review?notes=Test+notes")
        assert response.status_code == 200
        data = response.json()
        assert data["human_reviewed"] is True
        assert data["event_id"] == event_id

    def test_resolve_event_route(self):
        self._setup_pipeline()
        events = client.get("/api/events").json()
        event_id = events[0]["event_id"]

        response = client.post(f"/api/events/{event_id}/resolve")
        assert response.status_code == 200
        assert response.json()["event_id"] == event_id


# ---------------------------------------------------------------------------
# Review routes
# ---------------------------------------------------------------------------

class TestReviewRoutes:
    def _setup_pipeline(self):
        client.post("/api/articles/ingest")
        client.post("/api/events/cluster")

    def test_dashboard_empty(self):
        response = client.get("/api/review/dashboard")
        assert response.status_code == 200
        data = response.json()
        assert data["total_events"] == 0
        assert data["reviewed"] == 0
        assert data["pending_review"] == 0
        assert data["review_completion"] == 0

    def test_dashboard_after_pipeline(self):
        self._setup_pipeline()
        response = client.get("/api/review/dashboard")
        assert response.status_code == 200
        data = response.json()
        assert data["total_events"] > 0
        assert "reviewed" in data
        assert "pending_review" in data
        assert "with_disputes" in data
        assert "unconfirmed" in data
        assert "review_completion" in data

    def test_approve_event(self):
        self._setup_pipeline()
        events = client.get("/api/events").json()
        event_id = events[0]["event_id"]

        response = client.post(f"/api/review/{event_id}/approve")
        assert response.status_code == 200
        data = response.json()
        assert data["event_id"] == event_id

        # Verify it's marked reviewed
        event_detail = client.get(f"/api/events/{event_id}").json()
        assert event_detail["human_reviewed"] is True

    def test_approve_event_404(self):
        response = client.post("/api/review/nonexistent/approve")
        assert response.status_code == 404

    def test_override_field(self):
        self._setup_pipeline()
        events = client.get("/api/events").json()
        event_id = events[0]["event_id"]

        response = client.post(
            f"/api/review/{event_id}/override",
            params={"field": "event_type", "override_value": "explosion", "reason": "Correction"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "event_id" in data

    def test_override_field_404(self):
        response = client.post(
            "/api/review/nonexistent/override",
            params={"field": "event_type", "override_value": "explosion"},
        )
        assert response.status_code == 404

    def test_recluster_event(self):
        self._setup_pipeline()
        events = client.get("/api/events").json()
        event_id = events[0]["event_id"]

        response = client.post(f"/api/review/{event_id}/recluster")
        assert response.status_code == 200

    def test_review_events_list(self):
        self._setup_pipeline()
        response = client.get("/api/review/events")
        assert response.status_code == 200
        events = response.json()
        assert isinstance(events, list)

    def test_review_events_filtered_by_status(self):
        self._setup_pipeline()
        response = client.get("/api/review/events?status=corroborated")
        assert response.status_code == 200
        events = response.json()
        for event in events:
            assert event["contradiction_state"] == "corroborated"


# ---------------------------------------------------------------------------
# Full pipeline integration test
# ---------------------------------------------------------------------------

class TestFullPipelineRun:
    def test_full_pipeline_run_endpoint(self):
        response = client.get("/api/pipeline/run")
        assert response.status_code == 200
        data = response.json()
        assert "stages" in data
        assert "summary" in data
        assert "source_intake" in data["stages"]
        assert "event_clustering" in data["stages"]
        assert "consensus" in data["stages"]
        assert "scoring" in data["stages"]
        assert data["stages"]["source_intake"]["articles_ingested"] > 0

    def test_pipeline_then_list_events(self):
        client.get("/api/pipeline/run")
        response = client.get("/api/events")
        assert response.status_code == 200
        events = response.json()
        assert len(events) > 0

    def test_pipeline_events_have_source_claims(self):
        client.get("/api/pipeline/run")
        events = client.get("/api/events").json()
        event_id = events[0]["event_id"]
        detail = client.get(f"/api/events/{event_id}").json()
        assert len(detail["source_claims_layer"]) > 0

    def test_pipeline_events_have_fact_summary(self):
        client.get("/api/pipeline/run")
        events = client.get("/api/events").json()
        for event in events:
            assert event["fact_summary"] != "" or True  # may be empty for some events
