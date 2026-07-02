from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.db import get_db
from core.models import User, AuditLog, RefreshToken
from core.schemas import (
    UserRegister, UserLogin, UserOut, TokenPair,
    RefreshRequest, LogoutRequest,
)
from core.security import (
    hash_password, verify_password, create_access_token,
    create_refresh_token_record, rotate_refresh_token,
    revoke_refresh_token, hash_token, get_current_user,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=201)
def register(body: UserRegister, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenPair)
def login(body: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=401, detail="Account disabled")

    access_token = create_access_token(str(user.id))
    refresh_raw, _ = create_refresh_token_record(db, user.id)

    log = AuditLog(user_id=user.id, action="login", details={"email": body.email})
    db.add(log)
    db.commit()

    return TokenPair(access_token=access_token, refresh_token=refresh_raw)


@router.post("/refresh", response_model=TokenPair)
def refresh(body: RefreshRequest, db: Session = Depends(get_db)):
    old_hash = hash_token(body.refresh_token)
    new_raw, new_record = rotate_refresh_token(db, old_hash)

    user = db.query(User).filter(User.id == new_record.user_id).first()
    if not user:
        raise HTTPException(status_code=500, detail="Could not load user after refresh")

    access_token = create_access_token(str(user.id))
    return TokenPair(access_token=access_token, refresh_token=new_raw)


@router.post("/logout")
def logout(body: LogoutRequest, db: Session = Depends(get_db)):
    revoke_refresh_token(db, hash_token(body.refresh_token))
    return {"detail": "Logged out"}


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user
