"""FastAPI application entry point — 应用工厂 + 生命周期"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.config import _setup_langsmith_env

_setup_langsmith_env()

from src.agent.graph import build_graph
from src.agent.tools.mcp_client import get_mcp_manager
from src.api.middleware import APIKeyMiddleware, setup_cors
from src.api.router import router
from src.db.checkpointer import close_checkpointer, create_checkpointer
from src.db.session import close_db, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    checkpointer = await create_checkpointer()
    app.state.checkpointer = checkpointer
    app.state.graph = build_graph(checkpointer=checkpointer)
    await get_mcp_manager().connect()
    yield
    await close_checkpointer()
    await close_db()


def _custom_openapi(app: FastAPI):
    """注入 ApiKeyHeader 安全方案，使 Swagger UI 显示 Authorize 锁图标。"""
    from fastapi.openapi.utils import get_openapi

    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    schema.setdefault("components", {})["securitySchemes"] = {
        "ApiKeyHeader": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
        }
    }
    schema["security"] = [{"ApiKeyHeader": []}]
    app.openapi_schema = schema
    return schema


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
    app.openapi = lambda: _custom_openapi(app)
    return app


app = create_app()
