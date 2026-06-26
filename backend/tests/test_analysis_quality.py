"""Tests for the analysis-quality improvements:

* Source-reliability lookup is alias-aware and matches real source names
  ("BBC News", "New York Times", "TASS", etc.) — not just the bare priors keys.
* The propaganda lexicon catches both English and Russian/Cyrillic state
  framing ("special military operation", "киевский режим", "denazification",
  "orcs", "collective west", ...).
* Rule-based claim extraction no longer defaults to VERIFIED_FACT; uncertain
  or unevidenced sentences fall into INFERENCE instead.
* Time references extracted by normalize_claim() are anchored to the article's
  real published_at date rather than a hard-coded 2026-06-05.
* Seed ingestion is clock-resilient: the newest seed article is always within
  the days_back window regardless of the real wall clock.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from backend.models import (
    Article,
    Attribution,
    Claim,
    ClaimArgument,
    ClaimBucket,
    EvidenceIndicators,
    SourcePool,
    articles_store,
    claims_store,
    events_store,
    lookup_source_reliability,
    source_reliability_priors,
)
from backend.pipeline.ingestion import (
    PROPAGANDA_LEXICON,
    SEED_ARTICLES,
    _detect_propaganda_signals,
    _is_non_claim_sentence,
    _extract_claims_from_article,
    ingest_articles,
)
from backend.pipeline.normalization import normalize_claim


# ---------------------------------------------------------------------------
# Source reliability alias lookup
# ---------------------------------------------------------------------------

class TestSourceReliabilityLookup:
    def test_direct_key_matches(self):
        assert lookup_source_reliability("Reuters") == source_reliability_priors["reuters"]

    def test_bbc_news_display_name_resolves(self):
        # The display name "BBC News" should resolve via alias to the bbc prior.
        assert lookup_source_reliability("BBC News") == source_reliability_priors["bbc"]

    def test_new_york_times_display_name_resolves(self):
        prior = lookup_source_reliability("New York Times")
        assert prior == source_reliability_priors["new_york_times"]
        # And it's the high-reliability value, not the 0.5 fallback.
        assert prior > 0.6

    def test_al_jazeera_resolves(self):
        assert lookup_source_reliability("Al Jazeera") == source_reliability_priors["al_jazeera"]

    def test_the_hindu_resolves(self):
        assert lookup_source_reliability("The Hindu") == source_reliability_priors["the_hindu"]

    def test_tass_resolves(self):
        assert lookup_source_reliability("TASS") == source_reliability_priors["tass"]

    def test_rt_resolves(self):
        assert lookup_source_reliability("RT") == source_reliability_priors["rt"]

    def test_unknown_source_falls_back_to_neutral(self):
        assert lookup_source_reliability("Totally Unknown Outlet") == 0.5

    def test_empty_source_name_falls_back(self):
        assert lookup_source_reliability("") == 0.5

    def test_case_and_punctuation_insensitive(self):
        # "BBC News World" should still hit the bbc prior via substring match.
        assert lookup_source_reliability("BBC News World") == source_reliability_priors["bbc"]

    def test_reliable_outlet_scores_higher_than_unknown(self):
        assert lookup_source_reliability("Reuters") > lookup_source_reliability("Unknown Blog")


# ---------------------------------------------------------------------------
# Propaganda lexicon expansion
# ---------------------------------------------------------------------------

class TestPropagandaLexicon:
    def test_lexicon_covers_all_signal_categories(self):
        # Sanity: the lexicon has the four expected flag buckets.
        for flag in ("loaded_language", "us_vs_them", "certainty_without_evidence", "whataboutism"):
            assert flag in PROPAGANDA_LEXICON
            assert len(PROPAGANDA_LEXICON[flag]) > 0

    def test_russian_special_military_operation_detected(self):
        s = "The special military operation continues according to plan.".lower()
        assert "loaded_language" in _detect_propaganda_signals(s)

    def test_denazification_detected(self):
        s = "The goals of denazification and demilitarization remain.".lower()
        assert "loaded_language" in _detect_propaganda_signals(s)

    def test_kyiv_regime_detected(self):
        s = "The kyiv regime continues to shell civilian areas.".lower()
        assert "loaded_language" in _detect_propaganda_signals(s)

    def test_cyrillic_kyiv_regime_detected(self):
        s = "Киевский режим обстрелял жилые кварталы.".lower()
        assert "loaded_language" in _detect_propaganda_signals(s)

    def test_cyrillic_special_operation_detected(self):
        # Uses genitive case "специальной военной операции"; the lexicon matches
        # on invariant stems so case-form variation doesn't evade detection.
        s = "В ходе специальной военной операции уничтожено три дрона.".lower()
        assert "loaded_language" in _detect_propaganda_signals(s)

    def test_cyrillic_svo_abbreviation_detected(self):
        # The abbreviation СВО (SVO) is the standard Russian-state shorthand
        # for the invasion; flagged when surrounded by spaces.
        s = "В ходе СВО было уничтожено три дрона. ".lower()
        assert "loaded_language" in _detect_propaganda_signals(s)

    def test_collective_west_us_vs_them_detected(self):
        s = "The collective west is trying to weaken our country.".lower()
        assert "us_vs_them" in _detect_propaganda_signals(s)

    def test_orcs_dehumanization_detected(self):
        # "orcs" appears in both loaded_language and us_vs_them; either is fine.
        s = "The orcs advanced on the eastern front.".lower()
        signals = _detect_propaganda_signals(s)
        assert "loaded_language" in signals or "us_vs_them" in signals

    def test_whataboutism_detected(self):
        s = "But America also invaded Iraq in 2003, so what about that?".lower()
        assert "whataboutism" in _detect_propaganda_signals(s)

    def test_certainty_without_evidence_detected(self):
        # _detect_propaganda_signals expects already-lowered input.
        assert "certainty_without_evidence" in _detect_propaganda_signals(
            "It is obvious that they are lying to the whole world.".lower()
        )

    def test_neutral_sentence_has_no_flags(self):
        assert _detect_propaganda_signals(
            "the strike occurred at 03:10 local time near the river."
        ) == []

    def test_word_boundary_no_false_positive_on_substring(self):
        # "crush" must not match inside "crushing debt" via the bare-substring
        # path; this guards the word-boundary branch for single-word terms.
        # ("crush" is in the loaded list; a clean finance sentence using the
        # substring should NOT fire.)
        signals = _detect_propaganda_signals(
            "the company reported crushing debt and declining revenues.".lower()
        )
        assert "loaded_language" not in signals


# ---------------------------------------------------------------------------
# Claim extraction tightening
# ---------------------------------------------------------------------------

def _make_article(full_text: str, pool: SourcePool = SourcePool.WESTERN_MAINSTREAM) -> Article:
    return Article(
        canonical_url="https://example.com/test",
        title="Test Article",
        source_name="Test Source",
        source_pool=pool,
        source_country="US",
        language="en",
        full_text=full_text,
        topic_tags=["test"],
        published_at=datetime(2026, 6, 5),
    )


class TestClaimExtractionTightening:
    def test_question_sentences_skipped(self):
        article = _make_article(
            "Will the ceasefire hold through the weekend? "
            "A drone strike hit a fuel depot near the river."
        )
        claims = _extract_claims_from_article(article)
        for c in claims:
            assert not c.claim_text_original.endswith("?")

    def test_default_bucket_is_inference_not_verified_fact(self):
        # A plain declarative sentence with no attribution, no hedging, and no
        # framing cues should land in INFERENCE (the new default), not
        # VERIFIED_FACT. Verified-fact status now requires corroboration.
        article = _make_article(
            "The depot is located in an area where both sides have conducted operations."
        )
        claims = _extract_claims_from_article(article)
        assert len(claims) == 1
        assert claims[0].bucket == ClaimBucket.INFERENCE

    def test_attribution_still_takes_priority_over_inference(self):
        article = _make_article(
            "The defense ministry stated that air defense intercepted the drones."
        )
        claims = _extract_claims_from_article(article)
        assert any(c.bucket == ClaimBucket.ATTRIBUTED_STATEMENT for c in claims)

    def test_framing_beats_attribution(self):
        # The sentence is attributed ("according to analysts") but is also
        # editorial framing ("fits a pattern"). Framing should win so the
        # reviewer sees a yellow flag.
        article = _make_article(
            "According to analysts, this incident fits a pattern of escalating attacks."
        )
        claims = _extract_claims_from_article(article)
        framing = [c for c in claims if c.bucket == ClaimBucket.OPINIONATED_FRAMING]
        assert len(framing) >= 1

    def test_propaganda_flags_attached_to_extracted_claim(self):
        article = _make_article(
            "The kyiv regime launched another terrorist attack against civilians."
        )
        claims = _extract_claims_from_article(article)
        assert any("loaded_language" in c.propaganda_flags for c in claims)


class TestNonClaimHeuristic:
    def test_question_is_non_claim(self):
        assert _is_non_claim_sentence("What happens next?") is True

    def test_declarative_is_claim(self):
        assert _is_non_claim_sentence("A strike hit the depot.") is False


# ---------------------------------------------------------------------------
# Time anchoring in normalize_claim
# ---------------------------------------------------------------------------

class TestTimeAnchoring:
    def _claim(self, text: str) -> Claim:
        return Claim(
            source_article_id="a_test",
            source_pool=SourcePool.WESTERN_MAINSTREAM,
            source_name="Test Source",
            claim_text_original=text,
            evidence=EvidenceIndicators(),
            attribution=Attribution(),
        )

    def test_anchor_date_used_when_provided(self):
        c = self._claim("The attack occurred at 03:10 local time.")
        normalize_claim(c, anchor_date="2027-01-15")
        time_arg = c.arguments["time"]
        assert time_arg.normalized.startswith("2027-01-15T")
        assert "03:10" in time_arg.normalized

    def test_no_hardcoded_2026_date(self):
        c = self._claim("The attack occurred at 03:10 local time.")
        normalize_claim(c, anchor_date="2027-01-15")
        # The old code hard-coded "2026-06-05" — make sure it's gone.
        assert "2026-06-05" not in c.arguments["time"].normalized

    def test_pm_time_converted_to_24h(self):
        c = self._claim("The meeting was held at 2:00 pm local time.")
        normalize_claim(c, anchor_date="2027-01-15")
        assert "14:00" in c.arguments["time"].normalized

    def test_am_midnight_converted(self):
        c = self._claim("The strike happened at 12:00 am.")
        normalize_claim(c, anchor_date="2027-01-15")
        assert "00:00" in c.arguments["time"].normalized

    def test_falls_back_to_today_when_no_anchor(self):
        c = self._claim("The attack occurred at 03:10 local time.")
        normalize_claim(c)
        today_prefix = datetime.now().strftime("%Y-%m-%d")
        assert c.arguments["time"].normalized.startswith(today_prefix)


# ---------------------------------------------------------------------------
# Seed ingestion is clock-resilient
# ---------------------------------------------------------------------------

class TestSeedIngestionClockResilience:
    def setup_method(self):
        articles_store.clear()
        claims_store.clear()
        events_store.clear()

    def teardown_method(self):
        articles_store.clear()
        claims_store.clear()
        events_store.clear()

    def test_seed_ingests_articles_regardless_of_real_clock(self):
        # Even though seed articles are dated June 5 and today might be much
        # later, ingest_articles(seed=True) must still populate the store.
        from datetime import timezone
        articles = ingest_articles(seed=True, days_back=1)
        assert len(articles) > 0
        # And every article should be within the days_back window of "now".
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        for a in articles:
            assert a.published_at is not None
            age = now - a.published_at.replace(tzinfo=None)
            assert age < timedelta(days=2), (
                f"Article dated {a.published_at} is older than the window"
            )

    def test_seed_articles_preserve_relative_spacing(self):
        # The fix shifts all seed timestamps by a constant offset, so the
        # delta between the earliest and latest seed should be unchanged.
        original_times = [s["published_at"] for s in SEED_ARTICLES if s.get("published_at")]
        original_span = max(original_times) - min(original_times)

        ingest_articles(seed=True, days_back=7)  # wide window, captures all
        stored_times = [a.published_at for a in articles_store.values() if a.published_at]
        stored_span = max(stored_times) - min(stored_times)

        # Allow sub-second rounding; spans must match exactly.
        assert abs(stored_span - original_span) < timedelta(seconds=1)
