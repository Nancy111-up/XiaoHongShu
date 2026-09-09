import { act, fireEvent, render, screen, within } from "@testing-library/react"
import { afterEach, describe, expect, it, vi } from "vitest"
import { OpportunityPage } from "../opportunities/OpportunityPage"

const draft = { id:"draft-1", sourceOpportunityId:"opp-1", topicId:"topic-1", brandProfileVersion:3,
  promptVersion:"v1", titles:["城市晨跑计划", "晨跑装备指南"], body:"真实草稿正文", tags:["晨跑"], status:"draft" }
const profile = { positioning:"城市跑者的专业伙伴", audiences:["城市跑者"], scenes:["晨跑"], tone:["专业"],
  forbidden:["绝对化承诺"], content_strategy:{ traffic:50, brand:30, product:20 },
  products:[{ id:"shoe-1", name:"轻量跑鞋", category:"鞋", audience:"跑者", scene:"晨跑", selling_point:"轻量", goal:"转化", inventory:"充足" }] }

function respond(resources: Record<string, unknown>, failure?: string) {
  vi.stubGlobal("fetch", vi.fn(async (url: string) => {
    const path = new URL(url).pathname.split("/").pop()!
    if (path === failure) return { ok:false, status:500, json:async()=>({ message:"secret stderr" }) }
    return { ok:true, json:async()=>path === "opportunities" ? { items:[], data_source:"live" } : resources[path] ?? (path === "calendar" ? {items:[]} : undefined) }
  }))
}

async function openModule(name: string) {
  render(<OpportunityPage />)
  fireEvent.click(screen.getByRole("button", { name:new RegExp(name) }))
  await act(async () => {})
}

afterEach(() => vi.unstubAllGlobals())

