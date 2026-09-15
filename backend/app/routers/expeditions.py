import random

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import col, delete, select, Session, update

from app.database import get_session
from app.enums import (
    BattleResult,
    CardType,
    ExpeditionStatus,
    ExpeditionVariant,
    LossRandomizerType,
    SupplyCardStatus,
)
from app.models import (
    BreachMage,
    Expedition,
    ExpeditionBattle,
    ExpeditionBattleCard,
    ExpeditionBattleMage,
    ExpeditionMage,
    ExpeditionPlayerCard,
    ExpeditionSet,
    Nemesis,
    PlayerCard,
)
from app.rules import (
    MAX_MAGES,
    MIN_MAGES,
    STARTING_MAGES,
    STARTING_SUPPLY,
    SUPPLY_SIZE,
    effective_length,
    first_battle_number,
    nemesis_tier,
    required_nemesis_tiers,
)
from app.schemas import (
    BattleDetail,
    ExpeditionCreate,
    ExpeditionStateResponse,
    LockBattleRequest,
    ResolveBattleRequest,
)

router = APIRouter()

@router.get('/expeditions')
def get_expeditions(session: Session = Depends(get_session)):
    return session.exec(select(Expedition)).all()

@router.post('/expeditions')
def create_expedition(data: ExpeditionCreate, session: Session = Depends(get_session)):
    if not data.set_ids:
        raise HTTPException(status_code=400, detail='At least one set must be selected')

    # Checked up front: an expedition that cannot field a nemesis for its final
    # battle would otherwise create cleanly and then dead-end hours later.
    validate_nemesis_pools(session, data.variant, data.base_length, data.set_ids)

    start_battle = first_battle_number(data.variant)
    expedition = Expedition(
        name=data.name,
        variant=data.variant,
        current_battle=start_battle,
        base_length=data.base_length,
        big_pockets=data.big_pockets,
    )
    session.add(expedition)
    session.flush()

    for set_id in data.set_ids:
        session.add(ExpeditionSet(expedition_id=expedition.id, set_id=set_id))

    for card_type, count in STARTING_SUPPLY.items():
        draw_supply(session, expedition.id, CardType(card_type), count, data.set_ids)

    mage_pool = session.exec(
        select(BreachMage).where(col(BreachMage.set_id).in_(data.set_ids))
    ).all()
    if len(mage_pool) < STARTING_MAGES:
        raise HTTPException(
            status_code=400,
            detail=f'Selected sets have {len(mage_pool)} mages, but {STARTING_MAGES} are needed to start'
        )
    for mage in random.sample(mage_pool, STARTING_MAGES):
        session.add(ExpeditionMage(expedition_id=expedition.id, mage_id=mage.id))

    draw_next_battle(session, expedition, data.set_ids, start_battle)

    session.commit()
    session.refresh(expedition)
    return expedition

@router.get('/expeditions/active')
def get_active_expeditions(session: Session = Depends(get_session)):
    return session.exec(
        select(Expedition).where(Expedition.status == ExpeditionStatus.ACTIVE)
    ).all()

@router.get('/expeditions/{expedition_id}', response_model=ExpeditionStateResponse)
def get_expedition_by_id(expedition_id: int, session: Session = Depends(get_session)):
    return build_state(session, expedition_id)

