# Frontend

Next.js 16 + TypeScript + Tailwind CSS v4 chat interface for AI Agent.

## Project Structure

```
frontend/
├── app/
│   ├── globals.css          # Global styles & scrollbar
│   ├── layout.tsx           # Root layout, fonts, metadata
│   └── page.tsx             # Main page (composition layer only)
├── components/
│   ├── chat/
│   │   ├── AssistantMessage.tsx   # AI response with Markdown rendering
│   │   ├── InputBox.tsx           # Textarea, PDF upload, send/stop button
│   │   └── ThinkingPanel.tsx      # Collapsible tool-call steps panel
│   ├── sidebar/
│   │   └── Sidebar.tsx            # Conversation history sidebar
│   └── ui/
│       ├── CodeBlock.tsx          # Syntax-highlighted code with copy button
│       ├── Icons.tsx              # Shared SVG icons
│       └── ModelDropdown.tsx      # Model selector dropdown
├── hooks/
│   └── useChat.ts           # All chat state & business logic
├── lib/
│   ├── api.ts               # Backend API calls (fetch wrappers)
│   └── sse.ts               # SSE stream event parser
├── types/
│   └── chat.ts              # Shared TypeScript types
└── constants/
    └── models.ts            # Available model list
```

## Environment Variables

Create `.env.local` in this directory:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Development

```bash
npm install
npm run dev      # http://localhost:3000
npm run build    # production build
npm run lint     # ESLint
```

## Supported Models

| Model ID | Display Name |
|---|---|
| `deepseek-chat` | DeepSeek |
| `gemini-3-flash` | Gemini |
| `qwen-plus` | Qwen |
| `claude-sonnet-4-6` | Claude |

## Key Design Decisions

- **`app/page.tsx` is a thin composition layer** — all state lives in `useChat`, all UI in `components/`
- **`@/` path alias** maps to `frontend/` root (configured in `tsconfig.json`)
- **`"use client"` is added only where needed** — components using hooks or browser APIs
- **Unidirectional dependency** — `types` → `constants` → `lib` → `hooks` → `components` → `app`

## SSE Event Types

The frontend parses three event types from the backend stream:

```ts
{ type: "text",       content: string }             // append text to message
{ type: "tool_start", tool: string, query: string } // add a thinking step
{ type: "tool_end",   snippet: string }             // mark step as done
```
