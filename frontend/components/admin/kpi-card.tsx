"use client"

import { Card, CardContent } from "@/components/ui/card"
import { cn } from "@/lib/utils"

interface KpiCardProps {
  label: string
  value: string | number
  unit?: string
  sublabel?: string
  highlight?: boolean
}

export function KpiCard({ label, value, unit, sublabel, highlight }: KpiCardProps) {
  return (
    <Card className={cn("py-4 gap-2", highlight && "border-amber-500/40")}>
      <CardContent className="px-4">
        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-1">
          {label}
        </p>
        <div className="flex items-baseline gap-1">
          <span
            className={cn(
              "text-2xl font-bold tracking-tight",
              highlight ? "text-amber-400" : "text-foreground"
            )}
          >
            {value}
          </span>
          {unit && (
            <span className="text-sm text-muted-foreground font-medium">{unit}</span>
          )}
        </div>
        {sublabel && (
          <p className="text-xs text-muted-foreground mt-1">{sublabel}</p>
        )}
      </CardContent>
    </Card>
  )
}
