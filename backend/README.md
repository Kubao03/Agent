# Backend

FastAPI + LangGraph agent server with streaming SSE, multi-model support, conversation persistence, and PDF RAG.

## Project Structure

```
backend/
├── main.py              # FastAPI app, agent setup, all API endpoints
├── requirements.txt     # Python dependencies
└── .env                 # API keys (not committed)
```

## Environment Variables

Create `.env` in this directory:

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
uvicorn main:app --reload
# http://localhost:8000
```

Requires a PostgreSQL instance with the `pgvector` extension enabled.

## API Reference

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
