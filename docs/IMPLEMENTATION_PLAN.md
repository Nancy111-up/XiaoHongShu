# 小红书自主品牌运营专家 V1.5 — 技术实现拆解计划

> **最后更新**: 2026-05-04 | **当前进度**: Phase 1 完成 (14/14), Phase 3 部分完成 (3/5)

---

## 0. 现状审计

### 已完成 ✅

| 模块 | 状态 | 说明 |
|------|------|------|
| 四层配置体系 | ✅ | `config.toml` + `.env` + `config.py` + `pyproject.toml` |
| DashScope Qwen LLM 客户端 | ✅ | `src/agent/tools/llm_client.py` — qwen-turbo / qwen-plus |
| AgentState 完整字段矩阵 | ✅ | 24 字段，对齐 PRD §6.4，包含 TopicCard / FeedbackRecord / VisualGuidance 子结构体 |
| LangGraph 10 节点完整拓扑 | ✅ | 全部 10 节点 + 2 条件边 + 1 interrupt，使用 AsyncSqliteSaver |
| JSON 结构化输出 | ✅ | generate_copy / generate_visuals 强制 JSON，3 层提取降级 |
| 合规审核双层机制 | ✅ | Layer 1 敏感词词典 + Layer 2 Qwen-Turbo LLM 五维审核 |
| Human-in-the-loop | ✅ | interrupt() + Command(resume) 断点审核 |
| 资产进化 Pipeline | ✅ | finalize 节点内置：一稿过→best_practices，高轮次→negative_prompts，Token>8000 瘦身标记 |
| 反馈规则提取 | ✅ | extract_rules 节点：4+4 few-shot 分类器 → negative_prompts.md |
| SqliteSaver 持久化 | ✅ | AsyncSqliteSaver 工厂 + aiosqlite monkey-patch 兼容方案 |
| Pydantic Schemas | ✅ | common (统一信封)、agent (请求/响应)、board (看板) |
| SQLAlchemy ORM | ✅ | Task 模型 (tasks 表)，declarative base |
| FastAPI 应用层 | ✅ | main.py 应用工厂 + lifespan + middleware |
| API 端点 | ✅ | /agent/discover, /start, /status/{id}, /feedback, /cancel/{id}, /board |
| 业务服务层 | ✅ | task_service (CRUD + 状态机), board_service (看板聚合) |
| 核心工具 | ✅ | exceptions.py, constants.py, sensitive_words.py, mcp_client.py |

### 已知差距 ⚠️

| 差距 | 严重度 | 说明 |
|------|--------|------|
| `deps.py` 缺失 | P1 | 依赖注入散落在各模块；plan 中有规划但未创建独立文件 |
| main.py 未初始化 graph/checkpointer | **P0** | lifespan 只管理 DB，没有创建 graph + checkpointer 实例 |
| `/start` 不运行 Graph | **P0** | 当前只创建 DB Task 记录，不执行 LangGraph workflow |
| `/feedback` 不使用 Command(resume) | **P0** | 当前只更新 DB，不通过 graph resume 触发后续节点 |
| `models/kanban.py` 缺失 | P2 | kanban 列位置用 Task.column 字段存储，无独立 kanban 模型 |
| `services/evolution_service.py` 缺失 | P2 | 进化逻辑已内嵌在 finalize.py 节点中，未抽成独立 service |

### 遗留文件

| 文件 | 状态 | 说明 |
|------|------|------|
| `src/agent/nodes/write.py` | 遗留 | Phase 1 原始 generate 节点，已被 generate_copy.py 取代 |
| `src/agent/tools/tavily_search.py` | 遗留 | Phase 2 将替换为 MediaCrawler MCP |
| `src/agent/nodes/research.py` | 额外 | plan 中未规划，需确认用途或清理 |

---

## 1. 后端目录结构（当前实际态）

