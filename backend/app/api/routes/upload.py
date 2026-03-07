import asyncio

from fastapi import APIRouter, File, Form, UploadFile

from app.services.upload_service import process_pdf

router = APIRouter()


@router.post("/upload")
async def upload_file(file: UploadFile = File(...), thread_id: str = Form(...)):
    content = await file.read()
    num_chunks = await asyncio.to_thread(process_pdf, content, file.filename, thread_id)
    return {"filename": file.filename, "chunks": num_chunks}
