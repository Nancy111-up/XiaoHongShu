  终端 1 — 启动后端（端口 8000）                                                                                                                 
  cd "D:\Program Files\XiaoHongShu\backend"                                                                                                      
  uv run uvicorn src.main:app --reload --port 8000                                                                                               
                                                                                                                                                 
  终端 2 — 启动前端（端口 3000）                                                                                                                 
  cd "D:\Program Files\XiaoHongShu\frontend"
  npm run dev                                                                                                                                    
                                                                                                                                                 
  ---
  如果之前没有安装过 Playwright 的浏览器，还需要额外执行一次：
  cd "D:\Program Files\XiaoHongShu\backend"
  uv run playwright install chromium
  （只需要 chromium，后端用的是 Playwright 做网页抓取，不需要 Firefox/WebKit）

  ---
  启动后访问：
  - 后端 API 文档：http://localhost:8000/docs
  - 前端页面：http://localhost:3000
  - 健康检查：http://localhost:8000/health