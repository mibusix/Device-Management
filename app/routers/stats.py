from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models import Device, GroupDevice, SubLocation, DeviceType, DeviceGroup, User
from app.auth import get_current_user
from app.pagination import paginate

router = APIRouter(prefix="/api/stats")


@router.get("/devices")
def get_all_devices(
    search: str = "",
    source: str = "",
    group_type: str = "",
    status: str = "",
    area_id: int = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=500),
    current_user: User = Depends(get_current_user),
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
        if group_type and group_type.startswith("group_"):
            try:
                gid = int(group_type.split("_", 1)[1])
                q = q.filter(GroupDevice.group_id == gid)
            except (IndexError, ValueError):
                pass
        def _group_name(g):
            fv = g.field_values or {}
            return next((v for v in fv.values() if v), f"分组设备#{g.id}")

        if search:
            # 先在 SQL 层面用其他条件过滤，再在 Python 中按 field_values 匹配，最后 limit
            all_g = q.order_by(GroupDevice.id.desc()).all()
            matched = []
            for g in all_g:
                name = _group_name(g)
                fv = g.field_values or {}
                if search.lower() in name.lower() or any(search.lower() in str(v).lower() for v in fv.values()):
                    matched.append({
                        "uid": f"g{g.id}", "source": "group",
                        "name": name,
                        "group_type": g.group.name,
                        "area": g.sub_location.area.name if g.sub_location else "",
                        "sub_location": g.sub_location.name if g.sub_location else "",
                        "status": g.status,
                    })
            all_devices.extend(matched[:500])
        else:
            all_g = q.order_by(GroupDevice.id.desc()).limit(500).all()
            for g in all_g:
                name = _group_name(g)
                all_devices.append({
                    "uid": f"g{g.id}", "source": "group",
                    "name": name,
                    "group_type": g.group.name,
                    "area": g.sub_location.area.name if g.sub_location else "",
                    "sub_location": g.sub_location.name if g.sub_location else "",
                    "status": g.status,
                })

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
            try:
                tid = int(group_type.split("_", 1)[1])
                q = q.filter(Device.device_type_id == tid)
            except (IndexError, ValueError):
                pass

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

    result = paginate(all_devices, page, page_size)
    result.update({
        "normal": normal,
        "fault": fault,
        "scrapped": scrapped,
    })
    return result
