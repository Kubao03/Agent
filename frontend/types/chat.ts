// ─── SSE streaming event types ────────────────────────────────────────────────

export type TextEvent      = { type: "text";       content: string };
export type ToolStartEvent = { type: "tool_start"; tool: string; query: string };
export type ToolEndEvent   = { type: "tool_end";   snippet: string };
export type SSEEvent       = TextEvent | ToolStartEvent | ToolEndEvent;

// ─── Domain types ─────────────────────────────────────────────────────────────

export type Step = {
  tool:     string;
  query:    string;
  snippet?: string;
  done:     boolean;
};

export type Message = {
  role:          "user" | "assistant";
  content:       string;
  steps?:        Step[];
  uploadedFile?: string;   // 仅 user 消息，历史记录里恢复用
};

export type Thread = {
  id:         string;
  title:      string;
  created_at: string;
};
