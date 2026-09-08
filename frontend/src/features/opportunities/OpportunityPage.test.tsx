import { fireEvent, render, screen } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
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
    if (options?.method === "POST") return { ok:true, status:202, json:async()=>({}) }
    return { ok:true, json:async()=>({items,data_source:"live"}) }
  }))
})

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
    expect(await screen.findByText("已载入 2 条记录")).toBeInTheDocument()
    expect(screen.getByLabelText("品牌定位")).toBeInTheDocument()
    expect(screen.getByRole("button", { name:"保存品牌大脑" })).toBeInTheDocument()
  })

  it("starts a real refresh and shows feedback", async () => {
    render(<OpportunityPage />)
    fireEvent.click(await screen.findByRole("button", { name: /刷新热点/ }))
    expect(await screen.findByText("刷新任务已启动")).toBeInTheDocument()
    expect(fetch).toHaveBeenCalledWith(expect.stringContaining("/refresh-jobs"),
      expect.objectContaining({ method:"POST" }))
  })
})
