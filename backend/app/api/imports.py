from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Form
from pathlib import Path
import uuid
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.api.deps import get_current_user
from app.services.imports import import_bank_csv, import_payables_csv, import_po_csv
from app.core.config import settings
from app.models.models import Document, DocumentChunk
from app.worker import process_document, reindex_documents

router = APIRouter(prefix="/imports", tags=["imports"])


@router.post("/bank_csv")
async def bank_csv(file: UploadFile = File(...), db: Session = Depends(get_db), user=Depends(get_current_user)):
    content = (await file.read()).decode("utf-8")
    count = import_bank_csv(db, user.company_id, content)
    return {"imported": count}


@router.post("/payables_csv")
async def payables_csv(file: UploadFile = File(...), db: Session = Depends(get_db), user=Depends(get_current_user)):
    content = (await file.read()).decode("utf-8")
    count = import_payables_csv(db, user.company_id, content)
    return {"imported": count}


@router.post("/po_csv")
async def po_csv(file: UploadFile = File(...), db: Session = Depends(get_db), user=Depends(get_current_user)):
    content = (await file.read()).decode("utf-8")
    count = import_po_csv(db, user.company_id, content)
    return {"imported": count}


@router.post("/docs")
async def upload_document(
    file: UploadFile = File(...),
    embedding_model: str | None = Form(None),
    chunk_size: int | None = Form(None),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    filename = file.filename or "document"
    extension = filename.split(".")[-1].lower()
    if extension not in {"pdf", "docx", "csv", "xlsx"}:
        raise HTTPException(status_code=400, detail="Unsupported file type.")
    allowed_models = {"text-embedding-3-large", "text-embedding-3-small", "text-embedding-ada-002"}
    if embedding_model and embedding_model not in allowed_models:
        raise HTTPException(status_code=400, detail="Unsupported embedding model.")
    if chunk_size is not None and (chunk_size < 200 or chunk_size > 5000):
        raise HTTPException(status_code=400, detail="chunk_size must be between 200 and 5000.")

    storage_dir = Path(settings.document_storage_path)
    storage_dir.mkdir(parents=True, exist_ok=True)
    storage_name = f"{uuid.uuid4().hex}.{extension}"
    destination = storage_dir / storage_name
    content = await file.read()
    destination.write_bytes(content)

    document = Document(
        company_id=user.company_id,
        filename=filename,
        file_type=extension,
        storage_path=storage_name,
        status="queued",
        uploaded_by=user.id,
        embedding_model=embedding_model or settings.embedding_model,
        chunk_size=chunk_size,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    process_document.delay(document.id)
    return {"status": "queued", "document_id": document.id}


@router.get("/docs")
def list_documents(db: Session = Depends(get_db), user=Depends(get_current_user)):
    documents = db.query(Document).filter(Document.company_id == user.company_id).order_by(Document.uploaded_at.desc()).all()
    return [
        {
            "id": doc.id,
            "filename": doc.filename,
            "file_type": doc.file_type,
            "status": doc.status,
            "indexed_chunks": doc.indexed_chunks,
            "indexed_at": doc.indexed_at.isoformat() if doc.indexed_at else None,
            "error_message": doc.error_message,
            "uploaded_at": doc.uploaded_at.isoformat(),
            "embedding_model": doc.embedding_model,
            "chunk_size": doc.chunk_size,
        }
        for doc in documents
    ]


@router.delete("/docs/{document_id}")
def delete_document(document_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    document = db.query(Document).filter(
        Document.id == document_id,
        Document.company_id == user.company_id,
    ).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")

    storage_path = Path(settings.document_storage_path) / document.storage_path
    db.query(DocumentChunk).filter(
        DocumentChunk.document_id == document.id,
        DocumentChunk.company_id == user.company_id,
    ).delete()
    db.delete(document)
    db.commit()
    if storage_path.exists():
        storage_path.unlink()
    return {"status": "deleted"}


@router.post("/docs/reindex")
def reindex_docs(db: Session = Depends(get_db), user=Depends(get_current_user)):
    job = reindex_documents.delay(user.company_id)
    return {"status": "queued", "task_id": job.id}
