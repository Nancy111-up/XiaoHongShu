"use client"

import { useEffect, useState } from "react"
import { DataSourceBadge } from "../shared/DataSourceBadge"
import { acceptOpportunity, getWorkspaceModule, rejectOpportunity, saveBrandProfile } from "../shared/api"
import type { Opportunity } from "../shared/types"
import { useOpportunities } from "./useOpportunities"

const navItems = ["热点机会", "内容工作室", "内容日历", "数据复盘", "品牌大脑"]

export function OpportunityPage() {
  const { items, data_source, loading, error, refresh, refreshProgress, refreshing } = useOpportunities()
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [activeModule, setActiveModule] = useState(0)
  const [notice, setNotice] = useState<string | null>(null)
  const selected = items.find((item) => item.id === selectedId) ?? items[0]

  async function handleRefresh() {
    try {
      await refresh()
    } catch {
      setNotice("刷新任务未能启动，请检查登录状态和数据源配置后重试。")
    }
  }

  const highPotential = items.filter(item=>item.score!==null&&item.score>=80).length
  const manualReview = items.filter(item=>item.eligibility==="manual_review").length
  return <main className="workspace-shell fresh-forest" data-testid="app-shell">
    <aside className="sidebar">
      <div className="wordmark"><span className="wordmark-mark">B</span><div>BRAND PACE<small>SPORTS OPERATIONS</small></div></div>
      <div className="brand-context"><span className="brand-ball">RUN</span><div><small>当前品牌</small><strong>体育品牌工作区</strong></div></div>
      <nav aria-label="主导航" className="main-nav"><span className="nav-label">工作空间</span>{navItems.map((item,index)=><button className={index===activeModule?"nav-item active":"nav-item"} key={item} type="button" onClick={()=>setActiveModule(index)}><span className="nav-icon">{["↗","✎","□","⌁","◎"][index]}</span><span>{item}<small>{["Opportunity","Studio","Calendar","Analytics","Brand Brain"][index]}</small></span></button>)}</nav>
      <div className="sidebar-foot"><span className="status-dot"/> 数据工作区已就绪</div>
    </aside>
    <section className="app-area">
      <header className="topbar"><div><p className="eyebrow">{["OPPORTUNITY DESK","CONTENT STUDIO","CALENDAR","ANALYTICS","BRAND BRAIN"][activeModule]}</p><h1>{navItems[activeModule]}</h1></div><div className="topbar-actions"><DataSourceBadge source={data_source}/>{activeModule===0&&<button type="button" className="refresh-button" disabled={refreshing} aria-busy={refreshing} onClick={()=>void handleRefresh()}>↻ 刷新热点</button>}<span className="avatar">林</span></div></header>
      {notice&&<div className="notice" role="status">{notice}<button onClick={()=>setNotice(null)}>×</button></div>}
      {activeModule===0&&refreshProgress&&<RefreshProgressPanel progress={refreshProgress}/>}
      {activeModule===0&&<><section className="summary-strip"><Summary label="总机会" value={items.length}/><Summary label="高潜机会" value={highPotential}/><Summary label="待审核" value={manualReview}/><Summary label="已生成草稿" value={0}/></section><nav className="insight-tabs" aria-label="机会视图"><button className="active">热点洞察</button><button>趋势变化</button><button>内容缺口</button><button>品牌适配</button><button>产品机会</button></nav></>}
      {activeModule!==0 ? <ModuleView index={activeModule}/> : loading ? <StatePanel text="正在读取最新机会…"/> : error ? <StatePanel text={error}/> : !selected ? <StatePanel text="还没有可展示的机会，请先刷新热点。"/> : <Workspace items={items} selected={selected} onSelect={setSelectedId} onNotice={setNotice}/>} 
    </section>
  </main>
}

