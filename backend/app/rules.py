'''
Expedition rules derived from the Aeon's End expedition variants.

Kept separate from the router so the arithmetic can be read and tested on its
own. See docs/MVP_PLAN.md for the sourcing of each rule.
'''
import math

from app.enums import ExpeditionVariant

# A player supply is always exactly 9 cards.
SUPPLY_SIZE = 9

# Between 1 and 4 mages may be used in a battle.
MIN_MAGES = 1
MAX_MAGES = 4

# An expedition runs 4 battles, or 5 with Beyond the Breach.
MIN_BASE_LENGTH = 4
MAX_BASE_LENGTH = 5

# Starting barracks: 3 gems, 2 relics, 4 spells, 4 mages.
STARTING_SUPPLY = {'gem': 3, 'relic': 2, 'spell': 4}
STARTING_MAGES = 4

def effective_length(variant: ExpeditionVariant, base_length: int) -> int:
    '''
    Total battles in the expedition. An extended expedition is always exactly
    double the base length.
    '''
    if variant == ExpeditionVariant.EXTENDED:
        return base_length * 2
    return base_length

def first_battle_number(variant: ExpeditionVariant) -> int:
    '''
    A short expedition skips the first battle and opens against nemesis deck 2.
    '''
    if variant == ExpeditionVariant.SHORT:
        return 2
    return 1

def nemesis_tier(variant: ExpeditionVariant, battle_number: int) -> int:
    '''
    Which nemesis deck a battle draws from. An extended expedition spends two
    battles per deck: battles 1-2 draw from deck 1, battles 3-4 from deck 2, and
    so on.
    '''
    if variant == ExpeditionVariant.EXTENDED:
        return math.ceil(battle_number / 2)
    return battle_number

def required_nemesis_tiers(variant: ExpeditionVariant, base_length: int) -> dict[int, int]:
    '''
    Maps each nemesis deck the expedition will draw from to the number of
    distinct nemeses it needs. An extended expedition fights each deck twice and
    never repeats a nemesis, so it needs two from every deck.
    '''
    battles = range(
        first_battle_number(variant),
        effective_length(variant, base_length) + 1,
    )
    tiers: dict[int, int] = {}
    for battle_number in battles:
        tier = nemesis_tier(variant, battle_number)
        tiers[tier] = tiers.get(tier, 0) + 1
    return tiers
