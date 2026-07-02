import os
import uuid
import json
from typing import Dict, Any, List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from dotenv import load_dotenv
load_dotenv()

from core.extractor import extract_text
from core.pii_detector import detect_pii, count_findings
from core.risk_engine import compute_risk
from core.redactor import redact_text
from core.summarizer import generate_summary, answer_question
from core.rag_engine import index_document, query_document
from core.audit import log_action, read_log

app = FastAPI(
    title="Compliance Sentinel API",
    description="Backend API for PII detection, risk classification, and RAG-based QA",
    version="1.0.0"
)

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CONTENTS_DIR = os.path.join(DATA_DIR, "contents")
DOCS_DB_FILE = os.path.join(DATA_DIR, "documents.json")

os.makedirs(CONTENTS_DIR, exist_ok=True)

def load_docs_db() -> Dict[str, Dict[str, Any]]:
    if not os.path.exists(DOCS_DB_FILE):
        return {}
    try:
        with open(DOCS_DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_docs_db(db: Dict[str, Dict[str, Any]]):
    with open(DOCS_DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2, ensure_ascii=False)

class QueryRequest(BaseModel):
    question: str

@app.post("/api/scan")
async def scan_document(
    file: UploadFile = File(...),
    use_spacy: bool = Form(False)
):
    try:
        file_bytes = await file.read()
        filename = file.filename
        
        # Extract text
        raw_text, source_type, count = extract_text(file_bytes, filename)
        if not raw_text.strip():
            raise HTTPException(status_code=400, detail="No text could be extracted from the document.")
        
        # PII Detection and Processing
        findings = detect_pii(raw_text, use_spacy=use_spacy)
        risk = compute_risk(findings)
        redacted = redact_text(raw_text, findings)
        
        doc_id = str(uuid.uuid4())[:8]
        
        # Save raw & redacted texts to file system
        raw_path = os.path.join(CONTENTS_DIR, f"{doc_id}_raw.txt")
        redacted_path = os.path.join(CONTENTS_DIR, f"{doc_id}_redacted.txt")
        
        with open(raw_path, "w", encoding="utf-8") as f:
            f.write(raw_text)
            
        with open(redacted_path, "w", encoding="utf-8") as f:
            f.write(redacted)
            
        # Log action
        log_action(
            action="scan",
            doc_id=doc_id,
            filename=filename,
            risk_level=risk["level"],
            details=count_findings(findings),
        )
        
        # Save to DB
        db = load_docs_db()
        db[doc_id] = {
            "id": doc_id,
            "filename": filename,
            "source_type": source_type,
            "count": count,
            "risk": risk,
            "findings": findings,
            "indexed": False,
            "has_summary": False
        }
        save_docs_db(db)
        
        return {
            "id": doc_id,
            "filename": filename,
            "risk": risk,
            "findings": findings,
            "findings_summary": count_findings(findings)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/documents")
async def list_documents():
    db = load_docs_db()
    # Return documents summary list
    return list(db.values())

@app.get("/api/documents/{doc_id}")
async def get_document(doc_id: str):
    db = load_docs_db()
    if doc_id not in db:
        raise HTTPException(status_code=404, detail="Document not found")
    
    doc = db[doc_id]
    
    # Read text contents
    raw_path = os.path.join(CONTENTS_DIR, f"{doc_id}_raw.txt")
    redacted_path = os.path.join(CONTENTS_DIR, f"{doc_id}_redacted.txt")
    summary_path = os.path.join(CONTENTS_DIR, f"{doc_id}_summary.txt")
    
    raw_text = ""
    if os.path.exists(raw_path):
        with open(raw_path, "r", encoding="utf-8") as f:
            raw_text = f.read()
            
    redacted_text = ""
    if os.path.exists(redacted_path):
        with open(redacted_path, "r", encoding="utf-8") as f:
            redacted_text = f.read()
            
    summary_text = ""
    if os.path.exists(summary_path):
        with open(summary_path, "r", encoding="utf-8") as f:
            summary_text = f.read()
            
    return {
        **doc,
        "raw_text": raw_text,
        "redacted_text": redacted_text,
        "summary": summary_text
    }

@app.post("/api/documents/{doc_id}/summary")
async def get_document_summary(doc_id: str):
    db = load_docs_db()
    if doc_id not in db:
        raise HTTPException(status_code=404, detail="Document not found")
        
    doc = db[doc_id]
    redacted_path = os.path.join(CONTENTS_DIR, f"{doc_id}_redacted.txt")
    
    if not os.path.exists(redacted_path):
         raise HTTPException(status_code=404, detail="Redacted text not found")
         
    with open(redacted_path, "r", encoding="utf-8") as f:
        redacted_text = f.read()
        
    try:
        summary = generate_summary(
            redacted_text=redacted_text,
            findings_summary=count_findings(doc["findings"]),
            risk_level=doc["risk"]["level"],
        )
        
        # Save summary to file
        summary_path = os.path.join(CONTENTS_DIR, f"{doc_id}_summary.txt")
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(summary)
            
        # Update db
        doc["has_summary"] = True
        save_docs_db(db)
        
        # Log action
        log_action(
            action="summary",
            doc_id=doc_id,
            filename=doc["filename"],
            risk_level=doc["risk"]["level"],
        )
        
        return {"summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/documents/{doc_id}/index")
async def index_document_rag(doc_id: str):
    db = load_docs_db()
    if doc_id not in db:
        raise HTTPException(status_code=404, detail="Document not found")
        
    doc = db[doc_id]
    redacted_path = os.path.join(CONTENTS_DIR, f"{doc_id}_redacted.txt")
    
    if not os.path.exists(redacted_path):
         raise HTTPException(status_code=404, detail="Redacted text not found")
         
    with open(redacted_path, "r", encoding="utf-8") as f:
        redacted_text = f.read()
        
    try:
        n_chunks = index_document(doc_id, redacted_text)
        
        # Update db
        doc["indexed"] = True
        save_docs_db(db)
        
        return {"chunks": n_chunks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/documents/{doc_id}/query")
async def query_document_rag(doc_id: str, request: QueryRequest):
    db = load_docs_db()
    if doc_id not in db:
        raise HTTPException(status_code=404, detail="Document not found")
        
    doc = db[doc_id]
    if not doc.get("indexed"):
         raise HTTPException(status_code=400, detail="Document must be indexed before querying")
         
    try:
        chunks = query_document(doc_id, request.question)
        answer = answer_question(request.question, chunks, doc_id)
        
        # Log action
        log_action(
            action="query",
            doc_id=doc_id,
            filename=doc["filename"],
            risk_level=doc["risk"]["level"],
        )
        
        return {"answer": answer}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/audit")
async def get_audit_logs():
    try:
        return read_log()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Mount static files folder to serve the Vue frontend
# (Make sure to run npm build first)
dist_dir = os.path.join(os.path.dirname(__file__), "frontend", "dist")
if os.path.exists(dist_dir):
    app.mount("/assets", StaticFiles(directory=os.path.join(dist_dir, "assets")), name="assets")
    
    @app.get("/{catchall:path}")
    async def serve_vue_app(catchall: str):
        if catchall.startswith("api/"):
            raise HTTPException(status_code=404, detail="API endpoint not found")
        index_path = os.path.join(dist_dir, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {"message": "Frontend assets found, but index.html was missing."}
else:
    @app.get("/{catchall:path}")
    async def no_frontend(catchall: str):
        if catchall.startswith("api/"):
            raise HTTPException(status_code=404, detail="API endpoint not found")
        return {"message": "Frontend dev environment active. Run npm run dev in frontend/ or compile using npm run build."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
