from fastapi import APIRouter

from app.config import MODEL_CONFIGS

router = APIRouter()


@router.get("/models")
def list_models():
    return [{"id": k, "label": v["label"]} for k, v in MODEL_CONFIGS.items()]
