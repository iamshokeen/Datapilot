const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080"

export async function connectDatabase(data: {
  alias: string
  host: string
  port: number
  database: string
  username: string
  password: string
}): Promise<{ connection_id: string }> {
  const response = await fetch(`${API_BASE_URL}/connect`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...data, schemas: ["public"] }),
  })
  if (!response.ok) {
    const err = await response.json().catch(() => ({}))
    throw new Error(err.detail || `Connection failed (${response.status})`)
  }
  return response.json()
}

export async function submitFeedback(data: {
  session_id: string
  turn_number: number
  verdict: "up" | "down"
  correction_note?: string
}): Promise<{ ok: boolean; verified: boolean; lore_updated: boolean }> {
  const response = await fetch(`${API_BASE_URL}/agent/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  })
  if (!response.ok) {
    const err = await response.json().catch(() => ({}))
    throw new Error(err.detail || `Feedback failed (${response.status})`)
  }
  return response.json()
}

export async function askQuestion(data: {
  connection_id: string
  question: string
  session_id?: string
}) {
  const response = await fetch(`${API_BASE_URL}/agent/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  })
  if (!response.ok) {
    const err = await response.json().catch(() => ({}))
    throw new Error(err.detail || `Query failed (${response.status})`)
  }
  return response.json()
}
