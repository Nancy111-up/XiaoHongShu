import type { OpportunityResponse } from "./types"

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api"

export async function getOpportunities(signal?: AbortSignal): Promise<OpportunityResponse> {
  const response = await fetch(`${API_BASE}/opportunities`, { signal })
  if (!response.ok) throw new Error(`API request failed: ${response.status}`)
  return response.json() as Promise<OpportunityResponse>
}

export async function startRefresh(): Promise<void> {
  const response = await fetch(`${API_BASE}/refresh-jobs`, { method: "POST" })
  if (!response.ok && response.status !== 409) throw new Error("刷新任务启动失败")
}

export async function getWorkspaceModule(path: string): Promise<Record<string, unknown>> {
  const response = await fetch(`${API_BASE}/${path}`)
  if (!response.ok) throw new Error("模块数据加载失败")
  return response.json() as Promise<Record<string, unknown>>
}

export async function acceptOpportunity(id: string): Promise<void> {
  const response = await fetch(`${API_BASE}/opportunities/${id}/accept`, { method: "POST" })
  if (!response.ok) throw new Error(response.status === 503 ? "请先配置 AI 模型" : "生成草稿失败")
}

export async function rejectOpportunity(id: string): Promise<void> {
  const response = await fetch(`${API_BASE}/opportunities/${id}/reject`, {
    method: "POST",
    headers: { "Content-Type":"application/json" },
    body: JSON.stringify({ reason:"other" }),
  })
  if (!response.ok) throw new Error("暂不采用操作失败")
}

export async function saveBrandProfile(positioning: string): Promise<void> {
  const response = await fetch(`${API_BASE}/brand-profile`, {
    method: "PUT",
    headers: { "Content-Type":"application/json" },
    body: JSON.stringify({ positioning, audiences:[], scenes:[], tone:[], forbidden:[],
      content_strategy:{ traffic:40, brand:35, product:25 }, products:[] }),
  })
  if (!response.ok) throw new Error("品牌大脑保存失败")
}
