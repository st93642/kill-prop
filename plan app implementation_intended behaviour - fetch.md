<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# plan app implementation

intended behaviour - fetching latest news from different pools , western, eastern (russia), sources to be fetchable with online tools, then analyze those news and remove different propaganda assumptions, leaving only facts from all sources to display to user

Build it as a **source-triangulation news web app**, not as a generic “truth detector.” The core behavior should be: ingest articles from ideologically and geographically different pools, break each story into claims, score each claim by evidence strength and cross-source corroboration, then show users a fact-first event brief plus a clearly separated “disputed framing” layer.[^1][^2][^3]

## Product scope

Your intended behavior is feasible if you define the output carefully: the app should not claim to “remove propaganda” in an absolute sense, because journalism standards focus on verifying sources, cross-referencing information, correcting inaccuracies, and distinguishing fact from opinion rather than declaring one side perfectly objective. A better promise is: “We compare reporting across Western and Russian-source pools, identify overlapping verified facts, flag unsupported or emotionally loaded claims, and expose where framing diverges.”[^4][^2][^3]

For the interface, treat it as a compact dashboard-style web app with a sidebar, top filters, and a main evidence panel, because data-dense apps work best when users can move from KPIs to trends to details without oversized marketing-style UI. The app should let users open one event, inspect claim-by-claim evidence, and see which outlets independently support, contradict, or merely speculate about each statement.[^2][^1]

## System design

Use a pipeline with six stages: source intake, article normalization, event clustering, claim extraction, evidence scoring, and user presentation. For source intake, keep separate pools such as Western mainstream, Russian state-aligned, Russian independent/exile, and neutral wire or primary-document sources, because cross-referencing works better when source provenance is explicit rather than blended too early.[^3][^1][^2]

For fetching, connect to news APIs that support country- and source-based retrieval, since Russian-source coverage is available through country filters like `ru` in some APIs and through dedicated feeds such as Google News Russia endpoints. Persist raw article metadata, canonical URL, timestamp, author, language, source country, source class, and full text snapshot, because later fact scoring depends on preserving what was actually published at retrieval time.[^5][^6][^7][^2][^3]

## Fact extraction

Do not summarize whole articles first. Instead, cluster articles into the same event, then extract atomic claims such as “an explosion occurred in city X,” “official Y said Z,” or “the ministry released a document,” because cross-source verification works at the claim level, not at the article level.[^1][^2]

Each claim should be labeled into one of four buckets: verified fact, attributed statement, inference, or opinionated framing. A practical heuristic is that claims tied to primary evidence, official documents, direct on-record quotes, timestamps, geolocation, images, or multiple independent reports receive higher confidence, while adjectives, sweeping generalizations, anonymous assertions, and emotionally triggering language are pushed into framing or low-confidence attribution layers.[^8][^9][^4][^2][^3]

You should also maintain a propaganda-risk detector, but keep it narrow and auditable. Good signals are loaded adjectives, dehumanizing language, certainty without evidence, “us vs them” formulations, and claims repeated by only one ideological pool with no corroboration elsewhere. The detector should never delete content silently; it should mark phrases as framing and keep the original text visible for inspection.[^4][^3]

## Ranking logic

Your scoring model should reward corroboration quality rather than outlet popularity alone. A strong event brief is built from claims that are supported by multiple independent sources, especially when those sources differ in geography or editorial alignment, and by primary-source material when available.[^2][^3]

A simple v1 score can be:

$$
\text{claim score} = 0.35(\text{independent corroboration}) + 0.25(\text{primary evidence}) + 0.15(\text{source reliability prior}) + 0.15(\text{specificity}) - 0.10(\text{loaded framing})
$$

This matches your product goal better than a single “bias score,” because journalism guidance emphasizes accuracy, attribution, multiple perspectives, and fact/opinion separation. You can also incorporate external source-quality priors from media-rating organizations, since some services explicitly rate news sources for reliability and political bias.[^10][^3][^2]

## User experience

The main screen should open on an event feed, not an article feed. Each event card can show the event title, number of corroborating sources, source-pool spread, last update time, and confidence level, which aligns with dashboard guidance that users should see status, freshness, and structure immediately.[^1]

Inside an event page, split the layout into three panes: “Facts agreed across sources,” “Claims still disputed,” and “Framing differences.” That separation is critical, because ethical journalism standards require differentiating fact and opinion, and users need to see both the stable core and the contested edges without them being mixed together.[^3][^8][^1]

A good event row might read like this: “Bridge closure confirmed by 5 sources across 3 pools; cause disputed; casualty figures inconsistent.” That style is short, scannable, and consistent with compact dashboard copy recommendations.[^1]

## Implementation phases

For v1, focus on English and Russian only, ingest maybe 20 to 50 sources, and support a few domains where source disagreement is common, such as geopolitics, sanctions, elections, and military incidents. Keep humans in the loop by adding an internal review console where you can inspect clustering mistakes, approve source classifications, and override claim labels, because fully automated bias removal will make visible errors early on.[^6][^7][^5][^2][^3]

For v2, add translation alignment, quote-to-source tracing, media forensics hooks, and source-network graphs showing how a claim propagated across pools. For v3, add user controls for “strict facts only,” “include attributed official claims,” and “show full framing comparison,” because different users want different thresholds for ambiguity.[^2][^3][^1]

A practical initial stack is a web app with a compact dashboard UI, a retrieval service, a document store for raw articles, a vector or search index for clustering, an LLM layer for claim extraction with strict schemas, and a rules engine for evidence scoring. Would you like me to turn this into a concrete technical architecture with database schema, API routes, and a first MVP backlog?[^1]
<span style="display:none">[^11][^12][^13][^14][^15]</span>

<div align="center">⁂</div>

[^1]: https://dl.acm.org/doi/10.1145/2209310.2209311

[^2]: https://en.wikiversity.org/wiki/Evaluating_Journalism_Standards/Ensuring_Journalism_Accuracy

[^3]: https://www.nuj.org.uk/about-us/rules-and-guidance/code-of-conduct.html

[^4]: https://www.facingfacts.eu/how-to-mitigate-bias-when-reading-the-news/

[^5]: https://worldnewsapi.com/docs/news-sources/russia-news-api/

[^6]: https://gnews.io/top-headlines-example/russia-news-api

[^7]: https://newsapi.org/s/google-news-ru-api

[^8]: https://pressombudsman.ie/code-of-practice/

[^9]: https://ethicsandjournalism.org/resources/best-practices/best-practices-anonymous-sources/

[^10]: https://adfontesmedia.com/methodology/

[^11]: https://zenodo.org/records/14806065

[^12]: https://nclab.kaist.ac.kr/files/papers/Conference/WS11.pdf

[^13]: https://www.semanticscholar.org/paper/A-Computational-Framework-for-Media-Bias-Mitigation-Park-Kang/ba66ba40df589554adf800074758f46a43b7ed76

[^14]: https://kangseungwoo.wordpress.com/wp-content/uploads/2018/01/201205-tiis12a-computational-framework-for-media-bias-mitigation.pdf

[^15]: https://en.wikipedia.org/wiki/Media_bias

