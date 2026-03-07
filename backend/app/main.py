import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool

from app.api.routes import chat, models, threads, upload
from app.config import CORS_ORIGINS, DATABASE_URL
from app.core.agent import create_agents
from app.core.rag import init_vectorstore

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_vectorstore(DATABASE_URL)

    pool = AsyncConnectionPool(DATABASE_URL, kwargs={"autocommit": True}, open=False)
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

    app.state.agents = create_agents(checkpointer)
    yield

    await pool.close()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(models.router, prefix="/api")
app.include_router(threads.router, prefix="/api")
app.include_router(upload.router, prefix="/api")
app.include_router(chat.router, prefix="/api")


@app.get("/")
def health_check():
    return {"status": "Backend is running!"}
