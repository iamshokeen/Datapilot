"use client"

import { useState, useEffect } from "react"
import { AppSidebar } from "@/components/app-sidebar"
import { ChatInterface } from "@/components/chat-interface"
import { ConnectionModal } from "@/components/connection-modal"
import { askQuestion } from "@/lib/api"
import type { Connection, QueryHistoryItem, ChatMessage } from "@/lib/types"

const STORAGE_KEY_CONNECTION = "datapilot_connection"
const STORAGE_KEY_HISTORY = "datapilot_history"

export default function DataPilotApp() {
  const [connection, setConnection] = useState<Connection | null>(null)
  const [showConnectionModal, setShowConnectionModal] = useState(false)
  const [queryHistory, setQueryHistory] = useState<QueryHistoryItem[]>([])
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [sessionId, setSessionId] = useState<string>("")

  // Restore connection and history from localStorage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY_CONNECTION)
      if (stored) setConnection(JSON.parse(stored))
    } catch {}
    try {
      const history = localStorage.getItem(STORAGE_KEY_HISTORY)
      if (history) setQueryHistory(JSON.parse(history))
    } catch {}
  }, [])

  const handleConnect = (conn: Connection) => {
    setConnection(conn)
    setShowConnectionModal(false)
    setMessages([])
    setSessionId(crypto.randomUUID())
    localStorage.setItem(STORAGE_KEY_CONNECTION, JSON.stringify(conn))
  }

  const handleDisconnect = () => {
    setConnection(null)
    setMessages([])
    setSessionId("")
    setQueryHistory([])
    localStorage.removeItem(STORAGE_KEY_CONNECTION)
    localStorage.removeItem(STORAGE_KEY_HISTORY)
  }

  const handleQuery = async (question: string) => {
    if (!connection) return

    const msgId = crypto.randomUUID()
    const newMsg: ChatMessage = {
      id: msgId,
      question,
      response: null,
      error: null,
      isLoading: true,
      timestamp: new Date().toISOString(),
    }

    setMessages((prev) => [...prev, newMsg])

    try {
      const response = await askQuestion({
        connection_id: connection.id,
        question,
        session_id: sessionId || undefined,
      })

      setMessages((prev) =>
        prev.map((m) =>
          m.id === msgId ? { ...m, response, isLoading: false } : m
        )
      )

      const newItem: QueryHistoryItem = {
        id: msgId,
        question,
        timestamp: new Date().toISOString(),
        rowCount: response.total_rows,
        processingTime: response.processing_time_ms,
        subQuestionCount: response.sub_question_count,
      }

      setQueryHistory((prev) => {
        const updated = [newItem, ...prev].slice(0, 50)
        localStorage.setItem(STORAGE_KEY_HISTORY, JSON.stringify(updated))
        return updated
      })
    } catch (err) {
      const error = err instanceof Error ? err.message : "Query failed"
      setMessages((prev) =>
        prev.map((m) =>
          m.id === msgId ? { ...m, error, isLoading: false } : m
        )
      )
    }
  }

  const handleHistorySelect = (item: QueryHistoryItem) => {
    handleQuery(item.question)
  }

  const handleClearHistory = () => {
    setQueryHistory([])
    localStorage.removeItem(STORAGE_KEY_HISTORY)
  }

  const handleNewThread = () => {
    setMessages([])
    setSessionId(crypto.randomUUID())
  }

  return (
    <div className="flex h-screen w-full overflow-hidden">
      <AppSidebar
        connection={connection}
        queryHistory={queryHistory}
        onConnect={() => setShowConnectionModal(true)}
        onDisconnect={handleDisconnect}
        onHistorySelect={handleHistorySelect}
        onClearHistory={handleClearHistory}
      />

      <main className="flex-1 flex flex-col min-w-0">
        <ChatInterface
          connection={connection}
          messages={messages}
          sessionId={sessionId}
          onQuery={handleQuery}
          onConnect={() => setShowConnectionModal(true)}
          onNewThread={handleNewThread}
        />
      </main>

      <ConnectionModal
        open={showConnectionModal}
        onOpenChange={setShowConnectionModal}
        onConnect={handleConnect}
      />
    </div>
  )
}
