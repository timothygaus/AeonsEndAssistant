from fastapi.testclient import TestClient

from app.enums import BattleResult, ExpeditionStatus, ExpeditionVariant, LossRandomizerType
from app.rules import STARTING_MAGES, SUPPLY_SIZE
from tests.helpers import (
    barracks_by_type,
    create_expedition,
    get_state,
    lock_battle,
    pending_battle,
    play_battle,
    resolve,
)

def test_create_expedition(client: TestClient, test_data):
    '''
    A new expedition draws its starting barracks, four mages and a first battle,
    all from the selected sets.
    '''
    expedition = create_expedition(client, test_data)
    state = get_state(client, expedition['id'])
    cards = barracks_by_type(state)

    assert len(cards['gem']) == 3
    assert len(cards['relic']) == 2
    assert len(cards['spell']) == 4
    assert len(state['mages']) == STARTING_MAGES
    assert state['total_battles'] == 4

    battle = pending_battle(state)
    assert battle['battle_number'] == 1
    assert battle['attempt'] == 1
    assert battle['locked'] is False
    assert battle['nemesis']['expedition_battle'] == 1

    assert all(c['set_id'] == test_data['set_id'] for c in state['barracks_cards'])
    assert all(m['set_id'] == test_data['set_id'] for m in state['mages'])
    assert battle['nemesis']['set_id'] == test_data['set_id']

def test_resolve_battle_win(client: TestClient, test_data):
    '''
    Winning records the result, advances the battle number, adds one card of each
    type to the barracks and draws the next nemesis one tier up.
    '''
    expedition = create_expedition(client, test_data)
    before = barracks_by_type(get_state(client, expedition['id']))

    expedition = play_battle(client, expedition['id'], won=True)
    state = get_state(client, expedition['id'])
    after = barracks_by_type(state)

    assert expedition['current_battle'] == 2
    assert len(after['gem']) == len(before['gem']) + 1
    assert len(after['relic']) == len(before['relic']) + 1
    assert len(after['spell']) == len(before['spell']) + 1

    fought = [b for b in state['battles'] if b['result'] is not None]
    assert [b['result'] for b in fought] == [BattleResult.WIN.value]

    battle = pending_battle(state)
    assert battle['battle_number'] == 2
    assert battle['attempt'] == 1
    assert battle['locked'] is False
    assert battle['nemesis']['expedition_battle'] == 2

def test_loss_reopens_the_same_battle(client: TestClient, test_data):
    '''
    Losing must leave a pending attempt against the same nemesis. Without one the
    expedition has no current battle and cannot be resumed.
    '''
    expedition = create_expedition(client, test_data)
    lost_nemesis = pending_battle(get_state(client, expedition['id']))['nemesis']

    expedition = play_battle(
        client, expedition['id'], won=False, loss_randomizer_type=LossRandomizerType.GEM
    )
    state = get_state(client, expedition['id'])

    assert expedition['current_battle'] == 1
    battle = pending_battle(state)
    assert battle is not None
    assert battle['battle_number'] == 1
    assert battle['attempt'] == 2
    assert battle['locked'] is False
    assert battle['nemesis']['id'] == lost_nemesis['id']

def test_repeated_losses_record_each_attempt(client: TestClient, test_data):
    '''Every loss is its own row, so the history shows all three attempts.'''
    expedition = create_expedition(client, test_data)
    for _ in range(2):
        play_battle(
            client, expedition['id'], won=False, loss_randomizer_type=LossRandomizerType.GEM
        )

    state = get_state(client, expedition['id'])
    battle_one = [b for b in state['battles'] if b['battle_number'] == 1]

    assert [b['attempt'] for b in battle_one] == [1, 2, 3]
    assert [b['result'] for b in battle_one] == ['loss', 'loss', None]
    assert len({b['nemesis']['id'] for b in battle_one}) == 1

def test_loss_randomizer_adds_the_chosen_type(client: TestClient, test_data):
    '''A treasure leaves the barracks alone; a mage or card adds to it.'''
    expedition = create_expedition(client, test_data)
    before = get_state(client, expedition['id'])

    play_battle(
        client, expedition['id'], won=False, loss_randomizer_type=LossRandomizerType.TREASURE
    )
    after_treasure = get_state(client, expedition['id'])
    assert len(after_treasure['barracks_cards']) == len(before['barracks_cards'])
    assert len(after_treasure['mages']) == len(before['mages'])

    play_battle(
        client, expedition['id'], won=False, loss_randomizer_type=LossRandomizerType.MAGE
    )
    after_mage = get_state(client, expedition['id'])
    assert len(after_mage['mages']) == len(before['mages']) + 1
    assert len(after_mage['barracks_cards']) == len(before['barracks_cards'])

    play_battle(
        client, expedition['id'], won=False, loss_randomizer_type=LossRandomizerType.SPELL
    )
    after_spell = get_state(client, expedition['id'])
    assert len(barracks_by_type(after_spell)['spell']) == len(barracks_by_type(before)['spell']) + 1

def test_loss_requires_a_randomizer_choice(client: TestClient, test_data):
    expedition = create_expedition(client, test_data)
    lock_battle(client, expedition['id'])

    response = client.post(
        f"/expeditions/{expedition['id']}/resolve-battle", json={'won_battle': False}
    )
    assert response.status_code == 400
    assert 'randomizer' in response.json()['detail'].lower()

def test_expedition_completes_on_the_final_win(client: TestClient, test_data):
    expedition = create_expedition(client, test_data)
    for _ in range(4):
        expedition = play_battle(client, expedition['id'], won=True)

    assert expedition['status'] == ExpeditionStatus.COMPLETE.value
    assert pending_battle(get_state(client, expedition['id'])) is None

def test_resolving_a_complete_expedition_is_rejected(client: TestClient, test_data):
    expedition = create_expedition(client, test_data)
    for _ in range(4):
        expedition = play_battle(client, expedition['id'], won=True)

    response = client.post(
        f"/expeditions/{expedition['id']}/resolve-battle", json={'won_battle': True}
    )
    assert response.status_code == 400
    assert 'complete' in response.json()['detail'].lower()

def test_getting_nonexistent_expedition(client: TestClient):
    assert client.get('/expeditions/999').status_code == 404

def test_drawn_cards_are_never_repeated(client: TestClient, test_data):
    '''Banished cards stay out of the pool for the rest of the expedition.'''
    expedition = create_expedition(client, test_data)
    seen = set()

    for _ in range(3):
        state = get_state(client, expedition['id'])
        ids = {c['id'] for c in state['barracks_cards']} | {c['id'] for c in state['banished_cards']}
        assert not (seen - ids), 'a previously drawn card disappeared from the expedition'
        seen = ids
        play_battle(client, expedition['id'], won=True)

    final = get_state(client, expedition['id'])
    all_ids = [c['id'] for c in final['barracks_cards'] + final['banished_cards']]
    assert len(all_ids) == len(set(all_ids))

def test_cards_are_only_drawn_from_expedition_sets(client: TestClient, test_data):
    expedition = create_expedition(client, test_data)
    play_battle(client, expedition['id'], won=True)
    state = get_state(client, expedition['id'])

    assert all(c['set_id'] == test_data['set_id'] for c in state['barracks_cards'])
    assert all(c['set_id'] == test_data['set_id'] for c in state['banished_cards'])
    assert all(m['set_id'] == test_data['set_id'] for m in state['mages'])
