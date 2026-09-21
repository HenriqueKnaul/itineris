from sqlmodel import SQLModel, Field

# Modelo Base com o ID string (no nosso caso Admin/Admin)
class UsuarioBase(SQLModel):
    id: str = Field(primary_key=True)
    nome: str

# Tabela na Base de Dados
class Usuario(UsuarioBase, table=True):
    hashed_password: str

# DTO para a requisição de Login/Registo
class UsuarioCreate(SQLModel):
    id: str
    password: str

# DTO do Token
class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"