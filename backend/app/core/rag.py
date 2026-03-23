import os
import re

import psycopg
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_core.documents import Document
from langchain_postgres import PGVector
from rank_bm25 import BM25Okapi

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
    return _vectorstore


def get_vectorstore() -> PGVector | None:
    return _vectorstore


def _tokenize(text: str) -> list[str]:
    """英文按单词切分，中文按单字切分，用于 BM25。"""
    return re.findall(r"[a-zA-Z0-9]+|[\u4e00-\u9fff]", text.lower())


def _bm25_search(query: str, thread_id: str, k: int = 5) -> list[Document]:
    """从 PostgreSQL 拉取该会话所有文档块，做内存内 BM25 检索。"""
    if _db_url is None:
        return []
    with psycopg.connect(_db_url) as conn:
        rows = conn.execute(
            """
            SELECT e.document, e.cmetadata
            FROM langchain_pg_embedding e
            JOIN langchain_pg_collection c ON e.collection_id = c.uuid
            WHERE c.name = 'documents'
              AND e.cmetadata->>'thread_id' = %s
            """,
            (thread_id,),
        ).fetchall()

    if not rows:
        return []

    docs = [Document(page_content=row[0], metadata=row[1]) for row in rows]
    tokenized_corpus = [_tokenize(doc.page_content) for doc in docs]
    bm25 = BM25Okapi(tokenized_corpus)

    query_tokens = _tokenize(query)
    scores = bm25.get_scores(query_tokens)
    top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
    return [docs[i] for i in top_indices if scores[i] > 0]


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
    """混合检索：向量相似度 + BM25 关键词，用 RRF 融合结果。"""
    vs = get_vectorstore()
    if vs is None:
        return []
    vector_results = vs.similarity_search(query, k=k, filter={"thread_id": thread_id})
    bm25_results = _bm25_search(query, thread_id, k=k)
    return _reciprocal_rank_fusion([vector_results, bm25_results], k=k)
