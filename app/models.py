from sqlalchemy import (
    Column, Integer, String, Float, ForeignKey, Text, Enum, DateTime, Date, JSON
)
from sqlalchemy.orm import relationship
from app.database import Base
import enum
from datetime import datetime


class DeviceStatus(str, enum.Enum):
    NORMAL = "正常"
    FAULT = "故障"
    SCRAPPED = "报废"


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default=UserRole.USER.value)
    is_active = Column(Integer, default=1)
    must_change_password = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class OperationLog(Base):
    __tablename__ = "operation_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    username = Column(String(50), default="")
    action = Column(String(20), nullable=False)
    target_type = Column(String(50), nullable=False)
    target_id = Column(Integer, nullable=True)
    target_name = Column(String(200), default="")
    detail = Column(JSON, default=dict)
    ip_address = Column(String(50), default="")
    created_at = Column(DateTime, default=datetime.now)

    user = relationship("User")


class Area(Base):
    __tablename__ = "areas"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, default="")
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True, default=None)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True, default=None)

    sub_locations = relationship("SubLocation", back_populates="area", cascade="all, delete-orphan")


class SubLocation(Base):
    __tablename__ = "sub_locations"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    area_id = Column(Integer, ForeignKey("areas.id"), nullable=False, index=True)
    description = Column(Text, default="")
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True, default=None)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True, default=None)

    area = relationship("Area", back_populates="sub_locations")
    devices = relationship("Device", back_populates="sub_location")


class DeviceType(Base):
    __tablename__ = "device_types"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, default="")

    fields = relationship("DeviceTypeField", back_populates="device_type", cascade="all, delete-orphan",
                          order_by="DeviceTypeField.sort_order")
    devices = relationship("Device", back_populates="device_type")


class DeviceTypeSubType(Base):
    __tablename__ = "device_type_sub_types"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    device_type_id = Column(Integer, ForeignKey("device_types.id"), nullable=False)
    description = Column(Text, default="")

    device_type = relationship("DeviceType", backref="sub_types")
    devices = relationship("Device", back_populates="sub_type")


class DeviceTypeField(Base):
    __tablename__ = "device_type_fields"
    id = Column(Integer, primary_key=True, index=True)
    device_type_id = Column(Integer, ForeignKey("device_types.id"), nullable=False)
    field_name = Column(String(100), nullable=False)
    field_type = Column(String(20), default="text")
    unit = Column(String(50), default="")
    required = Column(Integer, default=0)
    sort_order = Column(Integer, default=0)

    device_type = relationship("DeviceType", back_populates="fields")
    values = relationship("DeviceFieldValue", back_populates="field", cascade="all, delete-orphan")


class Device(Base):
    __tablename__ = "devices"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    device_type_id = Column(Integer, ForeignKey("device_types.id"), nullable=False, index=True)
    sub_type_id = Column(Integer, ForeignKey("device_type_sub_types.id"), nullable=True)
    sub_location_id = Column(Integer, ForeignKey("sub_locations.id"), nullable=False, index=True)
    status = Column(String(20), default=DeviceStatus.NORMAL.value, index=True)
    power_rating = Column(Float, default=0)

    notes = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.now)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True, default=None)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True, default=None)

    device_type = relationship("DeviceType", back_populates="devices")
    sub_type = relationship("DeviceTypeSubType", back_populates="devices")
    sub_location = relationship("SubLocation", back_populates="devices")
    field_values = relationship("DeviceFieldValue", back_populates="device", cascade="all, delete-orphan")
    energy_records = relationship("EnergyRecord", back_populates="device", cascade="all, delete-orphan")


class DeviceFieldValue(Base):
    __tablename__ = "device_field_values"
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    field_id = Column(Integer, ForeignKey("device_type_fields.id"), nullable=False)
    value = Column(String(500), default="")

    device = relationship("Device", back_populates="field_values")
    field = relationship("DeviceTypeField", back_populates="values")


class EnergyRecord(Base):
    __tablename__ = "energy_records"
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    power = Column(Float, nullable=False)
    runtime_hours = Column(Float, nullable=False)
    energy_kwh = Column(Float, nullable=False)
    record_date = Column(Date, nullable=False)
    notes = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.now)

    device = relationship("Device", back_populates="energy_records")


class MultiSplitEnergy(Base):
    __tablename__ = "multi_split_energy"
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=False)
    power = Column(Float, nullable=False)
    runtime_hours = Column(Float, nullable=False)
    energy_kwh = Column(Float, nullable=False)
    outdoor_temp = Column(Float, nullable=True)
    indoor_temp = Column(Float, nullable=True)
    record_date = Column(Date, nullable=False)
    notes = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.now)

    device = relationship("Device")


class DeviceGroup(Base):
    __tablename__ = "device_groups"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, default="")
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True, default=None)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True, default=None)

    fields = relationship("GroupField", back_populates="group",
                          cascade="all, delete-orphan",
                          order_by="GroupField.sort_order")
    devices = relationship("GroupDevice", back_populates="group",
                           cascade="all, delete-orphan")


class GroupField(Base):
    __tablename__ = "group_fields"
    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("device_groups.id"), nullable=False)
    field_name = Column(String(100), nullable=False)
    field_type = Column(String(20), default="text")
    unit = Column(String(50), default="")
    required = Column(Integer, default=0)
    sort_order = Column(Integer, default=0)

    group = relationship("DeviceGroup", back_populates="fields")


class GroupDevice(Base):
    __tablename__ = "group_devices"
    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("device_groups.id"), nullable=False, index=True)
    area_id = Column(Integer, ForeignKey("areas.id"), nullable=True, index=True)
    sub_location_id = Column(Integer, ForeignKey("sub_locations.id"), nullable=True, index=True)
    status = Column(String(20), default="正常")
    power_rating = Column(Float, default=0)
    notes = Column(Text, default="")
    field_values = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.now)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True, default=None)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True, default=None)

    group = relationship("DeviceGroup", back_populates="devices")
    area = relationship("Area")
    sub_location = relationship("SubLocation")
