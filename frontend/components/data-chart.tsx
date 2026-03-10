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

// Chart colors matching the design tokens
const COLORS = [
  "hsl(45, 80%, 55%)",   // Primary amber/gold
  "hsl(200, 50%, 50%)",  // Teal
  "hsl(150, 50%, 55%)",  // Green
  "hsl(340, 55%, 55%)",  // Rose
  "hsl(280, 45%, 55%)",  // Purple
  "hsl(30, 70%, 55%)",   // Orange
]

const CustomTooltip = ({ active, payload, label }: {
  active?: boolean
  payload?: Array<{ value: number; name: string; color: string }>
  label?: string
}) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-popover border border-border rounded-lg px-3 py-2 shadow-lg">
        <p className="text-xs text-muted-foreground mb-1">{label}</p>
        {payload.map((item, index) => (
          <p key={index} className="text-sm font-medium text-foreground">
            {item.name}: {typeof item.value === "number" ? item.value.toLocaleString() : item.value}
          </p>
        ))}
      </div>
    )
  }
  return null
}

export function DataChart({ type, data, xAxis, yAxis }: DataChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground">
        No data available
      </div>
    )
  }

  const commonAxisProps = {
    tick: { fill: "hsl(var(--muted-foreground))", fontSize: 11 },
    axisLine: { stroke: "hsl(var(--border))" },
    tickLine: { stroke: "hsl(var(--border))" },
  }

  if (type === "bar") {
    return (
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 20, right: 20, left: 20, bottom: 60 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.5} />
          <XAxis
            dataKey={xAxis}
            {...commonAxisProps}
            angle={-45}
            textAnchor="end"
            height={80}
            interval={0}
          />
          <YAxis {...commonAxisProps} tickFormatter={(value) => formatNumber(value)} />
          <Tooltip content={<CustomTooltip />} />
          <Bar dataKey={yAxis} radius={[4, 4, 0, 0]}>
            {data.map((_, index) => (
              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    )
  }

  if (type === "line") {
    return (
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 20, right: 20, left: 20, bottom: 20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.5} />
          <XAxis dataKey={xAxis} {...commonAxisProps} />
          <YAxis {...commonAxisProps} tickFormatter={(value) => formatNumber(value)} />
          <Tooltip content={<CustomTooltip />} />
          <Line
            type="monotone"
            dataKey={yAxis}
            stroke={COLORS[0]}
            strokeWidth={2}
            dot={{ fill: COLORS[0], strokeWidth: 0, r: 4 }}
            activeDot={{ r: 6, fill: COLORS[0] }}
          />
        </LineChart>
      </ResponsiveContainer>
    )
  }

  if (type === "pie") {
    return (
      <ResponsiveContainer width="100%" height="100%">
        <PieChart margin={{ top: 20, right: 20, left: 20, bottom: 20 }}>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            labelLine={false}
            label={({ name, percent }: { name: string; percent: number }) =>
              `${name} (${(percent * 100).toFixed(0)}%)`
            }
            outerRadius={100}
            innerRadius={40}
            dataKey={yAxis}
            nameKey={xAxis}
            paddingAngle={2}
          >
            {data.map((_, index) => (
              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip content={<CustomTooltip />} />
          <Legend
            formatter={(value) => <span className="text-foreground text-sm">{value}</span>}
          />
        </PieChart>
      </ResponsiveContainer>
    )
  }

  if (type === "scatter") {
    return (
      <ResponsiveContainer width="100%" height="100%">
        <ScatterChart margin={{ top: 20, right: 20, left: 20, bottom: 20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.5} />
          <XAxis dataKey={xAxis} {...commonAxisProps} name={xAxis} />
          <YAxis dataKey={yAxis} {...commonAxisProps} name={yAxis} />
          <Tooltip content={<CustomTooltip />} cursor={{ strokeDasharray: "3 3" }} />
          <Scatter name="Data" data={data} fill={COLORS[0]}>
            {data.map((_, index) => (
              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
            ))}
          </Scatter>
        </ScatterChart>
      </ResponsiveContainer>
    )
  }

  // Fallback for table type - render a simple bar chart
  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={data} margin={{ top: 20, right: 20, left: 20, bottom: 60 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.5} />
        <XAxis
          dataKey={xAxis}
          {...commonAxisProps}
          angle={-45}
          textAnchor="end"
          height={80}
          interval={0}
        />
        <YAxis {...commonAxisProps} tickFormatter={(value) => formatNumber(value)} />
        <Tooltip content={<CustomTooltip />} />
        <Bar dataKey={yAxis} radius={[4, 4, 0, 0]}>
          {data.map((_, index) => (
            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

function formatNumber(value: number): string {
  if (value >= 1000000) return `${(value / 1000000).toFixed(1)}M`
  if (value >= 1000) return `${(value / 1000).toFixed(0)}K`
  return value.toString()
}
