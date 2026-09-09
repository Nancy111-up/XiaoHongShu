export function DataSourceBadge({ source }: { source: string }) {
  const labels: Record<string, string> = {
    live: "实时数据",
    partial: "部分实时数据",
    fixture: "测试数据",
    demo: "演示数据",
    unavailable: "数据不可用",
  }
  return <span className="demo-badge">{labels[source] ?? source}</span>
}
