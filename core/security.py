import os
import uuid
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from core.db import get_db
from core.models import User, RefreshToken

JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "change-me-to-a-random-64-char-secret")
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "10"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.environ.get("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

bearer_scheme = HTTPBearer()


def hash_password(password: str) -> str:
    raw = password.encode("utf-8")[:72]
    return bcrypt.hashpw(raw, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    raw = password.encode("utf-8")[:72]
    return bcrypt.checkpw(raw, hashed.encode("utf-8"))


def create_access_token(user_id: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(64)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_refresh_token_record(db: Session, user_id: uuid.UUID) -> tuple[str, RefreshToken]:
    raw_token = generate_refresh_token()
    token_hash = hash_token(raw_token)
    expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    record = RefreshToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return raw_token, record


def revoke_refresh_token(db: Session, token_hash: str):
    record = db.query(RefreshToken).filter(
        RefreshToken.token_hash == token_hash,
        RefreshToken.revoked == False,
    ).first()
    if record:
        record.revoked = True
        db.commit()


def rotate_refresh_token(db: Session, old_token_hash: str) -> tuple[str, RefreshToken]:
    record = db.query(RefreshToken).filter(
        RefreshToken.token_hash == old_token_hash,
        RefreshToken.revoked == False,
    ).first()
    if not record:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    if record.expires_at < datetime.now(timezone.utc):
        record.revoked = True
        db.commit()
        raise HTTPException(status_code=401, detail="Refresh token expired")

    record.revoked = True
    db.commit()

    new_raw, new_record = create_refresh_token_record(db, record.user_id)
    return new_raw, new_record


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    payload = decode_access_token(credentials.credentials)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid user ID in token")

    user = db.query(User).filter(User.id == uid, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return user
