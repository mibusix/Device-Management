from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.models import Area, SubLocation, Device, GroupDevice, User
from app.auth import get_current_user, require_role, create_log

router = APIRouter(prefix="/api/locations")


class AreaCreate(BaseModel):
    name: str
    description: str = ""


class SubLocationCreate(BaseModel):
    name: str
    area_id: int
    description: str = ""


@router.get("/areas")
def list_areas(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
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
def create_area(
    data: AreaCreate,
    request: Request,
    current_user: User = Depends(require_role("admin", "user")),
    db: Session = Depends(get_db),
):
    area = Area(name=data.name, description=data.description, created_by=current_user.id)
    db.add(area)
    db.flush()
    create_log(
        db, current_user.id, current_user.username,
        "create", "area", area.id, data.name,
        ip_address=request.client.host if request.client else "",
    )
    db.commit()
    return {"ok": True, "id": area.id}


@router.put("/areas/{area_id}")
def update_area(
    area_id: int, data: AreaCreate,
    request: Request,
    current_user: User = Depends(require_role("admin", "user")),
    db: Session = Depends(get_db),
):
    area = db.query(Area).get(area_id)
    if not area:
        raise HTTPException(404, "区域不存在")
    area.name = data.name
    area.description = data.description
    area.updated_by = current_user.id
    create_log(
        db, current_user.id, current_user.username,
        "update", "area", area_id, data.name,
        ip_address=request.client.host if request.client else "",
    )
    db.commit()
    return {"ok": True}


@router.delete("/areas/{area_id}")
def delete_area(
    area_id: int,
    request: Request,
    current_user: User = Depends(require_role("admin", "user")),
    db: Session = Depends(get_db),
):
    area = db.query(Area).get(area_id)
    if not area:
        raise HTTPException(404, "区域不存在")
    sub_ids = [sl.id for sl in area.sub_locations]
    device_count = db.query(Device).filter(Device.sub_location_id.in_(sub_ids)).count() if sub_ids else 0
    group_device_count = db.query(GroupDevice).filter(GroupDevice.sub_location_id.in_(sub_ids)).count() if sub_ids else 0
    if device_count > 0 or group_device_count > 0:
        raise HTTPException(400, "该区域下存在关联的设备，无法删除")
    name = area.name
    db.delete(area)
    create_log(
        db, current_user.id, current_user.username,
        "delete", "area", area_id, name,
        ip_address=request.client.host if request.client else "",
    )
    db.commit()
    return {"ok": True}


@router.post("/sub-locations")
def create_sub(
    data: SubLocationCreate,
    request: Request,
    current_user: User = Depends(require_role("admin", "user")),
    db: Session = Depends(get_db),
):
    sl = SubLocation(name=data.name, area_id=data.area_id, description=data.description, created_by=current_user.id)
    db.add(sl)
    db.flush()
    create_log(
        db, current_user.id, current_user.username,
        "create", "sub_location", sl.id, data.name,
        ip_address=request.client.host if request.client else "",
    )
    db.commit()
    return {"ok": True, "id": sl.id}


@router.put("/sub-locations/{sub_id}")
def update_sub(
    sub_id: int, data: SubLocationCreate,
    request: Request,
    current_user: User = Depends(require_role("admin", "user")),
    db: Session = Depends(get_db),
):
    sl = db.query(SubLocation).get(sub_id)
    if not sl:
        raise HTTPException(404, "子区域不存在")
    sl.name = data.name
    sl.area_id = data.area_id
    sl.description = data.description
    sl.updated_by = current_user.id
    create_log(
        db, current_user.id, current_user.username,
        "update", "sub_location", sub_id, data.name,
        ip_address=request.client.host if request.client else "",
    )
    db.commit()
    return {"ok": True}


@router.delete("/sub-locations/{sub_id}")
def delete_sub(
    sub_id: int,
    request: Request,
    current_user: User = Depends(require_role("admin", "user")),
    db: Session = Depends(get_db),
):
    sl = db.query(SubLocation).get(sub_id)
    if not sl:
        raise HTTPException(404, "子区域不存在")
    device_count = db.query(Device).filter(Device.sub_location_id == sub_id).count()
    group_device_count = db.query(GroupDevice).filter(GroupDevice.sub_location_id == sub_id).count()
    if device_count > 0 or group_device_count > 0:
        raise HTTPException(400, "该子区域下存在关联的设备，无法删除")
    name = sl.name
    db.delete(sl)
    create_log(
        db, current_user.id, current_user.username,
        "delete", "sub_location", sub_id, name,
        ip_address=request.client.host if request.client else "",
    )
    db.commit()
    return {"ok": True}
