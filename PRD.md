产品需求文档 (PRD): 小红书自主品牌运营专家 V1.5

1. 产品愿景与价值主张
定位：具备长期记忆、工具调用能力及生产级 Web 交互界面的自动化自媒体运营智能体（Agent）。本产品采用极简架构，定位为单租户、单品牌、本地部署的商业化演示/辅助运营工具，不考虑复杂的后台系统、多品牌/多店铺管理或 RPA 自动发布，核心是辅助人类运营高效、高质量产出。
核心价值：通过"越用越懂你"的 Markdown 资产库自动沉淀机制与"双轨制"人类在环审核机制，实现"热点监测-内容创作（含本土化可控视觉策划）-人工润色"的高效生产闭环，极致平衡 AI 效率与人类审美品控，辅助运营人员完成高质量内容输出（通过人工或未来可选自动化进行平台物理发布）。
视觉策划与国产模型：基于小红书平台高审美、本土版权合规的要求，本产品默认且强制使用国内主流图像生成大模型接口（如智谱 CogView、百度文心一格、阿里云通义万相等），针对国内审美和版权合规要求，提供本土化视觉风格提示词，杜绝版权隐患，确保内容生成的合规性与本土审美风格。
技术目标：打造一个基于 FastAPI 与 Next.js/Vue3 的前后端分离、极简部署的单品牌 AI Agent 演示级高价值项目。

2. 核心技术栈选型 (Standard Stack)
后端引擎：Python 3.12+ / FastAPI（负责 API 与并发处理，挂载本地资产目录）。
Agent 编排：LangGraph（状态机控制）+ LangChain >= 1.0（工具集成）。
大语言模型：Qwen（通义千问）或其他兼容 OpenAI 接口格式的国产 LLM（如智谱 GLM 系列、百度文心一言系列等）。辅助节点可使用更轻量国内小模型（如 Qwen-Turbo）。
图像大模型：集成国内先进的生成式 AI 图像大模型接口（如智谱 CogView、百度文心一格、阿里云通义万相等），保障生成图像的本土审美风格与合规性。提示词将针对所选国产大模型进行深度优化。
数据源与爬虫：MediaCrawler 以独立 MCP Server Skill 形式运行，通过 MCP 协议暴露 search_trends / get_note_detail 等 Tool，供 LangGraph Agent 调用。Agent 侧通过 langchain-mcp-adapters 加载 MCP Tool，实现数据源与编排层解耦。
前端框架：Next.js 14+ 或 Vue 3（提供基于 Kanban 看板流设计的响应式 Web 界面）。
数据持久化：SQLite（Agent 状态与任务卡片持久化，轻量零配置）。
观测运维：LangSmith 或国内兼容 Trace 监控工具。
配置管理：四层分离体系 — pyproject.toml（依赖声明）+ config.toml（业务参数·提交 Git）+ .env（密钥·不入 Git）+ config.py（Pydantic 融合加载中心）。

3. 核心功能模块划分
模块一：全局单品牌资产库 (Asset Library & Memory)
系统采用极简架构，在根目录 /assets/brand_data/ 下采用 .md 格式固定存储核心资产，不支持复杂的租户/多品牌数据库。
  brand_voice.md：定义品牌人设、常用口癖、排版偏好（如：多用🌟符号）。
  negative_prompts.md：避坑指南，记录历史不满意风格。[核心记忆载体]（自我迭代机制 1：修改轮次 > 3 触发反思补充）
  product_info.md：产品/卖点详情，用于文案末尾自动植入自然广告。
  best_practices.md：高分范文库。[核心记忆载体]（自我迭代机制 2：一稿过触发 Few-Shot 提取存储）
强制约束：系统进行 Token 压缩（Eviction）时，必须将以上文件内容设为"Pinned（置顶保护）"，严禁清理。
进化动作：随着学习沉淀资产 Token 超标（累计 > 8000 token），触发自动总结与瘦身任务（LLM 摘要压缩，保留核心规则与最高分样本，淘汰低价值历史条目）。

模块二：高阶技能链 (Skills)
🔍 选题雷达 (Trend Radar)：接收宏观主题（或每日定时自动触发），调用 MediaCrawler MCP Skill 的 search_trends Tool 爬取小红书等平台热搜及热门笔记（标题、互动量、关键评论），经 LLM 提炼后输出 3-5 个高潜力选题卡片（包含选题标题、提报理由、热度指数及预估平台流量池）。
✍️ 品牌撰写 (Generate Copy & Visuals)：结合选题、品牌资产（含 Few-Shot 高分范文库）及产品信息，输出符合小红书规范（爆款标题/正文结构/精准标签）的图文策划案，强制包含文本与视觉策划两大模块。
  文本输出：符合品牌调性和平台规范的最终标题、正文、标签。
  视觉建议 <Visual_Guidance>：包含封面大字报排版建议、3-4 张内页分镜设计描述，以及 2-3 个可直接用于国产图像大模型（CogView、文心一格、通义万相）的优化中文/英文提示词 (Prompt)，杜绝外网模型提示词，确保版权合规与本土审美风格。
