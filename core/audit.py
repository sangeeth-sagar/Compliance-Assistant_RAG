import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from sqlalchemy.orm import Session

from core.models import AuditLog


def log_action(
    db: Session,
    user_id,
    action: str,
    document_id=None,
    filename: str = "",
    risk_level: str = "",
    details: Optional[Dict[str, Any]] = None,
):
    entry = AuditLog(
        user_id=user_id,
        document_id=document_id,
        action=action,
        filename=filename,
        risk_level=risk_level,
        details=details,
    )
    db.add(entry)
    db.commit()


def read_log(db: Session, user_id, limit: int = 100):
    rows = (
        db.query(AuditLog)
        .filter(AuditLog.user_id == user_id)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
        .all()
    )
    return rows
