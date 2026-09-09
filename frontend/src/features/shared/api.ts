import type { Analytics, BrandProfile, BrandProfileResponse, BrandProfileVersion, CalendarItem, Draft, OpportunityResponse, RefreshJob } from "./types"

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

async function getWorkspaceModule<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${API_BASE}/${path}`, { signal })
  if (!response.ok) throw new Error("模块数据加载失败")
  return response.json() as Promise<T>
}

export const getDrafts = (signal?: AbortSignal) => getWorkspaceModule<{ items: Draft[] }>("drafts", signal)
export const getCalendar = (signal?: AbortSignal) => getWorkspaceModule<{ items: CalendarItem[] }>("calendar", signal)
export const getAnalytics = (signal?: AbortSignal) => getWorkspaceModule<Analytics>("analytics", signal)
export const getBrandProfile = (signal?: AbortSignal) => getWorkspaceModule<BrandProfileResponse>("brand-profile", signal)

export async function scheduleDraft(id: string, when: string): Promise<CalendarItem> {
  const response = await fetch(`${API_BASE}/drafts/${encodeURIComponent(id)}/schedule?${new URLSearchParams({ when })}`, { method: "POST" })
  if (!response.ok) throw new Error("排期保存失败，请检查服务配置或查看是否已有排期。")
  return response.json() as Promise<CalendarItem>
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

export async function saveBrandProfile(profile: BrandProfile): Promise<BrandProfileVersion> {
  const response = await fetch(`${API_BASE}/brand-profile`, {
    method: "PUT",
    headers: { "Content-Type":"application/json" },
    body: JSON.stringify(profile),
  })
  if (!response.ok) throw new Error("品牌大脑保存失败")
  return response.json() as Promise<BrandProfileVersion>
}
