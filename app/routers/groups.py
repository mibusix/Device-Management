from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.models import DeviceGroup, GroupField, GroupDevice, SubLocation

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


class DeviceCreate(BaseModel):
    group_id: int
    area_id: Optional[int] = None
    sub_location_id: Optional[int] = None
    status: str = "正常"
    power_rating: float = 0
    notes: str = ""
    field_values: dict = {}


# --- Groups ---

@router.get("/")
def list_groups(db: Session = Depends(get_db)):
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
def create_group(data: GroupCreate, db: Session = Depends(get_db)):
    g = DeviceGroup(name=data.name, description=data.description)
    db.add(g)
    db.commit()
    return {"ok": True, "id": g.id}


@router.put("/{group_id}")
def update_group(group_id: int, data: GroupCreate, db: Session = Depends(get_db)):
    g = db.query(DeviceGroup).get(group_id)
    if not g:
        raise HTTPException(404)
    g.name = data.name
    g.description = data.description
    db.commit()
    return {"ok": True}


@router.delete("/{group_id}")
def delete_group(group_id: int, db: Session = Depends(get_db)):
    g = db.query(DeviceGroup).get(group_id)
    if not g:
        raise HTTPException(404)
    db.delete(g)
    db.commit()
    return {"ok": True}


# --- Fields ---

@router.post("/fields")
def create_field(data: FieldCreate, db: Session = Depends(get_db)):
    f = GroupField(
        group_id=data.group_id,
        field_name=data.field_name,
        field_type=data.field_type,
        unit=data.unit,
        required=data.required,
        sort_order=data.sort_order,
    )
    db.add(f)
    db.commit()
    return {"ok": True, "id": f.id}


@router.put("/fields/{field_id}")
def update_field(field_id: int, data: FieldCreate, db: Session = Depends(get_db)):
    f = db.query(GroupField).get(field_id)
    if not f:
        raise HTTPException(404)
    f.field_name = data.field_name
    f.field_type = data.field_type
    f.unit = data.unit
    f.required = data.required
    f.sort_order = data.sort_order
    db.commit()
    return {"ok": True}


@router.delete("/fields/{field_id}")
def delete_field(field_id: int, db: Session = Depends(get_db)):
    f = db.query(GroupField).get(field_id)
    if not f:
        raise HTTPException(404)
    db.delete(f)
    db.commit()
    return {"ok": True}


# --- Devices ---

@router.get("/{group_id}/devices")
def list_group_devices(group_id: int, db: Session = Depends(get_db)):
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
    return result


@router.post("/devices")
def create_group_device(data: DeviceCreate, db: Session = Depends(get_db)):
    d = GroupDevice(
        group_id=data.group_id,
        area_id=data.area_id,
        sub_location_id=data.sub_location_id,
        status=data.status,
        power_rating=data.power_rating,
        notes=data.notes,
        field_values=data.field_values,
    )
    db.add(d)
    db.commit()
    return {"ok": True, "id": d.id}


@router.put("/devices/{device_id}")
def update_group_device(device_id: int, data: DeviceCreate, db: Session = Depends(get_db)):
    d = db.query(GroupDevice).get(device_id)
    if not d:
        raise HTTPException(404)
    d.area_id = data.area_id
    d.sub_location_id = data.sub_location_id
    d.status = data.status
    d.power_rating = data.power_rating
    d.notes = data.notes
    d.field_values = data.field_values
    db.commit()
    return {"ok": True}


@router.delete("/devices/{device_id}")
def delete_group_device(device_id: int, db: Session = Depends(get_db)):
    d = db.query(GroupDevice).get(device_id)
    if not d:
        raise HTTPException(404)
    db.delete(d)
    db.commit()
    return {"ok": True}
