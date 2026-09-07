"use client"

import { useCallback, useEffect, useState } from "react"
import { getOpportunities, startRefresh } from "../shared/api"
import type { OpportunityResponse } from "../shared/types"

export function useOpportunities() {
  const [data, setData] = useState<OpportunityResponse>({ items: [], data_source: "unavailable" })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

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
    await startRefresh()
    await reload()
  }, [reload])

  useEffect(() => {
    const controller = new AbortController()
    void getOpportunities(controller.signal).then(setData).catch(() => {
      if (!controller.signal.aborted) setError("暂时无法连接数据服务")
    }).finally(() => {
      if (!controller.signal.aborted) setLoading(false)
    })
    return () => controller.abort()
  }, [])
  return { ...data, loading, error, reload, refresh }
}
