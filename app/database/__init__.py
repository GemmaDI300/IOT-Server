from typing import Annotated, Generator
from fastapi import Depends
from sqlmodel import Session, SQLModel, create_engine
from app.config import settings
from app.database.views import create_views

engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    connect_args={"check_same_thread": False},
)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        create_views(session)
    with Session(engine) as session:
        create_views(session)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
