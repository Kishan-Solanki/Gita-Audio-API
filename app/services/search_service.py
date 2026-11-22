"""Search service: full-text and verse-reference search across shloks."""

from __future__ import annotations

import re
import unicodedata

from sqlalchemy import func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Chapter, Shlok, ShlokContent
from app.schemas.content import ChapterResponse, SearchResultResponse, SearchShlokResult


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MAX_RESULTS = 50

# Matches verse references like "2.47", "2:47", "02.047"
_VERSE_REF_PATTERN = re.compile(r"^(\d{1,2})\s*[.:]\s*(\d{1,3})$")

# Rough check for Devanagari characters (Unicode block 0900-097F)
_DEVANAGARI_PATTERN = re.compile(r"[\u0900-\u097F]")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _normalize_query(raw: str) -> str:
    """Strip, collapse whitespace, and NFC-normalize the query string."""
    normalised = unicodedata.normalize("NFC", raw.strip())
    return re.sub(r"\s+", " ", normalised)


def _is_devanagari(query: str) -> bool:
    """Return ``True`` if the query contains any Devanagari characters."""
    return bool(_DEVANAGARI_PATTERN.search(query))


def _truncate_snippet(text_value: str, max_len: int = 200) -> str:
    """Truncate a text field to *max_len* characters with an ellipsis."""
    if len(text_value) <= max_len:
        return text_value
    return text_value[: max_len - 1] + "…"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def search(
    db: AsyncSession,
    query: str,
    lang: str = "en",
    limit: int = _MAX_RESULTS,
) -> SearchResultResponse:
    """Search shloks (and optionally chapters) for the given query.

    Behaviour:
      1. **Verse reference** (e.g. ``2.47`` or ``2:47``): exact chapter+verse
         lookup, ranked first.
      2. **Devanagari query**: ``ILIKE`` search on the ``sanskrit`` field of
         ``shloks``.
      3. **Latin query**: trigram similarity (``%``) on ``transliteration`` and
         trigram search on ``literal_meaning`` / ``simple_explanation`` in
         ``shlok_contents``.

    Results are capped at *limit* (default 50).

    Args:
        db: Async database session.
        query: User-supplied search string.
        lang: Language code for content-field searching.
        limit: Maximum number of shlok results.

    Returns:
        ``SearchResultResponse`` with matched shloks, chapters, and total.
    """
    limit = min(limit, _MAX_RESULTS)
    query = _normalize_query(query)

    if not query:
        return SearchResultResponse(shloks=[], chapters=[], total=0)

    shlok_results: list[SearchShlokResult] = []
    chapter_results: list[ChapterResponse] = []

    # --- 1. Verse reference detection ------------------------------------
    ref_match = _VERSE_REF_PATTERN.match(query)
    if ref_match:
        ch_num, vs_num = int(ref_match.group(1)), int(ref_match.group(2))
        exact = await _search_exact_verse(db, ch_num, vs_num, lang)
        if exact:
            shlok_results.append(exact)

    # --- 2. Text-based search --------------------------------------------
    remaining = limit - len(shlok_results)
    if remaining > 0:
        if _is_devanagari(query):
            hits = await _search_sanskrit(db, query, remaining)
        else:
            hits = await _search_latin(db, query, lang, remaining)

        # De-duplicate against any exact-match reference we already found
        seen_refs = {s.reference for s in shlok_results}
        for hit in hits:
            if hit.reference not in seen_refs:
                shlok_results.append(hit)
                seen_refs.add(hit.reference)
            if len(shlok_results) >= limit:
                break

    total = len(shlok_results) + len(chapter_results)
    return SearchResultResponse(
        shloks=shlok_results,
        chapters=chapter_results,
        total=total,
    )


# ---------------------------------------------------------------------------
# Private search strategies
# ---------------------------------------------------------------------------


