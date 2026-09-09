"use client"

import { useCallback, useEffect, useState } from "react"
import { getOpportunities, getRefreshJob, startRefresh } from "../shared/api"
import { toRefreshProgress, type OpportunityResponse, type RefreshProgress } from "../shared/types"

export function useOpportunities() {
  const [data, setData] = useState<OpportunityResponse>({ items: [], data_source: "unavailable" })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [refreshProgress, setRefreshProgress] = useState<RefreshProgress | null>(null)

  const reload = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setData(await getOpportunities())
    } catch {
      setError("暂时无法连接数据服务")
    } finally {
      setLoading(false)
    }
  }, [])

  const refresh = useCallback(async () => {
    if (refreshProgress && !refreshProgress.terminal) return
    const started = await startRefresh()
    setRefreshProgress(toRefreshProgress(started.job, started.joinedExistingJob))
  }, [refreshProgress])

  useEffect(() => {
    if (!refreshProgress || refreshProgress.terminal) return
    const timer = window.setTimeout(() => {
      void getRefreshJob(refreshProgress.id).then(async job => {
        const nextProgress = toRefreshProgress(job, refreshProgress.joinedExistingJob)
        setRefreshProgress(nextProgress)
        if (nextProgress.terminal && (job.status === "completed" || job.status === "partial_success")) {
          await reload()
        }
      }).catch(() => {
        setRefreshProgress({
          ...refreshProgress,
          status: "failed",
          stageLabel: "刷新失败",
          terminal: true,
          safeErrorMessage: "刷新进度暂时不可用，请检查登录状态和数据源配置后重试。",
        })
      })
    }, 1500)
    return () => window.clearTimeout(timer)
  }, [refreshProgress, reload])

  useEffect(() => {
    const controller = new AbortController()
    void getOpportunities(controller.signal).then(setData).catch(() => {
      if (!controller.signal.aborted) setError("暂时无法连接数据服务")
    }).finally(() => {
      if (!controller.signal.aborted) setLoading(false)
    })
    return () => controller.abort()
  }, [])
  return { ...data, loading, error, reload, refresh, refreshProgress, refreshing: Boolean(refreshProgress && !refreshProgress.terminal) }
}
