import random
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import SQLModel, Session, select

from app.database import get_session
from app.models import BreachMage, Expedition, ExpeditionBattle, ExpeditionMage, ExpeditionPlayerCard, ExpeditionSet, Nemesis, PlayerCard, Set
from app.enums import CardType

router = APIRouter()

class ExpeditionCreate(SQLModel):
    name: Optional[str] = None
    set_ids: list[int]
    variant: str = 'standard'

@router.post('/expeditions')
def create_expedition(data: ExpeditionCreate, session: Session = Depends(get_session)):
    start_battle = 2 if data.variant == 'short' else 1    
    expedition = Expedition(name=data.name, variant=data.variant, current_battle=start_battle)
    session.add(expedition)
    session.flush()

    for set_id in data.set_ids:
        session.add(ExpeditionSet(expedition_id=expedition.id, set_id=set_id))

    def draw_supply(card_type: CardType, count: int):
        pool = session.exec(
            select(PlayerCard).where(
                PlayerCard.type == card_type,
                PlayerCard.is_supply == True,
                PlayerCard.set_id.in_(data.set_ids)
            )
        ).all()
        if len(pool) < count:
            raise HTTPException(status_code=400, detail=f'Not enough {card_type}s in selected sets')
        for card in random.sample(pool, count):
            session.add(ExpeditionPlayerCard(
                expedition_id=expedition.id,
                player_card_id=card.id,
                status='barracks'
            ))

    # Seeding the initial supply cards
    draw_supply(CardType.GEM, 3)
    draw_supply(CardType.RELIC, 2)
    draw_supply(CardType.SPELL, 4)

    mage_pool = session.exec(
        select(BreachMage).where(BreachMage.set_id.in_(data.set_ids))
    ).all()
    if len(mage_pool) < 4:
        raise HTTPException(status_code=400, detail='Not enough mages in selected sets')
    for mage in random.sample(mage_pool, 4):
        session.add(ExpeditionMage(expedition_id=expedition.id, mage_id=mage.id))

    nemesis_pool = session.exec(
        select(Nemesis).where(
            Nemesis.expedition_battle == start_battle,
            Nemesis.set_id.in_(data.set_ids)
        )
    ).all()
    if not nemesis_pool:
        raise HTTPException(status_code=400, detail='No nemesis available for this battle tier')
    session.add(ExpeditionBattle(
        expedition_id=expedition.id,
        battle_number=start_battle,
        nemesis_id=random.choice(nemesis_pool).id
    ))

    session.commit()
    session.refresh(expedition)
    return expedition