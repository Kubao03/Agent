from typing import Literal, Union

from pydantic import BaseModel


class TextEvent(BaseModel):
    type: Literal["text"] = "text"
    content: str


class ToolStartEvent(BaseModel):
    type: Literal["tool_start"] = "tool_start"
    tool: str
    query: str


class ToolEndEvent(BaseModel):
    type: Literal["tool_end"] = "tool_end"
    snippet: str


SSEEvent = Union[TextEvent, ToolStartEvent, ToolEndEvent]


def sse(event: SSEEvent) -> str:
    return f"data: {event.model_dump_json()}\n\n"
