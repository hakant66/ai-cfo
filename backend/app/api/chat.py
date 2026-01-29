import json
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from openai import OpenAI
from app.core.config import settings
from app.core.database import get_db
from app.api.deps import get_current_user
from app.services.metrics import get_morning_brief, get_inventory_health, get_cash_forecast, list_payables
from app.services.documents import search_document_chunks
from app.schemas.chat import ChatRequest

router = APIRouter(prefix="/chat", tags=["chat"])
client = OpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None

SYSTEM_PROMPT = (
    "You are an AI CFO. You must only answer using tool results. "
    "If required metrics are missing or a tool call fails, say what is missing and how to fix it. "
    "Always include numbers with time window, sources, confidence level, and metric ids from the tool outputs."
)

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_morning_brief",
            "description": "Return the Morning CFO Brief metrics for a date",
            "parameters": {
                "type": "object",
                "properties": {"date": {"type": "string"}},
                "required": ["date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_inventory_health",
            "description": "Return inventory health metrics",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_cash_forecast",
            "description": "Return cash forecast for a number of days",
            "parameters": {
                "type": "object",
                "properties": {"days": {"type": "integer"}},
                "required": ["days"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_documents",
            "description": "Search uploaded company documents for relevant passages",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "limit": {"type": "integer"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_payables",
            "description": "List payables, optionally filtered by days ahead",
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {"type": "integer"},
                },
            },
        },
    },
]


def run_tool(name: str, args: dict, db: Session, company_id: int):
    if name == "get_morning_brief":
        from datetime import datetime
        return get_morning_brief(db, company_id, datetime.strptime(args["date"], "%Y-%m-%d"))
    if name == "get_inventory_health":
        return get_inventory_health(db, company_id)
    if name == "get_cash_forecast":
        return get_cash_forecast(db, company_id, int(args["days"]))
    if name == "search_documents":
        query = args["query"]
        limit = int(args.get("limit", 5))
        results = search_document_chunks(db, company_id, query, limit=limit)
        return {
            "query": query,
            "results": results,
            "sources": ["Documents"],
            "provenance": "documents.search_document_chunks",
        }
    if name == "list_payables":
        days = args.get("days")
        return list_payables(db, company_id, int(days) if days is not None else None)
    raise ValueError("Unknown tool")


def collect_metric_ids(payload):
    metric_ids = []
    if isinstance(payload, dict):
        if "query_id" in payload:
            metric_ids.append(payload["query_id"])
        for value in payload.values():
            metric_ids.extend(collect_metric_ids(value))
    elif isinstance(payload, list):
        for item in payload:
            metric_ids.extend(collect_metric_ids(item))
    return metric_ids


@router.post("/ask")
def ask_cfo(payload: ChatRequest, db: Session = Depends(get_db), user=Depends(get_current_user)):
    if not client:
        return {
            "answer": "LLM is not configured. Set OPENAI_API_KEY to enable chat.",
            "metrics_used": [],
        }

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": payload.question},
    ]

    first = client.chat.completions.create(
        model=settings.llm_model,
        messages=messages,
        tools=TOOLS,
        tool_choice="auto",
    )

    assistant_message = first.choices[0].message
    tool_calls = assistant_message.tool_calls or []
    if not tool_calls:
        return {
            "answer": "I need more data to answer. Please run the relevant reports or connect data sources.",
            "metrics_used": [],
        }

    messages.append({
        "role": "assistant",
        "content": assistant_message.content or "",
        "tool_calls": [call.model_dump() for call in tool_calls],
    })

    metrics_used = []
    for call in tool_calls:
        tool_name = call.function.name
        tool_args = call.function.arguments
        if isinstance(tool_args, str):
            tool_args = json.loads(tool_args)
        try:
            result = run_tool(tool_name, tool_args, db, user.company_id)
        except Exception as exc:
            return {
                "answer": f"Tool call failed: {tool_name}. Error: {exc}",
                "metrics_used": [],
            }
        metrics_used.extend(collect_metric_ids(result))
        messages.append({
            "role": "tool",
            "tool_call_id": call.id,
            "content": json.dumps(result),
        })

    final = client.chat.completions.create(
        model=settings.llm_model,
        messages=messages,
    )

    answer = final.choices[0].message.content or ""
    return {"answer": answer, "metrics_used": sorted(set(metrics_used))}
