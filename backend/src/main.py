"""FastAPI application entry point — 应用工厂 + 生命周期"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.middleware import APIKeyMiddleware, setup_cors
from src.api.router import router
from src.db.session import close_db, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await close_db()


def create_app() -> FastAPI:
    app = FastAPI(
        title="XHS Brand Agent",
        description="小红书自主品牌运营专家 — AI Agent 后端服务",
        version="0.1.0",
        lifespan=lifespan,
    )

    setup_cors(app)
    app.add_middleware(APIKeyMiddleware)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    app.include_router(router)
    return app


app = create_app()
