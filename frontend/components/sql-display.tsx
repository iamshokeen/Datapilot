"use client"

import { useState } from "react"
import { Check, Copy } from "lucide-react"

interface SQLDisplayProps {
  sql: string
}

// Simple SQL syntax highlighting
function highlightSQL(sql: string): React.ReactNode[] {
  const keywords = [
    "SELECT",
    "FROM",
    "WHERE",
    "AND",
    "OR",
    "JOIN",
    "LEFT",
    "RIGHT",
    "INNER",
    "OUTER",
    "ON",
    "GROUP BY",
    "ORDER BY",
    "HAVING",
    "LIMIT",
    "OFFSET",
    "AS",
    "IN",
    "NOT",
    "NULL",
    "IS",
    "LIKE",
    "BETWEEN",
    "CASE",
    "WHEN",
    "THEN",
    "ELSE",
    "END",
    "COUNT",
    "SUM",
    "AVG",
    "MIN",
    "MAX",
    "DISTINCT",
    "USING",
    "DESC",
    "ASC",
    "ROUND",
    "OVER",
    "DATE_TRUNC",
  ]

  const parts: React.ReactNode[] = []
  let remaining = sql

  while (remaining.length > 0) {
    let matched = false

    // Check for keywords (case-insensitive)
    for (const keyword of keywords) {
      const regex = new RegExp(`^(${keyword})\\b`, "i")
      const match = remaining.match(regex)
      if (match) {
        parts.push(
          <span key={parts.length} className="text-primary font-medium">
            {match[0]}
          </span>
        )
        remaining = remaining.slice(match[0].length)
        matched = true
        break
      }
    }

    if (matched) continue

    // Check for strings (single quotes)
    const stringMatch = remaining.match(/^'[^']*'/)
    if (stringMatch) {
      parts.push(
        <span key={parts.length} className="text-success">
          {stringMatch[0]}
        </span>
      )
      remaining = remaining.slice(stringMatch[0].length)
      continue
    }

    // Check for numbers
    const numberMatch = remaining.match(/^\d+(\.\d+)?/)
    if (numberMatch) {
      parts.push(
        <span key={parts.length} className="text-chart-4">
          {numberMatch[0]}
        </span>
      )
      remaining = remaining.slice(numberMatch[0].length)
      continue
    }

    // Check for comments
    const commentMatch = remaining.match(/^--[^\n]*/)
    if (commentMatch) {
      parts.push(
        <span key={parts.length} className="text-muted-foreground italic">
          {commentMatch[0]}
        </span>
      )
      remaining = remaining.slice(commentMatch[0].length)
      continue
    }

    // Default: add one character at a time
    parts.push(
      <span key={parts.length} className="text-foreground">
        {remaining[0]}
      </span>
    )
    remaining = remaining.slice(1)
  }

  return parts
}

export function SQLDisplay({ sql }: SQLDisplayProps) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    await navigator.clipboard.writeText(sql)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  // Format SQL for better readability
  const formattedSQL = sql
    .replace(/\s+/g, " ")
    .replace(/(SELECT|FROM|WHERE|GROUP BY|ORDER BY|HAVING|JOIN|LEFT|RIGHT|INNER|AND|OR)/gi, "\n$1")
    .trim()

  return (
    <div className="relative group">
      <pre className="bg-secondary/50 rounded-lg p-4 overflow-x-auto text-sm font-mono leading-relaxed">
        <code>{highlightSQL(formattedSQL)}</code>
      </pre>
      <button
        onClick={handleCopy}
        className="absolute top-3 right-3 p-2 rounded-md bg-background/80 border border-border opacity-0 group-hover:opacity-100 transition-opacity hover:bg-accent"
        title="Copy SQL"
      >
        {copied ? (
          <Check className="w-4 h-4 text-success" />
        ) : (
          <Copy className="w-4 h-4 text-muted-foreground" />
        )}
      </button>
    </div>
  )
}
