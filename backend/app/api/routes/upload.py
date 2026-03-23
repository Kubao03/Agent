import asyncio
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, BackgroundTasks, File, Form, UploadFile

from app.services.upload_service import process_pdf

router = APIRouter()

# 记录每个 thread_id 的处理状态
_upload_status: dict[str, dict] = {}
_executor = ThreadPoolExecutor(max_workers=4)


def _run_process(content: bytes, filename: str, thread_id: str):
    try:
        chunks = process_pdf(content, filename, thread_id)
        _upload_status[thread_id] = {"status": "done", "filename": filename, "chunks": chunks}
    except Exception as e:
        _upload_status[thread_id] = {"status": "error", "error": str(e)}


@router.post("/upload")
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    thread_id: str = Form(...),
):
    content = await file.read()
    _upload_status[thread_id] = {"status": "processing", "filename": file.filename}
    background_tasks.add_task(asyncio.to_thread, _run_process, content, file.filename, thread_id)
    return {"filename": file.filename, "status": "processing"}


@router.get("/upload/status/{thread_id}")
async def upload_status(thread_id: str):
    return _upload_status.get(thread_id, {"status": "not_found"})
