import { act, fireEvent, render, screen } from "@testing-library/react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { OpportunityPage } from "./OpportunityPage"

const items = [
  { id:"one", topicId:"t1", title:"开学季校园跑", currentHeat:86, trendScore:78,
    trendStage:"Growing", score:88, decision:"High Opportunity", goal:"品牌", eligibility:"eligible",
    risk:"low", confidence:"High", scores:{}, reasons:{why_now:"讨论增长"}, sources:[],
    preview:{titles:["标题一","标题二","标题三"], body:"预览正文", angle:"校园跑指南"},
    updatedAt:"2026-09-07T09:00:00Z", data_source:"live" },
  { id:"two", topicId:"t2", title:"城市夜跑装备清单", currentHeat:78, trendScore:71,
    trendStage:"Growing", score:82, decision:"Recommend", goal:"产品", eligibility:"eligible",
    risk:"low", confidence:"Medium", scores:{}, reasons:{why_now:"夜跑升温"}, sources:[],
    preview:{titles:["夜跑一","夜跑二","夜跑三"], body:"夜跑预览", angle:"夜跑安全与轻量装备组合"},
    updatedAt:"2026-09-07T09:00:00Z", data_source:"live" },
]

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn().mockImplementation(async (url: string, options?: RequestInit) => {
    if (options?.method === "POST") return { ok:true, status:202, json:async()=>({ id:"job-default", status:"queued" }) }
    if (url.endsWith("/brand-profile")) return { ok:true, json:async()=>({status:"not_configured"}) }
    return { ok:true, json:async()=>({items,data_source:"live"}) }
  }))
})

afterEach(() => {
  vi.useRealTimers()
  vi.unstubAllGlobals()
})

function job(status: string, overrides: Record<string, unknown> = {}) {
  return {
    id: "job-live",
    status,
    successfulKeywords: [],
    failedKeywords: [],
    errorSummary: null,
    updatedAt: "2026-09-08T09:00:00Z",
    ...overrides,
  }
}

