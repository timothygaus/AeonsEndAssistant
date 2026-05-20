import math
import random

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select, Session

from app.database import get_session
from app.enums import BattleResult, CardType, ExpeditionStatus, ExpeditionVariant, LossRandomizerType, SupplyCardStatus
from app.models import BreachMage, Expedition, ExpeditionBattle, ExpeditionMage, ExpeditionPlayerCard, ExpeditionSet, Nemesis, PlayerCard
from app.schemas import BattleDetail, ExpeditionCreate, ExpeditionStateResponse, ResolveBattleRequest

router = APIRouter()

MAX_EXP_LEN = 4

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

    # Seeding the initial supply cards
    draw_supply(session, expedition.id, CardType.GEM, 3, data.set_ids)
    draw_supply(session, expedition.id, CardType.RELIC, 2, data.set_ids)
    draw_supply(session, expedition.id, CardType.SPELL, 4, data.set_ids)

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

@router.post('/expeditions/{expedition_id}/resolve-battle')
def resolve_battle(expedition_id: int, data: ResolveBattleRequest, session: Session = Depends(get_session)):
    expedition = session.exec(select(Expedition).where(Expedition.id == expedition_id)).first()
    expedition_battle = session.exec(
        select(ExpeditionBattle).where(
            ExpeditionBattle.expedition_id == expedition_id,
            ExpeditionBattle.battle_number == expedition.current_battle
        )
    ).first()
    expedition_sets = session.exec(select(ExpeditionSet).where(ExpeditionSet.expedition_id == expedition_id)).all()
    set_ids = [exp_set.set_id for exp_set in expedition_sets]

    if data.won_battle:
        expedition_battle.result = BattleResult.WIN
        if (expedition_battle.battle_number == MAX_EXP_LEN and not expedition.variant == ExpeditionVariant.EXTENDED
            or expedition_battle.battle_number == MAX_EXP_LEN*2):
            expedition.status = ExpeditionStatus.COMPLETE
            session.add(expedition)
            session.add(expedition_battle)
            session.commit()
            session.refresh(expedition)
            return expedition
        
        session.add(expedition_battle)

        expedition.current_battle += 1

        draw_supply(session, expedition_id, CardType.GEM, 1, set_ids)
        draw_supply(session, expedition_id, CardType.RELIC, 1, set_ids)
        draw_supply(session, expedition_id, CardType.SPELL, 1, set_ids)

        fought_nemeses = session.exec(select(ExpeditionBattle).where(ExpeditionBattle.expedition_id == expedition_id)).all()
        fought_nemesis_ids = [nem.nemesis_id for nem in fought_nemeses]
        nemesis_battle_num = math.ceil(expedition.current_battle/2) if expedition.variant == ExpeditionVariant.EXTENDED else expedition.current_battle

        nemesis_pool = session.exec(
            select(Nemesis).where(
                Nemesis.expedition_battle == nemesis_battle_num,
                Nemesis.set_id.in_(set_ids),
                Nemesis.id.not_in(fought_nemesis_ids)
            )
        ).all()
        nemesis_ids = [nemesis.id for nemesis in nemesis_pool]

        session.add(ExpeditionBattle(
            expedition_id=expedition_id,
            battle_number=expedition.current_battle,
            nemesis_id=random.choice(nemesis_ids)
        ))

    else:
        expedition_battle.result = BattleResult.LOSS
        session.add(expedition_battle)
        if data.loss_randomizer_type is not LossRandomizerType.TREASURE:
            if data.loss_randomizer_type is LossRandomizerType.MAGE:
                expedition_mages = session.exec(select(ExpeditionMage).where(ExpeditionMage.expedition_id == expedition_id)).all()
                expedition_mage_ids = [mage.mage_id for mage in expedition_mages]
                mage_pool = session.exec(
                    select(BreachMage).where(
                        BreachMage.id.not_in(expedition_mage_ids),
                        BreachMage.set_id.in_(set_ids)
                    )
                ).all()
                random_mage = random.choice(mage_pool)
                session.add(ExpeditionMage(
                    expedition_id=expedition_id,
                    mage_id=random_mage.id
                ))
            else:
                draw_supply(session, expedition_id, CardType(data.loss_randomizer_type.value), 1, set_ids)

    session.add(expedition)
    session.commit()
    session.refresh(expedition)
    return expedition

def draw_supply(
        session: Session,
        expedition_id: int,
        card_type: CardType,
        count: int,
        set_ids: list[int]):
    
    used_cards = session.exec(select(ExpeditionPlayerCard).where(ExpeditionPlayerCard.expedition_id == expedition_id)).all()
    used_card_ids = [card.player_card_id for card in used_cards]

    pool = session.exec(
        select(PlayerCard).where(
            PlayerCard.type == card_type,
            PlayerCard.is_supply == True,
            PlayerCard.set_id.in_(set_ids),
            PlayerCard.id.not_in(used_card_ids),
        )
    ).all()

    if len(pool) < count:
        raise HTTPException(status_code=400, detail=f'Not enough {card_type}s in selected sets')
    
    for card in random.sample(pool, count):
        session.add(ExpeditionPlayerCard(
            expedition_id=expedition_id,
            player_card_id=card.id,
            status=SupplyCardStatus.BARRACKS
        ))