```
backend/
├── pyproject.toml
├── config.toml
├── .env / .env.example
├── alembic/ + alembic.ini              # ⚠️ 未创建
├── data/                               # SQLite + assets
│   ├── xhs_agent.db
│   └── assets/
│       ├── brand_voice.md
│       ├── product_info.md
│       ├── negative_prompts.md
│       └── best_practices.md
├── src/
│   ├── __init__.py
│   ├── config.py                       # ✅ Pydantic Settings
│   ├── main.py                         # ✅ FastAPI 应用工厂 (⚠️ 缺少 graph 初始化)
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── router.py                   # ✅ 聚合所有子路由
│   │   ├── middleware.py               # ✅ X-API-Key + CORS
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── agent.py                # ✅ /api/v1/agent/* (⚠️ 不运行 graph)
│   │       └── board.py                # ✅ /api/v1/board
│   │
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── state.py                    # ✅ 24 字段完整 AgentState + 工厂函数
│   │   ├── graph.py                    # ✅ 10 节点完整拓扑 + AsyncSqliteSaver
│   │   ├── nodes/
│   │   │   ├── __init__.py
│   │   │   ├── init_task.py            # ✅ 节点 1 — 纯逻辑，初始化任务
│   │   │   ├── crawl_trends.py         # ✅ 节点 2 — MCP/Tavily 趋势抓取
│   │   │   ├── load_assets.py          # ✅ 节点 3 — 品牌资产加载
│   │   │   ├── generate_copy.py        # ✅ 节点 4 — JSON 结构化文案生成
│   │   │   ├── generate_visuals.py     # ✅ 节点 5 — 视觉策划 + 国产模型 prompt
│   │   │   ├── compliance.py           # ✅ 节点 6 — 双层合规审核
│   │   │   ├── human_review.py         # ✅ 节点 7 — interrupt() 断点
│   │   │   ├── handle_feedback.py      # ✅ 节点 8 — 纯路由节点
│   │   │   ├── extract_rules.py        # ✅ 节点 9 — 反馈规则提取
│   │   │   ├── finalize.py             # ✅ 节点 10 — 资产进化 + Token 瘦身
│   │   │   ├── write.py                # ⚠️ 遗留 (Phase 1 原始节点)
│   │   │   └── research.py             # ⚠️ 额外文件
│   │   └── tools/
│   │       ├── __init__.py
│   │       ├── llm_client.py           # ✅ DashScope Qwen 客户端
│   │       ├── mcp_client.py           # ✅ langchain-mcp-adapters 封装
│   │       ├── sensitive_words.py      # ✅ 敏感词词典
│   │       └── tavily_search.py        # ⚠️ 遗留 (Phase 2 替换)
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py                     # ✅ SQLAlchemy declarative base
│   │   └── task.py                     # ✅ Task ORM (含 kanban column 字段)
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── common.py                   # ✅ APIResponse 统一信封 + 子结构体 schema
│   │   ├── agent.py                    # ✅ Agent 请求/响应 schemas
│   │   └── board.py                    # ✅ Kanban 相关 schemas
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── asset_loader.py             # ✅ 品牌资产读写 + append_to_asset
│   │   ├── task_service.py             # ✅ 任务 CRUD + 状态机
│   │   └── board_service.py            # ✅ 看板聚合查询
│   │
│   ├── db/
│   │   ├── __init__.py
│   │   ├── session.py                  # ✅ aiosqlite 异步 session
│   │   └── checkpointer.py             # ✅ AsyncSqliteSaver 工厂 + monkey-patch
│   │
│   └── core/
│       ├── __init__.py
│       ├── exceptions.py               # ✅ 自定义异常类
│       └── constants.py                # ✅ 魔法数字 + 枚举集中管理
│
├── skills/                              # ❌ Phase 2 — MediaCrawler MCP Server
└── tests/                               # ❌ Phase 5 — 测试套件
```

---

## 2. 核心数据结构（前后端协议基础）

### 2.1 AgentState 完整定义（已实现 ✅）

```python
# src/agent/state.py — 已实现 24 字段，对齐 PRD §5 + §6.4
class AgentState(TypedDict, total=False):
    user_input: str
    thread_id: str
    topic_cards: list[TopicCard]
    draft_copy: str
    visual_guidance: VisualGuidance
    is_revision: bool
    human_feedback: str
    edited_draft_copy: str
    feedback_action: str               # "approve" | "revise"
    feedback_history: list[FeedbackRecord]
    draft_versions: list[str]
    revision_count: int
    final_copy: str
    brand_context: str
    product_context: str
    best_practices: str
    negative_prompts: str
    trends_context: str
    compliance_severity: str           # "pass" | "mild_warning" | "severe_violation"
    violation_count: int
    current_step: str
    error_logs: list[str]
```

### 2.2 SQLAlchemy ORM 模型（已实现 ✅）

