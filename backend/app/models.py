from datetime import datetime, timezone
from typing import Optional
from sqlmodel import Field, SQLModel

class Set(SQLModel, table=True):
    __tablename__ = 'sets'

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str

class PlayerCard(SQLModel, table=True):
    __tablename__ = 'player_cards'

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    type: str
    is_supply: bool
    set_id: int = Field(foreign_key='sets.id')

class BreachMage(SQLModel, table=True):
    __tablename__ = 'breach_mages'

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    set_id: int = Field(foreign_key='sets.id')
    complexity: Optional[int] = None

class Nemesis(SQLModel, table=True):
    __tablename__ = 'nemeses'

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    set_id: int = Field(foreign_key='sets.id')
    expedition_battle: Optional[int] = None
    difficulty: Optional[int] = None

class Expedition(SQLModel, table=True):
    __tablename__ = 'expeditions'

    id: Optional[int] = Field(default=None, primary_key=True)
    name: Optional[str] = None
    status: str = 'active'
    current_battle: int = 1
    variant: str = 'standard'
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ExpeditionSet(SQLModel, table=True):
    __tablename__ = 'expedition_sets'

    id: Optional[int] = Field(default=None, primary_key=True)
    expedition_id: int = Field(foreign_key='expeditions.id')
    set_id: int = Field(foreign_key='sets.id')
class ExpeditionPlayerCard(SQLModel, table=True):
    __tablename__ = 'expedition_player_cards'

    id: Optional[int] = Field(default=None, primary_key=True)
    expedition_id: int = Field(foreign_key='expeditions.id')
    player_card_id: int = Field(foreign_key='player_cards.id')
    status: str # 'barracks', 'banished'

class ExpeditionMage(SQLModel, table=True):
    __tablename__ = 'expedition_mages'

    id: Optional[int] = Field(default=None, primary_key=True)
    expedition_id: int = Field(foreign_key='expeditions.id')
    mage_id: int = Field(foreign_key='breach_mages.id')

class ExpeditionBattle(SQLModel, table=True):
    __tablename__ = 'expedition_battles'

    id: Optional[int] = Field(default=None, primary_key=True)
    expedition_id: int = Field(foreign_key='expeditions.id')
    battle_number: int
    nemesis_id: int = Field(foreign_key='nemeses.id')
    result: Optional[str] = None
