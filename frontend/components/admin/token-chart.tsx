"use client"

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts"
import type { TokenPoint } from "@/lib/admin-api"

interface TokenChartProps {
  data: TokenPoint[]
}

const axisStyle = {
  tick: { fill: "hsl(var(--muted-foreground))", fontSize: 11 },
  axisLine: { stroke: "hsl(var(--border))" },
  tickLine: false as const,
}

function formatTokens(v: number): string {
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`
  if (v >= 1_000) return `${(v / 1_000).toFixed(0)}K`
  return String(v)
}

const CustomTooltip = ({
  active,
  payload,
  label,
}: {
  active?: boolean
  payload?: Array<{ value: number; name: string; color: string }>
  label?: string
}) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-popover border border-border rounded-lg px-3 py-2 shadow-lg text-xs">
      <p className="text-muted-foreground mb-1">{label}</p>
      {payload.map((item, i) => (
        <p key={i} style={{ color: item.color }} className="font-medium">
          {item.name}: {formatTokens(item.value)}
        </p>
      ))}
    </div>
  )
}

export function TokenChart({ data }: TokenChartProps) {
  return (
    <div className="bg-card border border-border rounded-xl p-4">
      <p className="text-sm font-semibold text-foreground mb-3">Token Usage</p>
      <ResponsiveContainer width="100%" height={220}>
        <AreaChart data={data} margin={{ top: 4, right: 8, left: 8, bottom: 0 }}>
          <defs>
            <linearGradient id="inputGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="outputGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="cacheReadGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="cacheWriteGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.4} vertical={false} />
          <XAxis
            dataKey="day"
            {...axisStyle}
            tickFormatter={(v: string) => v.slice(5)}
          />
          <YAxis {...axisStyle} width={44} tickFormatter={formatTokens} />
          <Tooltip content={<CustomTooltip />} />
          <Legend
            wrapperStyle={{ fontSize: 11, paddingTop: 8 }}
            formatter={(value) => <span className="text-muted-foreground">{value}</span>}
          />
          <Area type="monotone" dataKey="input" name="Input" stroke="#3b82f6" strokeWidth={1.5} fill="url(#inputGrad)" stackId="1" />
          <Area type="monotone" dataKey="output" name="Output" stroke="#f59e0b" strokeWidth={1.5} fill="url(#outputGrad)" stackId="1" />
          <Area type="monotone" dataKey="cache_read" name="Cache Read" stroke="#10b981" strokeWidth={1.5} fill="url(#cacheReadGrad)" stackId="1" />
          <Area type="monotone" dataKey="cache_write" name="Cache Write" stroke="#8b5cf6" strokeWidth={1.5} fill="url(#cacheWriteGrad)" stackId="1" />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
