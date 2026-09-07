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
