from typing import Optional

from pydantic import Field as PydanticField
from sqlmodel import SQLModel

from app.enums import ExpeditionVariant, LossRandomizerType
from app.models import BreachMage, Expedition, Nemesis, PlayerCard
from app.rules import MAX_BASE_LENGTH, MIN_BASE_LENGTH

class ExpeditionCreate(SQLModel):
    name: Optional[str] = None
    set_ids: list[int]
    variant: ExpeditionVariant = ExpeditionVariant.STANDARD
    base_length: int = PydanticField(
        default=MIN_BASE_LENGTH, ge=MIN_BASE_LENGTH, le=MAX_BASE_LENGTH
    )
    big_pockets: bool = False

class BattleDetail(SQLModel):
    battle_number: int
    attempt: int
    result: Optional[str]
    locked: bool
    nemesis: Nemesis
    mages: list[BreachMage]
    supply_cards: list[PlayerCard]

class ExpeditionStateResponse(SQLModel):
    expedition: Expedition
    # Total battles including the extended variant's doubling, so the client can
    # render "battle 3 of 8" without reimplementing the rules.
    total_battles: int
    barracks_cards: list[PlayerCard]
    banished_cards: list[PlayerCard]
    mages: list[BreachMage]
    battles: list[BattleDetail]

class LockBattleRequest(SQLModel):
    '''
    The player's choices for the pending battle: exactly 9 supply cards and
    between 1 and 4 mages, all drawn from the barracks. Barracks cards left
    unselected are banished unless Big Pockets is enabled.
    '''
    supply_card_ids: list[int]
    mage_ids: list[int]

class ResolveBattleRequest(SQLModel):
    won_battle: bool
    loss_randomizer_type: Optional[LossRandomizerType] = None

class QuickplayResponse(SQLModel):
    player_cards: list[PlayerCard]
    mages: list[BreachMage]
    nemesis: Nemesis
