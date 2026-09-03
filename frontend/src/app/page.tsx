const modules = ["热点机会", "内容工作室", "内容日历", "数据复盘", "品牌大脑"]

export default function Page() {
  return (
    <main>
      <h1>体育品牌运营 Agent</h1>
      <nav aria-label="工作区模块">
        {modules.map((name) => (
          <button key={name} type="button">
            {name}
          </button>
        ))}
      </nav>
    </main>
  )
}
