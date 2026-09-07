"use client"

import { useState } from "react"

type Opportunity = { id:string; title:string; subtitle:string; heat:number; trend:string; lifecycle:string; confidence:string; score:number; angle:string; reason:string; titleOptions:string[]; preview:string }

const opportunities: Opportunity[] = [
  { id:"campus", title:"开学季校园跑热度上升", subtitle:"新生训练 × 基础跑步装备", heat:86, trend:"+24%", lifecycle:"上升期", confidence:"高", score:88, angle:"从第一双跑鞋出发，做一份不劝退新手的校园跑入门指南", reason:"近 7 天校园跑、开学体测与新手跑鞋讨论同步增长，和品牌的轻运动场景高度匹配。", titleOptions:["开学第一跑：新手别急着追配速","校园跑不劝退装备清单","从宿舍到操场，我只带这 5 件"], preview:"刚开始跑步时，真正需要的不是一套昂贵装备，而是一套愿意让你明天继续出门的轻量方案。" },
  { id:"night", title:"城市夜跑装备清单", subtitle:"夜间安全 × 轻量穿搭", heat:78, trend:"+17%", lifecycle:"成长期", confidence:"中高", score:82, angle:"夜跑安全与轻量装备组合", reason:"入秋后夜跑相关内容持续增长，用户更关注反光、安全收纳与温差穿搭。", titleOptions:["下班后的 5 公里，安全感这样穿","夜跑装备不是越多越好","城市夜跑：轻一点，也安全一点"], preview:"夜跑的自由感来自城市降温后的风，而安全感来自每一处看得见、拿得稳的小设计。" },
  { id:"outdoor", title:"周末户外恢复成为新习惯", subtitle:"轻徒步 × 运动恢复", heat:71, trend:"+11%", lifecycle:"萌芽期", confidence:"中", score:75, angle:"把周末轻户外做成都市运动人群的恢复日", reason:"轻徒步和恢复训练开始被同一批用户讨论，适合测试品牌的生活方式表达。", titleOptions:["周末不冲强度，我去山里恢复","运动人的恢复日可以在户外","轻徒步之后，身体真的松开了"], preview:"恢复不是停下来，而是换一种更柔和的方式继续移动。" },
]

const navItems = ["热点机会", "内容工作室", "内容日历", "数据复盘", "品牌大脑"]

export function OpportunityPage() {
  const [selectedId, setSelectedId] = useState(opportunities[0].id)
  const selected = opportunities.find((item) => item.id === selectedId) ?? opportunities[0]
  return <main className="workspace-shell">
    <aside className="sidebar">
      <div className="wordmark"><span className="wordmark-mark">B</span><div>BRAND PACE<small>SPORTS OPERATIONS</small></div></div>
      <div className="brand-context"><span className="brand-ball">RUN</span><div><small>当前品牌</small><strong>逐风运动</strong></div></div>
      <nav aria-label="主导航" className="main-nav"><span className="nav-label">工作空间</span>{navItems.map((item,index)=><button className={index===0?"nav-item active":"nav-item"} key={item} type="button"><span className="nav-icon">{["↗","✎","□","⌁","◎"][index]}</span><span>{item}<small>{["Opportunity","Studio","Calendar","Analytics","Brand Brain"][index]}</small></span></button>)}</nav>
      <div className="sidebar-foot"><span className="status-dot"/> 数据工作区已就绪</div>
    </aside>
    <section className="app-area">
      <header className="topbar"><div><p className="eyebrow">OPPORTUNITY DESK</p><h1>热点机会</h1></div><div className="topbar-actions"><span className="demo-badge">演示数据</span><button type="button" className="refresh-button">↻ 刷新热点</button><span className="avatar">林</span></div></header>
      <div className="workspace-grid">
        <section className="panel opportunity-list-panel"><div className="panel-head"><div><span className="panel-kicker">DISCOVER</span><h2>今日机会</h2></div><span className="count-pill">{opportunities.length} 条</span></div><div className="filter-row"><button className="filter active" type="button">全部</button><button className="filter" type="button">高潜</button><button className="filter" type="button">观察</button></div><div className="opportunity-list">{opportunities.map((item,index)=><button aria-pressed={item.id===selected.id} className={item.id===selected.id?"opportunity-card active":"opportunity-card"} key={item.id} onClick={()=>setSelectedId(item.id)} type="button"><span className="rank">0{index+1}</span><span className="card-copy"><strong>{item.title}</strong><small>{item.subtitle}</small><span className="mini-tags"><i>{item.lifecycle}</i><i className="hot">热度 {item.heat}</i></span></span><span className="card-score">{item.score}</span></button>)}</div><p className="source-note">数据更新时间：今天 09:00 · 仅用于界面预览</p></section>
        <section className="panel detail-panel"><div className="detail-hero"><div className="status-row"><span className="status-pill high">高潜机会</span><span className="status-pill pass">品牌适配</span></div><div className="hero-title"><div><span className="panel-kicker">OPPORTUNITY DETAIL</span><h2>{selected.title}</h2><p>{selected.subtitle}</p></div><div className="score-ring" style={{"--score":selected.score} as React.CSSProperties}><span>{selected.score}<small>机会分</small></span></div></div></div><div className="detail-content"><div className="metric-grid"><article><span>当前热度</span><strong>{selected.heat}</strong><div className="bar"><i style={{width:`${selected.heat}%`}}/></div></article><article><span>趋势变化</span><strong className="positive">{selected.trend}</strong><small>近 7 天</small></article><article><span>生命周期</span><strong>{selected.lifecycle}</strong><small>适合快速切入</small></article><article><span>分析置信度</span><strong>{selected.confidence}</strong><small>多来源信号</small></article></div><div className="section-title"><span>WHY NOW</span><h3>为什么值得现在做</h3></div><div className="explain-grid"><article><b>趋势信号</b><p>{selected.reason}</p></article><article><b>品牌连接</b><p>可以自然连接训练体验、装备选择与真实运动场景，不需要追逐泛热点。</p></article></div><div className="angle-box"><span>内容切入建议</span><h3>{selected.angle}</h3><p>以真实体验和实用建议建立可信度，避免硬性产品植入。</p></div><div className="source-links"><span>依据来源</span><a href="#source-1">小红书趋势样本 01 ↗</a><a href="#source-2">代表笔记样本 02 ↗</a></div></div></section>
        <aside className="panel preview-panel"><div className="preview-meta"><span className="panel-kicker">COPY PREVIEW</span><h2>内容预览</h2><p>基于当前机会生成的方向草案</p><div className="preview-facts"><div><span>目标</span><b>建立品牌认知</b></div><div><span>形式</span><b>清单 / 经验</b></div></div></div><div className="preview-content"><div className="section-title"><span>TITLE OPTIONS</span><h3>标题方向</h3></div>{selected.titleOptions.map((title,index)=><div className="title-option" key={title}><span>{index+1}</span>{title}</div>)}<div className="section-title"><span>OPENING</span><h3>开篇预览</h3></div><p className="preview-body">{selected.preview}</p><div className="decision-note"><b>人工决策提示</b><p>接受后将进入内容工作室，原始机会与生成记录会被完整保留。</p></div><button className="primary-button" type="button">接受并生成草稿</button><button className="secondary-button" type="button">暂不采用</button></div></aside>
      </div>
    </section>
  </main>
}
