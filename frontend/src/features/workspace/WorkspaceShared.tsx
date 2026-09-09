import { useEffect, useState, type ReactNode } from "react"

export function useWorkspaceResource<T>(load: (signal?: AbortSignal) => Promise<T>) {
  const [state, setState] = useState<{ data: T | null; loading: boolean; error: boolean }>({ data:null, loading:true, error:false })
  const [attempt, setAttempt] = useState(0)
  useEffect(() => {
    const controller = new AbortController()
    void load(controller.signal).then(data => {
      if (!controller.signal.aborted) setState({ data, loading:false, error:false })
    }).catch(() => {
      if (!controller.signal.aborted) setState({ data:null, loading:false, error:true })
    })
    return () => controller.abort()
  }, [load, attempt])
  function retry() {
    setState({ data:null, loading:true, error:false })
    setAttempt(value => value + 1)
  }
  return { ...state, retry }
}

export function ModuleFrame({ kicker, title, children }: { kicker: string; title: string; children: ReactNode }) {
  return <section className="module-page"><div className="module-hero"><span>{kicker}</span><h2>{title}</h2></div>{children}</section>
}

export function ResourceState({ loading, error, retry }: { loading: boolean; error: boolean; retry: () => void }) {
  if (loading) return <div className="module-empty" role="status">正在加载…</div>
  if (error) return <div className="module-empty" role="alert"><p>暂时无法加载该模块，请重试。</p><button className="secondary-button" onClick={retry}>重新加载</button></div>
  return null
}

export function UpstreamAction({ text, label, onClick }: { text: string; label: string; onClick: () => void }) {
  return <div className="module-empty"><p>{text}</p><button className="secondary-button" onClick={onClick}>{label}</button></div>
}

export function statusLabel(status: string) {
  return ({ draft:"草稿", scheduled:"已排期", published:"已发布", cancelled:"已取消", ready:"待排期" } as Record<string, string>)[status] ?? status
}
