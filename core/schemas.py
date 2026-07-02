import uuid
from datetime import datetime
from typing import Optional, Any

from pydantic import BaseModel, EmailStr


# ── Auth ──

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int = 600


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    full_name: Optional[str]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Documents ──

class DocumentOut(BaseModel):
    id: uuid.UUID
    filename: str
    source_type: Optional[str]
    page_count: Optional[int]
    risk_level: Optional[str]
    risk_score: Optional[int]
    risk_breakdown: Optional[Any]
    findings: Optional[Any]
    indexed: bool
    has_summary: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentDetail(DocumentOut):
    raw_text: Optional[str]
    redacted_text: Optional[str]
    summary_text: Optional[str]


class QueryRequest(BaseModel):
    question: str


# ── Chat ──

class ChatMessageOut(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Audit ──

class AuditLogOut(BaseModel):
    id: int
    document_id: Optional[uuid.UUID]
    action: str
    filename: Optional[str]
    risk_level: Optional[str]
    details: Optional[Any]
    created_at: datetime

    model_config = {"from_attributes": True}