```python
# src/models/task.py — 已实现
class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[str]              # UUID PK (thread_id)
    user_input: Mapped[str]
    source: Mapped[str]          # "inspiration_pool" | "manual"
    status: Mapped[str]          # "in_progress" | "waiting_for_human" | "done" | "cancelled"
    revision_count: Mapped[int]
    current_step: Mapped[str | None]
    draft_copy: Mapped[str | None]
    visual_guidance_json: Mapped[str | None]
    final_copy: Mapped[str | None]
    feedback_history_json: Mapped[str | None]
    column: Mapped[str]          # "inspiration" | "in_progress" | "pending_review" | "done"
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
```

### 2.3 Pydantic Schemas（已实现 ✅）

- `APIResponse[T]` — 统一响应信封 (success, data, error, meta)
- `DiscoverRequest`, `StartRequest`, `FeedbackRequest` — Agent 请求
- `AgentStatusResponse` — 任务状态响应
- `TopicCardSchema`, `TaskCardSchema`, `KanbanBoardResponse` — 看板

---

## 3. API 接口协议详细设计

| 方法 | 路径 | 请求 Body | 响应 `data` | 状态 |
|------|------|-----------|-------------|------|
| `POST` | `/api/v1/agent/discover` | `{keyword?: string}` | `TopicCardSchema[]` | ✅ 已实现 (via Tavily) |
| `POST` | `/api/v1/agent/start` | `{topic: string, source: string}` | `{thread_id: string}` | ⚠️ 不运行 Graph |
| `GET` | `/api/v1/agent/status/{thread_id}` | — | `AgentStatusResponse` | ✅ 已实现 |
| `POST` | `/api/v1/agent/feedback` | `FeedbackRequest` | `{thread_id, action}` | ⚠️ 不调用 Command(resume) |
| `POST` | `/api/v1/agent/cancel/{thread_id}` | — | `{thread_id, status: "cancelled"}` | ✅ 已实现 |
| `GET` | `/api/v1/board` | — | `KanbanBoardResponse` | ✅ 已实现 |

---

## 4. LangGraph Agent 完整拓扑（已实现 ✅）

```
START → init_task → crawl_trends → load_assets → generate_copy → generate_visuals
                                                                       │
                                                                  compliance
                                                                  │       │
                                                        pass/     │   severe_
                                                     mild_warning │  violation
                                                             │    │    │
                                                        ┌────┘    │  <3次→generate_copy
                                                        ▼         │  ≥3次→END
                                                   human_review   │
                                                   (interrupt)    │
                                                        │         │
                                                   handle_feedback│
                                                   │           │
                                               approve      revise
                                                   │           │
                                                   ▼           ▼
                                               finalize   extract_rules → generate_copy (loop)
                                                   │
                                                   ▼
                                                  END
```

### 4.1 各节点实现要点（全部实现 ✅）

| 节点 | 文件 | 关键行为 |
|------|------|----------|
| 1. init_task | `init_task.py` | 纯逻辑，初始化 thread_id + revision_count + violation_count |
| 2. crawl_trends | `crawl_trends.py` | Tavily 趋势搜索 → Qwen-Turbo 提炼为结构化 trends_context |
| 3. load_assets | `load_assets.py` | 读取 4 个 .md → brand/product/best/negative context |
| 4. generate_copy | `generate_copy.py` | Qwen-Plus JSON 结构化输出，3 层提取降级，revision 模式跳过趋势 |
| 5. generate_visuals | `generate_visuals.py` | JSON 结构化 VisualGuidance，国产模型 prompt，外模检测 |
| 6. compliance | `compliance.py` | Layer 1 敏感词 + Layer 2 LLM 五维审核，violation_count 追踪 |
| 7. human_review | `human_review.py` | interrupt() 断点，返回 draft/visual/severity 供前端审核面板 |
| 8. handle_feedback | `handle_feedback.py` | 纯路由：approve→final_copy，revise→revision_count++、draft_versions 快照 |
| 9. extract_rules | `extract_rules.py` | Qwen-Turbo 4+4 few-shot 分类器 → negative_prompts.md，非规则丢弃 |
| 10. finalize | `finalize.py` | 一稿过→best_practices.md，高轮次→negative_prompts.md，Token>8000 瘦身标记 |

### 4.2 条件边（已实现 ✅）

| 源节点 | 目标节点 | 条件 |
|--------|----------|------|
| compliance | human_review | severity = pass 或 mild_warning |
| compliance | generate_copy | severity = severe_violation 且累计 < 3 次 |
| compliance | END | severity = severe_violation 且累计 >= 3 次 |
| handle_feedback | finalize | action = approve |
| handle_feedback | extract_rules | action = revise |

---

## 5. 前端架构（待实现 ❌）

