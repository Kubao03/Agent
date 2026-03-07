import os
import logging
import tempfile
import asyncio
from contextlib import asynccontextmanager
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)
from fastapi import FastAPI, Request, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Literal, Union
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_anthropic import ChatAnthropic
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

# ── LLM configs ───────────────────────────────────────────────────────────────
MODEL_CONFIGS = {
    "deepseek-chat": {
        "label": "DeepSeek",
        "llm": ChatOpenAI(
            model="deepseek-chat",
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com",
        ),
    },
    "gemini-3-flash": {
        "label": "Gemini",
        "llm": ChatGoogleGenerativeAI(
            model="gemini-3-flash-preview",
            google_api_key=os.getenv("GOOGLE_API_KEY"),
        ),
    },
    "qwen-plus": {
        "label": "Qwen",
        "llm": ChatOpenAI(
            model="qwen-plus",
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        ),
    },
    "claude-sonnet-4-6": {
        "label": "Claude",
        "llm": ChatAnthropic(
            model="claude-sonnet-4-6",
            api_key=os.getenv("CLAUDE_API_KEY"),
        ),
    },
}
DEFAULT_MODEL = "deepseek-chat"

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
def make_system_prompt(label: str) -> str:
    return (
        f"你是 {label}，一个有用的 AI 助手。工具使用规则：\n"
        "1. 如果需要查询关于上传文件/文档的内容时，用 search_documents 工具。\n"
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

    app.state.agents = {
        model_id: create_agent(
            model=cfg["llm"],
            tools=tools,
            system_prompt=make_system_prompt(cfg["label"]),
            checkpointer=checkpointer,
        )
        for model_id, cfg in MODEL_CONFIGS.items()
    }
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
    model: str = DEFAULT_MODEL
    uploaded_file: str | None = None

@app.get("/")
def read_root():
    return {"status": "Backend is running!"}

# ── Thread management ─────────────────────────────────────────────────────────
@app.get("/api/models")
def list_models():
    return [{"id": k, "label": v["label"]} for k, v in MODEL_CONFIGS.items()]

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
    agent = request.app.state.agents[DEFAULT_MODEL]
    state = await agent.aget_state({"configurable": {"thread_id": thread_id}})
    raw_messages = state.values.get("messages", []) if state.values else []

    # tool_call_id -> ToolMessage，用于重建 steps
    tool_results: dict = {}
    for msg in raw_messages:
        if isinstance(msg, ToolMessage):
            tool_results[msg.tool_call_id] = msg

    result = []
    pending_steps: list = []   # 当前轮次积累的工具调用步骤

    for msg in raw_messages:
        if isinstance(msg, HumanMessage):
            content = msg.content if isinstance(msg.content, str) else ""
            uploaded_file = None
            # 剥离发送时拼入的文件前缀 "[用户已上传文件：xxx]\n"
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
                # 积累工具调用步骤，等最终回复一起返回
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
                # 最终回复：把前面积累的 steps 一并带上
                entry = {"role": "assistant", "content": text}
                if pending_steps:
                    entry["steps"] = pending_steps
                result.append(entry)
                pending_steps = []

    return result

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...), thread_id: str = Form(...)):
    content = await file.read()
    filename = file.filename

    def process():
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        try:
            docs = PyPDFLoader(tmp_path).load()
        finally:
            os.unlink(tmp_path)
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=2000, chunk_overlap=200, add_start_index=True
        )
        chunks = splitter.split_documents(docs)
        for chunk in chunks:
            chunk.metadata["source"] = filename
            chunk.metadata["thread_id"] = thread_id
        vectorstore.add_documents(chunks)
        return len(chunks)

    num_chunks = await asyncio.to_thread(process)
    return {"filename": filename, "chunks": num_chunks}

@app.post("/api/chat")
async def chat_endpoint(chat_request: ChatRequest, request: Request):
    model_id = chat_request.model if chat_request.model in MODEL_CONFIGS else DEFAULT_MODEL
    agent = request.app.state.agents[model_id]
    logger.info(f"[CHAT] thread={chat_request.thread_id[:8]} model={model_id} msg={chat_request.message[:60]!r}")
    title = chat_request.message[:40]
    async with request.app.state.db.connection() as conn:
        await conn.execute(
            "INSERT INTO threads (id, title) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING",
            (chat_request.thread_id, title),
        )

    async def event_generator():
        config = {"configurable": {"thread_id": chat_request.thread_id}}
        user_content = chat_request.message
        if chat_request.uploaded_file:
            user_content = f"[用户已上传文件：{chat_request.uploaded_file}]\n{user_content}"
        async for stream_mode, data in agent.astream(
            {"messages": [HumanMessage(content=user_content)]},
            config=config,
            stream_mode=["messages", "updates"],
        ):
            if await request.is_disconnected():
                logger.info(f"[CHAT] client disconnected, stopping stream thread={chat_request.thread_id[:8]}")
                break
            if stream_mode == "messages":
                token, _ = data
                if isinstance(token, AIMessageChunk) and not token.tool_call_chunks:
                    blocks = token.content_blocks
                    for block in blocks:
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

    return StreamingResponse(event_generator(), media_type="text/event-stream")
