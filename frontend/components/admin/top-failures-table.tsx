"use client"

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import type { TopFailure } from "@/lib/admin-api"

interface TopFailuresTableProps {
  data: TopFailure[]
}

export function TopFailuresTable({ data }: TopFailuresTableProps) {
  return (
    <div className="bg-card border border-border rounded-xl p-4">
      <div className="flex items-center justify-between mb-3">
        <p className="text-sm font-semibold text-foreground">Top Failures</p>
        <p className="text-xs text-muted-foreground">{data.length} entries</p>
      </div>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-[360px]">Question</TableHead>
            <TableHead>Count</TableHead>
            <TableHead>Avg Retries</TableHead>
            <TableHead>Last Seen</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {data.length === 0 ? (
            <TableRow>
              <TableCell colSpan={4} className="text-center text-muted-foreground py-6">
                No failures recorded
              </TableCell>
            </TableRow>
          ) : (
            data.slice(0, 10).map((row, i) => (
              <TableRow key={i}>
                <TableCell className="max-w-[360px]">
                  <span
                    className="block truncate text-foreground text-xs"
                    title={row.question}
                  >
                    {row.question.length > 90
                      ? row.question.slice(0, 90) + "…"
                      : row.question}
                  </span>
                </TableCell>
                <TableCell>
                  <span className="inline-flex items-center justify-center w-7 h-7 rounded-full bg-red-500/15 text-red-400 text-xs font-bold">
                    {row.failure_count}
                  </span>
                </TableCell>
                <TableCell className="text-xs text-muted-foreground font-mono">
                  {typeof row.avg_retries === "number"
                    ? row.avg_retries.toFixed(1)
                    : "—"}
                </TableCell>
                <TableCell className="text-xs text-muted-foreground whitespace-nowrap">
                  {row.last_seen
                    ? new Date(row.last_seen).toLocaleDateString("en-GB", {
                        day: "2-digit",
                        month: "short",
                        year: "2-digit",
                      })
                    : "—"}
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
    </div>
  )
}
