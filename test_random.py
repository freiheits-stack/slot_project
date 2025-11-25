from random_source import PseudoRandomSource, QuantumRandomSource

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
print("Test Quantum:")
quantum = QuantumRandomSource(bits=test_bits)
for i in range(5):
    print(quantum.next_float())