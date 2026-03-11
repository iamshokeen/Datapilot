# DataPilot

**AI-powered Business Intelligence agent for Lohono Stays** — ask questions in plain English, get SQL-backed answers with narrative summaries, charts, and a continuously self-improving query cache.

Built as a portfolio project demonstrating production-grade LLM engineering: multi-step agent orchestration, semantic caching, multi-turn conversation, cost optimisation, and a feedback-driven learning loop.

---

## What It Does

Connect DataPilot to your PostgreSQL database and ask anything in natural language:

> *"Compare Net GMV by channel FY25 vs FY26 with % change"*
> *"Which 5 properties had the highest cancellation rate last quarter?"*
> *"Show me occupancy trends by location over the last 12 months"*

DataPilot decomposes the question, generates validated SQL, executes it, runs statistical analysis, writes a narrative insight, and renders the best chart — all in one round trip.

---

## Key Features

### ECHO — Every Cached Hit Optimizes
Three-tier semantic SQL cache powered by OpenAI embeddings and pgvector cosine similarity:

| Tier | Trigger | Action | Cost |
|------|---------|--------|------|
| 1 — Exact | Similarity ≥ 0.95 + matching entities | Recycle cached SQL directly, skip Claude entirely | ~$0.0002 |
| 2 — Modify | Similarity 0.82–0.95 or differing dates/locations | Claude minimally edits cached SQL (dates, filters, limits) | ~$0.002 |
| 3 — Full | Similarity < 0.82 | Full agent pipeline | ~$0.008 |

Entity extraction (temporal, location, metric, limit) prevents false positives — "last month" vs "last year" routes to Tier 2 even at high embedding similarity.

### LORE — Learned Operational Rules & Evidence
A persistent business knowledge file (`backend/knowledge/lore.json`) auto-updated by GPT-4o-mini on every thumbs-up. Stores verified SQL patterns, metric definitions, join paths, and business terms observed in production. Injected into SQL generation as few-shot context.

### Correction Learning
Thumbs-down feedback saves a user correction note to the query record. Next time a similar question is asked, ECHO forces Tier 2 and injects the correction directly into Claude's SQL modifier prompt: *"Previous attempt failed — user reported: [note]. Ensure this is fixed."*

### Multi-Turn Conversation
The query planner classifies each follow-up as either:
- **New query** — run full SQL pipeline
- **Re-analysis** — answer from previous turn's data using text analysis only (no SQL, near-zero cost)

Last 3 turns are compressed to single-sentence summaries (~50 tokens/turn) and injected as context. Stored in `conversation_turns` Postgres table.

### Self-Healing SQL
On execution failure, a rewriter node asks Claude to fix the SQL. Detects truncated output (unbalanced parentheses, dangling keywords) and applies a simplification strategy (conditional aggregation instead of nested CTEs). Up to 2 retries per sub-question.

### Anthropic Prompt Caching
All four LLM nodes cache their system prompts (`cache_control: ephemeral`). ~80% cost reduction on repeated queries within a 5-minute session window.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Agent orchestration | LangGraph (StateGraph) |
| LLM — SQL & narration | Claude Sonnet (`claude-sonnet-4-5`) |
| LLM — LORE updates | GPT-4o-mini |
| Embeddings | OpenAI `text-embedding-3-small` (1536d) |
| Vector store | PostgreSQL 16 + pgvector |
| Backend | FastAPI + psycopg2 + pandas |
| Frontend | Next.js 16 (App Router) + TypeScript + Tailwind v4 + shadcn/ui |
| Charts | Recharts |
| PDF export | react-to-print |
| Containerisation | Docker Compose |

---

## Architecture

### Agent Pipeline

