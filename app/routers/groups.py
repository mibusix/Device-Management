from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.models import Area, DeviceGroup, GroupField, GroupDevice, SubLocation, User
from app.auth import get_current_user, require_role, create_log
from app.pagination import paginate

router = APIRouter(prefix="/api/groups")


class GroupCreate(BaseModel):
    name: str
    description: str = ""


class FieldCreate(BaseModel):
    group_id: int
    field_name: str
    field_type: str = "text"
    unit: str = ""
    required: int = 0
    sort_order: int = 0


class FieldItem(BaseModel):
    id: int | None = None
    field_name: str
    field_type: str = "text"
    unit: str = ""
    required: int = 0
    sort_order: int = 0


class FieldBatchUpdate(BaseModel):
    fields: list[FieldItem]


class DeviceCreate(BaseModel):
    group_id: int
    area_id: Optional[int] = None
    sub_location_id: Optional[int] = None
    status: str = "正常"
    power_rating: float = 0
    notes: str = ""
    field_values: dict = {}


_VALID_GROUP_STATUSES = {"正常", "故障", "报废"}


def _validate_group_device_payload(db: Session, data: DeviceCreate):
    group = db.get(DeviceGroup, data.group_id)
    if not group:
        raise HTTPException(400, "分组不存在")
    if data.area_id is not None:
        area = db.get(Area, data.area_id)
        if not area:
            raise HTTPException(400, "大区域不存在")
    if data.sub_location_id is not None:
        sub = db.get(SubLocation, data.sub_location_id)
        if not sub:
            raise HTTPException(400, "子区域不存在")
        if data.area_id is not None and sub.area_id != data.area_id:
            raise HTTPException(400, "子区域不属于所选大区域")
    if data.status not in _VALID_GROUP_STATUSES:
        raise HTTPException(400, f"无效状态：{data.status}")
    if data.field_values:
        valid_names = {f.field_name for f in group.fields}
        for name in data.field_values.keys():
            if name not in valid_names:
                raise HTTPException(400, f"字段不存在：{name}")


