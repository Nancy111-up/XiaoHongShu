from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(title="体育品牌运营 Agent", version="0.1.0")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "sports-brand-agent"}

    return app
