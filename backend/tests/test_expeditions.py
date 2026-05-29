from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models import ExpeditionBattle, ExpeditionMage, Nemesis
from app.enums import BattleResult, CardType, ExpeditionStatus, ExpeditionVariant, LossRandomizerType

def test_create_expedition(client: TestClient, test_data):
    '''
    Test that POST /expeditions returns 200, the correct number of cards and mages were drawn,
    the initial battle was created correctly, and all drawn options belong to the correct set
    '''
    data = create_expedition(client, test_data)

    state_response = client.get(f'/expeditions/{data["id"]}')
    assert state_response.status_code == 200
    state = state_response.json()

    gems, relics, spells = get_barracks_cards(state)

    assert len(gems) == 3
    assert len(relics) == 2
    assert len(spells) == 4
    assert len(state['mages']) == 4
    assert len(state['battles']) == 1
    assert state['battles'][0]['battle_number'] == 1
    assert state['battles'][0]['result'] == None
    assert all(c['set_id'] == test_data['set_id'] for c in state['barracks_cards'])
    assert all(m['set_id'] == test_data['set_id'] for m in state['mages'])
    assert state['battles'][0]['nemesis']['set_id'] == test_data['set_id']

def test_resolve_battle_win(client: TestClient, session: Session, test_data):
    '''
    Test that the current ExpeditionBattle result is updated to win, the expedition's current battle
    is incremented by 1, one gem, relic and spell are added to the barracks, and a new ExpeditionBattle
    is created for the next fight with the correct battle number and a valid nemesis.
    '''
    data = create_expedition(client, test_data)
    current_battle_num = data['current_battle']

    data = resolve_battle_win(client, data['id'])

    current_expedition_battle = session.exec(
        select(ExpeditionBattle).where(
            ExpeditionBattle.expedition_id==data['id'],
            ExpeditionBattle.battle_number==current_battle_num
        )
    ).first()

    next_expedition_battle = session.exec(
        select(ExpeditionBattle).where(
            ExpeditionBattle.expedition_id==data['id'],
            ExpeditionBattle.battle_number==data['current_battle']
        )
    ).first()

    next_nemesis = session.exec(
        select(Nemesis).where(
            Nemesis.id==next_expedition_battle.nemesis_id
        )
    ).first()

    state_response = client.get(f'/expeditions/{data["id"]}')
    assert state_response.status_code == 200
    state = state_response.json()

    gems, relics, spells = get_barracks_cards(state)

    assert current_expedition_battle.result == BattleResult.WIN
    assert data['current_battle'] == current_battle_num + 1
    assert next_expedition_battle.battle_number == current_battle_num + 1
    assert len(gems) == 4
    assert len(relics) == 3
    assert len(spells) == 5
    assert next_nemesis.expedition_battle == current_battle_num + 1
    assert next_nemesis.set_id == test_data['set_id']

def test_resolve_battle_loss(client: TestClient, session: Session, test_data):
    '''
    Tests that after a loss the current expedition battle's result was updated to loss, the next battle num
    remains the same, one randomizer was added (in this case, a gem) to the barracks and all other barracks contents
    remain unchanged, and the next nemesis to be fought remains unchanged.
    '''
    data = create_expedition(client, test_data)
    current_battle_num = data['current_battle']

    state_response = client.get(f'/expeditions/{data["id"]}')
    assert state_response.status_code == 200
    state = state_response.json()

    cur_gems, cur_relics, cur_spells = get_barracks_cards(state)
    cur_mages = get_barracks_mages(session, data['id'])

    current_expedition_battle = session.exec(
        select(ExpeditionBattle).where(
            ExpeditionBattle.expedition_id==data['id'],
            ExpeditionBattle.battle_number==current_battle_num
        )
    ).first()
    cur_nemesis = session.exec(
        select(Nemesis).where(
            Nemesis.id==current_expedition_battle.nemesis_id
        )
    ).first()

    response = client.post(f'/expeditions/{data["id"]}/resolve-battle', json={
        'won_battle': False,
        'loss_randomizer_type': LossRandomizerType.GEM.value
    })
    assert response.status_code == 200
    data = response.json()
    next_battle_num = data['current_battle']

    next_expedition_battle = session.exec(
        select(ExpeditionBattle).where(
            ExpeditionBattle.expedition_id==data['id'],
            ExpeditionBattle.battle_number==next_battle_num
        )
    ).first()
    next_nemesis = session.exec(
        select(Nemesis).where(
            Nemesis.id==next_expedition_battle.nemesis_id
        )
    ).first()

    state_response = client.get(f'/expeditions/{data["id"]}')
    assert state_response.status_code == 200
    state = state_response.json()

    gems, relics, spells = get_barracks_cards(state)
    mages = get_barracks_mages(session, data['id'])

    assert next_expedition_battle.result == BattleResult.LOSS
    assert next_battle_num == current_battle_num
    assert len(gems) == len(cur_gems) + 1
    assert len(relics) == len(cur_relics)
    assert len(spells) == len(cur_spells)
    assert len(mages) == len(cur_mages)
    assert next_nemesis.id == cur_nemesis.id

