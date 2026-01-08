from config import default_slot_config
from slot_machine import SlotMachine

from random_source import PseudoRandomSource, QuantumRandomSource
from bitstore import load_bits_sequence

# optional live TrueRNG
try:
    from truerng import TrueRNGDevice
    TRUERNG_AVAILABLE = True
except Exception:
    TRUERNG_AVAILABLE = False


def build_rng():
    print("Choose RNG source:")
    print("  1) pseudo")
    print("  2) quantum (load bits from file)")
    if TRUERNG_AVAILABLE:
        print("  3) quantum (live TrueRNG)")

    choice = input("Your choice: ").strip()

    if choice == "1":
        seed_txt = input("Seed (empty = none): ").strip()
        seed = int(seed_txt) if seed_txt else None
        return PseudoRandomSource(seed)

    if choice == "2":
        filename = input("Bits filename (e.g. data/truerng_sequences_offline.txt): ").strip()
        index_txt = input("Sequence index (0-based, default 0): ").strip()
        index = int(index_txt) if index_txt else 0
        bits = load_bits_sequence(filename, index=index)
        return QuantumRandomSource(bits)

    if choice == "3" and TRUERNG_AVAILABLE:
        bits_txt = input("How many bits to read (e.g. 2000000): ").strip()
        n_bits = int(bits_txt)
        dev = TrueRNGDevice()  # or TrueRNGDevice(port="COM3")
        try:
            bits = dev.read_bits(n_bits)
        finally:
            dev.close()
        return QuantumRandomSource(bits)

    raise ValueError("Invalid choice.")


def main():
    rng = build_rng()
    cfg = default_slot_config()

    bet_txt = input("Bet per spin (default 1.0): ").strip()
    bet = float(bet_txt) if bet_txt else 1.0

    n_txt = input("Autoplay spins (default 15000): ").strip()
    n_spins = int(n_txt) if n_txt else 15000

    gamble_txt = input("Enable gamble (double-or-nothing)? (y/N): ").strip().lower()
    do_gamble = gamble_txt == "y"

    machine = SlotMachine(cfg, rng, bet=bet)
    stats = machine.autoplay(n_spins=n_spins, do_gamble=do_gamble)

    print("\n--- Results ---")
    for k in ["n_spins", "bet", "total_bet", "total_base_win", "total_final_win", "rtp_base", "rtp_final", "hit_rate_base", "hit_rate_final", "gamble_count", "gamble_win_rate"]:
        print(f"{k}: {stats[k]}")

    print("\nPayline hits:", stats["payline_hits"])
    print("Symbol hits:", stats["symbol_hits"])


if __name__ == "__main__":
    main()