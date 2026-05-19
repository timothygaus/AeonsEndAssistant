import random

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select, Session

from app.database import get_session
from app.enums import CardType, ExpeditionVariant, SupplyCardStatus
from app.models import BreachMage, Expedition, ExpeditionBattle, ExpeditionMage, ExpeditionPlayerCard, ExpeditionSet, Nemesis, PlayerCard
from app.schemas import BattleDetail, ExpeditionCreate, ExpeditionStateResponse

router = APIRouter()

@router.get('/expeditions')
def get_expeditions(session: Session = Depends(get_session)):
    return session.exec(select(Expedition)).all()

@router.post('/expeditions')
def create_expedition(data: ExpeditionCreate, session: Session = Depends(get_session)):
    start_battle = 2 if data.variant == ExpeditionVariant.SHORT else 1    
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
                status=SupplyCardStatus.BANISHED
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

@router.get('/expeditions/{id}')
def get_expedition_by_id(id: int, session: Session = Depends(get_session)):
    expedition = session.exec(select(Expedition).where(Expedition.id == id)).first()
    if not expedition:
        raise HTTPException(status_code=404, detail=f'Expedition with id={id} not found')
    
    expedition_player_cards = session.exec(select(ExpeditionPlayerCard).where(ExpeditionPlayerCard.expedition_id==id)).all()
    barracks_ids = [card.player_card_id for card in expedition_player_cards if card.status == SupplyCardStatus.BARRACKS]
    banished_ids = [card.player_card_id for card in expedition_player_cards if card.status == SupplyCardStatus.BANISHED]

    barracks_cards = session.exec(select(PlayerCard).where(PlayerCard.id.in_(barracks_ids))).all()
    banished_cards = session.exec(select(PlayerCard).where(PlayerCard.id.in_(banished_ids))).all()

    expedition_mages = session.exec(select(ExpeditionMage).where(ExpeditionMage.expedition_id==id)).all()
    mage_ids = [mage.mage_id for mage in expedition_mages]
    mages = session.exec(select(BreachMage).where(BreachMage.id.in_(mage_ids))).all()
    
    expedition_battles = session.exec(select(ExpeditionBattle).where(ExpeditionBattle.expedition_id==id)).all()
    battle_details = []
    for battle in expedition_battles:
        nemesis = session.exec(select(Nemesis).where(Nemesis.id == battle.nemesis_id)).first()
        battle_details.append(BattleDetail(
            battle_number=battle.battle_number,
            result=battle.result,
            nemesis=nemesis
        ))

    return ExpeditionStateResponse(
        expedition=expedition,
        barracks_cards=barracks_cards,
        banished_cards=banished_cards,
        mages=mages,
        battles=battle_details
    )

# @router.post('/expeditions/{id}/resolve-battle')
# def resolve_battle(result: str, randomizer_on_loss: str, session: Session = Depends(get_session)):
