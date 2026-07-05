from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from app.database import get_db
from app.models import Device, DeviceFieldValue, DeviceStatus, SubLocation, User
from app.auth import get_current_user, require_role, create_log

router = APIRouter(prefix="/api/devices")


class DeviceCreate(BaseModel):
    name: str
    device_type_id: int
    sub_type_id: Optional[int] = None
    sub_location_id: int
    status: str = "正常"
    power_rating: float = 0

    notes: str = ""
    field_values: dict = {}


class DeviceUpdate(DeviceCreate):
    pass


@router.get("/")
def list_devices(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return db.query(Device).order_by(Device.id.desc()).all()


@router.get("/by-type/{type_id}")
def get_by_type(
    type_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    devices = db.query(Device).filter(Device.device_type_id == type_id).all()
    result = []
    for d in devices:
        area_name = d.sub_location.area.name if d.sub_location else ""
        sub_name = d.sub_location.name if d.sub_location else ""
        result.append({
            "id": d.id,
            "name": d.name,
            "area": area_name,
            "sub_location": sub_name,
            "status": d.status,
        })
    return result


@router.get("/by-location/{sub_id}")
def get_by_location(
    sub_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    devices = db.query(Device).filter(Device.sub_location_id == sub_id).all()
    result = []
    for d in devices:
        result.append({
            "id": d.id,
            "name": d.name,
            "type": d.device_type.name,
            "status": d.status,
        })
    return result


@router.get("/counts-by-location")
def counts_by_location(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """一次性返回所有子区域的设备计数 {sub_id: count}，避免 N+1 查询"""
    from sqlalchemy import func as sqlfunc
    rows = db.query(
        Device.sub_location_id,
        sqlfunc.count(Device.id)
    ).group_by(Device.sub_location_id).all()
    return {sid: cnt for sid, cnt in rows if sid is not None}


@router.post("/")
def create_device(
    data: DeviceCreate,
    request: Request,
    current_user: User = Depends(require_role("admin", "user")),
    db: Session = Depends(get_db),
):
    device = Device(
        name=data.name,
        device_type_id=data.device_type_id,
        sub_type_id=data.sub_type_id,
        sub_location_id=data.sub_location_id,
        status=data.status or DeviceStatus.NORMAL.value,
        power_rating=data.power_rating,
        notes=data.notes,
        created_by=current_user.id,
    )
    db.add(device)
    db.flush()

    for field_id, value in data.field_values.items():
        if value is not None and str(value) != '':
            fv = DeviceFieldValue(device_id=device.id, field_id=int(field_id), value=str(value))
            db.add(fv)

    create_log(
        db, current_user.id, current_user.username,
        "create", "device", device.id, data.name,
        ip_address=request.client.host if request.client else "",
    )
    db.commit()
    return {"ok": True, "id": device.id}


@router.put("/{device_id}")
def update_device(
    device_id: int,
    data: DeviceUpdate,
    request: Request,
    current_user: User = Depends(require_role("admin", "user")),
    db: Session = Depends(get_db),
):
    device = db.query(Device).get(device_id)
    if not device:
        raise HTTPException(404, "设备不存在")

    device.name = data.name
    device.device_type_id = data.device_type_id
    device.sub_type_id = data.sub_type_id
    device.sub_location_id = data.sub_location_id
    device.status = data.status
    device.power_rating = data.power_rating
    device.notes = data.notes
    device.updated_by = current_user.id

    db.query(DeviceFieldValue).filter(
        DeviceFieldValue.device_id == device_id
    ).delete()
    for field_id, value in data.field_values.items():
        if value is not None and str(value) != '':
            fv = DeviceFieldValue(device_id=device.id, field_id=int(field_id), value=str(value))
            db.add(fv)

    create_log(
        db, current_user.id, current_user.username,
        "update", "device", device.id, data.name,
        ip_address=request.client.host if request.client else "",
    )
    db.commit()
    return {"ok": True}


@router.delete("/{device_id}")
def delete_device(
    device_id: int,
    request: Request,
    current_user: User = Depends(require_role("admin", "user")),
    db: Session = Depends(get_db),
):
    device = db.query(Device).get(device_id)
    if not device:
        raise HTTPException(404, "设备不存在")
    name = device.name
    db.delete(device)
    create_log(
        db, current_user.id, current_user.username,
        "delete", "device", device_id, name,
        ip_address=request.client.host if request.client else "",
    )
    db.commit()
    return {"ok": True}


@router.get("/types")
def get_device_types(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.models import DeviceType, DeviceTypeSubType, DeviceTypeField
    types = db.query(DeviceType).all()
    result = []
    for t in types:
        result.append({
            "id": t.id,
            "name": t.name,
            "sub_types": [{"id": st.id, "name": st.name} for st in t.sub_types],
            "fields": [
                {"id": f.id, "name": f.field_name, "type": f.field_type,
                 "unit": f.unit, "required": f.required}
                for f in t.fields
            ],
        })
    return result


@router.get("/types/{type_id}/subs")
def get_sub_types(
    type_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.models import DeviceTypeSubType
    subs = db.query(DeviceTypeSubType).filter(
        DeviceTypeSubType.device_type_id == type_id
    ).all()
    return [{"id": s.id, "name": s.name} for s in subs]


@router.get("/locations")
def get_locations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.models import Area
    areas = db.query(Area).all()
    result = []
    for a in areas:
        result.append({
            "id": a.id,
            "name": a.name,
            "sub_locations": [{"id": sl.id, "name": sl.name} for sl in a.sub_locations],
        })
    return result


@router.get("/sub-locations/{sub_id}")
def get_sub_location(
    sub_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.models import SubLocation
    sl = db.query(SubLocation).get(sub_id)
    if not sl:
        raise HTTPException(404)
    return {"id": sl.id, "name": sl.name, "area_id": sl.area_id, "area_name": sl.area.name}


@router.get("/multi-split/devices")
def filter_devices(
    type_id: int,
    area_id: int = None,
    sub_id: int = None,
    status: str = None,
    search: str = "",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """按 type_id 查询设备，支持区域/状态/搜索过滤。
    路由名 multi-split 为历史遗留，实际是通用按类型筛选接口。"""
    q = db.query(Device).filter(Device.device_type_id == type_id)
    if area_id:
        sub_ids = [sl.id for sl in db.query(SubLocation).filter(SubLocation.area_id == area_id).all()]
        q = q.filter(Device.sub_location_id.in_(sub_ids)) if sub_ids else q
    if sub_id:
        q = q.filter(Device.sub_location_id == sub_id)
    if status:
        q = q.filter(Device.status == status)
    if search:
        q = q.filter(
            Device.name.contains(search) |
            Device.notes.contains(search)
        )

    devices = q.order_by(Device.id.desc()).all()
    result = []
    for d in devices:
        fields = {}
        for fv in d.field_values:
            fields[fv.field.field_name] = fv.value
        result.append({
            "id": d.id,
            "name": d.name,
            "device_type_id": d.device_type_id,
            "area_id": d.sub_location.area_id,
            "area": d.sub_location.area.name,
            "sub_location_id": d.sub_location_id,
            "sub_location": d.sub_location.name,
            "status": d.status,
            "power_rating": d.power_rating,
            "notes": d.notes,
            "fields": fields,
        })
    return result
