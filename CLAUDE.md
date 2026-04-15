# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

洛克王国精灵图鉴 (Roco Kingdom Pokédex) — a full-stack app that scrapes game data from an external site, stores it in MySQL, and serves it via a FastAPI backend + Vue 3 frontend.

## Common Commands

### Backend (Python, managed by `uv`)

```bash
uv sync                                              # Install/sync dependencies
uv run uvicorn api.main:app --reload --port 8000     # Start API dev server
uv run python main.py                                # Run full scrape+import pipeline
uv run python scripts/<script>.py                    # Run a single import script
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
External game site → scraper/ → main.py → MySQL → api/repositories → api/services → api/routes → Vue frontend
```

### Backend Layers (api/)

Three-layer pattern: **routes → services → repositories**. All database access is async via `aiomysql` connection pool (initialized in `api/main.py` lifespan). Response shapes are defined in `api/schemas/`. There is a single router file (`api/routes/pokemon.py`) mounted in `api/main.py`.

### Database (db/)

- `db/connection.py` — Dual connection strategy: synchronous `pymysql` for scripts/imports, async `aiomysql` pool for the API
- `db/schema.py` — DDL table creation
- `db/repository.py` — Sync upsert functions used by the import pipeline

### Import Pipeline

`main.py` orchestrates the import by calling `scripts/*.py` as subprocesses. Each script in `scripts/` is independently runnable and handles one data domain (egg groups, evolution chains, maps, skill stones, etc.).

### Frontend (front/pc-front/)

Vue 3 + TypeScript + Vite + Vue Router. API calls go through `src/api/pokemon.ts`. Views: Home (grid), PokemonDetail, SkillList, SkillStone, Map (MapLibre GL), BodyMatch. API base URL is configured via `.env.development` / `.env.production`.

## Key Configuration

- `.env` (root) — MySQL connection config, read by `config.py` via `python-dotenv`
- `config.py` — Exports `DB_CONFIG` dict and `BASE_URL` (scraping target)
- `front/pc-front/.env.development` / `.env.production` — Frontend API base URL
