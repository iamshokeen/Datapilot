const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080"

export interface AdminStats {
  total_queries: number
  success_rate_pct: number
  avg_cost_usd: number
  total_cost_usd: number
  avg_response_time_ms: number
  echo_hit_rate_pct: number
  retry_rate_pct: number
  few_shot_rate_pct: number
  total_tokens: number
  total_input_tokens: number
  total_output_tokens: number
  total_cache_read_tokens: number
  total_cache_write_tokens: number
  thumbs_up: number
  thumbs_down: number
  verified_count: number
  avg_retries: number
  lore_entry_count: number
}

export interface VolumePoint {
  day: string
  queries: number
  successful: number
  failed: number
}

export interface CostPoint {
  day: string
  total_cost: number
  avg_cost: number
}

export interface TokenPoint {
  day: string
  input: number
  output: number
  cache_read: number
  cache_write: number
}

export interface EchoTierPoint {
  name: string
  value: number
}

export interface ResponseTimePoint {
  day: string
  avg_ms: number
  p95_ms: number
}

export interface QueryRow {
  id: number
  question: string
  echo_tier: number
  cost_usd: number
  total_tokens: number
  retry_count: number
  few_shot_used: boolean
  was_successful: boolean
  execution_time_ms: number
  feedback: string | null
  verified: boolean | null
  created_at: string
}

export interface TopFailure {
  question: string
  failure_count: number
  last_seen: string
  avg_retries: number
}

async function apiFetch<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`)
  if (!response.ok) {
    const err = await response.json().catch(() => ({}))
    throw new Error((err as { detail?: string }).detail || `Request failed (${response.status})`)
  }
  return response.json() as Promise<T>
}

export async function fetchAdminStats(days = 30): Promise<AdminStats> {
  return apiFetch<AdminStats>(`/admin/stats?days=${days}`)
}

export async function fetchVolumeChart(days = 30): Promise<VolumePoint[]> {
  return apiFetch<VolumePoint[]>(`/admin/chart/volume?days=${days}`)
}

export async function fetchCostChart(days = 30): Promise<CostPoint[]> {
  return apiFetch<CostPoint[]>(`/admin/chart/cost?days=${days}`)
}

export async function fetchTokenChart(days = 30): Promise<TokenPoint[]> {
  return apiFetch<TokenPoint[]>(`/admin/chart/tokens?days=${days}`)
}

export async function fetchEchoTiers(days = 30): Promise<EchoTierPoint[]> {
  return apiFetch<EchoTierPoint[]>(`/admin/chart/echo-tiers?days=${days}`)
}

export async function fetchResponseTimeChart(days = 30): Promise<ResponseTimePoint[]> {
  return apiFetch<ResponseTimePoint[]>(`/admin/chart/response-time?days=${days}`)
}

export async function fetchRecentQueries(
  days = 30,
  limit = 50,
  offset = 0
): Promise<{ rows: QueryRow[]; total: number }> {
  return apiFetch<{ rows: QueryRow[]; total: number }>(
    `/admin/queries?days=${days}&limit=${limit}&offset=${offset}`
  )
}

export async function fetchTopFailures(): Promise<TopFailure[]> {
  return apiFetch<TopFailure[]>(`/admin/top-failures`)
}

export async function fetchLore(): Promise<{ entries: unknown[] }> {
  return apiFetch<{ entries: unknown[] }>(`/admin/lore`)
}
