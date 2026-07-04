from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.database import init_db
from app.routers import pages, devices, locations, groups, stats
import os

init_db()

app = FastAPI(title="设备管理系统")

app.mount("/static", StaticFiles(directory="app/static"), name="static") if os.path.exists("app/static") else None

app.include_router(pages.router)
app.include_router(devices.router)
app.include_router(locations.router)
app.include_router(groups.router)
app.include_router(stats.router)