```
User Question
      │
      ▼
 query_planner ──────────────────────────────────┐
      │  Decomposes into sub-questions            │
      │  Classifies: new_query vs re-analysis     │
      │  Injects last 3 conversation turns        │
      │                                           │
      │  requires_new_query=False ────────────────┘
      │  (re-uses previous data, no SQL)     python_analyst
      │
      ▼ requires_new_query=True
  echo_lookup  ←── OpenAI embeddings + pgvector cosine search
      │
      ├── Tier 1 (sim ≥ 0.95, entities match)
      │       └──→ sql_executor  (cached SQL, skip Claude)
      │
      ├── Tier 2 (sim 0.82–0.95 OR entity diff OR correction note)
      │       └──→ sql_modifier  (Claude minimal edit)
      │               └──→ sql_executor
      │
      └── Tier 3 (sim < 0.82)
              └──→ sql_generator  (full Claude generation)
                      └──→ sql_executor
                              │  on failure:
                              └──→ sql_rewriter (×2 retries)

      ▼
  python_analyst  ── pandas stats, distributions, top-N
      │
      ▼
  accumulate_result  ── loops per sub-question, merges results
      │
      ▼
  insight_narrator  ── Claude executive summary (prompt cached)
      │
      ▼
  chart_suggester  ── Claude recommends chart type + axes (prompt cached)
      │
      ▼
  assemble_response  ── final JSON response
```

### Data Flow (single request)

```
POST /agent/ask
    { connection_id, question, session_id }
          │
          ├── Load conversation history (last 3 turns, Postgres)
          ├── Run LangGraph agent (streaming state machine)
          ├── Save to query_history (ECHO + embedding)
          ├── Save to conversation_turns (multi-turn)
          └── Return { narrative, data, chart_suggestion, results,
                       echo_tier, echo_similarity, processing_time_ms, ... }
```

### Database Schema (key tables)

```sql
-- Schema index for RAG-based SQL generation
schema_embeddings (id, connection_id, object_type, object_name,
                   ddl_text, embedding VECTOR(1536))

-- ECHO semantic cache + feedback store
query_history (id, connection_id, session_id, question, generated_sql,
               question_embedding VECTOR(1536), echo_tier,
               verified BOOLEAN, feedback TEXT, correction_note TEXT,
               rows_returned, execution_time_ms, created_at)

-- Multi-turn conversation log
conversation_turns (id, session_id, connection_id, turn_number,
                    question, narrative, data_summary, created_at)
```

---

## Project Structure

```
datapilot/
├── backend/
│   ├── app/
│   │   ├── agent/
│   │   │   ├── graph/
│   │   │   │   └── agent_graph.py        # LangGraph StateGraph definition + routing logic
│   │   │   ├── nodes/
│   │   │   │   ├── query_planner.py      # Sub-question decomposition, requires_new_query classification
│   │   │   │   ├── echo_node.py          # ECHO lookup — sets tier, cached SQL, correction note
│   │   │   │   ├── sql_generator_node.py # Full text-to-SQL via Claude (Tier 3)
│   │   │   │   ├── sql_modifier.py       # Minimal SQL edit via Claude (Tier 2)
│   │   │   │   ├── sql_executor.py       # Executes SQL against user's Postgres
│   │   │   │   ├── sql_rewriter.py       # Self-healing: fixes failed SQL (×2 retries)
│   │   │   │   ├── python_analyst.py     # pandas stats + distribution analysis
│   │   │   │   ├── insight_narrator.py   # Claude narrative summary (prompt cached)
│   │   │   │   └── chart_suggester.py    # Claude chart type recommendation (prompt cached)
│   │   │   └── state.py                  # AgentState TypedDict (shared across all nodes)
│   │   ├── api/routes/
│   │   │   ├── connect.py                # POST /connect — DB connect + schema indexing
│   │   │   ├── feedback.py               # POST /agent/feedback — thumbs up/down + LORE
│   │   │   ├── ask.py                    # POST /ask — legacy single-query endpoint
│   │   │   └── health.py                 # GET /health
│   │   ├── core/
│   │   │   ├── echo.py                   # ECHO engine: find_similar(), save_to_history()
│   │   │   ├── lore.py                   # LORE updater — GPT-4o-mini on thumbs-up
│   │   │   ├── conversation.py           # Multi-turn: get_history(), save_turn()
│   │   │   ├── sql_generator.py          # SQL prompt builder (300+ Lohono business rules)
│   │   │   ├── embedding.py              # OpenAI embedding client + pgvector ops
│   │   │   ├── schema_introspector.py    # Introspects Postgres schema → DDL for RAG
│   │   │   └── llm.py                    # LLM client abstraction (Anthropic + OpenAI)
│   │   ├── agent_router.py               # POST /agent/ask — orchestrates full pipeline
│   │   ├── config.py                     # Pydantic settings (loads .env)
│   │   └── main.py                       # FastAPI app + router registration
│   ├── knowledge/
│   │   └── lore.json                     # LORE: auto-updated business rules + verified patterns
│   ├── init_db.sql                       # Postgres schema init (run once)
│   └── requirements.txt
├── frontend/
│   ├── app/
│   │   ├── layout.tsx                    # Root layout + theme provider
│   │   └── page.tsx                      # App state: messages, sessionId, connection, history
│   ├── components/
│   │   ├── chat-interface.tsx            # Chat thread UI, input bar, New Thread button
│   │   ├── query-result.tsx              # Per-response card: insight, chart, table, SQL, feedback
│   │   ├── data-chart.tsx                # Recharts wrapper (bar/line/pie/scatter)
│   │   ├── data-table.tsx                # Paginated sortable result table
│   │   ├── sql-display.tsx               # Syntax-highlighted SQL block
│   │   ├── query-progress.tsx            # Loading state animation
│   │   ├── connection-modal.tsx          # DB connection form
│   │   └── app-sidebar.tsx               # Query history + connection status
│   ├── lib/
│   │   ├── api.ts                        # connectDatabase(), askQuestion(), submitFeedback()
│   │   └── types.ts                      # TypeScript interfaces for all API shapes
│   └── .env.local                        # NEXT_PUBLIC_API_URL=http://localhost:8080
├── docker-compose.yml                    # Postgres 5433 + Redis 6379
├── start.bat                             # Windows one-click startup
├── stop.bat                              # Windows teardown
└── README.md
```

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker Desktop (running)
- Anthropic API key
- OpenAI API key