@router.post('/expeditions/{expedition_id}/lock-battle', response_model=ExpeditionStateResponse)
def lock_battle(
        expedition_id: int,
        data: LockBattleRequest,
        session: Session = Depends(get_session)):
    '''
    Commits the player's supply and mage choices for the pending battle. Barracks
    cards left unselected are banished for the rest of the expedition, unless Big
    Pockets is enabled, in which case they return to the barracks.
    '''
    expedition = get_exp(session, expedition_id)
    if expedition.status == ExpeditionStatus.COMPLETE:
        raise HTTPException(status_code=400, detail='This expedition is already complete')

    battle = get_pending_battle(session, expedition_id)
    if battle.locked:
        raise HTTPException(status_code=400, detail='This battle has already been locked in')

    mage_ids = validate_selection(
        data.mage_ids,
        available=set(session.exec(
            select(ExpeditionMage.mage_id).where(ExpeditionMage.expedition_id == expedition_id)
        ).all()),
        label='mage',
        minimum=MIN_MAGES,
        maximum=MAX_MAGES,
    )
    barracks_card_ids = set(session.exec(
        select(ExpeditionPlayerCard.player_card_id).where(
            ExpeditionPlayerCard.expedition_id == expedition_id,
            ExpeditionPlayerCard.status == SupplyCardStatus.BARRACKS,
        )
    ).all())
    supply_card_ids = validate_selection(
        data.supply_card_ids,
        available=barracks_card_ids,
        label='supply card',
        minimum=SUPPLY_SIZE,
        maximum=SUPPLY_SIZE,
    )

    for mage_id in mage_ids:
        session.add(ExpeditionBattleMage(battle_id=battle.id, mage_id=mage_id))
    for card_id in supply_card_ids:
        session.add(ExpeditionBattleCard(battle_id=battle.id, player_card_id=card_id))

    if not expedition.big_pockets:
        banished = barracks_card_ids - supply_card_ids
        if banished:
            session.exec(
                update(ExpeditionPlayerCard)
                .where(ExpeditionPlayerCard.expedition_id == expedition_id)
                .where(col(ExpeditionPlayerCard.player_card_id).in_(banished))
                .values(status=SupplyCardStatus.BANISHED)
            )

    battle.locked = True
    session.add(battle)
    session.commit()
    return build_state(session, expedition_id)

@router.post('/expeditions/{expedition_id}/resolve-battle')
def resolve_battle(
        expedition_id: int,
        data: ResolveBattleRequest,
        session: Session = Depends(get_session)):
    expedition = get_exp(session, expedition_id)
    if expedition.status == ExpeditionStatus.COMPLETE:
        raise HTTPException(status_code=400, detail='This expedition is already complete')

    battle = get_pending_battle(session, expedition_id)
    if not battle.locked:
        raise HTTPException(
            status_code=400,
            detail='The supply and mages must be locked in before recording a result'
        )
    if not data.won_battle and data.loss_randomizer_type is None:
        raise HTTPException(
            status_code=400,
            detail='A randomizer type must be chosen when a battle is lost'
        )

    variant = ExpeditionVariant(expedition.variant)
    set_ids = [
        exp_set.set_id for exp_set in session.exec(
            select(ExpeditionSet).where(ExpeditionSet.expedition_id == expedition_id)
        ).all()
    ]

    if data.won_battle:
        battle.result = BattleResult.WIN
        session.add(battle)

        if battle.battle_number >= effective_length(variant, expedition.base_length):
            expedition.status = ExpeditionStatus.COMPLETE
            session.add(expedition)
            session.commit()
            session.refresh(expedition)
            return expedition

        expedition.current_battle = battle.battle_number + 1
        for card_type in (CardType.GEM, CardType.RELIC, CardType.SPELL):
            draw_supply(session, expedition_id, card_type, 1, set_ids)
        draw_next_battle(session, expedition, set_ids, expedition.current_battle)
    else:
        battle.result = BattleResult.LOSS
        session.add(battle)

        if data.loss_randomizer_type == LossRandomizerType.MAGE:
            draw_mage(session, expedition_id, set_ids)
        elif data.loss_randomizer_type != LossRandomizerType.TREASURE:
            # Treasures are out of scope for this app; the player takes one at
            # the table and the barracks is left untouched.
            draw_supply(
                session, expedition_id, CardType(data.loss_randomizer_type.value), 1, set_ids
            )

        # The fight repeats against the same nemesis, following the start-of-fight
        # rules again, so a fresh unlocked attempt is opened.
        session.add(ExpeditionBattle(
            expedition_id=expedition_id,
            battle_number=battle.battle_number,
            attempt=battle.attempt + 1,
            nemesis_id=battle.nemesis_id,
        ))

    session.add(expedition)
    session.commit()
    session.refresh(expedition)
    return expedition

