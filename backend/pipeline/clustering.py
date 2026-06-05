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
    EventContradictionState,
    SourcePool,
    articles_store,
    claims_store,
    events_store,
)

CLUSTER_WINDOW_HOURS = 6  # Max time gap for articles to be the same event
TAG_OVERLAP_THRESHOLD = 0.35  # Min combined similarity score to cluster articles

# Only these topic categories are relevant for propaganda/political analysis.
# Additionally, _infer_tags() applies a geo-filter: only articles mentioning
# Europe or Russia geography pass through (no Gaza, Delhi, Peru, etc.).
POLITICAL_TOPICS = {
    "military", "geopolitics", "diplomacy", "peace", "war", "conflict",
    "economy", "trade", "sanctions", "energy", "food_security",
    "infrastructure", "defense", "nuclear", "election", "government",
    "policy", "international", "foreign_policy", "security",
    "terrorism", "human_rights", "refugees", "migration",
}


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


def _article_title_similarity(a1: Article, a2: Article) -> float:
    """Compute title similarity using both SequenceMatcher and word overlap.
    
    Word overlap catches cases where key entities match even if phrasing differs
    (e.g., 'Drone strike hits fuel depot near Dnipro' vs 'Casualty figures 
    emerge from Dnipro region strike' — both share 'Dnipro' and 'strike').
    """
    t1 = a1.title.lower()
    t2 = a2.title.lower()
    
    # SequenceMatcher for phrasing similarity
    seq_sim = SequenceMatcher(None, t1, t2).ratio()
    
    # Word overlap for entity matching (words > 3 chars, skip stopwords)
    stopwords = {'the', 'and', 'for', 'from', 'has', 'its', 'not', 'over', 'that', 
                 'was', 'with', 'after', 'into', 'said', 'says', 'this', 'what',
                 'have', 'been', 'were', 'will', 'more', 'than', 'about', 'their'}
    # Strip punctuation for word matching
    import re
    clean1 = re.sub(r'[^\w\s]', '', t1)
    clean2 = re.sub(r'[^\w\s]', '', t2)
    words1 = {w for w in clean1.split() if len(w) > 3 and w not in stopwords}
    words2 = {w for w in clean2.split() if len(w) > 3 and w not in stopwords}
    
    if not words1 or not words2:
        word_sim = 0.0
    else:
        intersection = words1 & words2
        union = words1 | words2
        word_sim = len(intersection) / len(union)
    
    # Blend: 60% SequenceMatcher + 40% word overlap
    return 0.6 * seq_sim + 0.4 * word_sim


def _article_text_similarity(a1: Article, a2: Article) -> float:
    """Compute title + topic + content similarity between two articles."""
    # Use title + topic tags for lightweight comparison
    text1 = (a1.title + " " + " ".join(a1.topic_tags)).lower()
    text2 = (a2.title + " " + " ".join(a2.topic_tags)).lower()
    title_topic_sim = SequenceMatcher(None, text1, text2).ratio()
    
    # Add content similarity using first 500 chars of text for heavier comparison
    content1 = a1.full_text[:500].lower()
    content2 = a2.full_text[:500].lower()
    content_sim = SequenceMatcher(None, content1, content2).ratio()
    
    # Weighted combination: 40% title+tags, 60% content
    return 0.4 * title_topic_sim + 0.6 * content_sim


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
    
    Filters out non-political topics (sports, entertainment, local news).
    Deduplicates: only one representative claim per source pool per event.
    """
    # Clear previous events to avoid duplicates on re-run
    events_store.clear()
    # Also unlink claims from previous events
    for c in claims_store.values():
        c.event_id = None

    articles = list(articles_store.values())

    if not articles:
        return []

    # Filter to only political/propaganda-relevant articles
    articles = [
        a for a in articles
        if any(t in POLITICAL_TOPICS for t in a.topic_tags)
    ]

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

            # Title word overlap + SequenceMatcher
            title_sim = _article_title_similarity(article, rep)
            # Tag overlap
            tag_score = _article_topic_overlap(article, rep)
            # Content text similarity
            text_score = _article_text_similarity(article, rep)
            
            # Weighted: title provides entity matching (entities, places),
            # tags confirm topic alignment, content confirms same story
            combined = 0.35 * title_sim + 0.25 * tag_score + 0.40 * text_score

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

        # Deduplicate: keep only one representative claim per source pool
        # For each pool, pick the claim with the highest confidence/best evidence
        pool_claims: dict[str, Claim] = {}
        for c in group_claims:
            pool_key = c.source_pool.value
            if pool_key not in pool_claims:
                pool_claims[pool_key] = c
            else:
                # Keep the claim with more evidence indicators
                existing_evidence = sum(1 for v in pool_claims[pool_key].evidence.model_dump().values() if v)
                new_evidence = sum(1 for v in c.evidence.model_dump().values() if v)
                if new_evidence > existing_evidence:
                    pool_claims[pool_key] = c
                elif new_evidence == existing_evidence and len(c.claim_text_original) > len(pool_claims[pool_key].claim_text_original):
                    pool_claims[pool_key] = c

        deduped_claims = list(pool_claims.values())

        event = Event()
        for claim in deduped_claims:
            event.claim_ids.append(claim.claim_id)
            claim.event_id = event.event_id

        event.article_ids = article_ids
        event.source_pools_represented = list({c.source_pool for c in deduped_claims})

        # Generate title from article titles
        titles = [a.title for a in article_group if a.title]
        if titles:
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
            actor_values = set()
            for c in deduped_claims:
                actor = c.arguments.get("actor")
                if actor and actor.normalized:
                    actor_values.add(actor.normalized)
            if len(actor_values) > 1:
                event.contradiction_state = EventContradictionState.DISPUTED_DETAIL

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