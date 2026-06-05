"""Test LLM integration."""
import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent.parent))

from backend.models import Article, SourcePool
from backend.pipeline.llm_extraction import extract_claims_llm

def test_llm_extraction():
    # Mock article
    article = Article(
        canonical_url="https://test.com",
        title="Test Article: Drone strike near Dnipro",
        source_name="Test Source",
        source_pool=SourcePool.WESTERN_MAINSTREAM,
        source_country="US",
        full_text="A drone strike hit a fuel depot near the Dnipro river at 03:10 local time. The defense ministry confirmed the attack. No casualties were reported."
    )

    print("Starting LLM extraction test...")
    os.environ["USE_LLM"] = "true"
    claims = extract_claims_llm(article)
    
    print(f"Extracted {len(claims)} claims:")
    for i, c in enumerate(claims):
        print(f"{i+1}. {c.claim_text_original}")
        print(f"   Bucket: {c.bucket}")
        print(f"   Arguments: {c.arguments}")
        print(f"   Evidence: {c.evidence}")
        print(f"   Attribution: {c.attribution}")
        print(f"   Propaganda: {c.propaganda_flags}")
        print("-" * 20)

if __name__ == "__main__":
    test_llm_extraction()
