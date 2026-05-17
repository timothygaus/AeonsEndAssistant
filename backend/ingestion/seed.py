import os
import json
import time
import requests
import mwparserfromhell
from pathlib import Path
from sqlmodel import Session, create_engine, select
from app.models import Set, PlayerCard, BreachMage, Nemesis

BASE_URL = 'https://aeonsend.wiki.gg/api.php'
CACHE_DIR = Path(__file__).parent / 'cache'
CACHE_DIR.mkdir(exist_ok=True)
HEADERS = {
    'User-Agent': 'AeonsEndAssistant/1.0 (github.com/timothygaus)'
}

engine = create_engine(os.environ.get('DATABASE_URL'))

CATEGORIES = {
    'player_card': ['Gem', 'Relic', 'Spell'],
    'breach_mage': ['Mage'],
    'nemesis': ['Nemesis'],
}

def get_category_members(category: str) -> list[str]:
    members = []
    params = {
        'action': 'query',
        'list': 'categorymembers',
        'cmtitle': f'Category:{category}',
        'cmlimit': 500,
        'cmtype': 'page',
        'format': 'json',
    }

    while True:
        response = requests.get(BASE_URL, params=params, headers=HEADERS)
        data = response.json()
        if 'query' not in data:
            print(f'Unexpected response in categorymembers: {data}')
            break
        members.extend([m['title'] for m in data['query']['categorymembers']])
        if 'continue' not in data:
            break
        params['cmcontinue'] = data['continue']['cmcontinue']
        time.sleep(1.5)
    
    return members

def get_page_wikitext(title: str) -> str:
    cache_file = CACHE_DIR / f"{title.replace('/', '_')}.json"

    if cache_file.exists():
        return json.loads(cache_file.read_text())['wikitext']
    
    response = requests.get(BASE_URL, params= {
        'action': 'parse',
        'page': title,
        'prop': 'wikitext',
        'format': 'json',
    }, headers=HEADERS)

    data = response.json()
    if 'parse' not in data:
        print(f'Skipping {title} - unexpected response: {data}')
        return None

    wikitext = response.json()['parse']['wikitext']['*']
    cache_file.write_text(json.dumps({'wikitext': wikitext}))
    time.sleep(1.5)
    print(f'Fetched data for {title}')
    return wikitext

def get_or_create_set(session: Session, set_name: str) -> int:
    existing = session.exec(select(Set).where(Set.name == set_name)).first()
    if existing:
        return existing.id
    
    new_set = Set(name=set_name)
    session.add(new_set)
    session.commit()
    session.refresh(new_set)
    return new_set.id

def parse_player_card(title: str, wikitext: str) -> dict | None:
    wikicode = mwparserfromhell.parse(wikitext)
    templates = {t.name.strip(): t for t in wikicode.filter_templates()}

    card_template = templates.get('PlayerCard')
    if not card_template:
        return None
    
    card_type = card_template.get('Type').value.strip().lower() if card_template.has('Type') else None
    if card_type not in ('gem', 'relic', 'spell'):
        return None
    
    set_name = card_template.get('Box 1').value.strip() if card_template.has('Box 1') else None
    unique_to = card_template.has('Unique To') and card_template.get('Unique To').value.strip()
    is_supply = not bool(unique_to)

    return {
        'name': title,
        'type': card_type,
        'is_supply': is_supply,
        'set_name': set_name
    }

def parse_breach_mage(title: str, wikitext: str) -> dict | None:
    wikicode = mwparserfromhell.parse(wikitext)
    templates = {t.name.strip(): t for t in wikicode.filter_templates()}

    mage_template = templates.get('Mage')
    if not mage_template:
        return None
    
    set_name = mage_template.get('Box').value.strip() if mage_template.has('Box') else None
    complexity = int(mage_template.get('Complexity').value.strip()) if mage_template.has('Complexity') else None

    return {
        'name': title,
        'set_name': set_name,
        'complexity': complexity
    }

def parse_nemesis(title: str, wikitext: str) -> dict | None:
    wikicode = mwparserfromhell.parse(wikitext)
    templates = {t.name.strip(): t for t in wikicode.filter_templates()}

    nemesis_template = templates.get('Nemesis')
    if not nemesis_template:
        return None
    
    set_name = nemesis_template.get('Box').value.strip() if nemesis_template.has('Box') else None
    expedition_battle = int(nemesis_template.get('Expedition Battle').value.strip()) if nemesis_template.has('Expedition Battle') else None
    difficulty = int(nemesis_template.get('Difficulty Level').value.strip()) if nemesis_template.has('Difficulty Level') else None

    return {
        'name': title,
        'set_name': set_name,
        'expedition_battle': expedition_battle,
        'difficulty': difficulty
    }

def main():
    with Session(engine) as session:
        for category in CATEGORIES['player_card']:
            print(f'Fetching {category}s...')
            for title in get_category_members(category):
                wikitext = get_page_wikitext(title)
                if not wikitext:
                    continue
                data = parse_player_card(title, wikitext)
                if not data:
                    continue
                if not data['set_name']:
                    print(f'Skipping {title} - no set_name found')
                    continue
                set_id = get_or_create_set(session, data['set_name'])
                session.add(PlayerCard(
                    name=data['name'],
                    type=data['type'],
                    is_supply=data['is_supply'],
                    set_id=set_id
                ))
            session.commit()

        print('Fetching Mages...')
        for title in get_category_members('Mage'):
            wikitext = get_page_wikitext(title)
            if not wikitext:
                continue
            data = parse_breach_mage(title, wikitext)
            if not data:
                continue
            if not data['set_name']:
                print(f'Skipping {title} - no set_name found')
                continue
            set_id = get_or_create_set(session, data['set_name'])
            session.add(BreachMage(
                name=data['name'],
                set_id=set_id,
                complexity=data['complexity']
            ))
        session.commit()

        print('Fetching Nemeses...')
        for title in get_category_members('Nemesis'):
            wikitext = get_page_wikitext(title)
            if not wikitext:
                continue
            data = parse_nemesis(title, wikitext)
            if not data:
                continue
            if not data['set_name']:
                print(f'Skipping {title} - no set_name found')
                continue
            set_id = get_or_create_set(session, data['set_name'])
            session.add(Nemesis(
                name=data['name'],
                set_id=set_id,
                expedition_battle=data['expedition_battle'],
                difficulty=data['difficulty']
            ))
        session.commit()

if __name__ == '__main__':
    main()