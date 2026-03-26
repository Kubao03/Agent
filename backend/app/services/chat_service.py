import logging

from fastapi import Request
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, ToolMessage
from langchain.agents.middleware.tool_call_limit import ToolCallLimitExceededError
from langgraph.errors import GraphRecursionError

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
    # run_limit=5，适当放宽给模型生成最终回答的步骤空间
    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 30}
    user_content = message
    if uploaded_file:
        user_content = f"[用户已上传文件：{uploaded_file}]\n{message}"

    try:
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
                    content = token.content
                    if isinstance(content, str) and content:
                        yield sse(TextEvent(content=content))
                    elif isinstance(content, list):
                        for block in content:
                            if block.get("type") == "text" and block.get("text"):
                                yield sse(TextEvent(content=block["text"]))

            elif stream_mode == "updates":
                for node, update in data.items():
                    if update is None:
                        continue
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

    except ToolCallLimitExceededError:
        logger.warning(f"[CHAT] tool call limit reached thread={thread_id[:8]}")
        yield sse(TextEvent(content="\n\n（已达到工具调用上限，以上是目前收集到的信息。）"))
    except GraphRecursionError:
        logger.warning(f"[CHAT] recursion limit reached thread={thread_id[:8]}")
        yield sse(TextEvent(content="\n\n（执行步骤超出上限，以上是目前收集到的信息。）"))

    yield "data: [DONE]\n\n"
