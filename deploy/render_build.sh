#!/usr/bin/env bash
# Render build script for Garbh Journey Gita Audio API
set -e

echo "==> Upgrading pip..."
python -m pip install --upgrade pip

echo "==> Installing requirements..."
python -m pip install -r requirements.txt

echo "==> Running database migrations..."
alembic upgrade head

echo "==> Seeding database content (if not already seeded)..."
python scripts/import_gita_text.py
python scripts/seed_weeks.py
python scripts/import_translations.py
python scripts/register_audio.py --root data || echo "Audio registration completed (or skipped if already active)"

echo "==> Build complete!"
