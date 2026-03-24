import os

import psycopg
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_core.documents import Document
from langchain_postgres import PGVector

embeddings = DashScopeEmbeddings(
    model="text-embedding-v2",
    dashscope_api_key=os.getenv("DASHSCOPE_API_KEY"),
)

_vectorstore: PGVector | None = None
_db_url: str | None = None


def init_vectorstore(db_url: str) -> PGVector:
    global _vectorstore, _db_url
    _db_url = db_url
    vector_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)
    _vectorstore = PGVector(
        embeddings=embeddings,
        collection_name="documents",
        connection=vector_url,
    )
    # 为全文检索建立 GIN 索引（如已存在则跳过）
    with psycopg.connect(_db_url) as conn:
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_embedding_fts
            ON langchain_pg_embedding USING GIN (to_tsvector('simple', document))
            """
        )
        conn.commit()
    return _vectorstore


def get_vectorstore() -> PGVector | None:
    return _vectorstore


def _fts_search(query: str, thread_id: str, k: int = 5) -> list[Document]:
    """用 PostgreSQL 全文检索（tsvector + GIN 索引）替代内存 BM25。"""
    if _db_url is None:
        return []
    # 将查询词转为 tsquery：中文按单字、英文按词，都用 simple 字典处理
    with psycopg.connect(_db_url) as conn:
        rows = conn.execute(
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


def hybrid_search(query: str, thread_id: str, k: int = 5) -> list[Document]:
    """混合检索：向量相似度 + PostgreSQL 全文检索，用 RRF 融合结果。"""
    vs = get_vectorstore()
    if vs is None:
        return []
    vector_results = vs.similarity_search(query, k=k, filter={"thread_id": thread_id})
    bm25_results = _fts_search(query, thread_id, k=k)
    return _reciprocal_rank_fusion([vector_results, bm25_results], k=k)
