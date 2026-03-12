"use client"

import { useState, useEffect, useCallback } from "react"
import { RefreshCw, BarChart3 } from "lucide-react"
import { KpiCard } from "@/components/admin/kpi-card"
import { VolumeChart } from "@/components/admin/volume-chart"
import { TierPie } from "@/components/admin/tier-pie"
import { CostChart } from "@/components/admin/cost-chart"
import { TokenChart } from "@/components/admin/token-chart"
import { ResponseTimeChart } from "@/components/admin/response-time-chart"
import { RecentQueriesTable } from "@/components/admin/recent-queries-table"
import { TopFailuresTable } from "@/components/admin/top-failures-table"
import {
  fetchAdminStats,
  fetchVolumeChart,
  fetchCostChart,
  fetchTokenChart,
  fetchEchoTiers,
  fetchResponseTimeChart,
  fetchRecentQueries,
  fetchTopFailures,
  type AdminStats,
  type VolumePoint,
  type CostPoint,
  type TokenPoint,
  type EchoTierPoint,
  type ResponseTimePoint,
  type QueryRow,
  type TopFailure,
} from "@/lib/admin-api"
import { cn } from "@/lib/utils"

type Days = 7 | 30 | 90

interface DashboardData {
  stats: AdminStats | null
  volume: VolumePoint[]
  cost: CostPoint[]
  tokens: TokenPoint[]
  echoTiers: EchoTierPoint[]
  responseTime: ResponseTimePoint[]
  queries: QueryRow[]
  queriesTotal: number
  failures: TopFailure[]
}

const EMPTY_DATA: DashboardData = {
  stats: null,
  volume: [],
  cost: [],
  tokens: [],
  echoTiers: [],
  responseTime: [],
  queries: [],
  queriesTotal: 0,
  failures: [],
}

