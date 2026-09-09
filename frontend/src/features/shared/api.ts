import type { OpportunityResponse, RefreshJob } from "./types"

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api"

export async function getOpportunities(signal?: AbortSignal): Promise<OpportunityResponse> {
  const response = await fetch(`${API_BASE}/opportunities`, { signal })
  if (!response.ok) throw new Error(`API request failed: ${response.status}`)
  return response.json() as Promise<OpportunityResponse>
}

export async function startRefresh(): Promise<{ job: RefreshJob | null; jobId: string; joinedExistingJob: boolean }> {
  const response = await fetch(`${API_BASE}/refresh-jobs`, { method: "POST" })
  const payload = await response.json() as Record<string, unknown>
  if (response.ok && typeof payload.id === "string" && typeof payload.status === "string") {
    return { job: refreshJobFrom(payload), jobId: payload.id, joinedExistingJob: false }
  }
  if (response.status === 409 && payload.code === "REFRESH_ALREADY_RUNNING" && typeof payload.running_job_id === "string") {
    return {
      job: null,
      jobId: payload.running_job_id,
      joinedExistingJob: true,
    }
  }
  throw new Error("刷新任务启动失败")
}

export async function getRefreshJob(id: string): Promise<RefreshJob> {
  const response = await fetch(`${API_BASE}/refresh-jobs/${id}`)
  if (!response.ok) throw new Error("刷新进度暂时不可用")
  return refreshJobFrom(await response.json() as Record<string, unknown>)
}

function refreshJobFrom(payload: Record<string, unknown>): RefreshJob {
  if (typeof payload.id !== "string" || typeof payload.status !== "string") {
    throw new Error("刷新任务响应无效")
  }
  return {
    id: payload.id,
    status: payload.status,
    successfulKeywords: Array.isArray(payload.successfulKeywords) ? payload.successfulKeywords.filter((value): value is string => typeof value === "string") : [],
    failedKeywords: Array.isArray(payload.failedKeywords) ? payload.failedKeywords.filter((value): value is string => typeof value === "string") : [],
    errorSummary: typeof payload.errorSummary === "string" ? payload.errorSummary : null,
    updatedAt: typeof payload.updatedAt === "string" ? payload.updatedAt : "",
  }
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
