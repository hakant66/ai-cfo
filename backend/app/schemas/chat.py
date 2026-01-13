from typing import List

from pydantic import BaseModel


class ToolResult(BaseModel):
    metric_id: str
    payload: dict


class ChatRequest(BaseModel):
    question: str


class ChatResponse(BaseModel):
    answer: str
    tool_results: List[ToolResult]
