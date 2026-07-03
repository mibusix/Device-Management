from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import date
from app.database import get_db
from app.models import Device, DeviceFieldValue, DeviceStatus

router = APIRouter(prefix="/api/devices")


class DeviceCreate(BaseModel):
    name: str
    device_type_id: int
    sub_type_id: Optional[int] = None
    sub_location_id: int
    status: str = "正常"
    power_rating: float = 0
    purchase_date: Optional[str] = None
    notes: str = ""
    field_values: dict = {}


class DeviceUpdate(DeviceCreate):
    pass


@router.get("/")
def list_devices(db: Session = Depends(get_db)):
    return db.query(Device).order_by(Device.id.desc()).all()


@router.get("/by-type/{type_id}")
def get_by_type(type_id: int, db: Session = Depends(get_db)):
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
def get_by_location(sub_id: int, db: Session = Depends(get_db)):
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


@router.post("/")
def create_device(data: DeviceCreate, db: Session = Depends(get_db)):
    device = Device(
        name=data.name,
        device_type_id=data.device_type_id,
        sub_type_id=data.sub_type_id,
        sub_location_id=data.sub_location_id,
        status=data.status or DeviceStatus.NORMAL.value,
        power_rating=data.power_rating,
        purchase_date=(
            date.fromisoformat(data.purchase_date) if data.purchase_date else None
        ),
        notes=data.notes,
    )
    db.add(device)
    db.flush()

    for field_id, value in data.field_values.items():
        if value:
            fv = DeviceFieldValue(device_id=device.id, field_id=int(field_id), value=str(value))
            db.add(fv)

    db.commit()
    return {"ok": True, "id": device.id}


@router.put("/{device_id}")
def update_device(device_id: int, data: DeviceUpdate, db: Session = Depends(get_db)):
    device = db.query(Device).get(device_id)
    if not device:
        raise HTTPException(404, "设备不存在")

    device.name = data.name
    device.device_type_id = data.device_type_id
    device.sub_type_id = data.sub_type_id
    device.sub_location_id = data.sub_location_id
    device.status = data.status
    device.power_rating = data.power_rating
    device.purchase_date = (
        date.fromisoformat(data.purchase_date) if data.purchase_date else None
    )
    device.notes = data.notes

    db.query(DeviceFieldValue).filter(
        DeviceFieldValue.device_id == device_id
    ).delete()
    for field_id, value in data.field_values.items():
        if value:
            fv = DeviceFieldValue(device_id=device.id, field_id=int(field_id), value=str(value))
            db.add(fv)

    db.commit()
    return {"ok": True}


@router.delete("/{device_id}")
def delete_device(device_id: int, db: Session = Depends(get_db)):
    device = db.query(Device).get(device_id)
    if not device:
        raise HTTPException(404, "设备不存在")
    db.delete(device)
    db.commit()
    return {"ok": True}


@router.get("/types")
def get_device_types(db: Session = Depends(get_db)):
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
def get_sub_types(type_id: int, db: Session = Depends(get_db)):
    from app.models import DeviceTypeSubType
    subs = db.query(DeviceTypeSubType).filter(
        DeviceTypeSubType.device_type_id == type_id
    ).all()
    return [{"id": s.id, "name": s.name} for s in subs]


@router.get("/locations")
def get_locations(db: Session = Depends(get_db)):
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
def get_sub_location(sub_id: int, db: Session = Depends(get_db)):
    from app.models import SubLocation
    sl = db.query(SubLocation).get(sub_id)
    if not sl:
        raise HTTPException(404)
    return {"id": sl.id, "name": sl.name, "area_id": sl.area_id, "area_name": sl.area.name}