@router.delete('/expeditions/{expedition_id}', status_code=204)
def delete_expedition(expedition_id: int, session: Session = Depends(get_session)):
    get_exp(session, expedition_id)

    battle_ids = session.exec(
        select(ExpeditionBattle.id).where(ExpeditionBattle.expedition_id == expedition_id)
    ).all()
    if battle_ids:
        session.exec(
            delete(ExpeditionBattleMage).where(col(ExpeditionBattleMage.battle_id).in_(battle_ids))
        )
        session.exec(
            delete(ExpeditionBattleCard).where(col(ExpeditionBattleCard.battle_id).in_(battle_ids))
        )
    session.exec(delete(ExpeditionBattle).where(ExpeditionBattle.expedition_id == expedition_id))
    session.exec(delete(ExpeditionMage).where(ExpeditionMage.expedition_id == expedition_id))
    session.exec(delete(ExpeditionPlayerCard).where(ExpeditionPlayerCard.expedition_id == expedition_id))
    session.exec(delete(ExpeditionSet).where(ExpeditionSet.expedition_id == expedition_id))
    session.exec(delete(Expedition).where(Expedition.id == expedition_id))
    session.commit()

def build_state(session: Session, expedition_id: int) -> ExpeditionStateResponse:
    expedition = get_exp(session, expedition_id)

    expedition_player_cards = session.exec(
        select(ExpeditionPlayerCard).where(ExpeditionPlayerCard.expedition_id == expedition_id)
    ).all()
    barracks_ids = [
        c.player_card_id for c in expedition_player_cards
        if c.status == SupplyCardStatus.BARRACKS
    ]
    banished_ids = [
        c.player_card_id for c in expedition_player_cards
        if c.status == SupplyCardStatus.BANISHED
    ]

    mage_ids = session.exec(
        select(ExpeditionMage.mage_id).where(ExpeditionMage.expedition_id == expedition_id)
    ).all()

    battles = session.exec(
        select(ExpeditionBattle)
        .where(ExpeditionBattle.expedition_id == expedition_id)
        .order_by(col(ExpeditionBattle.battle_number), col(ExpeditionBattle.attempt))
    ).all()

    battle_details = []
    for battle in battles:
        battle_mage_ids = session.exec(
            select(ExpeditionBattleMage.mage_id).where(ExpeditionBattleMage.battle_id == battle.id)
        ).all()
        battle_card_ids = session.exec(
            select(ExpeditionBattleCard.player_card_id).where(
                ExpeditionBattleCard.battle_id == battle.id
            )
        ).all()
        battle_details.append(BattleDetail(
            battle_number=battle.battle_number,
            attempt=battle.attempt,
            result=battle.result,
            locked=battle.locked,
            nemesis=session.get(Nemesis, battle.nemesis_id),
            mages=fetch_by_ids(session, BreachMage, battle_mage_ids),
            supply_cards=fetch_by_ids(session, PlayerCard, battle_card_ids),
        ))

    return ExpeditionStateResponse(
        expedition=expedition,
        total_battles=effective_length(
            ExpeditionVariant(expedition.variant), expedition.base_length
        ),
        barracks_cards=fetch_by_ids(session, PlayerCard, barracks_ids),
        banished_cards=fetch_by_ids(session, PlayerCard, banished_ids),
        mages=fetch_by_ids(session, BreachMage, mage_ids),
        battles=battle_details,
    )

def validate_selection(
        selected: list[int],
        available: set[int],
        label: str,
        minimum: int,
        maximum: int) -> set[int]:
    '''
    Checks a client-supplied list of ids against what the barracks actually holds
    and returns it as a set. Rejects duplicates, out-of-range counts and anything
    the expedition does not own.
    '''
    unique = set(selected)
    if len(unique) != len(selected):
        raise HTTPException(status_code=400, detail=f'Duplicate {label} ids were submitted')

    if minimum == maximum and len(unique) != minimum:
        raise HTTPException(
            status_code=400,
            detail=f'Exactly {minimum} {label}s must be chosen, got {len(unique)}'
        )
    if not minimum <= len(unique) <= maximum:
        raise HTTPException(
            status_code=400,
            detail=f'Between {minimum} and {maximum} {label}s must be chosen, got {len(unique)}'
        )

    unavailable = unique - available
    if unavailable:
        raise HTTPException(
            status_code=400,
            detail=f'{label.capitalize()}s {sorted(unavailable)} are not in this expedition\'s barracks'
        )
    return unique

