import re
from typing import Any
from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.services.documents import search_document_chunks


router = APIRouter(tags=["knowledge"])


class RetrievalSetting(BaseModel):
    top_k: int = 3
    score_threshold: float | None = None


class MetadataCondition(BaseModel):
    logical_operator: str | None = None
    conditions: list[dict[str, Any]] | None = None


class RetrievalRequest(BaseModel):
    knowledge_id: str | None = None
    query: str
    retrieval_setting: RetrievalSetting | None = None
    metadata_condition: MetadataCondition | None = None


def _extract_company_id(knowledge_id: str | None) -> int | None:
    if not knowledge_id:
        return None
    if knowledge_id.isdigit():
        return int(knowledge_id)
    matches = re.findall(r"\d+", knowledge_id)
    if matches:
        return int(matches[0])
    return None


def _score_from_distance(distance: float) -> float:
    # pgvector cosine_distance is roughly 0..2; normalize to 0..1
    return max(0.0, min(1.0, 1.0 - (distance / 2.0)))


def _match_metadata(record: dict, conditions: list[dict[str, Any]] | None) -> bool:
    if not conditions:
        return True
    for condition in conditions:
        name = str(condition.get("name") or "").lower()
        value = str(condition.get("value") or "")
        comparison = str(condition.get("comparison_operator") or "").lower()
        record_value = ""
        if name in {"file_type", "filetype"}:
            record_value = str(record.get("file_type") or "")
        elif name in {"filename", "file_name"}:
            record_value = str(record.get("filename") or "")
        elif name in {"document_id", "doc_id"}:
            record_value = str(record.get("document_id") or "")
        if not record_value:
            continue
        if comparison in {"equals", "eq"} and record_value != value:
            return False
        if comparison in {"contains", "in"} and value not in record_value:
            return False
    return True


@router.post("/retrieval")
def external_kb_retrieval(
    payload: RetrievalRequest,
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
):
    api_key = settings.dify_external_kb_api_key
    if not api_key:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="External KB API key not configured")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing API key")
    if authorization.removeprefix("Bearer ").strip() != api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    company_id = _extract_company_id(payload.knowledge_id) or settings.primary_company_id
    if not company_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="knowledge_id not mapped to a company")

    retrieval = payload.retrieval_setting or RetrievalSetting()
    matches = search_document_chunks(
        db,
        company_id,
        payload.query,
        limit=retrieval.top_k,
        include_score=True,
    )
    filtered = []
    for match in matches:
        if not _match_metadata(match, payload.metadata_condition.conditions if payload.metadata_condition else None):
            continue
        score = _score_from_distance(float(match.get("distance") or 0.0))
        if retrieval.score_threshold is not None and score < retrieval.score_threshold:
            continue
        filtered.append(
            {
                "content": match.get("content") or "",
                "score": score,
                "title": match.get("filename") or "Document",
                "metadata": {
                    "document_id": match.get("document_id"),
                    "chunk_id": match.get("chunk_id"),
                    "file_type": match.get("file_type"),
                },
            }
        )
    return {"records": filtered}
