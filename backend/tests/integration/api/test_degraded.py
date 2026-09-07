from fastapi.testclient import TestClient

from src.app import create_app
from src.db.base import Base
from src.db.session import create_session_factory


def test_no_history_returns_explicit_unavailable_response(tmp_path) -> None:
    factory = create_session_factory(f"sqlite+aiosqlite:///{(tmp_path / 'empty.db').as_posix()}")

    async def create_schema() -> None:
        async with factory() as session, session.bind.begin() as connection:  # type: ignore[union-attr]
            await connection.run_sync(Base.metadata.create_all)

    import asyncio

    asyncio.run(create_schema())
    response = TestClient(create_app(factory)).get("/api/opportunities")
    assert response.status_code == 200
    assert response.json() == {"items": [], "data_source": "unavailable"}