export default function AdminPage() {
  const [days, setDays] = useState<Days>(30)
  const [queriesOffset, setQueriesOffset] = useState(0)
  const [data, setData] = useState<DashboardData>(EMPTY_DATA)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [refreshing, setRefreshing] = useState(false)

  const loadData = useCallback(
    async (selectedDays: Days, offset: number) => {
      try {
        const [
          stats,
          volume,
          cost,
          tokens,
          echoTiers,
          responseTime,
          queriesResult,
          failures,
        ] = await Promise.all([
          fetchAdminStats(selectedDays),
          fetchVolumeChart(selectedDays),
          fetchCostChart(selectedDays),
          fetchTokenChart(selectedDays),
          fetchEchoTiers(selectedDays),
          fetchResponseTimeChart(selectedDays),
          fetchRecentQueries(selectedDays, 50, offset),
          fetchTopFailures(),
        ])
        setData({
          stats,
          volume,
          cost,
          tokens,
          echoTiers,
          responseTime,
          queries: queriesResult.rows,
          queriesTotal: queriesResult.total,
          failures,
        })
        setError(null)
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load admin data")
      }
    },
    []
  )

  useEffect(() => {
    setLoading(true)
    setQueriesOffset(0)
    loadData(days, 0).finally(() => setLoading(false))
  }, [days, loadData])

  const handlePageChange = useCallback(
    (offset: number) => {
      setQueriesOffset(offset)
      loadData(days, offset)
    },
    [days, loadData]
  )

  const handleRefresh = useCallback(async () => {
    setRefreshing(true)
    await loadData(days, queriesOffset)
    setRefreshing(false)
  }, [days, queriesOffset, loadData])

  const { stats } = data

  function fmt(n: number | undefined | null, decimals = 0): string {
    if (n == null) return "—"
    return decimals > 0 ? n.toFixed(decimals) : n.toLocaleString()
  }

  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* Header */}
      <div className="border-b border-border bg-card sticky top-0 z-10">
        <div className="max-w-[1400px] mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-7 h-7 rounded-lg bg-primary/10 flex items-center justify-center">
              <BarChart3 className="w-4 h-4 text-primary" />
            </div>
            <h1 className="text-sm font-semibold tracking-tight">DataPilot Admin</h1>
          </div>

          <div className="flex items-center gap-3">
            {/* Day selector */}
            <div className="flex items-center bg-muted/40 rounded-lg p-0.5 border border-border">
              {([7, 30, 90] as Days[]).map((d) => (
                <button
                  key={d}
                  onClick={() => setDays(d)}
                  className={cn(
                    "px-3 py-1 text-xs font-medium rounded-md transition-colors",
                    days === d
                      ? "bg-primary text-primary-foreground"
                      : "text-muted-foreground hover:text-foreground"
                  )}
                >
                  {d}d
                </button>
              ))}
            </div>

            {/* Refresh */}
            <button
              onClick={handleRefresh}
              disabled={refreshing || loading}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-muted/40 hover:bg-muted/70 border border-border rounded-lg transition-colors text-muted-foreground hover:text-foreground disabled:opacity-50"
            >
              <RefreshCw className={cn("w-3.5 h-3.5", refreshing && "animate-spin")} />
              Refresh
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-[1400px] mx-auto px-6 py-6 space-y-6">
        {/* Error banner */}
        {error && (
          <div className="bg-destructive/10 border border-destructive/30 text-destructive rounded-xl px-4 py-3 text-sm">
            {error}
          </div>
        )}

        {loading ? (
          <div className="flex items-center justify-center py-24">
            <div className="flex flex-col items-center gap-3">
              <RefreshCw className="w-6 h-6 text-muted-foreground animate-spin" />
              <p className="text-sm text-muted-foreground">Loading dashboard…</p>
            </div>
          </div>
        ) : (
          <>
            {/* Section 1 — KPI Grid */}
            <section>
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 mb-3">
                <KpiCard
                  label="Total Queries"
                  value={fmt(stats?.total_queries)}
                />
                <KpiCard
                  label="Success Rate"
                  value={fmt(stats?.success_rate_pct, 1)}
                  unit="%"
                  highlight={
                    stats?.success_rate_pct != null && stats.success_rate_pct < 80
                  }
                />
                <KpiCard
                  label="Avg Cost"
                  value={stats?.avg_cost_usd != null ? `$${stats.avg_cost_usd.toFixed(4)}` : "—"}
                  sublabel="per query"
                />
                <KpiCard
                  label="Total Cost"
                  value={stats?.total_cost_usd != null ? `$${stats.total_cost_usd.toFixed(3)}` : "—"}
                  sublabel={`last ${days} days`}
                />
                <KpiCard
                  label="Avg Response"
                  value={fmt(stats?.avg_response_time_ms, 0)}
                  unit="ms"
                />
                <KpiCard
                  label="ECHO Hit Rate"
                  value={fmt(stats?.echo_hit_rate_pct, 1)}
                  unit="%"
                  sublabel="cache hits"
                />
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <KpiCard
                  label="Retry Rate"
                  value={fmt(stats?.retry_rate_pct, 1)}
                  unit="%"
                  highlight={
                    stats?.retry_rate_pct != null && stats.retry_rate_pct > 20
                  }
                />
                <KpiCard
                  label="Few-shot Rate"
                  value={fmt(stats?.few_shot_rate_pct, 1)}
                  unit="%"
                />
                <KpiCard
                  label="Total Tokens"
                  value={
                    stats?.total_tokens != null
                      ? stats.total_tokens >= 1_000_000
                        ? `${(stats.total_tokens / 1_000_000).toFixed(2)}M`
                        : `${(stats.total_tokens / 1_000).toFixed(1)}K`
                      : "—"
                  }
                />
                <KpiCard
                  label="LORE Entries"
                  value={fmt(stats?.lore_entry_count)}
                  sublabel="business rules"
                />
              </div>
            </section>

            {/* Section 2 — Charts Row */}
            <section className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <VolumeChart data={data.volume} />
              <TierPie data={data.echoTiers} />
              <CostChart data={data.cost} />
            </section>

            {/* Section 3 — Token Chart Full Width */}
            <section>
              <TokenChart data={data.tokens} />
            </section>

            {/* Section 4 — Response Time + Feedback Stats */}
            <section className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <ResponseTimeChart data={data.responseTime} />

              <div className="bg-card border border-border rounded-xl p-4">
                <p className="text-sm font-semibold text-foreground mb-4">Feedback Overview</p>
                <div className="flex flex-col gap-3">
                  <div className="flex items-center justify-between p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
                    <div className="flex items-center gap-2">
                      <span className="text-lg">👍</span>
                      <span className="text-sm text-foreground font-medium">Thumbs Up</span>
                    </div>
                    <span className="text-xl font-bold text-emerald-400">
                      {fmt(stats?.thumbs_up)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between p-3 rounded-lg bg-red-500/10 border border-red-500/20">
                    <div className="flex items-center gap-2">
                      <span className="text-lg">👎</span>
                      <span className="text-sm text-foreground font-medium">Thumbs Down</span>
                    </div>
                    <span className="text-xl font-bold text-red-400">
                      {fmt(stats?.thumbs_down)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between p-3 rounded-lg bg-blue-500/10 border border-blue-500/20">
                    <div className="flex items-center gap-2">
                      <span className="text-lg">✓</span>
                      <span className="text-sm text-foreground font-medium">Verified Queries</span>
                    </div>
                    <span className="text-xl font-bold text-blue-400">
                      {fmt(stats?.verified_count)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between p-3 rounded-lg bg-muted/30 border border-border">
                    <span className="text-sm text-muted-foreground">Avg Retries / Query</span>
                    <span className="text-lg font-bold text-foreground">
                      {fmt(stats?.avg_retries, 2)}
                    </span>
                  </div>
                </div>
              </div>
            </section>

            {/* Section 5 — Recent Queries Table */}
            <section>
              <RecentQueriesTable
                rows={data.queries}
                total={data.queriesTotal}
                offset={queriesOffset}
                onPageChange={handlePageChange}
              />
            </section>

            {/* Section 6 — Top Failures */}
            <section>
              <TopFailuresTable data={data.failures} />
            </section>
          </>
        )}
      </div>
    </div>
  )
}
