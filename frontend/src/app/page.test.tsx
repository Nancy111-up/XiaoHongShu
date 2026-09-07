import { render, screen } from "@testing-library/react"
import { vi } from "vitest"
import Page from "./page"

it("renders the five V0.4 workspace modules", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({ items: [], data_source: "unavailable" }),
  }))
  render(<Page />)
  await screen.findByText("数据不可用")
  for (const name of ["热点机会", "内容工作室", "内容日历", "数据复盘", "品牌大脑"]) {
    expect(screen.getByRole("button", { name: new RegExp(name) })).toBeInTheDocument()
  }
})
