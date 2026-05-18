from typing import Optional
from sqlmodel import SQLModel
from app.models import PlayerCard, BreachMage, Nemesis, Expedition, ExpeditionBattle

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