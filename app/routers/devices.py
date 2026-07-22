from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.models import Device, DeviceFieldValue, DeviceStatus, DeviceType, DeviceTypeSubType, SubLocation, User
from app.auth import get_current_user, require_role, create_log
from app.pagination import paginate

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


_VALID_DEVICE_STATUSES = {s.value for s in DeviceStatus}


def _validate_device_payload(db: Session, data: DeviceCreate):
    """把非法的系统设备输入从 500 转成 422/400。"""
    device_type = db.get(DeviceType, data.device_type_id)
    if not device_type:
        raise HTTPException(400, "设备类型不存在")

    sub_location = db.get(SubLocation, data.sub_location_id)
    if not sub_location:
        raise HTTPException(400, "位置不存在")

    if data.sub_type_id is not None:
        sub_type = db.get(DeviceTypeSubType, data.sub_type_id)
        if not sub_type or sub_type.device_type_id != data.device_type_id:
            raise HTTPException(400, "子类型不存在或不属于该设备类型")

    if data.status not in _VALID_DEVICE_STATUSES:
        raise HTTPException(400, f"无效状态：{data.status}")

    if data.field_values:
        valid_field_ids = {f.id for f in device_type.fields}
        for field_id in data.field_values.keys():
            try:
                fid = int(field_id)
            except (ValueError, TypeError):
                raise HTTPException(400, f"字段 ID 必须是整数：{field_id}")
            if fid not in valid_field_ids:
                raise HTTPException(400, f"字段不存在：{field_id}")


@router.get("/")
def list_devices(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    devices = db.query(Device).order_by(Device.id.desc()).all()
    return paginate(devices, page, page_size)


@router.get("/{device_id}")
def get_device(
    device_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    device = db.get(Device, device_id)
    if not device:
        raise HTTPException(404, "设备不存在")
    fields = {fv.field_id: fv.value for fv in device.field_values}
    return {
        "id": device.id,
        "name": device.name,
        "device_type_id": device.device_type_id,
        "sub_type_id": device.sub_type_id,
        "sub_location_id": device.sub_location_id,
        "area_id": device.sub_location.area_id if device.sub_location else None,
        "status": device.status,
        "power_rating": device.power_rating,
        "notes": device.notes,
        "field_values": fields,
    }


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
    _validate_device_payload(db, data)
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
    device = db.get(Device, device_id)
    if not device:
        raise HTTPException(404, "设备不存在")
    _validate_device_payload(db, data)

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
    device = db.get(Device, device_id)
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
    sl = db.get(SubLocation, sub_id)
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
