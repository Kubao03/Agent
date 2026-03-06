import os
import tempfile
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, Request, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Literal, Union
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, AIMessageChunk, ToolMessage
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from langchain_tavily import TavilySearch
from langchain_community.tools import WikipediaQueryRun
from langchain_community.utilities import WikipediaAPIWrapper
from langchain.agents import create_agent
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_postgres import PGVector
from langchain_community.embeddings import DashScopeEmbeddings
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool
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

vectorstore: PGVector | None = None  # initialized in lifespan after DB is ready

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
def search_documents(query: str, config: RunnableConfig) -> str:
    """从用户上传的文档中搜索相关内容。当用户询问关于已上传文件的问题时优先使用。"""
    if vectorstore is None:
        return "向量数据库尚未初始化，请稍后再试。"
    thread_id = config.get("configurable", {}).get("thread_id", "")
    results = vectorstore.similarity_search(
        query, k=3, filter={"thread_id": thread_id}
    )
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
    global vectorstore
    db_url = os.getenv("DATABASE_URL", "")
    vector_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)
    vectorstore = PGVector(
        embeddings=embeddings,
        collection_name="documents",
        connection=vector_url,
    )

    pool = AsyncConnectionPool(db_url, kwargs={"autocommit": True}, open=False)
    await pool.open()
    app.state.db = pool

    checkpointer = AsyncPostgresSaver(conn=pool)
    await checkpointer.setup()

    async with pool.connection() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS threads (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)

    app.state.agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
        checkpointer=checkpointer,
    )
    yield

    await pool.close()

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

# ── Thread management ─────────────────────────────────────────────────────────
@app.get("/api/threads")
async def list_threads(request: Request):
    async with request.app.state.db.connection() as conn:
        rows = await conn.execute("SELECT id, title, created_at FROM threads ORDER BY created_at DESC")
        records = await rows.fetchall()
    return [{"id": r[0], "title": r[1], "created_at": r[2].isoformat()} for r in records]

@app.delete("/api/threads/{thread_id}")
async def delete_thread(thread_id: str, request: Request):
    async with request.app.state.db.connection() as conn:
        result = await conn.execute("DELETE FROM threads WHERE id = %s", (thread_id,))
    if result.pgresult.command_tuples == 0:
        raise HTTPException(status_code=404, detail="Thread not found")
    return {"ok": True}

@app.get("/api/threads/{thread_id}/messages")
async def get_thread_messages(thread_id: str, request: Request):
    agent = request.app.state.agent
    state = await agent.aget_state({"configurable": {"thread_id": thread_id}})
    messages = state.values.get("messages", []) if state.values else []
    result = []
    for msg in messages:
        if isinstance(msg, HumanMessage):
            result.append({"role": "user", "content": msg.content})
        elif isinstance(msg, AIMessage):
            text = ""
            if isinstance(msg.content, str):
                text = msg.content
            elif isinstance(msg.content, list):
                text = "".join(b.get("text", "") for b in msg.content if isinstance(b, dict) and b.get("type") == "text")
            if text and not msg.tool_calls:
                result.append({"role": "assistant", "content": text})
    return result

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...), thread_id: str = Form(...)):
    content = await file.read()
    with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp:
        tmp.write(content)
        tmp.flush()
        docs = PyPDFLoader(tmp.name).load()
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, chunk_overlap=200, add_start_index=True
    )
    chunks = splitter.split_documents(docs)
    for chunk in chunks:
        chunk.metadata["source"] = file.filename
        chunk.metadata["thread_id"] = thread_id
    vectorstore.add_documents(chunks)
    return {"filename": file.filename, "chunks": len(chunks)}

@app.post("/api/chat")
async def chat_endpoint(chat_request: ChatRequest, request: Request):
    agent = request.app.state.agent
    title = chat_request.message[:40]
    async with request.app.state.db.connection() as conn:
        await conn.execute(
            "INSERT INTO threads (id, title) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING",
            (chat_request.thread_id, title),
        )

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
