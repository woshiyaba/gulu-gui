# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

洛克王国精灵图鉴 (Roco Kingdom Pokédex) — a full-stack app that scrapes game data from an external site, imports it into MySQL, migrates to PostgreSQL for the API layer, and serves it via a FastAPI backend + Vue 3 frontend. Includes a LangChain-based chatbot agent accessible via WebSocket (QQ bot integration).

## Common Commands

### Backend (Python, managed by `uv`)

```bash
uv sync                                              # Install/sync dependencies
uv run uvicorn api.main:app --reload --port 8000     # Start API dev server
uv run python main.py                                # Run full scrape+import pipeline
uv run python scripts/<script>.py                    # Run a single import script
uv run python agents/main_agent.py                   # Run chatbot agent CLI
```

### Frontend (Vue 3 + Vite, in `front/pc-front/`)

```bash
cd front/pc-front
npm install              # Install dependencies
npm run dev              # Dev server (localhost:5173)
npm run build            # Production build (type-check + vite build)
npm run type-check       # TypeScript check only (vue-tsc --build)
```

## Architecture

### Data Flow

```
External game site → scraper/ → main.py → MySQL → migration scripts → PostgreSQL
PostgreSQL → api/repositories → api/services → api/routes → Vue frontend
                                                         → WebSocket → QQ bot (via agents/)
```

### Backend Layers (api/)

Three-layer pattern: **routes → services → repositories**. All database access is async via `psycopg` (PostgreSQL) connection pool (initialized in `api/main.py` lifespan). Response shapes are defined in `api/schemas/`.

Three routers mounted in `api/main.py`:
- `api/routes/pokemon.py` — Public Pokédex endpoints (`/api/pokemon`, `/api/attributes`, `/api/skills`, etc.)
- `api/routes/ops.py` — Admin/ops endpoints (`/api/ops/`) with Bearer token auth for CRUD on pokemon, users, dicts, evolution chains
- `api/routes/ws_route.py` — WebSocket endpoint (`/ws`) for QQ bot message handling

### Database (db/)

- `db/connection.py` — Dual connection strategy: synchronous `pymysql` (MySQL) for scraper/import scripts, async `psycopg` pool (PostgreSQL) for the API
- `db/schema.py` — DDL table creation (MySQL)
- `db/repository.py` — Sync upsert functions used by the import pipeline (MySQL)
- `sql/wikiroco.sql` — PostgreSQL schema reference

### Import Pipeline

`main.py` orchestrates the import by calling `scripts/*.py` as subprocesses. Each script in `scripts/` is independently runnable and handles one data domain (egg groups, evolution chains, maps, skill stones, etc.). Data lands in MySQL first; migration scripts (`scripts/migrate_mysql_to_pg*.py`) move it to PostgreSQL.

### Chatbot Agent (agents/)

LangChain/LangGraph-based agent (`agents/main_agent.py`) that answers game questions by calling the FastAPI backend via a `call_api` tool. Skill definitions in `skills/*/SKILL.md` describe available API endpoints — the agent reads these as context. Connected to users via WebSocket through `ws/handlers/qq_agent_handler.py`.

### WebSocket Layer (ws/)

`ws/ws_manager.py` — Connection manager mapping user IDs to WebSocket connections. `ws/handlers/qq_agent_handler.py` — Processes incoming QQ messages and routes them to the agent.

### Frontend

- `front/pc-front/` — Vue 3 + TypeScript + Vite + Vue Router. API calls go through `src/api/pokemon.ts`. Views: Home (grid), PokemonDetail, SkillList, SkillStone, Map (MapLibre GL), BodyMatch.
- `front/mini-app/` — WeChat mini-app frontend (separate build toolchain).

## Key Configuration

- `.env` (root) — MySQL + PostgreSQL connection config, read by `config.py` via `python-dotenv`. Required vars: `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_DATABASE`, `MYSQL_USER`, `MYSQL_PASSWORD`, `PG_HOST`, `PG_PORT`, `PG_DATABASE`, `PG_USER`, `PG_PASSWORD`
- `config.py` — Exports `DB_CONFIG` (MySQL), `PG_CONFIG` (PostgreSQL), and `BASE_URL` (scraping target)
- `front/pc-front/.env.development` / `.env.production` — Frontend API base URL
