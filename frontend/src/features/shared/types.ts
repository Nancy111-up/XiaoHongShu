export type Opportunity = {
  id: string
  topicId: string
  title: string
  currentHeat: number | null
  trendScore: number | null
  trendStage: string | null
  score: number | null
  decision: string
  goal: string | null
  eligibility: string
  risk: string
  confidence: string
  scores: Record<string, number | null>
  reasons: Record<string, string>
  sources: Array<{ url: string }>
  preview: null | {
    titles?: string[]
    body?: string
    angle?: string
    format?: string
    tags?: string[]
  }
  updatedAt: string
  data_source: "live" | "fixture" | "demo"
}

export type OpportunityResponse = {
  items: Opportunity[]
  data_source: "live" | "fixture" | "demo" | "unavailable"
}
