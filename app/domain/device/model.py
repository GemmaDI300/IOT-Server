from sqlmodel import Field, Relationship
from app.domain.service.model import Service
from app.shared.base_domain.model import BaseTable
from uuid import UUID

class Device(BaseTable, table=True):
    __tablename__ = "device"

    nombre: str
    modelo: str | None = None
    numero_serie: str | None = Field(default=None, unique=True)
    ip: str | None = None #sensible
    mac: str | None = Field(default=None, unique=True) #sensible
    activo: bool = Field(default=True)

    device_services: list["DeviceService"] = Relationship(
        back_populates="device"
    )


class DeviceService(BaseTable, table=True):
    __tablename__ = "device_service"

    device_id: UUID = Field(foreign_key="device.id")
    service_id: UUID = Field(foreign_key="service.id")

    device: Device = Relationship(back_populates="device_services")
    service: Service = Relationship(back_populates="device_services")
    activo: bool = Field(default=True)
