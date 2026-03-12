"use client"

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts"
import type { ResponseTimePoint } from "@/lib/admin-api"

interface ResponseTimeChartProps {
  data: ResponseTimePoint[]
}

const axisStyle = {
  tick: { fill: "hsl(var(--muted-foreground))", fontSize: 11 },
  axisLine: { stroke: "hsl(var(--border))" },
  tickLine: false as const,
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
          {item.name}: {item.value.toFixed(0)}ms
        </p>
      ))}
    </div>
  )
}

export function ResponseTimeChart({ data }: ResponseTimeChartProps) {
  return (
    <div className="bg-card border border-border rounded-xl p-4">
      <p className="text-sm font-semibold text-foreground mb-3">Response Time (ms)</p>
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.4} vertical={false} />
          <XAxis
            dataKey="day"
            {...axisStyle}
            tickFormatter={(v: string) => v.slice(5)}
          />
          <YAxis {...axisStyle} width={50} tickFormatter={(v: number) => `${v}ms`} />
          <Tooltip content={<CustomTooltip />} />
          <Legend
            wrapperStyle={{ fontSize: 11, paddingTop: 8 }}
            formatter={(value) => <span className="text-muted-foreground">{value}</span>}
          />
          <Line
            type="monotone"
            dataKey="avg_ms"
            name="Avg"
            stroke="#f59e0b"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4, fill: "#f59e0b" }}
          />
          <Line
            type="monotone"
            dataKey="p95_ms"
            name="P95"
            stroke="#ef4444"
            strokeWidth={2}
            strokeDasharray="5 3"
            dot={false}
            activeDot={{ r: 4, fill: "#ef4444" }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
