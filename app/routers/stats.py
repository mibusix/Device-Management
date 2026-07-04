from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import Device, GroupDevice, SubLocation, DeviceType

router = APIRouter(prefix="/api/stats")


@router.get("/devices")
def get_all_devices(
    search: str = "",
    source: str = "",
    group_type: str = "",
    status: str = "",
    area_id: int = None,
    db: Session = Depends(get_db),
):
    all_devices = []

    # --- Group devices ---
    if not source or source == "group":
        q = db.query(GroupDevice)
        if status:
            q = q.filter(GroupDevice.status == status)
        if area_id:
            q = q.join(GroupDevice.sub_location).filter(SubLocation.area_id == area_id)
        if search:
            # search in field_values JSON (simple approach)
            all_g = q.order_by(GroupDevice.id.desc()).all()
            for g in all_g:
                fv = g.field_values or {}
                name = next((v for v in fv.values() if v), f"分组设备#{g.id}")
                if search.lower() in name.lower() or any(search.lower() in str(v).lower() for v in fv.values()):
                    all_devices.append({
                        "uid": f"g{g.id}", "source": "group",
                        "name": name,
                        "group_type": g.group.name,
                        "area": g.sub_location.area.name if g.sub_location else "",
                        "sub_location": g.sub_location.name if g.sub_location else "",
                        "status": g.status,
                    })
        else:
            all_g = q.order_by(GroupDevice.id.desc()).limit(500).all()
            for g in all_g:
                fv = g.field_values or {}
                name = next((v for v in fv.values() if v), f"分组设备#{g.id}")
                all_devices.append({
                    "uid": f"g{g.id}", "source": "group",
                    "name": name,
                    "group_type": g.group.name,
                    "area": g.sub_location.area.name if g.sub_location else "",
                    "sub_location": g.sub_location.name if g.sub_location else "",
                    "status": g.status,
                })

        # filter by group_type
        if group_type and group_type.startswith("group_"):
            gid = int(group_type.split("_")[1])
            all_devices = [d for d in all_devices if d["uid"].startswith("g") and
                           db.query(GroupDevice).filter(GroupDevice.id == int(d["uid"][1:])).first().group_id == gid]

    # --- Main devices ---
    if not source or source == "main":
        q = db.query(Device)
        if status:
            q = q.filter(Device.status == status)
        if area_id:
            q = q.join(Device.sub_location).filter(SubLocation.area_id == area_id)
        if search:
            q = q.filter(Device.name.contains(search))
        if group_type and group_type.startswith("type_"):
            tid = int(group_type.split("_")[1])
            q = q.filter(Device.device_type_id == tid)

        all_m = q.order_by(Device.id.desc()).limit(500).all()
        for d in all_m:
            all_devices.append({
                "uid": f"m{d.id}", "source": "main",
                "name": d.name,
                "group_type": d.device_type.name,
                "area": d.sub_location.area.name if d.sub_location else "",
                "sub_location": d.sub_location.name if d.sub_location else "",
                "status": d.status,
            })

    # Stats
    total = len(all_devices)
    normal = sum(1 for d in all_devices if d["status"] == "正常")
    fault = sum(1 for d in all_devices if d["status"] == "故障")
    scrapped = sum(1 for d in all_devices if d["status"] == "报废")

    return {
        "total": total,
        "normal": normal,
        "fault": fault,
        "scrapped": scrapped,
        "devices": all_devices,
    }
