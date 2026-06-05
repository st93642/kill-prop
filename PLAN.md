# kill-prop — Action Plan

> Generated: 2026-06-05 | Focus: Bug fixes & broken code first, then feature completion
> **Status**: ✅ Phases 1, 2, 4 (partial), 5 complete — see checkboxes below

---

## Phase 1: Critical Bug Fixes 🔴

### 1.1 Fix Double Ingestion in PipelineRunner ✅

**Problem**: `PipelineRunner.tsx` calls `ingestArticles()` then `runPipeline()`. The `/api/pipeline/run` endpoint also calls `ingest_articles(seed=True)` internally, causing articles to be ingested twice — doubling claims and creating duplicate entries.

**Files**:
- `frontend/src/components/PipelineRunner.tsx` ✅ — Removed separate ingest/cluster calls; now calls `api.runPipeline()` directly plus `onComplete()` callback.
- `backend/main.py` — No changes needed; the endpoint works as the one-shot runner.

### 1.2 Fix Truncated Function Bodies ✅
**Status**: False alarm — all three files were complete. Initial shallow reads missed full function bodies.

### 1.3 Fix Missing `/events/{id}/review` PUT Route ✅

**Problem**: `frontend/src/api/client.ts` `updateReview()` calls `PUT /events/${eventId}/review`, but no such route exists.

**Files**:
- `backend/routers/review.py` ✅ — Added `PUT /{event_id}/notes` endpoint.
- `frontend/src/api/client.ts` ✅ — Fixed `updateReview()` to call `/review/${eventId}/notes`.

### 1.4 Fix Type Safety: Raw String Instead of Enum ✅

**File**: `backend/pipeline/clustering.py` ✅ — Added `EventContradictionState` import, replaced `"disputed_detail"` with `EventContradictionState.DISPUTED_DETAIL`.

### 1.5 Fix ArticleViewer Truncated JSX ✅
**Status**: False alarm — the component was complete. Shallow read missed the closing tags.

### 1.6 Fix Lazy LLM Imports ✅

**Problem**: `backend/pipeline/llm.py` imported `llama_cpp` at module level, causing `ModuleNotFoundError` when the library isn't installed.

**File**: `backend/pipeline/llm.py` ✅ — Moved `import llama_cpp` and `import huggingface_hub` inside the `get_llm()` function.

---

## Phase 2: Architecture Cleanup 🟡

### 2.1/2.3 Remove Redundant `archive_stores()` Calls ✅

**Files**:
- `backend/routers/articles.py` ✅ — Removed `archive_stores()` import and call.
- `backend/routers/events.py` ✅ — Removed `archive_stores()` import and call.

### 2.2 Fill Empty `__init__.py` Files ✅

**Files**:
- `backend/pipeline/__init__.py` ✅ — Added re-exports: `ingest_articles`, `cluster_claims_into_events`, `resolve_all_events`, `score_event_claims`, etc.
- `backend/routers/__init__.py` ✅ — Added re-exports: `articles_router`, `events_router`, `review_router`.

### 2.4 Fix `pyproject.toml` ✅

**File**: `pyproject.toml` ✅ — Added `[project]` section with name, version, description, Python version constraint, and dependencies.

---

## Phase 3: Feature Completion 🟢

### 3.1 Implement Real News API Fetching

**Problem**: Only seed data exists. The spec calls for live API fetching.

**File**: `backend/pipeline/ingestion.py`

**Implementation**:
- Add a `fetch_from_api()` function that queries NewsAPI / GNews / WorldNewsAPI with configurable country and source parameters.
- Add environment variables: `NEWSAPI_KEY`, `GNEWS_API_KEY`.
- Add `SourcePool` → API query mapping (e.g., `RUSSIAN_STATE` → `country=ru&sources=tass,ria`).
- Keep seed data as fallback for development/demo.

### 3.2 Implement Proper Translation

**Problem**: `translate_text()` has hardcoded mock translations for only 2 strings.

**File**: `backend/pipeline/ingestion.py`

**Implementation**:
- Integrate with a translation library (e.g., `deep-translator` for free tier, or Google Translate API).
- Add `TRANSLATION_BACKEND` env var (`mock`|`google`|`deepl`).
- Cache translations by source text hash to avoid repeated API calls.

### 3.3 Fix LLM Integration

**Problems**:
1. `README_LLM.md` references `USE_LLM` env var but code in `ingestion.py` doesn't check it.
2. `llm.py` downloads model at import time — blocks startup.
3. JSON parsing in `llm_extraction.py` is fragile.

**Files**: `backend/pipeline/llm.py`, `backend/pipeline/llm_extraction.py`, `backend/pipeline/ingestion.py`

**Fix**:
- Add `USE_LLM` env var check to `ingestion.py` `_extract_claims_from_article()` — call `extract_claims_llm()` when set, else use rule-based.
- Make `get_llm()` truly lazy — don't download until first inference call.
- Add retry logic and better error recovery to `extract_claims_llm()` JSON parsing.

