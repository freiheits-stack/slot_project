from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Any

from src.rng.bitstore import load_bits_sequence
from src.rng.random_source import PseudoRandomSource, QuantumRandomSource
from src.slotgame.slot_machine import SlotMachine
from src.slotgame.config import default_slot_config


def count_sequences(bits_file: str) -> int:
    n = 0
    with open(bits_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                n += 1
    return n


# --------- Online Feature Tracker (pro Run) ---------

@dataclass
class RunFeatureTracker:
    # streaks on FINAL hits (after gamble)
    current_loss_streak: int = 0
    current_win_streak: int = 0
    max_loss_streak: int = 0
    max_win_streak: int = 0

    # hit gap stats (distance between FINAL hits)
    last_hit_index: Optional[int] = None
    gap_count: int = 0
    gap_mean: float = 0.0
    gap_M2: float = 0.0  # for variance (Welford)

    def update(self, spin_index: int, hit_final: int):
        if hit_final:
            # win streak update
            self.current_win_streak += 1
            self.current_loss_streak = 0
            if self.current_win_streak > self.max_win_streak:
                self.max_win_streak = self.current_win_streak

            # gap update
            if self.last_hit_index is not None:
                gap = spin_index - self.last_hit_index
                self._update_gap_stats(gap)
            self.last_hit_index = spin_index

        else:
            # loss streak update
            self.current_loss_streak += 1
            self.current_win_streak = 0
            if self.current_loss_streak > self.max_loss_streak:
                self.max_loss_streak = self.current_loss_streak

    def _update_gap_stats(self, gap: int):
        self.gap_count += 1
        delta = gap - self.gap_mean
        self.gap_mean += delta / self.gap_count
        delta2 = gap - self.gap_mean
        self.gap_M2 += delta * delta2

    def finalize(self):
        if self.gap_count >= 2:
            gap_var = self.gap_M2 / (self.gap_count - 1)
        else:
            gap_var = ""  # not enough data
        gap_mean = self.gap_mean if self.gap_count >= 1 else ""
        return gap_mean, gap_var


# --------- CSV helpers ---------

RUNS_FIELDS = [
    "rng_type", "run_id", "seq_index", "seed", "gamble_mode",
    "start_balance", "end_balance", "stop_reason", "max_spins", "spins_played",
    "bet_per_line", "active_paylines",
    "total_bet", "total_base_win", "total_final_win",
    "rtp_base", "rtp_final",
    "hit_rate_base", "hit_rate_final",
    "gamble_count", "gamble_win_rate",
    # new run-level sequence features
    "max_loss_streak", "max_win_streak",
    "hit_gap_mean", "hit_gap_var",
]

SPINS_FIELDS = [
    "rng_type", "run_id", "seq_index", "seed", "gamble_mode",
    "spin_index",
    "payout_base", "payout_final",
    "hit_base", "hit_final",
    "net_final",
    "gamble_taken", "gamble_win",
]


def result_to_run_row(
    rng_type: str,
    run_id: int,
    seq_index: Optional[int],
    seed: Optional[int],
    gamble_mode: str,
    res: Any,
    tracker: RunFeatureTracker
) -> Dict[str, Any]:
    hit_gap_mean, hit_gap_var = tracker.finalize()

    return {
        "rng_type": rng_type,
        "run_id": run_id,
        "seq_index": "" if seq_index is None else seq_index,
        "seed": "" if seed is None else seed,
        "gamble_mode": gamble_mode,

        "start_balance": res.start_balance,
        "end_balance": res.end_balance,
        "stop_reason": res.stop_reason,
        "max_spins": res.max_spins,
        "spins_played": res.n_spins,

        "bet_per_line": res.bet_per_line,
        "active_paylines": res.active_paylines,

        "total_bet": res.total_bet,
        "total_base_win": res.total_base_win,
        "total_final_win": res.total_final_win,

        "rtp_base": res.rtp_base,
        "rtp_final": res.rtp_final,

        "hit_rate_base": res.hit_rate_base,
        "hit_rate_final": res.hit_rate_final,

        "gamble_count": res.gamble_count,
        "gamble_win_rate": "" if res.gamble_win_rate is None else res.gamble_win_rate,

        "max_loss_streak": tracker.max_loss_streak,
        "max_win_streak": tracker.max_win_streak,
        "hit_gap_mean": hit_gap_mean,
        "hit_gap_var": hit_gap_var,
    }


def open_writer(path: str, fieldnames: List[str]):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    f = open(path, "w", newline="", encoding="utf-8")
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    return f, w


# --------- Core runner logic ---------

def run_one_condition(
    *,
    rng_type: str,
    run_id: int,
    seq_index: Optional[int],
    seed: Optional[int],
    bits_file: Optional[str],
    gamble_mode: str,
    args,
    spins_writer: Optional[csv.DictWriter],
) -> Dict[str, Any]:
    cfg = default_slot_config()

    # create RNG fresh so "never" and "always" use identical streams
    if rng_type == "quantum":
        assert bits_file is not None
        assert seq_index is not None
        bits = load_bits_sequence(bits_file, index=seq_index)
        rng = QuantumRandomSource(bits=bits)
    elif rng_type == "pseudo":
        assert seed is not None
        rng = PseudoRandomSource(seed=seed)
    else:
        raise ValueError(f"Unknown rng_type: {rng_type}")

    machine = SlotMachine(config=cfg, modus=rng, bet=args.bet, active_paylines=args.paylines)

    tracker = RunFeatureTracker()

    def on_spin(spin_dict: Dict[str, Any]):
        """
        Expect spin_dict to include at least:
          - spin_index (int) OR we infer it if absent (but better include it)
          - payout_base (int/float)
          - payout_final (int/float)
          - gamble_taken (0/1)
          - gamble_win (0/1 or None)
        """
        s = spin_dict.get("spin_index")
        if s is None:
            raise ValueError("on_spin requires 'spin_index' in spin_dict.")

        payout_base = spin_dict["payout_base"]
        payout_final = spin_dict["payout_final"]

        hit_base = 1 if payout_base > 0 else 0
        hit_final = 1 if payout_final > 0 else 0

        # fixed bet=1 assumption (as discussed)
        net_final = payout_final - 1

        tracker.update(spin_index=s, hit_final=hit_final)

        if spins_writer is not None:
            spins_writer.writerow({
                "rng_type": rng_type,
                "run_id": run_id,
                "seq_index": "" if seq_index is None else seq_index,
                "seed": "" if seed is None else seed,
                "gamble_mode": gamble_mode,

                "spin_index": s,
                "payout_base": payout_base,
                "payout_final": payout_final,
                "hit_base": hit_base,
                "hit_final": hit_final,
                "net_final": net_final,
                "gamble_taken": int(spin_dict.get("gamble_taken", 0)),
                "gamble_win": "" if spin_dict.get("gamble_win") is None else int(spin_dict["gamble_win"]),
            })

    res = machine.autoplay(
        start_balance=args.start_balance,
        max_spins=args.max_spins,
        bet=args.bet,
        active_paylines=args.paylines,
        gamble_mode=gamble_mode,
        target_balance=None,
        on_spin=on_spin if spins_writer is not None else None,
    )

    return result_to_run_row(
        rng_type=rng_type,
        run_id=run_id,
        seq_index=seq_index,
        seed=seed,
        gamble_mode=gamble_mode,
        res=res,
        tracker=tracker,
    )


def main():
    p = argparse.ArgumentParser(
        description="Run paired slot experiments (never + always) for quantum vs pseudo RNG and save run- and spin-level CSVs."
    )
    p.add_argument("--bits-file", default="data/truerng_sequences.txt")
    p.add_argument("--out-runs", default="data/experiment_runs.csv")
    p.add_argument("--out-spins", default="data/experiment_spins.csv")
    p.add_argument("--runs", type=int, default=None, help="Number of base runs (default: all sequences in bits-file).")

    p.add_argument("--start-balance", type=int, default=1000)
    p.add_argument("--max-spins", type=int, default=7000)
    p.add_argument("--bet", type=int, default=1)
    p.add_argument("--paylines", type=int, default=5)

    p.add_argument("--seed-base", type=int, default=12345, help="Pseudo seed per run = seed_base + i")

    # If you ever want to disable spin logging:
    p.add_argument("--no-spin-log", action="store_true", help="Do not write spin-level CSV (faster, smaller).")

    args = p.parse_args()

    if args.runs is None:
        n_runs = count_sequences(args.bits_file)
    else:
        n_runs = args.runs

    if n_runs <= 0:
        raise ValueError("No runs to execute (n_runs <= 0). Check bits-file or --runs.")

    if args.bet != 1:
        raise ValueError("This runner assumes bet=1 for net_final. If you want bet!=1, tell me and we generalize net_final.")

    print("=== Experiment settings ===")
    print(f"bits_file     : {args.bits_file}")
    print(f"out_runs      : {args.out_runs}")
    print(f"out_spins     : {args.out_spins}")
    print(f"n_runs        : {n_runs}")
    print(f"start_balance : {args.start_balance}")
    print(f"max_spins     : {args.max_spins}")
    print(f"bet           : {args.bet}")
    print(f"paylines      : {args.paylines}")
    print(f"pseudo seeds  : seed = seed_base + i (seed_base={args.seed_base})")
    print("paired modes  : never + always (same RNG stream per run)")

    # Writers
    run_rows: List[Dict[str, Any]] = []

    spins_file = None
    spins_writer = None
    if not args.no_spin_log:
        spins_file, spins_writer = open_writer(args.out_spins, SPINS_FIELDS)

    try:
        # For each base run i, run both gamble conditions with identical RNG streams
        for i in range(n_runs):
            # QUANTUM paired
            for mode in ("never", "always"):
                run_row = run_one_condition(
                    rng_type="quantum",
                    run_id=i,
                    seq_index=i,
                    seed=None,
                    bits_file=args.bits_file,
                    gamble_mode=mode,
                    args=args,
                    spins_writer=spins_writer,
                )
                run_rows.append(run_row)
                print(f"[quantum] run {i+1}/{n_runs} mode={mode}: spins={run_row['spins_played']} end={run_row['end_balance']} stop={run_row['stop_reason']}")

            # PSEUDO paired (same seed for never/always)
            seed = args.seed_base + i
            for mode in ("never", "always"):
                run_row = run_one_condition(
                    rng_type="pseudo",
                    run_id=i,
                    seq_index=None,
                    seed=seed,
                    bits_file=None,
                    gamble_mode=mode,
                    args=args,
                    spins_writer=spins_writer,
                )
                run_rows.append(run_row)
                print(f"[pseudo ] run {i+1}/{n_runs} seed={seed} mode={mode}: spins={run_row['spins_played']} end={run_row['end_balance']} stop={run_row['stop_reason']}")

    finally:
        if spins_file is not None:
            spins_file.close()

    # Write run-level CSV
    Path(args.out_runs).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out_runs, "w", newline="", encoding="utf-8") as f_runs:
        w = csv.DictWriter(f_runs, fieldnames=RUNS_FIELDS)
        w.writeheader()
        for row in run_rows:
            w.writerow(row)

    print(f"\nDone.")
    print(f"  Wrote {len(run_rows)} run rows to: {args.out_runs}")
    if not args.no_spin_log:
        print(f"  Wrote spin-level rows to: {args.out_spins}")


if __name__ == "__main__":
    main()