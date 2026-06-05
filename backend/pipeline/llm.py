"""LLM provider for kill-prop."""
from __future__ import annotations

import os
import logging

logger = logging.getLogger(__name__)

MODEL_REPO = "TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF"
MODEL_FILE = "tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"

_llm = None

def get_llm():
    """Lazy load the LLM."""
    global _llm
    if _llm is None:
        from huggingface_hub import hf_hub_download
        from llama_cpp import Llama

        logger.info(f"Downloading model {MODEL_FILE} from {MODEL_REPO}...")
        try:
            model_path = hf_hub_download(repo_id=MODEL_REPO, filename=MODEL_FILE)
            logger.info(f"Model downloaded to {model_path}")
            _llm = Llama(
                model_path=model_path,
                n_ctx=2048,
                n_threads=2,
                verbose=False
            )
            logger.info("LLM initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize LLM: {e}")
            raise e
    return _llm
