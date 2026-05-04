# 小红书自主品牌运营专家 V1.5 — 技术实现拆解计划

## 0. 现状审计

**已有**：
- 四层配置体系（`config.toml` + `.env` + `config.py` + `pyproject.toml`）✅ 符合 PRD
- 品牌资产 3/4 文件（缺 `best_practices.md`）
- 简化版 AgentState TypedDict（缺 10+ 字段）
- 简化版 LangGraph（4 节点，缺 6 节点）
- Tavily 搜索（非 PRD 指定的 MediaCrawler MCP）
- `MemorySaver`（非 PRD 指定的 SQLite）
- DashScope Qwen LLM 客户端

**缺失**：FastAPI 应用层、全部 API 端点、SQLite 持久化、前端、MediaCrawler MCP Server、视觉策划节点、资产进化 Pipeline、Token 瘦身、鉴权中间件、Kanban 业务服务层

---

## 1. 后端目录结构（目标态）

```
backend/
├── pyproject.toml
├── config.toml
├── .env / .env.example
├── alembic/ + alembic.ini
├── data/                        # SQLite + cookies
├── src/
│   ├── __init__.py
│   ├── config.py                # ✅ 已有，需扩展
│   ├── main.py                  # ❌ FastAPI 入口
│   ├── deps.py                  # ❌ 依赖注入（get_db, get_settings, get_graph）
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── router.py            # ❌ 聚合所有子路由
│   │   ├── middleware.py        # ❌ X-API-Key 鉴权 + CORS
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── agent.py         # ❌ /api/v1/agent/* 端点
│   │       └── board.py         # ❌ /api/v1/board 端点
│   │
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── state.py             # ⚠️ 需扩展至 PRD 6.4 完整字段
│   │   ├── graph.py             # ⚠️ 需扩展至 PRD 6.5 完整拓扑
│   │   ├── nodes/
│   │   │   ├── __init__.py
│   │   │   ├── init_task.py     # ❌ 节点1
│   │   │   ├── crawl_trends.py  # ❌ 节点2（MediaCrawler MCP）
│   │   │   ├── load_assets.py   # ❌ 节点3（独立节点）
│   │   │   ├── generate_copy.py # ⚠️ 需增强 JSON 结构化输出
│   │   │   ├── generate_visuals.py # ❌ 节点5
│   │   │   ├── compliance.py    # ⚠️ 需增强 LLM 二次判定
│   │   │   ├── human_review.py  # ⚠️ 已嵌入 graph.py，独立
│   │   │   ├── handle_feedback.py # ❌ 节点8
│   │   │   ├── extract_rules.py # ❌ 节点9（异步旁路）
│   │   │   └── finalize.py      # ❌ 节点10
│   │   └── tools/
│   │       ├── __init__.py
│   │       ├── llm_client.py    # ✅ 已有
│   │       ├── mcp_client.py    # ❌ langchain-mcp-adapters 封装
│   │       └── sensitive_words.py # ❌ 敏感词词典（compliance 用）
│   │
│   ├── models/                   # SQLAlchemy ORM
│   │   ├── __init__.py
│   │   ├── base.py              # ❌ declarative base
│   │   ├── task.py              # ❌ 创作任务卡片
│   │   └── kanban.py            # ❌ 看板列/快照
│   │
│   ├── schemas/                  # Pydantic 请求/响应模型
│   │   ├── __init__.py
│   │   ├── agent.py             # ❌ Agent 相关 schemas
│   │   ├── board.py             # ❌ Kanban 相关 schemas
│   │   └── common.py            # ❌ 统一响应信封
│   │
│   ├── services/                 # 业务逻辑层
│   │   ├── __init__.py
│   │   ├── asset_loader.py      # ✅ 已有，需扩展
│   │   ├── task_service.py      # ❌ 任务 CRUD + 状态机
│   │   ├── board_service.py     # ❌ 看板聚合查询
│   │   └── evolution_service.py # ❌ 资产进化 Pipeline
│   │
│   ├── db/
│   │   ├── __init__.py
│   │   ├── session.py           # ❌ aiosqlite 异步 session
│   │   └── checkpointer.py      # ❌ SqliteSaver 工厂
│   │
│   └── core/
│       ├── __init__.py
│       ├── exceptions.py        # ❌ 自定义异常
│       └── constants.py         # ❌ 魔法数字集中管理
│
├── skills/                       # ❌ MediaCrawler MCP Server
│   └── media_crawler/
│       ├── __init__.py
│       ├── server.py            # MCP Server 入口
│       ├── tools.py             # search_trends / get_note_detail / check_health
│       ├── browser_manager.py   # Playwright 单例
│       ├── login_manager.py     # Cookie 持久化
│       └── pipeline.py          # 爬取管线
│
└── tests/
    ├── __init__.py
    ├── conftest.py              # ❌ fixtures
    ├── unit/
    │   ├── test_state.py
    │   ├── test_config.py
    │   ├── test_compliance.py
    │   └── ...
    ├── integration/
    │   ├── test_api_agent.py
    │   ├── test_api_board.py
    │   └── ...
    └── e2e/
        └── test_workflow.py
```

