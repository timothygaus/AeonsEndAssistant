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
