from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime, timezone

from app.database import get_db
from app.models import User
from app.auth import get_current_user, require_role, hash_password, verify_password, create_log

router = APIRouter(prefix="/api/users")


class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "user"


class UserUpdate(BaseModel):
    username: str | None = None
    password: str | None = None
    role: str | None = None
    is_active: int | None = None


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


def _validate_password(password: str | None):
    if not password or len(password) < 6:
        raise HTTPException(400, "密码至少 6 位")


@router.get("/")
def list_users(
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    users = db.query(User).order_by(User.id).all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "role": u.role,
            "is_active": u.is_active,
            "must_change_password": bool(u.must_change_password),
            "created_at": u.created_at.strftime("%Y-%m-%d %H:%M") if u.created_at else "",
        }
        for u in users
    ]


@router.post("/")
def create_user(
    data: UserCreate,
    request: Request,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(400, "用户名已存在")
    if data.role not in ("admin", "user", "guest"):
        raise HTTPException(400, "无效的角色")
    _validate_password(data.password)

    user = User(
        username=data.username,
        password_hash=hash_password(data.password),
        role=data.role,
    )
    db.add(user)
    db.flush()
    create_log(
        db, current_user.id, current_user.username,
        "create", "user", user.id, data.username,
        ip_address=request.client.host if request.client else "",
    )
    db.commit()
    return {"ok": True, "id": user.id}


@router.put("/{user_id}")
def update_user(
    user_id: int,
    data: UserUpdate,
    request: Request,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "用户不存在")
    if data.username:
        existing = db.query(User).filter(
            User.username == data.username, User.id != user_id
        ).first()
        if existing:
            raise HTTPException(400, "用户名已存在")
        user.username = data.username
    if data.password is not None:
        _validate_password(data.password)
        user.password_hash = hash_password(data.password)
        # 管理员重置他人密码后也要求对方改密
        user.must_change_password = 1
    if data.role:
        if data.role not in ("admin", "user", "guest"):
            raise HTTPException(400, "无效的角色")
        user.role = data.role
    if data.is_active is not None:
        user.is_active = data.is_active
    user.updated_at = datetime.now(timezone.utc)
    create_log(
        db, current_user.id, current_user.username,
        "update", "user", user_id, user.username,
        ip_address=request.client.host if request.client else "",
    )
    db.commit()
    return {"ok": True}


@router.post("/me/password")
def change_my_password(
    data: ChangePasswordRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """用户自己改密码，改后清除 must_change_password 标志"""
    if not verify_password(data.old_password, current_user.password_hash):
        raise HTTPException(400, "原密码错误")
    if len(data.new_password) < 6:
        raise HTTPException(400, "新密码至少 6 位")
    if data.new_password == data.old_password:
        raise HTTPException(400, "新密码不能与原密码相同")
    current_user.password_hash = hash_password(data.new_password)
    current_user.must_change_password = 0
    current_user.updated_at = datetime.now(timezone.utc)
    create_log(
        db, current_user.id, current_user.username,
        "update", "user_password", current_user.id, current_user.username,
        ip_address=request.client.host if request.client else "",
    )
    db.commit()
    return {"ok": True}


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    request: Request,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    if user_id == current_user.id:
        raise HTTPException(400, "不能删除自己")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "用户不存在")
    name = user.username
    db.delete(user)
    create_log(
        db, current_user.id, current_user.username,
        "delete", "user", user_id, name,
        ip_address=request.client.host if request.client else "",
    )
    db.commit()
    return {"ok": True}
