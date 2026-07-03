from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from app.database import get_db
from app.models import DeviceType, DeviceTypeSubType, DeviceTypeField

router = APIRouter(prefix="/api/types")


class TypeCreate(BaseModel):
    name: str
    description: str = ""


class SubTypeCreate(BaseModel):
    name: str
    device_type_id: int
    description: str = ""


class FieldCreate(BaseModel):
    device_type_id: int
    field_name: str
    field_type: str = "text"
    unit: str = ""
    required: int = 0
    sort_order: int = 0


@router.get("/")
def list_types(db: Session = Depends(get_db)):
    types = db.query(DeviceType).all()
    result = []
    for t in types:
        result.append({
            "id": t.id,
            "name": t.name,
            "description": t.description,
            "sub_types": [
                {"id": st.id, "name": st.name} for st in t.sub_types
            ],
            "fields": [
                {"id": f.id, "name": f.field_name, "type": f.field_type,
                 "unit": f.unit, "required": f.required}
                for f in t.fields
            ],
        })
    return result


@router.post("/")
def create_type(data: TypeCreate, db: Session = Depends(get_db)):
    t = DeviceType(name=data.name, description=data.description)
    db.add(t)
    db.commit()
    return {"ok": True, "id": t.id}


@router.put("/{type_id}")
def update_type(type_id: int, data: TypeCreate, db: Session = Depends(get_db)):
    t = db.query(DeviceType).get(type_id)
    if not t:
        raise HTTPException(404)
    t.name = data.name
    t.description = data.description
    db.commit()
    return {"ok": True}


@router.delete("/{type_id}")
def delete_type(type_id: int, db: Session = Depends(get_db)):
    t = db.query(DeviceType).get(type_id)
    if not t:
        raise HTTPException(404)
    db.delete(t)
    db.commit()
    return {"ok": True}


@router.post("/sub-types")
def create_sub_type(data: SubTypeCreate, db: Session = Depends(get_db)):
    st = DeviceTypeSubType(
        name=data.name,
        device_type_id=data.device_type_id,
        description=data.description,
    )
    db.add(st)
    db.commit()
    return {"ok": True, "id": st.id}


@router.put("/sub-types/{sub_id}")
def update_sub_type(sub_id: int, data: SubTypeCreate, db: Session = Depends(get_db)):
    st = db.query(DeviceTypeSubType).get(sub_id)
    if not st:
        raise HTTPException(404)
    st.name = data.name
    st.description = data.description
    db.commit()
    return {"ok": True}


@router.delete("/sub-types/{sub_id}")
def delete_sub_type(sub_id: int, db: Session = Depends(get_db)):
    st = db.query(DeviceTypeSubType).get(sub_id)
    if not st:
        raise HTTPException(404)
    db.delete(st)
    db.commit()
    return {"ok": True}


@router.post("/fields")
def create_field(data: FieldCreate, db: Session = Depends(get_db)):
    f = DeviceTypeField(
        device_type_id=data.device_type_id,
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
    f = db.query(DeviceTypeField).get(field_id)
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
    f = db.query(DeviceTypeField).get(field_id)
    if not f:
        raise HTTPException(404)
    db.delete(f)
    db.commit()
    return {"ok": True}