前端架构设计保持不变，详见原计划 §5.1-5.3。

---

## 6. 分阶段实施计划

### Phase 1: 后端核心 ✅ 完成 (2026-05-04)

| 任务 | 内容 | 状态 |
|------|------|------|
| 1.1 | 扩展 `AgentState` 至 PRD 完整字段 (24 fields + 3 子结构体) | ✅ |
| 1.2 | 新增 `src/schemas/` — Pydantic 请求/响应模型 | ✅ |
| 1.3 | 新增 `src/models/` — SQLAlchemy Task ORM | ✅ |
| 1.4 | 新增 `src/db/` — aiosqlite session + AsyncSqliteSaver 工厂 | ✅ |
| 1.5 | 新增 `src/core/exceptions.py` + `constants.py` | ✅ |
| 1.6 | 新增 `src/api/middleware.py` — X-API-Key + CORS | ✅ |
| 1.7 | 新增 `src/api/v1/agent.py` — 全部 Agent 端点 | ✅ (⚠️ 不运行 Graph) |
| 1.8 | 新增 `src/api/v1/board.py` — 看板聚合端点 | ✅ |
| 1.9 | 新增 `src/main.py` — FastAPI 应用工厂 + 生命周期 | ✅ (⚠️ 缺少 graph 初始化) |
| 1.10 | 新增 `src/services/task_service.py` — 任务 CRUD | ✅ |
| 1.11 | 新增 `src/services/board_service.py` — 看板聚合 | ✅ |
| 1.12 | 扩展 `src/agent/graph.py` — 完整 10 节点拓扑 | ✅ |
| 1.13 | 新增所有缺失节点 (Round 5: 5.1-5.9) | ✅ |
| 1.14 | 新增 MCP Client 封装 (`src/agent/tools/mcp_client.py`) | ✅ |

**Round 5 子轮次明细**:
| 子轮次 | 内容 | 新建/修改文件 |
|--------|------|--------------|
| 5.1-5.4 | (前置 session 完成) | state.py, schemas/, models/, db/session.py, services/, api/ |
| 5.5 | generate_visuals 节点 | `nodes/generate_visuals.py` (214 行) |
| 5.6 | compliance 重写 + human_review 独立 | `nodes/compliance.py` (重写), `nodes/human_review.py` (新建) |
| 5.7 | handle_feedback + extract_rules + append_to_asset | `nodes/handle_feedback.py`, `nodes/extract_rules.py`, `services/asset_loader.py` (更新) |
| 5.8 | generate_copy 增强 + finalize | `nodes/generate_copy.py` (新建), `nodes/finalize.py` (新建) |
| 5.9 | 图拓扑重写 + SqliteSaver | `graph.py` (重写), `db/checkpointer.py` (新建) |

### Phase 2: MediaCrawler MCP Server（未开始 ❌，预计 2-3 天）

| 任务 | 内容 | 优先级 |
|------|------|--------|
| 2.1 | `skills/media_crawler/server.py` — MCP Server 骨架 | P0 |
| 2.2 | `browser_manager.py` — Playwright 单例生命周期 | P0 |
| 2.3 | `login_manager.py` — Cookie 持久化 + 扫码恢复 | P0 |
| 2.4 | `pipeline.py` — 爬取 + 数据清洗 | P0 |
| 2.5 | `tools.py` — search_trends / get_note_detail / check_health | P0 |
| 2.6 | 替换现有 Tavily 搜索为 MCP 调用 + 清理遗留文件 | P0 |

### Phase 3: 资产进化 Pipeline（部分完成 ⚠️，预计 1 天剩余）

| 任务 | 内容 | 状态 |
|------|------|------|
| 3.1 | `services/evolution_service.py` — 独立进化服务 | ❌ (逻辑内嵌在 finalize.py) |
| 3.2 | 一稿过 → best_practices.md 提取 | ✅ (finalize.py: 调用 Qwen-Turbo 提取结构模式) |
| 3.3 | 高轮次反思 → negative_prompts.md | ✅ (finalize.py: revision_count>3 时提取教训) |
| 3.4 | Token 瘦身机制（> 8000 触发瘦身标记） | ✅ (finalize.py: _estimate_state_tokens + error_logs 标记) |
| 3.5 | 创建/维护 brand assets 初始文件 | ⚠️ (需确认 assets/ 下文件完整性) |

### Phase 4: 前端（未开始 ❌，预计 4-5 天）

同原计划 §5，10 项任务 (4.1-4.10)，状态全部 ❌。

