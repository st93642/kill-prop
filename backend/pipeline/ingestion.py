"""Stage 1: Source Intake - Ingest articles from different source pools.

In production, this connects to news APIs. For MVP, we use a seeded dataset
and a mock fetch mechanism that demonstrates the full pipeline.
"""

from __future__ import annotations

import os
import re
from datetime import datetime

from backend.models import (
    Article,
    Attribution,
    Claim,
    ClaimBucket,
    EvidenceIndicators,
    SourcePool,
    articles_store,
    claims_store,
)

# Sample seed data demonstrating cross-pool contradictions
SEED_ARTICLES: list[dict] = [
    {
        "canonical_url": "https://example-western.com/bridge-strike",
        "title": "Russian drone strike hits key bridge near Kyiv",
        "author": "Jane Western",
        "published_at": datetime(2026, 6, 5, 3, 10),
        "source_name": "Western Herald",
        "source_pool": SourcePool.WESTERN_MAINSTREAM,
        "source_country": "US",
        "language": "en",
        "full_text": (
            "A Russian Shahed drone struck a fuel depot near the Dnipro river early Friday, "
            "according to regional officials. The attack, which occurred at approximately 03:10 local time, "
            "caused a large fire that was contained by emergency services. No casualties were reported. "
            "The defense ministry stated that air defense systems intercepted two additional drones "
            "heading toward the same area. The depot was one of several infrastructure targets "
            "in a series of strikes this week."
        ),
        "topic_tags": ["geopolitics", "military", "infrastructure"],
    },
    {
        "canonical_url": "https://example-eastern.com/bridge-strike",
        "title": "Ukrainian drone hits military fuel depot",
        "author": "Ivan Eastern",
        "published_at": datetime(2026, 6, 5, 3, 15),
        "source_name": "Eastern Times",
        "source_pool": SourcePool.RUSSIAN_STATE,
        "source_country": "RU",
        "language": "en",
        "full_text": (
            "A Ukrainian FPV drone struck a fuel storage facility near the Dnipro river early Friday, "
            "the defense ministry confirmed. The strike at 03:10 local time targeted a depot "
            "used by Ukrainian forces. Emergency services quickly contained the resulting fire. "
            "There were no civilian casualties. The Ukrainian military has been increasingly "
            "using drone strikes against infrastructure targets in the region."
        ),
        "topic_tags": ["geopolitics", "military", "infrastructure"],
    },
    {
        "canonical_url": "https://example-neutral.com/bridge-strike",
        "title": "Drone strike hits fuel depot near Dnipro, sources disagree on responsibility",
        "author": "Neutral Reporter",
        "published_at": datetime(2026, 6, 5, 4, 0),
        "source_name": "Wire Service",
        "source_pool": SourcePool.NEUTRAL_WIRE,
        "source_country": "CH",
        "language": "en",
        "full_text": (
            "A drone strike hit a fuel depot near the Dnipro river early Friday, causing a fire "
            "that was later contained. Regional officials confirmed the strike occurred at approximately "
            "03:10 local time. Russian state media attributed the attack to Ukrainian forces, while "
            "Western outlets reported it as a Russian strike. The depot is located in an area "
            "where both sides have conducted operations. No casualties have been reported. "
            "Satellite imagery reviewed by independent analysts confirmed the fire but could not "
            "determine the origin of the drone. Both sides have denied responsibility."
        ),
        "topic_tags": ["geopolitics", "military", "infrastructure"],
    },
    {
        "canonical_url": "https://example-russian-indy.com/analysis",
        "title": "Analysis: Fuel depot fire shows fog of war in drone campaign",
        "author": "Independent Analyst",
        "published_at": datetime(2026, 6, 5, 5, 30),
        "source_name": "Independent Gazette",
        "source_pool": SourcePool.RUSSIAN_INDEPENDENT,
        "source_country": "RU",
        "language": "en",
        "full_text": (
            "The fire at the fuel depot near Dnipro early Friday highlights the difficulty "
            "of attributing drone strikes in the ongoing conflict. While official sources on both sides "
            "have claimed the drone was operated by the other party, independent observers note "
            "that both Russia and Ukraine operate similar drone models in this region. "
            "What is clear is that a strike occurred at approximately 03:10 and that a fire "
            "resulted. The depot was likely chosen for its logistical significance. "
            "This incident fits a pattern of escalating drone warfare."
        ),
        "topic_tags": ["geopolitics", "military", "analysis"],
    },
    {
        "canonical_url": "https://example-western2.com/casualty-report",
        "title": "Casualty figures emerge from Dnipro region strike",
        "author": "Mike Reporter",
        "published_at": datetime(2026, 6, 5, 6, 0),
        "source_name": "Western Herald",
        "source_pool": SourcePool.WESTERN_MAINSTREAM,
        "source_country": "US",
        "language": "en",
        "full_text": (
            "New reports from the Dnipro region indicate that the early morning drone strike "
            "may have caused casualties. Local hospital officials reported treating three injured "
            "personnel from the depot. The extent of injuries is described as minor to moderate. "
            "This contradicts earlier reports of no casualties. The hospital statement was "
            "released at 05:45 local time. Emergency services continue to assess the damage."
        ),
        "topic_tags": ["geopolitics", "military", "casualties"],
    },
    {
        "canonical_url": "https://tass.ru/armiya-i-opk/1234567",
        "title": "МО РФ: Средства ПВО сбили украинский беспилотник над Брянской областью",
        "author": "ТАСС",
        "published_at": datetime(2026, 6, 5, 4, 30),
        "source_name": "TASS",
        "source_pool": SourcePool.RUSSIAN_STATE,
        "source_country": "RU",
        "language": "ru",
        "full_text": (
            "Москва. 5 июня. ТАСС. Дежурными средствами ПВО украинский беспилотный летательный аппарат "
            "уничтожен над территорией Брянской области, сообщили в Минобороны РФ. "
            "Попытка киевского режима совершить террористическую атаку была пресечена около 04:30 мск. "
            "Пострадавших и разрушений нет. Ранее в ведомстве сообщили о перехвате еще двух дронов."
        ),
        "topic_tags": ["military", "air_defense"],
    },
    {
        "canonical_url": "https://english.news.cn/20260605/abcde",
        "title": "China calls for restraint after drone strikes in Ukraine",
        "author": "Xinhua",
        "published_at": datetime(2026, 6, 5, 8, 0),
        "source_name": "Xinhua",
        "source_pool": SourcePool.CHINESE_STATE,
        "source_country": "CN",
        "language": "en",
        "full_text": (
            "Beijing, June 5 (Xinhua) -- China on Friday urged all parties involved in the Ukraine crisis "
            "to exercise maximum restraint and avoid targeting civilian infrastructure. "
            "Foreign Ministry spokesperson stated that the international community should promote peace talks. "
            "The comments came after reports of drone strikes near the Dnipro river. "
            "China maintains a neutral position and calls for a political settlement of the conflict."
        ),
        "topic_tags": ["diplomacy", "geopolitics"],
    },
]


