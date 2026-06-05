"""Stage 4: Event Clustering.

Groups articles about the same event using time proximity, shared topic tags,
and cross-article entity overlap. All claims from clustered articles are
aggregated into a single event.
"""

from __future__ import annotations

from datetime import timedelta
from difflib import SequenceMatcher

from backend.models import (
    Article,
    Claim,
    Event,
    SourcePool,
    articles_store,
    claims_store,
    events_store,
)

CLUSTER_WINDOW_HOURS = 48  # Max time gap for articles to be the same event
TAG_OVERLAP_THRESHOLD = 0.3  # Min tag overlap ratio to cluster articles


def _article_time_proximity(a1: Article, a2: Article) -> bool:
    """Check if two articles are within the clustering time window."""
    t1 = a1.published_at or a1.retrieved_at
    t2 = a2.published_at or a2.retrieved_at
    diff = abs((t1 - t2).total_seconds())
    return diff <= CLUSTER_WINDOW_HOURS * 3600


def _article_topic_overlap(a1: Article, a2: Article) -> float:
    """Calculate topic tag overlap ratio between two articles."""
    tags1 = set(t.lower() for t in a1.topic_tags)
    tags2 = set(t.lower() for t in a2.topic_tags)
    if not tags1 or not tags2:
        return 0.0
    intersection = tags1 & tags2
    union = tags1 | tags2
    return len(intersection) / len(union)


def _article_text_similarity(a1: Article, a2: Article) -> float:
    """Compute title + topic similarity between two articles."""
    text1 = (a1.title + " " + " ".join(a1.topic_tags)).lower()
    text2 = (a2.title + " " + " ".join(a2.topic_tags)).lower()
    return SequenceMatcher(None, text1, text2).ratio()


def _claim_entity_similarity(c1: Claim, c2: Claim) -> float:
    """Calculate entity overlap between two individual claims."""
    shared = 0
    total = 0
    for field in ["location", "target", "event_type", "weapon_type"]:
        v1 = c1.arguments.get(field)
        v2 = c2.arguments.get(field)
        if v1 and v2 and v1.normalized and v2.normalized:
            total += 1
            if v1.normalized == v2.normalized:
                shared += 1
            elif v1.value.lower() in v2.value.lower() or v2.value.lower() in v1.value.lower():
                shared += 0.5
    if total == 0:
        return 0.0
    return shared / total


def cluster_claims_into_events() -> list[Event]:
    """Group articles about the same event, then aggregate their claims.
    
    Two-stage approach:
    1. Cluster articles by time proximity + topic overlap + title similarity
    2. Aggregate all claims from clustered articles into one Event object
    
    This produces coherent events where each event represents one news story
    covered by multiple source pools.
    """
    articles = list(articles_store.values())

    if not articles:
        return []

    # Stage 1: Cluster articles
    articles_sorted = sorted(articles, key=lambda a: a.published_at or a.retrieved_at)
    article_clusters: list[list[Article]] = []

    for article in articles_sorted:
        best_cluster_idx = -1
        best_score = 0.0

        for idx, cluster in enumerate(article_clusters):
            rep = cluster[0]

            # Time proximity
            if not _article_time_proximity(article, rep):
                continue

            # Combined similarity
            tag_score = _article_topic_overlap(article, rep)
            text_score = _article_text_similarity(article, rep)
            combined = 0.5 * tag_score + 0.5 * text_score

            if combined > best_score and combined >= TAG_OVERLAP_THRESHOLD:
                best_score = combined
                best_cluster_idx = idx

        if best_cluster_idx >= 0:
            article_clusters[best_cluster_idx].append(article)
        else:
            article_clusters.append([article])

    # Stage 2: Convert article clusters to Event objects
    events: list[Event] = []
    for article_group in article_clusters:
        # Collect all claims from these articles
        article_ids = [a.article_id for a in article_group]
        group_claims = [
            c for c in claims_store.values()
            if c.source_article_id in article_ids
        ]

        if not group_claims:
            continue

        event = Event()
        for claim in group_claims:
            event.claim_ids.append(claim.claim_id)
            claim.event_id = event.event_id

        event.article_ids = article_ids
        event.source_pools_represented = list({c.source_pool for c in group_claims})

        # Generate title from article titles
        titles = [a.title for a in article_group if a.title]
        if titles:
            # Find common words across titles
            common_title = max(set(titles), key=len) if len(titles) > 1 else titles[0]
            event.title = common_title
        else:
            event.title = "Uncategorized event"

        # Topic from tags
        all_tags = set()
        for a in article_group:
            all_tags.update(a.topic_tags)
        event.topic = ", ".join(sorted(all_tags)) if all_tags else ""

        # Mark contradiction state based on pool diversity
        if len(event.source_pools_represented) >= 2:
            # Check if there are contradictory actor claims
            actor_values = set()
            for c in group_claims:
                actor = c.arguments.get("actor")
                if actor and actor.normalized:
                    actor_values.add(actor.normalized)
            if len(actor_values) > 1:
                event.contradiction_state = "disputed_detail"

        events_store[event.event_id] = event
        events.append(event)

    return events


def get_event(event_id: str) -> Event | None:
    """Get an event by ID."""
    return events_store.get(event_id)


def get_all_events() -> list[Event]:
    """Return all events sorted by update time (newest first)."""
    events = list(events_store.values())
    events.sort(key=lambda e: e.updated_at, reverse=True)
    return events