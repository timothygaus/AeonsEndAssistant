from datetime import datetime, timezone
from typing import Optional
from sqlmodel import Field, SQLModel

from app.enums import ExpeditionStatus, ExpeditionVariant
from app.rules import MIN_BASE_LENGTH

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
    status: str = ExpeditionStatus.ACTIVE.value
    current_battle: int = 1
    variant: str = ExpeditionVariant.STANDARD.value
    # Battles before the extended variant doubles it. See app.rules.
    base_length: int = MIN_BASE_LENGTH
    # A banishing rule, independent of the variant: unused supply cards return
    # to the barracks instead of being banished.
    big_pockets: bool = False
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
    status: str

class ExpeditionMage(SQLModel, table=True):
    __tablename__ = 'expedition_mages'

    id: Optional[int] = Field(default=None, primary_key=True)
    expedition_id: int = Field(foreign_key='expeditions.id')
    mage_id: int = Field(foreign_key='breach_mages.id')

class ExpeditionBattle(SQLModel, table=True):
    '''
    One row per attempt at a battle. Losing a battle closes the current row and
    opens a fresh one against the same nemesis, so the pending attempt is always
    the row whose result is null.
    '''
    __tablename__ = 'expedition_battles'

    id: Optional[int] = Field(default=None, primary_key=True)
    expedition_id: int = Field(foreign_key='expeditions.id')
    battle_number: int
    attempt: int = 1
    nemesis_id: int = Field(foreign_key='nemeses.id')
    result: Optional[str]
    # Set once the player has committed their supply and mages for this attempt.
    locked: bool = False

class ExpeditionBattleMage(SQLModel, table=True):
    '''Which mages were taken into a given battle attempt.'''
    __tablename__ = 'expedition_battle_mages'

    id: Optional[int] = Field(default=None, primary_key=True)
    battle_id: int = Field(foreign_key='expedition_battles.id')
    mage_id: int = Field(foreign_key='breach_mages.id')

class ExpeditionBattleCard(SQLModel, table=True):
    '''
    Which 9 supply cards were taken into a given battle attempt. Without this the
    choice would only be recoverable by inference from what was banished, which
    does not work under Big Pockets since nothing is banished.
    '''
    __tablename__ = 'expedition_battle_cards'

    id: Optional[int] = Field(default=None, primary_key=True)
    battle_id: int = Field(foreign_key='expedition_battles.id')
    player_card_id: int = Field(foreign_key='player_cards.id')

class UserSet(SQLModel, table=True):
    __tablename__ = 'user_sets'

    id: Optional[int] = Field(default=None, primary_key=True)
    set_id: int