"""API routes for articles and the pipeline intake."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.models import Article, articles_store, claims_store
from backend.pipeline.ingestion import fetch_article, ingest_articles
from backend.pipeline.normalization import normalize_claims_batch
from backend.storage import archive_stores

router = APIRouter(prefix="/api/articles", tags=["articles"])


@router.post("/ingest")
async def ingest(seed: bool = True):
    """Ingest articles from source pools (seed data for MVP)."""
    articles = ingest_articles(seed=seed)
    # Persist newly ingested articles to disk
    archive_stores()
    return {
        "message": f"Ingested {len(articles)} articles",
        "article_ids": [a.article_id for a in articles],
        "total_claims": sum(len(a.claims) for a in articles),
    }


@router.get("")
async def list_articles():
    """List all ingested articles."""
    articles = list(articles_store.values())
    return [
        {
            "article_id": a.article_id,
            "title": a.title,
            "source": a.source_name,
            "source_pool": a.source_pool.value,
            "language": a.language,
            "claim_count": len(a.claims),
        }
        for a in articles
    ]


@router.get("/{article_id}")
async def get_article(article_id: str):
    """Get a single article with its claims."""
    article = fetch_article(article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    # Normalize claims
    normalized = normalize_claims_batch(article.claims)
    return {
        "article_id": article.article_id,
        "title": article.title,
        "source": article.source_name,
        "source_pool": article.source_pool.value,
        "canonical_url": article.canonical_url,
        "published_at": article.published_at,
        "retrieved_at": article.retrieved_at,
        "full_text": article.full_text,
        "topic_tags": article.topic_tags,
        "claims": [
            {
                "claim_id": c.claim_id,
                "text_original": c.claim_text_original,
                "text_normalized": c.claim_text_normalized,
                "bucket": c.bucket.value,
                "arguments": {
                    k: {"value": v.value, "normalized": v.normalized, "attributed": v.attributed}
                    for k, v in c.arguments.items()
                },
                "evidence": c.evidence.model_dump(),
                "attribution": c.attribution.model_dump(),
                "propaganda_flags": c.propaganda_flags,
                "confidence": c.confidence,
            }
            for c in normalized
        ],
    }