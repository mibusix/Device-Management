from datetime import datetime, timedelta, timezone
import secrets
import time
from threading import Lock

from jose import JWTError, jwt
import bcrypt
from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from app.config import SECRET_KEY, HTTPS_ENV
from app.database import get_db

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

CSRF_COOKIE_NAME = "csrf_token"
CSRF_SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}
CSRF_EXEMPT_PATHS = {"/login", "/api/auth/login"}


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def set_csrf_cookie(response: Response, token: str):
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=token,
        httponly=False,
        max_age=ACCESS_TOKEN_EXPIRE_HOURS * 3600,
        samesite="lax",
        secure=HTTPS_ENV,
        path="/",
    )


def verify_csrf(request: Request) -> bool:
    if request.method in CSRF_SAFE_METHODS or request.url.path in CSRF_EXEMPT_PATHS:
        return True
    cookie = request.cookies.get(CSRF_COOKIE_NAME)
    header = request.headers.get("X-CSRF-Token") or request.headers.get("X-CSRFToken")
    return bool(cookie and header and cookie == header)


class _RateLimiter:
    """进程内简单滑动窗口限流器。多进程/多 worker 场景下每个进程独立计数。"""

    def __init__(self, max_attempts: int = 5, window_seconds: int = 300):
        self.max_attempts = max_attempts
        self.window = window_seconds
        self._store: dict[str, list[float]] = {}
        self._lock = Lock()

    def is_allowed(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            attempts = [t for t in self._store.get(key, []) if now - t < self.window]
            if len(attempts) >= self.max_attempts:
                self._store[key] = attempts
                return False
            attempts.append(now)
            self._store[key] = attempts
            return True


_login_rate_limiter = _RateLimiter()


def check_login_rate_limit(key: str) -> bool:
    return _login_rate_limiter.is_allowed(key)


def reset_login_rate_limit():
    """测试用：清空登录限流计数。"""
    with _login_rate_limiter._lock:
        _login_rate_limiter._store.clear()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode.update({
        "exp": expire,
        "jti": secrets.token_urlsafe(16),
    })
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(token: str, db: Session | None = None):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None

    # 检查 token 是否已被注销
    jti = payload.get("jti")
    if jti:
        from app.models import TokenBlacklist
        if db is None:
            db = next(get_db())
            try:
                blacklisted = db.query(TokenBlacklist).filter(TokenBlacklist.jti == jti).first()
            finally:
                db.close()
        else:
            blacklisted = db.query(TokenBlacklist).filter(TokenBlacklist.jti == jti).first()
        if blacklisted:
            return None
    return payload


def blacklist_token(db: Session, payload: dict):
    """退出时把 token jti 加入黑名单，使其立即失效。"""
    jti = payload.get("jti")
    exp = payload.get("exp")
    if not jti or not exp:
        return
    expires_at = datetime.fromtimestamp(exp, tz=timezone.utc)
    from app.models import TokenBlacklist
    if not db.query(TokenBlacklist).filter(TokenBlacklist.jti == jti).first():
        db.add(TokenBlacklist(jti=jti, expires_at=expires_at))


def is_token_blacklisted(db: Session, jti: str) -> bool:
    from app.models import TokenBlacklist
    return db.query(TokenBlacklist).filter(TokenBlacklist.jti == jti).first() is not None


def get_current_user(request: Request, db: Session = Depends(get_db)):
    # 中间件已解析 token 并设置 state，优先读
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(401, "未登录")
    from app.models import User
    user = db.get(User, int(user_id))
    if not user or not user.is_active:
        raise HTTPException(401, "用户不存在或已禁用")
    return user


def get_optional_user(request: Request, db: Session = Depends(get_db)):
    """获取当前用户，不登录也返回 None"""
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        return None
    from app.models import User
    user = db.get(User, int(user_id))
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
