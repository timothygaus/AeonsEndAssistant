import pytest
from fastapi.testclient import TestClient

from app.enums import ExpeditionStatus, ExpeditionVariant, LossRandomizerType
from app.rules import SUPPLY_SIZE
from tests.helpers import create_expedition, get_state, lock_battle, pending_battle, play_battle

def play_to_completion(client: TestClient, expedition, expected_battles):
    '''Wins every battle, asserting the nemesis tier along the way.'''
    seen_tiers = []
    for _ in range(expected_battles):
        battle = pending_battle(get_state(client, expedition['id']))
        seen_tiers.append((battle['battle_number'], battle['nemesis']['expedition_battle']))
        expedition = play_battle(client, expedition['id'], won=True)
    return expedition, seen_tiers

@pytest.mark.parametrize('base_length', [4, 5])
def test_standard_expedition_runs_its_full_length(client: TestClient, test_data, base_length):
    expedition = create_expedition(client, test_data, base_length=base_length)
    assert get_state(client, expedition['id'])['total_battles'] == base_length

    expedition, tiers = play_to_completion(client, expedition, base_length)

    assert expedition['status'] == ExpeditionStatus.COMPLETE.value
    assert tiers == [(n, n) for n in range(1, base_length + 1)]

@pytest.mark.parametrize('base_length', [4, 5])
def test_short_expedition_skips_the_first_battle(client: TestClient, test_data, base_length):
    '''A short expedition opens against nemesis deck 2 and still ends at the base length.'''
    expedition = create_expedition(
        client, test_data, variant=ExpeditionVariant.SHORT, base_length=base_length
    )
    assert expedition['current_battle'] == 2

    expedition, tiers = play_to_completion(client, expedition, base_length - 1)

    assert expedition['status'] == ExpeditionStatus.COMPLETE.value
    assert tiers == [(n, n) for n in range(2, base_length + 1)]

@pytest.mark.parametrize('base_length', [4, 5])
def test_extended_expedition_doubles_and_pairs_tiers(client: TestClient, test_data, base_length):
    '''
    Extended is always exactly double the base length, spending two battles per
    nemesis deck and never repeating a nemesis.
    '''
    expedition = create_expedition(
        client, test_data, variant=ExpeditionVariant.EXTENDED, base_length=base_length
    )
    assert get_state(client, expedition['id'])['total_battles'] == base_length * 2

    expedition, tiers = play_to_completion(client, expedition, base_length * 2)
    assert expedition['status'] == ExpeditionStatus.COMPLETE.value

    expected = [(n, (n + 1) // 2) for n in range(1, base_length * 2 + 1)]
    assert tiers == expected

    fought = [b['nemesis']['id'] for b in get_state(client, expedition['id'])['battles']]
    assert len(fought) == len(set(fought)), 'a nemesis was fought twice'

def test_big_pockets_banishes_nothing(client: TestClient, test_data):
    expedition = create_expedition(client, test_data, big_pockets=True)
    play_battle(client, expedition['id'], won=True)

    state = get_state(client, expedition['id'])
    assert state['banished_cards'] == []
    assert len(state['barracks_cards']) == SUPPLY_SIZE + 3

    lock_battle(client, expedition['id'])
    state = get_state(client, expedition['id'])
    assert state['banished_cards'] == []
    assert len(state['barracks_cards']) == SUPPLY_SIZE + 3

def test_big_pockets_still_records_the_chosen_nine(client: TestClient, test_data):
    '''
    Nothing is banished, so the chosen supply is only recoverable because it is
    stored against the battle.
    '''
    expedition = create_expedition(client, test_data, big_pockets=True)
    play_battle(client, expedition['id'], won=True)

    state = get_state(client, expedition['id'])
    chosen = [c['id'] for c in state['barracks_cards'][:SUPPLY_SIZE]]
    client.post(f"/expeditions/{expedition['id']}/lock-battle", json={
        'supply_card_ids': chosen,
        'mage_ids': [state['mages'][0]['id']],
    })

    battle = pending_battle(get_state(client, expedition['id']))
    assert {c['id'] for c in battle['supply_cards']} == set(chosen)

def test_big_pockets_combines_with_short(client: TestClient, test_data):
    '''Big Pockets is a banishing rule, so it stacks with any variant.'''
    expedition = create_expedition(
        client, test_data, variant=ExpeditionVariant.SHORT, big_pockets=True
    )
    assert expedition['current_battle'] == 2
    assert expedition['big_pockets'] is True

    play_battle(client, expedition['id'], won=True)
    state = get_state(client, expedition['id'])

    assert state['banished_cards'] == []
    assert pending_battle(state)['nemesis']['expedition_battle'] == 3

def test_base_length_is_bounded(client: TestClient, test_data):
    for bad_length in (3, 6):
        response = client.post('/expeditions', json={
            'set_ids': [test_data['set_id']],
            'variant': ExpeditionVariant.STANDARD.value,
            'base_length': bad_length,
        })
        assert response.status_code == 422

def test_big_pockets_is_no_longer_a_variant(client: TestClient, test_data):
    response = client.post('/expeditions', json={
        'set_ids': [test_data['set_id']],
        'variant': 'big-pockets',
    })
    assert response.status_code == 422

def test_create_rejects_sets_that_cannot_field_every_tier(client: TestClient, session, test_data):
    '''
    A length-5 expedition needs a tier 5 nemesis. Failing at creation beats
    dead-ending at the final battle.
    '''
    from app.models import Nemesis
    from sqlmodel import select

    tier_five = session.exec(
        select(Nemesis).where(
            Nemesis.expedition_battle == 5, Nemesis.set_id == test_data['set_id']
        )
    ).all()
    for nemesis in tier_five:
        session.delete(nemesis)
    session.flush()

    response = client.post('/expeditions', json={
        'set_ids': [test_data['set_id']],
        'variant': ExpeditionVariant.STANDARD.value,
        'base_length': 5,
    })
    assert response.status_code == 400
    assert 'tier 5' in response.json()['detail']

    # The same sets are fine for the default length.
    assert create_expedition(client, test_data, base_length=4)

def test_extended_requires_two_nemeses_per_tier(client: TestClient, session, test_data):
    from app.models import Nemesis
    from sqlmodel import select

    duplicates = session.exec(
        select(Nemesis).where(
            Nemesis.expedition_battle == 3,
            Nemesis.set_id == test_data['set_id'],
        )
    ).all()
    session.delete(duplicates[0])
    session.flush()

    response = client.post('/expeditions', json={
        'set_ids': [test_data['set_id']],
        'variant': ExpeditionVariant.EXTENDED.value,
        'base_length': 4,
    })
    assert response.status_code == 400
    assert 'needs 2' in response.json()['detail']
