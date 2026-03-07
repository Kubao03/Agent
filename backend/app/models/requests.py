from pydantic import BaseModel

from app.config import DEFAULT_MODEL


class ChatRequest(BaseModel):
    thread_id: str
    message: str
    model: str = DEFAULT_MODEL
    uploaded_file: str | None = None