def test_resolve_battle_win_final(client: TestClient, test_data):
    '''
    Tests that when the final battle of an expedition is completed, the status of the expedition is updated to complete.
    '''
    data = create_expedition(client, test_data)

    # 4 battles in a standard expedition
    # TODO: Beyond the Breach makes this 5 if present, need to handle that case
    data = resolve_battle_win(client, data['id'])
    data = resolve_battle_win(client, data['id'])
    data = resolve_battle_win(client, data['id'])
    data = resolve_battle_win(client, data['id'])

    assert data['status'] == ExpeditionStatus.COMPLETE.value

def test_resolve_battle_loss_chose_treasure(client: TestClient, session: Session, test_data):
    '''
    Tests that no gems, relics, spells, or mages were added to the barracks after a loss if a treasure was chosen.
    '''
    data = create_expedition(client, test_data)

    state_response = client.get(f'/expeditions/{data["id"]}')
    assert state_response.status_code == 200
    state = state_response.json()

    cur_gems, cur_relics, cur_spells = get_barracks_cards(state)
    cur_mages = get_barracks_mages(session, data['id'])

    response = client.post(f'/expeditions/{data["id"]}/resolve-battle', json={
        'won_battle': False,
        'loss_randomizer_type': LossRandomizerType.TREASURE.value
    })
    assert response.status_code == 200
    data = response.json()

    state_response = client.get(f'/expeditions/{data["id"]}')
    assert state_response.status_code == 200
    state = state_response.json()

    gems, relics, spells = get_barracks_cards(state)
    mages = get_barracks_mages(session, data['id'])

    assert len(gems) == len(cur_gems)
    assert len(relics) == len(cur_relics)
    assert len(spells) == len(cur_spells)
    assert len(mages) == len(cur_mages)

def test_resolve_battle_loss_chose_mage(client: TestClient, session: Session, test_data):
    '''
    Tests that a mage was added to the barracks after a loss if a mage randomizer was chosen.
    '''
    data = create_expedition(client, test_data)

    state_response = client.get(f'/expeditions/{data["id"]}')
    assert state_response.status_code == 200
    state = state_response.json()

    cur_gems, cur_relics, cur_spells = get_barracks_cards(state)
    cur_mages = get_barracks_mages(session, data['id'])

    response = client.post(f'/expeditions/{data["id"]}/resolve-battle', json={
        'won_battle': False,
        'loss_randomizer_type': LossRandomizerType.MAGE.value
    })
    assert response.status_code == 200
    data = response.json()

    state_response = client.get(f'/expeditions/{data["id"]}')
    assert state_response.status_code == 200
    state = state_response.json()

    gems, relics, spells = get_barracks_cards(state)
    mages = get_barracks_mages(session, data['id'])

    assert len(gems) == len(cur_gems)
    assert len(relics) == len(cur_relics)
    assert len(spells) == len(cur_spells)
    assert len(mages) == len(cur_mages) + 1

def test_getting_nonexistent_expedition(client: TestClient):
    '''
    Tests that attempting to get an expedition that doesn't exists returns a 404 response.
    '''
    state_response = client.get(f'/expeditions/999')
    assert state_response.status_code == 404

def test_draw_valid_cards(client: TestClient, test_data):
    '''
    Tests that cards are not drawn from sets not present in the expedition.
    '''    
    data = create_expedition(client, test_data)

    state_response = client.get(f'/expeditions/{data["id"]}')
    assert state_response.status_code == 200
    state = state_response.json()

    assert all(c['set_id'] == test_data['set_id'] for c in state['barracks_cards'])

def test_drawn_cards_not_repeated(client: TestClient, session: Session, test_data):
    '''
    Tests that new cards drawn are not already present in the list of barracks or banished cards.
    '''
    data = create_expedition(client, test_data)
    state_response = client.get(f'/expeditions/{data["id"]}')
    assert state_response.status_code == 200
    state = state_response.json()
    initial_ids = {c['id'] for c in state['barracks_cards']}

    data = resolve_battle_win(client, data['id'])
    state_response = client.get(f'/expeditions/{data["id"]}')
    assert state_response.status_code == 200
    state = state_response.json()
    all_ids = {c['id'] for c in state['barracks_cards']}

    assert len(all_ids) == len(initial_ids) + 3

def create_expedition(client: TestClient, test_data):
    '''
    Calls POST /expeditions using the set_id of test_data and asserts a 200 response,
    and returns the json response.
    '''
    response = client.post('/expeditions', json={
        'set_ids': [test_data['set_id']],
        'variant': ExpeditionVariant.STANDARD.value
    })
    assert response.status_code == 200
    return response.json()

def get_barracks_cards(state):
    '''
    Gets the gems, relics, and spells from the barracks from the GET /expeditions/{id} json response
    '''
    gems = [c for c in state['barracks_cards'] if c['type'] == CardType.GEM.value]
    relics = [c for c in state['barracks_cards'] if c['type'] == CardType.RELIC.value]
    spells = [c for c in state['barracks_cards'] if c['type'] == CardType.SPELL.value]
    return gems, relics, spells

def get_barracks_mages(session: Session, id):
    '''
    Gets the mages from the barracks from the GET /expeditions/{id} json response
    '''
    return session.exec(
        select(ExpeditionMage).where(
            ExpeditionMage.expedition_id==id,
        )
    ).all()

def resolve_battle_win(client: TestClient, id):
    '''
    Calls POST /expeditions/{id}/resolve-battle with won_battle = True, asserts a 200 response,
    and returns the json response.
    '''
    response = client.post(f'/expeditions/{id}/resolve-battle', json={
        'won_battle': True
    })
    assert response.status_code == 200
    return response.json()