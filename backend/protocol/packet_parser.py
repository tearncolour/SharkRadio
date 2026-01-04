
import struct
import numpy as np
from dataclasses import dataclass
from typing import List, Optional, Tuple
import time

from .crc import verify_crc8_check_sum, verify_crc16_check_sum

@dataclass
class RadarPacket:
    timestamp: float
    data_length: int
    seq: int
    crc8: int
    cmd_id: int
    payload: bytes
    crc16: int
    frame_bytes: bytes
    packet_type: str = "unknown"
    is_valid: bool = False
    
    @property
    def hex_string(self) -> str:
        return self.frame_bytes.hex().upper()

class PacketParser:
    """
    RoboMaster Radar Protocol Parser
    Frame Format:
    SOF(1) + Len(2) + Seq(1) + CRC8(1) + CmdID(2) + Data(N) + CRC16(2)
    """
    
    SOF = 0xA5
    HEADER_SIZE = 5 # SOF + Len + Seq + CRC8
    MIN_FRAME_SIZE = 9 # Header(5) + Cmd(2) + CRC16(2) (Empty Data)
    
    def __init__(self):
        self._buffer = bytearray()
        self._symbol_buffer = []  # For symbol stream processing
        
    def clear(self):
        self._buffer.clear()
        self._symbol_buffer = []
        
    def feed_bytes(self, data: bytes) -> List[RadarPacket]:
        """处理字节流，返回解析出的数据包"""
        if not data:
            return []
            
        self._buffer.extend(data)
        packets = []
        
        while len(self._buffer) >= self.MIN_FRAME_SIZE:
            # 1. 查找 SOF
            try:
                sof_index = self._buffer.index(self.SOF)
                # 丢弃 SOF 之前的数据
                if sof_index > 0:
                    del self._buffer[:sof_index]
            except ValueError:
                # 没找到 SOF，保留最后几个字节
                if len(self._buffer) > self.MIN_FRAME_SIZE:
                     del self._buffer[:-self.MIN_FRAME_SIZE]
                break
                
            # 再次检查长度
            if len(self._buffer) < self.HEADER_SIZE:
                break
                
            # 2. 预读 Header
            header_bytes = self._buffer[:self.HEADER_SIZE]
            if not verify_crc8_check_sum(header_bytes, self.HEADER_SIZE):
                # CRC8 失败，跳过这个字节
                del self._buffer[0]
                continue
                
            # 3. 解析 Length
            data_len = struct.unpack('<H', header_bytes[1:3])[0]
            
            # 合理性检查：最大数据长度检查
            MAX_DATA_LEN = 256
            if data_len > MAX_DATA_LEN:
                del self._buffer[0]
                continue
            
            # Header(5) + Cmd(2) + Data(Len) + CRC16(2)
            total_len = self.HEADER_SIZE + 2 + data_len + 2
            
            # 4. 检查缓冲区是否有完整包
            if len(self._buffer) < total_len:
                break
                
            # 5. 校验 CRC16
            frame_bytes = self._buffer[:total_len]
            if verify_crc16_check_sum(frame_bytes, total_len):
                packet = self._parse_frame(frame_bytes)
                if packet:
                    packets.append(packet)
                
                # 移除已处理的包
                del self._buffer[:total_len]
            else:
                # CRC16 失败 (不打印日志)
                del self._buffer[0]
                continue
                
        return packets
    
    def _parse_frame(self, frame_bytes: bytes) -> Optional[RadarPacket]:
        try:
            # Header
            data_len = struct.unpack('<H', frame_bytes[1:3])[0]
            seq = frame_bytes[3]
            crc8 = frame_bytes[4]
            
            # Body
            cmd_id = struct.unpack('<H', frame_bytes[5:7])[0]
            payload = frame_bytes[7:7+data_len]
            
            # Tail
            crc16 = struct.unpack('<H', frame_bytes[-2:])[0]
            
            # Identify Packet Type
            packet_type = "unknown"
            if cmd_id == 0x0201:
                packet_type = "robot_status"
            elif cmd_id == 0x0301:
                packet_type = "realtime_data"
            
            return RadarPacket(
                timestamp=time.time(),
                data_length=data_len,
                seq=seq,
                crc8=crc8,
                cmd_id=cmd_id,
                payload=payload,
                crc16=crc16,
                frame_bytes=frame_bytes,
                packet_type=packet_type,
                is_valid=True
            )
        except Exception as e:
            print(f"Parse error: {e}")
            return None

    def feed_symbols(self, symbols: np.ndarray) -> List[RadarPacket]:
        """
        输入解调后的符号数据，返回检测到的数据包
        包含 Preamble 跳转和 SOF 搜索逻辑
        """
        if len(symbols) == 0:
            return []
            
        self._symbol_buffer.extend(symbols.tolist())
        packets = []
        
        # Preamble: [3, 1, -1, -3] (0xE4)
        PREAMBLE_PATTERN = [3.0, 1.0, -1.0, -3.0]
        # SOF: 0xA5 (10 10 01 01) -> [1, 1, -1, -1]
        SOF_PATTERN = [1.0, 1.0, -1.0, -1.0]
        
        while True:
            if len(self._symbol_buffer) < 36: 
                break
                
            # 1. 查找 Preamble
            found_preamble = False
            preamble_idx = -1
            
            search_len = len(self._symbol_buffer) - 20
            buffer_view = self._symbol_buffer
            
            for i in range(search_len):
                if (abs(buffer_view[i] - PREAMBLE_PATTERN[0]) < 0.5 and
                    abs(buffer_view[i+1] - PREAMBLE_PATTERN[1]) < 0.5 and
                    abs(buffer_view[i+2] - PREAMBLE_PATTERN[2]) < 0.5 and
                    abs(buffer_view[i+3] - PREAMBLE_PATTERN[3]) < 0.5):
                    preamble_idx = i
                    found_preamble = True
                    break
            
            if not found_preamble:
                keep_len = 20 
                if len(self._symbol_buffer) > keep_len:
                    self._symbol_buffer = self._symbol_buffer[-keep_len:]
                break
            
            # 2. 跳过 Preamble 序列，找到 SOF
            pos = preamble_idx
            while pos + 4 <= len(self._symbol_buffer) - 4:
                # 检查是否还是 Preamble
                is_preamble = (
                    abs(buffer_view[pos] - PREAMBLE_PATTERN[0]) < 0.5 and
                    abs(buffer_view[pos+1] - PREAMBLE_PATTERN[1]) < 0.5 and
                    abs(buffer_view[pos+2] - PREAMBLE_PATTERN[2]) < 0.5 and
                    abs(buffer_view[pos+3] - PREAMBLE_PATTERN[3]) < 0.5
                )
                if is_preamble:
                    pos += 4
                    continue
                
                # 检查是否是 SOF
                is_sof = (
                    abs(buffer_view[pos] - SOF_PATTERN[0]) < 0.5 and
                    abs(buffer_view[pos+1] - SOF_PATTERN[1]) < 0.5 and
                    abs(buffer_view[pos+2] - SOF_PATTERN[2]) < 0.5 and
                    abs(buffer_view[pos+3] - SOF_PATTERN[3]) < 0.5
                )
                if is_sof:
                    break
                else:
                    pos += 1
            
            if pos > 0:
                self._symbol_buffer = self._symbol_buffer[pos:]
            
            # 3. 提取 Header
            if len(self._symbol_buffer) < 20:
                break
                
            header_symbols = self._symbol_buffer[:20]
            header_bytes = self._symbols_to_bytes(header_symbols)
            
            if not verify_crc8_check_sum(header_bytes, 5):
                self._symbol_buffer.pop(0)
                continue
                
            data_len = struct.unpack('<H', header_bytes[1:3])[0]
            
            # MAX LENGTH CHECK
            if data_len > 256:
                self._symbol_buffer.pop(0)
                continue
            
            total_len_bytes = 5 + 2 + data_len + 2
            total_len_symbols = total_len_bytes * 4
            
            if len(self._symbol_buffer) < total_len_symbols:
                break
                
            # 提取整帧
            frame_symbols = self._symbol_buffer[:total_len_symbols]
            frame_bytes = self._symbols_to_bytes(frame_symbols)
            
            if verify_crc16_check_sum(frame_bytes, total_len_bytes):
                packet = self._parse_frame(frame_bytes)
                if packet:
                    packets.append(packet)
                self._symbol_buffer = self._symbol_buffer[total_len_symbols:]
            else:
                self._symbol_buffer.pop(0)
        
        return packets

    def _symbols_to_bytes(self, symbols: list) -> bytes:
        """
        将符号流转换为字节流
        Mapping: 3->11, 1->10, -1->01, -3->00
        """
        byte_data = []
        num_bytes = len(symbols) // 4
        
        for i in range(num_bytes):
            byte_val = 0
            # Process 4 symbols for 1 byte (2 bits per symbol)
            # From earlier files, it seems symbols are coming in order:
            # symbol 0 -> bits 7,6
            # symbol 1 -> bits 5,4
            # symbol 2 -> bits 3,2
            # symbol 3 -> bits 1,0
            # (Assuming standard packing)
            
            for j in range(4):
                sym = symbols[i * 4 + j]
                bits = 0
                if sym > 2.0:   # 3
                    bits = 0b11
                elif sym > 0.0: # 1
                    bits = 0b10
                elif sym > -2.0: # -1
                    bits = 0b01
                else:           # -3
                    bits = 0b00
                
                byte_val = (byte_val << 2) | bits
                
            byte_data.append(byte_val)
            
        return bytes(byte_data)
