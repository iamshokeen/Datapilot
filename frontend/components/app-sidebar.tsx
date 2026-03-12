"use client"

import { useState } from "react"
import {
  Database,
  History,
  LogOut,
  MessageSquare,
  ChevronRight,
  Trash2,
  Clock,
  Rows3,
  Timer,
  BarChart3,
} from "lucide-react"
import Link from "next/link"
import { cn } from "@/lib/utils"
import type { Connection, QueryHistoryItem } from "@/lib/types"

interface AppSidebarProps {
  connection: Connection | null
  queryHistory: QueryHistoryItem[]
  onConnect: () => void
  onDisconnect: () => void
  onHistorySelect: (item: QueryHistoryItem) => void
  onClearHistory: () => void
}

export function AppSidebar({
  connection,
  queryHistory,
  onConnect,
  onDisconnect,
  onHistorySelect,
  onClearHistory,
}: AppSidebarProps) {
  const [historyExpanded, setHistoryExpanded] = useState(true)

  return (
    <aside className="w-72 flex-shrink-0 border-r border-border bg-sidebar flex flex-col h-full">
      {/* Logo */}
      <div className="h-16 flex items-center px-5 border-b border-sidebar-border">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center">
            <MessageSquare className="w-4 h-4 text-primary" />
          </div>
          <div>
            <h1 className="text-sm font-semibold text-foreground tracking-tight">DataPilot</h1>
            <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Lohono Stays</p>
          </div>
        </div>
      </div>

      {/* Connection Status */}
      <div className="px-4 py-4 border-b border-sidebar-border">
        {connection ? (
          <div className="bg-sidebar-accent rounded-lg p-3">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-2 h-2 rounded-full bg-success animate-pulse" />
              <span className="text-xs font-medium text-foreground">Connected</span>
            </div>
            <p className="text-sm font-medium text-foreground truncate">{connection.alias}</p>
            <p className="text-xs text-muted-foreground truncate mt-0.5">
              {connection.host}:{connection.port}
            </p>
            <button
              onClick={onDisconnect}
              className="mt-3 w-full flex items-center justify-center gap-2 px-3 py-1.5 text-xs text-muted-foreground hover:text-destructive hover:bg-destructive/10 rounded-md transition-colors"
            >
              <LogOut className="w-3 h-3" />
              Disconnect
            </button>
          </div>
        ) : (
          <button
            onClick={onConnect}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors"
          >
            <Database className="w-4 h-4" />
            Connect Database
          </button>
        )}
      </div>

      {/* Query History */}
      <div className="flex-1 flex flex-col min-h-0">
        <button
          onClick={() => setHistoryExpanded(!historyExpanded)}
          className="flex items-center justify-between px-4 py-3 text-xs font-medium text-muted-foreground uppercase tracking-wider hover:text-foreground transition-colors"
        >
          <div className="flex items-center gap-2">
            <History className="w-3.5 h-3.5" />
            Query History
          </div>
          <ChevronRight
            className={cn(
              "w-3.5 h-3.5 transition-transform",
              historyExpanded && "rotate-90"
            )}
          />
        </button>

        {historyExpanded && (
          <div className="flex-1 overflow-y-auto px-2 pb-4">
            {queryHistory.length > 0 ? (
              <>
                <div className="px-2 mb-2">
                  <button
                    onClick={onClearHistory}
                    className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-destructive transition-colors"
                  >
                    <Trash2 className="w-3 h-3" />
                    Clear all
                  </button>
                </div>
                <div className="flex flex-col gap-1">
                  {queryHistory.map((item, idx) => (
                    <button
                      key={item.id ?? item.timestamp ?? idx}
                      onClick={() => onHistorySelect(item)}
                      className="group text-left p-3 rounded-lg hover:bg-sidebar-accent transition-colors"
                    >
                      <p className="text-sm text-foreground line-clamp-2 leading-snug mb-2">
                        {item.question}
                      </p>
                      <div className="flex items-center gap-3 text-xs text-muted-foreground">
                        <span className="flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {formatRelativeTime(item.timestamp)}
                        </span>
                        <span className="flex items-center gap-1">
                          <Rows3 className="w-3 h-3" />
                          {item.rowCount}
                        </span>
                        <span className="flex items-center gap-1">
                          <Timer className="w-3 h-3" />
                          {(item.processingTime / 1000).toFixed(1)}s
                        </span>
                      </div>
                    </button>
                  ))}
                </div>
              </>
            ) : (
              <div className="px-4 py-8 text-center">
                <div className="w-10 h-10 rounded-full bg-muted/50 flex items-center justify-center mx-auto mb-3">
                  <History className="w-5 h-5 text-muted-foreground" />
                </div>
                <p className="text-sm text-muted-foreground">No queries yet</p>
                <p className="text-xs text-muted-foreground/70 mt-1">
                  Your query history will appear here
                </p>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Admin Link */}
      <div className="px-4 py-3 border-t border-sidebar-border">
        <Link
          href="/admin"
          className="flex items-center gap-2 px-3 py-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-sidebar-accent transition-colors w-full"
        >
          <BarChart3 className="w-4 h-4" />
          <span className="text-sm font-medium">Admin Dashboard</span>
        </Link>
      </div>

      {/* Footer */}
      <div className="px-4 py-2 border-t border-sidebar-border">
        <p className="text-[10px] text-muted-foreground/60 text-center">
          Powered by AI
        </p>
      </div>
    </aside>
  )
}

function formatRelativeTime(timestamp: string): string {
  const now = new Date()
  const then = new Date(timestamp)
  const diffMs = now.getTime() - then.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 1) return "Just now"
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  return `${diffDays}d ago`
}
