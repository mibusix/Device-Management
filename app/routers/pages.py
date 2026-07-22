from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import (
    Device, DeviceType, Area, SubLocation, DeviceStatus,
    GroupDevice, DeviceGroup, User,
)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def _user_context(request: Request, db: Session = None):
    """从中间件设置的 state 获取当前用户信息供模板使用"""
    if not db:
        return {"current_user": None}
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        return {"current_user": None}
    user = db.get(User, int(user_id))
    if user and user.is_active:
        return {"current_user": user}
    return {"current_user": None}


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", {"current_user": None})


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    # 系统设备状态聚合：用一次 group_by 代替 4 次 COUNT
    sys_status_counts = dict(
        db.query(Device.status, func.count(Device.id)).group_by(Device.status).all()
    )
    sys_total = sum(sys_status_counts.values())
    sys_normal = sys_status_counts.get(DeviceStatus.NORMAL.value, 0)
    sys_fault = sys_status_counts.get(DeviceStatus.FAULT.value, 0)
    sys_scrapped = sys_status_counts.get(DeviceStatus.SCRAPPED.value, 0)

    # 分组设备状态聚合
    grp_status_counts = dict(
        db.query(GroupDevice.status, func.count(GroupDevice.id)).group_by(GroupDevice.status).all()
    )
    grp_total = sum(grp_status_counts.values())
    grp_normal = grp_status_counts.get("正常", 0)
    grp_fault = grp_status_counts.get("故障", 0)
    grp_scrapped = grp_status_counts.get("报废", 0)

    # 按类型统计：系统设备类型
    all_types = db.query(DeviceType).all()
    type_total = dict(
        db.query(Device.device_type_id, func.count(Device.id))
        .group_by(Device.device_type_id)
        .all()
    )
    type_normal = dict(
        db.query(Device.device_type_id, func.count(Device.id))
        .filter(Device.status == DeviceStatus.NORMAL.value)
        .group_by(Device.device_type_id)
        .all()
    )
    type_stats = [
        {"name": t.name, "total": type_total.get(t.id, 0), "normal": type_normal.get(t.id, 0), "type_id": t.id}
        for t in all_types
        if type_total.get(t.id, 0) > 0
    ]

    # 按分组统计
    all_groups = db.query(DeviceGroup).all()
    group_total = dict(
        db.query(GroupDevice.group_id, func.count(GroupDevice.id))
        .group_by(GroupDevice.group_id)
        .all()
    )
    group_normal = dict(
        db.query(GroupDevice.group_id, func.count(GroupDevice.id))
        .filter(GroupDevice.status == "正常")
        .group_by(GroupDevice.group_id)
        .all()
    )
    group_stats = [
        {"name": g.name, "total": group_total.get(g.id, 0), "normal": group_normal.get(g.id, 0), "type_id": None}
        for g in all_groups
        if group_total.get(g.id, 0) > 0
    ]

    # 按区域统计：系统设备 + 分组设备，避免每个区域一次 COUNT
    areas = db.query(Area).all()
    sub_to_area = {}
    for a in areas:
        for sl in a.sub_locations:
            sub_to_area[sl.id] = a.id

    area_counts = {a.id: 0 for a in areas}
    if sub_to_area:
        sub_ids = list(sub_to_area.keys())
        sys_by_sub = dict(
            db.query(Device.sub_location_id, func.count(Device.id))
            .filter(Device.sub_location_id.in_(sub_ids))
            .group_by(Device.sub_location_id)
            .all()
        )
        grp_by_sub = dict(
            db.query(GroupDevice.sub_location_id, func.count(GroupDevice.id))
            .filter(GroupDevice.sub_location_id.in_(sub_ids))
            .group_by(GroupDevice.sub_location_id)
            .all()
        )
        for sid, cnt in sys_by_sub.items():
            area_counts[sub_to_area.get(sid)] += cnt
        for sid, cnt in grp_by_sub.items():
            area_counts[sub_to_area.get(sid)] += cnt

    area_data = [
        {"name": a.name, "count": area_counts[a.id], "area_id": a.id}
        for a in areas
    ]

    return templates.TemplateResponse(request, "dashboard.html", {
        **_user_context(request, db),
        "total": sys_total + grp_total,
        "normal": sys_normal + grp_normal,
        "fault": sys_fault + grp_fault,
        "scrapped": sys_scrapped + grp_scrapped,
        "type_stats": type_stats,
        "group_stats": group_stats,
        "area_data": area_data,
        "group_count": grp_total,
    })


