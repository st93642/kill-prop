"""Stage 1: Source Intake - Ingest articles from different source pools.

In production, this connects to news APIs. For MVP, we use a seeded dataset
and a mock fetch mechanism that demonstrates the full pipeline.
"""

from __future__ import annotations

import os
import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

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
        "canonical_url": "",
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
        "canonical_url": "",
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
        "canonical_url": "",
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
        "canonical_url": "",
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
        "canonical_url": "",
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
    # ── Second event: Oil refinery explosion ──────────────────────────
    {
        "canonical_url": "",
        "title": "Massive explosion at oil refinery in Ryazan region",
        "author": "Sarah Field",
        "published_at": datetime(2026, 6, 5, 14, 0),
        "source_name": "Western Herald",
        "source_pool": SourcePool.WESTERN_MAINSTREAM,
        "source_country": "US",
        "language": "en",
        "full_text": (
            "A massive explosion rocked an oil refinery in the Ryazan region on Thursday afternoon, "
            "sending thick black smoke into the sky visible from miles away. Emergency services "
            "rushed to the scene as fires spread across multiple processing units. Regional governor "
            "Pavel Malkov confirmed the incident, stating that preliminary assessments suggest "
            "a drone attack may have been responsible. At least two firefighting crews were deployed. "
            "The refinery processes approximately 17 million tons of crude oil annually and is "
            "a critical piece of energy infrastructure for central Russia."
        ),
        "topic_tags": ["energy", "military", "infrastructure", "economy"],
    },
    {
        "canonical_url": "",
        "title": "Fire at Ryazan refinery caused by technical malfunction, authorities say",
        "author": "Dmitry Petrov",
        "published_at": datetime(2026, 6, 5, 14, 45),
        "source_name": "Eastern Times",
        "source_pool": SourcePool.RUSSIAN_STATE,
        "source_country": "RU",
        "language": "en",
        "full_text": (
            "A fire broke out at an oil processing facility in the Ryazan region on Thursday, "
            "which emergency services have since brought under control. Regional authorities "
            "stated that preliminary investigation points to a technical malfunction in one "
            "of the processing units, not an external attack. The Ministry of Emergency Situations "
            "confirmed that no casualties have been reported and that the refinery's output "
            "will not be significantly affected. Production is expected to resume within 48 hours."
        ),
        "topic_tags": ["energy", "infrastructure", "economy"],
    },
    {
        "canonical_url": "",
        "title": "Ryazan refinery fire raises questions about cause as both sides offer conflicting accounts",
        "author": "Neutral Reporter",
        "published_at": datetime(2026, 6, 5, 15, 30),
        "source_name": "Wire Service",
        "source_pool": SourcePool.NEUTRAL_WIRE,
        "source_country": "CH",
        "language": "en",
        "full_text": (
            "A fire at an oil refinery in Ryazan, approximately 200km southeast of Moscow, "
            "was reported Thursday afternoon. Satellite data from NASA FIRMS showed thermal "
            "anomalies consistent with a large industrial fire beginning around 13:45 local time. "
            "Western intelligence sources have suggested the incident may be linked to a long-range "
            "drone operation, while Russian authorities maintain it was a technical fault. "
            "The refinery is a major supplier of diesel and jet fuel to the Russian military. "
            "Independent verification of the cause remains impossible at this stage."
        ),
        "topic_tags": ["energy", "military", "infrastructure"],
    },
    # ── Third event: Ceasefire negotiations ──────────────────────────
    {
        "canonical_url": "",
        "title": "Ukraine and Russia agree to preliminary ceasefire framework in Istanbul talks",
        "author": "James Diplomat",
        "published_at": datetime(2026, 6, 5, 10, 0),
        "source_name": "Western Herald",
        "source_pool": SourcePool.WESTERN_MAINSTREAM,
        "source_country": "US",
        "language": "en",
        "full_text": (
            "Ukrainian and Russian delegations have agreed to a preliminary framework for a "
            "30-day ceasefire during talks hosted by Turkey in Istanbul, according to diplomats "
            "familiar with the negotiations. The proposed framework includes a halt to long-range "
            "strikes on energy infrastructure and the establishment of humanitarian corridors "
            "in contested regions. Turkish Foreign Minister Hakan Fidan praised both sides "
            "for what he called 'constructive engagement.' The United Nations Secretary-General "
            "welcomed the development but cautioned that 'implementation remains the true test.'"
        ),
        "topic_tags": ["diplomacy", "geopolitics", "peace"],
    },
    {
        "canonical_url": "",
        "title": "Russia agrees to consider ceasefire proposal, insists on security guarantees",
        "author": "Sergei Kremlin",
        "published_at": datetime(2026, 6, 5, 10, 30),
        "source_name": "Eastern Times",
        "source_pool": SourcePool.RUSSIAN_STATE,
        "source_country": "RU",
        "language": "en",
        "full_text": (
            "The Russian delegation in Istanbul has agreed to consider a temporary ceasefire "
            "proposal but emphasized that any agreement must include legally binding security "
            "guarantees regarding NATO expansion and the status of Russian-speaking populations "
            "in eastern Ukraine. Foreign Ministry spokeswoman Maria Zakharova stated that "
            "Russia remains open to dialogue but will not accept 'ultimatums disguised as proposals.' "
            "The talks are expected to continue through the weekend with technical working groups "
            "addressing specific provisions."
        ),
        "topic_tags": ["diplomacy", "geopolitics", "peace"],
    },
    {
        "canonical_url": "",
        "title": "China welcomes Istanbul ceasefire initiative, offers to host follow-up talks",
        "author": "Wang Correspondent",
        "published_at": datetime(2026, 6, 5, 11, 0),
        "source_name": "Xinhua",
        "source_pool": SourcePool.CHINESE_STATE,
        "source_country": "CN",
        "language": "en",
        "full_text": (
            "China has welcomed the ceasefire framework agreed upon in Istanbul and offered "
            "to host a follow-up round of negotiations in Beijing. Foreign Ministry spokesperson "
            "said China supports all efforts conducive to a political settlement of the Ukraine "
            "crisis. Beijing's 12-point peace plan, released earlier this year, has been "
            "referenced by several delegations as a potential basis for broader discussions. "
            "China reiterated its call for respecting the sovereignty and territorial integrity "
            "of all countries."
        ),
        "topic_tags": ["diplomacy", "geopolitics", "peace"],
    },
    # ── Fourth event: Grain deal collapse ────────────────────────────
    {
        "canonical_url": "",
        "title": "Black Sea grain deal collapses as Russia withdraws, wheat prices surge",
        "author": "Emma Trade",
        "published_at": datetime(2026, 6, 4, 22, 0),
        "source_name": "Western Herald",
        "source_pool": SourcePool.WESTERN_MAINSTREAM,
        "source_country": "US",
        "language": "en",
        "full_text": (
            "The Black Sea Grain Initiative has collapsed after Russia formally notified "
            "the United Nations and Turkey of its withdrawal from the agreement, effective "
            "immediately. Wheat futures surged 6.5% on the Chicago Board of Trade following "
            "the announcement. The UN Secretary-General expressed 'deep disappointment' and "
            "warned that the collapse threatens food security for millions in Africa and the "
            "Middle East. Ukraine's agricultural exports through the corridor had reached "
            "33 million metric tons since the deal's inception."
        ),
        "topic_tags": ["economy", "diplomacy", "food_security", "trade"],
    },
    {
        "canonical_url": "",
        "title": "Russia exits grain deal citing Western failure to lift sanctions on agricultural exports",
        "author": "Olga Ministry",
        "published_at": datetime(2026, 6, 4, 22, 30),
        "source_name": "Eastern Times",
        "source_pool": SourcePool.RUSSIAN_STATE,
        "source_country": "RU",
        "language": "en",
        "full_text": (
            "Russia has suspended its participation in the Black Sea grain deal, citing "
            "the West's failure to fulfill its obligations under the agreement. The Foreign "
            "Ministry stated that restrictions on Russian agricultural exports, including "
            "insurance, logistics, and payment processing, remain in place despite promises "
            "made when the deal was signed. Russia indicated it would consider rejoining "
            "only when 'concrete results' are achieved on these issues. Domestic grain "
            "exports through alternative routes remain unaffected."
        ),
        "topic_tags": ["economy", "diplomacy", "food_security", "trade"],
    },
    {
        "canonical_url": "",
        "title": "Grain deal collapse: What it means for global food prices and who is most affected",
        "author": "Neutral Reporter",
        "published_at": datetime(2026, 6, 5, 0, 0),
        "source_name": "Wire Service",
        "source_pool": SourcePool.NEUTRAL_WIRE,
        "source_country": "CH",
        "language": "en",
        "full_text": (
            "The collapse of the Black Sea Grain Initiative threatens to push global food "
            "prices to levels not seen since the 2022 crisis. Countries most dependent on "
            "Ukrainian grain imports — including Egypt, Bangladesh, and Somalia — face "
            "immediate price pressures. The World Food Programme, which sourced 80% of its "
            "wheat from Ukraine under the deal, must now find alternative suppliers at "
            "higher cost. Analysts warn that the timing is particularly dangerous as several "
            "regions enter their lean season before harvest."
        ),
        "topic_tags": ["economy", "food_security", "trade", "analysis"],
    },
    # --- Middle Eastern pool ---
    {
        "canonical_url": "",
        "title": "Iran nuclear talks stall as US demands halt to enrichment",
        "author": "Hassan Mousavi",
        "published_at": datetime(2026, 6, 5, 10, 0),
        "source_name": "Middle East Monitor",
        "source_pool": SourcePool.MIDDLE_EASTERN,
        "source_country": "QA",
        "language": "en",
        "full_text": (
            "Negotiations between Iran and the United States over Tehran's nuclear program "
            "have stalled again, with Washington insisting on a complete halt to uranium "
            "enrichment. Iranian officials maintain their enrichment activities are for "
            "peaceful purposes and protected under the Nuclear Non-Proliferation Treaty. "
            "The IAEA has been unable to inspect Iranian facilities since the US-Israeli "
            "military strikes began in February. Regional analysts warn that continued "
            "deadlock risks further escalation in the Persian Gulf, where maritime traffic "
            "through the Strait of Hormuz remains heavily disrupted."
        ),
        "topic_tags": ["geopolitics", "nuclear", "diplomacy", "sanctions"],
    },
    # --- Latin American pool ---
    {
        "canonical_url": "",
        "title": "Venezuela seeks Indian investment to revive oil sector",
        "author": "Carlos Mendoza",
        "published_at": datetime(2026, 6, 5, 9, 0),
        "source_name": "Telesur English",
        "source_pool": SourcePool.LATIN_AMERICAN,
        "source_country": "VE",
        "language": "en",
        "full_text": (
            "Acting Venezuelan President Delcy Rodriguez is visiting New Delhi this week "
            "to negotiate Indian participation in Venezuela's oil and gas sector. Venezuela "
            "holds the world's largest proven oil reserves but production has been crippled "
            "by US sanctions and mismanagement. India, the world's third-largest oil importer, "
            "is diversifying its energy sources following disruptions in the Middle East "
            "caused by the US-Iran war. Indian refiners resumed Venezuelan crude imports "
            "in February after Washington eased some sanctions. The deal could see Indian "
            "companies invest up to $1.5 billion in the Orinoco Belt."
        ),
        "topic_tags": ["economy", "energy", "trade", "sanctions"],
    },
    # --- African pool ---
    {
        "canonical_url": "",
        "title": "Sahel violence displaces 4 million as militant groups expand reach",
        "author": "Amina Diallo",
        "published_at": datetime(2026, 6, 5, 8, 0),
        "source_name": "African News Agency",
        "source_pool": SourcePool.AFRICAN,
        "source_country": "SN",
        "language": "en",
        "full_text": (
            "More than 4 million people have been displaced across the Sahel region as "
            "Islamist militant groups expand their reach from Mali into coastal West African "
            "states. The Islamic State West Africa Province (ISWAP) has eclipsed Boko Haram "
            "as the dominant jihadist force in the Lake Chad basin. Military juntas in Mali, "
            "Burkina Faso, and Niger have expelled French forces and turned to Russian "
            "security assistance, reshaping the geopolitical landscape. The UN warns that "
            "the humanitarian crisis is deepening, with food insecurity affecting over "
            "25 million people across the region."
        ),
        "topic_tags": ["military", "conflict", "terrorism", "food_security"],
    },
    # --- South Asian pool ---
    {
        "canonical_url": "",
        "title": "India and China hold border talks amid arms race concerns",
        "author": "Priya Sharma",
        "published_at": datetime(2026, 6, 5, 7, 0),
        "source_name": "South Asian Monitor",
        "source_pool": SourcePool.SOUTH_ASIAN,
        "source_country": "IN",
        "language": "en",
        "full_text": (
            "Indian and Chinese military commanders held a new round of border talks this week "
            "as both nations continue to modernize their armed forces. Pakistan's recent "
            "acquisition of 40 Chinese J-35 fifth-generation stealth fighters has intensified "
            "the regional arms race, with India accelerating its own Advanced Medium Combat "
            "Aircraft (AMCA) program. Russia has offered India its Su-57 stealth fighter as "
            "an interim solution. Meanwhile, India-Russia trade has surged to nearly $69 "
            "billion annually, driven largely by discounted Russian oil purchases that have "
            "drawn criticism from Washington."
        ),
        "topic_tags": ["geopolitics", "military", "trade", "defense"],
    },
    # --- East Asian pool ---
    {
        "canonical_url": "",
        "title": "North Korea unveils new nuclear facility ahead of Xi visit",
        "author": "Kim Soo-jin",
        "published_at": datetime(2026, 6, 5, 6, 0),
        "source_name": "Asia Pacific Report",
        "source_pool": SourcePool.EAST_ASIAN,
        "source_country": "KR",
        "language": "en",
        "full_text": (
            "North Korea has unveiled a new facility to produce nuclear bomb fuels, just "
            "days before Chinese President Xi Jinping's scheduled state visit to Pyongyang. "
            "The visit, Xi's first to North Korea since 2019, comes amid deepening "
            "Pyongyang-Moscow ties and heightened tensions on the Korean Peninsula. "
            "North Korean leader Kim Jong Un has vowed an 'exponential' increase in nuclear "
            "forces, having conducted eight missile tests already in 2026. South Korea and "
            "Japan have responded by increasing defense cooperation with the United States, "
            "while China warns against further militarization of the region."
        ),
        "topic_tags": ["nuclear", "geopolitics", "military", "diplomacy"],
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


# Propaganda-detection lexicon. Lowercased; matched as substrings against the
# lowercased sentence text. Grouped so the cross-pool analysis can later cite
# which lexicon a flag came from.
PROPAGANDA_LEXICON: dict[str, list[str]] = {
    "loaded_language": [
        # Generic emotive / dehumanizing terms
        "terror", "terrorist", "aggressor", "fascist", "nazi", "neo-nazi",
        "liberation", "liberated", "puppet", "regime", "junta",
        "genocide", "ethnic cleansing", "crusade", "barbaric", "savage",
        "extermination", "annihilation", "crush", "destroy",
        "heroic", "martyr", "martyrdom",
        # Russian-state framing (Latin + Cyrillic)
        "special military operation", "special operation",
        "denazification", "demilitarization",
        "kyiv regime", "kiev regime", "kyiv junta",
        "zio", "russophobic", "russophobia",
        "western-backed", "washington-backed",
        "nazifier", "bandera",
        "киевский режим", "киевской хунтой", "хунта",
        # Russian has six noun cases; endings vary, so we match on the
        # invariant leading stem of each key word independently. Matching the
        # three stems together (in any order) catches "специальная военная
        # операция" and all its grammatical case variants.
        "спецопераци", "специальн", "военн операци", "денацификац",
        "демилитаризац",
        "нацист", "нацистов", "бандеровц", "русофоб",
        # The СВО / SVO abbreviation, the Kremlin's shorthand for the invasion.
        # Surrounded by spaces to avoid colliding with unrelated Cyrillic text.
        " сво ",
        # Western / Ukrainian framing of Russia
        "war criminal", "war criminals", "butcher",
        "putin loyalist", "kremlin stooge", "kremlin propagandist",
        "orcs", "ruscism", "racism", "terror state", "terrorist state",
        # Chinese-state framing
        "western hegemony", "containment", "smear campaign",
        "separatist", "splittist", "anti-china forces",
    ],
    "us_vs_them": [
        # Explicit in-group / out-group phrasings
        "us vs them", "us and them",
        "the free world", "axis of evil", "empire of evil",
        "coalition of the willing", "civilized world",
        "barbaric enemy", "mortal enemy", "sworn enemy",
        "our values", "their aggression",
        # Russian-state narrative us-vs-them
        "collective west", "anglo-saxons", "англо-сакс",
        "western elites", "western curators",
        # Dehumanization
        "subhuman", "cockroaches", "vermin", "orcs",
    ],
    "certainty_without_evidence": [
        # Absolute quantifiers used to assert without backing
        "always ", "never ", "everyone knows", "everybody knows",
        "it is obvious", "it's obvious", "clearly", "without a doubt",
        "undeniable", "irrefutable", "definitely", "absolutely",
        "всем известно", "очевидно", "безусловно", "несомненно",
    ],
    "whataboutism": [
        "what about", "whataboutism",
        "but america", "but the us", "but washington",
        "and you are lynching negroes", "а у вас негров линчуют",
    ],
}


def _detect_propaganda_signals(sentence_lower: str) -> list[str]:
    """Return the propaganda flag IDs triggered by *sentence_lower*.

    *sentence_lower* must already be lowercased by the caller.
    """
    signals: list[str] = []
    for flag_id, terms in PROPAGANDA_LEXICON.items():
        for term in terms:
            # Wrap latin/word terms in word boundaries when possible so that
            # 'crush' does not match 'crushing debt' spuriously, but skip
            # boundaries for multi-word or non-ascii phrases.
            if " " in term or not term[0].isascii():
                if term in sentence_lower:
                    signals.append(flag_id)
                    break
            else:
                if re.search(rf"\b{re.escape(term)}\b", sentence_lower):
                    signals.append(flag_id)
                    break
    return signals


def _is_non_claim_sentence(sentence: str) -> bool:
    """Heuristic: should this sentence be skipped entirely as a non-claim?

    Catches rhetorical questions and reader-facing questions that do not
    assert anything. Length filtering is handled separately by the caller.
    """
    stripped = sentence.strip()
    # Questions are not assertions
    if stripped.endswith("?"):
        return True
    # Direct quotes of a single speaker with no framing are still useful
    # (they often carry attribution), so we keep them.
    return False


def _extract_claims_from_article(article: Article) -> list[Claim]:
    """Rule-based claim extraction from article text.

    Splits into sentences, drops obvious non-claims (questions, very short
    fragments), then classifies each remaining sentence into one of the four
    claim buckets using attribution/hedging/framing cues. Also stamps
    evidence indicators and propaganda flags.
    """
    claims_list: list[Claim] = []
    text = article.full_text
    sentences = re.split(r'(?<=[.!?])\s+', text)

    # Hedge / speculation vocabulary → INFERENCE bucket
    hedge_words = {
        "may", "might", "could", "likely", "possibly", "perhaps", "unclear",
        "appears", "seems", "allegedly", "reportedly", "presumably",
        "purportedly", "suspected", "believed to",
    }
    # Editorial / framing vocabulary → OPINIONATED_FRAMING bucket
    framing_words = {
        "escalating", "escalation", "fog of war", "pattern of",
        "raises questions", "raises the question", "shows the difficulty",
        "fits a pattern", "highlights the", "underscores", "signals",
        "marks a turning point", "represents a shift",
    }

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence or len(sentence) < 20:
            continue
        if _is_non_claim_sentence(sentence):
            continue

        sentence_lower = sentence.lower()

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
            r"reported\b", r"attributed\b", r"announced\b", r"noted\b",
        ]
        attribution_match = None
        for phrase in attribution_phrases:
            m = re.search(phrase, sentence, re.IGNORECASE)
            if m:
                attribution_match = m.group(0)
                break

        # --- Bucket classification --------------------------------------
        # Order matters: framing > attribution > inference > fact. A sentence
        # can be both attributed and loaded; framing is the stronger signal
        # because it tells the user "treat with care" regardless of source.
        words = set(re.findall(r"\b[\w']+\b", sentence_lower))

        if framing_words & words or any(w in sentence_lower for w in framing_words):
            claim.bucket = ClaimBucket.OPINIONATED_FRAMING
        elif attribution_match:
            claim.bucket = ClaimBucket.ATTRIBUTED_STATEMENT
            claim.attribution.status = "on_record"
            claim.attribution.phrase = attribution_match
            speaker_match = re.search(
                r"(?:according to\s+)?(\w+\s+\w+)(?:\s+(?:said|stated|confirmed|reported|announced))?",
                sentence, re.IGNORECASE
            )
            if speaker_match:
                claim.attribution.speaker = speaker_match.group(1)
        elif hedge_words & words:
            claim.bucket = ClaimBucket.INFERENCE
        else:
            # Default is now INFERENCE (uncorroborated assertion) rather than
            # VERIFIED_FACT — a sentence is only a verified fact once the
            # consensus engine has cross-pool corroboration. This avoids
            # inflating the count of supposedly high-confidence claims.
            claim.bucket = ClaimBucket.INFERENCE

        # --- Evidence indicators ----------------------------------------
        claim.evidence.quote = '"' in sentence or "said" in sentence_lower
        claim.evidence.official_statement = any(
            w in sentence_lower for w in [
                "official", "ministry", "defense ministry", "regional",
                "government", "spokesperson", "spokesman", "spokeswoman",
                "minster", "department of", "press secretary", "ministry of",
            ]
        )
        claim.evidence.eyewitness = any(
            w in sentence_lower for w in ["eyewitness", "witness", "i saw", "we saw"]
        )
        claim.evidence.satellite_imagery = any(
            w in sentence_lower for w in [
                "satellite", "imagery", "satellite image", "satellite data",
                "remote sensing", "nasa firms",
            ]
        )
        claim.evidence.timestamp_geolocation = bool(re.search(r'\d{1,2}:\d{2}', sentence))

        # --- Propaganda signals -----------------------------------------
        claim.propaganda_flags = _detect_propaganda_signals(sentence_lower)

        claims_list.append(claim)

    return claims_list


