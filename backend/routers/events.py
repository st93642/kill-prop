"""API routes for events - the main presentation layer."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.models import (
    ConfidenceClass,
    Event,
    EventContradictionState,
    events_store,
)
from backend.pipeline.clustering import cluster_claims_into_events, get_all_events, get_event
from backend.pipeline.consensus import resolve_all_events, resolve_event
from backend.pipeline.scoring import score_event_claims
from backend.storage import archive_stores

router = APIRouter(prefix="/api/events", tags=["events"])


@router.post("/cluster")
async def cluster():
    """Cluster claims into events and run consensus."""
    events = cluster_claims_into_events()
    resolved = resolve_all_events()
    archive_stores()
    return {
        "message": f"Clustered into {len(events)} events",
        "event_ids": [e.event_id for e in resolved],
    }


@router.get("")
async def list_events(
    pool: str | None = None,
    min_confidence: str | None = None,
    topic: str | None = None,
):
    """List all events with optional filtering.
    
    Args:
        pool: Filter by source pool (e.g., "western_mainstream")
        min_confidence: Minimum confidence level (e.g., "probable")
        topic: Filter by topic tag
    """
    events = get_all_events()

    if pool:
        events = [
            e for e in events
            if any(p.value == pool for p in e.source_pools_represented)
        ]

    if min_confidence:
        confidence_order = {
            "confirmed": 5, "probable": 4, "single_source": 3,
            "disputed": 2, "unknown": 1,
        }
        min_level = confidence_order.get(min_confidence, 0)
        events = [
            e for e in events
            if confidence_order.get(e.overall_confidence.value, 0) >= min_level
        ]

    if topic:
        events = [e for e in events if topic.lower() in e.topic.lower()]

    return [
        {
            "event_id": e.event_id,
            "title": e.title,
            "topic": e.topic,
            "fact_summary": e.fact_layer.summary,
            "overall_confidence": e.overall_confidence.value,
            "contradiction_state": e.contradiction_state.value,
            "corroborating_sources": e.fact_layer.corroborating_sources,
            "pool_spread": e.fact_layer.pool_spread,
            "pool_count": len(e.source_pools_represented),
            "pools": [p.value for p in e.source_pools_represented],
            "dispute_count": len(e.dispute_layer.fields),
            "contradiction_count": len(e.dispute_layer.contradictions),
            "source_claim_count": len(e.source_claims_layer),
            "updated_at": e.updated_at,
            "human_reviewed": e.human_reviewed,
        }
        for e in events
    ]


@router.get("/{event_id}")
async def get_event_detail(event_id: str):
    """Get full event detail with all three layers and claim scores."""
    event = get_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Ensure consensus is applied
    event = resolve_event(event)
    claim_scores = score_event_claims(event)

    return {
        "event_id": event.event_id,
        "title": event.title,
        "topic": event.topic,
        "created_at": event.created_at,
        "updated_at": event.updated_at,
        "overall_confidence": event.overall_confidence.value,
        "contradiction_state": event.contradiction_state.value,
        "human_reviewed": event.human_reviewed,
        "source_pools": [p.value for p in event.source_pools_represented],
        "fact_layer": {
            "summary": event.fact_layer.summary,
            "fields": event.fact_layer.fields,
            "confidence": event.fact_layer.confidence.value,
            "corroborating_sources": event.fact_layer.corroborating_sources,
            "pool_spread": event.fact_layer.pool_spread,
        },
        "dispute_layer": {
            "fields": {
                field_name: {
                    "status": res.status.value,
                    "value": res.value,
                    "disputed_values": res.disputed_values,
                    "top_support": {
                        "value": res.top_support.value,
                        "score": round(res.top_support.score, 3),
                        "pool_count": res.top_support.pool_count,
                        "source_names": res.top_support.source_names,
                    } if res.top_support else None,
                }
                for field_name, res in event.dispute_layer.fields.items()
            },
            "contradictions": [
                {
                    "type": c.contradiction_type.value,
                    "outcome": c.outcome.value if c.outcome else None,
                    "field": c.field_name,
                    "description": c.description,
                    "state": c.state.value,
                }
                for c in event.dispute_layer.contradictions
            ],
        },
        "source_claims_layer": [
            {
                "source": s.source,
                "source_pool": s.source_pool.value,
                "claim": s.claim,
                "attribution": s.attribution,
                "bucket": s.bucket.value,
                "score": round(claim_scores.get(s.claim_id, 0.0), 3),
            }
            for s in event.source_claims_layer
        ],
    }


@router.post("/{event_id}/resolve")
async def resolve_event_route(event_id: str):
    """Manually trigger re-resolution of an event's fields."""
    event = get_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    event = resolve_event(event)
    return {"message": "Event resolved", "event_id": event.event_id}


@router.put("/{event_id}/review")
async def update_review(
    event_id: str,
    notes: str | None = None,
    overrides: dict | None = None,
):
    """Human-in-the-loop review: add notes and overrides."""
    event = get_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    if notes is not None:
        event.human_review_notes = notes
    if overrides is not None:
        event.human_overrides.update(overrides)
    event.human_reviewed = True
    return {
        "message": "Review saved",
        "event_id": event.event_id,
        "human_reviewed": event.human_reviewed,
        "notes": event.human_review_notes,
    }