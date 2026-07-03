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
    from app.models import DeviceType, DeviceTypeField, DeviceTypeSubType
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        multi = db.query(DeviceType).filter(DeviceType.name == "多联机").first()
        if not multi:
            multi = DeviceType(name="多联机", description="多联机设备管理")
            db.add(multi)
            db.flush()
            fields = [
                ("序号", "text", "", 0, 1),
                ("编号", "text", "", 1, 2),
                ("型号", "text", "", 1, 3),
                ("制冷剂型号", "text", "", 0, 4),
                ("外机位置", "text", "", 0, 5),
                ("内机位置", "text", "", 0, 6),
            ]
            for name, ftype, unit, required, order in fields:
                db.add(DeviceTypeField(
                    device_type_id=multi.id, field_name=name,
                    field_type=ftype, unit=unit,
                    required=required, sort_order=order,
                ))
            db.commit()
    finally:
        db.close()
