import os

from sqlmodel import SQLModel, create_engine, Session

# Nome do arquivo do banco de dados SQLite local
sqlite_file_name = "roteiro_db.sqlite"
sqlite_url = f"sqlite:///{sqlite_file_name}"

# O Engine é o motor de conexão (no Delphi equivale ao TFDConnection do FireDAC)
# echo=True despeja todo SQL no log; deixamos desligado por padrão e
# ligável via variável de ambiente para depurar quando precisar.
echo_sql = os.getenv("SQL_ECHO", "false").lower() == "true"
engine = create_engine(sqlite_url, echo=echo_sql)

def create_db_and_tables():
    """Cria o arquivo do banco e as tabelas caso ainda não existam."""
    SQLModel.metadata.create_all(engine)

def get_session():
    """Gera uma sessão de banco de dados para cada requisição HTTP e fecha ao terminar."""
    with Session(engine) as session:
        yield session