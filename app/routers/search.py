"""Search endpoint for Gita library."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.deps import DBSession
from app.schemas.content import SearchResultResponse
from app.services.search_service import search

router = APIRouter(tags=["Search"])


@router.get(
    "/search",
    response_model=SearchResultResponse,
    summary="Search shloks and chapters",
)
async def search_gita(
    db: DBSession,
    q: str = Query(..., min_length=1, description="Search query (verse reference like 2.47, Sanskrit Devanagari, transliteration, or meaning text)"),
    lang: str = Query("en", description="Preferred language for meanings (en, hi)"),
    limit: int = Query(20, ge=1, le=50, description="Max results to return (capped at 50)"),
) -> SearchResultResponse:
    """Search shloks and chapters by verse reference ('2.47'), Sanskrit Devanagari,

    transliteration, or English/Hindi meanings.
    Results are ranked with exact verse matches first, followed by text relevance.
    """
    return await search(db, query=q, lang=lang, limit=limit)
