import type { SSEEvent } from "@/types/chat";

export function parseSSEEvent(raw: string): SSEEvent | null {
  try {
    const ev = JSON.parse(raw) as SSEEvent;
    if (ev.type === "text" || ev.type === "tool_start" || ev.type === "tool_end") {
      return ev;
    }
  } catch {
    // malformed JSON — ignore
  }
  return null;
}
