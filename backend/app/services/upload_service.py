import os
import tempfile

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.rag import get_vectorstore


def process_pdf(content: bytes, filename: str, thread_id: str) -> int:
    """Chunk and embed a PDF into the vectorstore. Returns number of chunks stored."""
    vs = get_vectorstore()

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

    vs.add_documents(chunks)
    return len(chunks)
