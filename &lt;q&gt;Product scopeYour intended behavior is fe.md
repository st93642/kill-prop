<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>
```
# <q>Product scopeYour intended behavior is feasible if you define the output carefully: the app should not claim to “remove propaganda” in an absolute sense, because journalism standards focus on verifying sources, cross-referencing information, correcting inaccuracies, and distinguishing fact from opinion rather than declaring one side perfectly objective</q> What i mean is that if in western pool is mentioned "hit by russian drone" and same fact is mentioned in eastern pool as "hit by ukrainian drone" - resulting display should be just "hit by drone"
```

Yes — that is a valid and useful design choice, but it should be implemented as **claim decomposition with uncertainty-preserving abstraction**, not as naive averaging of two contradictory sentences.[^1][^2][^3]

In your example, if both pools agree an object was struck and disagree only on the actor, the system should split the report into separate claim slots such as: “an impact occurred,” “the target/location,” “the time,” and “the alleged responsible party.” The display can then show the shared minimum fact as “hit by a drone” while moving authorship into a disputed attribution field like “responsibility contested across sources.”[^4][^3][^1]

## Correct model

This is closer to “finding the greatest common verified denominator” of conflicting reports. Journalism attribution guidance supports making controversial or uncertain parts explicit, because when a point is disputed, the safe factual statement is often the narrower one that all credible reports support, while the disputed element remains attributed rather than asserted as fact.[^5][^2][^4]

So for your app, the internal representation should not store one sentence per event. It should store a structured event graph with fields like `event_type`, `object_affected`, `location`, `time`, `weapon_type`, `claimed_actor`, `source_support`, and `confidence`, because contradiction often exists only in one field rather than the whole event.[^3][^6][^1]

## Example logic

For the pair “hit by Russian drone” versus “hit by Ukrainian drone,” the overlap is not the entire sentence but the predicate “hit by drone.” The system should therefore emit three layers: a normalized fact, a disputed detail, and provenance, for example: “A site was hit by a drone” as the fact, “sources disagree on whose drone it was” as the dispute, and then the source-backed claims beneath it.[^2][^4][^3]

That approach is stronger than declaring one side wrong too early, because attribution standards emphasize telling readers where contested claims come from so they can judge reliability for themselves. It also prevents the app from laundering speculation into certainty by forcing every contested field to remain visibly contested.[^5][^4][^2]

## Implementation rule

You can formalize this with a field-level consensus rule. If a field is supported across multiple independent sources with compatible values, promote it to the fact layer; if a field has conflicting values across pools, collapse upward to the last non-controversial abstraction and mark the field as disputed.[^7][^1][^3]

In practice, that means:


| Input field | Western pool | Eastern pool | User display |
| :-- | :-- | :-- | :-- |
| event type | strike [^3] | strike [^3] | strike [^3] |
| object type | drone [^3] | drone [^3] | drone [^3] |
| actor | Russian [^3] | Ukrainian [^3] | contested attribution [^4][^2] |

This is essentially claim normalization, where raw statements are converted into concise normalized claims suitable for later verification and comparison.[^3][^7]

## Guardrails

The important guardrail is that abstraction must not erase meaningful uncertainty. If one source says “drone” and another says “missile,” you may need to collapse further to “aerial strike” or even “attack reported,” depending on evidence quality, rather than force “drone” just because it appears in one sentence. Likewise, if only one pool reports the event at all, the app should not produce a stripped-down fact; it should show “reported by one source pool, awaiting corroboration.”[^1][^2]

A good UI label set for this is: **Confirmed facts**, **Disputed details**, and **Source claims**. That gives you exactly the behavior you described while staying transparent about what was preserved, what was collapsed, and what remains unresolved.[^4][^2]

Would you like me to write the exact normalization algorithm and database schema for this field-by-field consensus model?
<span style="display:none">[^10][^11][^12][^13][^14][^15][^8][^9]</span>

<div align="center">⁂</div>

[^1]: https://pressbooks.montgomerycollege.edu/aiethics/chapter/module-4-source-cross-referencing-and-fact-checking/

[^2]: https://ethics.journalists.org/topics/sources-reliability-and-attribution/

[^3]: https://zenodo.org/records/19092304

[^4]: https://en.wikinews.org/wiki/Wikinews:Attribution

[^5]: https://www.npr.org/sections/npr-training/2025/05/28/g-s1-64301/if-you-want-people-to-trust-your-reporting-attribute-your-sources

[^6]: https://www.microsoft.com/en-us/research/blog/claimify-extracting-high-quality-claims-from-language-model-outputs/

[^7]: https://aclanthology.org/2025.acl-long.348.pdf

[^8]: https://cursa.app/en/page/journalism-basics-attribution-fairness-and-avoiding-common-reporting-errors

[^9]: https://www.thenewsmanual.net/Manuals Volume 1/volume1_09.htm

[^10]: https://opentext.ku.edu/becredible/chapter/attribute-all-sources/

[^11]: https://huggingface.co/papers?q=fact-checked+claims

[^12]: https://arxiv.org/html/2510.08224v2

[^13]: https://michaelcarbonara.com/attribution-political-writing-according-to-done-right/

[^14]: https://www.red-gate.com/simple-talk/blogs/the-myth-of-over-normalization/

[^15]: https://mediahelpingmedia.org/basics/referencing-attribution-and-plagiarism/

