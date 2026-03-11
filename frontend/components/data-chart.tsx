"use client"

import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  Legend,
} from "recharts"

interface DataChartProps {
  type: "bar" | "line" | "pie" | "scatter" | "table"
  data: Record<string, unknown>[]
  xAxis: string
  yAxis: string
}

const COLORS = [
  "#f59e0b", "#3b82f6", "#10b981", "#f43f5e",
  "#8b5cf6", "#f97316", "#06b6d4", "#84cc16",
]

function formatNumber(value: number): string {
  if (value >= 10_000_000) return `₹${(value / 10_000_000).toFixed(1)}Cr`
  if (value >= 100_000) return `₹${(value / 100_000).toFixed(1)}L`
  if (value >= 1_000) return `${(value / 1_000).toFixed(0)}K`
  return String(value)
}

function truncateLabel(str: string, max = 12): string {
  if (!str) return ""
  return str.length > max ? str.slice(0, max) + "…" : str
}

const CustomTooltip = ({
  active,
  payload,
  label,
}: {
  active?: boolean
  payload?: Array<{ value: number; name: string }>
  label?: string
}) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-popover border border-border rounded-lg px-3 py-2 shadow-lg max-w-[200px]">
      <p className="text-xs text-muted-foreground mb-1 break-words">{label}</p>
      {payload.map((item, i) => (
        <p key={i} className="text-sm font-semibold text-foreground">
          {typeof item.value === "number" ? item.value.toLocaleString("en-IN") : item.value}
        </p>
      ))}
    </div>
  )
}

const axisStyle = {
  tick: { fill: "hsl(var(--muted-foreground))", fontSize: 11 },
  axisLine: { stroke: "hsl(var(--border))" },
  tickLine: false as const,
}

export function DataChart({ type, data, xAxis, yAxis }: DataChartProps) {
  if (!data || data.length === 0 || !xAxis || !yAxis) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
        No chart data available
      </div>
    )
  }

  if (type === "bar") {
    return (
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 10, right: 20, left: 10, bottom: 60 }} barCategoryGap="35%">
          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.4} vertical={false} />
          <XAxis
            dataKey={xAxis}
            {...axisStyle}
            angle={-35}
            textAnchor="end"
            height={70}
            interval={0}
            tickFormatter={(v) => truncateLabel(String(v))}
          />
          <YAxis {...axisStyle} tickFormatter={formatNumber} width={60} />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: "hsl(var(--accent))", opacity: 0.5 }} />
          <Bar dataKey={yAxis} radius={[4, 4, 0, 0]} maxBarSize={48}>
            {data.map((_, i) => (
              <Cell key={i} fill={COLORS[i % COLORS.length]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    )
  }

  if (type === "line") {
    return (
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 10, right: 20, left: 10, bottom: 20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.4} vertical={false} />
          <XAxis dataKey={xAxis} {...axisStyle} tickFormatter={(v) => truncateLabel(String(v), 8)} />
          <YAxis {...axisStyle} tickFormatter={formatNumber} width={60} />
          <Tooltip content={<CustomTooltip />} />
          <Line
            type="monotone"
            dataKey={yAxis}
            stroke={COLORS[0]}
            strokeWidth={2.5}
            dot={{ fill: COLORS[0], r: 4, strokeWidth: 0 }}
            activeDot={{ r: 6, fill: COLORS[0] }}
          />
        </LineChart>
      </ResponsiveContainer>
    )
  }

  if (type === "pie") {
    return (
      <ResponsiveContainer width="100%" height="100%">
        <PieChart margin={{ top: 10, right: 20, left: 20, bottom: 10 }}>
          <Pie
            data={data}
            cx="50%"
            cy="45%"
            outerRadius="65%"
            innerRadius="30%"
            dataKey={yAxis}
            nameKey={xAxis}
            paddingAngle={2}
            label={({ name, percent }) =>
              percent > 0.05 ? `${truncateLabel(String(name), 10)} ${(percent * 100).toFixed(0)}%` : ""
            }
            labelLine={{ stroke: "hsl(var(--muted-foreground))", strokeWidth: 1 }}
          >
            {data.map((_, i) => (
              <Cell key={i} fill={COLORS[i % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip content={<CustomTooltip />} />
          <Legend
            formatter={(value) => (
              <span className="text-foreground text-xs">{truncateLabel(String(value), 16)}</span>
            )}
          />
        </PieChart>
      </ResponsiveContainer>
    )
  }

  if (type === "scatter") {
    return (
      <ResponsiveContainer width="100%" height="100%">
        <ScatterChart margin={{ top: 10, right: 20, left: 10, bottom: 20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.4} />
          <XAxis dataKey={xAxis} {...axisStyle} name={xAxis} tickFormatter={formatNumber} width={60} />
          <YAxis dataKey={yAxis} {...axisStyle} name={yAxis} tickFormatter={formatNumber} width={60} />
          <Tooltip content={<CustomTooltip />} cursor={{ strokeDasharray: "3 3" }} />
          <Scatter data={data} fill={COLORS[0]} />
        </ScatterChart>
      </ResponsiveContainer>
    )
  }

  // Fallback: bar chart
  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={data} margin={{ top: 10, right: 20, left: 10, bottom: 60 }} barCategoryGap="35%">
        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.4} vertical={false} />
        <XAxis
          dataKey={xAxis}
          {...axisStyle}
          angle={-35}
          textAnchor="end"
          height={70}
          interval={0}
          tickFormatter={(v) => truncateLabel(String(v))}
        />
        <YAxis {...axisStyle} tickFormatter={formatNumber} width={60} />
        <Tooltip content={<CustomTooltip />} cursor={{ fill: "hsl(var(--accent))", opacity: 0.5 }} />
        <Bar dataKey={yAxis} radius={[4, 4, 0, 0]} maxBarSize={48}>
          {data.map((_, i) => (
            <Cell key={i} fill={COLORS[i % COLORS.length]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
