import logging

from fastapi import Request
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, ToolMessage

from app.models.events import TextEvent, ToolEndEvent, ToolStartEvent, sse

logger = logging.getLogger(__name__)


async def stream_agent_response(
    agent,
    thread_id: str,
    message: str,
    uploaded_file: str | None,
    request: Request,
):
    """Async generator yielding SSE-formatted strings for the chat stream."""
    config = {"configurable": {"thread_id": thread_id}}
    user_content = message
    if uploaded_file:
        user_content = f"[用户已上传文件：{uploaded_file}]\n{message}"

    async for stream_mode, data in agent.astream(
        {"messages": [HumanMessage(content=user_content)]},
        config=config,
        stream_mode=["messages", "updates"],
    ):
        if await request.is_disconnected():
            logger.info(f"[CHAT] client disconnected thread={thread_id[:8]}")
            break

        if stream_mode == "messages":
            token, _ = data
            if isinstance(token, AIMessageChunk) and not token.tool_call_chunks:
                for block in token.content_blocks:
                    if block.get("type") == "text" and block.get("text"):
                        yield sse(TextEvent(content=block["text"]))

        elif stream_mode == "updates":
            for node, update in data.items():
                logger.info(f"[UPDATE] node={node} keys={list(update.keys())}")
                msgs = update.get("messages", [])
                if not msgs:
                    continue
                last = msgs[-1]
                logger.info(f"[MSG] type={type(last).__name__} content={str(last.content)[:100]!r}")
                if isinstance(last, AIMessage) and last.tool_calls:
                    for tc in last.tool_calls:
                        args = tc.get("args", {})
                        query = args.get("query", str(args)) if isinstance(args, dict) else str(args)
                        logger.info(f"[TOOL CALL] {tc['name']} query={query!r}")
                        yield sse(ToolStartEvent(tool=tc["name"], query=query))
                elif isinstance(last, ToolMessage):
                    snippet = str(last.content)[:200] if last.content else ""
                    logger.info(f"[TOOL RESULT] {snippet!r}")
                    yield sse(ToolEndEvent(snippet=snippet))

    yield "data: [DONE]\n\n"
