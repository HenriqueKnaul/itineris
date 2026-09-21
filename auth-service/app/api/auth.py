from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from app.infrastructure.database import get_session
from app.domain.models import Usuario, UsuarioCreate, Token
from app.core.security import verificar_senha, criar_token_acesso

router = APIRouter(prefix="/auth", tags=["Autenticação"])

@router.post("/login", response_model=Token)
def login(usuario_in: UsuarioCreate, session: Session = Depends(get_session)):
    """Mapeamento para autenticar o utilizador e devolver o token JWT."""
    usuario = session.exec(select(Usuario).where(Usuario.id == usuario_in.id)).first()
    
    if not usuario or not verificar_senha(usuario_in.password, usuario.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ID ou palavra-passe incorretos."
        )

    # Cria o token contendo o ID do utilizador no campo "sub"
    token = criar_token_acesso(data={"sub": usuario.id, "nome": usuario.nome})
    return {"access_token": token, "token_type": "bearer"}