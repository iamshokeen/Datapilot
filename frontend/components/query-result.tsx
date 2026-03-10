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
  MessageSquare,
} from "lucide-react"
import { DataChart } from "@/components/data-chart"
import { DataTable } from "@/components/data-table"
import { SQLDisplay } from "@/components/sql-display"
import { cn } from "@/lib/utils"
import type { QueryResponse } from "@/lib/types"

interface QueryResultProps {
  response: QueryResponse
}

const chartIcons = {
  bar: BarChart3,
  line: LineChartIcon,
  pie: PieChartIcon,
  scatter: BarChart3,
  table: Table2,
}

export function QueryResult({ response }: QueryResultProps) {
  const [showSQL, setShowSQL] = useState(false)
  const [showDecomposition, setShowDecomposition] = useState(false)

  const ChartIcon = chartIcons[response.chart_suggestion.type] || BarChart3

  return (
    <div className="p-6 lg:p-8 max-w-6xl mx-auto">
      {/* Question */}
      <div className="mb-6">
        <div className="flex items-center gap-2 text-xs text-muted-foreground uppercase tracking-wider mb-2">
          <MessageSquare className="w-3.5 h-3.5" />
          Your Question
        </div>
        <h2 className="text-lg font-medium text-foreground">{response.question}</h2>
      </div>

      {/* Narrative Insight */}
      <div className="bg-card border border-border rounded-xl p-6 mb-6">
        <div className="flex items-start gap-4">
          <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
            <Zap className="w-5 h-5 text-primary" />
          </div>
          <div>
            <h3 className="text-sm font-medium text-primary uppercase tracking-wider mb-2">
              AI Insight
            </h3>
            <p className="text-foreground leading-relaxed">{response.narrative}</p>
          </div>
        </div>
      </div>

      {/* Chart */}
      <div className="bg-card border border-border rounded-xl p-6 mb-6">
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
          <div className="flex items-center gap-2 px-2 py-1 rounded-md bg-secondary text-xs text-muted-foreground">
            <span className="capitalize">{response.chart_suggestion.type} Chart</span>
          </div>
        </div>
        <div className="h-80">
          <DataChart
            type={response.chart_suggestion.type}
            data={response.data}
            xAxis={response.chart_suggestion.x_axis}
            yAxis={response.chart_suggestion.y_axis}
          />
        </div>
      </div>

      {/* Data Table */}
      <div className="bg-card border border-border rounded-xl p-6 mb-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center">
            <Table2 className="w-4 h-4 text-primary" />
          </div>
          <div>
            <h3 className="text-sm font-medium text-foreground">Result Data</h3>
            <p className="text-xs text-muted-foreground mt-0.5">
              {response.total_rows} rows returned
            </p>
          </div>
        </div>
        <DataTable data={response.data} />
      </div>

      {/* Query Decomposition (if multiple sub-questions) */}
      {response.sub_questions.length > 1 && (
        <div className="bg-card border border-border rounded-xl mb-6 overflow-hidden">
          <button
            onClick={() => setShowDecomposition(!showDecomposition)}
            className="w-full flex items-center justify-between p-4 hover:bg-accent/50 transition-colors"
          >
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-secondary flex items-center justify-center">
                <span className="text-sm font-medium text-foreground">
                  {response.sub_questions.length}
                </span>
              </div>
              <span className="text-sm font-medium text-foreground">
                Query Decomposition
              </span>
            </div>
            {showDecomposition ? (
              <ChevronUp className="w-4 h-4 text-muted-foreground" />
            ) : (
              <ChevronDown className="w-4 h-4 text-muted-foreground" />
            )}
          </button>
          {showDecomposition && (
            <div className="px-4 pb-4">
              <ul className="flex flex-col gap-2">
                {response.sub_questions.map((sq, index) => (
                  <li
                    key={index}
                    className="flex items-start gap-3 p-3 rounded-lg bg-secondary/50"
                  >
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
      <div className="bg-card border border-border rounded-xl overflow-hidden">
        <button
          onClick={() => setShowSQL(!showSQL)}
          className="w-full flex items-center justify-between p-4 hover:bg-accent/50 transition-colors"
        >
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-secondary flex items-center justify-center">
              <Code2 className="w-4 h-4 text-muted-foreground" />
            </div>
            <span className="text-sm font-medium text-foreground">
              Generated SQL
            </span>
          </div>
          {showSQL ? (
            <ChevronUp className="w-4 h-4 text-muted-foreground" />
          ) : (
            <ChevronDown className="w-4 h-4 text-muted-foreground" />
          )}
        </button>
        {showSQL && (
          <div className="px-4 pb-4">
            {response.results.map((result, index) => (
              <div key={index} className="mb-4 last:mb-0">
                {response.results.length > 1 && (
                  <p className="text-xs text-muted-foreground mb-2">
                    {result.sub_question}
                  </p>
                )}
                <SQLDisplay sql={result.sql} />
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Metadata Footer */}
      <div className="flex items-center justify-center gap-6 mt-6 py-4 text-xs text-muted-foreground">
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
