import pytest


def _create_area(client, csrf_token, name="A区"):
    r = client.post(
        "/api/locations/areas",
        json={"name": name, "description": ""},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _create_sub(client, csrf_token, area_id, name="机房"):
    r = client.post(
        "/api/locations/sub-locations",
        json={"name": name, "area_id": area_id, "description": ""},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _create_device_type():
    from app.database import SessionLocal
    from app.models import DeviceType, DeviceTypeField
    db = SessionLocal()
    dt = DeviceType(name="TestType", description="")
    db.add(dt)
    db.flush()
    db.add(DeviceTypeField(device_type_id=dt.id, field_name="型号", field_type="text", required=1, sort_order=0))
    db.commit()
    db.refresh(dt)
    return dt


def test_create_device(admin_client, csrf_token):
    area_id = _create_area(admin_client, csrf_token)
    sub_id = _create_sub(admin_client, csrf_token, area_id)
    dt = _create_device_type()

    r = admin_client.post(
        "/api/devices/",
        json={
            "name": "设备-001",
            "device_type_id": dt.id,
            "sub_location_id": sub_id,
            "status": "正常",
            "power_rating": 100,
            "notes": "",
            "field_values": {},
        },
        headers={"X-CSRF-Token": csrf_token},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["ok"] is True
    assert isinstance(data["id"], int)


def test_create_device_invalid_type(admin_client, csrf_token):
    r = admin_client.post(
        "/api/devices/",
        json={
            "name": "设备-001",
            "device_type_id": 9999,
            "sub_location_id": 1,
            "status": "正常",
            "power_rating": 0,
            "notes": "",
            "field_values": {},
        },
        headers={"X-CSRF-Token": csrf_token},
    )
    assert r.status_code == 400
    assert "设备类型不存在" in r.json()["detail"]


def test_create_device_invalid_field_key(admin_client, csrf_token):
    area_id = _create_area(admin_client, csrf_token)
    sub_id = _create_sub(admin_client, csrf_token, area_id)
    dt = _create_device_type()

    r = admin_client.post(
        "/api/devices/",
        json={
            "name": "设备-002",
            "device_type_id": dt.id,
            "sub_location_id": sub_id,
            "status": "正常",
            "power_rating": 0,
            "notes": "",
            "field_values": {"abc": "1"},
        },
        headers={"X-CSRF-Token": csrf_token},
    )
    assert r.status_code == 400
    assert "字段 ID 必须是整数" in r.json()["detail"]


def test_update_device(admin_client, csrf_token):
    area_id = _create_area(admin_client, csrf_token)
    sub_id = _create_sub(admin_client, csrf_token, area_id)
    dt = _create_device_type()

    r = admin_client.post(
        "/api/devices/",
        json={
            "name": "设备-003",
            "device_type_id": dt.id,
            "sub_location_id": sub_id,
            "status": "正常",
            "power_rating": 0,
            "notes": "",
            "field_values": {},
        },
        headers={"X-CSRF-Token": csrf_token},
    )
    device_id = r.json()["id"]

    r = admin_client.put(
        f"/api/devices/{device_id}",
        json={
            "name": "设备-003-修改",
            "device_type_id": dt.id,
            "sub_location_id": sub_id,
            "status": "故障",
            "power_rating": 200,
            "notes": "已修改",
            "field_values": {},
        },
        headers={"X-CSRF-Token": csrf_token},
    )
    assert r.status_code == 200


def test_delete_device(admin_client, csrf_token):
    area_id = _create_area(admin_client, csrf_token)
    sub_id = _create_sub(admin_client, csrf_token, area_id)
    dt = _create_device_type()

    r = admin_client.post(
        "/api/devices/",
        json={
            "name": "设备-004",
            "device_type_id": dt.id,
            "sub_location_id": sub_id,
            "status": "正常",
            "power_rating": 0,
            "notes": "",
            "field_values": {},
        },
        headers={"X-CSRF-Token": csrf_token},
    )
    device_id = r.json()["id"]

    r = admin_client.delete(
        f"/api/devices/{device_id}",
        headers={"X-CSRF-Token": csrf_token},
    )
    assert r.status_code == 200

    r = admin_client.get(f"/api/devices/{device_id}")
    assert r.status_code == 404
