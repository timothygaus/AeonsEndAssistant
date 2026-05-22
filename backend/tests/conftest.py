import pytest
from fastapi.testclient import TestClient
from sqlmodel import create_engine, Session, SQLModel

from app.main import app
from app.database import get_session
from app.models import BreachMage, Nemesis, PlayerCard, Set
from app.enums import CardType

TEST_DATABASE_URL = 'postgresql://postgres:postgres@db:5432/aeonsend_test'

@pytest.fixture(scope='session')
def engine():
    test_engine = create_engine(TEST_DATABASE_URL)
    SQLModel.metadata.create_all(test_engine)
    yield test_engine
    SQLModel.metadata.drop_all(test_engine)

@pytest.fixture
def session(engine):
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def client(session):
    app.dependency_overrides[get_session] = lambda: session
    yield TestClient(app)
    app.dependency_overrides.clear()

@pytest.fixture
def test_data(session):
    test_set = Set(name='Test Set')
    test_set_2 = Set(name='Test Set 2')
    session.add(test_set)
    session.add(test_set_2)
    session.flush()

    # Valid options to choose from
    for i in range(10):
        session.add(PlayerCard(name=f'Gem {i}', type=CardType.GEM.value, is_supply=True, set_id=test_set.id))
    for i in range(8):
        session.add(PlayerCard(name=f'Relic {i}', type=CardType.RELIC.value, is_supply=True, set_id=test_set.id))
    for i in range(10):
        session.add(PlayerCard(name=f'Spell {i}', type=CardType.SPELL.value, is_supply=True, set_id=test_set.id))
    for i in range(8):
        session.add(BreachMage(name=f'Mage {i}', set_id=test_set.id))
    for tier in range(1, 5):
        session.add(Nemesis(name=f'Nemesis Tier {tier}', set_id=test_set.id, expedition_battle=tier, difficulty=tier))

    # Invalid options, these should not be chosen
    for i in range(5):
        session.add(PlayerCard(name=f'Bad Gem {i}', type=CardType.GEM.value, is_supply=True, set_id=test_set_2.id))
    for i in range(4):
        session.add(PlayerCard(name=f'Bad Relic {i}', type=CardType.RELIC.value, is_supply=True, set_id=test_set_2.id))
    for i in range(6):
        session.add(PlayerCard(name=f'Bad Spell {i}', type=CardType.SPELL.value, is_supply=True, set_id=test_set_2.id))
    for i in range(6):
        session.add(BreachMage(name=f'Bad Mage {i}', set_id=test_set_2.id))
    for tier in range(1, 5):
        session.add(Nemesis(name=f'Bad Nemesis Tier {tier}', set_id=test_set_2.id, expedition_battle=tier, difficulty=tier))
    
    session.flush()
    return {'set_id': test_set.id}
