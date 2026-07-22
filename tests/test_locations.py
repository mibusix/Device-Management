def _csrf_header(client):
    return {"X-CSRF-Token": client.cookies.get("csrf_token")}


def test_create_area(admin_client):
    r = admin_client.post(
        "/api/locations/areas",
        json={"name": "A区", "description": ""},
        headers=_csrf_header(admin_client),
    )
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_create_sub_location(admin_client):
    r = admin_client.post(
        "/api/locations/areas",
        json={"name": "B区", "description": ""},
        headers=_csrf_header(admin_client),
    )
    area_id = r.json()["id"]

    r = admin_client.post(
        "/api/locations/sub-locations",
        json={"name": "机房", "area_id": area_id, "description": ""},
        headers=_csrf_header(admin_client),
    )
    assert r.status_code == 200
    assert r.json()["id"]


def test_delete_area_with_sub_location_blocked(admin_client):
    r = admin_client.post(
        "/api/locations/areas",
        json={"name": "C区", "description": ""},
        headers=_csrf_header(admin_client),
    )
    area_id = r.json()["id"]

    r = admin_client.post(
        "/api/locations/sub-locations",
        json={"name": "夹层", "area_id": area_id, "description": ""},
        headers=_csrf_header(admin_client),
    )
    sub_id = r.json()["id"]

    # 子区域下没有设备，可以删除大区域
    r = admin_client.delete(
        f"/api/locations/areas/{area_id}",
        headers=_csrf_header(admin_client),
    )
    assert r.status_code == 200


def test_delete_area_with_group_device_area_id_blocked(admin_client):
    from app.database import SessionLocal
    from app.models import Area, GroupDevice

    db = SessionLocal()
    area = Area(name="D区", description="")
    db.add(area)
    db.commit()
    db.refresh(area)

    # 直接通过 area_id 关联的分组设备
    gd = GroupDevice(group_id=1, area_id=area.id, status="正常", power_rating=0, notes="", field_values={})
    db.add(gd)
    db.commit()

    r = admin_client.delete(
        f"/api/locations/areas/{area.id}",
        headers=_csrf_header(admin_client),
    )
    assert r.status_code == 400
    assert "存在关联的设备" in r.json()["detail"]
