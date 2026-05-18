from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from app.models import BreachMage, Expedition, ExpeditionBattle, ExpeditionMage, ExpeditionPlayerCard, Nemesis, PlayerCard
from app.schemas import BattleDetail, ExpeditionStateResponse

router = APIRouter()

@router.get('/expeditions')
def get_expeditions(session: Session = Depends(get_session)):
    return session.exec(select(Expedition)).all()

@router.get('/expeditions/{id}')
def get_expedition_by_id(id: int, session: Session = Depends(get_session)):
    expedition = session.exec(select(Expedition).where(Expedition.id == id)).first()
    if not expedition:
        raise HTTPException(status_code=404, detail=f'Expedition with id={id} not found')
    
    expedition_player_cards = session.exec(select(ExpeditionPlayerCard).where(ExpeditionPlayerCard.expedition_id==id)).all()
    barracks_ids = [card.player_card_id for card in expedition_player_cards if card.status == 'barracks']
    banished_ids = [card.player_card_id for card in expedition_player_cards if card.status == 'banished']

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