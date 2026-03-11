"use client"

import { useState } from "react"
import {
  BarChart3,
  LineChart as LineChartIcon,
  PieChart as PieChartIcon,
  Table2,
  Code2,
  ChevronDown,
  ChevronUp,
  Clock,
  Rows3,
  Zap,
  ThumbsUp,
  ThumbsDown,
  Zap as EchoIcon,
} from "lucide-react"
import { DataChart } from "@/components/data-chart"
import { DataTable } from "@/components/data-table"
import { SQLDisplay } from "@/components/sql-display"
import { submitFeedback } from "@/lib/api"
import { cn } from "@/lib/utils"
import type { QueryResponse } from "@/lib/types"

interface QueryResultProps {
  response: QueryResponse
  sessionId?: string
  turnNumber?: number
}

const chartIcons = {
  bar: BarChart3,
  line: LineChartIcon,
  pie: PieChartIcon,
  scatter: BarChart3,
  table: Table2,
}

export function QueryResult({ response, sessionId, turnNumber = 0 }: QueryResultProps) {
  const [showSQL, setShowSQL] = useState(false)
  const [showDecomposition, setShowDecomposition] = useState(false)
  const [feedback, setFeedback] = useState<"up" | "down" | null>(null)
  const [feedbackLoading, setFeedbackLoading] = useState(false)

  const ChartIcon = chartIcons[response.chart_suggestion?.type] || BarChart3
  const isEchoHit = response.echo_tier === 1 || response.echo_tier === 2

  const handleFeedback = async (verdict: "up" | "down") => {
    if (!sessionId || feedback || feedbackLoading) return
    setFeedbackLoading(true)
    try {
      await submitFeedback({ session_id: sessionId, turn_number: turnNumber, verdict })
      setFeedback(verdict)
    } catch {
      // best-effort
    } finally {
      setFeedbackLoading(false)
    }
  }

  return (
    <div className="p-6 lg:p-8 max-w-6xl mx-auto">

      {/* ECHO badge */}
      {isEchoHit && (
        <div className="flex items-center gap-2 mb-4">
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-amber-500/10 border border-amber-500/20 text-xs font-medium text-amber-500">
            <EchoIcon className="w-3 h-3" />
            ECHO {response.echo_tier === 1 ? "exact match" : "modified"}
            {response.echo_similarity && (
              <span className="text-amber-500/70 ml-1">
                {(response.echo_similarity * 100).toFixed(0)}% similar
              </span>
            )}
          </div>
        </div>
      )}

      {/* Narrative Insight */}
      <div className="bg-card border border-border rounded-xl p-6 mb-4">
        <div className="flex items-start gap-4">
          <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
            <Zap className="w-5 h-5 text-primary" />
          </div>
          <div className="flex-1">
            <h3 className="text-sm font-medium text-primary uppercase tracking-wider mb-2">
              AI Insight
            </h3>
            <p className="text-foreground leading-relaxed">{response.narrative}</p>
          </div>
        </div>

        {/* Feedback buttons */}
        {sessionId && (
          <div className="flex items-center gap-2 mt-4 pt-4 border-t border-border/50">
            <span className="text-xs text-muted-foreground mr-1">Was this helpful?</span>
            <button
              onClick={() => handleFeedback("up")}
              disabled={!!feedback || feedbackLoading}
              className={cn(
                "flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all",
                feedback === "up"
                  ? "bg-green-500/20 text-green-500 border border-green-500/30"
                  : "text-muted-foreground hover:text-green-500 hover:bg-green-500/10 border border-transparent"
              )}
            >
              <ThumbsUp className="w-3.5 h-3.5" />
              {feedback === "up" ? "Marked helpful" : "Yes"}
            </button>
            <button
              onClick={() => handleFeedback("down")}
              disabled={!!feedback || feedbackLoading}
              className={cn(
                "flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all",
                feedback === "down"
                  ? "bg-red-500/20 text-red-500 border border-red-500/30"
                  : "text-muted-foreground hover:text-red-500 hover:bg-red-500/10 border border-transparent"
              )}
            >
              <ThumbsDown className="w-3.5 h-3.5" />
              {feedback === "down" ? "Marked unhelpful" : "No"}
            </button>
          </div>
        )}
      </div>

      {/* Chart */}
      {response.chart_suggestion?.type && response.chart_suggestion.type !== "table" && response.data?.length > 0 && (
        <div className="bg-card border border-border rounded-xl p-6 mb-4">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center">
                <ChartIcon className="w-4 h-4 text-primary" />
              </div>
              <div>
                <h3 className="text-sm font-medium text-foreground">Data Visualization</h3>
                <p className="text-xs text-muted-foreground mt-0.5">
                  {response.chart_suggestion.reason}
                </p>
              </div>
            </div>
            <span className="text-xs text-muted-foreground px-2 py-1 rounded-md bg-secondary capitalize">
              {response.chart_suggestion.type} chart
            </span>
          </div>
          <div className="h-72">
            <DataChart
              type={response.chart_suggestion.type}
              data={response.data}
              xAxis={response.chart_suggestion.x_axis}
              yAxis={response.chart_suggestion.y_axis}
            />
          </div>
        </div>
      )}

      {/* Data Table */}
      <div className="bg-card border border-border rounded-xl p-6 mb-4">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center">
            <Table2 className="w-4 h-4 text-primary" />
          </div>
          <div>
            <h3 className="text-sm font-medium text-foreground">Result Data</h3>
            <p className="text-xs text-muted-foreground mt-0.5">{response.total_rows} rows</p>
          </div>
        </div>
        <DataTable data={response.data} />
      </div>

      {/* Query Decomposition */}
      {response.sub_questions?.length > 1 && (
        <div className="bg-card border border-border rounded-xl mb-4 overflow-hidden">
          <button
            onClick={() => setShowDecomposition(!showDecomposition)}
            className="w-full flex items-center justify-between p-4 hover:bg-accent/50 transition-colors"
          >
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-secondary flex items-center justify-center">
                <span className="text-sm font-medium text-foreground">{response.sub_questions.length}</span>
              </div>
              <span className="text-sm font-medium text-foreground">Query Decomposition</span>
            </div>
            {showDecomposition ? <ChevronUp className="w-4 h-4 text-muted-foreground" /> : <ChevronDown className="w-4 h-4 text-muted-foreground" />}
          </button>
          {showDecomposition && (
            <div className="px-4 pb-4">
              <ul className="flex flex-col gap-2">
                {response.sub_questions.map((sq, index) => (
                  <li key={index} className="flex items-start gap-3 p-3 rounded-lg bg-secondary/50">
                    <span className="w-6 h-6 rounded-full bg-primary/20 flex items-center justify-center flex-shrink-0 text-xs font-medium text-primary">
                      {index + 1}
                    </span>
                    <span className="text-sm text-foreground">{sq}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* SQL Display */}
      <div className="bg-card border border-border rounded-xl overflow-hidden mb-4">
        <button
          onClick={() => setShowSQL(!showSQL)}
          className="w-full flex items-center justify-between p-4 hover:bg-accent/50 transition-colors"
        >
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-secondary flex items-center justify-center">
              <Code2 className="w-4 h-4 text-muted-foreground" />
            </div>
            <span className="text-sm font-medium text-foreground">Generated SQL</span>
          </div>
          {showSQL ? <ChevronUp className="w-4 h-4 text-muted-foreground" /> : <ChevronDown className="w-4 h-4 text-muted-foreground" />}
        </button>
        {showSQL && (
          <div className="px-4 pb-4">
            {response.results?.map((result, index) => (
              <div key={index} className="mb-4 last:mb-0">
                {response.results.length > 1 && (
                  <p className="text-xs text-muted-foreground mb-2">{result.sub_question}</p>
                )}
                <SQLDisplay sql={result.sql} />
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Metadata */}
      <div className="flex items-center justify-center gap-6 py-2 text-xs text-muted-foreground">
        <div className="flex items-center gap-1.5">
          <Clock className="w-3.5 h-3.5" />
          <span>{(response.processing_time_ms / 1000).toFixed(2)}s</span>
        </div>
        <div className="flex items-center gap-1.5">
          <Rows3 className="w-3.5 h-3.5" />
          <span>{response.total_rows} rows</span>
        </div>
        <div className="flex items-center gap-1.5">
          <Zap className="w-3.5 h-3.5" />
          <span>{response.sub_question_count} sub-queries</span>
        </div>
      </div>
    </div>
  )
}
