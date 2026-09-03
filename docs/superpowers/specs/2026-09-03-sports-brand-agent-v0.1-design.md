# 体育品牌运营 Agent V0.1 重建设计

**日期：** 2026-09-03  
**状态：** 已完成对话设计确认，等待书面审阅  
**需求基线：** `D:\Program Files\体育品牌运营 Agent — Implementation Contract V0.1.md`  
**交互基线：** `D:\Program Files\体育品牌运营Agent_交互原型_V0.4.html`

## 1. 目标与优先级

本项目在保留 Git 历史的前提下全量清空现有业务实现，并从空白结构重建一个本地、单用户、使用真实公开数据、低频采集且全链路可追溯的体育品牌运营 Agent。

Implementation Contract V0.1 是实现层面的最高优先级要求。V0.4 HTML 是前端视觉、信息结构和交互流程的基准。本文只补充经用户确认的工程组织方式，不修改需求基线中的评分公式、阈值、状态机、Topic 身份规则或产品边界。

工程原则依次为：真实数据优先、可解释优先、稳定演示优先、规则与 LLM 分工、完整可追溯。

## 2. 范围

### 2.1 包含

- 固定版本的官方 MediaCrawler CLI 集成与 P0 真实数据验证。
- 两阶段采集：宽搜索与代表笔记窄化增强。
- 标准化、快照、稳定 Topic 身份、热度、趋势和生命周期。
- Brand Brain、资格门槛、五维机会评分和证据链。
- 文案预览、接受后完整 Draft、结构化拒绝、内容日历。
- 与 V0.4 对齐的热点机会、内容工作室、内容日历、数据复盘和品牌大脑界面。
- 定时刷新、单任务锁、崩溃恢复及契约规定的降级行为。
- 单元测试、匿名化真实 fixture 集成测试、启动和演示文档。

### 2.2 不包含

- 自动发布、自动互动、多账号、多用户。
- Redis、Celery、分布式任务、云端常驻服务。
- 向量数据库、模型微调、验证码绕过和大规模采集。
- 对 V0.4 的产品结构或视觉系统进行重新设计。

## 3. 重建策略

删除现有前后端业务代码，从新的模块边界和数据库迁移开始重建。保留以下内容：

- `.git` 及完整提交历史；
- 两份外部需求基线文件；
- 经审阅确认仍适用的工程配置或素材，但不沿用与新契约冲突的业务实现。

旧的自写 Playwright 抓取、LangGraph 业务流程以及静态假数据降级不进入新实现。删除工作在新设计和实施计划通过审阅后进行，并在删除前核对准确目标。

## 4. 总体架构

```text
Next.js V0.4 UI
        ↓ REST API
FastAPI Application
        ├─ Refresh Job / APScheduler
        ├─ MediaCrawler Adapter
        │      ↓ subprocess
        │  external/MediaCrawler（固定 commit）
        ├─ Normalizer / Topic / Trend / Opportunity Engines
        ├─ Unified LLM Service + versioned prompts
        └─ SQLite（产品唯一事实来源）
```

前端只消费 Brand Agent API，不读取原始 JSONL。MediaCrawler 作为外部数据采集组件运行，不被业务代码直接 import，也不与 Brand Agent 共享数据库。

后端采用 FastAPI、SQLAlchemy Async、Alembic、SQLite、APScheduler 和 Pydantic。前端采用 Next.js、React、TypeScript、TanStack Query；是否继续使用当前其他前端依赖，以实现 V0.4 行为所需的最小集合为准。

## 5. 实施顺序与阶段门禁

严格按以下顺序推进：

1. P0 MediaCrawler POC。
2. P1 Normalizer、数据库和匿名化真实 Fixtures。
3. P2 Refresh Job 和 Scheduler。
4. P3 Topic 聚类、稳定身份和 Trend Engine。
5. P4 Opportunity Engine。
6. P5 Copy Service。
7. P6 V0.4 API Integration。
8. P7 测试、坏案例、README 和 Definition of Done 核验。

不得并行重写前端、数据库、Crawler 和 AI。P0 未完成前，不实现依赖真实字段的趋势算法。

P0 从官方 MediaCrawler 仓库建立 `external/MediaCrawler` 工作副本。验证成功后，将仓库地址、准确 commit、平台和 JSONL 存储方式写入 `config/mediacrawler.yaml`，后续运行不自动拉取最新版本。

P0 必须用至少三个体育关键词完成真实 Search，确认契约列出的笔记与评论字段，并生成：

- `docs/p0-mediacrawler-field-report.md`
- `tests/fixtures/mediacrawler/`
- `data/raw/<test-job>/`

如果 `published_at` 无法稳定获取，P0 报告写入 `BLOCKED_FIELD: published_at`，并停止七天窗口的正式实现。

## 6. 模块边界

### 6.1 后端