describe("populated operational workspaces", () => {
  it("shows real draft titles, status, body and schedules with an explicit date", async () => {
    respond({ drafts:{ items:[draft] } })
    await openModule("内容工作室")
    expect(screen.getByRole("heading", { name:"城市晨跑计划" })).toBeInTheDocument()
    expect(screen.getByText("草稿")).toBeInTheDocument()
    fireEvent.click(screen.getByText("查看完整草稿"))
    expect(screen.getByText("真实草稿正文")).toBeVisible()
    fireEvent.change(screen.getByLabelText("安排时间"), { target:{ value:"2026-09-15T09:30" } })
    vi.mocked(fetch).mockImplementationOnce(async () => ({ ok:true, json:async()=>({ id:"cal-1", draftId:"draft-1", scheduledFor:"2026-09-15T01:30:00Z", status:"scheduled" }) }) as Response)
    fireEvent.click(screen.getByRole("button", { name:"保存排期" }))
    expect(await screen.findByText("排期已保存，可在内容日历查看。")).toBeInTheDocument()
    const call = vi.mocked(fetch).mock.calls.find(([url])=>String(url).includes("/schedule?"))!
    expect(new URL(String(call[0])).searchParams.get("when")).toBe(new Date("2026-09-15T09:30").toISOString())
    expect(call[1]?.method).toBe("POST")
  })

  it("shows calendar dates and statuses from the scheduling resource", async () => {
    respond({ calendar:{ items:[{ id:"cal-1", draftId:"draft-1", scheduledFor:"2026-09-15T01:30:00Z", status:"scheduled" }] } })
    await openModule("内容日历")
    expect(screen.getByText("draft-1")).toBeInTheDocument()
    expect(screen.getByText("已排期")).toBeInTheDocument()
    expect(document.querySelector("time")).toHaveAttribute("datetime", "2026-09-15T01:30:00Z")
    expect(document.querySelector("time")?.textContent).toContain("2026")
  })

  it("derives a clearly labeled draft conversion ratio from real counts", async () => {
    respond({ analytics:{ opportunities:8, drafts:3 } })
    await openModule("数据复盘")
    expect(within(screen.getByRole("article", { name:"机会总数" })).getByText("8")).toBeInTheDocument()
    expect(within(screen.getByRole("article", { name:"草稿总数" })).getByText("3")).toBeInTheDocument()
    expect(screen.getByText("37.5%")).toBeInTheDocument()
    expect(screen.getByText(/草稿数 ÷ 机会数/)).toBeInTheDocument()
  })

  it("loads and saves the full versioned brand profile without discarding existing fields", async () => {
    respond({ "brand-profile":{ version:3, profile } })
    await openModule("品牌大脑")
    expect(screen.getByText("当前版本 v3")).toBeInTheDocument()
    expect(screen.getByLabelText("品牌定位")).toHaveValue(profile.positioning)
    expect(screen.getByLabelText("目标人群（每行一项）")).toHaveValue("城市跑者")
    expect(screen.getByText("轻量跑鞋")).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText("品牌定位"), { target:{ value:"更新后的品牌定位" } })
    vi.mocked(fetch).mockImplementationOnce(async (_url, options) => ({ ok:true, json:async()=>({ version:4, profile:JSON.parse(options!.body as string) }) }) as Response)
    fireEvent.click(screen.getByRole("button", { name:"保存品牌大脑" }))
    expect(await screen.findByText("当前版本 v4")).toBeInTheDocument()
    expect(screen.getByText("品牌大脑已保存")).toBeInTheDocument()
    const save = vi.mocked(fetch).mock.calls.find(([,options])=>options?.method === "PUT")!
    expect(JSON.parse(save[1]!.body as string)).toEqual({ ...profile, positioning:"更新后的品牌定位" })
  })

  it.each([
    ["内容工作室", "drafts"], ["内容日历", "calendar"], ["数据复盘", "analytics"], ["品牌大脑", "brand-profile"],
  ])("shows a loading state while %s is pending", async (name, path) => {
    vi.stubGlobal("fetch", vi.fn(async (url:string)=>url.endsWith(path) ? new Promise(()=>{}) : { ok:true, json:async()=>({items:[],data_source:"live"}) }))
    await openModule(name)
    expect(screen.getByRole("status")).toHaveTextContent("正在加载")
  })

  it.each([
    ["内容工作室", "drafts"], ["内容日历", "calendar"], ["数据复盘", "analytics"], ["品牌大脑", "brand-profile"],
  ])("shows a safe error and retry for %s", async (name, path) => {
    respond({}, path)
    await openModule(name)
    expect(screen.getByRole("alert")).toHaveTextContent("暂时无法加载")
    expect(screen.queryByText("secret stderr")).not.toBeInTheDocument()
    expect(screen.getByRole("button", { name:"重新加载" })).toBeInTheDocument()
  })

  it.each([
    ["内容工作室", "drafts", {items:[]}, "前往热点机会", "热点机会"],
    ["内容日历", "calendar", {items:[]}, "前往内容工作室", "内容工作室"],
    ["数据复盘", "analytics", {opportunities:0,drafts:0}, "前往热点机会", "热点机会"],
  ])("points empty %s to its upstream workspace", async (name, path, data, action, destination) => {
    respond({ [path]:data, drafts:{items:[]} })
    await openModule(name as string)
    fireEvent.click(screen.getByRole("button", { name:action as string }))
    await act(async () => {})
    expect(screen.getByRole("heading", { level:1, name:destination as string })).toBeInTheDocument()
  })

  it("shows a create form for an unconfigured brand", async () => {
    respond({ "brand-profile":{ status:"not_configured" } })
    await openModule("品牌大脑")
    expect(screen.getByText(/尚未配置品牌大脑/)).toBeInTheDocument()
    expect(screen.getByLabelText("品牌定位")).toHaveValue("")
    expect(screen.getByRole("button", { name:"保存品牌大脑" })).toBeInTheDocument()
  })

  it("retains edits and current version after a brand save failure", async () => {
    respond({ "brand-profile":{ version:3, profile } })
    await openModule("品牌大脑")
    fireEvent.change(screen.getByLabelText("品牌定位"), { target:{ value:"未保存定位" } })
    vi.mocked(fetch).mockRejectedValueOnce(new Error("private connection detail"))
    fireEvent.click(screen.getByRole("button", { name:"保存品牌大脑" }))
    expect(await screen.findByRole("alert")).toHaveTextContent("品牌大脑保存失败")
    expect(screen.getByLabelText("品牌定位")).toHaveValue("未保存定位")
    expect(screen.getByText("当前版本 v3")).toBeInTheDocument()
    expect(screen.queryByText("private connection detail")).not.toBeInTheDocument()
  })

  it("does not offer duplicate scheduling for a draft already in the calendar", async () => {
    respond({ drafts:{items:[draft]}, calendar:{items:[{ id:"cal-1", draftId:draft.id, scheduledFor:"2026-09-15T01:30:00Z", status:"scheduled" }]} })
    await openModule("内容工作室")
    expect(screen.getByText("该草稿已有排期。")).toBeInTheDocument()
    expect(screen.queryByRole("button", {name:"保存排期"})).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", {name:"查看内容日历"}))
    expect(await screen.findByText("已排期")).toBeInTheDocument()
  })

  it("keeps scheduling available with a safe message when the service fails", async () => {
    respond({ drafts:{items:[draft]} })
    await openModule("内容工作室")
    fireEvent.change(screen.getByLabelText("安排时间"), {target:{value:"2026-09-15T09:30"}})
    vi.mocked(fetch).mockRejectedValueOnce(new Error("private detail"))
    fireEvent.click(screen.getByRole("button", {name:"保存排期"}))
    expect(await screen.findByRole("alert")).toHaveTextContent("排期保存失败")
    expect(screen.getByLabelText("安排时间")).toHaveValue("2026-09-15T09:30")
    expect(screen.getByRole("button", {name:"保存排期"})).toBeEnabled()
  })

  it("reloads a failed resource when requested", async () => {
    respond({}, "analytics")
    await openModule("数据复盘")
    expect(screen.getByRole("alert")).toBeInTheDocument()
    respond({analytics:{opportunities:8,drafts:3}})
    fireEvent.click(screen.getByRole("button", {name:"重新加载"}))
    expect(await screen.findByText("37.5%")).toBeInTheDocument()
    expect(screen.queryByRole("alert")).not.toBeInTheDocument()
  })

  it("uses no ratio for a zero denominator", async () => {
    respond({analytics:{opportunities:0,drafts:0}})
    await openModule("数据复盘")
    expect(within(screen.getByRole("article", {name:"草稿转化比"})).getByText("—")).toBeInTheDocument()
    expect(screen.queryByText(/NaN|Infinity/)).not.toBeInTheDocument()
  })

  it("prevents saving strategy percentages that do not total 100", async () => {
    respond({"brand-profile":{version:3,profile}})
    await openModule("品牌大脑")
    fireEvent.change(screen.getByLabelText("流量占比（%）"), {target:{value:"80"}})
    fireEvent.click(screen.getByRole("button", {name:"保存品牌大脑"}))
    expect(screen.getByRole("alert")).toHaveTextContent("合计必须为 100%")
    expect(vi.mocked(fetch).mock.calls.some(([,options])=>options?.method === "PUT")).toBe(false)
  })
})
