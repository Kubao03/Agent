# Backend

FastAPI + LangGraph agent server with streaming SSE, multi-model support, conversation persistence, and PDF RAG.

## Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI app entry, lifespan, middleware, router registration
│   ├── config.py            # Env vars, MODEL_CONFIGS, CORS origins
│   ├── core/
│   │   ├── agent.py         # Agent factory: make_system_prompt, create_agents
│   │   ├── rag.py           # Vectorstore singleton: init_vectorstore, get_vectorstore
│   │   └── tools.py         # LangChain tool definitions (search, wiki, time, RAG)
│   ├── models/
│   │   ├── events.py        # SSE event Pydantic models + sse() serializer
│   │   └── requests.py      # ChatRequest schema
│   ├── services/
│   │   ├── chat_service.py  # stream_agent_response async generator
│   │   └── upload_service.py# process_pdf sync function (called via asyncio.to_thread)
│   └── api/routes/
│       ├── chat.py          # POST /api/chat
│       ├── models.py        # GET /api/models
│       ├── threads.py       # GET/DELETE /api/threads, GET /api/threads/{id}/messages
│       └── upload.py        # POST /api/upload
├── requirements.txt
├── .env                     # API keys (not committed)
├── .env.example             # Template for required env vars
└── Dockerfile
```

## Environment Variables

Copy `.env.example` and fill in your keys:

```bash
cp .env.example .env
```

```env
DEEPSEEK_API_KEY=
GOOGLE_API_KEY=
DASHSCOPE_API_KEY=        # Qwen model + embeddings
CLAUDE_API_KEY=
TAVILY_API_KEY=
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/postgres
```

## Development

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
# http://localhost:8000
```

Requires a PostgreSQL instance with the `pgvector` extension enabled.

## API Reference

### `GET /api/models`
Returns available LLM models.

```json
[{ "id": "deepseek-chat", "label": "DeepSeek" }]
```

### `GET /api/threads`
Returns all conversation threads ordered by creation time.

```json
[{ "id": "uuid", "title": "...", "created_at": "2026-01-01T00:00:00Z" }]
```

### `GET /api/threads/{thread_id}/messages`
Returns reconstructed message history for a thread, including tool-call steps.

```json
[
  { "role": "user", "content": "..." },
  { "role": "assistant", "content": "...", "steps": [
    { "tool": "tavily_search_results_json", "query": "...", "snippet": "...", "done": true }
  ]}
]
```

### `DELETE /api/threads/{thread_id}`
Deletes a thread record.

### `POST /api/upload`
Uploads a PDF, chunks and embeds it into pgvector for RAG retrieval.

**Form fields:** `file` (PDF), `thread_id`

```json
{ "filename": "doc.pdf", "chunks": 42 }
```

### `POST /api/chat`
Sends a message to the agent and returns a streaming `text/event-stream` response.

**Request body:**
```json
{
  "thread_id": "uuid",
  "message": "What is in the uploaded document?",
  "model": "deepseek-chat",
  "uploaded_file": "doc.pdf"
}
```

**SSE stream:**
```
data: {"type":"tool_start","tool":"search_documents","query":"uploaded document"}
data: {"type":"tool_end","snippet":"..."}
data: {"type":"text","content":"Based on the document..."}
data: [DONE]
```

## Available Tools

| Tool | Description |
|---|---|
| `tavily_search_results_json` | Real-time web search via Tavily |
| `wikipedia` | Wikipedia article lookup |
| `get_current_time` | Returns current date and time |
| `search_documents` | Semantic search over uploaded PDFs (per thread) |

## Supported Models

| Model ID | Provider |
|---|---|
| `deepseek-chat` | DeepSeek |
| `gemini-3-flash` | Google |
| `qwen-plus` | Alibaba (DashScope) |
| `claude-sonnet-4-6` | Anthropic |
