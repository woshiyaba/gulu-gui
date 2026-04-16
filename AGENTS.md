# Repository Guidelines

## Project Structure & Module Organization
`api/` contains the FastAPI service: `routes/` defines endpoints, `services/` holds business logic, `repositories/` wraps database access, and `schemas/` defines response models. `db/` manages connections and schema helpers. `scraper/` and the root `main.py` handle data collection and import flows. Batch migration and sync utilities live in `scripts/`, with SQL assets in `sql/` and reference data in `docs/`.

Frontend code is split by target. `front/pc-front/` is the Vue 3 + Vite desktop web app. `front/mini-app/` is the uni-app client for H5 and WeChat Mini Program builds.

## Build, Test, and Development Commands
Backend setup and run from the repo root:

```bash
uv sync
uv run uvicorn api.main:app --reload --port 8000
uv run python main.py
uv run python -m compileall api
```

Use `main.py` for initial data import or refreshes. Use `compileall` as a quick syntax check when changing Python modules.

Desktop frontend:

```bash
cd front/pc-front
npm install
npm run dev
npm run build
npm run type-check
```

Mini app frontend:

```bash
cd front/mini-app
npm install
npm run dev:h5
npm run dev:mp-weixin
npm run type-check
```

## Coding Style & Naming Conventions
Follow the existing style in each area. Python uses 4-space indentation, `snake_case` for functions and modules, and small layered modules by responsibility. TypeScript/Vue files use `PascalCase` for components such as `PokemonCard.vue`, `camelCase` for utilities and composables such as `useTheme.ts`, and route/page folders that match features.

No formatter or linter is currently wired in; keep imports tidy, avoid unrelated refactors, and preserve the repo’s established naming.

## Testing Guidelines
There is no dedicated `tests/` suite yet. Before opening a PR, run `uv run python -m compileall api`, `npm run type-check` in affected frontend packages, and the relevant production build (`npm run build` or `npm run build:mp-weixin`) when UI code changes. Add focused tests alongside new automated test infrastructure if you introduce it.

## Commit & Pull Request Guidelines
Recent history uses short, task-focused messages, often with Conventional Commit prefixes such as `feat:`. Prefer messages like `feat: add PG migration script` or `fix: correct pokemon detail mapping`.

PRs should include a brief summary, impacted areas (`api`, `front/pc-front`, `scripts`, etc.), setup or migration notes, and screenshots for UI changes. Link related issues and note any required `.env` or database updates.

## Security & Configuration Tips
Keep secrets in `.env`; never commit real database credentials. Backend config currently reads both MySQL and PostgreSQL settings from environment variables in `config.py`. When changing API hosts for frontends, update the environment-specific files under each frontend package rather than hardcoding endpoints in components.
