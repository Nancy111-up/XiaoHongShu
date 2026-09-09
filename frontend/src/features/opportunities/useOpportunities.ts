"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import { getOpportunities, getRefreshJob, startRefresh } from "../shared/api"
import { awaitingExistingRefreshProgress, toRefreshProgress, type OpportunityResponse, type RefreshProgress } from "../shared/types"

export function useOpportunities() {
  const [data, setData] = useState<OpportunityResponse>({ items: [], data_source: "unavailable" })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [refreshProgress, setRefreshProgress] = useState<RefreshProgress | null>(null)
  const [refreshConnectionError, setRefreshConnectionError] = useState<string | null>(null)
  const [startingRefresh, setStartingRefresh] = useState(false)
  const [pollAttempt, setPollAttempt] = useState(0)
  const refreshStartInFlight = useRef(false)

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
    if (refreshStartInFlight.current || (refreshProgress && !refreshProgress.terminal)) return
    refreshStartInFlight.current = true
    setStartingRefresh(true)
    setRefreshConnectionError(null)
    try {
      const started = await startRefresh()
      setRefreshProgress(started.job
        ? toRefreshProgress(started.job, started.joinedExistingJob)
        : awaitingExistingRefreshProgress(started.jobId))
      setPollAttempt(0)
    } finally {
      refreshStartInFlight.current = false
      setStartingRefresh(false)
    }
  }, [refreshProgress])

  useEffect(() => {
    if (!refreshProgress || refreshProgress.terminal) return
    const timer = window.setTimeout(() => {
      void getRefreshJob(refreshProgress.id).then(async job => {
        const nextProgress = toRefreshProgress(job, refreshProgress.joinedExistingJob)
        setRefreshConnectionError(null)
        setRefreshProgress(nextProgress)
        if (nextProgress.terminal && (job.status === "completed" || job.status === "partial_success")) {
          await reload()
        }
      }).catch(() => {
        setRefreshConnectionError("刷新进度暂时不可用，正在继续尝试。")
        setPollAttempt(attempt => attempt + 1)
      })
    }, 1500)
    return () => window.clearTimeout(timer)
  }, [refreshProgress, reload, pollAttempt])

  useEffect(() => {
    const controller = new AbortController()
    void getOpportunities(controller.signal).then(setData).catch(() => {
      if (!controller.signal.aborted) setError("暂时无法连接数据服务")
    }).finally(() => {
      if (!controller.signal.aborted) setLoading(false)
    })
    return () => controller.abort()
  }, [])
  return {
    ...data,
    loading,
    error,
    reload,
    refresh,
    refreshProgress,
    refreshConnectionError,
    refreshing: startingRefresh || Boolean(refreshProgress && !refreshProgress.terminal),
  }
}
