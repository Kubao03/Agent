# AI Agent Chat

A fullstack AI chat application with streaming responses and multi-turn conversation support.

**Live demo:** https://cry-ai-agent.vercel.app

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 15, TypeScript, Tailwind CSS v4 |
| Backend | FastAPI, Python |
| AI | DeepSeek API (OpenAI-compatible) |
| Rendering | react-markdown, react-syntax-highlighter |
| Deployment | Vercel (frontend) + Railway (backend) |

## Features

- Multi-turn conversation — full message history sent to the model each turn
- Streaming responses with typewriter effect
- Markdown and code block rendering with syntax highlighting
- Auto-scroll to latest message
- Duplicate-send prevention during streaming

## Project Structure

```
my-ai-app/
├── frontend/          # Next.js app
│   └── app/
│       ├── page.tsx   # Chat UI and streaming logic
│       └── globals.css
├── backend/
│   └── main.py        # FastAPI server, DeepSeek API integration
├── docker-compose.yml
└── README.md
```

## Getting Started

### Prerequisites

- Node.js 18+
- Python 3.11+
- DeepSeek API key → [platform.deepseek.com](https://platform.deepseek.com)

### Local Development

**1. Clone and set up backend**

```bash
cd backend
pip install -r requirements.txt

# Create .env file
echo "DEEPSEEK_API_KEY=your_key_here" > .env

uvicorn main:app --reload
# Backend runs at http://localhost:8000
```

**2. Set up frontend**

```bash
cd frontend
npm install

# Create .env.local file
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

npm run dev
# Frontend runs at http://localhost:3000
```

### Docker (one command)

```bash
# Add your API key to backend/.env first
docker compose up --build
```

## API

`POST /api/chat`

```json
{
  "messages": [
    { "role": "user", "content": "Hello" },
    { "role": "assistant", "content": "Hi! How can I help?" },
    { "role": "user", "content": "Write a sort function" }
  ]
}
```

Returns a streaming `text/event-stream` response.

## Deployment

- **Frontend** — deployed on Vercel, set `NEXT_PUBLIC_API_URL` to your backend URL in project settings
- **Backend** — deployed on Railway, set `DEEPSEEK_API_KEY` as an environment variable
