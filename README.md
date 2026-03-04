# AI Agent Chat

A fullstack AI Agent application with tool calling, streaming responses, and thinking process visualization.

**Live demo:** https://cry-ai-agent.vercel.app

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 15, TypeScript, Tailwind CSS v4 |
| Backend | FastAPI, Python |
| AI | Gemini / DeepSeek (switchable) |
| Agent | LangChain + LangGraph (ReAct agent) |
| Rendering | react-markdown, react-syntax-highlighter |
| Deployment | Vercel (frontend) + Railway (backend) |

## Features

- **Tool calling** — agent autonomously decides when to use tools
- **Thinking process UI** — collapsible panel showing tool calls in real time
- **Multi-turn conversation** — full message history sent each turn
- **Streaming responses** — token-by-token output via SSE
- **Markdown and code rendering** — syntax highlighting with copy button
- **Structured SSE events** — typed JSON events (text / tool_start / tool_end)

## Tools

| Tool | Source | Use case |
|---|---|---|
| Tavily Search | `langchain_tavily` | Real-time news and web search |
| Wikipedia | `langchain_community` | Encyclopedic knowledge |
| get_current_time | custom `@tool` | Current date and time |

## Project Structure

```
my-ai-app/
├── frontend/
│   └── app/
│       ├── page.tsx        # Chat UI, SSE parsing, ThinkingPanel
│       └── globals.css
├── backend/
│   └── main.py             # FastAPI, LangChain agent, SSE streaming
├── docker-compose.yml
└── README.md
```

## Getting Started

### Prerequisites

- Node.js 18+
- Python 3.11+
- API keys: [DeepSeek](https://platform.deepseek.com) or [Gemini](https://aistudio.google.com), [Tavily](https://app.tavily.com)

### Local Development

**1. Backend**

```bash
cd backend
pip install -r requirements.txt

# .env
DEEPSEEK_API_KEY=your_key
GOOGLE_API_KEY=your_key
TAVILY_API_KEY=your_key

uvicorn main:app --reload
# http://localhost:8000
```

**2. Frontend**

```bash
cd frontend
npm install

# .env.local
NEXT_PUBLIC_API_URL=http://localhost:8000

npm run dev
# http://localhost:3000
```

### Docker

```bash
docker compose up --build
```

## API

`POST /api/chat` — returns `text/event-stream`

**Request**
```json
{
  "messages": [
    { "role": "user", "content": "今天上海天气怎么样？" }
  ]
}
```

**SSE Events**
```
data: {"type":"tool_start","tool":"tavily_search","query":"上海天气"}
data: {"type":"tool_end","snippet":"上海今日多云，气温 18°C..."}
data: {"type":"text","content":"根据"}
data: {"type":"text","content":"搜索结果"}
...
data: [DONE]
```

## Deployment

- **Frontend** — Vercel, set `NEXT_PUBLIC_API_URL` to backend URL
- **Backend** — Railway, set all API keys as environment variables