### Phase 5: 测试 + 文档（未开始 ❌，预计 2 天）

| 任务 | 内容 | 优先级 |
|------|------|--------|
| 5.1 | 单元测试 (pytest — 目标 80% 覆盖) | P0 |
| 5.2 | API 集成测试 (httpx + pytest-asyncio) | P0 |
| 5.3 | E2E 工作流测试 (Playwright) | P1 |
| 5.4 | ruff + mypy + bandit 全量通过 | P0 |

---

## 7. P0 优先事项：API-Graph 集成（预计 1 天）

当前最关键的缺失环节 — API 层和 Graph 层之间存在断层，需要 3 项修复：

### 7.1 main.py: lifespan 初始化 graph + checkpointer

```python
# main.py lifespan 需补充:
from src.agent.graph import build_graph
from src.db.checkpointer import create_checkpointer, close_checkpointer

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    checkpointer = await create_checkpointer()
    app.state.graph = build_graph(checkpointer=checkpointer)
    yield
    await close_checkpointer()
    await close_db()
```

### 7.2 `/start` 端点: 真正运行 Graph

```python
# agent.py /start 需改为:
from fastapi import Request

@router.post("/start")
async def start_task(req: StartRequest, request: Request, db: AsyncSession = Depends(get_db)):
    task = await create_task(db, user_input=req.topic, source=req.source)
    from src.agent.state import create_initial_state
    initial = create_initial_state(req.topic)
    graph = request.app.state.graph
    # 异步启动 graph 执行（后台任务）
    import asyncio
    asyncio.create_task(graph.ainvoke(initial, config={"configurable": {"thread_id": task.id}}))
    return APIResponse.ok({"thread_id": task.id})
```

### 7.3 `/feedback` 端点: 使用 Command(resume)

```python
# agent.py /feedback 需改为:
from langgraph.types import Command

@router.post("/feedback")
async def submit_feedback(req: FeedbackRequest, request: Request, db: AsyncSession = Depends(get_db)):
    graph = request.app.state.graph
    if req.action == "revise":
        resume_cmd = Command(resume={
            "feedback_action": "revise",
            "human_feedback": req.feedback,
            "edited_draft_copy": req.edited_content,
        })
        asyncio.create_task(
            graph.ainvoke(resume_cmd, config={"configurable": {"thread_id": req.thread_id}})
        )
    else:
        resume_cmd = Command(resume={
            "feedback_action": "approve",
            "edited_draft_copy": req.edited_content,
        })
        asyncio.create_task(
            graph.ainvoke(resume_cmd, config={"configurable": {"thread_id": req.thread_id}})
        )
    return APIResponse.ok({"thread_id": req.thread_id, "action": req.action})
```

---

## 8. 关键技术决策

1. **前端框架选型**：推荐 **Next.js 14 (App Router)**
2. **Kanban 拖拽库**：推荐 `@dnd-kit/core`
3. **富文本编辑器**：审核面板微调轨使用 `TipTap`
4. **LLM JSON 结构化输出**：✅ 已采用 prompt 强制 JSON + 3 层提取 (direct → codeblock → regex)
5. **MCP Server 通信**：Agent 侧用 `langchain-mcp-adapters` 的 `MultiServerMCPClient`；前端不需要直接连接 MCP
6. **并发控制**：后端用数据库行锁确保同一时间仅一个任务 `in_progress`
7. **aiosqlite 兼容方案**：✅ langgraph-checkpoint-sqlite 2.0.x 调用 `conn.is_alive()` 但 aiosqlite 0.22.x 未实现 → module-level monkey-patch `aiosqlite.Connection.is_alive = lambda self: True`

---

## 9. 风险与注意事项

- **MediaCrawler 爬取稳定性**：小红书反爬严格，需充分降级处理；MCP Server 应设计为独立进程
- **Cookie 登录态**：首次部署需人工扫码，过期后前端展示二维码重新登录
- **LLM 输出格式一致性**：✅ 已通过 3 层 JSON 提取 + 降级策略覆盖
- **Token 瘦身精度**：压缩可能丢失有价值资产，瘦身后需监控一稿过率变化
- **SQLite 并发写限制**：单写者模型，对于单租户本地部署足够；未来如需多用户需迁移 PostgreSQL
- **[新增] API-Graph 断层**：当前 API 端点只操作 DB 不驱动 Graph engine，是 P0 必须修复项
- **[新增] 遗留文件清理**：write.py / tavily_search.py / research.py 需在 Phase 2 确认并清理