def ingest_articles(seed: bool = True, days_back: int = 1) -> list[Article]:
    """Ingest articles from source pools.
    
    Args:
        seed: If True, load seed data for MVP demonstration.
              In production, this would call news APIs instead.
        days_back: Only return articles from this many days back (default 1 = today).
    
    Returns:
        List of ingested articles with extracted claims.
    """
    if seed:
        from backend.pipeline.normalization import normalize_claims_batch

        cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days_back)

        # Seed articles are authored with fixed past timestamps for reproducibility
        # of the relative spacing between articles (which is what clustering needs).
        # Shift the whole batch forward so the newest seed lands at "now"; this
        # keeps the demo pipeline populated regardless of the real wall clock,
        # while preserving the intra-batch time deltas the clusterer relies on.
        seed_times = [s.get("published_at") for s in SEED_ARTICLES if s.get("published_at")]
        offset = None
        if seed_times:
            newest_seed = max(seed_times)
            now_naive = datetime.now(timezone.utc).replace(tzinfo=None)
            offset = now_naive - newest_seed

        ingested = 0
        for seed_data in SEED_ARTICLES:
            # Shift published_at forward so the newest seed article is "now".
            pub = seed_data.get("published_at")
            if pub and offset is not None:
                seed_data = {**seed_data, "published_at": pub + offset}

            # Skip articles older than the cutoff (after shifting, all seeds
            # should fall inside the window, but guard anyway).
            pub = seed_data.get("published_at")
            if pub and pub < cutoff:
                continue

            # Skip non-Europe/Russia articles (geo-filter)
            title = seed_data.get("title", "")
            full_text = seed_data.get("full_text", "")
            combined = (title + " " + full_text).lower()
            if not _has_europe_russia_geo(combined):
                continue

            article = Article(**seed_data)
            
            # Apply translation if needed
            if article.language != "en":
                article.title = translate_text(article.title, article.language)
                article.full_text = translate_text(article.full_text, article.language)
            
            if os.getenv("USE_LLM", "false").lower() == "true":
                from backend.pipeline.llm_extraction import extract_claims_llm
                claims = extract_claims_llm(article)
                if not claims:
                    claims = _extract_claims_from_article(article)
            else:
                claims = _extract_claims_from_article(article)

            # Normalize claims immediately so arguments are populated
            anchor = (
                article.published_at.strftime("%Y-%m-%d")
                if article.published_at else None
            )
            claims = normalize_claims_batch(claims, anchor_date=anchor)
            article.claims = claims
            articles_store[article.article_id] = article
            for c in claims:
                claims_store[c.claim_id] = c
            ingested += 1

        return list(articles_store.values())

    # Production: fetch from real news APIs or RSS feeds
    api_key = os.getenv("NEWSAPI_KEY", "")
    articles: list[Article] = []
    if api_key:
        articles = _fetch_from_newsapi(days_back=days_back)
    if not articles:
        articles = _fetch_rss_feeds(days_back=days_back)
    return articles