describe("OpportunityPage", () => {
  it("renders live decision data", async () => {
    render(<OpportunityPage />)
    expect(await screen.findByText("实时数据")).toBeInTheDocument()
    expect(screen.getByText("总机会")).toBeInTheDocument()
    expect(screen.getByText("高潜机会")).toBeInTheDocument()
    expect(screen.getByText("待审核")).toBeInTheDocument()
    expect(screen.getByText("已生成草稿")).toBeInTheDocument()
    expect(screen.getByTestId("app-shell")).toHaveClass("fresh-forest")
    expect(screen.getByRole("button", { name: "接受并生成草稿" })).toBeInTheDocument()
  })

  it("updates the real draft total after accepting an opportunity", async () => {
    vi.stubGlobal("fetch", vi.fn().mockImplementation(async (url: string, options?: RequestInit) => {
      if (options?.method === "POST") return { ok:true, status:200, json:async()=>({}) }
      if (url.endsWith("/analytics")) return { ok:true, json:async()=>({opportunities:2,drafts:0}) }
      return { ok:true, json:async()=>({items,data_source:"live"}) }
    }))
    render(<OpportunityPage />)
    fireEvent.click(await screen.findByRole("button", { name: "接受并生成草稿" }))
    expect(await screen.findByText("草稿已生成")).toBeInTheDocument()
    expect(screen.getByText("已生成草稿").previousElementSibling).toHaveTextContent("1")
  })

  it("renders the preview contract persisted by the opportunity pipeline", async () => {
    const pipelineItem = {
      ...items[0],
      preview: {
        titles:["夜跑装备怎么选", "夜跑装备｜夜跑装备怎么选", "夜跑装备怎么选｜实用指南"],
        angle:"夜跑装备选择",
        body:"从使用场景出发\n场景\n选择",
        format:"图文",
        tags:[],
      },
    }
    vi.stubGlobal("fetch", vi.fn(async (url: string) => ({
      ok:true,
      json:async()=>url.endsWith("/analytics")
        ? {opportunities:1,drafts:4}
        : {items:[pipelineItem],data_source:"live"},
    })))

    render(<OpportunityPage />)

    expect(await screen.findByText("夜跑装备怎么选")).toBeInTheDocument()
    expect(screen.getByText("夜跑装备选择")).toBeInTheDocument()
    expect(screen.getByText(/从使用场景出发/)).toBeInTheDocument()
    expect(screen.getByText("4")).toBeInTheDocument()
  })

  it("labels populated partial results as partial live data", async () => {
    vi.stubGlobal("fetch", vi.fn(async (url: string) => ({
      ok:true,
      json:async()=>url.endsWith("/analytics")
        ? {opportunities:2,drafts:1}
        : {items,data_source:"partial"},
    })))
    render(<OpportunityPage />)
    expect(await screen.findByText("部分实时数据")).toBeInTheDocument()
  })

  it("changes the detail when another opportunity is selected", async () => {
    render(<OpportunityPage />)
    fireEvent.click(await screen.findByRole("button", { name: /城市夜跑装备清单/ }))
    expect(screen.getByRole("heading", { name: "城市夜跑装备清单", level: 2 })).toBeInTheDocument()
    expect(screen.getByText("夜跑安全与轻量装备组合")).toBeInTheDocument()
  })

  it("navigates to every workspace module", async () => {
    render(<OpportunityPage />)
    fireEvent.click(await screen.findByRole("button", { name: /品牌大脑/ }))
    expect(screen.getByRole("heading", { name: "品牌大脑", level: 1 })).toBeInTheDocument()
    expect(screen.getByText("品牌定位与内容策略")).toBeInTheDocument()
    expect(await screen.findByText(/尚未配置品牌大脑/)).toBeInTheDocument()
    expect(screen.getByLabelText("品牌定位")).toBeInTheDocument()
    expect(screen.getByRole("button", { name:"保存品牌大脑" })).toBeInTheDocument()
  })

  it("shows the queued stage after starting a real refresh", async () => {
    vi.stubGlobal("fetch", vi.fn().mockImplementation(async (url: string, options?: RequestInit) => {
      if (options?.method === "POST") return { ok:true, status:202, json:async()=>({ id:"job-queued", status:"queued" }) }
      return { ok:true, json:async()=>({items,data_source:"live"}) }
    }))
    render(<OpportunityPage />)
    fireEvent.click(screen.getByRole("button", { name: /刷新热点/ }))
    await act(async () => {})
    expect(screen.getByText("等待刷新任务")).toBeInTheDocument()
    expect(fetch).toHaveBeenCalledWith(expect.stringContaining("/refresh-jobs"),
      expect.objectContaining({ method:"POST" }))
  })

  it("polls an active refresh, disables duplicate starts, and reloads opportunities after completion", async () => {
    vi.useFakeTimers()
    const stages = [job("collecting_search"), job("completed")]
    vi.stubGlobal("fetch", vi.fn().mockImplementation(async (url: string, options?: RequestInit) => {
      if (options?.method === "POST") return { ok:true, status:202, json:async()=>({ id:"job-live", status:"queued" }) }
      if (url.includes("/refresh-jobs/job-live")) return { ok:true, json:async()=>stages.shift() }
      return { ok:true, json:async()=>({items,data_source:"live"}) }
    }))
    render(<OpportunityPage />)
    fireEvent.click(screen.getByRole("button", { name: /刷新热点/ }))
    await act(async () => {})
    expect(screen.getByText("等待刷新任务")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /刷新热点/ })).toBeDisabled()

    await act(async () => { await vi.advanceTimersByTimeAsync(1500) })
    expect(screen.getByText("正在采集热点")).toBeInTheDocument()

    await act(async () => { await vi.advanceTimersByTimeAsync(1500) })
    expect(screen.getByText("刷新完成")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /刷新热点/ })).toBeEnabled()
    expect(fetch).toHaveBeenCalledWith(expect.stringContaining("/opportunities"), { signal: undefined })
  })

  it("shows partial completion and the keywords that could not be refreshed", async () => {
    vi.useFakeTimers()
    vi.stubGlobal("fetch", vi.fn().mockImplementation(async (url: string, options?: RequestInit) => {
      if (options?.method === "POST") return { ok:true, status:202, json:async()=>({ id:"job-live", status:"queued" }) }
      if (url.includes("/refresh-jobs/job-live")) return { ok:true, json:async()=>job("partial_success", { failedKeywords:["城市夜跑"] }) }
      return { ok:true, json:async()=>({items,data_source:"live"}) }
    }))
    render(<OpportunityPage />)
    fireEvent.click(screen.getByRole("button", { name: /刷新热点/ }))
    await act(async () => {})
    await act(async () => { await vi.advanceTimersByTimeAsync(1500) })
    expect(screen.getByText("部分完成")).toBeInTheDocument()
    expect(screen.getByText("城市夜跑")).toBeInTheDocument()
  })

  it("shows the safe partial-success summary even when every keyword was collected", async () => {
    vi.useFakeTimers()
    vi.stubGlobal("fetch", vi.fn().mockImplementation(async (url: string, options?: RequestInit) => {
      if (options?.method === "POST") return { ok:true, status:202, json:async()=>({ id:"job-live", status:"queued" }) }
      if (url.includes("/refresh-jobs/job-live")) return { ok:true, json:async()=>job("partial_success", { errorSummary:"AI 服务未配置，请在品牌大脑中配置模型。" }) }
      return { ok:true, json:async()=>({items,data_source:"live"}) }
    }))
    render(<OpportunityPage />)
    fireEvent.click(screen.getByRole("button", { name: /刷新热点/ }))
    await act(async () => {})
    await act(async () => { await vi.advanceTimersByTimeAsync(1500) })
    expect(screen.getByText("部分完成")).toBeInTheDocument()
    expect(screen.getByText("AI 服务未配置，请在品牌大脑中配置模型。")).toBeInTheDocument()
  })

  it("guides the user to login, configure, and retry when the refresh fails", async () => {
    vi.useFakeTimers()
    vi.stubGlobal("fetch", vi.fn().mockImplementation(async (url: string, options?: RequestInit) => {
      if (options?.method === "POST") return { ok:true, status:202, json:async()=>({ id:"job-live", status:"queued" }) }
      if (url.includes("/refresh-jobs/job-live")) return { ok:true, json:async()=>job("failed", { errorSummary:"数据源暂时不可用" }) }
      return { ok:true, json:async()=>({items,data_source:"live"}) }
    }))
    render(<OpportunityPage />)
    fireEvent.click(screen.getByRole("button", { name: /刷新热点/ }))
    await act(async () => {})
    await act(async () => { await vi.advanceTimersByTimeAsync(1500) })
    expect(screen.getByText("刷新失败")).toBeInTheDocument()
    expect(screen.getByText("请检查登录状态和数据源配置后重试。")).toBeInTheDocument()
    expect(screen.getByText("数据源暂时不可用")).toBeInTheDocument()
  })

  it("keeps polling the last confirmed job after a progress connection error", async () => {
    vi.useFakeTimers()
    let pollCount = 0
    vi.stubGlobal("fetch", vi.fn().mockImplementation(async (url: string, options?: RequestInit) => {
      if (options?.method === "POST") return { ok:true, status:202, json:async()=>({ id:"job-live", status:"queued" }) }
      if (url.includes("/refresh-jobs/job-live")) {
        pollCount += 1
        if (pollCount === 1) throw new Error("temporary network loss")
        return { ok:true, json:async()=>job("completed") }
      }
      return { ok:true, json:async()=>({items,data_source:"live"}) }
    }))
    render(<OpportunityPage />)
    fireEvent.click(screen.getByRole("button", { name: /刷新热点/ }))
    await act(async () => {})
    await act(async () => { await vi.advanceTimersByTimeAsync(1500) })
    expect(screen.getByText("等待刷新任务")).toBeInTheDocument()
    expect(screen.getByText("刷新进度暂时不可用，正在继续尝试。" )).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /刷新热点/ })).toBeDisabled()

    await act(async () => { await vi.advanceTimersByTimeAsync(1500) })
    expect(screen.getByText("刷新完成")).toBeInTheDocument()
    expect(screen.queryByText("刷新进度暂时不可用，正在继续尝试。")).not.toBeInTheDocument()
  })

  it("continues polling the active job returned by a duplicate refresh response", async () => {
    vi.useFakeTimers()
    vi.stubGlobal("fetch", vi.fn().mockImplementation(async (url: string, options?: RequestInit) => {
      if (options?.method === "POST") return { ok:false, status:409, json:async()=>({ code:"REFRESH_ALREADY_RUNNING", running_job_id:"job-existing" }) }
      if (url.includes("/refresh-jobs/job-existing")) return { ok:true, json:async()=>job("collecting_detail", { id:"job-existing" }) }
      return { ok:true, json:async()=>({items,data_source:"live"}) }
    }))
    render(<OpportunityPage />)
    fireEvent.click(screen.getByRole("button", { name: /刷新热点/ }))
    await act(async () => {})
    expect(screen.getByText("正在获取已有任务进度")).toBeInTheDocument()
    expect(screen.getByText("已有刷新任务正在进行，将继续显示其进度。")).toBeInTheDocument()
    await act(async () => { await vi.advanceTimersByTimeAsync(1500) })
    expect(screen.getByText("正在补充笔记详情")).toBeInTheDocument()
  })

  it("disables refresh before a pending POST can be started twice", async () => {
    let resolveStart: (response: { ok: boolean; status: number; json: () => Promise<{ id: string; status: string }> }) => void = () => {}
    vi.stubGlobal("fetch", vi.fn().mockImplementation(async (url: string, options?: RequestInit) => {
      if (options?.method === "POST") return new Promise(resolve => { resolveStart = resolve })
      return { ok:true, json:async()=>({items,data_source:"live"}) }
    }))
    render(<OpportunityPage />)
    const refreshButton = screen.getByRole("button", { name: /刷新热点/ })
    fireEvent.click(refreshButton)
    expect(refreshButton).toBeDisabled()
    fireEvent.click(refreshButton)
    expect(vi.mocked(fetch).mock.calls.filter(([, options]) => options?.method === "POST")).toHaveLength(1)

    await act(async () => { resolveStart({ ok:true, status:202, json:async()=>({ id:"job-live", status:"queued" }) }) })
  })
})