---

## 2. 核心数据结构（前后端协议基础）

### 2.1 AgentState 完整定义（对齐 PRD §5 + §6.4）

```python
# src/agent/state.py — 目标态
from typing import TypedDict, List, NotRequired

class TopicCard(TypedDict):
    title: str
    reason: str
    heat_index: int
    estimated_traffic: str

class FeedbackRecord(TypedDict):
    round: int
    feedback: str

class VisualGuidance(TypedDict):
    cover_suggestion: str
    shot_descriptions: List[str]
    domestic_image_prompts: List[str]

class AgentState(TypedDict, total=False):
    # 基础
    user_input: str
    thread_id: str

    # 选题
    topic_cards: List[TopicCard]

    # 过程产物
    draft_copy: str
    visual_guidance: VisualGuidance
    is_revision: bool

    # 人类交互
    human_feedback: str
    edited_draft_copy: str
    feedback_action: str               # "approve" | "revise"
    feedback_history: List[FeedbackRecord]
    draft_versions: List[str]

    # 审核追踪
    revision_count: int
    final_copy: str

    # 品牌资产上下文
    brand_context: str
    product_context: str
    best_practices: str
    negative_prompts: str

    # 节点间传递上下文
    trends_context: str
    compliance_severity: str           # "pass" | "mild_warning" | "severe_violation"
    violation_count: int

    # 系统追踪
    current_step: str
    error_logs: List[str]
```

### 2.2 SQLAlchemy ORM 模型

```python
# src/models/task.py
class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[str]         # UUID, PK — 即 thread_id
    user_input: Mapped[str]
    source: Mapped[str]     # "inspiration_pool" | "manual"
    status: Mapped[str]     # "in_progress" | "waiting_for_human" | "done" | "cancelled"
    revision_count: Mapped[int]
    current_step: Mapped[str | None]

    # 内容快照（JSON 列）
    draft_copy: Mapped[str | None]
    visual_guidance_json: Mapped[str | None]  # JSON string
    final_copy: Mapped[str | None]
    feedback_history_json: Mapped[str | None]

    # Kanban 列位置
    column: Mapped[str]     # "inspiration" | "in_progress" | "pending_review" | "done"

    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
```

### 2.3 Pydantic Schemas（前后端协议核心）

```python
# src/schemas/common.py — 统一响应信封
class APIResponse[T](BaseModel):
    success: bool
    data: T | None = None
    error: str | None = None
    meta: dict | None = None  # {total, page, limit} 分页用

# src/schemas/agent.py
class DiscoverRequest(BaseModel):
    keyword: str | None = None  # 为空则自动发现

class StartRequest(BaseModel):
    topic: str
    source: str = "manual"  # "manual" | "inspiration"

class AgentStatusResponse(BaseModel):
    thread_id: str
    status: str             # "running" | "waiting_for_human" | "done" | "cancelled"
    current_step: str
    draft_copy: str | None
    visual_guidance: VisualGuidanceSchema | None
    error_logs: list[str]

class FeedbackRequest(BaseModel):
    thread_id: str
    action: str             # "approve" | "revise"
    feedback: str = ""
    edited_content: str = ""

# src/schemas/board.py
class TopicCardSchema(BaseModel):
    card_id: str
    title: str
    reason: str
    heat_index: int
    estimated_traffic: str
    created_at: datetime

class TaskCardSchema(BaseModel):
    thread_id: str
    user_input: str
    status: str
    column: str
    revision_count: int
    draft_copy: str | None
    final_copy: str | None
    visual_guidance: VisualGuidanceSchema | None
    created_at: datetime
    updated_at: datetime

class KanbanBoardResponse(BaseModel):
    inspiration: list[TopicCardSchema]
    in_progress: list[TaskCardSchema]
    pending_review: list[TaskCardSchema]
    done: list[TaskCardSchema]
```

---

## 3. API 接口协议详细设计

