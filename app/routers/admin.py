from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import require_role
from app.models import OperationLog, TokenBlacklist, User

router = APIRouter(prefix="/api/admin")


@router.post("/cleanup")
def cleanup(
    days: int = Query(90, ge=1, description="保留最近 N 天的操作日志"),
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """清理过期 token 黑名单与旧操作日志。"""
    now = datetime.now(timezone.utc)

    # 删除已过期（jti 对应 token 必然失效）的黑名单记录
    expired_blacklist = db.query(TokenBlacklist).filter(TokenBlacklist.expires_at < now).delete(
        synchronize_session=False
    )

    # 删除 N 天前的操作日志
    cutoff = now - timedelta(days=days)
    old_logs = db.query(OperationLog).filter(OperationLog.created_at < cutoff).delete(
        synchronize_session=False
    )

    db.commit()
    return {
        "ok": True,
        "deleted_token_blacklist": expired_blacklist,
        "deleted_operation_logs": old_logs,
    }