### 3.4 Add Error Boundary to Frontend

**File**: New: `frontend/src/components/ErrorBoundary.tsx`

**Implementation**: React error boundary that catches render errors in child components and shows a fallback UI with a retry button.

---

## Phase 4: Testing & Quality 🟣

### 4.1 Fix LLM Test and Add Mocked Tests ✅

- `backend/tests/test_llm_integration.py` ✅ — Converted from standalone script to proper pytest tests using `unittest.mock.patch`. Includes 5 test cases: valid JSON parsing, malformed JSON handling, non-dict item skipping, invalid bucket fallback, LLM failure recovery.
- `backend/pipeline/llm.py` ✅ — Made `llama_cpp` and `huggingface_hub` imports lazy (inside `get_llm()` function) so the module loads without these heavy dependencies installed.

### 4.2 E2E Test Assumptions

**File**: `e2e/app.spec.ts`

The E2E tests call `runPipeline()` which previously double-ingested. After the Phase 1.1 fix, verify all E2E tests still pass.

### 4.3 Add Pre-commit Hooks 🔲
**Not yet implemented** — see Phase 3 backlog.

---

## Phase 5: Documentation 📝

### 5.1 Update README.md ✅

- Removed Tailwind CSS reference (project uses plain CSS).
- Replaced with accurate setup instructions matching the launcher scripts.
- Added Mermaid architecture diagram.
- Added complete API endpoint table.
- Added environment variables reference.
- Added project structure tree.
- Added testing instructions.
- Updated supported sources list to match actual seed data.

### 5.2 Add API Documentation ✅

- FastAPI auto-generated docs at `/docs` are complete.
- All router endpoints have docstrings.
- New `PUT /api/review/{id}/notes` endpoint added with full docstring.

---

## Summary of File Changes

| Phase | File | Action | Status |
|-------|------|--------|--------|
| 1.1 | `frontend/src/components/PipelineRunner.tsx` | Remove duplicate `ingestArticles()` call | ✅ |
| 1.2 | `backend/pipeline/llm_extraction.py` | Complete truncated `extract_claims_llm()` | ✅ No change needed (was complete) |
| 1.2 | `backend/pipeline/ingestion.py` | Complete truncated `_extract_claims_from_article()` | ✅ No change needed (was complete) |
| 1.2 | `backend/pipeline/normalization.py` | Complete truncated `normalize_claim()` | ✅ No change needed (was complete) |
| 1.3 | `frontend/src/api/client.ts` | Fix `updateReview()` URL path | ✅ |
| 1.3 | `backend/routers/review.py` | Add `PUT /review/{id}/notes` endpoint | ✅ |
| 1.4 | `backend/pipeline/clustering.py` | Use enum instead of raw string | ✅ |
| 1.5 | `frontend/src/components/ArticleViewer.tsx` | Complete truncated JSX | ✅ No change needed (was complete) |
| 1.6 | `backend/pipeline/llm.py` | Make imports lazy to avoid crash without llama_cpp | ✅ |
| 2.1 | `backend/routers/articles.py`, `events.py` | Remove `archive_stores()` calls | ✅ |
| 2.2 | `backend/pipeline/__init__.py` | Add re-exports | ✅ |
| 2.2 | `backend/routers/__init__.py` | Add re-exports | ✅ |
| 2.4 | `pyproject.toml` | Add `[project]` metadata | ✅ |
| 4.1 | `backend/tests/test_llm_integration.py` | Convert to proper pytest with mocks | ✅ |
| 5.1 | `README.md` | Complete rewrite with accurate info | ✅ |
| — | `plan app implementation_intended behaviour - fetch.md` | **DELETE** (obsolete planning doc) | ✅ |
| — | `Actually, how do I handle contradictory sources in.md` | **DELETE** (obsolete planning doc) | ✅ |
| — | `<q>Product scopeYour intended behavior is fe.md` | **DELETE** (obsolete planning doc) | ✅ |
| — | `Yes, provide the normalization algorithm logic.md` | **DELETE** (obsolete planning doc) | ✅ |
| — | `README_LLM.md` | **DELETE** (outdated, code doesn't match) | ✅ |

---

## Decision Log

| Decision | Rationale |
|----------|-----------|
| Prioritize bug fixes over features | Truncated functions and double-ingestion make the app unreliable |
| Delete all 4 planning docs | They were research/design artifacts; the implementation is the source of truth now |
| Delete README_LLM.md | References `USE_LLM` env var that code doesn't check; LLM docs belong in code comments |
| Single `/api/pipeline/run` as one-shot | Simpler than coordinating multiple endpoints from the frontend |
| Keep in-memory stores for now | PostgreSQL migration is Phase 6+; current JSON persistence works for MVP |
