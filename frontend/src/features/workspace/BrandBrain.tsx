import { useState } from "react"
import { getBrandProfile, saveBrandProfile } from "../shared/api"
import type { BrandProfile, BrandProfileResponse } from "../shared/types"
import { ModuleFrame, ResourceState, useWorkspaceResource } from "./WorkspaceShared"

const emptyProfile: BrandProfile = { positioning:"", audiences:[], scenes:[], tone:[], forbidden:[], content_strategy:{ traffic:40, brand:35, product:25 }, products:[] }
const listFields = [
  ["audiences", "目标人群（每行一项）"], ["scenes", "使用场景（每行一项）"],
  ["tone", "品牌语气（每行一项）"], ["forbidden", "禁用表达（每行一项）"],
] as const
const strategies = [["traffic", "流量"], ["brand", "品牌"], ["product", "产品"]] as const

export function BrandBrain() {
  const resource = useWorkspaceResource(getBrandProfile)
  return <ModuleFrame kicker="BRAND BRAIN" title="品牌定位与内容策略">
    <ResourceState {...resource}/>
    {resource.data && <BrandForm initial={resource.data}/>}
  </ModuleFrame>
}

function BrandForm({ initial }: { initial: BrandProfileResponse }) {
  const initialProfile = "profile" in initial ? initial.profile : emptyProfile
  const [profile, setProfile] = useState(initialProfile)
  const [lists, setLists] = useState(() => Object.fromEntries(listFields.map(([key]) => [key, initialProfile[key].join("\n")])))
  const [version, setVersion] = useState("version" in initial ? initial.version : null)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState("")
  const [error, setError] = useState("")
  async function save() {
    if (saving) return
    setMessage("")
    setError("")
    if (Object.values(profile.content_strategy).reduce((sum,value) => sum + value, 0) !== 100) {
      setError("内容策略比例合计必须为 100%。")
      return
    }
    setSaving(true)
    try {
      const payload = { ...profile }
      for (const [key] of listFields) payload[key] = lists[key].split("\n").map(value => value.trim()).filter(Boolean)
      const saved = await saveBrandProfile(payload)
      setProfile(saved.profile)
      setVersion(saved.version)
      setMessage("品牌大脑已保存")
    } catch { setError("品牌大脑保存失败，请重试。") }
    finally { setSaving(false) }
  }
  return <form className="brand-form" onSubmit={event => { event.preventDefault(); void save() }}>
    <p>{version ? `当前版本 v${version}` : "尚未配置品牌大脑。填写品牌定位与内容策略，点击「保存品牌大脑」创建首个版本。"}</p>
    <fieldset disabled={saving}>
      <label>品牌定位<textarea value={profile.positioning} onChange={event => setProfile({ ...profile, positioning:event.target.value })} required/></label>
      <div className="brand-fields">{listFields.map(([key,label]) => <label key={key}>{label}<textarea value={lists[key]} onChange={event => setLists({ ...lists, [key]:event.target.value })}/></label>)}</div>
      <div className="strategy-inputs">{strategies.map(([key,label]) => <label key={key}>{label}占比（%）<input type="number" min="0" max="100" step="1" required value={profile.content_strategy[key]} onChange={event => setProfile({ ...profile, content_strategy:{ ...profile.content_strategy, [key]:Number(event.target.value) } })}/></label>)}</div>
      <section><h3>关联产品</h3>{profile.products.length ? <ul>{profile.products.map(product => <li key={product.id}><strong>{product.name}</strong>{product.selling_point && ` · ${product.selling_point}`}</li>)}</ul> : <p className="record-meta">暂无关联产品。</p>}</section>
    </fieldset>
    <button className="primary-button" type="submit" disabled={saving}>{saving ? "正在保存…" : "保存品牌大脑"}</button>
    {message && <p role="status">{message}</p>}{error && <p role="alert">{error}</p>}
  </form>
}
