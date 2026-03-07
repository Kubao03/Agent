import os

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

load_dotenv()

# ── Database ──────────────────────────────────────────────────────────────────
DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/postgres",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
CORS_ORIGINS: list[str] = [
    "http://localhost:3000",
    "https://cry-ai-agent.vercel.app",
]

# ── LLM configs ───────────────────────────────────────────────────────────────
MODEL_CONFIGS: dict = {
    "deepseek-chat": {
        "label": "DeepSeek",
        "llm": ChatOpenAI(
            model="deepseek-chat",
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com",
        ),
    },
    "gemini-3-flash": {
        "label": "Gemini",
        "llm": ChatGoogleGenerativeAI(
            model="gemini-3-flash-preview",
            google_api_key=os.getenv("GOOGLE_API_KEY"),
        ),
    },
    "qwen-plus": {
        "label": "Qwen",
        "llm": ChatOpenAI(
            model="qwen-plus",
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        ),
    },
    "claude-sonnet-4-6": {
        "label": "Claude",
        "llm": ChatAnthropic(
            model="claude-sonnet-4-6",
            api_key=os.getenv("CLAUDE_API_KEY"),
        ),
    },
}

DEFAULT_MODEL: str = "deepseek-chat"
