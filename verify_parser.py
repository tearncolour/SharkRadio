
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from protocol.packet_parser import PacketParser, RadarPacket
from protocol.crc import append_crc8_check_sum, append_crc16_check_sum

def create_test_frame(seq, cmd_id, data):
    # Header: SOF(A5) + Len(2) + Seq(1) + CRC8(1)
    # Len is length of data ONLY (not including cmd_id? Let's check parser logic)
    # Parser logic: total_len = HEADER_SIZE + 2 (Cmd) + data_len + 2 (CRC16)
    # And data_len is read from header.
    # So data_len should be len(data). Wait, parser says "Data: Offset 7, length data_len".
    # And CmdID is at Offset 5.
    # So the parser expects data_len to match the size of 'payload'.
    
    data_len = len(data)
    header_content = bytes([0xA5]) + data_len.to_bytes(2, 'little') + bytes([seq])
    header = append_crc8_check_sum(header_content)
    
    body = cmd_id.to_bytes(2, 'little') + data
    frame_no_tail = header + body
    frame = append_crc16_check_sum(frame_no_tail)
    
    return frame

def test_parser():
    parser = PacketParser()
    
    print("Testing PacketParser...")
    
    # 1. Test Valid Frame
    payload = b'Hello Radar'
    frame = create_test_frame(seq=1, cmd_id=0x0201, data=payload)
    print(f"Generated Frame (Hex): {frame.hex().upper()}")
    
    packets = parser.feed_bytes(frame)
    if len(packets) == 1:
        pkt = packets[0]
        print(f"[PASS] Parsed packet: Type={pkt.packet_type}, Seq={pkt.seq}, Len={pkt.data_length}")
        if pkt.payload == payload:
             print("[PASS] Payload matches")
        else:
             print(f"[FAIL] Payload mismatch: {pkt.payload}")
    else:
        print(f"[FAIL] Expected 1 packet, got {len(packets)}")

    # 2. Test Invalid CRC8
    print("\nTesting Invalid CRC8...")
    bad_header_frame = bytearray(frame)
    bad_header_frame[4] = 0x00 # Corrupt CRC8
    parser.clear()
    packets = parser.feed_bytes(bad_header_frame)
    if len(packets) == 0:
        print("[PASS] Ignored frame with bad CRC8")
    else:
        print(f"[FAIL] Parsed frame with bad CRC8")

    # 3. Test Invalid CRC16
    print("\nTesting Invalid CRC16...")
    bad_tail_frame = bytearray(frame)
    bad_tail_frame[-1] = 0x00 # Corrupt CRC16
    parser.clear()
    packets = parser.feed_bytes(bad_tail_frame)
    if len(packets) == 0:
        print("[PASS] Ignored frame with bad CRC16")
    else:
        print(f"[FAIL] Parsed frame with bad CRC16")

if __name__ == "__main__":
    test_parser()
