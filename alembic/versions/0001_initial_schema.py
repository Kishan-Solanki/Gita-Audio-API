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
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    """Drop the application tables while leaving the shared extension installed."""
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
