
● 好的。Round 5 确实过于庞大——9 个新/改节点 + MCP 封装 +
  图拓扑重连。让我按自底向上的独立性拆解。                                   
                                                                             
  ---
  Round 5 拆解计划                                                           
                  
  Sub-round 5.1: 品牌资产补全 + 敏感词配置化                                 
                  
  文件: best_practices.md, config.toml, sensitive_words.py, compliance.py

  - 创建第 4 份品牌资产 best_practices.md
  - config.toml 新增 [compliance] 段，迁移硬编码敏感词
  - 新建 agent/tools/sensitive_words.py — 从 config 加载敏感词词典
  - 更新 compliance.py 使用配置化敏感词

  Sub-round 5.2: init_task 节点

  文件: agent/nodes/init_task.py

  - 纯逻辑，无外部依赖
  - thread_id = uuid4()，判断 source（inspiration vs manual）
  - 初始化 revision_count=0, is_revision=False, violation_count=0

  Sub-round 5.3: load_assets 节点

  文件: agent/nodes/load_assets.py

  - 从 write_node 拆出品牌资产加载逻辑
  - 读取 4 个 .md → brand_context, product_context, best_practices,
  negative_prompts
  - 独立可验证：输入任意 state、输出 4 字段

  Sub-round 5.4: MCP Client 封装 + crawl_trends 节点

  文件: agent/tools/mcp_client.py, agent/nodes/crawl_trends.py

  - mcp_client.py — langchain-mcp-adapters MultiServerMCPClient 单例
  - crawl_trends.py — 调用 MCP search_trends → Qwen-Turbo 提炼 trends_context
  - 30s 超时 + 降级逻辑
  - 移除/弃用 tavily_search.py

  Sub-round 5.5: generate_visuals 节点

  文件: agent/nodes/generate_visuals.py

  - 强制 JSON 输出 VisualGuidance 结构
  - 2-3 个国产模型适配 prompt（CogView / 文心一格 / 通义万相）
  - 校验：禁止输出外网模型 prompt

  Sub-round 5.6: 风控增强 + human_review 独立

  文件: agent/nodes/compliance.py, agent/nodes/human_review.py

  - compliance 第二层：LLM 二次判定 → pass / mild_warning / severe_violation
  - 严重违规累计 ≥ 3 次 → 直接 END
  - human_review 从 graph.py 内联提取为独立节点文件

  Sub-round 5.7: handle_feedback + extract_rules 节点

  文件: agent/nodes/handle_feedback.py, agent/nodes/extract_rules.py

  - handle_feedback — 纯路由：approve → finalize, revise → generate_copy +
  触发 extract_rules
  - extract_rules — 小模型判定反馈是否通用规则 → 写入 negative_prompts.md

  Sub-round 5.8: generate_copy 增强 + finalize 节点

  文件: agent/nodes/generate_copy.py, agent/nodes/finalize.py

  - generate_copy 增强：强制 JSON 结构化输出 {title, body, tags,
  Sub-round 5.8: generate_copy 增强 + finalize 节点

  文件: agent/nodes/generate_copy.py, agent/nodes/finalize.py

  - generate_copy 增强：强制 JSON 结构化输出 {title, body, tags,
  ad_placement}
  - is_revision=True 时跳过趋势上下文，基于 feedback 重写
  - finalize — 一稿过写 best_practices.md，高轮次写
  negative_prompts.md，Token>8000 触发瘦身

  Sub-round 5.9: 图拓扑重连

  文件: agent/graph.py

  Sub-round 5.9: 图拓扑重连

  文件: agent/graph.py

  - 10 节点完整拓扑，对齐 §4 流程图
  - 全部 conditional edges（§4.2 表格）

  - 10 节点完整拓扑，对齐 §4 流程图
  - 全部 conditional edges（§4.2 表格）
  - SqliteSaver checkpoint 集成（替换 MemorySaver）

  ---
  依赖关系：

  5.1 ──┬── 5.2 ── 5.3 ──┐
  - SqliteSaver checkpoint 集成（替换 MemorySaver）

  ---
  依赖关系：

  5.1 ──┬── 5.2 ── 5.3 ──┐
        │                  ├── 5.7 ── 5.8 ── 5.9
        │                  ├── 5.7 ── 5.8 ── 5.9
  文件: agent/nodes/generate_copy.py, agent/nodes/finalize.py

  - generate_copy 增强：强制 JSON 结构化输出 {title, body, tags,
  ad_placement}
  - is_revision=True 时跳过趋势上下文，基于 feedback 重写
  - finalize — 一稿过写 best_practices.md，高轮次写
  negative_prompts.md，Token>8000 触发瘦身

  Sub-round 5.9: 图拓扑重连

  文件: agent/graph.py

  - 10 节点完整拓扑，对齐 §4 流程图
  - 全部 conditional edges（§4.2 表格）
  - SqliteSaver checkpoint 集成（替换 MemorySaver）

  ---
  依赖关系：

  5.1 ──┬── 5.2 ── 5.3 ──┐
        │                  ├── 5.7 ── 5.8 ── 5.9
        5.4 ───────────────┤
                            ├── 5.5 ──────────────┘
                            └── 5.6 ──────────────┘

  5.1 → 5.4 可并行；5.2/5.3/5.5/5.6 依赖 5.1 的部分产物但互不依赖；5.7/5.8
  依赖前面的节点就位；5.9 收尾。

