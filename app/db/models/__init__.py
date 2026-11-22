"""Re-export every ORM model so Alembic (and application code) can do::

    from app.db.models import User, Chapter, Shlok, ...
"""

from app.db.models.content import (
    AudioTrack,
    Chapter,
    ChapterTopic,
    Reciter,
    Shlok,
    ShlokContent,
    ShlokTopic,
    Topic,
)
from app.db.models.pregnancy import WeekShlok, WeekTheme
from app.db.models.user import (
    Favorite,
    ListenProgress,
    RefreshToken,
    SanskarCompletion,
    User,
)

__all__ = [
    # content
    "Chapter",
    "Shlok",
    "ShlokContent",
    "Topic",
    "ChapterTopic",
    "ShlokTopic",
    "Reciter",
    "AudioTrack",
    # pregnancy
    "WeekTheme",
    "WeekShlok",
    # user
    "User",
    "RefreshToken",
    "Favorite",
    "ListenProgress",
    "SanskarCompletion",
]
