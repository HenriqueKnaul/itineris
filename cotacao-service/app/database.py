from sqlmodel import Session, SQLModel, create_engine

from app import models  # noqa: F401  (garante que as tabelas estão registradas)
from app.seed import seed_voos

engine = create_engine("sqlite:///cotacao_db.sqlite", connect_args={"check_same_thread": False})


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        seed_voos(session)


def get_session():
    with Session(engine) as session:
        yield session
