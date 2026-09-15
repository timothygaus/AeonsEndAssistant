from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.enums import LossRandomizerType
from app.models import (
    ExpeditionBattle,
    ExpeditionBattleCard,
    ExpeditionBattleMage,
    ExpeditionMage,
    ExpeditionPlayerCard,
    ExpeditionSet,
)
from tests.helpers import create_expedition, lock_battle, play_battle

def test_delete_removes_every_trace(client: TestClient, session: Session, test_data):
    expedition = create_expedition(client, test_data)
    play_battle(client, expedition['id'], won=False,
                loss_randomizer_type=LossRandomizerType.MAGE)
    lock_battle(client, expedition['id'])

    response = client.delete(f"/expeditions/{expedition['id']}")
    assert response.status_code == 204
    assert client.get(f"/expeditions/{expedition['id']}").status_code == 404

    battle_ids = session.exec(
        select(ExpeditionBattle.id).where(ExpeditionBattle.expedition_id == expedition['id'])
    ).all()
    assert battle_ids == []
    for model in (ExpeditionMage, ExpeditionPlayerCard, ExpeditionSet):
        rows = session.exec(
            select(model).where(model.expedition_id == expedition['id'])
        ).all()
        assert rows == [], f'{model.__name__} rows survived the delete'
    assert session.exec(select(ExpeditionBattleMage)).all() == []
    assert session.exec(select(ExpeditionBattleCard)).all() == []

def test_delete_leaves_other_expeditions_alone(client: TestClient, test_data):
    doomed = create_expedition(client, test_data)
    survivor = create_expedition(client, test_data)
    lock_battle(client, survivor['id'])

    assert client.delete(f"/expeditions/{doomed['id']}").status_code == 204

    response = client.get(f"/expeditions/{survivor['id']}")
    assert response.status_code == 200
    assert response.json()['battles'][0]['locked'] is True

def test_delete_unknown_expedition_is_a_404(client: TestClient):
    assert client.delete('/expeditions/999').status_code == 404
