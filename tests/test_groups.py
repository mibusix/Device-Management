def _csrf_header(client):
    return {"X-CSRF-Token": client.cookies.get("csrf_token")}


def test_list_groups(admin_client):
    r = admin_client.get("/api/groups/")
    assert r.status_code == 200
    data = r.json()
    # 种子数据包含 4 个预设分组
    assert len(data) == 4


def test_create_group_device(admin_client):
    from app.database import SessionLocal
    from app.models import Area, SubLocation

    db = SessionLocal()
    area = Area(name="G区", description="")
    db.add(area)
    db.flush()
    sub = SubLocation(name="G机房", area_id=area.id)
    db.add(sub)
    db.commit()

    r = admin_client.post(
        "/api/groups/devices",
        json={
            "group_id": 1,
            "area_id": area.id,
            "sub_location_id": sub.id,
            "status": "正常",
            "power_rating": 5,
            "notes": "",
            "field_values": {"编号": "DEV-001"},
        },
        headers=_csrf_header(admin_client),
    )
    assert r.status_code == 200, r.text
    assert r.json()["ok"] is True


def test_create_group_device_invalid_group(admin_client):
    r = admin_client.post(
        "/api/groups/devices",
        json={
            "group_id": 9999,
            "area_id": None,
            "sub_location_id": None,
            "status": "正常",
            "power_rating": 0,
            "notes": "",
            "field_values": {},
        },
        headers=_csrf_header(admin_client),
    )
    assert r.status_code == 400
    assert "分组不存在" in r.json()["detail"]
