from typing import Optional

from sqlmodel import SQLModel

from app.enums import ExpeditionVariant, LossRandomizerType
from app.models import BreachMage, Expedition, Nemesis, PlayerCard

class ExpeditionCreate(SQLModel):
    name: Optional[str] = None
    set_ids: list[int]
    variant: ExpeditionVariant = ExpeditionVariant.STANDARD

class BattleDetail(SQLModel):
    battle_number: int
    result: Optional[str]
    nemesis: Nemesis

class ExpeditionStateResponse(SQLModel):
    expedition: Expedition
    barracks_cards: list[PlayerCard]
    banished_cards: list[PlayerCard]
    mages: list[BreachMage]
    battles: list[BattleDetail]

class ResolveBattleRequest(SQLModel):
    won_battle: bool
    loss_randomizer_type: Optional[LossRandomizerType] = None

class QuickplayResponse(SQLModel):
    player_cards: list[PlayerCard]
    mages: list[BreachMage]
    nemesis: Nemesis