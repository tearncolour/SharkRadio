
import sys
import numpy as np
import time

# Add backend to path
sys.path.append('backend')

from sdr.signal_generator import generate_signal
from sdr.demodulator import Demodulator, DemodulatorConfig
from protocol.packet_parser import PacketParser

def test_chain():
    print("Testing TX-RX Chain with Frame Structure...")
    
    # 1. Generate Signal
    payload_hex = "ABCD1234"
    print(f"User Payload: {payload_hex}")
    
    # 2MHz sample rate, using red_broadcast (250k symbol rate)
    iq_samples = generate_signal('red_broadcast', payload=payload_hex, sample_rate=2000000)
    print(f"Generated {len(iq_samples)} IQ samples")
    
    # 2. Demodulate
    config = DemodulatorConfig.from_signal_type('red_broadcast', sample_rate=2000000)
    demodulator = Demodulator(config)
    
    symbols, decoded_bytes = demodulator.demodulate(iq_samples)
    print(f"Demodulated {len(symbols)} symbols, {len(decoded_bytes)} bytes")
    
    if len(decoded_bytes) == 0:
        print("[FAIL] No bytes decoded")
        return False

    # 3. Parse
    parser = PacketParser()
    # Use feed_symbols to handle symbol alignment (Preamble search)
    packets = parser.feed_symbols(symbols)
    
    if not packets:
        print("[FAIL] No valid packets found after demodulation")
        # Try feed_bytes just to see debug info
        # parser.clear()
        # parser.feed_bytes(decoded_bytes)
        print(f"Raw Bytes snippet: {decoded_bytes[:50].hex().upper()}...")
        return False
        
    print(f"[PASS] Successfully parsed {len(packets)} packets")
    
    first_packet = packets[0]
    print(f"Packet: Type={first_packet.packet_type}, DataLen={first_packet.data_length}")
    print(f"Payload: {first_packet.payload.hex().upper()}")
    
    if first_packet.payload.hex().upper() == payload_hex:
        print("[PASS] Payload matches transmitted data")
        return True
    else:
        print(f"[FAIL] Payload mismatch! Expected {payload_hex}, got {first_packet.payload.hex().upper()}")
        return False

if __name__ == "__main__":
    try:
        if test_chain():
            sys.exit(0)
        else:
            sys.exit(1)
    except Exception as e:
        print(f"Exception during test: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
