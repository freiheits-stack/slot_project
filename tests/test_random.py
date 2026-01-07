from src.rng.random_source import PseudoRandomSource, QuantumRandomSource
from src.rng.truerng import TrueRNGDevice
from src.rng.bitstore import append_bits_line, load_bits_sequence
import random

print("Test Pseudo 1:")
pseudo = PseudoRandomSource()
for i in range(5):
    print (pseudo.next_float())

print("Test Pseudo 2:")
pseudo = PseudoRandomSource(42)
for i in range(5):
    print (pseudo.next_float())

test_bits = [
    1,0,1,1,0,0,1,1,
    0,1,0,1,1,0,0,1,
    1,1,1,0,0,1,0,1,
    0,1,1,0,1,0,1,0
] 
print("Test Quantum (fixed bits):")
quantum = QuantumRandomSource(bits=test_bits)
for i in range(5):
    print(quantum.next_float())

print("Test Quantum (TrueRNG bits):")
dev = TrueRNGDevice()              # optional: TrueRNGDevice(port="COM3")
try:
    rng_bits = dev.read_bits(32 * 5)   # 5 Floats à 32 Bits
finally:
    dev.close()

quantum_rng = QuantumRandomSource(bits=rng_bits)
for i in range(5):
    print(quantum_rng.next_float())

print("Test File append multiple sequences + load random one + compare:")
BITS_FILE = "data/truerng_sequences_test.txt"    # will be created automatically
N_SEQUENCES = 5
generated_sequences = []
dev = TrueRNGDevice()                       # optional: TrueRNGDevice(port="COM3")
try:
    for j in range(N_SEQUENCES):
        seq_len = random.randint(160, 800)
        bits = dev.read_bits(seq_len)
        append_bits_line(bits, BITS_FILE)
        generated_sequences.append(bits)
        print(f"Appended seq {j} with length {seq_len}")
finally:
    dev.close()

# choose random sequence and load it
chosen_index = random.randrange(N_SEQUENCES)
loaded_bits = load_bits_sequence(BITS_FILE, index=chosen_index)

print(f"\nLoaded sequence #{chosen_index}")
print(f"Loaded length: {len(loaded_bits)}")
print(f"Expected length: {len(generated_sequences[chosen_index])}")

# compare
if loaded_bits == generated_sequences[chosen_index]:
    print("OK: Loaded bits match expected bits exactly.")
else:
    print("ERROR: Loaded bits do NOT match expected bits!")

# 4) test loaded Bits in QuantumRandomSource
print("\nTest Quantum (loaded sequence):")
quantum_loaded = QuantumRandomSource(bits=loaded_bits)
for i in range(5):
    print(quantum_loaded.next_float())