def fetch_article(article_id: str) -> Article | None:
    """Fetch a single article by ID."""
    return articles_store.get(article_id)


# ── Real News API Integration ────────────────────────────────────────
# Sources mapped to NewsAPI source IDs, country codes, and RSS feeds
# Free tier: 100 req/day for NewsAPI. RSS feeds are unlimited.

# Known working public RSS feeds (free, no API key needed).
# Each feed URL should appear in exactly ONE pool as primary=True so we fetch
# each source only once. Other pools that legitimately want to track the same
# outlet use primary=False (they will be skipped during RSS fetching).
RSS_FEEDS: dict[str, list[dict]] = {
    # Western mainstream — US/UK/European establishment media
    "western_mainstream": [
        {"url": "https://feeds.bbci.co.uk/news/world/rss.xml", "source": "BBC News", "primary": True},
        {"url": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml", "source": "New York Times", "primary": True},
    ],
    # Russian state — Kremlin-aligned
    "russian_state": [
        {"url": "https://www.rt.com/rss/", "source": "RT", "primary": True},
        {"url": "https://tass.com/rss/v2.xml", "source": "TASS", "primary": True},
    ],
    # Chinese state — Beijing-aligned
    "chinese_state": [
        {"url": "https://english.news.cn/rss/latestnews.xml", "source": "Xinhua", "primary": True},
        {"url": "https://www.cgtn.com/subscribe/rss/section/world.xml", "source": "CGTN", "primary": True},
    ],
    # Neutral wire services — global coverage, non-aligned
    "neutral_wire": [
        {"url": "https://www.aljazeera.com/xml/rss/all.xml", "source": "Al Jazeera", "primary": True},
        {"url": "https://www.thehindu.com/news/international/feeder/default.rss", "source": "The Hindu", "primary": True},
    ],
    # Russian independent — critical of Kremlin (in exile / foreign-funded)
    "russian_independent": [
        # Meduza is an independent Latvian-based Russian-language outlet.
        {"url": "https://meduza.io/rss/podcasts/English.xml", "source": "Meduza", "primary": True},
    ],
    # Middle Eastern — Arab/Persian/Turkish perspectives
    "middle_eastern": [
        # Al Jazeera already primary in neutral_wire; Anadolu (Turkey) is a
        # genuinely Middle-Eastern state wire that does not duplicate AJ.
        {"url": "https://www.aa.com.tr/rss/default?cat=guncel&tag=en", "source": "Anadolu Agency", "primary": True},
        {"url": "https://www.tehrantimes.com/rss", "source": "Tehran Times", "primary": True},
    ],
    # Latin American — South/Central America perspectives
    "latin_american": [
        # TeleSUR is a multistate leftist Latin American network (Caracas HQ).
        {"url": "https://www.telesurenglish.net/rss", "source": "TeleSUR English", "primary": True},
    ],
    # African — continental perspectives
    "african": [
        # Daily Trust (Nigeria) and The East African (Kenya) cover the
        # continent from genuinely African editorial desks.
        {"url": "https://www.dailytrust.com.ng/feed/", "source": "Daily Trust", "primary": True},
        {"url": "https://www.theeastafrican.co.ke/tea/rss/rss.xml", "source": "The East African", "primary": True},
    ],
    # South Asian — India, Pakistan, Bangladesh, Sri Lanka
    "south_asian": [
        {"url": "https://www.thehindu.com/news/international/feeder/default.rss", "source": "The Hindu", "primary": False},
        {"url": "https://www.dawn.com/feed", "source": "Dawn", "primary": True},
    ],
    # East Asian — Japan, Korea, Southeast Asia
    "east_asian": [
        # Asia Times (Hong Kong/Singapore) covers the region with a
        # distinctly East-Asian editorial lens; NTV English is Japanese.
        {"url": "https://asiatimes.com/feed/", "source": "Asia Times", "primary": True},
        {"url": "https://www.ntv.co.jp/englishnews/index.xml", "source": "NTV English", "primary": True},
    ],
}

# NewsAPI sources (requires NEWSAPI_KEY)
NEWSAPI_SOURCES: dict[str, list[dict]] = {
    "western_mainstream": [
        {"source": "reuters", "country": None},
        {"source": "associated-press", "country": None},
        {"source": "bbc-news", "country": None},
    ],
    "russian_state": [
        {"country": "ru", "source": None},
    ],
    "chinese_state": [
        {"country": "cn", "source": None},
    ],
    "neutral_wire": [
        {"country": "ch", "source": None},
    ],
    "middle_eastern": [
        {"country": "sa", "source": None},
        {"country": "ae", "source": None},
        {"country": "ir", "source": None},
        {"country": "tr", "source": None},
    ],
    "latin_american": [
        {"country": "br", "source": None},
        {"country": "mx", "source": None},
        {"country": "ar", "source": None},
        {"country": "ve", "source": None},
        {"country": "co", "source": None},
    ],
    "african": [
        {"country": "za", "source": None},
        {"country": "ng", "source": None},
        {"country": "ke", "source": None},
        {"country": "eg", "source": None},
        {"country": "tz", "source": None},
    ],
    "south_asian": [
        {"country": "in", "source": None},
        {"country": "pk", "source": None},
        {"country": "bd", "source": None},
    ],
    "east_asian": [
        {"country": "jp", "source": None},
        {"country": "kr", "source": None},
        {"country": "id", "source": None},
        {"country": "ph", "source": None},
        {"country": "th", "source": None},
    ],
}


# Default ISO-3166 country codes per source pool. Used when an RSS/NewsAPI
# record doesn't itself expose a country. Covers all 10 pools.
_POOL_DEFAULT_COUNTRY: dict[str, str] = {
    "western_mainstream": "GB",
    "russian_state": "RU",
    "russian_independent": "LV",   # Meduza is headquartered in Riga
    "chinese_state": "CN",
    "neutral_wire": "QA",          # Al Jazeera primary
    "middle_eastern": "TR",
    "latin_american": "VE",        # TeleSUR HQ
    "african": "NG",
    "south_asian": "IN",
    "east_asian": "HK",
}


def _fetch_rss_feeds(days_back: int = 1) -> list[Article]:
    """Fetch articles from public RSS feeds (free, no API key needed).
    
    Uses xml.etree.ElementTree to parse RSS 2.0 feeds.
    Falls back gracefully if feeds are unavailable.
    """
    import logging
    import urllib.request
    import xml.etree.ElementTree as ET
    
    logger = logging.getLogger(__name__)
    articles: list[Article] = []
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days_back)
    for pool_name, feeds in RSS_FEEDS.items():
        pool = SourcePool(pool_name)
        
        for feed in feeds:
            # Skip non-primary feeds — only fetch each RSS URL once
            if not feed.get("primary", True):
                continue

            try:
                req = urllib.request.Request(
                    feed["url"],
                    headers={"User-Agent": "kill-prop/0.1 RSS Reader"}
                )
                with urllib.request.urlopen(req, timeout=15) as resp:
                    raw = resp.read()
                
                # Parse RSS XML
                root = ET.fromstring(raw)
                channel = root.find("channel")
                if channel is None:
                    continue
                
                items = channel.findall("item")
                count = 0
                for item in items[:8]:  # Max 8 per feed
                    title_el = item.find("title")
                    desc_el = item.find("description")
                    link_el = item.find("link")
                    date_el = item.find("pubDate")
                    
                    title = title_el.text.strip() if title_el is not None and title_el.text else "Untitled"
                    description = desc_el.text.strip() if desc_el is not None and desc_el.text else ""
                    link = link_el.text.strip() if link_el is not None and link_el.text else ""
                    
                    # Clean HTML from description
                    description = _strip_html(description)
                    
                    # Parse date
                    pub_dt = None
                    if date_el is not None and date_el.text:
                        try:
                            from email.utils import parsedate_to_datetime
                            pub_dt = parsedate_to_datetime(date_el.text.strip()).replace(tzinfo=None)
                        except Exception:
                            pass
                    
                    # Skip old articles
                    if pub_dt and pub_dt < cutoff:
                        continue

                    # Skip non-Europe/Russia articles
                    combined = (title + " " + description).lower()
                    if not _has_europe_russia_geo(combined):
                        continue
                    
                    article = Article(
                        canonical_url=link,
                        title=title[:200],
                        author=None,
                        published_at=pub_dt,
                        source_name=feed["source"],
                        source_pool=pool,
                        source_country=_POOL_DEFAULT_COUNTRY.get(pool_name, "unknown"),
                        full_text=description,
                        topic_tags=_infer_tags(title + " " + description),
                    )
                    
                    from backend.pipeline.normalization import normalize_claims_batch
                    claims = _extract_claims_from_article(article)
                    anchor = pub_dt.strftime("%Y-%m-%d") if pub_dt else None
                    claims = normalize_claims_batch(claims, anchor_date=anchor)
                    article.claims = claims

                    articles_store[article.article_id] = article
                    for c in claims:
                        claims_store[c.claim_id] = c
                    articles.append(article)
                    count += 1
                
                logger.info(f"RSS: fetched {count} articles from {feed['source']} ({pool_name})")
                
            except Exception as e:
                logger.warning(f"RSS feed failed for {feed['source']}: {e}")
                continue
    
    return articles


