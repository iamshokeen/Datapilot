"use client"

import {
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts"
import type { VolumePoint } from "@/lib/admin-api"

interface VolumeChartProps {
  data: VolumePoint[]
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
          {item.name}: {item.value}
        </p>
      ))}
    </div>
  )
}

export function VolumeChart({ data }: VolumeChartProps) {
  return (
    <div className="bg-card border border-border rounded-xl p-4">
      <p className="text-sm font-semibold text-foreground mb-3">Query Volume</p>
      <ResponsiveContainer width="100%" height={220}>
        <ComposedChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.4} vertical={false} />
          <XAxis
            dataKey="day"
            {...axisStyle}
            tickFormatter={(v: string) => v.slice(5)}
          />
          <YAxis {...axisStyle} width={36} allowDecimals={false} />
          <Tooltip content={<CustomTooltip />} />
          <Legend
            wrapperStyle={{ fontSize: 11, paddingTop: 8 }}
            formatter={(value) => <span className="text-muted-foreground">{value}</span>}
          />
          <Bar dataKey="failed" name="Failed" fill="#ef4444" opacity={0.8} radius={[2, 2, 0, 0]} maxBarSize={20} />
          <Line
            type="monotone"
            dataKey="queries"
            name="Total"
            stroke="#f59e0b"
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4, fill: "#f59e0b" }}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}