🛡️ 风控校验 (Compliance)：自动识别敏感词。若触碰红线严重违规，强制抛出异常并触发"重写"逻辑，更换选题。

模块三：Web 端基于 Kanban 看板流的人类在环 (HITL)
前端通过基于看板流设计的响应式 Web 界面提供清晰的内容生产工作流管理。看板分为以下四个核心列：
  📍 AI 灵感池 (AI Inspiration Pool)：展示 Agent 每日自动拉取或用户手动触发的 3-5 个高潜力热点选题卡片。卡片包含详细选题信息与预估平台流量，用户可勾选触发下一步。
  🚀 AI 创作中 (In Progress)：用户将选题卡片拖拽至此（或直接点击列内"+ 新建"输入明确主题），触发后端 Agent 启动（爬取热点、读取资产库、撰写爆款文案与国产模型视觉策划）。卡片显示 Loading 状态。
  👀 待人工审核 (Pending Review)：Agent 完成初稿及国产图像模型提示词后，卡片自动流转至此并 alert 提示。用户点击卡片，弹出版面精美的抽屉式"双轨制"审核面板：
    微调轨 (Direct Edit)：提供富文本框及可编辑区域，用户直接改字，点击【保存通过】。
    重做轨与自动记忆 (Feedback & Evolve)：用户输入文本指令（如："太浮夸了，改得实在点"）反馈重做。[核心记忆沉淀]：异步触发"规则提取器"节点（小模型），判定为通用规则后提取成条例（如：- 严禁过度使用感叹号，保持务实语境），自动追加写入 negative_prompts.md 文件末尾，实现"越用越懂你"。
  ✅ 已完成归档 (Done)：用户点击【保存通过】后卡片落入此列。提供快捷按钮：一键复制小红书格式文本、一键复制国产大模型提示词，供人工前往小红书物理发布。[系统动作]：异步触发自我进化机制——
    - 一稿过（修改轮次 = 0）：小模型提取「标题公式 + 正文结构模板 + 标签组合」三个要素，追加至 best_practices.md。
    - 修改轮次 > 3：触发深层自我反思，更新避坑指南 negative_prompts.md。
    - Token 超标（累计 > 8000）：触发总结瘦身机制。

4. 关键 API 接口设计 (Contract)
接口路径 | 方法 | 功能描述 | 关键参数/响应
/api/v1/agent/discover | POST | 手动触发热点发现 | Response: 选题卡片列表，写入灵感池
/api/v1/agent/start | POST | 启动创作任务 | Request: {topic: "主题"} -> Response: thread_id
/api/v1/agent/status/{tid} | GET | 查询进度与中间产物 | Response: status (running/waiting/success) 及中间产物（文案初稿、视觉提示词建议）
/api/v1/agent/feedback | POST | 提交判决与反馈意见 | Request: {action: "approve/revise", feedback: "意见", edited_content: "手动改后的稿件"}。approve 生成最终结果并 END；revise 更新状态触发重跑，并异步触发规则提取/反思
/api/v1/board | GET | 获取 Kanban 看板全量状态 | Response: 四列卡片数据，供前端渲染看板视图
/api/v1/agent/cancel/{tid} | POST | 取消进行中的任务 | Response: 任务状态更新为 cancelled

5. 核心数据结构 (AgentState)
class AgentState(TypedDict):
    # 基础信息
    user_input: str
    thread_id: str

    # 选题数据
    topic_cards: List[dict]             # 结构化选题卡片：[{title, reason, heat_index, estimated_traffic}]

    # 过程数据
    draft_copy: str
    visual_guidance: dict               # {cover_suggestion, shot_descriptions, domestic_image_prompts}
    is_revision: bool

    # 人类介入数据
    human_feedback: str
    edited_draft_copy: str              # 用户手动修改后的文案内容

    # 审核追踪
    revision_count: int                 # 当前任务修改轮次计数器（驱动度量指标与自我进化）
    final_copy: str                     # 审核通过后的最终定稿

    # 资产上下文
    brand_context: str
    product_context: str
    best_practices: str                 # Few-Shot 范文资产
    negative_prompts: str               # 避坑指南资产

    # 过程上下文（节点间传递）
    trends_context: str                # 爬取 + LLM 提炼后的结构化热点素材
    compliance_severity: str           # 风控判定: pass / mild_warning / severe_violation
    violation_count: int               # 本次任务累计严重违规次数

    # 人类交互
    feedback_action: str               # 人类操作: approve / revise
    feedback_history: List[dict]       # 修改轨迹：[{round: 1, feedback: "..."}, ...]
    draft_versions: List[str]          # 各轮 draft_copy 快照，供进化分析

    # 系统追踪
    current_step: str
    error_logs: List[str]

