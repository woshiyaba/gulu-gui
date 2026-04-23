# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

洛克王国精灵图鉴 (Roco Kingdom Pokédex) — a full-stack app that scrapes game data from an external site, imports it into MySQL, migrates to PostgreSQL for the API layer, and serves it via a FastAPI backend + Vue 3 frontend. Includes a LangChain-based chatbot agent accessible via WebSocket (QQ bot integration).

## Common Commands

### Backend (Python, managed by `uv`)

```bash
uv sync                                              # Install/sync dependencies
uv run uvicorn api.main:app --reload --port 8000     # Start API dev server (Swagger at /docs)
uv run python main.py                                # Run full scrape+import pipeline
uv run python scripts/<script>.py                    # Run a single import/migration script
uv run python agents/main_agent.py                   # Run chatbot agent CLI
uv run python -m compileall api                      # Syntax check (there is no test suite)
```

There is no configured formatter, linter, or pytest suite. `compileall` + the frontend `type-check` are the de-facto PR checks (per AGENTS.md).

### Desktop frontend (Vue 3 + Vite, in `front/pc-front/`)

```bash
cd front/pc-front
npm install
npm run dev              # Dev server (localhost:5173)
npm run build            # Production build (type-check + vite build)
npm run type-check       # TypeScript check only (vue-tsc --build)
```

### Mini-app frontend (uni-app, in `front/mini-app/`)

Multi-platform uni-app — builds for H5, WeChat Mini Program, and other `@dcloudio/uni-mp-*` targets. Not WeChat-only.

```bash
cd front/mini-app
npm install
npm run dev:h5           # H5 dev build
npm run dev:mp-weixin    # WeChat Mini Program dev build
npm run build:mp-weixin  # WeChat Mini Program production build
npm run type-check       # vue-tsc --noEmit
```

## Architecture

### Data Flow

```
External game site → scraper/ → main.py → MySQL → migration scripts → PostgreSQL
PostgreSQL → api/repositories → api/services → api/routes → Vue frontend
                                                         → WebSocket → QQ bot (via agents/)
```

### Backend Layers (api/)

Three-layer pattern: **routes → services → repositories**. All database access at the API layer is async via a `psycopg` (PostgreSQL) connection pool initialized in `api/main.py` lifespan. Response shapes live in `api/schemas/`.

Three routers mounted in `api/main.py`:
- `api/routes/pokemon.py` — Public Pokédex endpoints (`/api/pokemon`, `/api/attributes`, `/api/skills`, etc.)
- `api/routes/ops.py` — Admin/ops endpoints (`/api/ops/`) with Bearer token auth for CRUD on pokemon, users, dicts, evolution chains. Bootstrap runs on startup via `ensure_ops_bootstrap()`.
- `api/routes/ws_route.py` — WebSocket endpoint (`/ws`) for QQ bot message handling

CORS is fully open (`allow_origins=["*"]`) — keep this in mind before deploying.

### Database (db/)

- `db/connection.py` — Dual connection strategy: synchronous `pymysql` (MySQL) for scraper/import scripts, async `psycopg` pool (PostgreSQL) for the API
- `db/schema.py` — DDL table creation (MySQL)
- `db/repository.py` — Sync upsert functions used by the import pipeline (MySQL)
- `sql/wikiroco.sql` — PostgreSQL schema reference

### Import Pipeline

`main.py` is the orchestrator: it runs `db.schema.init_db()` for table setup, then invokes `scripts/*.py` as subprocesses for each domain (egg groups/hatch, attribute matchups, obtain methods, etc.). Many scrape-and-upsert steps inside `main.py` are currently commented out — re-enable them when a full refresh from the external source is needed. Each script in `scripts/` is independently runnable.

Migration scripts (`scripts/migrate_mysql_to_pg*.py`) move data from MySQL to PostgreSQL. Other `scripts/sync_*` scripts sync specific data slices incrementally without a full re-migration.

### Chatbot Agent (agents/)

LangChain/LangGraph-based agent (`agents/main_agent.py`) answers game questions by calling the FastAPI backend via a `call_api` tool. Skill definitions in `skills/<skill-name>/SKILL.md` describe available API endpoints — the agent reads these as context. Connected to users via WebSocket through `ws/handlers/qq_agent_handler.py`.

### WebSocket Layer (ws/)

`ws/ws_manager.py` — Connection manager mapping user IDs to WebSocket connections. `ws/handlers/qq_agent_handler.py` — Processes incoming QQ messages and routes them to the agent.

### Frontends

- `front/pc-front/` — Vue 3 + TypeScript + Vite + Vue Router. API calls go through `src/api/pokemon.ts`. Views include Home (grid), PokemonDetail, SkillList, SkillStone, Map (MapLibre GL), BodyMatch.
- `front/mini-app/` — uni-app (H5 + WeChat MP + other mini-program platforms). Separate `node_modules` and build toolchain.

## Key Configuration

- `.env` (root, gitignored) — read by `config.py` via `python-dotenv`.
  - MySQL: `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_DATABASE`, `MYSQL_USER`, `MYSQL_PASSWORD`
  - PostgreSQL: `PG_HOST`, `PG_PORT`, `PG_DATABASE`, `PG_USER`, `PG_PASSWORD`
  - Static assets (optional, default to `https://wikiroco.com/...`): `STATIC_BASE_URL`, `FRIEND_IMAGE_UPLOAD_DIR`, `YISE_IMAGE_UPLOAD_DIR`, `SKILL_ICON_UPLOAD_DIR`, `RESONANCE_MAGIC_ICON_UPLOAD_DIR`
- `config.py` — Exports `DB_CONFIG` (MySQL), `PG_CONFIG` (PostgreSQL), `BASE_URL` (scraping target, currently hardcoded), and the static-asset URL/upload-dir constants used when serving/uploading images.
- Frontend API base URL lives in `front/pc-front/.env.development` / `.env.production` — update there rather than hardcoding in components.

## Conventions

- Commit messages follow Conventional Commits (`feat:`, `fix:`, etc.) — see recent `git log` for examples.
- Python: 4-space indentation, `snake_case`, small layered modules.
- Vue/TS: `PascalCase.vue` components, `camelCase.ts` utilities/composables.
