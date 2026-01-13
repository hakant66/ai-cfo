from datetime import datetime
from typing import List

from app.schemas.chat import ToolResult


def build_llm_answer(question: str, tool_results: List[ToolResult]) -> str:
    if not tool_results:
        return "I could not retrieve metrics required to answer. Please connect data sources."
    summary = "\n".join(
        [f"- {result.metric_id}: {result.payload.get('value')} ({result.payload.get('window')})" for result in tool_results]
    )
    return (
        "Answer based on verified metrics:\n"
        f"Question: {question}\n"
        f"Metrics:\n{summary}\n"
        f"Generated at {datetime.utcnow().isoformat()}"
    )
