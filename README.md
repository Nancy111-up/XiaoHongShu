# 体育品牌运营工作区（V0.1）

这是一个本地运行的体育品牌内容工作区。它以已固定版本的 MediaCrawler 收集小红书公开内容，经过两阶段采集、机会评分与可选的 LLM 分析后，在工作区中呈现内容机会、草稿、排期和基础复盘数据。

它不会生成演示记录来冒充真实结果，不会绕过登录或验证码，也不会自动发布到任何社交平台。

## 本地启动

需要 Windows、Git、[uv](https://docs.astral.sh/uv/)、Node.js/npm，以及已按下文准备好的 MediaCrawler 工作副本。所有命令均从仓库根目录开始。

### 1. 检查已固定的 MediaCrawler

刷新任务只会使用 `external/MediaCrawler` 下的官方副本，且在开始前验证它没有被替换、偏移版本或改脏。当前固定版本为：

```text
https://github.com/NanmiCoder/MediaCrawler.git
d6f7c5bb906b6dac40ddf343ef9e26438a3de092
```

可先运行以下检查；第三条没有输出才表示工作区干净：

```powershell
git -C external/MediaCrawler remote get-url origin
git -C external/MediaCrawler rev-parse HEAD
git -C external/MediaCrawler status --porcelain
```

配置文件为 `config/mediacrawler.yaml`：小红书平台、二维码登录、可见浏览器、JSONL 输出和单并发都已固定。不要将 Cookie、二维码截图、令牌或原始抓取日志提交到仓库。

### 2. 登录或恢复登录

推荐在工作区中点击“刷新热点”后，按 MediaCrawler 打开的可见浏览器窗口完成正常的二维码登录。当前配置使用 `login_type: qrcode`、`headless: false` 和 `max_concurrency: 1`；没有隐藏的登录绕过或 Cookie 导入步骤。

如果想先手动触发同一套登录方式，可在固定副本中执行一次有边界的搜索（将示例关键词替换为自己的品牌关键词）：

```powershell
cd external/MediaCrawler
uv run --frozen main.py --platform xhs --lt qrcode --save_data_option jsonl --max_concurrency_num 1 --headless false --type search --keywords "城市夜跑" --get_comment false --get_sub_comment false --crawler_max_notes_count 40
cd ../..
```

这会真正发起一次搜索，不是只登录的空操作。登录态过期、出现二维码或 CAPTCHA 时，停止等待并在该浏览器窗口完成正常人工登录，然后重新开始刷新；不要尝试绕过平台验证。若固定副本检查失败，恢复与上方 URL 和提交完全一致、且无未提交改动的副本后再试。

### 3. 配置 AI（机会分析和草稿生成需要）

复制 `backend/.env.example` 为 `backend/.env`，只在本机填写密钥：

```dotenv
# 首选名称；LLM_API_KEY 是同一个值的兼容别名。
DASHSCOPE_API_KEY=...

# 可选：不填时使用 DashScope 兼容模式地址与 qwen-plus。
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen-plus
```

`DASHSCOPE_API_KEY` 优先于 `LLM_API_KEY`。缺少有效 API key 时，采集数据仍会保留，但刷新会以“部分完成”结束，并提示 AI 分析未配置；系统不会编造机会或草稿。

### 4. 启动后端

首次运行或迁移有更新时：

```powershell
cd backend
uv sync --frozen
uv run --frozen alembic upgrade head
```

在一个终端启动 API：

```powershell
cd backend
uv run --frozen uvicorn src.app:create_app --factory --reload --port 8000
```

健康检查位于 `http://localhost:8000/health`，API 根路径为 `http://localhost:8000/api`。

### 5. 启动前端

在第二个终端启动前端：

```powershell
cd frontend
npm ci
npm run dev
```

打开 `http://localhost:3000`。若 API 不在本机 8000 端口，请在前端启动前设置 `NEXT_PUBLIC_API_URL`，例如 `http://localhost:8000/api`。

## 操作顺序

1. 在“品牌大脑”填写品牌定位、受众、场景、语气、禁用表达和内容策略；保存会创建新的品牌资料版本。
2. 回到“热点机会”，点击“刷新热点”。一次只允许一个活动刷新；若已有任务，界面会接入并继续显示该任务的进度。
3. 刷新依次经历搜索采集、标准化、聚类、代表笔记详情采集和机会评分。完成后机会列表会重新读取持久化结果；没有数据时保持空状态，不显示占位机会。
4. 在机会详情中审阅来源、评分、风险和内容切入角度。选择“接受并生成草稿”后，可在“内容工作室”查看草稿；选择“暂不采用”会保存拒绝原因。
5. 在“内容工作室”为草稿保存带时区的排期；“内容日历”按当前设备时区显示计划时间。排期仅记录计划，绝不自动发布。
6. 在“数据复盘”查看机会数、草稿数和草稿转化比。该比值是“草稿数 ÷ 机会数”，不是发布率、互动率或业务成效。

## 刷新结果与恢复

- **完成**：搜索、详情采集和机会分析均完成。
- **部分完成**：至少有一部分数据被安全保留，例如某些关键词或详情采集失败，或者 AI 未配置/不可用。查看界面中的失败关键词和安全摘要，修复后再次刷新。
- **失败**：没有任何搜索关键词采集成功，或固定副本/登录状态不可用。检查上述固定副本、正常登录和品牌关键词后重试。

原始采集输出位于忽略的 `data/raw/<刷新任务 ID>/`；本地 SQLite 数据位于忽略的 `backend/data/`。二者都属于本机运行数据，不能作为 Git 输入，也不应共享其中的凭据、令牌或原始内容。

## 当前边界与限制

- 自动化验证覆盖后端、前端和构建；本仓库不将本机浏览器、二维码登录、MediaCrawler 或第三方 LLM 的实时接受测试作为自动化通过条件。需要控制者在本地浏览器中按上面的流程验收。
- 刷新采用进程内后台任务和 SQLite，限制为单一活动任务；没有队列服务和高并发设计。
- 机会分析需要有效的 AI 配置。AI 不可用不会丢弃已采集内容，但不会产生伪造的机会。
- 工作区已提供“机会 → 草稿 → 日历 → 复盘”的界面和 API 合同；当前默认应用工厂尚未装配用于生成/保存草稿的 `ContentService` 实现。因此，默认本地启动的“接受并生成草稿”、拒绝和排期操作会返回服务不可用，直到该服务在应用层完成装配。该限制不影响品牌资料、刷新状态、已持久化机会或只读工作区视图。
- 当前复盘只有机会数、草稿数和草稿转化比；没有发布、互动或归因指标。

## 验证命令

后端使用锁定的 uv 环境；如本机系统临时目录权限受限，可指定工作区内的临时目录：

```powershell
cd backend
uv run --frozen pytest --basetemp .pytest-tmp-local -q
uv run --frozen ruff check .
uv run --frozen mypy src
```

完整的严格 `mypy .` 当前不是通过门槛：它会把独立探针以两个模块名发现，且严格检查还会报告该探针和测试辅助代码的既有类型错误。生产源码范围 `mypy src` 是可复现的类型检查范围。运行后请删除自动生成的 `.pytest-tmp-local` 目录。

```powershell
cd frontend
npm test -- --run
npm run lint
npm run build
```
