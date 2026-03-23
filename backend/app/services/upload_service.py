import base64
from concurrent.futures import ThreadPoolExecutor, as_completed

import fitz  # pymupdf
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import QWEN_VISION_CLIENT
from app.core.rag import get_vectorstore

# 每页文字少于此字符数时，触发 Vision OCR
_OCR_THRESHOLD = 50
# 并发 OCR 的最大线程数（受限于 Qwen API 的 QPS）
_MAX_WORKERS = 5


def _ocr_page_with_qwen(pixmap: fitz.Pixmap) -> str:
    """将页面图像发送给 Qwen-VL 进行 OCR，返回提取的文本。"""
    img_b64 = base64.standard_b64encode(pixmap.tobytes("png")).decode()
    response = QWEN_VISION_CLIENT.chat.completions.create(
        model="qwen-vl-plus",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{img_b64}"},
                    },
                    {
                        "type": "text",
                        "text": (
                            "请提取这页PPT/文档的所有内容，包括标题、正文、图表说明。"
                            "保持原有层级结构，用换行分隔不同内容块。只输出提取的文本，不要添加解释。"
                        ),
                    },
                ],
            }
        ],
        max_tokens=1500,
    )
    return response.choices[0].message.content or ""



def _extract_pages(pdf_content: bytes) -> list[tuple[str, int]]:
    """
    并发提取各页文本：
    - 文字充足的页在主线程直接收集
    - 文字稀少的页提交线程池并发 OCR
    返回按页码排序的 [(page_text, page_number), ...]
    """
    doc = fitz.open(stream=pdf_content, filetype="pdf")

    # 先在主线程读取所有页数据（fitz 对象非线程安全）
    page_data: list[tuple[int, str, bytes | None]] = []
    for page in doc:
        text = page.get_text().strip()
        if len(text) >= _OCR_THRESHOLD:
            page_data.append((page.number, text, None))
        else:
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            page_data.append((page.number, "", pix.tobytes("png")))
    doc.close()

    # 并发处理：纯文本页直接返回，OCR 页提交线程池
    results: list[tuple[str, int]] = []
    ocr_tasks = [(num, pixmap) for num, text, pixmap in page_data if pixmap is not None]
    text_pages = [(text, num) for num, text, pixmap in page_data if pixmap is None]

    results.extend(text_pages)

    if ocr_tasks:
        with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as executor:
            futures = {
                executor.submit(_ocr_page_with_qwen, fitz.Pixmap(pixmap)): num
                for num, pixmap in ocr_tasks
            }
            for future in as_completed(futures):
                results.append((future.result(), futures[future]))

    results.sort(key=lambda x: x[1])
    return results


def process_pdf(content: bytes, filename: str, thread_id: str) -> int:
    """Chunk and embed a PDF into the vectorstore. Returns number of chunks stored."""
    vs = get_vectorstore()

    pages = _extract_pages(content)
    docs = [
        Document(
            page_content=text,
            metadata={"source": filename, "page": page_num, "thread_id": thread_id},
        )
        for text, page_num in pages
        if text.strip()
    ]

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=2000, chunk_overlap=200, add_start_index=True
    )
    chunks = splitter.split_documents(docs)

    vs.add_documents(chunks)
    return len(chunks)
