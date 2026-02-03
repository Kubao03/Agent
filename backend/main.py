import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from openai import AsyncOpenAI
from pydantic import BaseModel

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000",
                   "https://cry-ai-agent.vercel.app"], # Next.js 的默认地址
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 定义数据格式（类似于 Java 的 DTO）
class ChatRequest(BaseModel):
    message: str

client = AsyncOpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com" # DeepSeek 的服务器地址
)


@app.get("/")
def read_root():
    return {"status": "Backend is running!"}

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    async def event_generator():
        response = await client.chat.completions.create(
            model="deepseek-chat", 
            messages=[
                    {"role": "system", "content": "你是一个有用的 AI 助手。"},
                    {"role": "user", "content": request.message},
                ],
                stream=True 
        )
        async for chunk in response:
            content = chunk.choices[0].delta.content
            if content:
                yield content
    return StreamingResponse(event_generator(), media_type="text/event-stream")