def translate_text(text: str, source_lang: str) -> str:
    """Translate text to English if it's not already in English.
    
    In a real-world scenario, this would call an external API like DeepL or Google Translate.
    For this MVP, we provide a mock translation that flags the text as translated.
    """
    if source_lang == "en":
        return text
    
    # Mock translation logic
    translations = {
        "ru": {
            "МО РФ: Средства ПВО сбили украинский беспилотник над Брянской областью": 
                "Russian MoD: Air defense systems shot down Ukrainian drone over Bryansk region",
            "Москва. 5 июня. ТАСС. Дежурными средствами ПВО украинский беспилотный летательный аппарат уничтожен над территорией Брянской области, сообщили в Минобороны РФ. Попытка киевского режима совершить террористическую атаку была пресечена около 04:30 мск. Пострадавших и разрушений нет. Ранее в ведомстве сообщили о перехвате еще двух дронов.":
                "Moscow. June 5. TASS. A Ukrainian unmanned aerial vehicle was destroyed over the territory of the Bryansk region by air defense systems on duty, the Russian Ministry of Defense reported. An attempt by the Kyiv regime to carry out a terrorist attack was thwarted around 04:30 Moscow time. There were no casualties or destruction. Earlier, the department reported the interception of two more drones."
        }
    }
    
    translated = translations.get(source_lang, {}).get(text)
    if translated:
        return translated
    
    return f"[Translated from {source_lang}] {text}"


