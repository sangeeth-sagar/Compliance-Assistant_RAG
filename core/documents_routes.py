import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from core.db import get_db
from core.models import User, Document, AuditLog, ChatMessage
from core.schemas import (
    DocumentOut, DocumentDetail, QueryRequest,
    ChatMessageOut, AuditLogOut,
)
from core.security import get_current_user
from core.extractor import extract_text
from core.pii_detector import detect_pii, count_findings
from core.risk_engine import compute_risk
from core.redactor import redact_text
from core.summarizer import generate_summary, answer_question, summarize_chat_history
from core.rag_engine import index_document as rag_index, query_document as rag_query
from core.audit import log_action

router = APIRouter(prefix="/api", tags=["documents"])


@router.post("/scan", response_model=DocumentOut, status_code=201)
async def scan_document(
    file: UploadFile = File(...),
    use_spacy: bool = Form(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    file_bytes = await file.read()
    filename = file.filename

    raw_text, source_type, count = extract_text(file_bytes, filename)
    if not raw_text.strip():
        raise HTTPException(status_code=400, detail="No text could be extracted from the document.")

    findings = detect_pii(raw_text, use_spacy=use_spacy)
    risk = compute_risk(findings)
    redacted = redact_text(raw_text, findings)

    doc = Document(
        user_id=current_user.id,
        filename=filename,
        source_type=source_type,
        page_count=count,
        risk_level=risk["level"],
        risk_score=risk["score"],
        risk_breakdown=risk.get("breakdown", []),
        findings=findings,
        raw_text=raw_text,
        redacted_text=redacted,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Automatically index the document for RAG Q&A
    try:
        rag_index(str(doc.id), str(current_user.id), doc.redacted_text)
        doc.indexed = True
        db.commit()
    except Exception as e:
        print(f"Failed to auto-index document {doc.id}: {e}")

    log_action(
        db=db,
        user_id=current_user.id,
        document_id=doc.id,
        action="scan",
        filename=filename,
        risk_level=risk["level"],
        details=count_findings(findings),
    )

    return doc


@router.get("/documents", response_model=list[DocumentOut])
def list_documents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(Document)
        .filter(Document.user_id == current_user.id)
        .order_by(Document.created_at.desc())
        .all()
    )


@router.get("/documents/{doc_id}", response_model=DocumentDetail)
def get_document(
    doc_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doc = (
        db.query(Document)
        .filter(Document.id == doc_id, Document.user_id == current_user.id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.post("/documents/{doc_id}/summary", response_model=DocumentDetail)
def get_document_summary(
    doc_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doc = (
        db.query(Document)
        .filter(Document.id == doc_id, Document.user_id == current_user.id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if not doc.redacted_text:
        raise HTTPException(status_code=404, detail="Redacted text not found")

    summary = generate_summary(
        redacted_text=doc.redacted_text,
        findings_summary=count_findings(doc.findings) if doc.findings else {},
        risk_level=doc.risk_level or "",
    )

    doc.summary_text = summary
    doc.has_summary = True
    db.commit()
    db.refresh(doc)

    log_action(
        db=db,
        user_id=current_user.id,
        document_id=doc.id,
        action="summary",
        filename=doc.filename,
        risk_level=doc.risk_level or "",
    )

    return doc


@router.post("/documents/{doc_id}/index")
def index_document_rag(
    doc_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doc = (
        db.query(Document)
        .filter(Document.id == doc_id, Document.user_id == current_user.id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if not doc.redacted_text:
        raise HTTPException(status_code=404, detail="Redacted text not found")

    n_chunks = rag_index(str(doc.id), str(current_user.id), doc.redacted_text)

    doc.indexed = True
    db.commit()

    log_action(
        db=db,
        user_id=current_user.id,
        document_id=doc.id,
        action="index",
        filename=doc.filename,
        risk_level=doc.risk_level or "",
    )

    return {"chunks": n_chunks}


@router.post("/documents/{doc_id}/query")
def query_document_rag(
    doc_id: uuid.UUID,
    request: QueryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doc = (
        db.query(Document)
        .filter(Document.id == doc_id, Document.user_id == current_user.id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if not doc.indexed:
        raise HTTPException(status_code=400, detail="Document must be indexed before querying")

    history_rows = (
        db.query(ChatMessage)
        .filter(
            ChatMessage.user_id == current_user.id,
            ChatMessage.document_id == doc.id,
        )
        .order_by(ChatMessage.created_at.desc())
        .limit(10)
        .all()
    )
    history_rows.reverse()
    chat_history = [{"role": m.role, "content": m.content} for m in history_rows]

    chunks = rag_query(str(doc.id), str(current_user.id), request.question)
    answer = answer_question(
        request.question,
        chunks,
        str(doc.id),
        chat_history=chat_history,
        memory_summary=doc.memory_summary,
        findings=doc.findings,
    )

    db.add(ChatMessage(
        user_id=current_user.id,
        document_id=doc.id,
        role="user",
        content=request.question,
    ))
    db.add(ChatMessage(
        user_id=current_user.id,
        document_id=doc.id,
        role="assistant",
        content=answer,
    ))

    total_messages = (
        db.query(ChatMessage)
        .filter(
            ChatMessage.user_id == current_user.id,
            ChatMessage.document_id == doc.id,
        )
        .count()
    )
    if total_messages > 20:
        old_messages = (
            db.query(ChatMessage)
            .filter(
                ChatMessage.user_id == current_user.id,
                ChatMessage.document_id == doc.id,
            )
            .order_by(ChatMessage.created_at.asc())
            .limit(total_messages - 10)
            .all()
        )
        old_dicts = [{"role": m.role, "content": m.content} for m in old_messages]
        new_summary = summarize_chat_history(old_dicts)
        if doc.memory_summary:
            doc.memory_summary = f"{doc.memory_summary}\n\n{new_summary}"
        else:
            doc.memory_summary = new_summary
        for m in old_messages:
            db.delete(m)

    db.commit()

    log_action(
        db=db,
        user_id=current_user.id,
        document_id=doc.id,
        action="query",
        filename=doc.filename,
        risk_level=doc.risk_level or "",
    )

    return {"answer": answer}


@router.get("/documents/{doc_id}/chat", response_model=list[ChatMessageOut])
def get_chat_history(
    doc_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doc = (
        db.query(Document)
        .filter(Document.id == doc_id, Document.user_id == current_user.id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    messages = (
        db.query(ChatMessage)
        .filter(
            ChatMessage.user_id == current_user.id,
            ChatMessage.document_id == doc.id,
        )
        .order_by(ChatMessage.created_at.asc())
        .all()
    )
    return messages


@router.get("/audit", response_model=list[AuditLogOut])
def get_audit_logs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(AuditLog)
        .filter(AuditLog.user_id == current_user.id)
        .order_by(AuditLog.created_at.desc())
        .limit(200)
        .all()
    )
