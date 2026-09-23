from sqlmodel import SQLModel, Session, create_engine, select
from app.domain.models import Usuario
from app.core.security import gerar_hash_senha

sqlite_file_name = "auth_database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

engine = create_engine(sqlite_url, echo=True)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    criar_admin_padrao()

def get_session():
    """Gera uma sessão de banco de dados por requisição (dependência do FastAPI).

    Faltava esta função — app/api/auth.py já importava `get_session`, mas ela
    nunca tinha sido definida aqui, então o serviço quebrava com ImportError
    assim que alguém tentasse subir ou importar o módulo.
    """
    with Session(engine) as session:
        yield session

def criar_admin_padrao():
    with Session(engine) as session:
        admin_existente = session.exec(select(Usuario).where(Usuario.id == "admin")).first()
        
        if not admin_existente:
            usuario_admin = Usuario(id="admin", nome="Administrador", hashed_password=gerar_hash_senha("admin"))
            
            session.add(usuario_admin)
            session.commit()
            print("Utilizador admin criado com sucesso! (ID: admin | Palavra-passe: admin)")