# DataPilot — Complete Setup Guide

## Quick Start (3 Steps)

### 1. Start Backend (FastAPI)

```bash
cd backend
python -m uvicorn app.main:app --reload
```

Backend runs on **http://localhost:8000**

### 2. Start Frontend (React)

```bash
cd frontend
npm install   # First time only
npm run dev
```

Frontend runs on **http://localhost:3000**

### 3. Open Your Browser

Navigate to **http://localhost:3000**

---

## What You'll See

### Page 1: Connection Setup

The app pre-fills the Lohono sample database credentials:
- Host: `localhost`
- Port: `5433`
- Database: `datapilot`
- Username: `datapilot`
- Password: `datapilot`

Click **"Connect & Index Schema"** to:
1. Test database connection
2. Introspect all 19 tables
3. Build semantic embeddings for schema search

### Page 2: Chat Interface

Once connected, you'll see:
- 4 example questions to get started
- A chat input at the bottom
- Clean, dark analytics tool design

**Try asking:**
- "What was the total gross GMV from confirmed bookings this fiscal year?"
- "Show me occupancy rates by location for the last quarter"
- "What is the lead to booking conversion rate this month?"

### Page 3: Results Display

After each query, you'll see:
1. **Narrative Summary** (top, most prominent) — Natural language answer
2. **SQL Code** (collapsible) — Generated query with syntax highlighting
3. **Data Table** (sortable) — Query results in a clean table
4. **Chart Suggestion** — Recommended visualization
5. **Metadata** — Response time, row count, retries

### Page 4: History

Click **"History"** in the header to:
- View all past queries this session
- Re-run any question with one click
- Clear history

---

## Architecture

```
DataPilot/
├── backend/           # FastAPI + LangGraph agent
│   ├── app/
│   │   ├── main.py
│   │   ├── api/routes/
│   │   ├── agent/     # Phase 2 multi-step agent
│   │   └── core/      # SQL generation, embeddings
│   └── .env
│
├── frontend/          # React + Vite
│   ├── src/
│   │   ├── components/
│   │   ├── api/
│   │   └── lib/
│   └── package.json
│
└── docker-compose.yml  # PostgreSQL + Redis
```

---

## Endpoints

### Backend (localhost:8000)

- `POST /connect` — Connect and index a database
- `POST /agent/ask` — Multi-step AI agent (Phase 2)
- `POST /ask` — Simple text-to-SQL (Phase 1, legacy)
- `GET /health` — Health check
- `GET /docs` — Swagger UI

### Frontend (localhost:3000)

Single-page React app that uses:
- `/connect` on initial connection
- `/agent/ask` for all queries

---

## Features Implemented

### Backend ✅
- [x] Embedding truncation fix (6000 char limit)
- [x] POST /connect indexes 19 tables
- [x] Multi-step LangGraph agent
- [x] SQL generation with 300+ business rules
- [x] Fiscal year logic (Apr-Mar)
- [x] IST timezone conversion
- [x] Query retries (up to 2x)
- [x] Connection ID persistence

### Frontend ✅
- [x] Dark theme with teal accents
- [x] Connection setup page
- [x] Chat interface (ChatGPT-style)
- [x] Step-by-step progress indicator
- [x] Result cards with narrative-first design
- [x] Collapsible SQL with syntax highlighting
- [x] Sortable data tables
- [x] Chart suggestions
- [x] Query history (localStorage)
- [x] Connection persistence
- [x] Responsive design

---

## Tech Stack

### Backend
- Python 3.13
- FastAPI
- LangGraph 0.2+
- Claude Sonnet 4 (Anthropic)
- OpenAI embeddings
- PostgreSQL + pgvector
- SQLAlchemy async

### Frontend
- React 18
- Vite
- Tailwind CSS
- Axios
- React Syntax Highlighter
- Recharts
- Lucide Icons

---

## Troubleshooting

### Frontend won't start
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run dev
```

### Backend errors
Check:
1. Docker containers running: `docker ps`
2. .env file has API keys
3. PostgreSQL on port 5433

### Connection fails
Make sure:
1. Docker Compose is running: `docker compose up -d`
2. Database is `datapilot` on port `5433`
3. Backend shows "Application startup complete"

---

## Next Steps

1. **Test the connection** — Click "Connect & Index Schema"
2. **Ask a question** — Try one of the examples
3. **Explore results** — Expand SQL, sort table columns
4. **View history** — Check past queries
5. **Disconnect** — Clear session and reconnect

---

## Notes

- Connection persists in `localStorage`
- History stored in `localStorage` (max 50 queries)
- Backend runs on port 8000
- Frontend runs on port 3000
- CORS is configured for `*` (development only)
