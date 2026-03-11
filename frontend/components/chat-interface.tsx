"use client"

import { useState, useRef, useEffect } from "react"
import {
  Send,
  Database,
  Sparkles,
  TrendingUp,
  Users,
  Home,
  Calendar,
  User,
  Bot,
  RefreshCw,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { QueryProgress } from "@/components/query-progress"
import { QueryResult } from "@/components/query-result"
import type { Connection, ChatMessage } from "@/lib/types"

interface ChatInterfaceProps {
  connection: Connection | null
  messages: ChatMessage[]
  sessionId?: string
  onQuery: (question: string) => void
  onConnect: () => void
}

const EXAMPLE_QUESTIONS = [
  {
    icon: TrendingUp,
    question: "What is the total revenue by property location?",
    category: "Revenue",
  },
  {
    icon: Calendar,
    question: "Show me booking trends over the last 12 months",
    category: "Bookings",
  },
  {
    icon: Users,
    question: "What is the distribution of guest segments?",
    category: "Guests",
  },
  {
    icon: Home,
    question: "Which properties have the highest ratings?",
    category: "Properties",
  },
]

export function ChatInterface({
  connection,
  messages,
  sessionId,
  onQuery,
  onConnect,
}: ChatInterfaceProps) {
  const [inputValue, setInputValue] = useState("")
  const inputRef = useRef<HTMLInputElement>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom whenever messages change
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  const isQuerying = messages.length > 0 && messages[messages.length - 1].isLoading

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (inputValue.trim() && connection && !isQuerying) {
      onQuery(inputValue.trim())
      setInputValue("")
    }
  }

  const handleExampleClick = (question: string) => {
    if (connection && !isQuerying) {
      onQuery(question)
    }
  }

  // Not connected state
  if (!connection) {
    return (
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="max-w-md text-center">
          <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center mx-auto mb-6">
            <Database className="w-8 h-8 text-primary" />
          </div>
          <h2 className="text-2xl font-semibold text-foreground mb-3">
            Connect to Your Database
          </h2>
          <p className="text-muted-foreground mb-8 leading-relaxed">
            Connect to your PostgreSQL database to start asking questions about your
            Lohono Stays data using natural language.
          </p>
          <Button
            onClick={onConnect}
            size="lg"
            className="bg-primary text-primary-foreground hover:bg-primary/90"
          >
            <Database className="w-4 h-4" />
            Connect Database
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 flex flex-col h-full">
      {/* Header */}
      <header className="h-16 flex items-center justify-between px-6 border-b border-border bg-card/50 flex-shrink-0">
        <div className="flex items-center gap-3">
          <Sparkles className="w-5 h-5 text-primary" />
          <span className="text-sm font-medium text-foreground">Ask anything about your data</span>
        </div>
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-success/10 border border-success/20">
          <div className="w-2 h-2 rounded-full bg-success animate-pulse" />
          <span className="text-xs font-medium text-success">{connection.alias}</span>
        </div>
      </header>

      {/* Chat Thread */}
      <div className="flex-1 overflow-y-auto">
        {messages.length === 0 ? (
          /* Empty state — example questions */
          <div className="flex flex-col items-center justify-center min-h-[400px] p-8">
            <div className="max-w-2xl w-full">
              <div className="text-center mb-10">
                <div className="w-14 h-14 rounded-2xl bg-primary/10 flex items-center justify-center mx-auto mb-5">
                  <Sparkles className="w-7 h-7 text-primary" />
                </div>
                <h2 className="text-2xl font-semibold text-foreground mb-2">
                  What would you like to know?
                </h2>
                <p className="text-muted-foreground">
                  Ask questions about your bookings, revenue, guests, or properties
                </p>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {EXAMPLE_QUESTIONS.map((item, index) => (
                  <button
                    key={index}
                    onClick={() => handleExampleClick(item.question)}
                    className="group flex items-start gap-4 p-4 rounded-xl bg-card border border-border hover:border-primary/30 hover:bg-accent/50 transition-all text-left"
                  >
                    <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0 group-hover:bg-primary/20 transition-colors">
                      <item.icon className="w-5 h-5 text-primary" />
                    </div>
                    <div>
                      <span className="text-xs font-medium text-primary uppercase tracking-wider">
                        {item.category}
                      </span>
                      <p className="text-sm text-foreground mt-1 leading-snug">
                        {item.question}
                      </p>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          /* Message thread */
          <div className="flex flex-col gap-0">
            {messages.map((msg) => (
              <div key={msg.id} className="border-b border-border/40 last:border-b-0">
                {/* User question */}
                <div className="px-6 pt-6 pb-3 flex items-start gap-3">
                  <div className="w-8 h-8 rounded-full bg-secondary flex items-center justify-center flex-shrink-0 mt-0.5">
                    <User className="w-4 h-4 text-muted-foreground" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-foreground leading-relaxed">
                      {msg.question}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">
                      {formatTime(msg.timestamp)}
                    </p>
                  </div>
                </div>

                {/* AI response */}
                <div className="px-6 pb-6 flex items-start gap-3">
                  <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0 mt-0.5">
                    {msg.isLoading ? (
                      <RefreshCw className="w-4 h-4 text-primary animate-spin" />
                    ) : (
                      <Bot className="w-4 h-4 text-primary" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    {msg.isLoading ? (
                      <div className="py-2">
                        <QueryProgress />
                      </div>
                    ) : msg.error ? (
                      <div className="bg-destructive/10 border border-destructive/20 rounded-xl px-4 py-3">
                        <p className="text-sm text-destructive">{msg.error}</p>
                      </div>
                    ) : msg.response ? (
                      <div className="-mx-3">
                        <QueryResult
                          response={msg.response}
                          sessionId={sessionId}
                          turnNumber={messages.filter(m => m.response !== null).findIndex(m => m.id === msg.id)}
                        />
                      </div>
                    ) : null}
                  </div>
                </div>
              </div>
            ))}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {/* Input Area */}
      <div className="border-t border-border bg-card/50 p-4 flex-shrink-0">
        <form onSubmit={handleSubmit} className="max-w-4xl mx-auto">
          <div className="flex items-center gap-3 bg-input border border-border rounded-xl px-4 py-2 focus-within:border-primary/50 focus-within:ring-2 focus-within:ring-primary/20 transition-all">
            <Sparkles className="w-5 h-5 text-muted-foreground flex-shrink-0" />
            <input
              ref={inputRef}
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder={
                messages.length > 0
                  ? "Ask a follow-up question..."
                  : "Ask a question about your data..."
              }
              disabled={isQuerying}
              className="flex-1 bg-transparent border-0 text-foreground placeholder:text-muted-foreground focus:outline-none text-sm py-2"
            />
            <Button
              type="submit"
              size="sm"
              disabled={!inputValue.trim() || isQuerying}
              className="bg-primary text-primary-foreground hover:bg-primary/90 rounded-lg"
            >
              <Send className="w-4 h-4" />
            </Button>
          </div>
          <p className="text-xs text-muted-foreground text-center mt-3">
            {messages.length > 0
              ? "You can ask follow-up questions about the data above"
              : "DataPilot will analyze your database and generate insights"}
          </p>
        </form>
      </div>
    </div>
  )
}

function formatTime(timestamp: string): string {
  try {
    return new Date(timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
  } catch {
    return ""
  }
}
