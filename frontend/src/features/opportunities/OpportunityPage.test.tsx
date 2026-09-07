import { fireEvent, render, screen } from "@testing-library/react"
import { OpportunityPage } from "./OpportunityPage"

describe("OpportunityPage", () => {
  it("renders the decision workspace with clearly labelled demo data", () => {
    render(<OpportunityPage />)

    expect(screen.getByRole("heading", { name: "热点机会" })).toBeInTheDocument()
    expect(screen.getByText("演示数据")).toBeInTheDocument()
    expect(screen.getByRole("navigation", { name: "主导航" })).toBeInTheDocument()
    expect(screen.getByText("当前热度")).toBeInTheDocument()
    expect(screen.getByText("内容切入建议")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "接受并生成草稿" })).toBeInTheDocument()
  })

  it("changes the decision detail when another opportunity is selected", () => {
    render(<OpportunityPage />)

    fireEvent.click(screen.getByRole("button", { name: /城市夜跑装备清单/ }))

    expect(screen.getByRole("heading", { name: "城市夜跑装备清单", level: 2 })).toBeInTheDocument()
    expect(screen.getByText("夜跑安全与轻量装备组合")).toBeInTheDocument()
  })
})
