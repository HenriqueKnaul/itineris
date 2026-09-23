import os

from sqlmodel import SQLModel, create_engine, Session

sqlite_file_name = "roteiro_db.sqlite"
sqlite_url = f"sqlite:///{sqlite_file_name}"

echo_sql = os.getenv("SQL_ECHO", "false").lower() == "true"
engine = create_engine(sqlite_url, echo=echo_sql)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session