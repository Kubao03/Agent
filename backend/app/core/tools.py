import os
from datetime import datetime

from langchain_community.tools import WikipediaQueryRun
from langchain_community.utilities import WikipediaAPIWrapper
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langchain_tavily import TavilySearch

from app.core.rag import get_vectorstore

search_tool = TavilySearch(
    max_results=3,
    tavily_api_key=os.getenv("TAVILY_API_KEY"),
    include_raw_content=True,
)

wiki_tool = WikipediaQueryRun(api_wrapper=WikipediaAPIWrapper(top_k_results=2))


@tool
def get_current_time() -> str:
    """返回当前日期和时间。当用户询问现在几点、今天星期几或当前日期时使用。"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S （%A）")


@tool
def search_documents(query: str, config: RunnableConfig) -> str:
    """从用户上传的文档中搜索相关内容。当用户询问关于已上传文件的问题时优先使用。"""
    vs = get_vectorstore()
    if vs is None:
        return "向量数据库尚未初始化，请稍后再试。"
    thread_id = config.get("configurable", {}).get("thread_id", "")
    results = vs.similarity_search(query, k=3, filter={"thread_id": thread_id})
    if not results:
        return "没有找到相关文档内容，请先上传文件。"
    return "\n\n".join([
        f"[来源: {doc.metadata.get('source', '文档')}]\n{doc.page_content}"
        for doc in results
    ])


tools = [search_tool, wiki_tool, get_current_time, search_documents]
