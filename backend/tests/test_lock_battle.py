from fastapi.testclient import TestClient

from app.enums import ExpeditionVariant, LossRandomizerType
from app.rules import MAX_MAGES, SUPPLY_SIZE
from tests.helpers import create_expedition, get_state, lock_battle, pending_battle, play_battle, resolve

def lock(client: TestClient, expedition_id, supply_card_ids, mage_ids):
    return client.post(f'/expeditions/{expedition_id}/lock-battle', json={
        'supply_card_ids': supply_card_ids,
        'mage_ids': mage_ids,
    })

def test_lock_banishes_everything_unselected(client: TestClient, test_data):
    expedition = create_expedition(client, test_data)
    play_battle(client, expedition['id'], won=True)

    state = get_state(client, expedition['id'])
    assert len(state['barracks_cards']) == SUPPLY_SIZE + 3

    kept = [c['id'] for c in state['barracks_cards'][:SUPPLY_SIZE]]
    dropped = {c['id'] for c in state['barracks_cards'][SUPPLY_SIZE:]}
    response = lock(client, expedition['id'], kept, [state['mages'][0]['id']])
    assert response.status_code == 200

    state = get_state(client, expedition['id'])
    assert {c['id'] for c in state['barracks_cards']} == set(kept)
    assert dropped <= {c['id'] for c in state['banished_cards']}

def test_lock_records_the_chosen_supply_and_mages(client: TestClient, test_data):
    expedition = create_expedition(client, test_data)
    state = get_state(client, expedition['id'])
    mage_ids = [m['id'] for m in state['mages'][:2]]
    card_ids = [c['id'] for c in state['barracks_cards'][:SUPPLY_SIZE]]

    lock(client, expedition['id'], card_ids, mage_ids)

    battle = pending_battle(get_state(client, expedition['id']))
    assert battle['locked'] is True
    assert {m['id'] for m in battle['mages']} == set(mage_ids)
    assert {c['id'] for c in battle['supply_cards']} == set(card_ids)

def test_lock_rejects_a_supply_that_is_not_nine_cards(client: TestClient, test_data):
    expedition = create_expedition(client, test_data)
    state = get_state(client, expedition['id'])
    mage_ids = [state['mages'][0]['id']]

    too_few = [c['id'] for c in state['barracks_cards'][:SUPPLY_SIZE - 1]]
    response = lock(client, expedition['id'], too_few, mage_ids)
    assert response.status_code == 400
    assert str(SUPPLY_SIZE) in response.json()['detail']

def test_lock_rejects_cards_from_another_expedition(client: TestClient, test_data):
    mine = create_expedition(client, test_data)
    theirs = create_expedition(client, test_data)

    my_state = get_state(client, mine['id'])
    their_state = get_state(client, theirs['id'])
    foreign = [c['id'] for c in their_state['barracks_cards'] if c['id'] not in
               {c['id'] for c in my_state['barracks_cards']}]
    assert foreign, 'fixture should give the two expeditions different cards'

    mixed = [c['id'] for c in my_state['barracks_cards'][:SUPPLY_SIZE - 1]] + foreign[:1]
    response = lock(client, mine['id'], mixed, [my_state['mages'][0]['id']])
    assert response.status_code == 400
    assert 'barracks' in response.json()['detail']

def test_lock_rejects_duplicate_ids(client: TestClient, test_data):
    expedition = create_expedition(client, test_data)
    state = get_state(client, expedition['id'])
    card_ids = [c['id'] for c in state['barracks_cards'][:SUPPLY_SIZE]]

    response = lock(client, expedition['id'], card_ids[:-1] + [card_ids[0]],
                    [state['mages'][0]['id']])
    assert response.status_code == 400
    assert 'duplicate' in response.json()['detail'].lower()

def test_lock_rejects_too_few_mages(client: TestClient, test_data):
    expedition = create_expedition(client, test_data)
    state = get_state(client, expedition['id'])
    card_ids = [c['id'] for c in state['barracks_cards'][:SUPPLY_SIZE]]

    response = lock(client, expedition['id'], card_ids, [])
    assert response.status_code == 400
    assert 'between' in response.json()['detail'].lower()

def test_lock_rejects_too_many_mages(client: TestClient, test_data):
    '''
    The barracks starts with exactly MAX_MAGES mages, so lose a battle taking a
    mage randomizer to get a fifth into the barracks first.
    '''
    expedition = create_expedition(client, test_data)
    play_battle(client, expedition['id'], won=False,
                loss_randomizer_type=LossRandomizerType.MAGE)

    state = get_state(client, expedition['id'])
    assert len(state['mages']) == MAX_MAGES + 1

    response = lock(
        client,
        expedition['id'],
        [c['id'] for c in state['barracks_cards'][:SUPPLY_SIZE]],
        [m['id'] for m in state['mages']],
    )
    assert response.status_code == 400
    assert 'between' in response.json()['detail'].lower()

def test_lock_rejects_mages_not_in_the_barracks(client: TestClient, test_data):
    expedition = create_expedition(client, test_data)
    state = get_state(client, expedition['id'])
    card_ids = [c['id'] for c in state['barracks_cards'][:SUPPLY_SIZE]]

    response = lock(client, expedition['id'], card_ids, [9999])
    assert response.status_code == 400
    assert 'barracks' in response.json()['detail']

def test_cannot_lock_the_same_battle_twice(client: TestClient, test_data):
    expedition = create_expedition(client, test_data)
    lock_battle(client, expedition['id'])
    state = get_state(client, expedition['id'])

    response = lock(
        client,
        expedition['id'],
        [c['id'] for c in state['barracks_cards'][:SUPPLY_SIZE]],
        [state['mages'][0]['id']],
    )
    assert response.status_code == 400
    assert 'already been locked' in response.json()['detail']

def test_resolve_requires_a_locked_battle(client: TestClient, test_data):
    expedition = create_expedition(client, test_data)
    response = client.post(
        f"/expeditions/{expedition['id']}/resolve-battle", json={'won_battle': True}
    )
    assert response.status_code == 400
    assert 'locked in' in response.json()['detail']

def test_a_retry_after_a_loss_must_be_locked_again(client: TestClient, test_data):
    '''
    The repeated fight follows the start-of-fight rules again, so the player
    re-picks their supply and mages and banishes what is left over.
    '''
    expedition = create_expedition(client, test_data)
    play_battle(client, expedition['id'], won=False,
                loss_randomizer_type=LossRandomizerType.GEM)

    state = get_state(client, expedition['id'])
    assert pending_battle(state)['locked'] is False
    assert len(state['barracks_cards']) == SUPPLY_SIZE + 1

    response = client.post(
        f"/expeditions/{expedition['id']}/resolve-battle", json={'won_battle': True}
    )
    assert response.status_code == 400

    lock_battle(client, expedition['id'])
    state = get_state(client, expedition['id'])
    assert len(state['barracks_cards']) == SUPPLY_SIZE
    assert len(state['banished_cards']) == 1
