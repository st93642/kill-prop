"""LLM provider for kill-prop.

Uses Groq's free OpenAI-compatible REST API (no SDK dependency needed).
Falls back gracefully when no GROQ_API_KEY is configured.

Get a free key at: https://console.groq.com/keys
"""
from __future__ import annotations

import json
import logging
import os
import urllib.request

logger = logging.getLogger(__name__)

GROQ_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"


def is_llm_available() -> bool:
    """Check whether LLM inference is available (i.e. a Groq API key is set)."""
    return bool(os.getenv("GROQ_API_KEY", "").strip())


def llm_chat(prompt: str, max_tokens: int = 512, temperature: float = 0.3) -> str | None:
    """Call the Groq chat completions endpoint and return the text response.

    Returns None if the LLM is unavailable or the call fails.
    """
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        return None

    payload = json.dumps({
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": "You are a concise, objective news analyst."},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }).encode("utf-8")

    req = urllib.request.Request(
        GROQ_ENDPOINT,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "BalancedNews/1.0",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        return body["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.warning(f"Groq LLM call failed: {e}")
        return None


# ── Legacy compatibility shim ──────────────────────────────────────────
# The original code called get_llm()(prompt, max_tokens=..., stop=..., echo=False)
# and expected a response dict with choices[0].text.  We keep the same call
# signature so callers in llm_extraction.py and events.py work unchanged.

def get_llm():
    """Return a callable that mimics the old llama-cpp interface.

    Usage (legacy):
        llm = get_llm()
        response = llm(prompt, max_tokens=512, stop=["</s>"], echo=False)
        text = response["choices"][0]["text"]
    """
    def _call(prompt: str, max_tokens: int = 512, **_kwargs) -> dict:
        text = llm_chat(prompt, max_tokens=max_tokens)
        if text is None:
            raise RuntimeError("LLM unavailable — set GROQ_API_KEY in news.env")
        return {"choices": [{"text": text}]}
    return _call
