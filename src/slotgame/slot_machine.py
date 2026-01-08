from dataclasses import dataclass
from typing import List, Optional, Dict

from config import SlotConfig
from src.rng.random_source import PseudoRandomSource


@dataclass
class SpinResult:
    grid: List[List[str]]          # n_rows x n_cols, grid[row][col]
    base_win: float                # payout before gamble
    final_win: float               # payout after gamble (if used)
    gambled: bool
    gamble_won: bool | None        # None if gambled=False
    winning_lines: List[int]       # indices of paylines that paid

@dataclass
class AutoPlayResult:
    n_spins: int
    bet_per_line: int
    active_paylines: int
    total_bet: int

    total_base_win: int
    total_final_win: int

    rtp_base: float
    rtp_final: float

    hit_rate_base: float
    hit_rate_final: float

    gamble_mode: str
    gamble_count: int
    gamble_win_rate: Optional[float]

    symbol_hits: Dict[str, int]
    payline_hits: Dict[int, int]


class SlotMachine:
    def _validate_bet(self, bet: int) -> int:
        bet = int(bet)
        if bet not in (1, 3, 5):
            raise ValueError("bet must be 1, 3 or 5")
        return bet

    def _validate_active_paylines(self, active_paylines: int) -> int:
        active_paylines = int(active_paylines)
        if active_paylines not in (1, 3, 5):
            raise ValueError("active_paylines must be 1, 3 or 5")
        return active_paylines

    def __init__(self, config: SlotConfig, modus = None, bet: int = 1, active_paylines: int = 1):
        # set attributes
        self.config = config
        self.random_source = modus if modus is not None else PseudoRandomSource()
        self.bet = self._validate_bet(bet)
        self.active_paylines = self._validate_active_paylines(active_paylines)

        probabilities = [symbol.probability for symbol in self.config.symbols]    # [0.30, 0.25, 0.20, 0.15, 0.10]
        total = sum(probabilities)
        if total <= 0 or total > 1:
            raise ValueError("Sum of symbol probabilities must be in (0,1].")

        # normalize + build cumulative distribution
        cum = []
        running = 0.0
        for prob in probabilities:
            running += prob / total                                # divide threw total if total is not 1
            cum.append(running)
        cum[-1] = 1.0                                           # guard against floating error
        self._cdf = cum                                         # [0.30, 0.55, 0.75, 0.90, 1.00]

        self._names = [symbol.name for symbol in self.config.symbols]     # ["A", "B", "C", "D", "E"]
        self._payout = {symbol.name: int(symbol.payout_multiplier) for symbol in self.config.symbols}  # {"A": 5, "B": 15, "C": 30, "D": 60, "E": 150}

    def _draw_symbol(self) -> str:
        #Draw one symbol according to configured probabilities using modus.next_float()
        random_number = self.random_source.next_float()  # expected in [0,1)
        # clamp just in case of numerical edge
        if random_number < 0.0:
            random_number = 0.0
        elif random_number >= 1.0:
            random_number = 0.999999999999

        for idx, probability in enumerate(self._cdf):
            if random_number < probability:
                return self._names[idx]
        raise RuntimeError("Sampling failed: random_number={random_number}, cdf_last={self._cdf[-1]}")
    
    def spin(self, bet: Optional[int] = None, active_paylines: Optional[int] = None) -> SpinResult:
        # check atributes
        bet_used = self.bet if bet is None else self._validate_bet(bet)
        n_paylines_used = self.active_paylines if active_paylines is None else self._validate_active_paylines(active_paylines)

        # generate grid
        grid = []
        for r in range(self.config.n_rows):
            row = []
            for c in range(self.config.n_cols):
                row.append(self._draw_symbol())
            grid.append(row)

        # evaluate paylines
        base_win = 0.0
        winning_lines: List[int] = []

        paylines_to_check = self.config.paylines[:n_paylines_used]
        for idx, line in enumerate(paylines_to_check):
            symbols = [grid[r][c] for (r, c) in line]
            if all(s == symbols[0] for s in symbols[1:]):
                winning_lines.append(idx)
                base_win += bet_used * self._payout[symbols[0]]

        # SpinResult: final_win erstmal = base_win, gamble flags leer
        return SpinResult(
            grid=grid,
            base_win=base_win,
            final_win=base_win,
            gambled=False,
            gamble_won=None,
            winning_lines=winning_lines,
        )
    
    def gamble(self, result: SpinResult) -> SpinResult:
        if result.base_win <= 0:
            raise ValueError("Cannot gamble without a win")

        gamble_won = self.random_source.next_float() < 0.5
        final_win = (2 * result.base_win) if gamble_won else 0

        # new SpinResult
        return SpinResult(
            grid=result.grid,
            base_win=result.base_win,
            final_win=final_win,
            gambled=True,
            gamble_won=gamble_won,
            winning_lines=result.winning_lines,
        )

    def autoplay(self, n_spins: int, bet: Optional[int] = None, active_paylines: Optional[int] = None, gamble_mode: str = "never") -> Dict[str, Any]:

        if n_spins <= 0:
            raise ValueError("n_spins must be > 0")

        # Use machine defaults unless overridden for this autoplay run
        bet_used = self.bet if bet is None else self._validate_bet(bet)
        paylines_used = self.active_paylines if active_paylines is None else self._validate_active_paylines(active_paylines)
        
        if gamble_mode not in ("never", "always"):
            raise ValueError("gamble_mode must be 'never' or 'always'")

        total_bet = bet_used * paylines_used * n_spins  # bet is per payline

        total_base_win = 0
        total_final_win = 0

        base_win_spins = 0
        final_win_spins = 0

        gamble_count = 0
        gamble_wins = 0

        symbol_hits = {name: 0 for name in self._names}
        payline_hits = {i: 0 for i in range(len(self.config.paylines))}

        for _ in range(n_spins):
            # spin with explicit settings (so it’s consistent)
            res = self.spin(bet=bet_used, active_paylines=paylines_used)

            total_base_win += res.base_win
            if res.base_win > 0:
                base_win_spins += 1

            # count symbols for distribution checks
            for r in range(self.config.n_rows):
                for c in range(self.config.n_cols):
                    symbol_hits[res.grid[r][c]] += 1

            # count hit paylines (indices are relative to the checked subset: 0..paylines_used-1)
            for li in res.winning_lines:
                payline_hits[li] += 1

            # gamble decision AFTER spin
            if gamble_mode == "always" and res.base_win > 0:
                gamble_count += 1
                res = self.gamble(res)
                if res.gamble_won:
                    gamble_wins += 1

            total_final_win += res.final_win
            if res.final_win > 0:
                final_win_spins += 1

        return AutoPlayResult(
        n_spins=n_spins,
        bet_per_line=bet_used,
        active_paylines=paylines_used,
        total_bet=total_bet,

        total_base_win=total_base_win,
        total_final_win=total_final_win,

        rtp_base=total_base_win / total_bet,
        rtp_final=total_final_win / total_bet,

        hit_rate_base=base_win_spins / n_spins,
        hit_rate_final=final_win_spins / n_spins,

        gamble_mode=gamble_mode,
        gamble_count=gamble_count,
        gamble_win_rate=(gamble_wins / gamble_count) if gamble_count else None,

        symbol_hits=symbol_hits,
        payline_hits=payline_hits,
    )