6. LangGraph Agent 节点拓扑设计

6.1 状态机图

                    ┌─────────────┐
                    │  init_task  │  ← START
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │ crawl_trends│  ← MediaCrawler Tool
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │ load_assets │  ← 读取 /assets/brand_data/*.md
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │generate_copy│  ← 主 LLM 撰写节点
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │generate_vis │  ← 视觉策划 + 国产模型提示词
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │ compliance  │  ← 敏感词/红线检测
                    └──┬──────┬───┘
               pass     │      │  severe_violation
                        │      ▼
                        │   ┌──────────────┐
                        │   │ rewrite_topic│ ← 自动换题，回到 generate_copy
                        │   └──────────────┘
                        │
              ┌─────────▼─────────┐
              │  human_review     │  ← __interrupt_before__ 断点
              └─────────┬─────────┘
                        │ (人类操作后恢复)
              ┌─────────▼─────────┐
              │ handle_feedback   │  ← 解析 approve / revise
              └──┬──────────┬─────┘
         approve │          │ revise
                 │          ▼
                 │   ┌──────────────────┐
                 │   │ extract_rules    │ ← 异步·规则提取器 (小模型)
                 │   │ → negative_prompts│
                 │   └──────────────────┘
                 │          │
                 │   ┌──────▼──────┐
                 │   │generate_copy│ ← 带回 feedback 重写
                 │   └─────────────┘
                 ▼
          ┌──────────────┐
          │   finalize   │  ← 一稿过提取 / 高轮次反思 / Token瘦身
          └──────────────┘
                 │
                 ▼
                END

6.2 节点详细定义

节点 1: init_task
  职责：解析入口输入，初始化 State，判断触发来源（灵感池卡片 / 手动输入）
  模型：无（纯逻辑）
  读 State：user_input, topic_cards
  写 State：thread_id, current_step="init", revision_count=0, is_revision=False
  内部逻辑：
    1. thread_id = uuid4()
    2. 如果来自灵感池卡片勾选 → 从 topic_cards 提取对应 title + reason
    3. 如果是手动输入字符串 → 直接将 user_input 作为主题

节点 2: crawl_trends
  职责：调用 MediaCrawler Tool，以主题为关键词爬取小红书热门笔记，LLM 提炼为结构化参考素材
  模型：LLM 提炼用（Qwen-Turbo 级别即可）
  读 State：user_input
  写 State：current_step="crawling"；内存储存 trends_context
  超时：30s（爬取）+ 10s（提炼）
  Tool 调用流程：
    MediaCrawler.search(keyword=user_input, platform="xhs", limit=10)
        ↓ 返回 [{title, likes, comments, collects, url}, ...]
        ↓ 喂给轻量 LLM 提炼：
    Prompt:
    "以下是小红书「{user_input}」相关热门笔记，请提炼：
      1. 当前话题的主流叙事角度（2-3 个）
      2. 高频关键词/标签
      3. 爆款标题的共同特征
      4. 可参考的文案结构模式
    热门笔记数据：{crawled_data}"
  异常处理：
    - MediaCrawler 超时 → error_logs 追加，降级为"无参考素材，直接创作"
    - 返回空结果 → 同上，标记 trends_context = "无相关热点数据"
    - Cookie 过期 → 抛异常，提示用户重新扫码登录

节点 3: load_assets
  职责：读取 /assets/brand_data/ 下全部 4 个 .md 文件，填充 State 上下文字段
  模型：无（文件 I/O）
  读 State：无
  写 State：brand_context, product_context, best_practices, negative_prompts
  读取清单：
    brand_voice.md      → brand_context
    product_info.md     → product_context
    best_practices.md   → best_practices
    negative_prompts.md → negative_prompts
  Pinned 保护：此四个文件在 Token 压缩时标记为不可驱逐

节点 4: generate_copy
  职责：核心创作节点——组装 System Prompt + 资产上下文 + 选题 + 反馈，调用主力 LLM 生成小红书文案
  模型：主力 LLM（Qwen-Plus / GLM-4 级别）
  读 State：user_input, brand_context, product_context, best_practices, negative_prompts, human_feedback(如有), is_revision
  写 State：draft_copy, current_step="writing"
  超时：30s
  Prompt 动态拼装结构：
    System:
      {brand_context}
      {negative_prompts}
      {best_practices}  ← Few-Shot 高分范文

    User:
      {if is_revision: "以下是上一版的修改意见：{human_feedback}，请据此重写。\n---\n"}
      主题：{user_input}
      产品信息：{product_context}
      参考素材（来自小红书热搜）：{trends_context}

      请输出符合小红书平台规范的完整文案：
      - 标题（爆款钩子 + 关键词前置）
      - 正文（分段叙事，emoji 适度点缀）
      - 标签（3-5 个精准标签）
      - 文末自然植入产品广告（基于 product_info）
  输出要求：强制 JSON 结构化返回：
    {"title": "...", "body": "...", "tags": ["...", "..."], "ad_placement": "..."}
  重写差异：is_revision=True 时跳过趋势上下文（不重复爬取），直接以 human_feedback 驱动重写

节点 5: generate_visuals
  职责：基于定稿文案，生成视觉策划方案及可直接使用的国产模型 Prompt
  模型：主力 LLM（同上）
  读 State：draft_copy, brand_context
  写 State：visual_guidance, current_step="visual"
  超时：20s
  输出结构 <Visual_Guidance>：
    {
      "cover_suggestion": "封面大字报排版描述",
      "shot_descriptions": ["分镜1: ...", "分镜2: ...", "分镜3: ..."],
      "domestic_image_prompts": [
        "CogView prompt: ...",
        "文心一格 prompt: ...",
        "通义万相 prompt: ..."
      ]
    }
  强制约束：
    - 必须生成 2-3 个不同国产模型的适配 prompt
    - 禁止输出 Midjourney / Stable Diffusion / DALL·E 等外网模型 prompt
    - 提示词须符合本土审美（新中式、ins 风、日系、韩系等小红书高互动风格）

节点 6: compliance
  职责：敏感词/红线检测，判定 pass / mild_warning / severe_violation
  模型：轻量 LLM + 敏感词词典双检
  读 State：draft_copy, visual_guidance
  写 State：current_step="compliance", error_logs
  超时：5s
  判定逻辑：
    第一层（词典匹配）：对标题+正文跑敏感词表，命中即标记位置与类型
    第二层（LLM 二次判定）：将标记结果给 LLM 判定严重程度
      → pass: 无误
      → mild_warning: 建议修改词，降级为备注提醒
      → severe_violation: 政治/色情/医疗断言等红线词
  严重违规处理：
    - error_logs 追加违规详情
    - 自动换题：当前选题标记为不可用，回到 generate_copy 重新选角度
    - 连续 3 次严重违规 → 直接 END，卡片标记为"审核不通过"

节点 7: human_review（中断点）
  职责：LangGraph interrupt_before 在此节点前挂起，状态持久化 SQLite，等待人类操作
  模型：无
  读 State：全部
  写 State：current_step="waiting_for_human"
  中断机制：
    graph.compile(
        checkpointer=SqliteSaver.from_conn_string("sqlite:///data/agent_state.db"),
        interrupt_before=["human_review"]
    )
  前端通过轮询 GET /api/v1/agent/status/{thread_id} 获得 status: waiting_for_human

节点 8: handle_feedback
  职责：解析人类操作（approve / revise），写回 State，决定下一跳
  模型：无（纯逻辑）
  读 State：human_feedback, edited_draft_copy
  写 State：current_step, revision_count += 1（若 revise）
  分支路由：
    approve → final_copy = edited_draft_copy or draft_copy，路由 → finalize
    revise  → is_revision = True，路由 → generate_copy，同时异步触发 extract_rules

节点 9: extract_rules（异步旁路）
  职责：收到 revise 反馈时，用小模型判定是否为通用规则，是则追加写入 negative_prompts.md
  模型：小模型（Qwen-Turbo）
  读 State：human_feedback
  写 State：无（直接写入文件系统）
  超时：10s
  提取 Prompt：
    "判断以下用户反馈是否为'通用内容风格规则'（可复用于未来所有文案），
     还是'单次具体修改指令'（仅本次有效）：

     用户反馈：'{human_feedback}'

     如果是通用规则，提取为一句 Markdown 列表项：- 严禁/避免/保持 [行为描述]
     如果不是通用规则，输出：NOT_A_RULE

     示例：
       反馈：'太浮夸了，少用感叹号' → - 严禁过度使用感叹号，保持务实平实语境
       反馈：'把秋季穿搭改成早秋通勤穿搭' → NOT_A_RULE"
  写入方式：追加到 negative_prompts.md 末尾，带时间戳注释

节点 10: finalize
  职责：收尾——组装最终结果，触发异步进化任务
  模型：小模型（进化提取用）
  读 State：全部
  写 State：final_copy, current_step="done"
  超时：15s
  异步进化任务（不阻塞主流程）：
    1. revision_count == 0（一稿过）:
       → 提取「标题公式 + 正文结构模板 + 标签组合」
       → 格式化追加到 best_practices.md
       → 格式: "## 一稿过案例 #{date}\n- 选题: {topic}\n- 标题模式: {pattern}\n- 结构: {structure}\n---\n"
    2. revision_count > 3:
       → 触发深层反思：分析 feedback 日志与修改轨迹
       → 提取共性失败模式，追加到 negative_prompts.md
    3. Token 超标（累计 > 8000）:
       → 触发瘦身：LLM 对 best_practices.md 和 negative_prompts.md 做摘要压缩
       → 保留最新 5 条 + 最高分 3 条，其余压缩为一段总结

6.3 条件边 (Conditional Edges)

  源节点          目标节点        条件
  ─────────────────────────────────────────────────
  compliance      human_review    severity = pass 或 mild_warning
  compliance      generate_copy   severity = severe_violation 且累计 < 3 次
  compliance      END             severity = severe_violation 且累计 >= 3 次
  handle_feedback finalize        action = approve
  handle_feedback generate_copy   action = revise

6.4 AgentState 字段与节点读写矩阵

  字段             init crawl assets gen_copy gen_vis comp  human fb    extr  finalize
  ────────────────────────────────────────────────────────────────────────────────────
  user_input       W    R                                      R               R
  thread_id        W
  topic_cards      R
  draft_copy                                  W      R        R     R             R
  visual_guidance                                    W        R     R             R
  is_revision      W                                  R                    W
  revision_count   W                                                  W
  human_feedback                                                   W     R     R
  edited_draft_copy                                                W     R
  final_copy                                                                        W
  brand_context                 W               R
  product_context               W               R
  best_practices                W               R                                     R
  negative_prompts              W               R                            W
  trends_context           W                     R
  current_step       W     W     W      W       W      W     W    W           W
  error_logs                                                 W                     W

6.5 构建伪代码

  from langgraph.graph import StateGraph, END
  from langgraph.checkpoint.sqlite import SqliteSaver

  def build_agent_graph() -> StateGraph:
      workflow = StateGraph(AgentState)

      # 注册节点
      workflow.add_node("init_task", init_task)
      workflow.add_node("crawl_trends", crawl_trends)
      workflow.add_node("load_assets", load_assets)
      workflow.add_node("generate_copy", generate_copy)
      workflow.add_node("generate_visuals", generate_visuals)
      workflow.add_node("compliance", compliance)
      workflow.add_node("human_review", human_review)
      workflow.add_node("handle_feedback", handle_feedback)
      workflow.add_node("extract_rules", extract_rules)
      workflow.add_node("finalize", finalize)

      # 固定边
      workflow.set_entry_point("init_task")
      workflow.add_edge("init_task", "crawl_trends")
      workflow.add_edge("crawl_trends", "load_assets")
      workflow.add_edge("load_assets", "generate_copy")
      workflow.add_edge("generate_copy", "generate_visuals")
      workflow.add_edge("generate_visuals", "compliance")
      workflow.add_edge("human_review", "handle_feedback")

      # 条件边
      workflow.add_conditional_edges("compliance", route_compliance, {
          "pass": "human_review",
          "mild_warning": "human_review",
          "severe": "generate_copy",
          "fatal": END
      })
      workflow.add_conditional_edges("handle_feedback", route_feedback, {
          "approve": "finalize",
          "revise": "generate_copy"
      })
      workflow.add_edge("finalize", END)

      checkpointer = SqliteSaver.from_conn_string("sqlite:///data/agent_state.db")
      return workflow.compile(checkpointer=checkpointer, interrupt_before=["human_review"])


  def route_compliance(state: AgentState) -> str:
      severity = state.get("compliance_severity", "pass")
      violation_count = state.get("violation_count", 0)
      if severity in ("pass", "mild_warning"):
          return "pass" if severity == "pass" else "mild_warning"
      if severity == "severe_violation":
          return "fatal" if violation_count >= 3 else "severe"
      return "pass"


  def route_feedback(state: AgentState) -> str:
      return state.get("feedback_action", "approve")

6.6 Checkpoint 持久化与恢复

  存储后端：SQLite (SqliteSaver)
  存储内容：每个 thread_id 对应的完整 AgentState 快照 + 当前节点位置
  写入时机：每个节点执行后 LangGraph 自动写入
  恢复场景：
    1. 服务重启 → 从 SQLite 加载所有未完成的 thread，恢复看板状态
    2. 人类审核后恢复 → await graph.astream(Command(resume=human_input), config)
    3. 重写循环 → 同一 thread_id 继续执行，不创建新线程

7. MediaCrawler 热点爬取 Skill（独立 MCP Server 模块）

7.1 架构定位
  将 MediaCrawler 拆分为独立 MCP (Model Context Protocol) Server，作为可复用 Skill 运行。
  LangGraph Agent 通过 MCP Client 调用其暴露的 Tool，不直接依赖爬虫实现。
  换数据源（如换成官方 API）只需替换 MCP Server，Agent 代码零改动。

  ┌──────────────┐    MCP Protocol     ┌──────────────────┐
  │  LangGraph    │ ──Tool Call──────→  │  MediaCrawler     │
  │  Agent        │                    │  MCP Server       │
  │  (FastAPI)    │ ←─Result─────────  │  (独立 Python 进程) │
  └──────────────┘                     │                    │
                                       │  Tools:            │
                                       │  - search_trends   │
                                       │  - get_note_detail │
                                       │  - check_health    │
                                       └──────────────────┘

  集成方式：langchain-mcp-adapters 将 MCP Tool 自动转换为 LangChain Tool

7.2 MCP Server 暴露的 Tool 清单

  Tool 名称: search_trends
  参数:     {keyword: str, platform: str, limit: int = 10, sort: str = "popular"}
  返回:     {keyword, total, notes: [{title, likes, comments, collects, url, author}]}
  用途:     搜索指定平台热门笔记，用于热点趋势发现
  支持平台: xhs(小红书), douyin(抖音), weibo(微博), bilibili(B站)

  Tool 名称: get_note_detail
  参数:     {platform: str, note_id: str}
  返回:     {title, content, comments: [...], images: [...], publish_time}
  用途:     获取指定笔记全文与评论区，用于竞品深度分析

  Tool 名称: check_health
  参数:     无
  返回:     {status: "ok"|"degraded"|"down", login_state: {platform: bool}, browser_alive: bool}
  用途:     健康检查，Agent 启动时校验 MCP Server 可用性

7.3 MCP Server 内部职责

  ┌─────────────────────────────────────────────────────┐
  │  MediaCrawler MCP Server                            │
  │                                                     │
  │  ┌───────────────┐  ┌──────────────┐  ┌──────────┐ │
  │  │ BrowserManager│  │ LoginManager │  │ DataClean │ │
  │  │ (Playwright   │  │ (Cookie持久化 │  │ (去重/    │ │
  │  │  单例生命周期) │  │  扫码/恢复)  │  │  质量过滤) │ │
  │  └───────┬───────┘  └──────┬───────┘  └────┬─────┘ │
  │          │                 │               │        │
  │          ▼                 ▼               ▼        │
  │  ┌───────────────────────────────────────────────┐  │
  │  │              CrawlPipeline                    │  │
  │  │  登录检查 → 执行爬取 → 数据清洗 → 结构化返回   │  │
  │  └───────────────────────────────────────────────┘  │
  └─────────────────────────────────────────────────────┘

7.4 登录态管理（Skill 内部闭环）
  存储路径: /data/cookies/{platform}_cookies.json
  生命周期: 首次部署扫码 → Cookie 持久化 → 复用 → 过期自动通知

  Skill 不直接弹 UI，而是通过 MCP Tool 返回值告知 Agent 需要登录：
    check_health() → {login_state: {"xhs": false}, "action": "login_required", "qr_base64": "..."}
  Agent 收到后通过 FastAPI 向前端推送二维码 → 用户扫码 → Agent 调用 check_health 确认恢复

7.5 异常处理与降级
  异常类型              MCP 返回               Agent 降级策略
  ─────────────────────────────────────────────────────────────
  登录失效              status: "login_required"  挂起任务，推送二维码
  爬取超时 (30s)       空结果 + timeout 标记      降级为无参考素材创作
  平台反爬              status: "blocked"         终止当前任务，30min 冷却
  浏览器崩溃            status: "degraded"        自动重启 Browser，透明恢复
  关键词无结果         空结果                     降级创作，不报错

7.6 MCP Server 启动与配置

  # mcp_config.json (LangChain/LangGraph 侧)
  {
    "mcpServers": {
      "media-crawler": {
        "command": "python",
        "args": ["-m", "skills.media_crawler.server"],
        "env": {
          "COOKIE_DIR": "/data/cookies",
          "BROWSER_HEADLESS": "true",
          "CRAWL_TIMEOUT": "30"
        }
      }
    }
  }

  # Agent 侧加载
  from langchain_mcp_adapters.client import MultiServerMCPClient

  async def load_skills():
      client = MultiServerMCPClient.from_config("mcp_config.json")
      tools = await client.get_tools()
      return tools  # 直接注入 LangGraph Agent 的 ToolNode

7.7 后续扩展
  - 新增平台（抖音/微博/B站）只需在 MCP Server 内加爬虫模块，Tool 接口不变
  - 未来替换为官方 API（如小红书开放平台），MCP Server 内部换实现，Agent 无感知
  - 多个 Agent（文案创作、竞品分析）可复用同一 MCP Server

8. 资产自动进化 Pipeline

8.1 概述
  四个触发时机，两条写入路径：

  触发器                        提取器                    目标文件
  ─────────────────────────────────────────────────────────────────────
  一稿过 (revision_count=0)  → 小模型提取范文结构    → best_practices.md
  修改轮次 > 3              → 小模型分析失败模式     → negative_prompts.md
  用户 revise 反馈          → 规则提取器实时判定     → negative_prompts.md
  Token 总量 > 8000         → LLM 摘要压缩           → 两个文件同时瘦身

8.2 进化一：一稿过 → best_practices.md 范文提取

  触发条件: revision_count == 0 && feedback_action == "approve"
  执行时机: finalize 节点内异步执行（不阻塞主流程）
  提取模型: Qwen-Turbo（小模型）

  提取 Prompt:
    "以下是一篇被直接采纳的小红书文案，请提取其可复用的创作模式：

    选题：{user_input}
    品牌调性：{brand_context}
    文案内容：{final_copy}

    请提取以下三个要素：
    1. 标题公式：用变量占位关键词，如「{数字}个{场景}穿搭公式，{人群}必收藏」
    2. 正文结构模板：用 [] 标注结构块，如 [痛点切入]→[解决方案]→[产品引入]→[行动号召]
    3. 标签组合策略：归纳标签类型，如 1个核心词 + 2个场景词 + 1个人群词"

  写入格式:
    ## 案例 #2026-05-03 | 早秋通勤穿搭
    - 标题公式: 「{数字}套{季节}{场景}公式，{人群}照着穿就对了」
    - 结构模板: [季节痛点] → [单品推荐×3] → [搭配公式] → [产品植入] → [互动引导]
    - 标签策略: 1核心场景词 + 2风格词 + 1人群词
    - 得分: 一稿过 ⭐
    ---

8.3 进化二：高轮次修改 → negative_prompts.md 反思

  触发条件: revision_count > 3
  执行时机: finalize 节点内异步执行
  分析范围: feedback_history（全部反馈记录）+ draft_versions（各版本差异）

  提取 Prompt:
    "以下是一篇经历了 {revision_count} 轮修改才通过的文案任务，请分析失败根因：

    主题：{user_input}
    修改轮次：{revision_count}
    各轮反馈：
      第1轮：{feedback_history[0].feedback}
      第2轮：{feedback_history[1].feedback}
      ...

    请分类：
    - 标记为 NOT_A_RULE：本次特有的具体修改指令
    - 标记为 RULE：应永久避开的通用规则

    通用规则以 Markdown 列表项输出，每条规则须有明确指向：
    - [严禁/避免/务必] [具体行为]  原因：[简述]

    示例：
    - 避免正文首段超过 3 句  原因：用户多轮反馈开头冗长
    - 严禁标题使用超过 2 个感叹号  原因：用户认为过度夸张"

  写入格式:
    ## 反思 #2026-05-03 | 修改 4 轮任务
    - 避免正文首段超过 3 句  原因：用户认为开头冗长，失去阅读耐心
    - 严禁标题使用超过 2 个感叹号  原因：用户反馈语气过度夸张
    ---

  与进化三的区别:
    进化二：事后批量分析，从多轮修改中提取深层模式（慢思考）
    进化三：实时逐条判定，快速沉淀显性规则（快反应）

8.4 进化三：用户反馈实时提取 → negative_prompts.md 规则沉淀

  触发条件: feedback_action == "revise"（每次用户点击【发送重做】）
  执行时机: handle_feedback 节点触发异步旁路 extract_rules 节点
  提取模型: Qwen-Turbo
  详见: 第 6 节 extract_rules 节点定义

  判定逻辑:
    通用规则 → 追加写入 negative_prompts.md，带时间戳
    单次指令 (NOT_A_RULE) → 丢弃，不写入

  写入格式:
    <!-- 2026-05-03 14:30  -->
    - 严禁在正文中使用网络缩写（如 yyds、xswl）  → 追加到文件末尾

8.5 Token 瘦身机制

  触发条件: /assets/brand_data/ 下所有 .md 文件 Token 总量 > 8000
  检查时机: finalize 节点完成后 + 每次 Agent 启动时
  执行模型: 主力 LLM（需要判断内容质量，小模型精度不够）

  瘦身算法:

    对 best_practices.md:
      步骤 1: 保留最新 5 条案例（按日期排序）
      步骤 2: 保留最高分 3 条案例（一稿过优先，其次按人工评分）
      步骤 3: 其余案例 → LLM 压缩为一段"共性模板总结"，替换被移出的原文
      步骤 4: 合并去重语义相似的模板公式

    对 negative_prompts.md:
      步骤 1: 保留最新 10 条规则
      步骤 2: 历史规则 → LLM 做语义去重合并
        - "少用感叹号" + "避免夸张语气" → "避免夸张表达，禁用多余感叹号"
      步骤 3: 合并后输出精简规则表

    瘦身后检查:
      Token > 8000 → 保留最新+最高分，其余归档到 /assets/archive/{date}/
      Token < 4000 → 不做操作（保留生长空间，避免过早压缩）

  监控指标:
    Token 瘦身频率（次/周）：过高说明资产沉淀过快，考虑提高阈值
    瘦身后一稿过率变化：验证瘦身是否误删了有价值资产，若下降则回滚

8.6 资产文件完整生命周期

  ┌─────────────────────────────────────────────────────────────────┐
  │                    /assets/brand_data/                          │
  │                                                                │
  │  brand_voice.md   ←── 人工编写，Agent 不自动修改                  │
  │  product_info.md  ←── 人工编写，Agent 不自动修改                  │
  │                                                                │
  │  best_practices.md  ←── 一稿过自动追加                           │
  │      │                   Token 超标触发瘦身                      │
  │      ▼                                                        │
  │    增长 → 压缩 → 归档 (/assets/archive/)                        │
  │                                                                │
  │  negative_prompts.md ←── 用户反馈实时提取                        │
  │      │                   高轮次任务反思                           │
  │      ▼                                                        │
  │    增长 → 合并去重 → 压缩 → 归档                                 │
  └─────────────────────────────────────────────────────────────────┘

9. 核心业务流转 (Business Workflow, 结合看板流)
触发阶段 (Double Entry, Kanban Driven)：
  主动模式 (Agent-Driven)：系统通过每日定时任务或用户点击前端"发现热点"，Agent 调用 MediaCrawler 爬取小红书热搜及热门笔记，经 LLM 提炼后提报 3-5 个高潜选题卡片至看板"AI 灵感池"。用户可勾选并触发下一步。
  被动模式 (User-Driven)：用户在"In Progress"列新建输入明确主题（如："秋季穿搭"），或直接将灵感池卡片拖拽至"In Progress"列。
创作阶段：
  FastAPI 接收请求，初始化 LangGraph。Agent 读取本地 /assets/brand_data/ 下全部资产文件。LangGraph 流程执行：MediaCrawler 爬取热点/参考素材 → 读取资产库（含 Few-Shot 高分范文库）→ 撰写爆款文案初稿并生成国产图像大模型视觉策划 <Visual_Guidance> → 风控校验。
审核中断与交互：
  LangGraph 触发 interrupt_before 断点，状态持久化到 SQLite。前端看板监听到卡片状态变为 waiting_for_human，卡片流转至"Pending Review"列并 alert 提示。用户点击卡片弹出"双轨制"审核面板：
    分支 A（反馈与重做）：用户不满输入意见发送。Agent 标记 is_revision=True 回到撰写步骤重跑；同时异步触发"规则提取器"节点提炼硬性规则写入 negative_prompts.md。
    分支 B（微调与保存通过）：用户手动微调后点击【保存通过】。系统将 edited_draft_copy 设为最终结果，流转至 END。卡片落入"Done"列。
后处理阶段：
  卡片在"Done"列提供一键复制文本和国产提示词功能，用户物理发布。任务结束，系统异步触发进化：一稿过提取范文结构至 best_practices.md；修改轮次 > 3 触发反思更新避坑指南；Token 超标触发瘦身。

并发与取消策略：
  同一时间仅允许一个任务处于"In Progress"状态。若用户尝试新建任务，前端提示"有任务进行中，请等待或取消当前任务"并提供跳转。用户可随时取消"In Progress"状态的任务，状态更新为 cancelled 并回滚卡片。

10. 部署与环境依赖
极简部署流程：
  1. 克隆项目，uv sync 安装 Python 依赖
  2. uv run playwright install chromium 安装浏览器环境
  3. 配置 .env 填入 LLM API Key、图像模型 API Key
  4. 首次启动后扫码登录小红书（MediaCrawler 依赖），后续 Cookie 缓存维持登录态
  5. uvicorn 启动 FastAPI + npm run dev 启动前端，即可访问

11. 安全与鉴权
虽然是单租户本地部署，API 仍需基础保护：
  - API Key 鉴权：所有 /api/v1/* 接口校验 X-API-Key 请求头
  - CORS 白名单：仅允许本地前端 origin
  - .env 不入 Git，密钥全部通过环境变量注入

12. 成功度量指标 (Metrics) 与指标驱动迭代
初稿采纳率（一稿过率）：核心正向指标。修改轮次 = 0 的任务占比，直接驱动 best_practices.md 的 Few-Shot 样本库扩充。
平均修改轮次：核心摩擦指标。单次任务阈值 > 3 时，直接驱动 Agent 自我反思与 negative_prompts.md 更新。长期应呈下降趋势。
Token 效能：单次任务 Token 消耗及资产文件 Token 总量。累计 > 8000 token 时，触发 negative_prompts.md 与 best_practices.md 的异步总结压缩瘦身，确保记忆库高效轻量。
