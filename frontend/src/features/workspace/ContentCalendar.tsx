import { getCalendar } from "../shared/api"
import { ModuleFrame, ResourceState, statusLabel, UpstreamAction, useWorkspaceResource } from "./WorkspaceShared"

export function ContentCalendar({ onStudio }: { onStudio: () => void }) {
  const resource = useWorkspaceResource(getCalendar)
  return <ModuleFrame kicker="CONTENT CALENDAR" title="安排草稿发布时间并查看生产节奏。">
    <ResourceState {...resource}/>
    {resource.data && (resource.data.items.length ? <div className="workspace-records">
      <p className="record-meta">时间按当前设备时区显示。排期不会自动发布。</p>
      {resource.data.items.map(item => <article key={item.id} className="panel workspace-record">
        <div className="record-heading"><h2>草稿 <span>{item.draftId}</span></h2><span className="status-pill pass">{statusLabel(item.status)}</span></div>
        <p>计划时间：<time dateTime={item.scheduledFor}>{new Date(item.scheduledFor).toLocaleString("zh-CN")}</time></p>
        <button className="secondary-button" onClick={onStudio}>前往内容工作室查看草稿</button>
      </article>)}
    </div> : <UpstreamAction text="还没有排期。前往内容工作室，为草稿选择「安排时间」并点击「保存排期」。" label="前往内容工作室" onClick={onStudio}/>)}
  </ModuleFrame>
}
