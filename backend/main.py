from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

# ⚠️ 关键：允许前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"], # Next.js 的默认地址
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 定义数据格式（类似于 Java 的 DTO）
class ChatRequest(BaseModel):
    message: str

@app.get("/")
def read_root():
    return {"status": "Backend is running!"}

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    # 这里以后会写调用 DeepSeek 或 OpenAI 的逻辑
    user_text = request.message
    ai_reply = f"这是来自 FastAPI 的回复。你刚才说的是：{user_text}"
    return {"reply": ai_reply}