function RefreshProgressPanel({ progress }: { progress: NonNullable<ReturnType<typeof useOpportunities>["refreshProgress"]> }) {
  const isFailure = progress.status === "failed" || progress.status === "interrupted"
  return <section className={`refresh-progress ${progress.terminal ? "terminal" : "active"} ${isFailure ? "failed" : ""}`} role="status" aria-live="polite">
    <div className="refresh-progress-main">
      <span className="refresh-progress-indicator" aria-hidden="true"/>
      <div>
        <strong>{progress.stageLabel}</strong>
        <p>任务 ID：{progress.id}</p>
      </div>
    </div>
    <div className="refresh-progress-copy">
      {progress.joinedExistingJob && !progress.terminal && <p>已有刷新任务正在进行，将继续显示其进度。</p>}
      {progress.failedKeywords.length > 0 && <p>未完成关键词：{progress.failedKeywords.map(keyword => <span className="failed-keyword" key={keyword}>{keyword}</span>)}</p>}
      {isFailure && <p>{progress.safeErrorMessage ?? "刷新未完成，请检查登录状态和数据源配置后重试。"}</p>}
      {isFailure && <p>请检查登录状态和数据源配置后重试。</p>}
    </div>
  </section>
}

function StatePanel({ text }: { text: string }) {
  return <section className="panel" style={{margin:24,padding:40,textAlign:"center"}}><h2>{text}</h2><p>系统不会用演示内容冒充真实分析结果。</p></section>
}

function Workspace({ items, selected, onSelect, onNotice }: {
  items: Opportunity[]; selected: Opportunity; onSelect: (id: string) => void; onNotice:(text:string)=>void
}) {
  const previewTitles = selected.preview?.titles ?? []
  return <div className="workspace-grid">
    <section className="panel opportunity-list-panel"><div className="panel-head"><div><span className="panel-kicker">DISCOVER</span><h2>今日机会</h2></div><span className="count-pill">{items.length} 条</span></div><div className="filter-row"><button className="filter active" type="button">全部</button><button className="filter" type="button">高潜</button><button className="filter" type="button">观察</button></div><div className="opportunity-list">{items.map((item,index)=><button aria-pressed={item.id===selected.id} className={item.id===selected.id?"opportunity-card active":"opportunity-card"} key={item.id} onClick={()=>onSelect(item.id)} type="button"><span className="rank">{String(index+1).padStart(2,"0")}</span><span className="card-copy"><strong>{item.title}</strong><small>{item.goal ?? "待确定内容目标"}</small><span className="mini-tags"><i>{item.trendStage ?? "观察中"}</i><i className="hot">热度 {item.currentHeat ?? "—"}</i></span></span><span className="card-score">{item.score ?? "—"}</span></button>)}</div><p className="source-note">数据更新时间：{new Date(selected.updatedAt).toLocaleString("zh-CN")}</p></section>
    <section className="panel detail-panel"><div className="detail-hero"><div className="status-row"><span className="status-pill high">{selected.decision}</span><span className="status-pill pass">{selected.eligibility}</span></div><div className="hero-title"><div><span className="panel-kicker">OPPORTUNITY DETAIL</span><h2>{selected.title}</h2><p>{selected.goal ?? "正在评估内容目标"}</p></div><div className="score-ring" style={{"--score":selected.score ?? 0} as React.CSSProperties}><span>{selected.score ?? "—"}<small>机会分</small></span></div></div></div><div className="detail-content"><div className="metric-grid"><Metric label="当前热度" value={selected.currentHeat}/><Metric label="趋势分" value={selected.trendScore}/><Metric label="生命周期" value={selected.trendStage}/><Metric label="分析置信度" value={selected.confidence}/></div><div className="section-title"><span>WHY NOW</span><h3>为什么值得现在做</h3></div><div className="explain-grid"><article><b>趋势信号</b><p>{selected.reasons.why_now ?? "暂无说明"}</p></article><article><b>品牌连接</b><p>{selected.reasons.why_brand ?? "暂无说明"}</p></article></div><div className="angle-box"><span>内容切入建议</span><h3>{selected.preview?.angle ?? "接受机会前先确认内容切入角度"}</h3></div><div className="source-links"><span>依据来源</span>{selected.sources.map((source,index)=><a href={source.url} key={source.url} target="_blank" rel="noreferrer">代表笔记 {index+1} ↗</a>)}</div></div></section>
    <aside className="panel preview-panel"><div className="preview-meta"><span className="panel-kicker">COPY PREVIEW</span><h2>内容预览</h2><p>基于当前机会生成的方向草案</p></div><div className="preview-content"><div className="section-title"><span>TITLE OPTIONS</span><h3>标题方向</h3></div>{previewTitles.length ? previewTitles.map((title,index)=><div className="title-option" key={title}><span>{index+1}</span>{title}</div>) : <p className="preview-body">尚未生成预览。</p>}<div className="section-title"><span>OPENING</span><h3>开篇预览</h3></div><p className="preview-body">{selected.preview?.body ?? "接受前可先生成轻量预览。"}</p><div className="decision-note"><b>人工决策提示</b><p>接受后进入内容工作室，原始机会与生成记录会被完整保留。</p></div><button className="primary-button" type="button" onClick={()=>void acceptOpportunity(selected.id).then(()=>onNotice("草稿已生成")).catch((e:Error)=>onNotice(e.message))}>接受并生成草稿</button><button className="secondary-button" type="button" onClick={()=>void rejectOpportunity(selected.id).then(()=>onNotice("已记录：暂不采用")).catch((e:Error)=>onNotice(e.message))}>暂不采用</button></div></aside>
  </div>
}

