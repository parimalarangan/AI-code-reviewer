"""
routers/review.py
==================
HTTP layer for code review. Keeps request/response handling and error
translation separate from business logic (`code_analyzer.py`), following
the standard FastAPI "thin router, fat service" pattern.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.config import Settings, get_settings
from app.models.schemas import CodeReviewRequest, CodeReviewResponse
from app.services.code_analyzer import analyze_code
from app.services.llm_service import LLMProviderError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["review"])


@router.post(
    "/review",
    response_model=CodeReviewResponse,
    summary="Analyze submitted source code and return a structured AI code review.",
)
async def review_code(
    request: CodeReviewRequest, settings: Settings = Depends(get_settings)
) -> CodeReviewResponse:
    """
    Accept source code and return bugs, security issues, performance notes,
    and best-practice feedback.

    - **code**: the raw source code to review (required).
    - **language**: optional hint (e.g. "python"); auto-detected if omitted.
    - **filename**: optional filename, improves language auto-detection.

    Returns HTTP 413 if the submission exceeds the configured size limit,
    and HTTP 502 if the configured LLM provider is unreachable or
    misconfigured (with a message explaining how to fix it).
    """
    if len(request.code) > settings.MAX_CODE_LENGTH_CHARS:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                f"Submitted code is {len(request.code)} characters, which exceeds the "
                f"{settings.MAX_CODE_LENGTH_CHARS}-character limit. Please review smaller "
                "files or functions at a time."
            ),
        )

    try:
        return await analyze_code(
            code=request.code,
            settings=settings,
            language_hint=request.language,
            filename=request.filename,
        )
    except LLMProviderError as exc:
        logger.error("LLM provider error: %s", exc)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 - convert any unexpected error into a clean 500
        logger.exception("Unexpected error during code review.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while reviewing the code.",
        ) from exc
