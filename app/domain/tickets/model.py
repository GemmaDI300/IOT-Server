from uuid import UUID, uuid4
from usuario_rol import UsuarioRol
from gerente_servicio import GerenteServicio
from service import Service
from sqlmodel import Field, Relationship, SQLModel, BaseTable

class TicketStatus(SQLModel, table=True):
    __tablename__ = "ticket_status"

    titulo: str
    id: int | None = Field(default=None, primary_key=True)
    nombre: str = Field(unique=True)
    descripcion: str | None = None

    tickets_servicio: list["TicketServicio"] = Relationship(back_populates="status")
    tickets_ecosistema: list["TicketEcosistema"] = Relationship(back_populates="status")


class TicketServicio(BaseTable, table=True):
    __tablename__ = "ticket_servicio"

    titulo: str
    descripcion: str | None = None
    usuario_rol_id: UUID = Field(foreign_key="usuario_rol.id")
    status_id: int = Field(foreign_key="ticket_status.id")
    servicio_id: UUID = Field(foreign_key="service.id")
    prioridad: str = Field(default="media")

    usuario_rol: UsuarioRol = Relationship(back_populates="tickets_servicio")
    status: TicketStatus = Relationship(back_populates="tickets_servicio")
    servicio: Service = Relationship(back_populates="tickets_servicio")


class TicketEcosistema(BaseTable, table=True):
    __tablename__ = "ticket_ecosistema"

    titulo: str
    descripcion: str | None = None
    gerente_servicio_id: UUID = Field(foreign_key="gerente_servicio.id")
    status_id: int = Field(foreign_key="ticket_status.id")
    prioridad: str = Field(default="media")

    gerente_servicio: GerenteServicio = Relationship(
        back_populates="tickets_ecosistema"
    )
    status: TicketStatus = Relationship(back_populates="tickets_ecosistema")