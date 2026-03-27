import os

from langchain_community.embeddings import DashScopeEmbeddings
from langchain_core.documents import Document
from langchain_postgres import PGVector
from psycopg_pool import AsyncConnectionPool

embeddings = DashScopeEmbeddings(
    model="text-embedding-v2",
    dashscope_api_key=os.getenv("DASHSCOPE_API_KEY"),
)

_vectorstore: PGVector | None = None
_pool: AsyncConnectionPool | None = None


async def init_vectorstore(db_url: str, pool: AsyncConnectionPool) -> PGVector:
    global _vectorstore, _pool
    _pool = pool
    vector_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)
    _vectorstore = PGVector(
        embeddings=embeddings,
        collection_name="documents",
        connection=vector_url,
        async_mode=True,
    )
    # 确保 pgvector 扩展、数据表、collection 记录在启动时就建好
    await _vectorstore.acreate_vector_extension()
    await _vectorstore.acreate_tables_if_not_exists()
    await _vectorstore.acreate_collection()
    # 为全文检索建立 GIN 索引（幂等）
    async with pool.connection() as conn:
        await conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_embedding_fts
            ON langchain_pg_embedding USING GIN (to_tsvector('simple', document))
            """
        )
    return _vectorstore


def get_vectorstore() -> PGVector | None:
    return _vectorstore


async def _fts_search(query: str, thread_id: str, k: int = 5) -> list[Document]:
    """用 PostgreSQL 全文检索（tsvector + GIN 索引）替代内存 BM25。"""
    if _pool is None:
        return []
    async with _pool.connection() as conn:
        rows = await (
            await conn.execute(
                """
                SELECT e.document, e.cmetadata,
                       ts_rank(to_tsvector('simple', e.document),
                               plainto_tsquery('simple', %s)) AS rank
                FROM langchain_pg_embedding e
                JOIN langchain_pg_collection c ON e.collection_id = c.uuid
                WHERE c.name = 'documents'
                  AND e.cmetadata->>'thread_id' = %s
                  AND to_tsvector('simple', e.document)
                      @@ plainto_tsquery('simple', %s)
                ORDER BY rank DESC
                LIMIT %s
                """,
                (query, thread_id, query, k),
            )
        ).fetchall()

    return [Document(page_content=row[0], metadata=row[1]) for row in rows]


def _reciprocal_rank_fusion(
    result_lists: list[list[Document]], k: int = 5, rrf_k: int = 60
) -> list[Document]:
    """用 Reciprocal Rank Fusion 合并多个排序列表。"""
    scores: dict[str, float] = {}
    doc_map: dict[str, Document] = {}

    for result_list in result_lists:
        for rank, doc in enumerate(result_list):
            key = doc.page_content
            if key not in scores:
                scores[key] = 0.0
                doc_map[key] = doc
            scores[key] += 1.0 / (rrf_k + rank + 1)

    sorted_keys = sorted(scores, key=lambda x: scores[x], reverse=True)
    return [doc_map[key] for key in sorted_keys[:k]]


async def hybrid_search(query: str, thread_id: str, k: int = 5) -> list[Document]:
    """混合检索：向量相似度 + PostgreSQL 全文检索，用 RRF 融合结果。"""
    vs = get_vectorstore()
    if vs is None:
        return []
    vector_results = await vs.asimilarity_search(query, k=k, filter={"thread_id": thread_id})
    bm25_results = await _fts_search(query, thread_id, k=k)
    return _reciprocal_rank_fusion([vector_results, bm25_results], k=k)