@router.get("/")
def list_groups(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    groups = db.query(DeviceGroup).order_by(DeviceGroup.sort_order).all()
    result = []
    for g in groups:
        result.append({
            "id": g.id,
            "name": g.name,
            "description": g.description,
            "sort_order": g.sort_order,
            "fields": [
                {"id": f.id, "name": f.field_name, "type": f.field_type,
                 "unit": f.unit, "required": f.required}
                for f in g.fields
            ],
            "device_count": len(g.devices),
        })
    return result


@router.post("/")
def create_group(
    data: GroupCreate,
    request: Request,
    current_user: User = Depends(require_role("admin", "user")),
    db: Session = Depends(get_db),
):
    g = DeviceGroup(name=data.name, description=data.description, created_by=current_user.id)
    db.add(g)
    db.flush()
    create_log(
        db, current_user.id, current_user.username,
        "create", "group", g.id, data.name,
        ip_address=request.client.host if request.client else "",
    )
    db.commit()
    return {"ok": True, "id": g.id}


@router.put("/{group_id}")
def update_group(
    group_id: int, data: GroupCreate,
    request: Request,
    current_user: User = Depends(require_role("admin", "user")),
    db: Session = Depends(get_db),
):
    g = db.get(DeviceGroup, group_id)
    if not g:
        raise HTTPException(404)
    g.name = data.name
    g.description = data.description
    g.updated_by = current_user.id
    create_log(
        db, current_user.id, current_user.username,
        "update", "group", group_id, data.name,
        ip_address=request.client.host if request.client else "",
    )
    db.commit()
    return {"ok": True}


@router.delete("/{group_id}")
def delete_group(
    group_id: int,
    request: Request,
    current_user: User = Depends(require_role("admin", "user")),
    db: Session = Depends(get_db),
):
    g = db.get(DeviceGroup, group_id)
    if not g:
        raise HTTPException(404)
    name = g.name
    db.delete(g)
    create_log(
        db, current_user.id, current_user.username,
        "delete", "group", group_id, name,
        ip_address=request.client.host if request.client else "",
    )
    db.commit()
    return {"ok": True}


@router.post("/fields")
def create_field(
    data: FieldCreate,
    request: Request,
    current_user: User = Depends(require_role("admin", "user")),
    db: Session = Depends(get_db),
):
    f = GroupField(
        group_id=data.group_id,
        field_name=data.field_name,
        field_type=data.field_type,
        unit=data.unit,
        required=data.required,
        sort_order=data.sort_order,
    )
    db.add(f)
    db.flush()
    create_log(
        db, current_user.id, current_user.username,
        "create", "group_field", f.id, data.field_name,
        ip_address=request.client.host if request.client else "",
    )
    db.commit()
    return {"ok": True, "id": f.id}


@router.put("/fields/{field_id}")
def update_field(
    field_id: int, data: FieldCreate,
    request: Request,
    current_user: User = Depends(require_role("admin", "user")),
    db: Session = Depends(get_db),
):
    f = db.get(GroupField, field_id)
    if not f:
        raise HTTPException(404)
    f.field_name = data.field_name
    f.field_type = data.field_type
    f.unit = data.unit
    f.required = data.required
    f.sort_order = data.sort_order
    create_log(
        db, current_user.id, current_user.username,
        "update", "group_field", field_id, data.field_name,
        ip_address=request.client.host if request.client else "",
    )
    db.commit()
    return {"ok": True}


@router.delete("/fields/{field_id}")
def delete_field(
    field_id: int,
    request: Request,
    current_user: User = Depends(require_role("admin", "user")),
    db: Session = Depends(get_db),
):
    f = db.get(GroupField, field_id)
    if not f:
        raise HTTPException(404)
    name = f.field_name
    db.delete(f)
    create_log(
        db, current_user.id, current_user.username,
        "delete", "group_field", field_id, name,
        ip_address=request.client.host if request.client else "",
    )
    db.commit()
    return {"ok": True}


@router.put("/{group_id}/fields/batch")
def batch_update_fields(
    group_id: int,
    data: FieldBatchUpdate,
    request: Request,
    current_user: User = Depends(require_role("admin", "user")),
    db: Session = Depends(get_db),
):
    """批量更新分组的字段：增量更新（按 id），重命名时同步迁移 GroupDevice.field_values 的 key"""
    g = db.get(DeviceGroup, group_id)
    if not g:
        raise HTTPException(404, "分组不存在")

    existing = {f.id: f for f in db.query(GroupField).filter(GroupField.group_id == group_id).all()}
    seen_ids = set()
    new_fields = []

    for i, item in enumerate(data.fields):
        if not item.field_name:
            continue
        if item.id and item.id in existing:
            f = existing[item.id]
            old_name = f.field_name
            f.field_name = item.field_name
            f.field_type = item.field_type
            f.unit = item.unit
            f.required = item.required
            f.sort_order = i
            seen_ids.add(item.id)
            # 重命名时迁移 GroupDevice.field_values 的 key
            if old_name != item.field_name:
                for d in db.query(GroupDevice).filter(GroupDevice.group_id == group_id).all():
                    fv = dict(d.field_values or {})
                    if old_name in fv:
                        fv[item.field_name] = fv.pop(old_name)
                        d.field_values = fv
                        flag_modified(d, "field_values")
        else:
            new_fields.append((item, i))

    # 删除不在列表里的旧字段，并清理对应 GroupDevice.field_values
    for fid, f in existing.items():
        if fid not in seen_ids:
            old_name = f.field_name
            db.delete(f)
            for d in db.query(GroupDevice).filter(GroupDevice.group_id == group_id).all():
                fv = dict(d.field_values or {})
                if old_name in fv:
                    fv.pop(old_name, None)
                    d.field_values = fv
                    flag_modified(d, "field_values")

    # 新建
    for item, i in new_fields:
        f = GroupField(
            group_id=group_id,
            field_name=item.field_name,
            field_type=item.field_type,
            unit=item.unit,
            required=item.required,
            sort_order=i,
        )
        db.add(f)

    create_log(
        db, current_user.id, current_user.username,
        "update", "group_fields", group_id, g.name,
        ip_address=request.client.host if request.client else "",
    )
    db.commit()
    return {"ok": True}


@router.get("/{group_id}/devices")
def list_group_devices(
    group_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    devices = db.query(GroupDevice).filter(
        GroupDevice.group_id == group_id
    ).order_by(GroupDevice.id.desc()).all()
    result = []
    for d in devices:
        fv = d.field_values or {}
        aid = d.area_id or (d.sub_location.area_id if d.sub_location else None)
        area_name = d.area.name if d.area else (d.sub_location.area.name if d.sub_location else "")
        result.append({
            "id": d.id,
            "group_id": d.group_id,
            "area_id": aid,
            "area": area_name,
            "sub_location_id": d.sub_location_id,
            "sub_location": d.sub_location.name if d.sub_location else "",
            "status": d.status,
            "power_rating": d.power_rating,
            "notes": d.notes,
            "field_values": fv,
        })
    return paginate(result, page, page_size)


@router.post("/devices")
def create_group_device(
    data: DeviceCreate,
    request: Request,
    current_user: User = Depends(require_role("admin", "user")),
    db: Session = Depends(get_db),
):
    _validate_group_device_payload(db, data)
    d = GroupDevice(
        group_id=data.group_id,
        area_id=data.area_id,
        sub_location_id=data.sub_location_id,
        status=data.status,
        power_rating=data.power_rating,
        notes=data.notes,
        field_values=data.field_values,
        created_by=current_user.id,
    )
    db.add(d)
    db.flush()
    name = next((v for v in (data.field_values or {}).values() if v), f"分组设备#{d.id}")
    create_log(
        db, current_user.id, current_user.username,
        "create", "group_device", d.id, str(name),
        ip_address=request.client.host if request.client else "",
    )
    db.commit()
    return {"ok": True, "id": d.id}


@router.put("/devices/{device_id}")
def update_group_device(
    device_id: int, data: DeviceCreate,
    request: Request,
    current_user: User = Depends(require_role("admin", "user")),
    db: Session = Depends(get_db),
):
    d = db.get(GroupDevice, device_id)
    if not d:
        raise HTTPException(404)
    _validate_group_device_payload(db, data)
    d.area_id = data.area_id
    d.sub_location_id = data.sub_location_id
    d.status = data.status
    d.power_rating = data.power_rating
    d.notes = data.notes
    d.field_values = data.field_values
    d.updated_by = current_user.id
    name = next((v for v in (data.field_values or {}).values() if v), f"分组设备#{device_id}")
    create_log(
        db, current_user.id, current_user.username,
        "update", "group_device", device_id, str(name),
        ip_address=request.client.host if request.client else "",
    )
    db.commit()
    return {"ok": True}


@router.delete("/devices/{device_id}")
def delete_group_device(
    device_id: int,
    request: Request,
    current_user: User = Depends(require_role("admin", "user")),
    db: Session = Depends(get_db),
):
    d = db.get(GroupDevice, device_id)
    if not d:
        raise HTTPException(404)
    fv = d.field_values or {}
    name = next((v for v in fv.values() if v), f"分组设备#{device_id}")
    db.delete(d)
    create_log(
        db, current_user.id, current_user.username,
        "delete", "group_device", device_id, str(name),
        ip_address=request.client.host if request.client else "",
    )
    db.commit()
    return {"ok": True}
