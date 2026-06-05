<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# Yes, provide the normalization algorithm logic

Use a **field-by-field claim normalization pipeline** that converts raw articles into structured event records, then promotes only the overlapping fields into the fact layer while keeping contradictory fields as attributed disputes. The key idea is that normalization happens at the event-argument level, because cross-document extraction research shows that multiple documents often contain partial or biased role information, so the system must normalize entities, roles, and event arguments before deciding what can be stated confidently.[^1][^2][^3][^4]

## Data model

Represent each article as a set of extracted claims, and each claim as a structured object rather than a sentence blob. A useful schema is:[^2][^1]

```json
{
  "claim_id": "c_123",
  "event_id": null,
  "source_article_id": "a_456",
  "source_pool": "western",
  "source_name": "Example Outlet",
  "language": "en",
  "claim_text_original": "The depot was hit by a Russian drone at 03:10.",
  "claim_text_normalized": "A depot was hit by a drone.",
  "event_type": "strike",
  "arguments": {
    "target": {"value": "depot", "normalized": "fuel_depot"},
    "location": {"value": "Bryansk", "normalized": "bryansk"},
    "time": {"value": "2026-06-05T03:10:00+03:00", "normalized": "2026-06-05T03:10:00+03:00"},
    "weapon_type": {"value": "drone", "normalized": "drone"},
    "actor": {"value": "Russian", "normalized": "russia", "attributed": true}
  },
  "evidence": {
    "quote": false,
    "official_statement": true,
    "primary_media": false,
    "document_link": false
  },
  "attribution": {
    "status": "on_record",
    "speaker": "regional officials",
    "phrase": "according to regional officials"
  },
  "confidence": 0.62
}
```

This structure fits claim-normalization work, which emphasizes reducing ambiguity and transforming messy text into clearer normalized claims suitable for downstream verification. It also matches cross-document event extraction pipelines, which explicitly separate event extraction, entity normalization, role normalization, and entity-role resolution.[^5][^4][^1][^2]

## Pipeline stages

Stage 1 is article ingestion and sentence segmentation. Each article is split into candidate factual statements, while opinion, rhetorical questions, and broad commentary are filtered out because claim-normalization systems work best when they start from check-worthy factual assertions instead of full narrative prose.[^6][^1]

Stage 2 is claim extraction. For every candidate sentence, extract an event predicate and its arguments: what happened, to whom or what, where, when, how, and who is said to be responsible. Keep explicit attribution markers such as “officials said,” “the ministry claimed,” or “according to local media,” because journalism guidance stresses that sourced assertions must preserve where the information came from rather than being rewritten as unattributed fact.[^3][^4][^7][^2]

Stage 3 is normalization. Convert surface forms into canonical values, so “UAV,” “drone,” and “unmanned aerial vehicle” map to one class when appropriate, while “Russian forces,” “Moscow,” and “the Russian military” can map to a common actor entity only if your ontology says those references are equivalent in context. Normalize timestamps to UTC, locations to geocoded identifiers, source names to canonical outlet IDs, and entity mentions to a single canonical record.[^4][^1][^2]

Stage 4 is event clustering. Group claims from different articles into the same underlying event using time proximity, geospatial overlap, shared target entities, and embedding similarity on the normalized predicate plus arguments, because cross-document extraction is specifically about integrating fragmented event information from multiple documents into one event-centric view.[^2][^4]

## Consensus algorithm

After clustering, compute consensus separately for each field. Never decide truth at the sentence level if only one argument differs.[^4][^2]

For each event cluster $E$, define fields such as:

- `event_type`
- `target`
- `location`
- `time_bucket`
- `weapon_type`
- `actor`
- `casualties`
- `damage_level`

For each field $f$, collect all candidate normalized values $v_1, v_2, \dots, v_n$ from claims in the cluster. Then calculate support by weighted evidence:[^1][^2]

$$
\text{support}(v, f) = \sum_{c \in E_f(v)} w_{source}(c) + w_{evidence}(c) + w_{specificity}(c) - w_{hedge}(c)
$$

where $E_f(v)$ is the set of claims in event $E$ assigning value $v$ to field $f$. The purpose is not to crown one outlet automatically, but to distinguish corroborated, specific, attributed reporting from weakly supported or highly hedged assertions.[^7][^8][^3]