- `crawler/`：MediaCrawler CLI 命令构造、子进程执行、Job 目录、原始文件定位和版本信息。
- `refresh/`：刷新状态机、单实例锁、关键词执行编排、崩溃恢复和 APScheduler。
- `notes/`：字段标准化、数据完整度、Note、Note Snapshot、Search Snapshot 和 Comment 持久化。
- `topics/`：候选聚类、Topic Resolution、代表笔记选择、Topic Snapshot 和 Lifecycle。
- `scoring/`：Current Heat、Trend Score、Confidence、Eligibility Gate 和 Opportunity Score 的纯规则计算。
- `llm/`：唯一模型调用入口、结构化 Schema、一次解析重试、Prompt 加载和 LLM Run 记录。
- `brand/`：版本化 Brand Brain、内容策略、产品库和安全规则。
- `opportunities/`：机会聚合、解释与证据、列表、重新分析、接受和拒绝。
- `content/`：文案预览、完整 Draft、版本信息和内容日历。
- `api/`：请求验证、响应序列化和 HTTP 状态映射，不承载评分或工作流规则。

每个模块通过明确的 service/repository/schema 接口协作。评分逻辑优先写成无数据库依赖的纯函数，便于对公式和边界值做确定性测试。

### 6.2 前端

- `opportunities/`：列表、详情、分数拆解、理由、来源、文案预览、接受、拒绝和刷新状态。
- `studio/`：Draft 列表、编辑、AI 候选版本、风险检查和图片建议。
- `calendar/`：排期、状态流转和内容详情。
- `analytics/`：已发布内容数据与解释性洞察；没有真实数据时显示不可用，不生成假指标。
- `brand/`：Brand Brain 和产品库的版本化编辑。
- `shared/`：布局、反馈状态、数据来源徽标和通用控件。

V0.4 的信息结构、核心文案语义和五个模块全部保留。首个端到端交付优先打通热点机会，后续阶段再接通其余模块。

## 7. 核心数据流

1. 用户或定时器触发刷新，系统在取得单实例锁后创建 `refresh_job`。
2. 六个关键词分别执行一次 MediaCrawler Search Job；每个 Job 最多抓取 40 条原始候选，不抓评论，串行执行。
3. 原始 JSONL 按 `data/raw/{refresh_job_id}/{keyword}/` 保存，并记录命令时间、退出码、路径和 stderr 摘要。
4. Normalizer 把原始字段转换为统一 Note 对象，保留缺失值为 `null`，计算数据完整度，执行七天窗口与每关键词最多 20 条的业务过滤。
5. 系统持久化 Note、Note Snapshot 与同轮同关键词的 Search Position Snapshot，再执行去重、初始聚类和 Topic Resolution。
6. 每个正式 Topic 选择默认三篇、最多五篇代表笔记，作者去重后执行 Detail Job，仅抓一级评论且每篇最多 20 条。
7. 规则引擎计算 Current Heat；只有存在至少两次成功 Topic Snapshot 时才计算 Trend Score。
8. Eligibility Gate 先执行。通过或进入人工复核的 Topic 再由 LLM Service 完成结构化评论分析与机会五维分析。
9. 系统保存 Opportunity、Topic/Note 来源链、LLM Run、Prompt 版本、模型和 Brand Brain 版本，再生成 80–150 字文案预览。
10. 用户接受 Opportunity 后生成 Content Brief 与完整 Draft，并进入 Content Studio；拒绝只保存结构化原因，不用于在线训练。

## 8. 数据模型

契约规定的核心表必须完整实现：

- `refresh_jobs`
- `notes`
- `note_snapshots`
- `note_search_snapshots`
- `topics`
- `topic_snapshots`
- `topic_snapshot_notes`
- `comments`
- `llm_runs`

为支持端到端功能，增加：

- `brand_profiles`：版本化保存 Brand Brain JSON、版本号和生效时间。
- `opportunities`：保存所属 Topic Snapshot、五维分数、决定、目标、资格、风险、置信度、解释、证据和数据来源。
- `opportunity_llm_runs`：连接 Opportunity 与参与其结果的多次 LLM Run。
- `drafts`：保存来源 Opportunity、Topic、Brand Profile、Prompt 版本、完整文案和风险检查。
- `reject_feedback`：保存拒绝枚举、可选备注和时间。
- `calendar_items`：保存 Draft 排期、状态和建议时间。
- `system_settings`：保存自动刷新开关、连续失败次数和调度配置。

所有动态指标进入快照表，不覆盖实体历史。JSON 字段用于保存契约要求的原始/归一化指标、模型输入输出和灵活内容结构；关键检索与关联字段使用明确列和外键。

## 9. 评分与决策职责

规则代码严格实现以下内容，不允许 LLM 覆盖：

- Weighted Engagement、Freshness、Note Volume、Creator Spread。
- 同轮 percentile normalization 与缺失指标权重重分配。
- Current Heat、Trend Score 及所有固定权重。
- Search Position Momentum、Persistence 和速度指标。
- Lifecycle、Confidence 和 Eligibility Gate 的规则部分。
- Trend Timing、Opportunity 加权总分、Decision 和 Content Goal 默认规则。

