export type Opportunity = {
  id: string
  topicId: string
  title: string
  currentHeat: number | null
  trendScore: number | null
  trendStage: string | null
  score: number | null
  decision: string
  goal: string | null
  eligibility: string
  risk: string
  confidence: string
  scores: Record<string, number | null>
  reasons: Record<string, string>
  sources: Array<{ url: string }>
  preview: null | {
    titles?: string[]
    body?: string
    angle?: string
    format?: string
    tags?: string[]
  }
  updatedAt: string
  data_source: "live" | "fixture" | "demo"
}

export type OpportunityResponse = {
  items: Opportunity[]
  data_source: "live" | "fixture" | "demo" | "unavailable"
}

export type RefreshJob = {
  id: string
  status: string
  successfulKeywords: string[]
  failedKeywords: string[]
  errorSummary: string | null
  updatedAt: string
}

export type RefreshProgress = {
  id: string
  status: string
  stageLabel: string
  terminal: boolean
  failedKeywords: string[]
  safeErrorMessage: string | null
  joinedExistingJob: boolean
}

const refreshStageLabels: Record<string, string> = {
  queued: "等待刷新任务",
  collecting_search: "正在采集热点",
  collecting_detail: "正在补充笔记详情",
  normalizing: "正在整理数据",
  clustering: "正在归纳话题",
  enriching: "正在补充品牌信息",
  scoring_trend: "正在评估趋势",
  scoring_opportunity: "正在筛选机会",
  generating_preview: "正在生成内容预览",
  completed: "刷新完成",
  partial_success: "部分完成",
  failed: "刷新失败",
  interrupted: "刷新已中断",
}

export function toRefreshProgress(job: RefreshJob, joinedExistingJob = false): RefreshProgress {
  const terminal = ["completed", "partial_success", "failed", "interrupted"].includes(job.status)
  return {
    id: job.id,
    status: job.status,
    stageLabel: refreshStageLabels[job.status] ?? "正在刷新数据",
    terminal,
    failedKeywords: job.failedKeywords,
    safeErrorMessage: job.status === "partial_success"
      ? job.errorSummary
      : ["failed", "interrupted"].includes(job.status)
        ? job.errorSummary ?? "刷新未完成，请检查登录状态和数据源配置后重试。"
        : null,
    joinedExistingJob,
  }
}

export function awaitingExistingRefreshProgress(id: string): RefreshProgress {
  return {
    id,
    status: "awaiting_existing_status",
    stageLabel: "正在获取已有任务进度",
    terminal: false,
    failedKeywords: [],
    safeErrorMessage: null,
    joinedExistingJob: true,
  }
}
