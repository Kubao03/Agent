import os
import io
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Literal, Union
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, AIMessageChunk, ToolMessage
from langchain_core.tools import tool
from langchain_tavily import TavilySearch
from langchain_community.tools import WikipediaQueryRun
from langchain_community.utilities import WikipediaAPIWrapper
from langchain.agents import create_agent
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_community.embeddings import DashScopeEmbeddings
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from pypdf import PdfReader
from datetime import datetime

load_dotenv()

# ── LLM ──────────────────────────────────────────────────────────────────────
llm = ChatOpenAI(
    model="deepseek-chat",
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)

# ── RAG ───────────────────────────────────────────────────────────────────────
embeddings = DashScopeEmbeddings(
    model="text-embedding-v2",
    dashscope_api_key=os.getenv("DASHSCOPE_API_KEY"),
)

vectorstore = Chroma(
    collection_name="documents",
    embedding_function=embeddings,
    persist_directory="./chroma_db",
)

# ── Tools ────────────────────────────────────────────────────────────────────
search_tool = TavilySearch(
    max_results=3,
    tavily_api_key=os.getenv("TAVILY_API_KEY"),
    include_raw_content=True,
)

wiki_tool = WikipediaQueryRun(api_wrapper=WikipediaAPIWrapper(top_k_results=2))

@tool
def get_current_time() -> str:
    """返回当前日期和时间。当用户询问现在几点、今天星期几或当前日期时使用。"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S （%A）")

@tool
def search_documents(query: str) -> str:
    """从用户上传的文档中搜索相关内容。当用户询问关于已上传文件的问题时优先使用。"""
    results = vectorstore.similarity_search(query, k=3)
    if not results:
        return "没有找到相关文档内容，请先上传文件。"
    return "\n\n".join([
        f"[来源: {doc.metadata.get('source', '文档')}]\n{doc.page_content}"
        for doc in results
    ])

tools = [search_tool, wiki_tool, get_current_time, search_documents]

# ── Agent ────────────────────────────────────────────────────────────────────
SYSTEM_PROMPT = (
    "你是一个有用的 AI 助手。工具使用规则：\n"
    "1. 用户询问关于上传文件/文档的内容时，用 search_documents 工具。\n"
    "2. 用户问到'今天'、'现在'、'最新'等时间相关内容时，先调用 get_current_time，再用搜索工具。\n"
    "3. 查询实时新闻、天气、近期事件用搜索工具。\n"
    "4. 查询百科知识、人物、历史用 Wikipedia。"
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with AsyncPostgresSaver.from_conn_string(os.getenv("DATABASE_URL")) as checkpointer:
        await checkpointer.setup()
        app.state.agent = create_agent(
            model=llm,
            tools=tools,
            system_prompt=SYSTEM_PROMPT,
            checkpointer=checkpointer,
        )
        yield

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000",
                   "https://cry-ai-agent.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
class ChatRequest(BaseModel):
    thread_id: str
    message: str

@app.get("/")
def read_root():
    return {"status": "Backend is running!"}

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    content = await file.read()
    reader = PdfReader(io.BytesIO(content))
    text = "\n".join(
        page.extract_text() for page in reader.pages if page.extract_text()
    )
    if not text.strip():
        return {"error": "无法从 PDF 中提取文字"}
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.create_documents([text], metadatas=[{"source": file.filename}])
    vectorstore.add_documents(chunks)
    return {"filename": file.filename, "chunks": len(chunks)}

@app.post("/api/chat")
async def chat_endpoint(chat_request: ChatRequest, request: Request):
    agent = request.app.state.agent

    async def event_generator():
        config = {"configurable": {"thread_id": chat_request.thread_id}}
        async for stream_mode, data in agent.astream(
            {"messages": [HumanMessage(content=chat_request.message)]},
            config=config,
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
                    if isinstance(last, AIMessage) and last.tool_calls:
                        for tc in last.tool_calls:
                            args = tc.get("args", {})
                            query = args.get("query", str(args)) if isinstance(args, dict) else str(args)
                            yield sse(ToolStartEvent(tool=tc["name"], query=query))
                    elif isinstance(last, ToolMessage):
                        snippet = str(last.content)[:200] if last.content else ""
                        yield sse(ToolEndEvent(snippet=snippet))

        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