Then apply field resolution rules:

1. If one value has strong support and no credible contradiction, promote it to `confirmed`.[^8][^3]
2. If multiple values share the same abstraction parent, collapse upward to the nearest common parent and mark child details as `disputed`.[^1][^2]
3. If values are mutually incompatible and no safe abstraction exists, emit `unknown` and retain all values in the dispute layer.[^3][^7]
4. If only one source pool reports the field, keep it as `single-pool report`, not `fact`.[^8][^3]

## Abstraction ladder

This is the logic you described in your drone example. You need a field ontology with parent-child relationships so the system can collapse contradictory values upward without inventing new meaning.[^2][^1]

Example ontology fragment:

```json
{
  "weapon_type": {
    "shahed_drone": "drone",
    "fpv_drone": "drone",
    "quadcopter": "drone",
    "cruise_missile": "missile",
    "ballistic_missile": "missile",
    "drone": "aerial_weapon",
    "missile": "aerial_weapon",
    "artillery": "indirect_fire"
  },
  "actor": {
    "russian_military": "russia_affiliated",
    "russia_affiliated": "claimed_actor_present",
    "ukrainian_military": "ukraine_affiliated",
    "ukraine_affiliated": "claimed_actor_present"
  }
}
```

If Western claims say `actor = russian_military` and Eastern claims say `actor = ukrainian_military`, the nearest safe common abstraction is not “Russia/Ukraine” but “claimed_actor_present,” which is too vague for user display. In that case the better UI output is to omit actor from the fact layer and render “responsibility disputed,” because attribution ethics favor transparent disagreement over false precision.[^7][^3][^1][^2]

For `weapon_type`, if one side says `shahed_drone` and the other says `fpv_drone`, you can collapse to `drone`. If one side says `drone` and the other says `missile`, you may collapse to `aerial_weapon` internally, but the user-facing wording should usually be “an aerial attack was reported” only if other evidence supports that abstraction.[^4][^1][^2]

## Resolution pseudocode

Here is the practical logic for one field:

```python
def resolve_field(field_name, candidate_claims, ontology):
    groups = aggregate_by_normalized_value(candidate_claims)
    scored = []

    for value, claims in groups.items():
        score = 0.0
        pool_set = set()
        for c in claims:
            score += source_weight(c.source_name)
            score += evidence_weight(c.evidence)
            score += specificity_weight(field_name, c.arguments.get(field_name))
            score -= hedge_penalty(c.claim_text_original)
            pool_set.add(c.source_pool)
        scored.append({
            "value": value,
            "score": score,
            "pool_count": len(pool_set),
            "claims": claims
        })

    scored.sort(key=lambda x: x["score"], reverse=True)

    if len(scored) == 0:
        return {"status": "unknown"}

    top = scored[^0]
    contradictory = [s for s in scored[1:] if is_contradictory(field_name, top["value"], s["value"], ontology)]

    if top["pool_count"] >= 2 and len(contradictory) == 0:
        return {"status": "confirmed", "value": top["value"], "support": top}

    if len(scored) >= 2:
        ancestor = lowest_common_safe_ancestor([s["value"] for s in scored], ontology, field_name)
        if ancestor and is_user_safe_abstraction(field_name, ancestor):
            return {
                "status": "abstracted",
                "value": ancestor,
                "disputed_values": [s["value"] for s in scored]
            }

    return {
        "status": "disputed",
        "value": None,
        "disputed_values": [s["value"] for s in scored]
    }
```

This design mirrors normalization research by first simplifying and structuring claims, then supporting comparison across differently phrased reports. It also aligns with attribution practice because contradictory claims are not erased; they remain linked to their originating sources.[^5][^3][^7][^1]

## Event summary generation

Once each field is resolved, generate the user-facing event using three layers:

1. `fact_layer`
2. `dispute_layer`
3. `source_claims_layer`

For your example, the output object could be:

```json
{
  "event_id": "e_789",
  "fact_layer": {
    "summary": "A depot was hit by a drone in Bryansk early Friday.",
    "fields": {
      "event_type": "strike",
      "target": "depot",
      "location": "bryansk",
      "weapon_type": "drone",
      "time_bucket": "early_friday"
    }
  },
  "dispute_layer": {
    "actor": {
      "status": "disputed",
      "display": "Sources disagree on whose drone was involved.",
      "claims": [
        {"value": "russian_military", "supported_by": ["western_pool"]},
        {"value": "ukrainian_military", "supported_by": ["eastern_pool"]}
      ]
    }
  },
  "source_claims_layer": [
    {
      "source": "Outlet A",
      "claim": "The depot was hit by a Russian drone.",
      "attribution": "according to regional officials"
    },
    {
      "source": "Outlet B",
      "claim": "The depot was hit by a Ukrainian drone.",
      "attribution": "according to the defense ministry"
    }
  ]
}
```

This output preserves your intended behavior exactly: the stable overlap is surfaced first, but contradictory authorship remains visible and attributable rather than silently discarded.[^3][^7]

## Confidence and guardrails

Add a confidence class per field: `confirmed`, `probable`, `single-source`, `disputed`, `unknown`. That gives you a safer product than binary true/false labeling, because fact-checking methodology generally relies on transparent evidence evaluation and explicit verdict criteria rather than hidden internal certainty.[^8][^3]

Do not collapse upward when the abstraction becomes misleading. If the values are “drone strike” and “gas explosion,” the safe common parent may just be “incident,” and that is often too weak to headline as a fact unless there is independent confirmation that an incident occurred at all. Also keep an audit trail showing which exact claims, sources, timestamps, and extraction decisions produced each normalized field, because attribution guidance emphasizes making the trail back to the source clear for readers and reviewers.[^2][^3][^4]

## Recommended thresholds

For an MVP, set simple deterministic rules before training anything learned. Require at least two independent articles or two source pools for `confirmed`, allow ontology collapse only when the parent concept is semantically natural in user language, and always send `actor`, `motive`, and `intent` through a stricter threshold because those fields are where propaganda and speculation concentrate most heavily.[^3][^2]

A practical first pass is:

- `confirmed`: two or more independent corroborations and no strong contradiction.[^8][^3]
- `abstracted`: contradiction exists, but a natural shared parent exists, like `shahed_drone` plus `fpv_drone` becoming `drone`.[^1][^2]
- `disputed`: contradiction exists with no safe user-facing parent, like `Russian actor` versus `Ukrainian actor`.[^7][^3]
- `single-source`: only one pool or one source supports it.[^3]
- `unknown`: extraction too weak or evidence too noisy.[^2]

The result is a deterministic normalization layer that an LLM can help populate, but the promotion of facts should stay rule-based and inspectable. That is the part users will trust.[^1][^3]

Would you like the next step to be a concrete PostgreSQL schema and FastAPI endpoint design for this pipeline?
<span style="display:none">[^10][^11][^12][^13][^14][^15][^9]</span>

<div align="center">⁂</div>

[^1]: https://aclanthology.org/2023.findings-emnlp.439/

[^2]: https://aclanthology.org/2024.findings-acl.114/

[^3]: https://mediahelpingmedia.org/quick-guides/attribution-in-journalism/

[^4]: https://arxiv.org/abs/2406.16021

[^5]: https://openreview.net/forum?id=bxltAqTJe2

[^6]: https://ceur-ws.org/Vol-4038/paper_83.pdf

[^7]: https://global.oup.com/us/companion.websites/9780190200886/student/chapter10/gline/level/

[^8]: https://ballotpedia.org/The_methodologies_of_fact-checking

[^9]: https://arxiv.org/abs/2310.14338

[^10]: https://elib.uni-stuttgart.de/bitstreams/53f43fc2-dd29-45c1-9d7a-5034ec49e4e5/download

[^11]: https://github.com/gkdey17cse/ClaimNormalization

[^12]: https://towardsdatascience.com/building-fact-checking-systems-catching-repeating-false-claims-before-they-spread/

[^13]: https://www.semanticscholar.org/paper/Harvesting-Events-from-Multiple-Sources:-Towards-a-Gao-Meng/15ade7969f0173f14ed6dbf54b3c695845e66ab8

[^14]: https://www.scribd.com/document/872133910/Attribution

[^15]: https://www.themoonlight.io/en/review/harvesting-events-from-multiple-sources-towards-a-cross-document-event-extraction-paradigm

