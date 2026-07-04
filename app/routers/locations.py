from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.models import Area, SubLocation, Device, GroupDevice

router = APIRouter(prefix="/api/locations")


class AreaCreate(BaseModel):
    name: str
    description: str = ""


class SubLocationCreate(BaseModel):
    name: str
    area_id: int
    description: str = ""


@router.get("/areas")
def list_areas(db: Session = Depends(get_db)):
    areas = db.query(Area).all()
    result = []
    for a in areas:
        result.append({
            "id": a.id,
            "name": a.name,
            "description": a.description,
            "sub_locations": [
                {"id": sl.id, "name": sl.name} for sl in a.sub_locations
            ],
        })
    return result


@router.post("/areas")
def create_area(data: AreaCreate, db: Session = Depends(get_db)):
    area = Area(name=data.name, description=data.description)
    db.add(area)
    db.commit()
    return {"ok": True, "id": area.id}


@router.put("/areas/{area_id}")
def update_area(area_id: int, data: AreaCreate, db: Session = Depends(get_db)):
    area = db.query(Area).get(area_id)
    if not area:
        raise HTTPException(404, "区域不存在")
    area.name = data.name
    area.description = data.description
    db.commit()
    return {"ok": True}


@router.delete("/areas/{area_id}")
def delete_area(area_id: int, db: Session = Depends(get_db)):
    area = db.query(Area).get(area_id)
    if not area:
        raise HTTPException(404, "区域不存在")
    sub_ids = [sl.id for sl in area.sub_locations]
    device_count = db.query(Device).filter(Device.sub_location_id.in_(sub_ids)).count() if sub_ids else 0
    group_device_count = db.query(GroupDevice).filter(GroupDevice.sub_location_id.in_(sub_ids)).count() if sub_ids else 0
    if device_count > 0 or group_device_count > 0:
        raise HTTPException(400, "该区域下存在关联的设备，无法删除")
    db.delete(area)
    db.commit()
    return {"ok": True}


@router.post("/sub-locations")
def create_sub(data: SubLocationCreate, db: Session = Depends(get_db)):
    sl = SubLocation(name=data.name, area_id=data.area_id, description=data.description)
    db.add(sl)
    db.commit()
    return {"ok": True, "id": sl.id}


@router.put("/sub-locations/{sub_id}")
def update_sub(sub_id: int, data: SubLocationCreate, db: Session = Depends(get_db)):
    sl = db.query(SubLocation).get(sub_id)
    if not sl:
        raise HTTPException(404, "子区域不存在")
    sl.name = data.name
    sl.area_id = data.area_id
    sl.description = data.description
    db.commit()
    return {"ok": True}


@router.delete("/sub-locations/{sub_id}")
def delete_sub(sub_id: int, db: Session = Depends(get_db)):
    sl = db.query(SubLocation).get(sub_id)
    if not sl:
        raise HTTPException(404, "子区域不存在")
    device_count = db.query(Device).filter(Device.sub_location_id == sub_id).count()
    group_device_count = db.query(GroupDevice).filter(GroupDevice.sub_location_id == sub_id).count()
    if device_count > 0 or group_device_count > 0:
        raise HTTPException(400, "该子区域下存在关联的设备，无法删除")
    db.delete(sl)
    db.commit()
    return {"ok": True}
