from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import DATABASE_URL, BASE_DIR
import os

os.makedirs(os.path.join(BASE_DIR, "data"), exist_ok=True)

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
        # Predefined groups: (name, fields)
        preset_groups = [
            ("多联机", [
                ("序号", "text", "", 0),
                ("编号", "text", "", 1),
                ("型号", "text", "", 1),
                ("制冷剂型号", "text", "", 0),
                ("外机位置", "text", "", 0),
                ("内机位置", "text", "", 0),
            ]),
            ("控制保护器", [
                ("编号", "text", "", 1),
                ("型号", "text", "", 0),
                ("额定电流", "text", "A", 0),
                ("品牌", "text", "", 0),
            ]),
            ("压缩机", [
                ("编号", "text", "", 1),
                ("型号", "text", "", 0),
                ("制冷剂型号", "text", "", 0),
                ("功率", "number", "kW", 0),
            ]),
            ("水泵", [
                ("编号", "text", "", 1),
                ("型号", "text", "", 0),
                ("扬程", "number", "m", 0),
                ("流量", "number", "m³/h", 0),
                ("功率", "number", "kW", 0),
            ]),
        ]
        for sort, (gname, gfields) in enumerate(preset_groups):
            g = db.query(DeviceGroup).filter(DeviceGroup.name == gname).first()
            if not g:
                g = DeviceGroup(name=gname, description=f"{gname}管理", sort_order=sort)
                db.add(g)
                db.flush()
                for i, (fname, ftype, unit, req) in enumerate(gfields):
                    db.add(GroupField(
                        group_id=g.id, field_name=fname,
                        field_type=ftype, unit=unit,
                        required=req, sort_order=i,
                    ))
        db.commit()
    finally:
        db.close()
