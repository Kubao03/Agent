import os

from langchain_community.embeddings import DashScopeEmbeddings
from langchain_postgres import PGVector

embeddings = DashScopeEmbeddings(
    model="text-embedding-v2",
    dashscope_api_key=os.getenv("DASHSCOPE_API_KEY"),
)

_vectorstore: PGVector | None = None


def init_vectorstore(db_url: str) -> PGVector:
    global _vectorstore
    vector_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)
    _vectorstore = PGVector(
        embeddings=embeddings,
        collection_name="documents",
        connection=vector_url,
    )
    return _vectorstore


def get_vectorstore() -> PGVector | None:
    return _vectorstore
