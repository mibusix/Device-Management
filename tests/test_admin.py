from datetime import datetime, timedelta, timezone


def _csrf_header(client):
    return {"X-CSRF-Token": client.cookies.get("csrf_token")}


def test_cleanup(admin_client):
    from app.database import SessionLocal
    from app.models import TokenBlacklist, OperationLog

    db = SessionLocal()
    now = datetime.now(timezone.utc)
    db.add(TokenBlacklist(jti="expired-jti", expires_at=now - timedelta(hours=1)))
    db.add(TokenBlacklist(jti="valid-jti", expires_at=now + timedelta(hours=1)))
    db.add(OperationLog(action="create", target_type="test", created_at=now - timedelta(days=100)))
    db.add(OperationLog(action="create", target_type="test", created_at=now - timedelta(days=1)))
    db.commit()

    r = admin_client.post(
        "/api/admin/cleanup?days=30",
        headers=_csrf_header(admin_client),
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["ok"] is True
    assert data["deleted_token_blacklist"] == 1
    assert data["deleted_operation_logs"] == 1

    # 验证只删了旧的（注意 admin_client 登录本身会写一条 operation_log）
    assert db.query(TokenBlacklist).count() == 1
    assert db.query(OperationLog).count() == 2
