# AI Agent

A full-stack AI chat application with multi-model support, tool calling, streaming responses, and conversation history.

**Live demo:** https://cry-ai-agent.vercel.app

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 16, TypeScript, Tailwind CSS v4 |
| Backend | FastAPI, Python 3.11 |
| AI Models | DeepSeek / Gemini / Qwen / Claude (switchable) |
| Agent | LangChain + LangGraph (ReAct) |
| Memory | PostgreSQL + LangGraph checkpointer |
| RAG | pgvector + DashScope embeddings |
| Deployment | Vercel (frontend) + Railway (backend) |

## Features

- **Multi-model switching** — DeepSeek, Gemini, Qwen, Claude selectable per conversation
- **Streaming responses** — token-by-token output via SSE
- **Tool calling** — agent autonomously uses search, Wikipedia, time, and document tools
- **Thinking process UI** — collapsible panel showing tool calls in real time
- **PDF upload & RAG** — upload documents and ask questions about them
- **Conversation history** — threads persisted in PostgreSQL, restorable on reload
- **Markdown & code rendering** — syntax highlighting with copy button

## Project Structure

```
my-ai-app/
├── frontend/
│   ├── app/                 # Next.js routes & global styles
│   ├── components/          # UI components (chat, sidebar, ui)
│   ├── hooks/               # useChat — state & business logic
│   ├── lib/                 # API calls, SSE parser
│   ├── types/               # TypeScript types
│   └── constants/           # Model list config
├── backend/
│   └── app/
│       ├── main.py          # FastAPI app entry, lifespan, middleware
│       ├── config.py        # Env vars, model configs, CORS
│       ├── core/            # Agent factory, RAG, tool definitions
│       ├── models/          # Pydantic request & SSE event schemas
│       ├── services/        # Chat streaming, PDF processing
│       └── api/routes/      # Route handlers (chat, threads, upload, models)
├── docker-compose.yml       # Local full-stack dev (Postgres + backend + frontend)
└── README.md
```

See [`frontend/README.md`](frontend/README.md) and [`backend/README.md`](backend/README.md) for detailed setup.

## Quick Start

### Prerequisites

- Node.js 18+
- Python 3.11+
- PostgreSQL with pgvector extension
- API keys: DeepSeek, Google, Qwen (DashScope), Anthropic, Tavily

### With Docker (recommended)

```bash
# Copy and fill in your API keys
cp backend/.env.example backend/.env

docker compose up --build
```

- Frontend: http://localhost:3000
- Backend: http://localhost:8000

### Manual Setup

```bash
# Backend
cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend (new terminal)
cd frontend && npm install
npm run dev
```

## API Overview

`POST /api/chat` — streaming chat, returns `text/event-stream`

```
data: {"type":"tool_start","tool":"tavily_search_results_json","query":"..."}
data: {"type":"tool_end","snippet":"..."}
data: {"type":"text","content":"..."}
data: [DONE]
```

Full API reference in [`backend/README.md`](backend/README.md).

## Deployment

| Service | Platform | Notes |
|---|---|---|
| Frontend | Vercel | Set `NEXT_PUBLIC_API_URL` to backend URL |
| Backend | Railway | Set all API keys as environment variables |
| Database | Railway PostgreSQL | Enable pgvector extension |
