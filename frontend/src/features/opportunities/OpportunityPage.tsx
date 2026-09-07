"use client"

import { useState } from "react"
import { DataSourceBadge } from "../shared/DataSourceBadge"
import type { Opportunity } from "../shared/types"
import { useOpportunities } from "./useOpportunities"

const navItems = ["热点机会", "内容工作室", "内容日历", "数据复盘", "品牌大脑"]

export function OpportunityPage() {
  const { items, data_source, loading, error, refresh } = useOpportunities()
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const selected = items.find((item) => item.id === selectedId) ?? items[0]

  return <main className="workspace-shell">
    <aside className="sidebar">
      <div className="wordmark"><span className="wordmark-mark">B</span><div>BRAND PACE<small>SPORTS OPERATIONS</small></div></div>
      <div className="brand-context"><span className="brand-ball">RUN</span><div><small>当前品牌</small><strong>体育品牌工作区</strong></div></div>
      <nav aria-label="主导航" className="main-nav"><span className="nav-label">工作空间</span>{navItems.map((item,index)=><button className={index===0?"nav-item active":"nav-item"} key={item} type="button"><span className="nav-icon">{["↗","✎","□","⌁","◎"][index]}</span><span>{item}<small>{["Opportunity","Studio","Calendar","Analytics","Brand Brain"][index]}</small></span></button>)}</nav>
      <div className="sidebar-foot"><span className="status-dot"/> 数据工作区已就绪</div>
    </aside>
    <section className="app-area">
      <header className="topbar"><div><p className="eyebrow">OPPORTUNITY DESK</p><h1>热点机会</h1></div><div className="topbar-actions"><DataSourceBadge source={data_source}/><button type="button" className="refresh-button" onClick={()=>void refresh()}>↻ 刷新热点</button><span className="avatar">林</span></div></header>
      {loading ? <StatePanel text="正在读取最新机会…"/> : error ? <StatePanel text={error}/> : !selected ? <StatePanel text="还没有可展示的机会，请先刷新热点。"/> : <Workspace items={items} selected={selected} onSelect={setSelectedId}/>} 
    </section>
  </main>
}

function StatePanel({ text }: { text: string }) {
  return <section className="panel" style={{margin:24,padding:40,textAlign:"center"}}><h2>{text}</h2><p>系统不会用演示内容冒充真实分析结果。</p></section>
}

function Workspace({ items, selected, onSelect }: {
  items: Opportunity[]; selected: Opportunity; onSelect: (id: string) => void
}) {
  const previewTitles = selected.preview?.titles ?? []
  return <div className="workspace-grid">
    <section className="panel opportunity-list-panel"><div className="panel-head"><div><span className="panel-kicker">DISCOVER</span><h2>今日机会</h2></div><span className="count-pill">{items.length} 条</span></div><div className="filter-row"><button className="filter active" type="button">全部</button><button className="filter" type="button">高潜</button><button className="filter" type="button">观察</button></div><div className="opportunity-list">{items.map((item,index)=><button aria-pressed={item.id===selected.id} className={item.id===selected.id?"opportunity-card active":"opportunity-card"} key={item.id} onClick={()=>onSelect(item.id)} type="button"><span className="rank">{String(index+1).padStart(2,"0")}</span><span className="card-copy"><strong>{item.title}</strong><small>{item.goal ?? "待确定内容目标"}</small><span className="mini-tags"><i>{item.trendStage ?? "观察中"}</i><i className="hot">热度 {item.currentHeat ?? "—"}</i></span></span><span className="card-score">{item.score ?? "—"}</span></button>)}</div><p className="source-note">数据更新时间：{new Date(selected.updatedAt).toLocaleString("zh-CN")}</p></section>
    <section className="panel detail-panel"><div className="detail-hero"><div className="status-row"><span className="status-pill high">{selected.decision}</span><span className="status-pill pass">{selected.eligibility}</span></div><div className="hero-title"><div><span className="panel-kicker">OPPORTUNITY DETAIL</span><h2>{selected.title}</h2><p>{selected.goal ?? "正在评估内容目标"}</p></div><div className="score-ring" style={{"--score":selected.score ?? 0} as React.CSSProperties}><span>{selected.score ?? "—"}<small>机会分</small></span></div></div></div><div className="detail-content"><div className="metric-grid"><Metric label="当前热度" value={selected.currentHeat}/><Metric label="趋势分" value={selected.trendScore}/><Metric label="生命周期" value={selected.trendStage}/><Metric label="分析置信度" value={selected.confidence}/></div><div className="section-title"><span>WHY NOW</span><h3>为什么值得现在做</h3></div><div className="explain-grid"><article><b>趋势信号</b><p>{selected.reasons.why_now ?? "暂无说明"}</p></article><article><b>品牌连接</b><p>{selected.reasons.why_brand ?? "暂无说明"}</p></article></div><div className="angle-box"><span>内容切入建议</span><h3>{selected.preview?.angle ?? "接受机会前先确认内容切入角度"}</h3></div><div className="source-links"><span>依据来源</span>{selected.sources.map((source,index)=><a href={source.url} key={source.url} target="_blank" rel="noreferrer">代表笔记 {index+1} ↗</a>)}</div></div></section>
    <aside className="panel preview-panel"><div className="preview-meta"><span className="panel-kicker">COPY PREVIEW</span><h2>内容预览</h2><p>基于当前机会生成的方向草案</p></div><div className="preview-content"><div className="section-title"><span>TITLE OPTIONS</span><h3>标题方向</h3></div>{previewTitles.length ? previewTitles.map((title,index)=><div className="title-option" key={title}><span>{index+1}</span>{title}</div>) : <p className="preview-body">尚未生成预览。</p>}<div className="section-title"><span>OPENING</span><h3>开篇预览</h3></div><p className="preview-body">{selected.preview?.body ?? "接受前可先生成轻量预览。"}</p><div className="decision-note"><b>人工决策提示</b><p>接受后进入内容工作室，原始机会与生成记录会被完整保留。</p></div><button className="primary-button" type="button">接受并生成草稿</button><button className="secondary-button" type="button">暂不采用</button></div></aside>
  </div>
}

function Metric({ label, value }: { label: string; value: string | number | null }) {
  return <article><span>{label}</span><strong>{value ?? "—"}</strong></article>
}