### 1. Clone and configure

```bash
git clone https://github.com/iamshokeen/Datapilot.git
cd datapilot

cp backend/.env.example backend/.env
# Edit backend/.env and set:
#   ANTHROPIC_API_KEY=sk-ant-...
#   OPENAI_API_KEY=sk-...
```

### 2. Start infrastructure

```bash
docker compose up -d
docker stop datapilot-backend-1   # free port for local backend
```

PostgreSQL starts on `localhost:5433` with pgvector. Redis on `localhost:6379`.

### 3. Start backend

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --port 8080
# API at http://localhost:8080  |  Swagger at http://localhost:8080/docs
```

### 4. Start frontend

```bash
cd frontend
npm install
npm run dev
# UI at http://localhost:3000
```

### 5. Connect and ask

1. Open `http://localhost:3000`
2. Click **Connect Database** and enter:
   ```
   Host: localhost  |  Port: 5433  |  Database: datapilot
   User: datapilot  |  Password: datapilot
   ```
3. Ask any question in plain English

### Windows one-click (PowerShell / cmd)

```bat
.\start.bat    # starts Docker, backend, frontend
.\stop.bat     # kills all three
```

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/connect` | Connect DB + index schema via pgvector |
| POST | `/agent/ask` | Full multi-step agent pipeline |
| POST | `/agent/feedback` | Thumbs up/down + optional correction note |
| POST | `/ask` | Legacy single-query (Phase 1) |
| GET | `/health` | Health check |
| GET | `/docs` | Swagger UI |

### POST /connect

```json
{
  "alias": "lohono",
  "host": "localhost",
  "port": 5433,
  "database": "datapilot",
  "username": "datapilot",
  "password": "datapilot"
}
```

Returns `{ "connection_id": "uuid" }` — pass this to all subsequent requests.

### POST /agent/ask

```json
{
  "connection_id": "uuid-from-connect",
  "question": "Compare Net GMV by channel FY25 vs FY26 with % change",
  "session_id": "optional-uuid-for-multi-turn"
}
```

Response:

```json
{
  "narrative": "Channel performance diverged significantly...",
  "data": [{ "channel": "Google", "fy25_gmv": 12500000, "fy26_gmv": 15800000, "change_pct": 26.4 }],
  "chart_suggestion": {
    "type": "bar",
    "x_axis": "channel",
    "y_axis": "fy26_gmv",
    "reason": "Bar chart best shows categorical comparison across channels"
  },
  "results": [{
    "sub_question": "Net GMV by channel for FY25 and FY26",
    "sql": "SELECT ...",
    "row_count": 8,
    "execution_success": true,
    "retries": 0
  }],
  "total_rows": 8,
  "sub_question_count": 1,
  "processing_time_ms": 3400,
  "echo_tier": 2,
  "echo_similarity": 0.91
}
```

### POST /agent/feedback

```json
{
  "session_id": "uuid",
  "turn_number": 0,
  "verdict": "down",
  "correction_note": "Revenue should include service charges, not just base rent"
}
```

- `verdict: "up"` → marks query as verified (ECHO-eligible), triggers LORE update via GPT-4o-mini
- `verdict: "down"` + `correction_note` → saves correction; next similar question triggers ECHO Tier 2 with note injected into Claude prompt

---

## How ECHO Works (deep dive)

```
New question arrives
        │
        ▼
