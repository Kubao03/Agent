import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from openai import AsyncOpenAI
from pydantic import BaseModel

load_dotenv()

app = FastAPI()

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

client = AsyncOpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com" # DeepSeek 的服务器地址
)


@app.get("/")
def read_root():
    return {"status": "Backend is running!"}

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    try:
        response = await client.chat.completions.create(
            model="deepseek-chat", 
            messages=[
                    {"role": "system", "content": "你是一个有用的 AI 助手。"},
                    {"role": "user", "content": request.message},
                ],
                stream=False 
        )
        ai_reply = response.choices[0].message.content
        return {"reply": ai_reply}
    except Exception as e:
        print(f"Error: {e}")
        return {"reply": "哎呀，AI 脑子断词了，请检查网络或 API Key。"}