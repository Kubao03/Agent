from fastapi import APIRouter, HTTPException, Request
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app.config import DEFAULT_MODEL

router = APIRouter()


@router.get("/threads")
async def list_threads(request: Request):
    async with request.app.state.db.connection() as conn:
        rows = await conn.execute(
            "SELECT id, title, created_at FROM threads ORDER BY created_at DESC"
        )
        records = await rows.fetchall()
    return [{"id": r[0], "title": r[1], "created_at": r[2].isoformat()} for r in records]


@router.delete("/threads/{thread_id}")
async def delete_thread(thread_id: str, request: Request):
    async with request.app.state.db.connection() as conn:
        result = await conn.execute(
            "DELETE FROM threads WHERE id = %s", (thread_id,)
        )
    if result.pgresult.command_tuples == 0:
        raise HTTPException(status_code=404, detail="Thread not found")
    return {"ok": True}


@router.get("/threads/{thread_id}/messages")
async def get_thread_messages(thread_id: str, request: Request):
    agent = request.app.state.agents[DEFAULT_MODEL]
    state = await agent.aget_state({"configurable": {"thread_id": thread_id}})
    raw_messages = state.values.get("messages", []) if state.values else []

    # Build a lookup from tool_call_id -> ToolMessage for step reconstruction
    tool_results: dict = {}
    for msg in raw_messages:
        if isinstance(msg, ToolMessage):
            tool_results[msg.tool_call_id] = msg

    result = []
    pending_steps: list = []

    for msg in raw_messages:
        if isinstance(msg, HumanMessage):
            content = msg.content if isinstance(msg.content, str) else ""
            uploaded_file = None
            if content.startswith("[用户已上传文件："):
                try:
                    end_idx = content.index("]\n")
                    uploaded_file = content[9:end_idx]
                    content = content[end_idx + 2:]
                except ValueError:
                    pass
            entry: dict = {"role": "user", "content": content}
            if uploaded_file:
                entry["uploadedFile"] = uploaded_file
            result.append(entry)
            pending_steps = []

        elif isinstance(msg, AIMessage):
            text = ""
            if isinstance(msg.content, str):
                text = msg.content
            elif isinstance(msg.content, list):
                text = "".join(
                    b.get("text", "") for b in msg.content
                    if isinstance(b, dict) and b.get("type") == "text"
                )

            if msg.tool_calls:
                for tc in msg.tool_calls:
                    args = tc.get("args", {})
                    query = args.get("query", str(args)) if isinstance(args, dict) else str(args)
                    tool_msg = tool_results.get(tc["id"])
                    snippet = str(tool_msg.content)[:200] if tool_msg and tool_msg.content else ""
                    pending_steps.append({
                        "tool": tc["name"], "query": query,
                        "snippet": snippet, "done": True,
                    })
            elif text:
                entry = {"role": "assistant", "content": text}
                if pending_steps:
                    entry["steps"] = pending_steps
                result.append(entry)
                pending_steps = []

    return result
