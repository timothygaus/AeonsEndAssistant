from enum import Enum

class CardType(str, Enum):
    GEM = 'gem'
    RELIC = 'relic'
    SPELL = 'spell'

class LossRandomizerType(str, Enum):
    GEM = 'gem'
    RELIC = 'relic'
    SPELL = 'spell'
    MAGE = 'mage'
    TREASURE = 'treasure'