Embed question → OpenAI text-embedding-3-small (1536d)
        │
        ▼
pgvector cosine search on query_history
WHERE (verified = TRUE OR correction_note IS NOT NULL)
ORDER BY embedding <=> query_vector
LIMIT 5
        │
        ▼
best_match.similarity = 1 - cosine_distance
        │
        ├── sim < 0.82  ──────────────────────────────→  Tier 3 (full generation)
        │
        ├── correction_note present  ─────────────────→  Tier 2 (fix the mistake)
        │
        ├── sim ≥ 0.95 AND entities match  ───────────→  Tier 1 (exact recycle)
        │   entities = {temporal, limits, locations}
        │   "last month" ≠ "last year" → entities differ
        │
        └── else  ────────────────────────────────────→  Tier 2 (minimal edit)
```

---

## Feedback Loop & Learning

```
User submits response
        │
        ├── Thumbs up
        │       ├── verified = TRUE  (ECHO-eligible)
        │       └── GPT-4o-mini reads question + SQL
        │               └── Merges new rules into lore.json
        │                   (verified_filters, metric_definitions, business_terms)
        │
        └── Thumbs down
                ├── Opens correction textarea in UI
                ├── User types: "Wrong — should exclude cancelled bookings"
                └── correction_note saved to query_history
                        └── Next similar question:
                            ECHO forces Tier 2
                            sql_modifier prompt includes:
                            "IMPORTANT: Previous attempt failed.
                             User reported: [correction_note]"
```

---

## Cost Per Query

| Scenario | Approximate Cost |
|----------|-----------------|
| Tier 3 (cold, full pipeline) | ~$0.008 |
| Tier 2 (ECHO modify) | ~$0.002 |
| Tier 1 (ECHO exact) | ~$0.0002 |
| Re-analysis (no SQL, prompt cached) | ~$0.0005 |

Prompt caching (Anthropic `cache_control: ephemeral`) covers system prompts in `query_planner`, `sql_generator`, `insight_narrator`, and `chart_suggester`. ~80% savings on cache hits within 5-minute windows.

---

## Example Questions

```
Revenue & GMV
  "What was total gross GMV from confirmed bookings this fiscal year?"
  "Compare Net GMV by channel FY25 vs FY26 with % change"
  "Show revenue breakdown by property type for Q3"

Occupancy & Bookings
  "Show me occupancy rates by location for the last quarter"
  "What is the lead-to-booking conversion rate this month?"
  "How do booking lead times differ across property categories?"

Guests & Segments
  "What is the distribution of guest segments across all properties?"
  "Which guest source drives the highest average booking value?"
  "Top 5 properties by repeat guest rate"

Multi-turn (follow-ups on same data)
  "Which properties have the highest ratings?"
  → "What is the average revenue for those properties?"   (re-analysis, no new SQL)
  → "Break that down by month"                            (new SQL)
```

---

## Roadmap

- [x] Phase 1 — Text-to-SQL with 300+ Lohono domain rules
- [x] Phase 2 — LangGraph agent (query planning, self-healing SQL, narration, charts)
- [x] Phase 3a — Next.js frontend (chat thread, connection manager, history)
- [x] Phase 3b — Multi-turn conversation (compressed history injection, re-analysis routing)
- [x] Phase 4a — ECHO semantic SQL cache (3-tier, entity extraction, correction learning)
- [x] Phase 4b — LORE auto-updating business knowledge file
- [x] Phase 4c — Feedback loop (thumbs up/down, correction notes, PDF export)
- [x] Phase 4d — Anthropic prompt caching (~80% cost reduction)
- [ ] Phase 5 — Evaluation harness (DeepEval, golden query set, regression CI)
- [ ] Phase 6 — Fine-tuning Llama 3.1 8B on verified query pairs (QLoRA)
- [ ] Phase 7 — Cost router (heuristic — route simple queries to fine-tuned local model)
