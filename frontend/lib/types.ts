export interface Connection {
  id: string
  alias: string
  host: string
  port: number
  database: string
  username: string
}

export interface QueryHistoryItem {
  id: string
  question: string
  timestamp: string
  rowCount: number
  processingTime: number
  subQuestionCount: number
}

export interface ChartSuggestion {
  type: "bar" | "line" | "pie" | "scatter" | "table"
  x_axis: string
  y_axis: string
  group_by?: string
  reason: string
}

export interface QueryResult {
  sub_question: string
  sql: string
  row_count: number
  execution_success: boolean
  retries: number
}

export interface QueryResponse {
  question: string
  sub_questions: string[]
  narrative: string
  chart_suggestion: ChartSuggestion
  data: Record<string, unknown>[]
  results: QueryResult[]
  total_rows: number
  sub_question_count: number
  processing_time_ms: number
  session_id?: string
  requires_new_query?: boolean
  echo_tier?: number
  echo_similarity?: number
}

export interface ChatMessage {
  id: string
  question: string
  response: QueryResponse | null
  error: string | null
  isLoading: boolean
  timestamp: string
}
