"""API routes for the internal review console (human-in-the-loop)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.models import (
    Claim,
    ClaimBucket,
    ConfidenceClass,
    Event,
    EventContradictionState,
    FieldResolutionStatus,
    SourcePool,
    events_store,
)
from backend.storage import archive_stores

router = APIRouter(prefix="/api/review", tags=["review"])


@router.get("/events")
async def review_events(status: str | None = None):
    """List all events for human review, optionally filtered by status."""
    events = list(events_store.values())
    events.sort(key=lambda e: e.updated_at, reverse=True)

    if status:
        events = [e for e in events if e.contradiction_state.value == status]

    return [
        {
            "event_id": e.event_id,
            "title": e.title,
            "contradiction_state": e.contradiction_state.value,
            "overall_confidence": e.overall_confidence.value,
            "human_reviewed": e.human_reviewed,
            "fact_summary": e.fact_layer.summary,
            "dispute_count": len(e.dispute_layer.fields),
            "updated_at": e.updated_at,
        }
        for e in events
    ]


@router.post("/{event_id}/override")
async def override_field(
    event_id: str,
    field: str,
    override_value: str,
    reason: str = "",
):
    """Human override of a specific field resolution for an event."""
    event = events_store.get(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Apply override to fact layer
    event.fact_layer.fields[field] = override_value
    event.human_overrides[field] = {
        "overridden_value": override_value,
        "reason": reason,
    }
    event.human_reviewed = True

    # Rebuild summary with overridden field
    summary_parts = []
    for fname, fval in event.fact_layer.fields.items():
        summary_parts.append(f"{fname.replace('_', ' ')}: {fval.replace('_', ' ')}")
    event.fact_layer.summary = "; ".join(summary_parts)

    archive_stores()

    return {
        "message": f"Field '{field}' overridden to '{override_value}'",
        "event_id": event.event_id,
    }


@router.post("/{event_id}/approve")
async def approve_event(event_id: str):
    """Mark an event as reviewed and approved without changes."""
    event = events_store.get(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    event.human_reviewed = True
    archive_stores()
    return {"message": "Event approved", "event_id": event.event_id}


@router.post("/{event_id}/recluster")
async def trigger_recluster(event_id: str):
    """Flag an event for reclustering."""
    event = events_store.get(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    # In MVP, just mark it
    event.human_review_notes = (event.human_review_notes or "") + "\n[FLAGGED FOR RECLUSTER]"
    archive_stores()
    return {"message": "Event flagged for reclustering", "event_id": event.event_id}


@router.get("/dashboard")
async def review_dashboard():
    """Get review dashboard stats."""
    events = list(events_store.values())
    total = len(events)
    reviewed = sum(1 for e in events if e.human_reviewed)
    with_disputes = sum(1 for e in events if e.dispute_layer.fields)
    unconfirmed = sum(
        1 for e in events
        if e.overall_confidence in (ConfidenceClass.DISPUTED, ConfidenceClass.UNKNOWN)
    )

    return {
        "total_events": total,
        "reviewed": reviewed,
        "pending_review": total - reviewed,
        "with_disputes": with_disputes,
        "unconfirmed": unconfirmed,
        "review_completion": round(reviewed / total * 100, 1) if total > 0 else 0,
    }