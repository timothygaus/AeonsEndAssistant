'''Shared helpers for driving an expedition through the API in tests.'''
from fastapi.testclient import TestClient

from app.enums import CardType, ExpeditionVariant
from app.rules import SUPPLY_SIZE

def create_expedition(
        client: TestClient,
        test_data,
        variant=ExpeditionVariant.STANDARD,
        base_length=4,
        big_pockets=False):
    response = client.post('/expeditions', json={
        'set_ids': [test_data['set_id']],
        'variant': variant.value,
        'base_length': base_length,
        'big_pockets': big_pockets,
    })
    assert response.status_code == 200, response.text
    return response.json()

def get_state(client: TestClient, expedition_id):
    response = client.get(f'/expeditions/{expedition_id}')
    assert response.status_code == 200, response.text
    return response.json()

def pending_battle(state):
    '''The attempt awaiting a result, or None once the expedition is complete.'''
    return next((b for b in state['battles'] if b['result'] is None), None)

def lock_battle(client: TestClient, expedition_id, num_mages=1):
    '''Locks in the first SUPPLY_SIZE barracks cards and the first mages.'''
    state = get_state(client, expedition_id)
    response = client.post(f'/expeditions/{expedition_id}/lock-battle', json={
        'supply_card_ids': [c['id'] for c in state['barracks_cards'][:SUPPLY_SIZE]],
        'mage_ids': [m['id'] for m in state['mages'][:num_mages]],
    })
    assert response.status_code == 200, response.text
    return response.json()

def resolve(client: TestClient, expedition_id, won, loss_randomizer_type=None):
    payload = {'won_battle': won}
    if loss_randomizer_type is not None:
        payload['loss_randomizer_type'] = loss_randomizer_type.value
    response = client.post(f'/expeditions/{expedition_id}/resolve-battle', json=payload)
    assert response.status_code == 200, response.text
    return response.json()

def play_battle(client: TestClient, expedition_id, won, loss_randomizer_type=None):
    '''Locks in a battle and records its result in one step.'''
    lock_battle(client, expedition_id)
    return resolve(client, expedition_id, won, loss_randomizer_type)

def barracks_by_type(state):
    return {
        card_type.value: [c for c in state['barracks_cards'] if c['type'] == card_type.value]
        for card_type in CardType
    }
