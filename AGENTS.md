# Repository Guidelines

## Project Overview
This repository is a full-stack Roco Kingdom Pokédex application. It scrapes game data from external sources, imports and syncs it into PostgreSQL, serves the data through a FastAPI backend, and provides Vue-based frontends. It also includes a LangChain/LangGraph chatbot agent that answers game questions through the backend and can be reached over WebSocket for QQ bot integration.

## Project Structure & Module Organization
`api/` contains the FastAPI service. Keep the backend layered as `routes/` for HTTP/WebSocket endpoints, `services/` for business logic, `repositories/` for database access, and `schemas/` for response models. `api/main.py` initializes the async PostgreSQL connection pool and mounts routers.

`db/` exposes PostgreSQL connection helpers. API code uses async `psycopg` through the shared pool; standalone scripts often open their own `psycopg2` connections via `config.PG_CONFIG`.

`scraper/` provides scraping helpers. Data collection, imports, syncs, seeds, and one-off migrations live in standalone scripts under `scripts/`. SQL assets live in `sql/`, with `sql/wikiroco.sql` as the schema reference. Reference and design documents live in `docs/`.

`agents/` contains the LangChain/LangGraph chatbot agent. `skills/<skill-name>/SKILL.md` files describe API-backed capabilities that the agent can load as context. `ws/` contains WebSocket connection handling and QQ-agent routing.

Frontend code is split by target. `front/pc-front/` is the Vue 3 + TypeScript + Vite desktop web app. `front/mini-app/` is the uni-app client for H5, WeChat Mini Program, and other `@dcloudio/uni-mp-*` targets.

## Architecture Notes
Data flow:

```text
External game sites -> scraper/ + scripts/ -> PostgreSQL
PostgreSQL -> api/repositories -> api/services -> api/routes -> Vue frontend
                                                        -> WebSocket -> QQ bot via agents/
```

Important backend areas:

- `api/routes/pokemon.py` exposes public Pokédex endpoints such as pokemon, attributes, and skills.
- `api/routes/ops.py` exposes admin/ops endpoints under `/api/ops/` with Bearer token auth and startup bootstrap via `ensure_ops_bootstrap()`.
- `api/routes/ws_route.py` exposes the `/ws` WebSocket endpoint for QQ bot message handling.
- CORS is currently open with `allow_origins=["*"]`; review this before deployment.

Important frontend areas:

- `front/pc-front/src/api/pokemon.ts` centralizes desktop frontend API calls.
- Desktop views include Home, PokemonDetail, SkillList, SkillStone, Map with MapLibre GL, and BodyMatch.
- The mini app has its own dependency tree and build toolchain separate from the desktop frontend.

## Build, Test, and Development Commands
Backend setup and run from the repo root:

```bash
uv sync
uv run uvicorn api.main:app --reload --port 8000
uv run python scripts/<script>.py
uv run python agents/main_agent.py
uv run python -m compileall api
```

There is no configured Python formatter, linter, or pytest suite. Use `compileall` as the quick syntax check when changing Python modules.

Desktop frontend:

```bash
cd front/pc-front
npm install
npm run dev
npm run build
npm run type-check
```

`npm run dev` starts Vite, normally on `localhost:5173`. `npm run build` runs type-checking and the production Vite build.

Mini app frontend:

```bash
cd front/mini-app
npm install
npm run dev:h5
npm run dev:mp-weixin
npm run build:mp-weixin
npm run type-check
```

Run individual scripts under `scripts/` for data refreshes. There is no top-level import orchestrator; each script is independently runnable and may write directly to PostgreSQL.

## Configuration
Keep secrets in `.env`; never commit real database credentials. `config.py` reads root `.env` through `python-dotenv`.

Backend PostgreSQL settings:

- `PG_HOST`
- `PG_PORT`
- `PG_DATABASE`
- `PG_USER`
- `PG_PASSWORD`

Static asset settings are also defined through `config.py`, with defaults pointing to `https://wikiroco.com/...` where applicable:

- `STATIC_BASE_URL`
- `FRIEND_IMAGE_UPLOAD_DIR`
- `YISE_IMAGE_UPLOAD_DIR`
- `SKILL_ICON_UPLOAD_DIR`
- `RESONANCE_MAGIC_ICON_UPLOAD_DIR`

Frontend API base URLs should be updated in environment-specific files such as `front/pc-front/.env.development` and `front/pc-front/.env.production`. Do not hardcode API hosts in components.

## Coding Style & Naming Conventions
Follow the existing style in each area. Python uses 4-space indentation, `snake_case` for functions and modules, and small layered modules by responsibility. Keep imports tidy and avoid unrelated refactors.

TypeScript and Vue files use `PascalCase` for components such as `PokemonCard.vue`, `camelCase` for utilities and composables such as `useTheme.ts`, and route/page folders that match features.

No formatter or linter is currently wired in. Preserve the repo's established naming and formatting unless a file already follows a more specific local pattern.

## Frontend UI Constraints
For dynamic lists and popup containers, use a fixed frame with internal scrolling. Any area whose item count changes, such as search results, pagination panels, popup panels, waterfall lists, or vertical lists, must keep a stable container size instead of growing or shrinking with content.

Use `height` rather than only `max-height` for the panel, set `display: flex` and `flex-direction: column`, keep headers and search inputs at `flex-shrink: 0`, and put scrolling content in a `flex: 1; min-height: 0` region. Avoid layouts where the top edge jumps as content changes, such as `max-height` combined with bottom alignment. See `front/mini-app/pages/more/pokemon-eggs.vue` and `front/mini-app/pages/change-egg/publish.vue` for reference patterns.

## Testing Guidelines
There is no dedicated automated `tests/` suite yet. Before opening a PR or handing off code, run the checks that match the touched areas:

- Python API changes: `uv run python -m compileall api`
- Desktop frontend changes: `npm run type-check` in `front/pc-front/`, plus `npm run build` for production-impacting UI changes
- Mini app changes: `npm run type-check` in `front/mini-app/`, plus `npm run build:mp-weixin` when WeChat Mini Program output is affected

Add focused tests alongside new automated test infrastructure if you introduce it.

## Commit & Pull Request Guidelines
Recent history uses short, task-focused messages, often with Conventional Commit prefixes such as `feat:` and `fix:`. Prefer messages like `feat: add PG migration script` or `fix: correct pokemon detail mapping`.

PRs should include a brief summary, impacted areas such as `api`, `front/pc-front`, `front/mini-app`, or `scripts`, setup or migration notes, and screenshots for UI changes. Link related issues and note any required `.env` or database updates.

## Security & Data Safety
Do not commit secrets, real credentials, production dumps, or generated files containing private data. Be careful with scripts under `scripts/` because they can write directly to PostgreSQL. Confirm the intended database before running imports, syncs, seeds, or migrations.
