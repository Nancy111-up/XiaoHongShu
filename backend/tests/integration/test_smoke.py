"""集成冒烟测试 — API ↔ Graph 集成验证"""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from src.main import create_app


@pytest.fixture(scope="module")
def client():
    """使用 Starlette TestClient（正确处理 lifespan 事件）。"""
    app = create_app()
    with TestClient(app) as c:
        yield c


def test_health_check(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_graph_attached_to_app_state(client):
    """lifespan 已将 graph + checkpointer 挂到 app.state。"""
    app = client.app
    assert hasattr(app.state, "graph"), "app.state 缺少 graph"
    assert app.state.graph is not None
    assert hasattr(app.state, "checkpointer"), "app.state 缺少 checkpointer"


def test_start_returns_thread_id(client):
    """POST /start 返回有效 thread_id。"""
    resp = client.post(
        "/api/v1/agent/start",
        json={"topic": "测试话题", "source": "manual"},
        headers={"X-API-Key": "dev-api-key-change-me"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert len(data["data"]["thread_id"]) == 36


def test_graph_topology():
    """验证 10 节点完整拓扑。"""
    from src.agent.graph import build_graph

    graph = build_graph(checkpointer=None)
    compiled = graph.get_graph() if hasattr(graph, "get_graph") else graph
    raw_nodes = compiled.nodes if hasattr(compiled, "nodes") else {}

    if isinstance(raw_nodes, dict):
        node_names = set(raw_nodes.keys())
    else:
        node_names = {n if isinstance(n, str) else getattr(n, "name", str(n)) for n in raw_nodes}

    expected = {
        "__start__",
        "init_task", "crawl_trends", "load_assets", "generate_copy",
        "generate_visuals", "compliance", "human_review", "handle_feedback",
        "extract_rules", "finalize",
    }
    missing = expected - node_names
    assert not missing, f"缺失节点: {missing}"


def test_all_modules_import():
    """全部模块可导入（回归检查）。"""
    import importlib
    from pathlib import Path

    src = Path(__file__).parent.parent.parent / "src"
    errors: list[str] = []

    for py_file in sorted(src.rglob("*.py")):
        if py_file.name == "__init__.py":
            continue
        rel = py_file.relative_to(src.parent).with_suffix("")
        mod_name = ".".join(rel.parts)
        try:
            importlib.import_module(mod_name)
        except Exception as e:
            errors.append(f"{mod_name}: {e}")

    assert not errors, f"{len(errors)} 模块导入失败:\n" + "\n".join(errors)
