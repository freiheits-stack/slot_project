from pathlib import Path

def append_bits_line(bits, filename):
    # appends a new bit sequence as a new line to the file
    line = "".join("1" if b else "0" for b in bits) + "\n"
    Path(filename).parent.mkdir(parents=True, exist_ok=True)
    with open(filename, "a", encoding="utf-8") as f:
        f.write(line)

def load_bits_sequence(filename, index=0):
    # loads the bit sequence with given Index (0-based) from the file
    path = Path(filename)
    if not path.exists():
        raise FileNotFoundError(f"Bit file not found: {filename}")

    with open(path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i == index:
                s = line.strip()
                if not s:
                    raise ValueError(f"Empty bit sequence at line {index}")
                return [1 if ch == "1" else 0 for ch in s]

    raise IndexError(f"Requested sequence #{index}, but file has only {i+1} sequences.")