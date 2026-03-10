# DataPilot

**AI-powered Business Intelligence agent for Lohono Stays** — ask questions in plain English, get SQL-backed answers with narrative summaries, data tables, and chart suggestions.

---

## What It Does

DataPilot connects to your PostgreSQL database, indexes the schema using embeddings, and exposes a conversational analytics interface. Under the hood, a multi-step LangGraph agent:

1. **Decomposes** your question into atomic sub-questions
2. **Generates SQL** using schema context retrieved from vector embeddings
3. **Executes** the SQL against your database
4. **Auto-fixes** failed queries (up to 2 retries via Claude)
5. **Analyses** results with pandas statistics
6. **Narrates** a concise executive summary
7. **Suggests** the best chart type for the data

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Agent orchestration | LangGraph |
| LLM | Claude Sonnet (Anthropic) |
| Embeddings | OpenAI text-embedding-3-small |
| Vector store | PostgreSQL + pgvector |
| Backend | FastAPI + SQLAlchemy async |
| Frontend | React 18 + Vite + Tailwind CSS |
| Charts | Recharts |

---

## Quick Start

### Prerequisites

- Python 3.13+
- Node.js 18+
- Docker (for PostgreSQL)
- Anthropic API key
- OpenAI API key

### 1. Start the database

```bash
docker compose up -d
```

This starts PostgreSQL on port `5433` with pgvector enabled.

### 2. Configure environment

```bash
cd backend
cp .env.example .env
# Edit .env and set:
#   ANTHROPIC_API_KEY=...
#   OPENAI_API_KEY=...
```

### 3. Start the backend

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
# Runs on http://localhost:8000
```

### 4. Start the frontend

```bash
cd frontend
npm install
npm run dev
# Runs on http://localhost:3000
```

### 5. Connect and ask

1. Open `http://localhost:3000`
2. Enter your database credentials (defaults pre-filled for the sample DB)
3. Click **Connect & Index Schema**
4. Ask any question in plain English

---

## Example Questions

- *"What was the total gross GMV from confirmed bookings this fiscal year?"*
- *"Show me occupancy rates by location for the last quarter"*
- *"Which properties had the highest cancellation rate in 2024?"*
- *"What is the lead to booking conversion rate this month?"*

---

## Project Structure

```
datapilot/
├── backend/
│   ├── app/
│   │   ├── agent/
│   │   │   ├── graph/          # LangGraph agent definition
│   │   │   ├── nodes/          # Agent nodes (planner, SQL gen, executor, etc.)
│   │   │   └── state.py        # Shared AgentState type
│   │   ├── core/
│   │   │   ├── sql_generator.py   # Phase 1 text-to-SQL
│   │   │   ├── embedding.py       # pgvector schema indexing
│   │   │   └── llm.py
│   │   ├── agent_router.py    # POST /agent/ask endpoint
│   │   └── main.py
│   └── .env
├── frontend/
│   └── src/
│       ├── components/        # Chat, Results, Connection views
│       └── api/
├── data/                      # Sample database schema + seed data
├── docker-compose.yml
└── SETUP.md                   # Detailed setup guide
```

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/connect` | Connect to a database and index its schema |
| POST | `/agent/ask` | Run the full multi-step agent pipeline |
| POST | `/ask` | Simple text-to-SQL (legacy, single query) |
| GET | `/health` | Health check |
| GET | `/docs` | Swagger UI |

---

## Agent Pipeline

```
question
   │
   ▼
query_planner  ──→  [sub_q_1, sub_q_2, ...]
   │
   ▼
sql_generator  ──→  SELECT ...
   │
   ▼
sql_executor   ──→  [{rows}]
   │         ↑
   │    (on error, max 2 retries)
   ▼         │
sql_rewriter ─┘
   │
   ▼
python_analyst  ──→  {stats, row_count, ...}
   │
   ▼
accumulate_result  ──→  (loop for each sub-question)
   │
   ▼
insight_narrator  ──→  "narrative text"
   │
   ▼
chart_suggester   ──→  {type, x_axis, y_axis}
   │
   ▼
assemble_response  ──→  final JSON
```

---

## See Also

- [SETUP.md](SETUP.md) — detailed setup, troubleshooting, and feature list
