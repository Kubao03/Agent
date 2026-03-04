import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Literal, Union
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, AIMessageChunk, ToolMessage
from langchain_core.tools import tool
from langchain_tavily import TavilySearch
from langchain_community.tools import WikipediaQueryRun
from langchain_community.utilities import WikipediaAPIWrapper
from langchain.agents import create_agent
from datetime import datetime

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000",
                   "https://cry-ai-agent.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── LLM ──────────────────────────────────────────────────────────────────────
llm = ChatGoogleGenerativeAI(
    model="gemini-3-flash-preview",
    google_api_key=os.getenv("GOOGLE_API_KEY"),
)

# llm = ChatOpenAI(
#     model="deepseek-chat",
#     api_key=os.getenv("DEEPSEEK_API_KEY"),
#     base_url="https://api.deepseek.com",
# )

# ── Tools ────────────────────────────────────────────────────────────────────
search_tool = TavilySearch(
    max_results=3,
    tavily_api_key=os.getenv("TAVILY_API_KEY"),
)

wiki_tool = WikipediaQueryRun(api_wrapper=WikipediaAPIWrapper(top_k_results=2))

@tool
def get_current_time() -> str:
    """返回当前日期和时间。当用户询问现在几点、今天星期几或当前日期时使用。"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S （%A）")

tools = [search_tool, wiki_tool, get_current_time]

# ── Agent ────────────────────────────────────────────────────────────────────
SYSTEM_PROMPT = "你是一个有用的 AI 助手。查询实时新闻或近期事件用搜索工具；查询百科知识、人物、历史用 Wikipedia；询问当前时间用 get_current_time。"
agent = create_agent(
    model=llm, 
    tools=tools, 
    system_prompt=SYSTEM_PROMPT
)

# ── SSE event models ──────────────────────────────────────────────────────────
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

# ── Request models ────────────────────────────────────────────────────────────
class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: list[Message]

def build_messages(request: ChatRequest):
    lc_messages = []
    for m in request.messages:
        if m.role == "user":
            lc_messages.append(HumanMessage(content=m.content))
        else:
            lc_messages.append(AIMessage(content=m.content))
    return lc_messages

@app.get("/")
def read_root():
    return {"status": "Backend is running!"}

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    async def event_generator():
        lc_messages = build_messages(request)
        async for stream_mode, data in agent.astream(
            {"messages": lc_messages},
            stream_mode=["messages", "updates"],
        ):
            if stream_mode == "messages":
                token, _meta = data
                if isinstance(token, AIMessageChunk) and not token.tool_call_chunks:
                    blocks = token.content_blocks
                    for block in blocks:
                        if block.get("type") == "text" and block.get("text"):
                            yield sse(TextEvent(content=block["text"]))

            elif stream_mode == "updates":
                for _node, update in data.items():
                    msgs = update.get("messages", [])
                    if not msgs:
                        continue
                    last = msgs[-1]
                    # Agent 决定调用工具
                    if isinstance(last, AIMessage) and last.tool_calls:
                        for tc in last.tool_calls:
                            args = tc.get("args", {})
                            query = args.get("query", str(args)) if isinstance(args, dict) else str(args)
                            yield sse(ToolStartEvent(tool=tc["name"], query=query))
                    # 工具执行完毕，带摘要
                    elif isinstance(last, ToolMessage):
                        snippet = str(last.content)[:200] if last.content else ""
                        yield sse(ToolEndEvent(snippet=snippet))

        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
