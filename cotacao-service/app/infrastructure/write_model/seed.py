from sqlmodel import Session, select
from app.domain.constantes import ORIGEM_PADRAO
from app.domain.models import Voo

VOOS_INICIAIS = [
    (ORIGEM_PADRAO, "Lisboa", 3800.00, 180, 150),
    (ORIGEM_PADRAO, "Paris", 4500.00, 200, 90),
    (ORIGEM_PADRAO, "Roma", 4700.00, 150, 20),
    (ORIGEM_PADRAO, "Buenos Aires", 1200.00, 120, 100),
    (ORIGEM_PADRAO, "Tóquio", 9800.00, 100, 0),
    ("Lisboa", "Paris", 650.00, 150, 120),
    ("Paris", "Roma", 550.00, 150, 100),
    ("Lisboa", ORIGEM_PADRAO, 3800.00, 180, 140),
    ("Paris", ORIGEM_PADRAO, 4500.00, 200, 100),
    ("Roma", ORIGEM_PADRAO, 4700.00, 150, 60),
    ("Buenos Aires", ORIGEM_PADRAO, 1200.00, 120, 90),
    ("Tóquio", ORIGEM_PADRAO, 9800.00, 100, 40),
]

def seed_voos(session: Session) -> int:
    existentes = {(v.origem, v.destino) for v in session.exec(select(Voo)).all()}
    inseridos = 0
    for origem, destino, preco_base, capacidade, vagas in VOOS_INICIAIS:
        if (origem, destino) in existentes:
            continue
        session.add(
            Voo(origem=origem, destino=destino, preco_base=preco_base, capacidade=capacidade, vagas=vagas)
        )
        inseridos += 1
    if inseridos:
        session.commit()
    return inseridos