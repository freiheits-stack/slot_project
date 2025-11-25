
import random


class PseudoRandomSource:
    # Baseclass for random source
    def __init__(self, seed = None):
        # Constructor with optional seed for reproducable Values
        self.random_number = random.Random(seed)

    def next_float(self):
        # Number between [0, 1)
        return self.random_number.random()
    
class QuantumRandomSource:
    # Generate quantum random number
    def __init__(self, bits):
        self.bits = bits
        self.pos = 0

    def next_float(self):
        # Slice in 32 bit pieces
        if self.pos + 32 >= len(self.bits):
            self.pos = 0
        chunk = self.bits[self.pos : self.pos + 32]
        self.pos += 32

        # change to int
        for index, bit in enumerate(chunk):
            pos_chunk = 31 - index
            if bit == 1:
                value += 2 ** pos_chunk

        # normalize to [0, 1)
        return value / (2**32)
        



        
