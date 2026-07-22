def _csrf_header(client):
    return {"X-CSRF-Token": client.cookies.get("csrf_token")}


def test_create_user(admin_client):
    r = admin_client.post(
        "/api/users/",
        json={"username": "testuser", "password": "testpass123", "role": "user"},
        headers=_csrf_header(admin_client),
    )
    assert r.status_code == 200, r.text
    assert r.json()["ok"] is True


def test_create_user_empty_password(admin_client):
    r = admin_client.post(
        "/api/users/",
        json={"username": "baduser", "password": "", "role": "user"},
        headers=_csrf_header(admin_client),
    )
    assert r.status_code == 400
    assert "密码至少 6 位" in r.json()["detail"]


def test_change_password(admin_client):
    r = admin_client.post(
        "/api/users/me/password",
        json={"old_password": "admin123", "new_password": "newpass123"},
        headers=_csrf_header(admin_client),
    )
    assert r.status_code == 200, r.text
    assert r.json()["ok"] is True

    # 旧密码已失效
    r = admin_client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert r.status_code == 401

    # 新密码可登录
    r = admin_client.post("/api/auth/login", json={"username": "admin", "password": "newpass123"})
    assert r.status_code == 200


def test_non_admin_cannot_create_user(client):
    # 普通用户/访客未登录，访问用户管理返回 401
    r = client.get("/api/users/")
    assert r.status_code == 401
