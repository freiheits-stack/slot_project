from src.rng.truerng import TrueRNGDevice
from src.rng.bitstore import append_bits_line

def main():
    OUT_FILE = "data/truerng_sequences.txt"

    # 50 x 15_000 x 4 x 1.2
    N_SEQUENCES = 50
    SPINS_TARGET = 7_000
    DRAWS_PER_SPIN = 10          # 3 for spinning wheels and 1 for gamble option
    SAFETY = 1.2

    bits_needed = int(SPINS_TARGET * DRAWS_PER_SPIN * SAFETY * 32)       # 32 Bits per draw

    print(f"Generating {N_SEQUENCES} sequences")
    print(f"Target: {SPINS_TARGET} spins, {DRAWS_PER_SPIN} draws/spin, safety {SAFETY}")
    print(f"=> {bits_needed} bits per sequence")

    dev = TrueRNGDevice()  # optional: TrueRNGDevice(port="COM3")
    try:
        for i in range(N_SEQUENCES):
            bits = dev.read_bits(bits_needed)
            append_bits_line(bits, OUT_FILE)
            print(f"Saved sequence {i+1}/{N_SEQUENCES} ({len(bits)} bits) -> {OUT_FILE}")
    finally:
        dev.close()

if __name__ == "__main__":
    main()