@router.get("/devices", response_class=HTMLResponse)
def device_stats(request: Request, db: Session = Depends(get_db)):
    areas = db.query(Area).all()
    return templates.TemplateResponse(request, "devices/stats.html", {
        **_user_context(request, db),
        "areas": areas,
    })


@router.get("/devices/add", response_class=HTMLResponse)
def device_add_form(request: Request, db: Session = Depends(get_db)):
    types = db.query(DeviceType).all()
    areas = db.query(Area).all()
    return templates.TemplateResponse(request, "devices/form.html", {
        **_user_context(request, db),
        "types": types,
        "areas": areas,
        "device": None,
        "device_data": None,
    })


@router.get("/devices/{device_id}/edit", response_class=HTMLResponse)
def device_edit_form(request: Request, device_id: int, db: Session = Depends(get_db)):
    device = db.get(Device, device_id)
    if not device:
        raise HTTPException(404, "设备不存在")
    types = db.query(DeviceType).all()
    areas = db.query(Area).all()
    field_values = {fv.field_id: fv.value for fv in device.field_values}
    # 传 dict 而非 SQLAlchemy 对象，避免 tojson 序列化失败
    device_data = {
        "id": device.id,
        "name": device.name,
        "device_type_id": device.device_type_id,
        "sub_type_id": device.sub_type_id,
        "sub_location_id": device.sub_location_id,
        "area_id": device.sub_location.area_id if device.sub_location else None,
        "status": device.status,
        "power_rating": device.power_rating,
        "notes": device.notes or "",
    }
    return templates.TemplateResponse(request, "devices/form.html", {
        **_user_context(request, db),
        "types": types,
        "areas": areas,
        "device": device,
        "device_data": device_data,
        "field_values_json": field_values,
    })


@router.get("/devices/{device_id}", response_class=HTMLResponse)
def device_detail(request: Request, device_id: int, db: Session = Depends(get_db)):
    device = db.get(Device, device_id)
    if not device:
        raise HTTPException(404, "设备不存在")
    return templates.TemplateResponse(request, "devices/detail.html", {
        **_user_context(request, db),
        "device": device,
    })


@router.get("/locations", response_class=HTMLResponse)
def location_list(request: Request, db: Session = Depends(get_db)):
    areas = db.query(Area).all()
    return templates.TemplateResponse(request, "locations/list.html", {
        **_user_context(request, db),
        "areas": areas,
    })


@router.get("/tools", response_class=HTMLResponse)
def tools_page(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(request, "tools/index.html", {
        **_user_context(request, db),
    })


@router.get("/groups", response_class=HTMLResponse)
def groups_page(request: Request, db: Session = Depends(get_db)):
    areas = db.query(Area).all()
    return templates.TemplateResponse(request, "groups/list.html", {
        **_user_context(request, db),
        "areas": areas,
    })


@router.get("/users", response_class=HTMLResponse)
def users_page(request: Request, db: Session = Depends(get_db)):
    ctx = _user_context(request, db)
    user = ctx.get("current_user")
    if not user or user.role != "admin":
        raise HTTPException(403, "仅管理员可访问")
    return templates.TemplateResponse(request, "users/list.html", ctx)


@router.get("/logs", response_class=HTMLResponse)
def logs_page(request: Request, db: Session = Depends(get_db)):
    ctx = _user_context(request, db)
    user = ctx.get("current_user")
    if not user or user.role != "admin":
        raise HTTPException(403, "仅管理员可访问")
    return templates.TemplateResponse(request, "logs/list.html", ctx)
