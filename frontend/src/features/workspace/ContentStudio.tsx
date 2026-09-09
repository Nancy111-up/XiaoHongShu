import { useState } from "react"
import { getCalendar, getDrafts, scheduleDraft } from "../shared/api"
import type { Draft } from "../shared/types"
import { ModuleFrame, ResourceState, statusLabel, UpstreamAction, useWorkspaceResource } from "./WorkspaceShared"

async function loadStudio(signal?: AbortSignal) {
  const [drafts, calendar] = await Promise.all([getDrafts(signal), getCalendar(signal)])
  return { drafts:drafts.items, calendar:calendar.items }
}

export function ContentStudio({ onOpportunities, onCalendar }: { onOpportunities: () => void; onCalendar: () => void }) {
  const resource = useWorkspaceResource(loadStudio)
  return <ModuleFrame kicker="CONTENT STUDIO" title="管理已接受机会生成的完整内容草稿。">
    <ResourceState {...resource}/>
    {resource.data && (resource.data.drafts.length ? <div className="workspace-records">{resource.data.drafts.map(draft =>
      <DraftCard key={draft.id} draft={draft} alreadyScheduled={resource.data!.calendar.some(item => item.draftId === draft.id)} onCalendar={onCalendar}/>
    )}</div> : <UpstreamAction text="还没有草稿。前往热点机会，选择机会后点击「接受并生成草稿」。" label="前往热点机会" onClick={onOpportunities}/>)}
  </ModuleFrame>
}

function DraftCard({ draft, alreadyScheduled, onCalendar }: { draft: Draft; alreadyScheduled: boolean; onCalendar: () => void }) {
  const [when, setWhen] = useState("")
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState(false)
  async function schedule() {
    if (saving) return
    setSaving(true)
    setError(false)
    try {
      await scheduleDraft(draft.id, new Date(when).toISOString())
      setSaved(true)
    } catch { setError(true) }
    finally { setSaving(false) }
  }
  return <article className="panel workspace-record">
    <div className="record-heading"><h2>{draft.titles[0] || `草稿 ${draft.id}`}</h2><span className="status-pill pass">{statusLabel(draft.status)}</span></div>
    <p className="record-meta">品牌版本 v{draft.brandProfileVersion} · 草稿 ID：{draft.id}</p>
    <details><summary>查看完整草稿</summary>{draft.titles.length > 1 && <ul>{draft.titles.slice(1).map((title,index) => <li key={index}>{title}</li>)}</ul>}<p className="draft-body">{draft.body}</p><p>{draft.tags.map(tag => `#${tag}`).join(" ")}</p></details>
    {alreadyScheduled || saved ? <div><p role="status">{saved ? "排期已保存，可在内容日历查看。" : "该草稿已有排期。"}</p><button className="secondary-button" onClick={onCalendar}>查看内容日历</button></div> : <form className="schedule-form" onSubmit={event => { event.preventDefault(); void schedule() }}>
      <label>安排时间<input type="datetime-local" value={when} onChange={event => setWhen(event.target.value)} required disabled={saving}/></label>
      <p className="record-meta">使用当前设备时区。排期仅用于计划，不会自动发布。</p>
      <button className="primary-button" disabled={saving || !when}>{saving ? "正在保存…" : "保存排期"}</button>
      {error && <p role="alert">排期保存失败，请检查服务配置或查看是否已有排期。</p>}
    </form>}
  </article>
}