async def _search_exact_verse(
    db: AsyncSession,
    chapter_num: int,
    verse_num: int,
    lang: str,
) -> SearchShlokResult | None:
    """Look up a shlok by exact chapter + verse numbers."""
    stmt = (
        select(Shlok, Chapter.number)
        .join(Chapter, Shlok.chapter_id == Chapter.id)
        .where(Chapter.number == chapter_num, Shlok.verse_number == verse_num)
    )
    row = (await db.execute(stmt)).first()
    if row is None:
        return None

    shlok: Shlok = row[0]
    ch: int = row[1]

    snippet = await _get_meaning_snippet(db, shlok.id, lang) or shlok.transliteration
    return SearchShlokResult(
        chapter=ch,
        verse=shlok.verse_number,
        reference=f"{ch}.{shlok.verse_number}",
        snippet=_truncate_snippet(snippet),
        sanskrit=shlok.sanskrit,
        transliteration=shlok.transliteration,
    )


async def _search_sanskrit(
    db: AsyncSession,
    query: str,
    limit: int,
) -> list[SearchShlokResult]:
    """ILIKE search on the ``sanskrit`` column (Devanagari queries)."""
    pattern = f"%{query}%"
    stmt = (
        select(Shlok, Chapter.number)
        .join(Chapter, Shlok.chapter_id == Chapter.id)
        .where(Shlok.sanskrit.ilike(pattern))
        .order_by(Chapter.number.asc(), Shlok.verse_number.asc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    rows = result.all()

    return [
        SearchShlokResult(
            chapter=ch_num,
            verse=s.verse_number,
            reference=f"{ch_num}.{s.verse_number}",
            snippet=_truncate_snippet(s.sanskrit),
            sanskrit=s.sanskrit,
            transliteration=s.transliteration,
        )
        for s, ch_num in rows
    ]


async def _search_latin(
    db: AsyncSession,
    query: str,
    lang: str,
    limit: int,
) -> list[SearchShlokResult]:
    """Trigram-based search on transliteration and content meaning fields.

    Uses PostgreSQL ``pg_trgm``'s ``%`` (similarity) operator on
    ``transliteration`` and ``ILIKE`` / trigram on ``literal_meaning``
    and ``simple_explanation``.
    """
    pattern = f"%{query}%"

    # Sub-query: shloks matching via transliteration trigram similarity
    transliteration_q = (
        select(
            Shlok.id.label("shlok_id"),
            func.similarity(Shlok.transliteration, query).label("score"),
        )
        .where(Shlok.transliteration.op("%")(query))
    ).subquery("trgm_trans")

    # Sub-query: shloks matching via content ILIKE
    content_q = (
        select(ShlokContent.shlok_id.label("shlok_id"))
        .where(
            ShlokContent.lang == lang,
            or_(
                ShlokContent.literal_meaning.ilike(pattern),
                ShlokContent.simple_explanation.ilike(pattern),
            ),
        )
        .distinct()
    ).subquery("content_match")

    # Union both sets of matching shlok IDs
    combined_ids = (
        select(transliteration_q.c.shlok_id)
        .union(select(content_q.c.shlok_id))
    ).subquery("combined")

    stmt = (
        select(Shlok, Chapter.number)
        .join(Chapter, Shlok.chapter_id == Chapter.id)
        .join(combined_ids, Shlok.id == combined_ids.c.shlok_id)
        .order_by(Chapter.number.asc(), Shlok.verse_number.asc())
        .limit(limit)
    )

    result = await db.execute(stmt)
    rows = result.all()

    out: list[SearchShlokResult] = []
    for shlok, ch_num in rows:
        snippet = await _get_meaning_snippet(db, shlok.id, lang) or shlok.transliteration
        out.append(
            SearchShlokResult(
                chapter=ch_num,
                verse=shlok.verse_number,
                reference=f"{ch_num}.{shlok.verse_number}",
                snippet=_truncate_snippet(snippet),
                sanskrit=shlok.sanskrit,
                transliteration=shlok.transliteration,
            )
        )
    return out


async def _get_meaning_snippet(
    db: AsyncSession,
    shlok_id: int,
    lang: str,
) -> str | None:
    """Return the first non-empty meaning text for a shlok in the given language."""
    content = await db.scalar(
        select(ShlokContent).where(
            ShlokContent.shlok_id == shlok_id,
            ShlokContent.lang == lang,
        )
    )
    if content is None:
        return None
    return content.simple_explanation or content.literal_meaning
