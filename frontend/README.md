# DataPilot Frontend

Modern React web UI for DataPilot AI Analytics.

## Quick Start

```bash
# Install dependencies
npm install

# Start development server (runs on localhost:3000)
npm run dev
```

## Features

- **Connection Setup** — Connect to any PostgreSQL database
- **Natural Language Queries** — Ask questions in plain English
- **AI-Powered SQL Generation** — Automatic SQL generation with business logic
- **Interactive Results** — Tables, charts, and narrative summaries
- **Query History** — Track and re-run past queries
- **Dark Theme** — Professional analytics tool aesthetic

## Tech Stack

- React 18
- Vite
- Tailwind CSS
- Axios
- Recharts
- React Syntax Highlighter
- Lucide Icons

## Backend Connection

The frontend connects to the FastAPI backend at `http://localhost:8000`.

Make sure the backend is running before starting the frontend:

```bash
cd ../backend
python -m uvicorn app.main:app --reload
```

## Project Structure

```
frontend/
├── src/
│   ├── api/          # API client
│   ├── components/   # React components
│   ├── lib/          # Utilities
│   ├── App.jsx       # Main app component
│   ├── main.jsx      # Entry point
│   └── index.css     # Tailwind styles
├── index.html
├── package.json
└── vite.config.js
```

## Available Scripts

- `npm run dev` — Start development server
- `npm run build` — Build for production
- `npm run preview` — Preview production build
