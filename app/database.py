from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import DATABASE_URL
import os

os.makedirs("data", exist_ok=True)

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from app.models import DeviceType, DeviceTypeField, DeviceTypeSubType, DeviceGroup, GroupField
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Create default device group "多联机"
        group = db.query(DeviceGroup).filter(DeviceGroup.name == "多联机").first()
        if not group:
            group = DeviceGroup(name="多联机", description="多联机设备管理", sort_order=1)
            db.add(group)
            db.flush()
            fields = [
                ("序号", "text", "", 0),
                ("编号", "text", "", 1),
                ("型号", "text", "", 1),
                ("制冷剂型号", "text", "", 0),
                ("外机位置", "text", "", 0),
                ("内机位置", "text", "", 0),
            ]
            for i, (name, ftype, unit, required) in enumerate(fields):
                db.add(GroupField(
                    group_id=group.id, field_name=name,
                    field_type=ftype, unit=unit,
                    required=required, sort_order=i,
                ))
        db.commit()
    finally:
        db.close()
