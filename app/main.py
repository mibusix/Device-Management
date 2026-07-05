from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from app.database import init_db
from app.routers import pages, devices, locations, groups, stats, auth, users, logs
from app.auth import verify_token
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
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(logs.router)

PUBLIC_PATHS = {"/login", "/api/auth/login"}

EXEMPT_PREFIXES = ("/static",)


def _is_exempt(path: str) -> bool:
    if path in PUBLIC_PATHS:
        return True
    for prefix in EXEMPT_PREFIXES:
        if path.startswith(prefix):
            return True
    return False


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    if _is_exempt(request.url.path):
        return await call_next(request)

    token = request.cookies.get("token")
    if not token:
        if request.url.path.startswith("/api/"):
            return JSONResponse({"detail": "未登录"}, status_code=401)
        return RedirectResponse("/login", status_code=302)

    payload = verify_token(token)
    if not payload:
        response = (
            RedirectResponse("/login", status_code=302)
            if not request.url.path.startswith("/api/")
            else JSONResponse({"detail": "登录已过期"}, status_code=401)
        )
        response.delete_cookie("token")
        return response

    request.state.user_id = int(payload.get("sub", 0))
    request.state.user_role = payload.get("role", "guest")
    request.state.username = payload.get("username", "")

    return await call_next(request)
