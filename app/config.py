import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    f"sqlite:///{os.path.join(BASE_DIR, 'data', 'devices.db')}",
)

SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError(
        "SECRET_KEY 未配置：请在环境变量中设置 SECRET_KEY（用于 JWT 签名）。"
        "例如：export SECRET_KEY=\"$(python3 -c 'import secrets; print(secrets.token_hex(32))')\""
    )

# 生产环境 HTTPS 开关：当设置为 "1" 或 "true" 时，cookie 会带 secure 标志
HTTPS_ENV = os.environ.get("HTTPS", "").lower() in ("1", "true", "yes", "on")
