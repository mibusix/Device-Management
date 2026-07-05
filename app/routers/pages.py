from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import (
    Device, DeviceType, Area, SubLocation, DeviceStatus,
    GroupDevice, DeviceGroup, User,
)
from app.auth import get_optional_user

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def _user_context(request: Request, db: Session = None):
    """从中间件设置的 state 获取当前用户信息供模板使用"""
    if not db:
        return {"current_user": None}
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        return {"current_user": None}
    user = db.query(User).get(int(user_id))
    if user and user.is_active:
        return {"current_user": user}
    return {"current_user": None}


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", {"current_user": None})


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    sys_total = db.query(Device).count()
    sys_normal = db.query(Device).filter(Device.status == DeviceStatus.NORMAL.value).count()
    sys_fault = db.query(Device).filter(Device.status == DeviceStatus.FAULT.value).count()
    sys_scrapped = db.query(Device).filter(Device.status == DeviceStatus.SCRAPPED.value).count()

    grp_total = db.query(GroupDevice).count()
    grp_normal = db.query(GroupDevice).filter(GroupDevice.status == "正常").count()
    grp_fault = db.query(GroupDevice).filter(GroupDevice.status == "故障").count()
    grp_scrapped = db.query(GroupDevice).filter(GroupDevice.status == "报废").count()

    # 按类型统计：系统设备类型 + 分组设备类型
    type_stats = []
    all_types = db.query(DeviceType).all()
    for t in all_types:
        total = db.query(Device).filter(Device.device_type_id == t.id).count()
        if total > 0:
            n = db.query(Device).filter(
                Device.device_type_id == t.id, Device.status == DeviceStatus.NORMAL.value
            ).count()
            type_stats.append({"name": t.name, "total": total, "normal": n, "type_id": t.id})

    all_groups = db.query(DeviceGroup).all()
    group_stats = []
    for g in all_groups:
        total = db.query(GroupDevice).filter(GroupDevice.group_id == g.id).count()
        if total > 0:
            n = db.query(GroupDevice).filter(
                GroupDevice.group_id == g.id, GroupDevice.status == "正常"
            ).count()
            group_stats.append({"name": g.name, "total": total, "normal": n, "type_id": None})

    # 按区域统计：系统设备 + 分组设备
    areas = db.query(Area).all()
    area_data = []
    for a in areas:
        ids = [sl.id for sl in a.sub_locations]
        if ids:
            sys_cnt = db.query(Device).filter(Device.sub_location_id.in_(ids)).count()
            grp_cnt = db.query(GroupDevice).filter(GroupDevice.sub_location_id.in_(ids)).count()
            cnt = sys_cnt + grp_cnt
        else:
            cnt = 0
        area_data.append({"name": a.name, "count": cnt, "area_id": a.id})

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
    device = db.query(Device).get(device_id)
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
    device = db.query(Device).get(device_id)
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
