from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Optional

from src.rng.bitstore import load_bits_sequence
from src.rng.random_source import PseudoRandomSource, QuantumRandomSource
from src.slotgame.slot_machine import SlotMachine
from src.slotgame.config import default_slot_config

# Optional: live TrueRNG
try:
    from src.rng.truerng import TrueRNGDevice
    TRUERNG_AVAILABLE = True
except Exception:
    TRUERNG_AVAILABLE = False

@dataclass
class Settings:
    bet: int = 1
    paylines: int = 5
    gamble_mode: str = "never"   # "never" | "always"
    payout_mode: str = "safe"    # "safe" | "risk"


def print_grid(grid):
    # grid[row][col]
    for r in grid:
        print(" ".join(r))

def choose_rng_interactive(args) -> tuple[object, str]:
    print("Choose RNG source:")
    print("  1) pseudo (seeded)")
    print("  2) quantum (offline bits from file)")
    if TRUERNG_AVAILABLE:
        print("  3) quantum (live TrueRNG stick)")
    choice = input("Your choice: ").strip()

    if choice == "1":
        seed_txt = input(f"Seed (empty = {args.seed}): ").strip()
        seed = int(seed_txt) if seed_txt else args.seed
        return PseudoRandomSource(seed=seed), f"pseudo(seed={seed})"

    if choice == "2":
        filename = input(f"Bits filename [{args.bits_file}]: ").strip() or args.bits_file
        idx_txt = input(f"Sequence index (0-based) [{args.seq_index}]: ").strip()
        idx = int(idx_txt) if idx_txt else args.seq_index
        bits = load_bits_sequence(filename, index=idx)
        return QuantumRandomSource(bits=bits), f"quantum(file, idx={idx})"

    if choice == "3" and TRUERNG_AVAILABLE:
        bits_txt = input(f"How many bits to read [{args.live_bits}]: ").strip()
        n_bits = int(bits_txt) if bits_txt else args.live_bits
        dev = TrueRNGDevice()  # optionally TrueRNGDevice(port="COM3")
        try:
            bits = dev.read_bits(n_bits)
        finally:
            dev.close()
        return QuantumRandomSource(bits=bits), f"quantum(live TrueRNG, bits={n_bits})"

    raise ValueError("Invalid RNG choice.")

def do_one_spin(machine: SlotMachine, balance: int, s: Settings) -> int:
    cost = s.bet * s.paylines
    if balance < cost:
        print(f"Not enough balance for spin. Need {cost}, have {balance}.")
        return balance

    balance_before = balance
    balance -= cost

    res = machine.spin(bet=s.bet, active_paylines=s.paylines)
    print("\n--- SPIN ---")
    print_grid(res.grid)
    print(f"Cost: {cost}")
    print(f"Base win: {res.base_win}")

    if s.gamble_mode == "always" and res.base_win > 0:
        res = machine.gamble(res)
        print(f"GAMBLE: {'WON' if res.gamble_won else 'LOST'} -> Final win: {res.final_win}")
    else:
        print(f"Final win: {res.final_win}")

    balance += res.final_win
    print(f"Balance: {balance_before} -> {balance}")
    return balance


def do_autoplay(machine: SlotMachine, balance: int, s: Settings, n: int) -> int:
    # reuse your autoplay (with on_spin=None)
    res = machine.autoplay(
        start_balance=balance,
        max_spins=n,
        bet=s.bet,
        active_paylines=s.paylines,
        gamble_mode=s.gamble_mode,
        target_balance=None,
        on_spin=None,
    )
    print("\n--- AUTOPLAY ---")
    print(f"Spins played: {res.n_spins}/{n} | stop_reason={res.stop_reason}")
    print(f"RTP_final: {res.rtp_final:.4f} | hit_rate_final: {res.hit_rate_final:.4f}")
    print(f"Balance: {balance} -> {res.end_balance}")
    return res.end_balance


def prompt_settings(s: Settings) -> Settings:
    print("\n--- SETTINGS ---")
    bet = input(f"bet (1/3/5) [{s.bet}]: ").strip()
    if bet:
        s.bet = int(bet)

    pl = input(f"paylines (1/3/5) [{s.paylines}]: ").strip()
    if pl:
        s.paylines = int(pl)

    gm = input(f"gamble_mode (never/always) [{s.gamble_mode}]: ").strip()
    if gm:
        s.gamble_mode = gm

    pm = input(f"payout_mode (safe/risk) [{s.payout_mode}]: ").strip()
    if pm:
        s.payout_mode = pm

    return s


def main():
    p = argparse.ArgumentParser(description="Interactive SlotMachine CLI (spin + autoplay blocks + settings).")
    p.add_argument("--seed", type=int, default=12345)
    p.add_argument("--bits-file", default="data/truerng_sequences.txt")
    p.add_argument("--seq-index", type=int, default=0)
    p.add_argument("--live-bits", type=int, default=2_000_000)
    p.add_argument("--start-balance", type=int, default=1000)
    args = p.parse_args()

    cfg = default_slot_config()
    rng, rng_info = choose_rng_interactive(args)

    s = Settings()
    bal_txt = input(f"Start balance [{args.start_balance}]: ").strip()
    balance = int(bal_txt) if bal_txt else args.start_balance

    # Create machine once; if payout_mode changes, rebuild (simple & safe)
    def make_machine() -> SlotMachine:
        return SlotMachine(
            config=cfg,
            modus=rng,
            bet=s.bet,
            active_paylines=s.paylines,
            payout_mode=s.payout_mode,
        )

    machine = make_machine()

    print("\n=== LIVE PLAY ===")
    print(f"RNG: {rng_info}")
    print(f"Start balance: {balance}")
    print("Commands: spin | auto N | set | rng | status | quit")

    while True:
        cmd = input("\n> ").strip()

        if cmd.lower() in ("q", "quit", "exit"):
            break

        if cmd.lower() in ("", "s", "spin"):
            balance = do_one_spin(machine, balance, s)
            continue

        if cmd.lower().startswith("auto"):
            parts = cmd.split()
            if len(parts) != 2 or not parts[1].isdigit():
                print("Usage: auto N")
                continue
            n = int(parts[1])
            balance = do_autoplay(machine, balance, s, n)
            continue

        if cmd.lower() in ("set", "settings"):
            old_payout = s.payout_mode
            s = prompt_settings(s)

            # Update machine config if needed
            if s.payout_mode != old_payout:
                machine = make_machine()
            else:
                # keep machine instance, but update defaults
                machine.bet = s.bet
                machine.active_paylines = s.paylines
            continue

        if cmd.lower() == "status":
            print("\n--- STATUS ---")
            print(f"balance     : {balance}")
            print(f"bet         : {s.bet}")
            print(f"paylines    : {s.paylines}")
            print(f"gamble_mode : {s.gamble_mode}")
            print(f"payout_mode : {s.payout_mode}")
            print(f"rng         : {rng_info}")
            continue

        if cmd.lower() in ("rng", "change rng"):
            print("\n--- CHANGE RNG ---")
            rng, rng_info = choose_rng_interactive(args)
            # rebuild machine with new RNG
            machine = make_machine()
            print(f"Now using: {rng_info}")
            continue

        print("Unknown command. Commands: spin | auto N | set | rng | status | quit")

if __name__ == "__main__":
    main()