# Local LLM Integration for kill-prop

This project now supports local LLM-based claim extraction using `llama-cpp-python` and TinyLlama.

## Requirements
- CPU with at least 4GB RAM (8GB recommended for smoother performance).
- The `llama-cpp-python` and `huggingface_hub` packages.

## How to use
By default, the system uses a fast rule-based extraction for the MVP. To enable the LLM:

1. Set the environment variable `USE_LLM=true`.
2. Run the pipeline.

The system will automatically download the `TinyLlama-1.1B-Chat-v1.0-GGUF` model (approx 660MB) from HuggingFace on the first run.

## Why TinyLlama?
Given the "low hardware, CPU only" constraint, TinyLlama-1.1B is one of the few models that can run reliably on limited hardware while still providing meaningful structured output for claim extraction.

## Pipeline Integration
The LLM is integrated into the `Source Intake` stage (Stage 1). When an article is ingested, if `USE_LLM` is enabled, the `extract_claims_llm` function is called. It uses a structured prompt to get the LLM to output a JSON list of claims, which are then parsed into the internal `Claim` model.

A fallback to the rule-based system is provided if the LLM fails or is not available.
