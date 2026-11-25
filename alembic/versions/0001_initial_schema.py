"""Create the initial application schema."""

from alembic import op

from app.db.base import Base
import app.db.models  # noqa: F401 -- register every model before creating metadata

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create tables and PostgreSQL trigram support for search indexes."""
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    bind = op.get_bind()
    # Ensure any created tables with timestamp without timezone are dropped/recreated cleanly if needed
    Base.metadata.create_all(bind=bind)
    # Alter created_at and updated_at to TIMESTAMPTZ in case tables already exist
    for table_name in ["chapters", "shloks", "shlok_contents", "topics", "reciters", "audio_tracks", "users", "refresh_tokens", "favorites", "listen_progress", "sanskar_completions"]:
        op.execute(f"ALTER TABLE IF EXISTS {table_name} ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE USING created_at AT TIME ZONE 'UTC'")
        op.execute(f"ALTER TABLE IF EXISTS {table_name} ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE USING updated_at AT TIME ZONE 'UTC'")


def downgrade() -> None:
    """Drop the application tables while leaving the shared extension installed."""
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
