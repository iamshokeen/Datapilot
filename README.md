# DataPilot

**AI-powered Business Intelligence agent for Lohono Stays** — ask questions in plain English, get SQL-backed answers with narrative summaries, data tables, and chart visualisations.

---

## What It Does

DataPilot connects to your PostgreSQL database, indexes the schema using embeddings, and exposes a conversational analytics interface. Under the hood, a multi-step LangGraph agent:

1. **Decomposes** your question into atomic sub-questions
2. **Generates SQL** using schema context retrieved from vector embeddings
3. **Executes** the SQL against your database
4. **Auto-fixes** failed queries (up to 2 retries via Claude) — detects truncation, type errors, syntax issues
5. **Analyses** results with pandas statistics
6. **Narrates** a concise executive summary via Claude
7. **Suggests and renders** the best chart type (bar / line / pie / scatter)

All Claude system prompts are **cached** (Anthropic prompt caching) — ~80% cost reduction on repeated queries within a session.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Agent orchestration | LangGraph |
| LLM | Claude Sonnet (`claude-sonnet-4-5`) |
| Embeddings | OpenAI text-embedding-3-small |
| Vector store | PostgreSQL + pgvector |
| Backend | FastAPI + SQLAlchemy async |
| Frontend | Next.js 16 + TypeScript + Tailwind v4 + shadcn/ui |
| Charts | Recharts |
| Containerisation | Docker Compose |

---

## Quick Start

### Prerequisites

- Python 3.13+
- Node.js 18+
- Docker Desktop
- Anthropic API key
- OpenAI API key

### 1. Start the database

```bash
docker compose up -d
docker stop datapilot-backend-1   # stop the docker backend to free port 8000
```

PostgreSQL starts on port `5433` with pgvector enabled.

### 2. Configure environment

```bash
cd backend
cp .env.example .env
# Set ANTHROPIC_API_KEY and OPENAI_API_KEY in .env
```

### 3. Start the backend

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --port 8080
# Runs on http://localhost:8080
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
2. Click **Connect Database** and enter your credentials
3. Ask any question in plain English

Default credentials for the sample DB:
```
Host: localhost  Port: 5433  Database: datapilot
Username: datapilot  Password: datapilot
```

---

## Example Questions

- *"What was the total gross GMV from confirmed bookings this fiscal year?"*
- *"Compare Net GMV by channel FY25 vs FY26 with % change"*
- *"Show me occupancy rates by location for the last quarter"*
- *"What is the lead to booking conversion rate this month?"*
- *"Top 5 performing channels by booking count"*

---

## Project Structure

```
datapilot/
├── backend/
│   ├── app/
│   │   ├── agent/
│   │   │   ├── graph/          # LangGraph agent definition
│   │   │   ├── nodes/          # query_planner, sql_generator, executor, rewriter,
│   │   │   │                   # python_analyst, insight_narrator, chart_suggester
│   │   │   └── state.py        # Shared AgentState type
│   │   ├── core/
│   │   │   ├── sql_generator.py   # Text-to-SQL with 300+ Lohono business rules
│   │   │   ├── embedding.py       # pgvector schema indexing
│   │   │   └── llm.py             # LLM client abstraction (Anthropic / OpenAI / Ollama)
│   │   ├── agent_router.py    # POST /agent/ask
│   │   └── main.py
│   └── .env
├── frontend/
│   ├── app/                   # Next.js App Router
│   ├── components/            # Chat, Results, Connection modal, Charts, Table
│   └── lib/
│       ├── api.ts             # connectDatabase() + askQuestion()
│       └── types.ts           # TypeScript interfaces
├── docker-compose.yml
└── README.md
```

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/connect` | Connect to a database and index its schema |
| POST | `/agent/ask` | Run the full multi-step agent pipeline |
| POST | `/ask` | Simple text-to-SQL (legacy, Phase 1) |
| GET | `/health` | Health check |
| GET | `/docs` | Swagger UI |

### POST /agent/ask

**Request:**
```json
{
  "connection_id": "uuid-from-connect",
  "question": "What was Net GMV by channel this fiscal year?"
}
```

**Response:**
```json
{
  "question": "...",
  "narrative": "AI-written insight paragraph",
  "chart_suggestion": { "type": "bar", "x_axis": "channel", "y_axis": "net_gmv", "reason": "..." },
  "data": [{ "channel": "Google", "net_gmv": 12500000 }, ...],
  "results": [{ "sub_question": "...", "sql": "SELECT ...", "row_count": 11, "execution_success": true, "retries": 0 }],
  "total_rows": 11,
  "sub_question_count": 1,
  "processing_time_ms": 8200
}
```

---

## Agent Pipeline

```
question
   │
   ▼
query_planner  ──→  [sub_q_1, sub_q_2, ...]
   │
   ▼
sql_generator  ──→  SELECT ...   (max_tokens=8192, prompt cached)
   │
   ▼
sql_executor   ──→  [{rows}]
   │         ↑
   │    on error: sql_rewriter (max 2 retries)
   │    truncation detected → simplify strategy
   ▼
python_analyst  ──→  {stats, distributions, top_5}
   │
   ▼
accumulate_result  ──→  (loop per sub-question)
   │
   ▼
insight_narrator  ──→  narrative (prompt cached)
   │
   ▼
chart_suggester   ──→  {type, x_axis, y_axis}
   │
   ▼
assemble_response  ──→  final JSON
```

---

## Roadmap

- [x] Phase 1 — Text-to-SQL with domain prompt engineering
- [x] Phase 2 — LangGraph agent (query planning, self-healing SQL, analytics, narration)
- [x] Phase 4 — Next.js frontend with charts, connection manager, query history
- [ ] Multi-turn conversation (LangGraph SqliteSaver + session threading)
- [ ] Phase 3 — Evaluation (DeepEval), few-shot SQL injection, Redis caching
- [ ] Phase 5 — Fine-tuning Llama 3.1 8B + cost routing + prompt caching

---

## Cost

~$0.04 per query at baseline. Anthropic prompt caching (implemented) reduces this to ~$0.008 for repeated queries within a 5-minute window.