def validate_nemesis_pools(
        session: Session,
        variant: ExpeditionVariant,
        base_length: int,
        set_ids: list[int]) -> None:
    for tier, needed in required_nemesis_tiers(variant, base_length).items():
        available = session.exec(
            select(Nemesis).where(
                Nemesis.expedition_battle == tier,
                col(Nemesis.set_id).in_(set_ids),
            )
        ).all()
        if len(available) < needed:
            raise HTTPException(
                status_code=400,
                detail=(
                    f'Selected sets have {len(available)} nemeses for battle tier {tier}, '
                    f'but this expedition needs {needed}'
                )
            )

def draw_next_battle(
        session: Session,
        expedition: Expedition,
        set_ids: list[int],
        battle_number: int) -> ExpeditionBattle:
    fought_nemesis_ids = session.exec(
        select(ExpeditionBattle.nemesis_id).where(
            ExpeditionBattle.expedition_id == expedition.id
        )
    ).all()
    tier = nemesis_tier(ExpeditionVariant(expedition.variant), battle_number)

    pool = session.exec(
        select(Nemesis).where(
            Nemesis.expedition_battle == tier,
            col(Nemesis.set_id).in_(set_ids),
            col(Nemesis.id).not_in(fought_nemesis_ids),
        )
    ).all()
    if not pool:
        raise HTTPException(
            status_code=400,
            detail=f'No unfought nemesis available for battle tier {tier}'
        )

    battle = ExpeditionBattle(
        expedition_id=expedition.id,
        battle_number=battle_number,
        nemesis_id=random.choice(pool).id,
    )
    session.add(battle)
    return battle

def draw_mage(session: Session, expedition_id: int, set_ids: list[int]) -> None:
    expedition_mage_ids = session.exec(
        select(ExpeditionMage.mage_id).where(ExpeditionMage.expedition_id == expedition_id)
    ).all()
    pool = session.exec(
        select(BreachMage).where(
            col(BreachMage.id).not_in(expedition_mage_ids),
            col(BreachMage.set_id).in_(set_ids),
        )
    ).all()
    if not pool:
        raise HTTPException(
            status_code=400,
            detail="No unused mages found for this expedition's sets"
        )
    session.add(ExpeditionMage(expedition_id=expedition_id, mage_id=random.choice(pool).id))

def draw_supply(
        session: Session,
        expedition_id: int,
        card_type: CardType,
        count: int,
        set_ids: list[int]) -> None:
    used_card_ids = session.exec(
        select(ExpeditionPlayerCard.player_card_id).where(
            ExpeditionPlayerCard.expedition_id == expedition_id
        )
    ).all()

    pool = session.exec(
        select(PlayerCard).where(
            PlayerCard.type == card_type,
            PlayerCard.is_supply == True,  # noqa: E712 - SQL comparison, not a bool check
            col(PlayerCard.set_id).in_(set_ids),
            col(PlayerCard.id).not_in(used_card_ids),
        )
    ).all()

    if len(pool) < count:
        raise HTTPException(
            status_code=400,
            detail=f'Not enough undrawn {card_type.value}s in the selected sets'
        )

    for card in random.sample(pool, count):
        session.add(ExpeditionPlayerCard(
            expedition_id=expedition_id,
            player_card_id=card.id,
            status=SupplyCardStatus.BARRACKS,
        ))

def fetch_by_ids(session: Session, model, ids) -> list:
    '''Fetches rows by id, preserving nothing in particular about order.'''
    ids = list(ids)
    if not ids:
        return []
    return list(session.exec(select(model).where(col(model.id).in_(ids))).all())

def get_pending_battle(session: Session, expedition_id: int) -> ExpeditionBattle:
    '''The attempt awaiting a result. Exactly one exists on an active expedition.'''
    battle = session.exec(
        select(ExpeditionBattle).where(
            ExpeditionBattle.expedition_id == expedition_id,
            col(ExpeditionBattle.result).is_(None),
        )
    ).first()
    if not battle:
        raise HTTPException(
            status_code=409,
            detail='This expedition has no battle awaiting a result'
        )
    return battle

def get_exp(session: Session, id: int) -> Expedition:
    expedition = session.exec(select(Expedition).where(Expedition.id == id)).first()
    if not expedition:
        raise HTTPException(status_code=404, detail=f'Expedition with id={id} not found')
    return expedition
