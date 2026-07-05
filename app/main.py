from fastapi import FastAPI, Request
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from app.database import init_db
from app.routers import pages, devices, locations, groups, stats
import os
import secrets
import base64
from typing import Optional

init_db()

app = FastAPI(title="设备管理系统")

app.mount("/static", StaticFiles(directory="app/static"), name="static") if os.path.exists("app/static") else None

app.include_router(pages.router)
app.include_router(devices.router)
app.include_router(locations.router)
app.include_router(groups.router)
app.include_router(stats.router)


def _parse_basic_auth(header: str) -> Optional[tuple]:
    """解析 Authorization: Basic <base64> 头，返回 (user, password) 或 None。"""
    try:
        scheme, _, token = header.partition(" ")
        if scheme.lower() != "basic" or not token:
            return None
        decoded = base64.b64decode(token).decode("utf-8")
        user, _, password = decoded.partition(":")
        return user, password
    except Exception:
        return None


@app.middleware("http")
async def basic_auth_middleware(request: Request, call_next):
    auth_user = os.environ.get("AUTH_USER")
    auth_password = os.environ.get("AUTH_PASSWORD")
    # 未配置凭据则跳过认证
    if not auth_user or not auth_password:
        return await call_next(request)
    provided = _parse_basic_auth(request.headers.get("authorization", ""))
    # 用 compare_digest 防时序攻击；用户名和密码都要匹配
    ok = (
        provided is not None
        and secrets.compare_digest(provided[0], auth_user)
        and secrets.compare_digest(provided[1], auth_password)
    )
    if not ok:
        return Response(
            "Unauthorized",
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="device-management"'},
        )
    return await call_next(request)
