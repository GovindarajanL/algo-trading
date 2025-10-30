"""
Strategy Engine
Trading strategies implementation
"""

from .base_strategy import BaseStrategy, StrategySignal
from .iron_condor import IronCondorStrategy
from .vertical_spreads import (
    BullCallSpread,
    BearPutSpread,
    BullPutSpread,
    BearCallSpread
)
from .volatility_strategies import (
    LongStraddle,
    LongStrangle,
    IronButterfly
)
from .strike_selector import StrikeSelector

__all__ = [
    'BaseStrategy',
    'StrategySignal',
    'IronCondorStrategy',
    'BullCallSpread',
    'BearPutSpread',
    'BullPutSpread',
    'BearCallSpread',
    'LongStraddle',
    'LongStrangle',
    'IronButterfly',
    'StrikeSelector'
]
