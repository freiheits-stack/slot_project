from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class SymbolConfig:
    name: str
    probability: float           
    payout_multiplier: int 


@dataclass
class SlotConfig:
    symbols: List[SymbolConfig]
    # every payline: liste of (row, col) coordinates, 0-based
    paylines: List[List[Tuple[int, int]]]
    n_rows: int = 3
    n_cols: int = 3


def default_slot_config() -> SlotConfig:
    # Standard-Config for 3x3-Slot with 5 Symbols & 5 Paylinies.

    symbols = [
        SymbolConfig("A", 0.30, 5),
        SymbolConfig("B", 0.25, 15),
        SymbolConfig("C", 0.20, 30),
        SymbolConfig("D", 0.15, 60),
        SymbolConfig("E", 0.10, 150),
    ]

    paylines = [
        # Line 1: middle row
        [(1, 0), (1, 1), (1, 2)],
        # Line 2: upper row
        [(0, 0), (0, 1), (0, 2)],
        # Line 3: lower row
        [(2, 0), (2, 1), (2, 2)],
        # Line 4: Diagonal upper left -> lower right
        [(0, 0), (1, 1), (2, 2)],
        # Line 5: Diagonal lower left -> upper right
        [(2, 0), (1, 1), (0, 2)],
    ]

    return SlotConfig(symbols=symbols, paylines=paylines)