def _strip_html(text: str) -> str:
    """Remove HTML tags from text."""
    import re
    clean = re.sub(r'<[^>]+>', ' ', text)
    clean = re.sub(r'\s+', ' ', clean)
    return clean.strip()


def _fetch_from_newsapi(days_back: int = 1) -> list[Article]:
    """Fetch real articles from NewsAPI.org (free tier).
    
    Set NEWSAPI_KEY environment variable to enable.
    Falls back to seed data if key is not set or API fails.
    """
    api_key = os.getenv("NEWSAPI_KEY", "")
    if not api_key:
        import logging
        logging.getLogger(__name__).info("NEWSAPI_KEY not set — skipping NewsAPI")
        return []

    try:
        import logging
        import urllib.request
        import json as json_mod
        
        logger = logging.getLogger(__name__)
        articles: list[Article] = []
        from_date = (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days_back)).strftime("%Y-%m-%d")
        
        for pool_name, source_configs in NEWSAPI_SOURCES.items():
            pool = SourcePool(pool_name)
            
            for config in source_configs:
                url = "https://newsapi.org/v2/top-headlines?"
                if config["source"]:
                    url += f"sources={config['source']}&"
                elif config["country"]:
                    url += f"country={config['country']}&"
                url += f"apiKey={api_key}"
                
                try:
                    req = urllib.request.Request(url, headers={"User-Agent": "kill-prop/0.1"})
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        data = json_mod.loads(resp.read())
                    
                    if data.get("status") != "ok":
                        logger.warning(f"NewsAPI returned error for {config}: {data.get('message', 'unknown error')}")
                        continue
                    
                    fetched = 0
                    for item in data.get("articles", [])[:5]:  # Max 5 per source
                        pub_str = item.get("publishedAt", "")
                        pub_dt = None
                        if pub_str:
                            try:
                                pub_dt = datetime.fromisoformat(pub_str.replace("Z", "+00:00")).replace(tzinfo=None)
                            except (ValueError, TypeError):
                                pass
                        
                        # Skip old articles
                        if pub_dt and pub_dt < datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days_back):
                            continue

                        title = item.get("title", "Untitled")
                        description = item.get("description") or ""
                        # Skip non-Europe/Russia articles
                        if not _has_europe_russia_geo((title + " " + description).lower()):
                            continue
                        
                        source_name = item.get("source", {}).get("name", config.get("source", "Unknown"))
                        # Map pool to default country for source_country field
                        country = config.get("country") or _POOL_DEFAULT_COUNTRY.get(pool_name, "unknown")
                        
                        article = Article(
                            canonical_url=item.get("url", ""),
                            title=item.get("title", "Untitled")[:200],
                            author=item.get("author"),
                            published_at=pub_dt,
                            source_name=source_name,
                            source_pool=pool,
                            source_country=country,
                            full_text=item.get("content") or item.get("description", ""),
                            topic_tags=_infer_tags(item.get("title", "") + " " + (item.get("description") or "")),
                        )
                        
                        from backend.pipeline.normalization import normalize_claims_batch
                        claims = _extract_claims_from_article(article)
                        anchor = pub_dt.strftime("%Y-%m-%d") if pub_dt else None
                        claims = normalize_claims_batch(claims, anchor_date=anchor)
                        article.claims = claims
                        
                        articles_store[article.article_id] = article
                        for c in claims:
                            claims_store[c.claim_id] = c
                        articles.append(article)
                        
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).warning(f"NewsAPI fetch failed for {pool_name}/{config}: {e}")
                    continue
        
        return articles
        
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"NewsAPI integration failed: {e}")
        return []


