import { getAnalytics } from "../shared/api"
import { ModuleFrame, ResourceState, UpstreamAction, useWorkspaceResource } from "./WorkspaceShared"

export function AnalyticsDashboard({ onOpportunities }: { onOpportunities: () => void }) {
  const resource = useWorkspaceResource(getAnalytics)
  const data = resource.data
  return <ModuleFrame kicker="ANALYTICS" title="复盘机会发现与内容转化表现。">
    <ResourceState {...resource}/>
    {data && <>
      <div className="analytics-counts">
        <article aria-label="机会总数" className="panel workspace-record"><h2>机会总数</h2><strong>{data.opportunities}</strong></article>
        <article aria-label="草稿总数" className="panel workspace-record"><h2>草稿总数</h2><strong>{data.drafts}</strong></article>
        <article aria-label="草稿转化比" className="panel workspace-record"><h2>草稿转化比</h2><strong>{data.opportunities > 0 ? `${(data.drafts / data.opportunities * 100).toFixed(1)}%` : "—"}</strong></article>
      </div>
      <p className="record-meta">草稿转化比 = 草稿数 ÷ 机会数 × 100%。一条机会可生成多份草稿，因此该比值可能超过 100%；这不是发布率或互动率。</p>
      {data.opportunities === 0 && <UpstreamAction text="暂无机会数据。前往热点机会点击「刷新热点」，再对选定机会点击「接受并生成草稿」以积累转化数据。" label="前往热点机会" onClick={onOpportunities}/>}
    </>}
  </ModuleFrame>
}
