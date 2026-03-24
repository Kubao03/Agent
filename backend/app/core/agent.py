from langchain.agents import create_agent
from langchain.agents.middleware import (
    ModelRetryMiddleware,
    SummarizationMiddleware,
    ToolCallLimitMiddleware,
    ToolRetryMiddleware,
)

from app.config import MODEL_CONFIGS
from app.core.tools import tools

# 共享：无状态，所有 agent 复用同一实例
_tool_limit = ToolCallLimitMiddleware(run_limit=5, exit_behavior="continue")
_tool_retry = ToolRetryMiddleware(max_retries=2)       # Tavily / Wikipedia 超时自动重试
_model_retry = ModelRetryMiddleware(max_retries=2)     # 模型 API 限速 / 抖动自动重试


def make_system_prompt(label: str) -> str:
    return f"""\
你是 {label}，一个专注、可靠的个人 AI 助手。

## 能力范围
- 回答知识性问题、帮助分析和总结
- 查询实时信息（新闻、天气、当前时间）
- 检索用户上传的文档内容

## 工具使用规则（按优先级）

1. **用户上传的文档** → 优先调用 `search_documents`
   - 用户提到"文件"、"文档"、"上传"，或问题明显针对某份材料时使用
   - 若返回"没有找到相关文档内容"，告知用户并说明可先上传文件

2. **当前时间/日期** → 调用 `get_current_time`
   - 用户问"今天"、"现在"、"几点"、"星期几"时使用
   - 需要结合实时信息时，先获取时间，再调用搜索工具

3. **实时信息** → 调用网络搜索工具
   - 近期新闻、天气、股价、赛事结果等知识截止日期后的信息

4. **百科/历史/人物** → 调用 `wikipedia`
   - 稳定的事实性知识，不涉及时效性时优先用 Wikipedia 而非网络搜索

5. **无需工具** → 直接回答
   - 通用推理、写作、计算、编程等任务直接完成，不要为了调用工具而调用

## 输出规范
- 默认使用中文回答；用户用其他语言提问时，用相同语言回答
- 回答简洁清晰，复杂问题使用结构化格式（标题、列表、代码块）
- 引用文档或搜索结果时，注明来源
- 工具调用失败或结果为空时，明确告知用户并给出替代建议，不要伪造信息\
"""


def create_agents(checkpointer) -> dict:
    return {
        model_id: create_agent(
            model=cfg["llm"],
            tools=tools,
            system_prompt=make_system_prompt(cfg["label"]),
            middleware=[
                _tool_limit,
                _tool_retry,
                _model_retry,
                # SummarizationMiddleware 与模型绑定，每个 agent 独立实例
                # 超过 40 条消息触发摘要，保留最近 20 条
                SummarizationMiddleware(
                    cfg["llm"],
                    trigger=("messages", 40),
                    keep=("messages", 20),
                ),
            ],
            checkpointer=checkpointer,
        )
        for model_id, cfg in MODEL_CONFIGS.items()
    }