def _extract_claims_from_article(article: Article) -> list[Claim]:
    """Simple rule-based claim extraction from article text.
    
    In production, this would use an LLM with strict schemas. For MVP,
    we use keyword and pattern matching to demonstrate the concept.
    """
    claims_list: list[Claim] = []
    text = article.full_text
    sentences = re.split(r'(?<=[.!?])\s+', text)

    for i, sentence in enumerate(sentences):
        sentence = sentence.strip()
        if not sentence or len(sentence) < 20:
            continue

        claim = Claim(
            source_article_id=article.article_id,
            source_pool=article.source_pool,
            source_name=article.source_name,
            language=article.language,
            claim_text_original=sentence,
            evidence=EvidenceIndicators(),
            attribution=Attribution(),
        )

        # Detect attribution markers
        attribution_phrases = [
            r"according to", r"said\b", r"stated\b", r"confirmed\b",
            r"reported\b", r"attributed\b", r"according\s+to",
        ]
        attribution_match = None
        for phrase in attribution_phrases:
            m = re.search(phrase, sentence, re.IGNORECASE)
            if m:
                attribution_match = m.group(0)
                break

        if attribution_match:
            claim.bucket = ClaimBucket.ATTRIBUTED_STATEMENT
            claim.attribution.status = "on_record"
            claim.attribution.phrase = attribution_match
            # Extract the speaker (simple heuristic)
            speaker_match = re.search(
                r"(?:according to\s+)?(\w+\s+\w+)(?:\s+(?:said|stated|confirmed|reported))?",
                sentence, re.IGNORECASE
            )
            if speaker_match:
                claim.attribution.speaker = speaker_match.group(1)
        elif any(word in sentence.lower() for word in ["may", "might", "could", "likely", "possibly", "unclear"]):
            claim.bucket = ClaimBucket.INFERENCE
        elif any(word in sentence.lower() for word in ["escalating", "fog of war", "pattern of"]):
            claim.bucket = ClaimBucket.OPINIONATED_FRAMING
        else:
            claim.bucket = ClaimBucket.VERIFIED_FACT

        # Check for evidence indicators
        claim.evidence.quote = '"' in sentence or "said" in sentence.lower()
        claim.evidence.official_statement = any(
            w in sentence.lower() for w in ["official", "ministry", "defense ministry", "regional"]
        )
        claim.evidence.eyewitness = "eyewitness" in sentence.lower() or "witness" in sentence.lower()
        claim.evidence.satellite_imagery = "satellite" in sentence.lower() or "imagery" in sentence.lower()
        claim.evidence.timestamp_geolocation = bool(re.search(r'\d{1,2}:\d{2}', sentence))

        # Detect propaganda signals
        propaganda_signals = []
        loaded_terms = ["terror", "aggressor", "fascist", "liberation", "puppet", "regime"]
        if any(term in sentence.lower() for term in loaded_terms):
            propaganda_signals.append("loaded_language")
        if "always" in sentence.lower() or "never" in sentence.lower():
            propaganda_signals.append("certainty_without_evidence")
        if re.search(r'\b(them|they)\b.*\b(us|we)\b', sentence, re.IGNORECASE):
            propaganda_signals.append("us_vs_them")
        claim.propaganda_flags = propaganda_signals

        claims_list.append(claim)

    return claims_list


def ingest_articles(seed: bool = True) -> list[Article]:
    """Ingest articles from source pools.
    
    Args:
        seed: If True, load seed data for MVP demonstration.
              In production, this would call news APIs instead.
    
    Returns:
        List of ingested articles with extracted claims.
    """
    if seed:
        from backend.pipeline.normalization import normalize_claims_batch

        for seed_data in SEED_ARTICLES:
            article = Article(**seed_data)
            
            # Apply translation if needed
            if article.language != "en":
                article.title = translate_text(article.title, article.language)
                article.full_text = translate_text(article.full_text, article.language)
                # Keep original language but the text is now English for the pipeline
                # In a real system, we might keep both.
            
            if os.getenv("USE_LLM", "false").lower() == "true":
                from backend.pipeline.llm_extraction import extract_claims_llm
                claims = extract_claims_llm(article)
                if not claims:
                    claims = _extract_claims_from_article(article)
            else:
                claims = _extract_claims_from_article(article)

            # Normalize claims immediately so arguments are populated
            claims = normalize_claims_batch(claims)
            article.claims = claims
            articles_store[article.article_id] = article
            for c in claims:
                claims_store[c.claim_id] = c

        return list(articles_store.values())

    # Production: call news APIs here
    # e.g., NewsAPI, GNews, Google News Russia endpoint
    return []


def fetch_article(article_id: str) -> Article | None:
    """Fetch a single article by ID."""
    return articles_store.get(article_id)
