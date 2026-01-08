import serial.tools.list_ports

def auto_detect_rng_port():
    """
    Automatically detect the COM port of a connected TrueRNG3 or similar USB serial device.
    Looks for common identifiers in the device description.
    """
    keywords = ['TrueRNG', 'USB Serial','Serielles USB']
    ports = list(serial.tools.list_ports.comports())

    for port in ports:
        desc = port.description.lower()
        if any(keyword.lower() in desc for keyword in keywords):
            print(f"Detected TrueRNG device: {port.device} ({port.description})")
            return port.device

    print("No matching TrueRNG COM port found.")
    return None

class TrueRNGDevice:
    def __init__(self, port=None, baudrate=300000, timeout=1):
        if port is None:
            port = auto_detect_rng_port()
        if not port:
            raise RuntimeError("TrueRNG COM port not found")

        self.ser = serial.Serial(port, baudrate, timeout=timeout)

    def read_bits(self, count):
        bits = []
        while len(bits) < count:
            raw = self.ser.read(1)
            if not raw:
                continue
            byte = raw[0]
            for i in range(8):
                bits.append((byte >> i) & 1)
                if len(bits) == count:
                    break
        return bits

    def close(self):
        try:
            self.ser.close()
        except Exception:
            pass