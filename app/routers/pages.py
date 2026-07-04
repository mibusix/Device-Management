from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import (
    Device, DeviceType, Area, SubLocation,
    EnergyRecord, DeviceStatus
)

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    devices = db.query(Device).count()
    normal = db.query(Device).filter(Device.status == DeviceStatus.NORMAL.value).count()
    fault = db.query(Device).filter(Device.status == DeviceStatus.FAULT.value).count()
    scrapped = db.query(Device).filter(Device.status == DeviceStatus.SCRAPPED.value).count()

    all_types = db.query(DeviceType).all()
    type_stats = []
    for t in all_types:
        total = db.query(Device).filter(Device.device_type_id == t.id).count()
        if total > 0:
            n = db.query(Device).filter(
                Device.device_type_id == t.id, Device.status == DeviceStatus.NORMAL.value
            ).count()
            type_stats.append({"name": t.name, "total": total, "normal": n, "type_id": t.id})

    areas = db.query(Area).all()
    area_data = []
    for a in areas:
        ids = [sl.id for sl in a.sub_locations]
        cnt = db.query(Device).filter(Device.sub_location_id.in_(ids)).count() if ids else 0
        area_data.append({"name": a.name, "count": cnt, "area_id": a.id})

    total_energy = db.query(func.sum(EnergyRecord.energy_kwh)).scalar() or 0

    return templates.TemplateResponse(request, "dashboard.html", {
        "total": devices,
        "normal": normal,
        "fault": fault,
        "scrapped": scrapped,
        "type_stats": type_stats,
        "area_data": area_data,
        "total_energy": round(total_energy, 2),
    })


@router.get("/devices", response_class=HTMLResponse)
def device_list(
    request: Request,
    type_id: int = None,
    status: str = None,
    area_id: int = None,
    search: str = "",
    db: Session = Depends(get_db),
):
    q = db.query(Device)
    if type_id:
        q = q.filter(Device.device_type_id == type_id)
    if status:
        q = q.filter(Device.status == status)
    if area_id:
        sub_ids = [sl.id for sl in db.query(SubLocation).filter(SubLocation.area_id == area_id).all()]
        q = q.filter(Device.sub_location_id.in_(sub_ids)) if sub_ids else q
    if search:
        q = q.filter(Device.name.contains(search))

    devices = q.order_by(Device.id.desc()).all()
    all_types = db.query(DeviceType).all()
    all_areas = db.query(Area).all()

    return templates.TemplateResponse(request, "devices/list.html", {
        "devices": devices,
        "types": all_types,
        "areas": all_areas,
        "filter_type": type_id,
        "filter_status": status,
        "filter_area": area_id,
        "search": search,
    })


@router.get("/devices/add", response_class=HTMLResponse)
def device_add_form(request: Request, db: Session = Depends(get_db)):
    types = db.query(DeviceType).all()
    areas = db.query(Area).all()
    return templates.TemplateResponse(request, "devices/form.html", {
        "types": types,
        "areas": areas,
        "device": None,
    })


@router.get("/devices/{device_id}/edit", response_class=HTMLResponse)
def device_edit_form(request: Request, device_id: int, db: Session = Depends(get_db)):
    device = db.query(Device).get(device_id)
    types = db.query(DeviceType).all()
    areas = db.query(Area).all()
    return templates.TemplateResponse(request, "devices/form.html", {
        "types": types,
        "areas": areas,
        "device": device,
    })


@router.get("/devices/{device_id}", response_class=HTMLResponse)
def device_detail(request: Request, device_id: int, db: Session = Depends(get_db)):
    device = db.query(Device).get(device_id)
    return templates.TemplateResponse(request, "devices/detail.html", {
        "device": device,
    })


@router.get("/locations", response_class=HTMLResponse)
def location_list(request: Request, db: Session = Depends(get_db)):
    areas = db.query(Area).all()
    return templates.TemplateResponse(request, "locations/list.html", {
        "areas": areas,
    })


@router.get("/energy", response_class=HTMLResponse)
def energy_page(request: Request, db: Session = Depends(get_db)):
    types = db.query(DeviceType).all()
    records = (
        db.query(EnergyRecord)
        .order_by(EnergyRecord.created_at.desc())
        .limit(100)
        .all()
    )
    return templates.TemplateResponse(request, "energy/list.html", {
        "types": types,
        "records": records,
        "multi": False,
    })


@router.get("/groups", response_class=HTMLResponse)
def groups_page(request: Request, db: Session = Depends(get_db)):
    areas = db.query(Area).all()
    return templates.TemplateResponse(request, "groups/list.html", {
        "areas": areas,
    })


@router.get("/types", response_class=HTMLResponse)
def types_page(request: Request):
    return templates.TemplateResponse(request, "types/list.html")
