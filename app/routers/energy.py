from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import date
from app.database import get_db
from app.models import Device, EnergyRecord, MultiSplitEnergy, DeviceType

router = APIRouter(prefix="/api/energy")


class EnergyCreate(BaseModel):
    device_id: int
    power: float
    runtime_hours: float
    record_date: str
    notes: str = ""


class MultiEnergyCreate(EnergyCreate):
    outdoor_temp: Optional[float] = None
    indoor_temp: Optional[float] = None


@router.post("/calculate")
def calculate_energy(data: EnergyCreate, db: Session = Depends(get_db)):
    device = db.query(Device).get(data.device_id)
    if not device:
        raise HTTPException(404, "设备不存在")

    energy_kwh = round(data.power * data.runtime_hours / 1000, 2)
    record = EnergyRecord(
        device_id=data.device_id,
        power=data.power,
        runtime_hours=data.runtime_hours,
        energy_kwh=energy_kwh,
        record_date=date.fromisoformat(data.record_date),
        notes=data.notes,
    )
    db.add(record)
    db.commit()
    return {"ok": True, "energy_kwh": energy_kwh, "id": record.id}


@router.get("/records")
def list_records(db: Session = Depends(get_db)):
    records = db.query(EnergyRecord).order_by(EnergyRecord.created_at.desc()).limit(100).all()
    result = []
    for r in records:
        result.append({
            "id": r.id,
            "device_name": r.device.name,
            "device_type": r.device.device_type.name,
            "power": r.power,
            "runtime_hours": r.runtime_hours,
            "energy_kwh": r.energy_kwh,
            "record_date": str(r.record_date),
            "notes": r.notes,
        })
    return result


@router.delete("/records/{record_id}")
def delete_record(record_id: int, db: Session = Depends(get_db)):
    r = db.query(EnergyRecord).get(record_id)
    if not r:
        raise HTTPException(404)
    db.delete(r)
    db.commit()
    return {"ok": True}


@router.post("/multi/calculate")
def calculate_multi_energy(data: MultiEnergyCreate, db: Session = Depends(get_db)):
    device = db.query(Device).get(data.device_id)
    if not device:
        raise HTTPException(404, "设备不存在")

    energy_kwh = round(data.power * data.runtime_hours / 1000, 2)
    record = MultiSplitEnergy(
        device_id=data.device_id,
        power=data.power,
        runtime_hours=data.runtime_hours,
        energy_kwh=energy_kwh,
        outdoor_temp=data.outdoor_temp,
        indoor_temp=data.indoor_temp,
        record_date=date.fromisoformat(data.record_date),
        notes=data.notes,
    )
    db.add(record)
    db.commit()
    return {"ok": True, "energy_kwh": energy_kwh, "id": record.id}


@router.get("/multi/records")
def list_multi_records(db: Session = Depends(get_db)):
    records = (
        db.query(MultiSplitEnergy)
        .order_by(MultiSplitEnergy.created_at.desc())
        .limit(100)
        .all()
    )
    result = []
    for r in records:
        result.append({
            "id": r.id,
            "device_name": r.device.name,
            "power": r.power,
            "runtime_hours": r.runtime_hours,
            "energy_kwh": r.energy_kwh,
            "outdoor_temp": r.outdoor_temp,
            "indoor_temp": r.indoor_temp,
            "record_date": str(r.record_date),
            "notes": r.notes,
        })
    return result


@router.delete("/multi/records/{record_id}")
def delete_multi_record(record_id: int, db: Session = Depends(get_db)):
    r = db.query(MultiSplitEnergy).get(record_id)
    if not r:
        raise HTTPException(404)
    db.delete(r)
    db.commit()
    return {"ok": True}
