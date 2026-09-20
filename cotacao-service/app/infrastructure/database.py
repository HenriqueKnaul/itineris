from sqlmodel import SQLModel, create_engine, Session
from app.domain import models
from app.infrastructure.write_model.seed import seed_voos

sqlite_file_name = "cotacao_db.sqlite"
sqlite_url = f"sqlite:///{sqlite_file_name}"

connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, echo=False, connect_args=connect_args)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        seed_voos(session)

def get_session():
    with Session(engine) as session:
        yield session