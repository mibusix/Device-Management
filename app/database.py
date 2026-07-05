from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import DATABASE_URL, BASE_DIR
import os
import re

os.makedirs(os.path.join(BASE_DIR, "data"), exist_ok=True)

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# DDL 标识符白名单：表名/列名只允许字母数字下划线，列类型只允许预定义集合
_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_ALLOWED_COLUMN_TYPES = {
    "INTEGER", "INTEGER DEFAULT 0", "INTEGER DEFAULT 1",
    "TEXT", "TEXT DEFAULT ''",
    "REAL", "REAL DEFAULT 0",
    "INTEGER REFERENCES users(id)",
    "INTEGER REFERENCES areas(id)",
    "INTEGER REFERENCES sub_locations(id)",
    "INTEGER REFERENCES device_types(id)",
    "INTEGER REFERENCES device_groups(id)",
}


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _add_column_if_missing(table_name, column_name, column_type):
    """SQLite 不支持 IF NOT EXISTS 对 ALTER TABLE，手动检查添加列。
    白名单校验防 SQL 注入反模式（虽然当前参数都是硬编码）。"""
    if not _IDENT_RE.match(table_name):
        raise ValueError(f"非法表名: {table_name!r}")
    if not _IDENT_RE.match(column_name):
        raise ValueError(f"非法列名: {column_name!r}")
    if column_type not in _ALLOWED_COLUMN_TYPES:
        raise ValueError(f"不在白名单中的列类型: {column_type!r}")
    insp = inspect(engine)
    cols = [c["name"] for c in insp.get_columns(table_name)]
    if column_name not in cols:
        with engine.connect() as conn:
            conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"))
            conn.commit()


def init_db():
    from app.models import DeviceType, DeviceTypeField, DeviceTypeSubType, DeviceGroup, GroupField
    Base.metadata.create_all(bind=engine)

    # 已有表加新列
    for table, col, ctype in [
        ("areas", "created_by", "INTEGER REFERENCES users(id)"),
        ("areas", "updated_by", "INTEGER REFERENCES users(id)"),
        ("sub_locations", "created_by", "INTEGER REFERENCES users(id)"),
        ("sub_locations", "updated_by", "INTEGER REFERENCES users(id)"),
        ("devices", "created_by", "INTEGER REFERENCES users(id)"),
        ("devices", "updated_by", "INTEGER REFERENCES users(id)"),
        ("device_groups", "created_by", "INTEGER REFERENCES users(id)"),
        ("device_groups", "updated_by", "INTEGER REFERENCES users(id)"),
        ("group_devices", "created_by", "INTEGER REFERENCES users(id)"),
        ("group_devices", "updated_by", "INTEGER REFERENCES users(id)"),
        ("users", "must_change_password", "INTEGER DEFAULT 0"),
    ]:
        _add_column_if_missing(table, col, ctype)

    db = SessionLocal()
    try:
        # 预设分组
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

        # 默认管理员（首次启动需改密）
        from app.models import User
        from app.auth import hash_password
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            admin = User(
                username="admin",
                password_hash=hash_password("admin123"),
                role="admin",
                must_change_password=1,
            )
            db.add(admin)

        # 默认访客
        guest = db.query(User).filter(User.username == "guest").first()
        if not guest:
            guest = User(
                username="guest",
                password_hash=hash_password("guest"),
                role="guest",
            )
            db.add(guest)

        db.commit()
    finally:
        db.close()
