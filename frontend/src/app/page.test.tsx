import { render, screen } from "@testing-library/react"
import Page from "./page"

it("renders the five V0.4 workspace modules", () => {
  render(<Page />)
  for (const name of ["热点机会", "内容工作室", "内容日历", "数据复盘", "品牌大脑"]) {
    expect(screen.getByRole("button", { name: new RegExp(name) })).toBeInTheDocument()
  }
})
