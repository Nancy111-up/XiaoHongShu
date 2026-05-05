# XiaoHongShu Brand Agent

Full-stack AI agent for automated XiaoHongShu (小红书) social media content operations.

## Project Structure

```
.
├── backend/         # FastAPI + LangGraph + SQLAlchemy + MCP (Python 3.12+)
│   ├── src/         # Application code (agent, api, services, models, schemas)
│   ├── tests/       # pytest (unit + integration)
│   ├── scripts/     # Utility scripts (mock demo, etc.)
│   ├── skills/      # MCP skill servers (media_crawler)
│   ├── data/        # Runtime data (SQLite DB) — gitignored
│   └── config.toml  # Business configuration
├── frontend/        # Next.js 16 + React 19 + Tailwind v4 + dnd-kit
│   └── src/         # App router, components, hooks, lib, store
└── docs/            # PRD, implementation plans, design assets
```

## Tech Stack

- **Backend**: FastAPI, LangGraph (10-node agent), Qwen LLM (DashScope), SQLite (aiosqlite)
- **Frontend**: Next.js 16 (App Router), TanStack Query, Zustand, @dnd-kit
- **Infra**: MCP protocol for tool servers, LangSmith for tracing

## Key URLs

- Backend API: http://localhost:8000/api/v1
- Frontend: http://localhost:3000
- API Docs: http://localhost:8000/docs

## Development

- Backend: `cd backend && uv run pytest`
- Frontend: `cd frontend && npm run dev`
