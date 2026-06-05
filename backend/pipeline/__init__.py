"""kill-prop pipeline stages.

Exposes the main pipeline functions for easy import:

    from backend.pipeline import ingest_articles, cluster_claims_into_events
"""

from backend.pipeline.ingestion import fetch_article, ingest_articles
from backend.pipeline.clustering import cluster_claims_into_events, get_all_events, get_event
from backend.pipeline.consensus import resolve_all_events, resolve_event
from backend.pipeline.scoring import score_claim, score_event_claims

__all__ = [
    "ingest_articles",
    "fetch_article",
    "cluster_claims_into_events",
    "get_all_events",
    "get_event",
    "resolve_all_events",
    "resolve_event",
    "score_claim",
    "score_event_claims",
]
