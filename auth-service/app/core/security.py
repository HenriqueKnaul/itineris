from datetime import datetime, timedelta, timezone
from jose import jwt
from passlib.context import CryptContext

SECRET_KEY = "sua_chave_secreta_devops"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 120

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def gerar_hash_senha(password: str) -> str:
    """Gera o hash Bcrypt da palavra-passe em texto limpo."""
    return pwd_context.hash(password)

def verificar_senha(password_limpa: str, hashed_password: str) -> bool:
    """Compara a palavra-passe enviada com o hash guardado."""
    return pwd_context.verify(password_limpa, hashed_password)

def criar_token_acesso(data: dict) -> str:
    """Gera um token JWT com tempo de expiração de 2 horas."""
    dados_token = data.copy()
    expiracao = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    dados_token.update({"exp": expiracao})
    return jwt.encode(dados_token, SECRET_KEY, algorithm=ALGORITHM)