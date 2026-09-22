# Architecture

## Design principles

1. **Provider independence.** The app must never be hard-wired to one paid
   vendor. `BaseLLMProvider` (in `llm_service.py`) defines a single
   `generate(prompt) -> str` contract; four providers implement it today,
   and adding a fifth never requires touching the router, the orchestrator,
   or the frontend.

2. **Layered trust.** Static analysis tools are deterministic and cannot
   hallucinate; the LLM is fluent but occasionally wrong. Rather than
   picking one, the app runs both and labels every finding with its
   `source` field so users can calibrate trust accordingly.

3. **Thin router, fat service.** `routers/review.py` only handles HTTP
   concerns (status codes, request size limits, error translation).
   All actual logic lives in `services/`, which makes it independently
   testable and reusable (e.g. from a future CLI or GitHub Action).

4. **Fail loud, fail clear.** If the configured LLM is unreachable
   (e.g. Ollama isn't running), the API returns HTTP 502 with a specific,
   actionable message ("Is Ollama running at http://localhost:11434? Try
   `ollama serve`...") instead of a generic 500 or a silent empty response.

## Request lifecycle

1. User pastes/writes code in the Monaco editor (`CodeEditor.jsx`) and
   clicks "Review Code".
2. `App.jsx` calls `reviewApi.reviewCode()`, which POSTs to `/api/review`.
3. FastAPI validates the payload against `CodeReviewRequest` (Pydantic).
   Empty code or oversized submissions are rejected before any processing.
4. `routers/review.py` delegates to `services/code_analyzer.analyze_code()`.
5. `code_analyzer`:
   a. Detects the language (`language_detector.py`) using the frontend's
      hint first, falling back to filename extension, then regex heuristics.
   b. Runs static analysis (`static_analysis.py`) if the language is
      supported (Python today).
   c. Builds a structured prompt instructing the LLM to return JSON only,
      and calls the configured provider (`llm_service.py`).
   d. Parses the LLM's JSON response defensively — malformed JSON or a
      missing field degrades gracefully instead of crashing the request.
   e. Merges LLM findings with static-analysis findings and computes a
      transparent 0-100 score by subtracting a fixed penalty per finding,
      weighted by severity.
6. The full `CodeReviewResponse` is returned and rendered by `ReviewPanel.jsx`.

## Why Ollama as the default

Azure OpenAI (the technology named in the original job/project brief)
requires a paid Azure subscription and an API key, which makes a project
unusable by anyone who doesn't have one — a poor fit for "everyone should
be able to run this." Ollama:

- Is open-source and free.
- Runs entirely on the user's own machine (or the Docker Compose stack) —
  no data ever leaves the device, which is also a meaningful privacy/security
  win when reviewing proprietary source code.
- Supports strong open-weight coding models (Qwen2.5-Coder, CodeLlama,
  DeepSeek-Coder, StarCoder2) that perform well on code-review tasks.

Cloud free tiers (Groq, Hugging Face) remain available for users who want
faster responses than CPU-only local inference and are fine using a
third-party API for a demo.

## Extending to a new language's static analysis

To add JavaScript/TypeScript support via ESLint, for example:

1. Add an `_run_eslint()` function in `static_analysis.py` following the
   exact same pattern as `_run_bandit()` (subprocess call, timeout, JSON
   parsing, `Finding` construction).
2. Add `"javascript"` / `"typescript"` to the language check in
   `run_static_analysis()`.
3. Nothing else changes — the router, orchestrator, and frontend are
   already language-agnostic.

## Extending to a new LLM provider

1. Create a new class implementing `BaseLLMProvider.generate()` in
   `llm_service.py`.
2. Add its configuration fields to `config.py`.
3. Add one branch to the `get_llm_provider()` factory function.

No other file needs to change.
