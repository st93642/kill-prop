"""Stage 2-3: Claim Extraction & Normalization.

Converts raw claims into normalized structured forms with canonical values
for downstream comparison and consensus.
"""

from __future__ import annotations

import re
from datetime import datetime

from backend.models import (
    Claim,
    ClaimArgument,
    FieldOntology,
    SourcePool,
    claims_store,
)

# Normalization maps for common surface form variations
WEAPON_NORMALIZATION: dict[str, str] = {
    "uav": "drone",
    "unmanned aerial vehicle": "drone",
    "unmanned aircraft": "drone",
    "shahed": "shahed_drone",
    "shahed drone": "shahed_drone",
    "shahed-136": "shahed_drone",
    "fpv": "fpv_drone",
    "fpv drone": "fpv_drone",
    "kamikaze drone": "drone",
    "loitering munition": "drone",
    "cruise missile": "cruise_missile",
    "ballistic missile": "ballistic_missile",
    "artillery shell": "artillery",
    "artillery round": "artillery",
}

ACTOR_NORMALIZATION: dict[str, str] = {
    "russian forces": "russian_military",
    "russian military": "russian_military",
    "russian army": "russian_military",
    "russia": "russian_military",
    "moscow": "russian_military",
    "the russian federation": "russian_military",
    "ukrainian forces": "ukrainian_military",
    "ukrainian military": "ukrainian_military",
    "ukrainian army": "ukrainian_military",
    "ukraine": "ukrainian_military",
    "kyiv": "ukrainian_military",
    "the ukrainian government": "ukrainian_government",
    "the russian government": "russian_government",
}

LOCATION_NORMALIZATION: dict[str, str] = {
    "dnipro": "dnipro",
    "dnepr": "dnipro",
    "dnipro river": "dnipro",
    "dnipro region": "dnipro_region",
    "dnipropetrovsk": "dnipro_region",
    "kyiv": "kyiv",
    "kiev": "kyiv",
    "bryansk": "bryansk",
    "moskva": "moscow",
    "moscow city": "moscow",
}

TARGET_NORMALIZATION: dict[str, str] = {
    "fuel depot": "fuel_depot",
    "fuel storage": "fuel_depot",
    "fuel storage facility": "fuel_depot",
    "oil depot": "fuel_depot",
    "depot": "fuel_depot",
    "bridge": "bridge",
    "power plant": "power_plant",
    "electrical substation": "power_substation",
    "ammunition depot": "ammo_depot",
    "warehouse": "supply_warehouse",
}


def _normalize_with_map(value: str, norm_map: dict[str, str]) -> str | None:
    """Normalize a value using a lookup map, or None if no match."""
    lower = value.lower().strip()
    if lower in norm_map:
        return norm_map[lower]
    # Try partial match
    for raw, canonical in norm_map.items():
        if raw in lower or lower in raw:
            return canonical
    return None


def normalize_claim(
    claim: Claim,
    ontology: dict[str, FieldOntology] | None = None,
    anchor_date: str | None = None,
) -> Claim:
    """Normalize a claim's arguments to canonical values.
    
    Converts surface forms to canonical identifiers, normalizes timestamps,
    locations, entities, and weapon types.

    Args:
        anchor_date: Optional ``YYYY-MM-DD`` string used to anchor extracted
            time-of-day references. Falls back to today's date if not given.
    """
    text = claim.claim_text_original
    normalized_text = text

    # --- Extract and normalize event_type ---
    event_type_patterns = [
        (r"(drone|aerial|missile|artillery)\s+(strike|attack|hit)", "strike"),
        (r"(struck|hit|targeted|attacked)", "strike"),
        (r"(explosion|blast|detonation)", "explosion"),
        (r"(fire|blaze|burning)", "fire"),
        (r"(shelling|bombardment)", "bombardment"),
    ]
    for pattern, etype in event_type_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            claim.arguments["event_type"] = ClaimArgument(
                value=etype, normalized=etype
            )
            claim.event_type = etype
            break

    # --- Extract and normalize weapon_type ---
    for raw in WEAPON_NORMALIZATION:
        if raw in text.lower():
            canonical = WEAPON_NORMALIZATION[raw]
            claim.arguments["weapon_type"] = ClaimArgument(
                value=raw, normalized=canonical
            )
            break

    # --- Extract and normalize actor ---
    for raw in ACTOR_NORMALIZATION:
        if raw in text.lower():
            canonical = ACTOR_NORMALIZATION[raw]
            # Determine if this is an attributed claim
            is_attributed = claim.attribution.speaker is not None
            claim.arguments["actor"] = ClaimArgument(
                value=raw, normalized=canonical, attributed=is_attributed
            )
            break

    # --- Extract and normalize location ---
    for raw in LOCATION_NORMALIZATION:
        if raw in text.lower():
            canonical = LOCATION_NORMALIZATION[raw]
            claim.arguments["location"] = ClaimArgument(
                value=raw, normalized=canonical
            )
            break

    # --- Extract and normalize target ---
    for raw in TARGET_NORMALIZATION:
        if raw in text.lower():
            canonical = TARGET_NORMALIZATION[raw]
            claim.arguments["target"] = ClaimArgument(
                value=raw, normalized=canonical
            )
            break

    # --- Extract time references ---
    time_match = re.search(
        r'(\d{1,2}):(\d{2})\s*(am|pm)?\s*(local\s+time)?',
        text, re.IGNORECASE
    )
    if time_match:
        # Anchor the extracted time-of-day to the article date when available;
        # otherwise fall back to today's date.
        anchor = anchor_date or datetime.now().strftime("%Y-%m-%d")
        hour = int(time_match.group(1))
        minute = time_match.group(2)
        ampm = time_match.group(3)
        if ampm:
            ampm = ampm.lower()
            if ampm == "pm" and hour != 12:
                hour += 12
            elif ampm == "am" and hour == 12:
                hour = 0
        claim.arguments["time"] = ClaimArgument(
            value=time_match.group(0).strip(),
            normalized=f"{anchor}T{str(hour).zfill(2)}:{minute}:00",
        )

    # --- Normalize claim text ---
    normalized_claim_text = text
    # Replace surface forms with bracketed normalized versions
    for raw, canonical in {**WEAPON_NORMALIZATION, **ACTOR_NORMALIZATION,
                           **TARGET_NORMALIZATION}.items():
        pattern = re.compile(re.escape(raw), re.IGNORECASE)
        normalized_claim_text = pattern.sub(f"[{canonical}]", normalized_claim_text)
    claim.claim_text_normalized = normalized_claim_text

    return claim


def normalize_claims_batch(
    claims: list[Claim],
    ontology: dict[str, FieldOntology] | None = None,
    anchor_date: str | None = None,
) -> list[Claim]:
    """Normalize a batch of claims."""
    return [normalize_claim(c, ontology, anchor_date=anchor_date) for c in claims]


def extract_candidate_claim_set(article_id: str) -> list[Claim]:
    """Get all claims for an article and normalize them."""
    from backend.models import articles_store

    article_claims = [
        c for c in claims_store.values() if c.source_article_id == article_id
    ]
    anchor = None
    article = articles_store.get(article_id)
    if article and article.published_at:
        anchor = article.published_at.strftime("%Y-%m-%d")
    return normalize_claims_batch(article_claims, anchor_date=anchor)