| 方法 | 路径 | 请求 Body | 响应 `data` | 说明 |
|------|------|-----------|-------------|------|
| `POST` | `/api/v1/agent/discover` | `{keyword?: string}` | `TopicCardSchema[]` | 手动触发热点发现，返回选题卡片列表 |
| `POST` | `/api/v1/agent/start` | `{topic: string, source: string}` | `{thread_id: string}` | 启动创作任务，返回 thread_id |
| `GET` | `/api/v1/agent/status/{thread_id}` | — | `AgentStatusResponse` | 查询任务进度与中间产物 |
| `POST` | `/api/v1/agent/feedback` | `FeedbackRequest` | `{thread_id: string, action: string}` | 提交审核判决。approve → finalize；revise → 重写+规则提取 |
| `POST` | `/api/v1/agent/cancel/{thread_id}` | — | `{thread_id: string, status: "cancelled"}` | 取消进行中任务 |
| `GET` | `/api/v1/board` | — | `KanbanBoardResponse` | 获取看板四列全量数据 |

**前端轮询策略**：
- 当 `status === "in_progress"` 时，前端每 2 秒轮询 `GET /api/v1/agent/status/{thread_id}`
- 当 `status` 变为 `"waiting_for_human"` 时，停止轮询，显示 alert 通知
- 审核面板通过 `GET /api/v1/board` 获取最新卡片数据后渲染

---

## 4. LangGraph Agent 完整拓扑（对齐 PRD §6）

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
                                                finalize   extract_rules (async)
                                                    │      generate_copy (loop)
                                                    ▼
                                                   END
```

### 4.1 各节点实现要点

**节点 1: init_task**
- 纯逻辑，无模型调用
- `thread_id = uuid4()`
- 判断 `source`: 若来自灵感池 → 从 `topic_cards` 提取；若手动 → 直接用 `user_input`
- 初始化 `revision_count = 0`, `is_revision = False`, `violation_count = 0`

**节点 2: crawl_trends**
- 通过 `langchain-mcp-adapters` 调用 MediaCrawler MCP `search_trends` Tool
- MCP Tool 返回 `[{title, likes, comments, collects, url}, ...]`
- 调用 Qwen-Turbo 提炼为结构化 `trends_context`：叙事角度(2-3)、高频关键词、标题特征、结构模式
- 超时 30s；超时 → `error_logs` 追加 + 降级创作
- **与现有 Tavily 搜索替换**：移除 `src/agent/tools/tavily_search.py`，改为 MCP 集成

**节点 3: load_assets**
- 从当前 write_node 中拆出为独立节点（符合 PRD）
- 读取 4 个 .md → `brand_context`, `product_context`, `best_practices`, `negative_prompts`

**节点 4: generate_copy**
- 主力 LLM（Qwen-Plus / GLM-4）
- 强制 JSON 结构化输出：`{"title": "...", "body": "...", "tags": ["..."], "ad_placement": "..."}`
- `is_revision=True` 时：跳过趋势上下文，只基于 `human_feedback` 重写
- 追加 `draft_versions` 快照

**节点 5: generate_visuals**
- 强制输出 `Visual_Guidance` JSON 结构
- 2-3 个国产模型适配 prompt（CogView / 文心一格 / 通义万相）
- 禁止输出外网模型 prompt（校验逻辑在节点内）

**节点 6: compliance**
- 第一层：敏感词词典匹配（可配置列表，当前硬编码改为从 `config.toml` 加载）
- 第二层：LLM 二次判定 → `pass` / `mild_warning` / `severe_violation`
- 严重违规 ≥ 3 次 → 直接 END，卡片标记"审核不通过"

**节点 7: human_review**
- `interrupt()` 断点，状态持久化 SQLite
- 返回 `{action: "waiting_for_human", draft_copy, visual_guidance}`

**节点 8: handle_feedback**
- 纯逻辑路由
- `approve` → `final_copy = edited_draft_copy or draft_copy`，路由 finalize
- `revise` → `is_revision = True`, `revision_count += 1`，路由 generate_copy；异步触发 extract_rules

**节点 9: extract_rules（异步旁路）**
- 小模型 Qwen-Turbo 判定反馈是否为通用规则
- 是 → 追加写入 `negative_prompts.md`（带时间戳注释）
- 否 → 丢弃 (`NOT_A_RULE`)

**节点 10: finalize**
- `revision_count == 0` → 提取范文结构 → `best_practices.md`
- `revision_count > 3` → 深层反思 → `negative_prompts.md`
- Token 总量 > 8000 → 触发瘦身

### 4.2 条件边 (Conditional Edges)

| 源节点 | 目标节点 | 条件 |
|--------|----------|------|
| compliance | human_review | severity = pass 或 mild_warning |
| compliance | generate_copy | severity = severe_violation 且累计 < 3 次 |
| compliance | END | severity = severe_violation 且累计 >= 3 次 |
| handle_feedback | finalize | action = approve |
| handle_feedback | generate_copy | action = revise |

---

## 5. 前端架构

### 5.1 页面/组件树

```
App
├── AppShell (全局布局：header + sidebar)
│   ├── Header
│   │   ├── BrandLogo
│   │   ├── NavMenu
│   │   └── AgentStatusBadge  (idle / running / waiting)
│   │
│   └── KanbanBoard (主视图 — 四列拖拽看板)
│       ├── Column: AI灵感池
│       │   ├── ColumnHeader ("📍 AI 灵感池" + 计数)
│       │   ├── DiscoverButton ("发现热点")
│       │   └── TopicCard[] (可勾选 + 拖拽)
│       │
│       ├── Column: AI创作中
│       │   ├── ColumnHeader ("🚀 AI 创作中" + 计数)
│       │   ├── NewTaskInput (手动输入主题 + "新建"按钮)
│       │   └── TaskCard[] (Loading 骨架屏状态)
│       │
│       ├── Column: 待人工审核
│       │   ├── ColumnHeader ("👀 待人工审核" + alert badge)
│       │   └── TaskCard[] (点击弹出审核面板)
│       │       └── ReviewDrawer (抽屉式审核面板)
│       │           ├── Tab: 微调轨 (富文本框 + 保存通过)
│       │           └── Tab: 重做轨 (反馈文本区 + 发送重做)
│       │
│       └── Column: 已完成归档
│           ├── ColumnHeader ("✅ 已完成归档" + 计数)
│           └── TaskCard[] (一键复制按钮)
│               ├── CopyButton[文案]
│               └── CopyButton[提示词]
```

### 5.2 前端关键状态管理

```typescript
// 使用 TanStack Query 管理服务端状态
// 使用 Zustand 管理客户端 UI 状态

