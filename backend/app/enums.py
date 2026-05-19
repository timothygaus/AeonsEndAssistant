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

class SupplyCardStatus(str, Enum):
    BARRACKS = 'barracks'
    BANISHED = 'banished'

class ExpeditionVariant(str, Enum):
    STANDARD = 'standard'
    SHORT = 'short'
    EXTENDED = 'extended'
    DEEP_POCKETS = 'deep-pockets'

class ExpeditionStatus(str, Enum):
    ACTIVE = 'active'
    COMPLETE = 'complete'