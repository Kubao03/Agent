from langchain.agents import create_agent

from app.config import MODEL_CONFIGS
from app.core.tools import tools


def make_system_prompt(label: str) -> str:
    return (
        f"你是 {label}，一个有用的 AI 助手。工具使用规则：\n"
        "1. 如果需要查询关于上传文件/文档的内容时，用 search_documents 工具。\n"
        "2. 用户问到'今天'、'现在'、'最新'等时间相关内容时，先调用 get_current_time，再用搜索工具。\n"
        "3. 查询实时新闻、天气、近期事件用搜索工具。\n"
        "4. 查询百科知识、人物、历史用 Wikipedia。"
    )


def create_agents(checkpointer) -> dict:
    return {
        model_id: create_agent(
            model=cfg["llm"],
            tools=tools,
            system_prompt=make_system_prompt(cfg["label"]),
            checkpointer=checkpointer,
        )
        for model_id, cfg in MODEL_CONFIGS.items()
    }
