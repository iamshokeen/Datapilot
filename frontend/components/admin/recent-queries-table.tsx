"use client"

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { cn } from "@/lib/utils"
import type { QueryRow } from "@/lib/admin-api"

interface RecentQueriesTableProps {
  rows: QueryRow[]
  total: number
  offset: number
  onPageChange: (offset: number) => void
}

const PAGE_SIZE = 50

function TierBadge({ tier }: { tier: number }) {
  const styles: Record<number, string> = {
    1: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
    2: "bg-amber-500/15 text-amber-400 border-amber-500/30",
    3: "bg-blue-500/15 text-blue-400 border-blue-500/30",
  }
  const labels: Record<number, string> = { 1: "T1", 2: "T2", 3: "T3" }
  const cls = styles[tier] ?? "bg-muted/30 text-muted-foreground border-border"
  return (
    <span
      className={cn(
        "inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold border",
        cls
      )}
    >
      {labels[tier] ?? `T${tier}`}
    </span>
  )
}

function FeedbackCell({ feedback }: { feedback: string | null }) {
  if (feedback === "up") return <span title="Thumbs up">👍</span>
  if (feedback === "down") return <span title="Thumbs down">👎</span>
  return <span className="text-muted-foreground">—</span>
}

export function RecentQueriesTable({
  rows,
  total,
  offset,
  onPageChange,
}: RecentQueriesTableProps) {
  const page = Math.floor(offset / PAGE_SIZE) + 1
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  return (
    <div className="bg-card border border-border rounded-xl p-4">
      <div className="flex items-center justify-between mb-3">
        <p className="text-sm font-semibold text-foreground">Recent Queries</p>
        <p className="text-xs text-muted-foreground">{total} total</p>
      </div>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-[280px]">Question</TableHead>
            <TableHead>Tier</TableHead>
            <TableHead>Cost</TableHead>
            <TableHead>Tokens</TableHead>
            <TableHead>Retries</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Time</TableHead>
            <TableHead>Feedback</TableHead>
            <TableHead>Date</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.length === 0 ? (
            <TableRow>
              <TableCell colSpan={9} className="text-center text-muted-foreground py-8">
                No queries found
              </TableCell>
            </TableRow>
          ) : (
            rows.map((row) => (
              <TableRow key={row.id}>
                <TableCell className="max-w-[280px]">
                  <span
                    className="block truncate text-foreground text-xs"
                    title={row.question}
                  >
                    {row.question.length > 80
                      ? row.question.slice(0, 80) + "…"
                      : row.question}
                  </span>
                </TableCell>
                <TableCell>
                  <TierBadge tier={row.echo_tier} />
                </TableCell>
                <TableCell className="text-xs text-muted-foreground font-mono">
                  ${(row.cost_usd ?? 0).toFixed(5)}
                </TableCell>
                <TableCell className="text-xs text-muted-foreground font-mono">
                  {(row.total_tokens ?? 0).toLocaleString()}
                </TableCell>
                <TableCell className="text-xs text-center text-muted-foreground">
                  {row.retry_count ?? 0}
                </TableCell>
                <TableCell>
                  {row.was_successful ? (
                    <span className="text-emerald-400 text-sm font-bold">✓</span>
                  ) : (
                    <span className="text-red-400 text-sm font-bold">✗</span>
                  )}
                </TableCell>
                <TableCell className="text-xs text-muted-foreground font-mono">
                  {row.execution_time_ms != null ? `${row.execution_time_ms}ms` : "—"}
                </TableCell>
                <TableCell>
                  <FeedbackCell feedback={row.feedback} />
                </TableCell>
                <TableCell className="text-xs text-muted-foreground whitespace-nowrap">
                  {new Date(row.created_at).toLocaleDateString("en-GB", {
                    day: "2-digit",
                    month: "short",
                  })}
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>

      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-3 pt-3 border-t border-border">
          <p className="text-xs text-muted-foreground">
            Page {page} of {totalPages}
          </p>
          <div className="flex gap-2">
            <button
              onClick={() => onPageChange(Math.max(0, offset - PAGE_SIZE))}
              disabled={offset === 0}
              className="px-3 py-1 text-xs bg-muted/40 hover:bg-muted/70 disabled:opacity-40 disabled:cursor-not-allowed rounded-md transition-colors text-foreground"
            >
              Prev
            </button>
            <button
              onClick={() => onPageChange(offset + PAGE_SIZE)}
              disabled={offset + PAGE_SIZE >= total}
              className="px-3 py-1 text-xs bg-muted/40 hover:bg-muted/70 disabled:opacity-40 disabled:cursor-not-allowed rounded-md transition-colors text-foreground"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
