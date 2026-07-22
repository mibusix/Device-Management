import os
import tempfile

# 使用临时文件作为测试数据库，避免 :memory: 在多连接/多线程下出现空库问题
_test_db_fd, _test_db_path = tempfile.mkstemp(suffix=".db")
os.close(_test_db_fd)

os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest-only")
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_test_db_path}")
os.environ.setdefault("HTTPS", "0")

import pytest
from fastapi.testclient import TestClient

from app.database import Base, engine, init_db
from app.auth import reset_login_rate_limit


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """会话级：确保表已创建并初始化种子数据。"""
    # 触发 app.main 导入（会执行 init_db），然后再次确保表结构和种子数据存在
    from app.main import app  # noqa: F401
    Base.metadata.create_all(bind=engine)
    init_db()
    yield
    Base.metadata.drop_all(bind=engine)
    try:
        os.remove(_test_db_path)
    except OSError:
        pass


@pytest.fixture(autouse=True)
def fresh_db():
    """每个测试前重置数据库并清空限流器，确保测试隔离。"""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    init_db()
    reset_login_rate_limit()
    yield


@pytest.fixture
def client():
    """返回 FastAPI TestClient。"""
    from app.main import app
    return TestClient(app)


@pytest.fixture
def admin_client(client):
    """已登录管理员的 TestClient。"""
    r = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert r.status_code == 200, r.text
    return client


@pytest.fixture
def csrf_token(admin_client):
    """从 Cookie 中提取当前会话的 csrf_token。"""
    cookie_header = admin_client.cookies.get("csrf_token")
    assert cookie_header, "missing csrf_token cookie"
    return cookie_header