const moduleConfig = [
  null,
  { path:"drafts", intro:"管理已接受机会生成的完整内容草稿。", empty:"还没有草稿" },
  { path:"calendar", intro:"安排草稿发布时间并查看生产节奏。", empty:"还没有排期" },
  { path:"analytics", intro:"复盘机会发现与内容转化表现。", empty:"数据积累后将在这里生成复盘" },
  { path:"brand-profile", intro:"品牌定位与内容策略", empty:"尚未配置品牌大脑" },
]

function ModuleView({ index }: { index:number }) {
  const config = moduleConfig[index]!
  const [state,setState] = useState("正在加载…")
  useEffect(()=>{let active=true;void getWorkspaceModule(config.path).then(data=>{
    if(!active)return
    const count=Array.isArray(data.items)?data.items.length:0
    setState(count?`已载入 ${count} 条记录`:config.empty)
  }).catch(()=>active&&setState("暂时无法加载该模块"));return()=>{active=false}},[config])
  return <section className="module-page"><div className="module-hero"><span>WORKSPACE / 0{index+1}</span><h2>{config.intro}</h2><p>{state}</p></div>{index===4?<BrandForm/>:<div className="module-empty"><b>{navItems[index]}</b><p>{state}</p></div>}</section>
}

function BrandForm() {
  const [positioning,setPositioning]=useState("")
  const [message,setMessage]=useState("")
  return <form className="brand-form" onSubmit={event=>{event.preventDefault();void saveBrandProfile(positioning).then(()=>setMessage("品牌大脑已保存")).catch((e:Error)=>setMessage(e.message))}}><label>品牌定位<textarea value={positioning} onChange={event=>setPositioning(event.target.value)} placeholder="例如：为城市跑者提供专业、轻量的运动体验" required/></label><div className="strategy-row"><span>流量 40%</span><span>品牌 35%</span><span>产品 25%</span></div><button className="primary-button" type="submit">保存品牌大脑</button>{message&&<p role="status">{message}</p>}</form>
}

function Metric({ label, value }: { label: string; value: string | number | null }) {
  return <article><span>{label}</span><strong>{value ?? "—"}</strong></article>
}

function Summary({label,value}:{label:string;value:number}) {
  return <article><strong>{value}</strong><span>{label}</span></article>
}