def _has_europe_russia_geo(text_lower: str) -> bool:
    """Check if text is about Europe/Russia political/military topics.
    
    Requires BOTH:
    1. A Europe/Russia geo-keyword
    2. A political/military topic keyword
    
    This filters out sports, entertainment, culture, and other non-political
    articles that happen to mention European locations.
    """
    EUROPE_RUSSIA_GEO = [
        "russia", "russian", "moscow", "kremlin", "putin",
        "ukraine", "ukrainian", "kyiv", "kiev", "zelensky",
        "belarus", "belarusian", "minsk", "lukashenko",
        "poland", "polish", "warsaw",
        "lithuania", "latvia", "estonia", "vilnius", "riga", "tallinn",
        "romania", "romanian", "bucharest",
        "bulgaria", "bulgarian", "sofia",
        "moldova", "moldovan", "chisinau",
        "hungary", "hungarian", "budapest",
        "czech", "czechia", "prague",
        "slovakia", "slovak", "bratislava",
        "armenia", "armenian", "yerevan",
        "azerbaijan", "azerbaijani", "baku",
        "georgia", "georgian", "tbilisi",
        "germany", "german", "berlin",
        "france", "french", "paris",
        "united kingdom", "britain", "british", "uk", "london",
        "italy", "italian", "rome",
        "spain", "spanish", "madrid",
        "sweden", "swedish", "stockholm",
        "norway", "norwegian", "oslo",
        "finland", "finnish", "helsinki",
        "denmark", "danish", "copenhagen",
        "netherlands", "dutch", "amsterdam",
        "belgium", "belgian", "brussels",
        "austria", "austrian", "vienna",
        "switzerland", "swiss", "bern",
        "portugal", "portuguese", "lisbon",
        "greece", "greek", "athens",
        "serbia", "serbian", "belgrade",
        "croatia", "croatian", "zagreb",
        "european union", "european commission", "european parliament",
        "nato", "europe", "european",
        "strasbourg",
        "black sea", "baltic sea", "dnipro", "dnieper", "dniester",
        "barents sea", "north sea",
        "crimea", "donbas", "donbass", "lugansk", "donetsk",
        "nord stream",
        "gazprom", "rosatom", "lavrov", "peskov",
        "bryansk", "ryazan", "kursk", "belgorod", "rostov",
        # Cyrillic variants
        "брянск", "рязан", "курск", "белгород", "ростов",
        "россия", "москва", "украин", "киев", "донбасс", "крым",
    ]

    # Must have a geo match
    if not any(geo in text_lower for geo in EUROPE_RUSSIA_GEO):
        return False

    # Must ALSO have a political/military topic keyword
    POLITICAL_TOPIC_KEYWORDS = [
        # War & conflict
        "war", "invasion", "offensive", "ceasefire", "truce", "strike", "attack",
        "military", "army", "troops", "navy", "air force", "drone", "missile",
        "artillery", "tank", "fighter jet", "warship", "submarine", "battle",
        "bombing", "airstrike", "shelling", "warfare", "insurgency",
        "conflict", "clash", "fighting", "hostilities", "skirmish", "standoff",
        "defense", "defence", "nato", "alliance", "deterrence",
        "nuclear", "atomic", "uranium", "enrichment", "reactor", "warhead",
        "icbm", "ballistic missile", "weapon",
        # Diplomacy & geopolitics
        "diplomacy", "diplomatic", "embassy", "ambassador", "treaty", "accord",
        "summit", "negotiation", "dialogue", "state visit", "foreign minister",
        "g7", "g20", "brics", "united nations", "security council",
        "sanction", "embargo", "trade ban", "asset freeze",
        "peace", "peacekeeping", "peace deal", "peace talk", "mediation",
        "geopolitic", "sphere of influence", "great power", "superpower",
        "cold war", "proxy war", "regime change", "coup",
        # Economy & energy (political context)
        "economy", "economic", "gdp", "recession", "inflation", "central bank",
        "trade", "tariff", "export", "import", "trade war", "supply chain",
        "energy", "oil", "gas", "pipeline", "refinery", "petroleum",
        "grain", "wheat", "food security", "famine",
        # Politics & governance
        "election", "vote", "ballot", "candidate", "presidential", "parliament",
        "congress", "senate", "referendum", "poll",
        "government", "cabinet", "minister", "president", "prime minister",
        "administration", "regime", "authority",
        "policy", "legislation", "law", "bill", "reform", "regulation",
        "human right", "civil right", "freedom of speech", "freedom of press",
        "political prisoner", "dissident", "oppression", "censorship",
        "media freedom", "press freedom", "nda", "whistleblower",
        "refugee", "asylum", "displaced", "migrant crisis",
        "migration", "immigration", "border control", "deportation",
        # Security
        "security", "cyber", "cyberattack", "hack", "espionage", "intelligence",
        "spy", "surveillance", "terrorism", "terrorist", "extremist",
        # Russian-specific political terms
        "kremlin", "putin", "lavrov", "peskov", "zelensky",
        "mobilization", "conscription", "draft",
        # Cyrillic political/military terms
        "война", "атака", "удар", "оборона", "пво", "беспилотник",
        "дрон", "минобороны", "террорист", "режим", "санкци",
        "переговор", "мирный", "соглашение", "договор",
        "мобилизация", "конфликт", "вторжение",
    ]

    return any(kw in text_lower for kw in POLITICAL_TOPIC_KEYWORDS)


