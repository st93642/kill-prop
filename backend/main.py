"""kill-prop: Source-triangulation news analysis web app.

FastAPI backend with the full 6-stage pipeline:
1. Source Intake
2. Article Normalization
3. Event Clustering
4. Claim Extraction
5. Evidence Scoring
6. User Presentation
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.routers import articles, events, review

app = FastAPI(
    title="kill-prop - Source Triangulation News Analyzer",
    description="Compares reporting across Western and Russian-source pools, "
                "identifies overlapping verified facts, flags unsupported or "
                "emotionally loaded claims, and exposes where framing diverges.",
    version="0.1.0",
)

# CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routers
app.include_router(articles.router)
app.include_router(events.router)
app.include_router(review.router)


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "0.1.0",
        "pipeline": {
            "stages": [
                "source_intake",
                "article_normalization",
                "event_clustering",
                "claim_extraction",
                "evidence_scoring",
                "user_presentation",
            ],
        },
    }


@app.get("/api/pipeline/run")
async def run_full_pipeline():
    """Run the full pipeline end-to-end."""
    from backend.pipeline.ingestion import ingest_articles
    from backend.pipeline.clustering import cluster_claims_into_events
    from backend.pipeline.consensus import resolve_all_events
    from backend.pipeline.scoring import score_event_claims

    # Stage 1: Ingest
    articles = ingest_articles(seed=True)
    article_count = len(articles)
    claim_count = sum(len(a.claims) for a in articles)

    # Stage 2-3: Normalization happens during clustering
    # Stage 4: Cluster
    events = cluster_claims_into_events()

    # Stage 5: Consensus + Scoring
    resolved = resolve_all_events()
    all_scores = {}
    for event in resolved:
        all_scores[event.event_id] = score_event_claims(event)

    return {
        "stages": {
            "source_intake": {"articles_ingested": article_count, "claims_extracted": claim_count},
            "event_clustering": {"events_created": len(events)},
            "consensus": {"events_resolved": len(resolved)},
            "scoring": {"events_scored": len(all_scores)},
        },
        "summary": f"Ingested {article_count} articles, extracted {claim_count} claims, "
                   f"clustered into {len(events)} events.",
    }