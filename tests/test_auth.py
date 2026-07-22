import pytest


def test_login_success(client):
    r = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["user"]["username"] == "admin"
    assert "token" in {c.name for c in client.cookies.jar}
    assert "csrf_token" in {c.name for c in client.cookies.jar}


def test_login_wrong_password(client):
    r = client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
    assert r.status_code == 401
    assert "detail" in r.json()


def test_login_rate_limit(client):
    # 连续失败 5 次后第 6 次应被限流
    for _ in range(5):
        r = client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
        assert r.status_code == 401
    r = client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
    assert r.status_code == 429


def test_logout_requires_csrf(admin_client, csrf_token):
    r = admin_client.post("/api/auth/logout")
    assert r.status_code == 403
    assert "CSRF" in r.json()["detail"]

    r = admin_client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf_token})
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_logout_blacklists_token(admin_client, csrf_token):
    r = admin_client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf_token})
    assert r.status_code == 200

    # 原 token 应立即失效
    r = admin_client.get("/api/stats/devices")
    assert r.status_code == 401


def test_me(admin_client):
    r = admin_client.get("/api/auth/me")
    assert r.status_code == 200
    assert r.json()["username"] == "admin"
