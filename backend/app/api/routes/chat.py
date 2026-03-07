import logging

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.config import DEFAULT_MODEL, MODEL_CONFIGS
from app.models.requests import ChatRequest
from app.services.chat_service import stream_agent_response

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/chat")
async def chat_endpoint(chat_request: ChatRequest, request: Request):
    model_id = chat_request.model if chat_request.model in MODEL_CONFIGS else DEFAULT_MODEL
    agent = request.app.state.agents[model_id]
    logger.info(
        f"[CHAT] thread={chat_request.thread_id[:8]} model={model_id} "
        f"msg={chat_request.message[:60]!r}"
    )

    async with request.app.state.db.connection() as conn:
        await conn.execute(
            "INSERT INTO threads (id, title) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING",
            (chat_request.thread_id, chat_request.message[:40]),
        )

    return StreamingResponse(
        stream_agent_response(
            agent=agent,
            thread_id=chat_request.thread_id,
            message=chat_request.message,
            uploaded_file=chat_request.uploaded_file,
            request=request,
        ),
        media_type="text/event-stream",
    )
