import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, Text, Boolean, Integer, DateTime, ForeignKey, Index,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from core.db import Base


def _utcnow():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(Text, unique=True, nullable=False, index=True)
    hashed_password = Column(Text, nullable=False)
    full_name = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    documents = relationship("Document", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")
    chat_messages = relationship("ChatMessage", back_populates="user", cascade="all, delete-orphan")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(Text, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    user = relationship("User", back_populates="refresh_tokens")


class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    filename = Column(Text, nullable=False)
    source_type = Column(Text)
    page_count = Column(Integer)
    risk_level = Column(Text)
    risk_score = Column(Integer)
    risk_breakdown = Column(JSONB)
    findings = Column(JSONB)
    raw_text = Column(Text)
    redacted_text = Column(Text)
    summary_text = Column(Text)
    memory_summary = Column(Text)
    indexed = Column(Boolean, default=False)
    has_summary = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    user = relationship("User", back_populates="documents")
    audit_logs = relationship("AuditLog", back_populates="document", cascade="all, delete-orphan")
    chat_messages = relationship("ChatMessage", back_populates="document", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_documents_user_id", "user_id"),
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL"))
    action = Column(Text, nullable=False)
    filename = Column(Text)
    risk_level = Column(Text)
    details = Column(JSONB)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    user = relationship("User", back_populates="audit_logs")
    document = relationship("Document", back_populates="audit_logs")

    __table_args__ = (
        Index("ix_audit_logs_user_id", "user_id"),
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    role = Column(Text, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    user = relationship("User", back_populates="chat_messages")
    document = relationship("Document", back_populates="chat_messages")

    __table_args__ = (
        Index("ix_chat_messages_user_id", "user_id"),
        Index("ix_chat_messages_doc_created", "document_id", "created_at"),
    )
