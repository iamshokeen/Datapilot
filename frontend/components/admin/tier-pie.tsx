"use client"

import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts"
import type { EchoTierPoint } from "@/lib/admin-api"

interface TierPieProps {
  data: EchoTierPoint[]
}

const TIER_COLORS: Record<string, string> = {
  "Tier 1": "#10b981",
  "Tier 2": "#f59e0b",
  "Tier 3": "#3b82f6",
}

const DEFAULT_COLORS = ["#10b981", "#f59e0b", "#3b82f6", "#8b5cf6"]

const CustomTooltip = ({
  active,
  payload,
}: {
  active?: boolean
  payload?: Array<{ name: string; value: number; payload: EchoTierPoint }>
}) => {
  if (!active || !payload?.length) return null
  const { name, value } = payload[0]
  return (
    <div className="bg-popover border border-border rounded-lg px-3 py-2 shadow-lg text-xs">
      <p className="text-muted-foreground">{name}</p>
      <p className="font-semibold text-foreground">{value} queries</p>
    </div>
  )
}

export function TierPie({ data }: TierPieProps) {
  return (
    <div className="bg-card border border-border rounded-xl p-4">
      <p className="text-sm font-semibold text-foreground mb-3">ECHO Tier Distribution</p>
      <ResponsiveContainer width="100%" height={220}>
        <PieChart margin={{ top: 0, right: 0, left: 0, bottom: 0 }}>
          <Pie
            data={data}
            cx="50%"
            cy="45%"
            outerRadius={70}
            innerRadius={38}
            dataKey="value"
            nameKey="name"
            paddingAngle={3}
          >
            {data.map((entry, i) => (
              <Cell
                key={i}
                fill={TIER_COLORS[entry.name] ?? DEFAULT_COLORS[i % DEFAULT_COLORS.length]}
              />
            ))}
          </Pie>
          <Tooltip content={<CustomTooltip />} />
          <Legend
            wrapperStyle={{ fontSize: 11, paddingTop: 4 }}
            formatter={(value) => <span className="text-muted-foreground">{value}</span>}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  )
}
