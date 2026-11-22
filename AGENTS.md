# Repository Guidelines

## Project Structure

`app/` contains the FastAPI application: routes in `app/routers/`, schemas in `app/schemas/`, database models in `app/db/`, and business logic in `app/services/`. Database migrations live in `alembic/`; automated tests are in `tests/`; import and audio registration utilities are in `scripts/`. Chapter audio and seed data live in `data/`, while Docker and Nginx configuration is in `deploy/`.

## Development Commands

Install development dependencies with `python -m pip install -e ".[dev]"`. Run locally with `uvicorn app.main:app --reload`. Start the full stack from `deploy/` with `docker compose up -d --build`, then apply schema changes with `alembic upgrade head`. Run the test suite with `pytest -v` and lint with `ruff check .`.

## Style and Tests

Use Python 3.12+, four-space indentation, and the 99-character line limit configured in Ruff. Use `snake_case` for functions and modules, `PascalCase` for classes, and `test_<feature>.py` for test files. Keep endpoint handlers small and put reusable logic in services. Add tests under `tests/` when changing behavior.

## Audio Data

Verse files use `data/chNN/slNN.mp3`; preserve the two-digit chapter and verse naming and update `data/iitk_audio_manifest.json` when refreshing files. Use `python scripts/register_audio.py --root data --dry-run` to preview database registration before applying it.

## Commits and Pull Requests

Use short, imperative commit subjects (for example, `Fix audio path resolution`). Describe behavior changes, configuration or migration steps, and test results in pull requests. Never commit populated `.env` files or production credentials.
