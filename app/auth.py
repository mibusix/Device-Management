from datetime import datetime, timedelta

from jose import JWTError, jwt
import bcrypt
from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from app.config import SECRET_KEY, HTTPS_ENV
from app.database import get_db

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def get_current_user(request: Request, db: Session = Depends(get_db)):
    # 中间件已解析 token 并设置 state，优先读
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(401, "未登录")
    from app.models import User
    user = db.query(User).get(int(user_id))
    if not user or not user.is_active:
        raise HTTPException(401, "用户不存在或已禁用")
    return user


def get_optional_user(request: Request, db: Session = Depends(get_db)):
    """获取当前用户，不登录也返回 None"""
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        return None
    from app.models import User
    user = db.query(User).get(int(user_id))
    if not user or not user.is_active:
        return None
    return user


def require_role(*roles):
    def checker(current_user=Depends(get_current_user)):
        if current_user.role not in roles:
            raise HTTPException(403, "权限不足")
        return current_user
    return checker


def create_log(
    db: Session,
    user_id: int | None,
    username: str,
    action: str,
    target_type: str,
    target_id: int | None,
    target_name: str = "",
    detail: dict | None = None,
    ip_address: str = "",
):
    from app.models import OperationLog
    log = OperationLog(
        user_id=user_id,
        username=username,
        action=action,
        target_type=target_type,
        target_id=target_id,
        target_name=target_name,
        detail=detail or {},
        ip_address=ip_address,
    )
    db.add(log)


def set_token_cookie(response: Response, token: str):
    response.set_cookie(
        key="token",
        value=token,
        httponly=True,
        max_age=ACCESS_TOKEN_EXPIRE_HOURS * 3600,
        samesite="lax",
        secure=HTTPS_ENV,
    )
