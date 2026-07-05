from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models import User
from app.auth import (
    verify_password, create_access_token, get_current_user,
    set_token_cookie, verify_token, create_log,
)

router = APIRouter(prefix="/api/auth")


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
def login(data: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == data.username).first()
    ip = request.client.host if request.client else ""
    if not user or not verify_password(data.password, user.password_hash):
        # 登录失败也记录（target_id 用 0 表示未知用户）
        create_log(
            db, user.id if user else None, data.username,
            "login_failed", "user", user.id if user else None, data.username,
            ip_address=ip,
        )
        db.commit()
        raise HTTPException(401, "用户名或密码错误")
    if not user.is_active:
        create_log(
            db, user.id, user.username,
            "login_failed", "user", user.id, user.username,
            detail={"reason": "disabled"},
            ip_address=ip,
        )
        db.commit()
        raise HTTPException(403, "账号已被禁用")

    token = create_access_token({
        "sub": str(user.id),
        "role": user.role,
        "username": user.username,
    })
    set_token_cookie(response, token)
    create_log(
        db, user.id, user.username,
        "login", "user", user.id, user.username,
        ip_address=ip,
    )
    db.commit()
    return {
        "ok": True,
        "user": {
            "id": user.id,
            "username": user.username,
            "role": user.role,
            "must_change_password": bool(user.must_change_password),
        }
    }


@router.post("/logout")
def logout(response: Response, request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    create_log(
        db, current_user.id, current_user.username,
        "logout", "user", current_user.id, current_user.username,
        ip_address=request.client.host if request.client else "",
    )
    db.commit()
    response.delete_cookie("token")
    return {"ok": True}


@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "role": current_user.role,
        "is_active": current_user.is_active,
        "must_change_password": bool(current_user.must_change_password),
    }