def _infer_tags(text: str) -> list[str]:
    """Infer topic tags from article text.
    
    Only returns tags for articles about Europe and Russia interconnected topics.
    Articles about other regions (Middle East, Asia, Africa, Americas) are filtered out
    UNLESS they directly involve Russia or European powers.
    """
    text_lower = text.lower()

    # ── Geo-filter: must mention Europe or Russia ──────────────────
    # Articles about Gaza, Delhi, Peru, Somalia, etc. are excluded
    # unless they also mention Russia/Europe involvement.
    EUROPE_RUSSIA_GEO = [
        # Russia & neighbors
        "russia", "russian", "moscow", "kremlin", "putin",
        "ukraine", "ukrainian", "kyiv", "kiev", "zelensky",
        "belarus", "belarusian", "minsk", "lukashenko",
        # Eastern Europe / Baltics
        "poland", "polish", "warsaw",
        "lithuania", "latvia", "estonia", "vilnius", "riga", "tallinn",
        "romania", "romanian", "bucharest",
        "bulgaria", "bulgarian", "sofia",
        "moldova", "moldovan", "chisinau",
        "hungary", "hungarian", "budapest",
        "czech", "czechia", "prague",
        "slovakia", "slovak", "bratislava",
        # Caucasus
        "armenia", "armenian", "yerevan",
        "azerbaijan", "azerbaijani", "baku",
        "georgia", "georgian", "tbilisi",
        # Western / Northern / Southern Europe
        "germany", "german", "berlin",
        "france", "french", "paris",
        "united kingdom", "britain", "british", "uk", "london",
        "italy", "italian", "rome",
        "spain", "spanish", "madrid",
        "sweden", "swedish", "stockholm",
        "norway", "norwegian", "oslo",
        "finland", "finnish", "helsinki",
        "denmark", "danish", "copenhagen",
        "netherlands", "dutch", "amsterdam",
        "belgium", "belgian", "brussels",
        "austria", "austrian", "vienna",
        "switzerland", "swiss", "bern",
        "portugal", "portuguese", "lisbon",
        "greece", "greek", "athens",
        "serbia", "serbian", "belgrade",
        "croatia", "croatian", "zagreb",
        # Transnational European orgs
        "european union", "european commission", "european parliament",
        "nato", "europe", "european",
        "brussels", "strasbourg",
        # Black Sea / Baltic / relevant waterways
        "black sea", "baltic sea", "dnipro", "dnieper", "dniester",
        "barents sea", "north sea", "mediterranean",
        "crimea", "donbas", "donbass", "lugansk", "donetsk",
    ]

    has_europe_russia_geo = any(geo in text_lower for geo in EUROPE_RUSSIA_GEO)
    if not has_europe_russia_geo:
        return []  # Filtered out — not Europe/Russia relevant

    tags = []

    # Only political/propaganda-relevant tag categories
    POLITICAL_TAG_KEYWORDS = {
        # Military & Conflict
        "military": ["military", "army", "troops", "navy", "air force", "artillery", "tank", "missile",
                     "drone", "fighter jet", "warship", "submarine", "battlefield", "frontline", "deployment"],
        "war": ["war", "invasion", "offensive", "ceasefire", "truce", "surrender", "occupation",
                "bombing", "airstrike", "shelling", "warfare", "insurgency", "counter-offensive"],
        "conflict": ["conflict", "clash", "fighting", "hostilities", "skirmish", "standoff", "confrontation"],
        "defense": ["defense", "defence", "nato", "alliance", "deterrence", "air defense", "patriot system"],
        "nuclear": ["nuclear", "atomic", "uranium", "plutonium", "enrichment", "reactor", "warhead",
                    "icbm", "ballistic missile", "non-proliferation"],
        "terrorism": ["terrorism", "terrorist", "extremist", "jihadist", "isis", "al-qaeda", "boko haram",
                      "suicide bomb", "insurgent", "militant"],

        # Geopolitics & Diplomacy
        "geopolitics": ["geopolitic", "russia", "ukraine", "china", "nato", "diplomatic", "summit", "treaty",
                        "sphere of influence", "great power", "superpower", "cold war", "proxy war",
                        "regime change", "coup", "strategic"],
        "diplomacy": ["diplomacy", "embassy", "ambassador", "accord", "negotiation", "dialogue",
                      "state visit", "foreign minister", "g7", "g20", "brics", "united nations",
                      "un security council", "security council", "general assembly"],
        "foreign_policy": ["foreign policy", "foreign affairs", "international relations", "bilateral",
                           "multilateral", "state department", "foreign office", "foreign ministry"],
        "sanctions": ["sanction", "embargo", "trade ban", "asset freeze", "travel ban", "blacklist",
                       "restrictive measure", "economic pressure"],
        "peace": ["peace", "peacekeeping", "peace deal", "peace talk", "mediation", "arbitration",
                  "reconciliation", "ceasefire agreement"],

        # Economy & Resources
        "economy": ["economy", "economic", "gdp", "recession", "inflation", "deflation", "central bank",
                    "interest rate", "fiscal", "monetary", "imf", "world bank", "debt", "default",
                    "sovereign debt", "credit rating"],
        "trade": ["trade", "tariff", "export", "import", "free trade", "protectionism", "wto",
                  "supply chain", "trade war", "trade deal", "trade agreement", "customs"],
        "energy": ["energy", "oil", "gas", "pipeline", "opec", "petroleum", "natural gas", "lng",
                   "nord stream", "oil field", "refinery", "petrol", "diesel", "crude oil",
                   "renewable energy", "solar", "wind farm", "energy security"],
        "food_security": ["food security", "grain", "wheat", "famine", "food shortage", "food crisis",
                          "agriculture export", "fertilizer", "harvest", "staple food"],
        "infrastructure": ["infrastructure", "belt and road", "bri", "port", "railway", "highway",
                           "bridge", "dam", "airport", "seaport", "logistics hub", "depot", "facility"],

        # Politics & Governance
        "election": ["election", "vote", "ballot", "candidate", "presidential", "parliament", "congress",
                     "senate", "referendum", "poll", "runoff", "electoral", "campaign"],
        "government": ["government", "parliament", "congress", "senate", "cabinet", "minister",
                       "president", "prime minister", "administration", "regime", "authority",
                       "legislature", "executive", "governance"],
        "policy": ["policy", "legislation", "law", "bill", "act", "reform", "regulation", "deregulation",
                   "executive order", "decree", "mandate"],
        "human_rights": ["human right", "civil right", "freedom of speech", "freedom of press",
                         "political prisoner", "dissident", "oppression", "censorship", "surveillance",
                         "mass arrest", "detention", "torture"],
        "refugees": ["refugee", "asylum", "displaced", "migrant crisis", "humanitarian crisis",
                     "internally displaced", "unhcr", "border crisis"],
        "migration": ["migration", "immigration", "emigration", "border control", "border wall",
                      "deportation", "visa", "asylum seeker"],

        # International / General
        "international": ["international", "global", "worldwide", "multilateral", "transnational"],
        "security": ["security", "cyber", "cyberattack", "hack", "espionage", "intelligence",
                     "spy", "surveillance", "data breach"],
    }

    for tag, keywords in POLITICAL_TAG_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            tags.append(tag)

    # Fallback: if no political tags found, try broader match
    if not tags:
        broad_political = ["war", "conflict", "military", "sanction", "diplomacy", "election",
                           "government", "economy", "trade", "security", "peace", "nuclear",
                           "policy", "president", "minister", "international", "foreign"]
        if any(kw in text_lower for kw in broad_political):
            tags.append("geopolitics")

    return tags if tags else []
