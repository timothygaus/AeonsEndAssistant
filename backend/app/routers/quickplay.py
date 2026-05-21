import random

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select, Session

from app.database import get_session
from app.models import BreachMage, Nemesis, PlayerCard, UserSet
from app.enums import CardType
from app.schemas import QuickplayResponse

router = APIRouter()

@router.get('/quickplay')
def get_quickplay(num_mages: int, session: Session = Depends(get_session)):
    user_sets = session.exec(select(UserSet)).all()
    if not user_sets:
        raise HTTPException(status_code=404, detail='No sets found in user sets')
    
    user_set_ids = [user_set.set_id for user_set in user_sets]
    gems = draw_supply(session, CardType.GEM, 3, user_set_ids)
    relics = draw_supply(session, CardType.RELIC, 2, user_set_ids)
    spells = draw_supply(session, CardType.SPELL, 4, user_set_ids)

    available_mages = session.exec(
        select(BreachMage).where(
            BreachMage.set_id.in_(user_set_ids)
        )
    ).all()
    if len(available_mages) < num_mages:
        raise HTTPException(status_code=400, detail=f'Unable to select {num_mages} mages from available sets')
    mages = random.sample(available_mages, num_mages)

    available_nemeses = session.exec(
        select(Nemesis).where(
            Nemesis.set_id.in_(user_set_ids)
        )
    ).all()
    if not available_nemeses:
        raise HTTPException(status_code=404, detail='No nemesis found in available sets')
    nemesis = random.choice(available_nemeses)

    return QuickplayResponse(
        player_cards = gems + relics + spells,
        mages=mages,
        nemesis=nemesis
    )

def draw_supply(
        session: Session,
        card_type: CardType,
        count: int,
        set_ids: list[int]):
    
    pool = session.exec(
        select(PlayerCard).where(
            PlayerCard.type == card_type,
            PlayerCard.is_supply == True,
            PlayerCard.set_id.in_(set_ids),
        )
    ).all()

    if len(pool) < count:
        raise HTTPException(status_code=400, detail=f'Not enough {card_type}s in selected sets')
    
    return random.sample(pool, count)
