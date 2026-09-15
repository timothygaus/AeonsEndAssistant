import random

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import col, select, Session

from app.database import get_session
from app.models import BreachMage, Nemesis, PlayerCard, UserSet
from app.enums import CardType
from app.rules import MAX_MAGES, MIN_MAGES, STARTING_SUPPLY
from app.schemas import QuickplayResponse

router = APIRouter()

@router.get('/quickplay', response_model=QuickplayResponse)
def get_quickplay(
        num_mages: int = Query(default=MIN_MAGES, ge=MIN_MAGES, le=MAX_MAGES),
        session: Session = Depends(get_session)):
    user_sets = session.exec(select(UserSet)).all()
    if not user_sets:
        raise HTTPException(status_code=404, detail='No sets found in user sets')

    user_set_ids = [user_set.set_id for user_set in user_sets]
    player_cards = []
    for card_type, count in STARTING_SUPPLY.items():
        player_cards += draw_supply(session, CardType(card_type), count, user_set_ids)

    available_mages = session.exec(
        select(BreachMage).where(
            col(BreachMage.set_id).in_(user_set_ids)
        )
    ).all()
    if len(available_mages) < num_mages:
        raise HTTPException(status_code=400, detail=f'Unable to select {num_mages} mages from available sets')
    mages = random.sample(available_mages, num_mages)

    available_nemeses = session.exec(
        select(Nemesis).where(
            col(Nemesis.set_id).in_(user_set_ids)
        )
    ).all()
    if not available_nemeses:
        raise HTTPException(status_code=404, detail='No nemesis found in available sets')
    nemesis = random.choice(available_nemeses)

    return QuickplayResponse(
        player_cards=player_cards,
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
            PlayerCard.is_supply == True,  # noqa: E712 - SQL comparison, not a bool check
            col(PlayerCard.set_id).in_(set_ids),
        )
    ).all()

    if len(pool) < count:
        raise HTTPException(status_code=400, detail=f'Not enough {card_type.value}s in the selected sets')
    
    return random.sample(pool, count)
