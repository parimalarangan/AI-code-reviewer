"""
code_analyzer.py
=================
The orchestrator that ties everything together to produce one
`CodeReviewResponse`:

    1. Detect the programming language.
    2. Run open-source static-analysis tools (deterministic findings).
    3. Build a structured prompt and ask the configured LLM for a narrative
       review (bugs, security, performance, best practices).
    4. Parse the LLM's JSON response into `Finding` objects.
    5. Merge LLM findings + static-analysis findings.
    6. Compute a simple, explainable 0-100 quality score.

Keeping this logic in one place (rather than scattered across the router)
makes the code easy to test and easy to extend — e.g. adding a new static
tool or a new LLM provider never requires touching this file's overall
control flow, only the pieces it calls.
"""

import json
import logging

from app.config import Settings
from app.models.schemas import CodeReviewResponse, Finding, Severity
from app.services.language_detector import detect_language
from app.services.llm_service import LLMProviderError, extract_json_block, get_llm_provider
from app.services.static_analysis import run_static_analysis

logger = logging.getLogger(__name__)

_SEVERITY_PENALTY = {
    Severity.CRITICAL: 20,
    Severity.HIGH: 10,
    Severity.MEDIUM: 5,
    Severity.LOW: 2,
    Severity.INFO: 0,
}

_REVIEW_PROMPT_TEMPLATE = """You are a senior software engineer performing a rigorous code review.
Analyze the following {language} code and identify real, concrete issues.

Focus on four categories: bugs, security vulnerabilities, performance problems,
and best-practice / maintainability violations. Do not invent issues that are
not present in the code. If the code is genuinely clean, say so.

Respond with ONLY a single valid JSON object (no markdown fences, no prose
before or after) matching exactly this schema:

{{
  "summary": "<2-3 sentence plain-English overview of overall code quality>",
  "findings": [
    {{
      "line": <integer line number or null>,
      "category": "<one of: bug, security, performance, best_practice, style, maintainability>",
      "severity": "<one of: critical, high, medium, low, info>",
      "title": "<short title>",
      "explanation": "<why this is a problem>",
      "suggestion": "<concrete fix, or null>"
    }}
  ]
}}

Code to review:
```{language}
{code}
```
"""


def _build_prompt(code: str, language: str) -> str:
    """Construct the deterministic review prompt sent to the LLM."""
    return _REVIEW_PROMPT_TEMPLATE.format(language=language, code=code)


def _parse_llm_findings(raw_response: str) -> tuple[str, list[Finding]]:
    """
    Parse the LLM's raw text response into a (summary, findings) tuple.

    LLM output is inherently unreliable, so this function is defensive:
    malformed JSON or missing fields never crash the request — they just
    result in fewer findings and a fallback summary.
    """
    json_text = extract_json_block(raw_response)
    try:
        payload = json.loads(json_text)
    except json.JSONDecodeError:
        logger.warning("LLM response was not valid JSON; returning raw text as summary.")
        return raw_response.strip()[:500] or "The model did not return a parseable review.", []

    summary = payload.get("summary", "No summary provided by the model.")
    findings: list[Finding] = []
    for item in payload.get("findings", []):
        try:
            findings.append(
                Finding(
                    line=item.get("line"),
                    category=item.get("category", "best_practice"),
                    severity=item.get("severity", "info"),
                    title=item.get("title", "Untitled finding"),
                    explanation=item.get("explanation", ""),
                    suggestion=item.get("suggestion"),
                    source="llm",
                )
            )
        except Exception:  # noqa: BLE001 - a single malformed finding must not break the rest
            logger.warning("Skipping malformed finding from LLM output: %s", item)
            continue

    return summary, findings


def _compute_score(findings: list[Finding]) -> int:
    """
    Derive a simple, explainable 0-100 quality score by subtracting a fixed
    penalty per finding, weighted by severity. This is intentionally
    transparent (not another black-box LLM call) so users can understand
    exactly why their score is what it is.
    """
    score = 100
    for finding in findings:
        score -= _SEVERITY_PENALTY.get(finding.severity, 0)
    return max(0, min(100, score))


async def analyze_code(code: str, settings: Settings, language_hint: str | None = None, filename: str | None = None) -> CodeReviewResponse:
    """
    Main entry point called by the API router.

    Args:
        code: Raw source code submitted by the user.
        settings: Application settings (determines which LLM provider to use).
        language_hint: Optional language name supplied by the frontend editor.
        filename: Optional filename, used to help detect the language.

    Returns:
        A fully populated `CodeReviewResponse`.

    Raises:
        LLMProviderError: propagated to the router, which converts it into a
            clean HTTP error response rather than a raw 500.
    """
    language = detect_language(code, filename=filename, hint=language_hint)

    static_findings, static_summaries = run_static_analysis(code, language)

    provider = get_llm_provider(settings)
    prompt = _build_prompt(code, language)

    try:
        raw_response = await provider.generate(prompt, timeout_seconds=settings.LLM_REQUEST_TIMEOUT_SECONDS)
    except LLMProviderError:
        # Re-raise so the router can return a clear, actionable error to the
        # client instead of a generic 500. Static-analysis findings are
        # still valuable on their own, but we surface the failure rather
        # than silently hiding it, so users know the LLM half didn't run.
        raise

    llm_summary, llm_findings = _parse_llm_findings(raw_response)

    all_findings = llm_findings + static_findings
    score = _compute_score(all_findings)

    model_label = {
        "ollama": settings.OLLAMA_MODEL,
        "groq": settings.GROQ_MODEL,
        "huggingface": settings.HF_MODEL,
        "openai_compatible": settings.OPENAI_COMPATIBLE_MODEL,
    }.get(settings.LLM_PROVIDER.lower(), settings.LLM_PROVIDER)

    return CodeReviewResponse(
        language_detected=language,
        summary=llm_summary,
        findings=all_findings,
        static_analysis=static_summaries,
        overall_score=score,
        model_used=model_label,
    )