LLM 仅负责：Topic 聚类、无足够 Note 重叠时的身份解析、评论分类、Brand/Audience Relevance、Content Opportunity、Product Fit、解释和文案。所有关键调用使用 JSON Schema，解析失败只重试一次；第二次失败写入失败的 `llm_runs`。

## 10. API 设计

公共 API 统一使用 `/api` 前缀，至少包括：

- `POST /api/refresh-jobs`：启动手动刷新；已有任务运行时返回契约规定的 409。
- `GET /api/refresh-jobs/current`：查看当前或最近刷新状态。
- `GET /api/opportunities`：返回契约规定的机会数据、来源、快照时间和数据来源标签。
- `POST /api/opportunities/{id}/reanalyze`：在 LLM 失败后重新分析，不重复抓取。
- `POST /api/opportunities/{id}/accept`：生成完整 Draft 并返回 Draft ID。
- `POST /api/opportunities/{id}/reject`：保存结构化拒绝原因。
- `GET/PATCH /api/brand-profile`：读取或创建新版本 Brand Brain。
- `GET/PATCH /api/drafts/{id}`：读取和编辑 Draft。
- `GET/POST/PATCH /api/calendar-items`：排期与状态管理。
- `GET /api/analytics`：返回真实已发布内容分析；无数据时明确不可用。

响应层统一提供机器可读的错误码。数据对象必须携带 `data_source`，值仅为 `real`、`fixture` 或 `demo`。

## 11. 异常和降级

- MediaCrawler 全部失败：有历史时返回最近成功快照并标记更新失败及真实历史时间；无历史时返回 unavailable。
- 部分关键词失败：刷新状态为 `partial_success`，成功数据继续分析，受影响 Topic 降低 Confidence。
- LLM 失败：保留 Raw Topic、Current Heat、Trend Data 与 Source Notes，将分析标记为 `analysis_unavailable` 并提供重新分析入口。
- 进程重启：启动时把超过 30 分钟未更新的运行中 Job 改为 `interrupted`。
- 调度失败：连续两次 scheduled refresh 失败后关闭自动刷新，UI 提示检查登录、页面或网络。
- 登录或验证码：只使用 MediaCrawler 支持的正常登录机制，由用户本人完成交互，不绕过平台验证。
- Fixture 或 Demo：只能在明确选择的演示/测试情境使用，UI 始终显示对应标签。

日志不得包含 Cookie、手机号、密钥或不必要的个人信息。数据库不保存 Cookie。

## 12. 前端状态设计

每个页面都必须显式处理：

- 初次加载、后台刷新和操作提交；
- 空数据；
- 无可用分析；
- 全部失败后的历史快照回退；
- 部分成功；
- `real`、`fixture`、`demo` 来源；
- 第一轮仅有 Current Heat、趋势积累中；
- Source Note 外链、发布时间、采集时间和缺失指标。

热点机会详情维持 V0.4 的三栏决策台与下方文案预览/内容简报结构。Filtered 项不允许被接受；manual_review 项需明确提示人工判断。

## 13. 测试策略

所有新增业务行为采用测试先行：先写能因功能缺失而失败的测试，再写最小实现使其通过，最后重构。

单元测试至少覆盖：Normalizer、Weighted Engagement、Current Heat、缺失指标重分配、Trend Score、Search Position Momentum、Topic Matching、Lifecycle、Confidence、Eligibility Gate、Opportunity Score 和 Refresh Lock。

集成测试使用 P0 匿名化保存的真实 JSONL Fixture，不访问实时小红书，覆盖：

- Search JSONL 到内部 Note/快照的完整导入；
- Search 与 Enrichment 的两阶段边界；
- 两轮快照后的 Topic 身份和趋势；
- Opportunity API 的证据链；
- Accept、Draft 和 Calendar 流程；
- 全失败、部分成功、LLM 失败与过期 Job 恢复。

前端测试覆盖 API 状态、数据来源标签、趋势未积累、来源展示、接受/拒绝以及关键模块导航。最终验证包括后端测试、类型检查、静态检查、前端测试和生产构建。

## 14. 安全与数据处理

- Cookie 只由 MediaCrawler 自身登录态机制维护，不进入 Git、Brand Agent SQLite、前端或普通日志。
- Raw JSONL 为本地溯源数据，默认不提交包含真实个人信息的原始数据。
- 测试 Fixture 在提交前匿名化作者等非必要个人字段，同时保留字段结构和评分所需数值。
- URL、Note ID 和 Comment ID 只用于公开来源追溯与内部关联。
- 不提供验证码规避、并发放大或反检测增强功能。

## 15. 验收

最终验收逐项执行 Implementation Contract 第 33 节的 22 条 Definition of Done。任何无法完成的条目必须呈现明确的 blocked、degraded 或 unavailable 状态，记录真实原因，不以模拟结果替代。

实施完成的核心判断是：系统能够从固定关键词样本、真实 Note/Comment 证据、跨轮快照和品牌上下文中，解释为什么推荐或过滤一个 Topic，而不是只展示无法追溯的 AI 分数。
