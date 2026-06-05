"""LLM-based claim extraction stage."""
from __future__ import annotations

import json
import logging
import re
from typing import Any

from backend.models import (
    Article,
    Attribution,
    Claim,
    ClaimArgument,
    ClaimBucket,
    EvidenceIndicators,
)
from backend.pipeline.llm import get_llm

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT_TEMPLATE = """<|system|>
You are an expert news analyst. Extract atomic claims from the following article.
Format the output as a JSON list of objects. Each object MUST have:
- "claim_text": string, the atomic claim
- "bucket": one of [verified_fact, attributed_statement, inference, opinionated_framing]
- "arguments": object with keys like "actor", "weapon_type", "location", "casualties"
- "evidence": object with boolean keys [quote, official_statement, eyewitness, satellite_imagery, timestamp_geolocation]
- "attribution": object with keys [status, speaker, phrase]
- "propaganda_flags": list of strings [loaded_language, us_vs_them, certainty_without_evidence]

Article:
{title}
{text}
</s>
<|assistant|>
```json
["""

def extract_claims_llm(article: Article) -> list[Claim]:
    """Extract claims using a local LLM with structured output."""
    try:
        llm = get_llm()
    except Exception as e:
        logger.error(f"LLM not available, falling back to rule-based: {e}")
        return []

    prompt = EXTRACTION_PROMPT_TEMPLATE.format(
        title=article.title, 
        text=article.full_text
    )
    
    logger.info(f"Extracting claims for article: {article.article_id}")
    
    response = llm(
        prompt,
        max_tokens=2048,
        stop=["```", "</s>"],
        echo=False
    )
    
    content = response["choices"][0]["text"]
    # We prepended [ in the prompt to guide the model
    full_json = "[" + content
    
    try:
        # Basic cleanup in case of trailing commas or garbage
        full_json = full_json.strip()
        if not full_json.endswith("]"):
            # Try to find the last ]
            last_bracket = full_json.rfind("]")
            if last_bracket != -1:
                full_json = full_json[:last_bracket+1]
            else:
                full_json += "]"
        
        data = json.loads(full_json)
        claims = []
        for item in data:
            if not isinstance(item, dict):
                continue
                
            # Ensure bucket is valid
            bucket_val = item.get("bucket", "inference")
            if bucket_val not in [b.value for b in ClaimBucket]:
                bucket_val = "inference"
                
            claim = Claim(
                source_article_id=article.article_id,
                source_pool=article.source_pool,
                source_name=article.source_name,
                language=article.language,
                claim_text_original=item.get("claim_text", ""),
                bucket=ClaimBucket(bucket_val),
                arguments={
                    k: ClaimArgument(value=str(v)) 
                    for k, v in item.get("arguments", {}).items()
                    if v is not None
                },
                evidence=EvidenceIndicators(**{
                    k: bool(v) for k, v in item.get("evidence", {}).items()
                    if k in EvidenceIndicators.model_fields
                }),
                attribution=Attribution(**{
                    k: v for k, v in item.get("attribution", {}).items()
                    if k in Attribution.model_fields
                }),
                propaganda_flags=[
                    str(f) for f in item.get("propaganda_flags", [])
                    if isinstance(f, (str, int))
                ]
            )
            claims.append(claim)
        
        logger.info(f"Successfully extracted {len(claims)} claims via LLM.")
        return claims
    except Exception as e:
        logger.error(f"Failed to parse LLM JSON: {e}\nRaw content: {full_json}")
        return []
