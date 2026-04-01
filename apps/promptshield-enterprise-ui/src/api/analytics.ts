import { adminClient } from './client'

export interface SummaryStats {
  total_requests: number
  total_tokens: number
  total_cost_usd: number
  block_rate: number
  decision_counts: Record<string, number>
}

export interface UserStat {
  user_id: string
  request_count: number
  total_tokens: number
  total_cost_usd: number
  avg_misuse_score: number
  daily_request_limit: number | null
  daily_spend_limit_usd: number | null
}

export interface ModelStat {
  model: string
  request_count: number
  total_tokens: number
  total_cost_usd: number
}

export async function fetchSummary(): Promise<SummaryStats> {
  const { data } = await adminClient.get<SummaryStats>('/v1/analytics/summary')
  return data
}

export async function fetchUserStats(): Promise<UserStat[]> {
  const { data } = await adminClient.get<UserStat[]>('/v1/analytics/users')
  return data
}

export async function fetchModelStats(): Promise<ModelStat[]> {
  const { data } = await adminClient.get<ModelStat[]>('/v1/analytics/models')
  return data
}

export async function fetchMisuseReport(threshold = 0.5): Promise<UserStat[]> {
  const { data } = await adminClient.get<UserStat[]>(`/v1/analytics/misuse?threshold=${threshold}`)
  return data
}