// Zustand Store
interface KanbanStore {
  // UI state
  selectedCardId: string | null
  isReviewDrawerOpen: boolean
  activeReviewTab: "edit" | "feedback"

  // Actions
  selectCard: (id: string) => void
  openReview: (id: string) => void
  closeReview: () => void
}

// TanStack Query Hooks
useKanbanBoard()        // GET /api/v1/board — 每 3s 轮询
useDiscoverTopics()     // POST /api/v1/agent/discover
useStartTask()          // POST /api/v1/agent/start
useTaskStatus(id)       // GET /api/v1/agent/status/{id} — 2s 轮询
useSubmitFeedback()     // POST /api/v1/agent/feedback
useCancelTask(id)       // POST /api/v1/agent/cancel/{id}
```

### 5.3 设计方向建议
- **编辑/杂志风格**：符合小红书平台的审美调性
- 柔和的暖色调（燕麦白底 + 摩卡棕 accent），匹配品牌 L'Atelier Luna 的法式轻奢调性
- 卡片设计有明确层次感与留白韵律
- 微交互动画：卡片从灵感池拖入创作中 → 轻微弹跳 + 状态过渡

---

## 6. 分阶段实施计划

### Phase 1: 后端核心重构（预计 3-4 天）

| 任务 | 内容 | 优先级 |
|------|------|--------|
| 1.1 | 扩展 `AgentState` 至 PRD 完整字段 | P0 |
| 1.2 | 新增 `src/schemas/` — 全部 Pydantic 请求/响应模型 | P0 |
| 1.3 | 新增 `src/models/` — SQLAlchemy Task ORM | P0 |
| 1.4 | 新增 `src/db/` — aiosqlite session + SqliteSaver 工厂 | P0 |
| 1.5 | 新增 `src/core/exceptions.py` + `constants.py` | P1 |
| 1.6 | 新增 `src/api/middleware.py` — X-API-Key + CORS | P0 |
| 1.7 | 新增 `src/api/v1/agent.py` — 全部 Agent 端点 | P0 |
| 1.8 | 新增 `src/api/v1/board.py` — 看板聚合端点 | P0 |
| 1.9 | 新增 `src/main.py` — FastAPI 应用工厂 + 生命周期 | P0 |
| 1.10 | 新增 `src/services/task_service.py` — 任务 CRUD | P0 |
| 1.11 | 新增 `src/services/board_service.py` — 看板聚合 | P0 |
| 1.12 | 扩展 `src/agent/graph.py` — 完整 10 节点拓扑 | P0 |
| 1.13 | 新增所有缺失节点 | P0 |
| 1.14 | 新增 MCP Client 封装 (`src/agent/tools/mcp_client.py`) | P0 |

### Phase 2: MediaCrawler MCP Server（预计 2-3 天）

| 任务 | 内容 | 优先级 |
|------|------|--------|
| 2.1 | `skills/media_crawler/server.py` — MCP Server 骨架 | P0 |
| 2.2 | `browser_manager.py` — Playwright 单例生命周期 | P0 |
| 2.3 | `login_manager.py` — Cookie 持久化 + 扫码恢复 | P0 |
| 2.4 | `pipeline.py` — 爬取 + 数据清洗 | P0 |
| 2.5 | `tools.py` — search_trends / get_note_detail / check_health | P0 |
| 2.6 | 替换现有 Tavily 搜索为 MCP 调用 | P0 |

### Phase 3: 资产进化 Pipeline（预计 2 天）

| 任务 | 内容 | 优先级 |
|------|------|--------|
| 3.1 | `services/evolution_service.py` — 4 个进化触发逻辑 | P0 |
| 3.2 | 一稿过 → best_practices.md 提取 | P1 |
| 3.3 | 高轮次反思 → negative_prompts.md | P1 |
| 3.4 | Token 瘦身机制（> 8000 触发） | P2 |
| 3.5 | 创建 `best_practices.md` 初始文件 | P1 |

### Phase 4: 前端（预计 4-5 天）

| 任务 | 内容 | 优先级 |
|------|------|--------|
| 4.1 | Next.js 14 / Vue 3 项目脚手架 + 路由 | P0 |
| 4.2 | 全局布局 + 设计系统 (tokens.css) | P0 |
| 4.3 | KanbanBoard 四列布局 + 响应式 | P0 |
| 4.4 | TopicCard 组件 (AI 灵感池) | P0 |
| 4.5 | TaskCard 组件 (含 Loading 骨架屏) | P0 |
| 4.6 | ReviewDrawer 双轨审核面板 | P0 |
| 4.7 | 拖拽交互 (dnd-kit 或原生) | P1 |
| 4.8 | TanStack Query + Zustand 集成 | P0 |
| 4.9 | 一键复制功能 | P1 |
| 4.10 | Alert/Toast 通知系统 | P1 |

### Phase 5: 测试 + 文档（预计 2 天）

| 任务 | 内容 | 优先级 |
|------|------|--------|
| 5.1 | 单元测试 (pytest — 目标 80% 覆盖) | P0 |
| 5.2 | API 集成测试 (httpx + pytest-asyncio) | P0 |
| 5.3 | E2E 工作流测试 (Playwright) | P1 |
| 5.4 | ruff + mypy + bandit 全量通过 | P0 |

---

## 7. 关键技术决策

1. **前端框架选型**：推荐 **Next.js 14 (App Router)** — 生态成熟，TanStack Query 集成平滑，且符合 PRD 技术栈指定
2. **Kanban 拖拽库**：推荐 `@dnd-kit/core` — 轻量、可访问性好、支持 React 生态
3. **富文本编辑器**：审核面板微调轨使用 `TipTap`（基于 ProseMirror），轻量可定制
4. **LLM JSON 结构化输出**：使用 LangChain `with_structured_output()` 或直接在 prompt 中强制 JSON + `json.loads` 解析，加异常重试
5. **MCP Server 通信**：Agent 侧用 `langchain-mcp-adapters` 的 `MultiServerMCPClient`；前端不需要直接连接 MCP
6. **并发控制**：后端用数据库行锁确保同一时间仅一个任务 `in_progress`

---

## 8. 风险与注意事项

- **MediaCrawler 爬取稳定性**：小红书反爬严格，需充分降级处理；MediaCrawler MCP Server 应设计为独立进程，崩溃不影响 FastAPI 主进程
- **Cookie 登录态**：首次部署需人工扫码，过期后前端展示二维码重新登录
- **LLM 输出格式一致性**：JSON 结构化输出需加 `response_format: {"type": "json_object"}` 和解析重试逻辑
- **Token 瘦身精度**：压缩可能丢失有价值资产，瘦身后需监控一稿过率变化，保留回滚能力
- **SQLite 并发写限制**：单写者模型，对于单租户本地部署足够；未来如需多用户需迁移 PostgreSQL
