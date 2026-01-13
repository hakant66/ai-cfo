from datetime import datetime

from fastapi import APIRouter

from app.schemas.chat import ChatRequest, ChatResponse, ToolResult
from app.services.chat import build_llm_answer

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/ask", response_model=ChatResponse)
def ask_chat(request: ChatRequest) -> ChatResponse:
    tool_results = [
        ToolResult(
            metric_id="cash_position",
            payload={
                "value": 42000,
                "currency": "USD",
                "window": "as_of_today",
                "source_systems": ["Bank"],
                "provenance": "compute_cash_position",
                "last_refresh": datetime.utcnow().isoformat(),
            },
        )
    ]
    answer = build_llm_answer(request.question, tool_results)
    return ChatResponse(answer=answer, tool_results=tool_results)
