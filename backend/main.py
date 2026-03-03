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
                   "https://cry-ai-agent.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: list[Message]

client = AsyncOpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)

@app.get("/")
def read_root():
    return {"status": "Backend is running!"}

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    async def event_generator():
        full_messages = [
            {"role": "system", "content": "你是一个有用的 AI 助手。"}
        ] + [{"role": m.role, "content": m.content} for m in request.messages]

        response = await client.chat.completions.create(
            model="deepseek-chat",
            messages=full_messages,
            stream=True
        )
        async for chunk in response:
            content = chunk.choices[0].delta.content
            if content:
                yield content

    return StreamingResponse(event_generator(), media_type="text/event-stream")
