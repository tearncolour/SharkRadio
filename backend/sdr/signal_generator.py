
import numpy as np
import math
import struct
import sys
import os

# Ensure we can import from protocol
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
from protocol.crc import append_crc8_check_sum, append_crc16_check_sum

# 信号规格定义 (频率, 波特率, 带宽, 功率dBm)
# Ref: Implementation Plan - RoboMaster 2026 规则
SIGNAL_SPECS = {
    # 红方信号
    'red_broadcast':  {'freq': 433.20e6, 'baud': 250000, 'bandwidth': 540000,  'power': -10}, # Debug: -10 (Rule: -60)
    'red_jam_1':      {'freq': 432.20e6, 'baud': 500000, 'bandwidth': 1040000, 'power': -10},
    'red_jam_2':      {'freq': 432.60e6, 'baud': 285000, 'bandwidth': 610000,  'power': 10},
    'red_jam_3':      {'freq': 433.20e6, 'baud': 200000, 'bandwidth': 440000,  'power': -10},
    # 蓝方信号
    'blue_broadcast': {'freq': 433.92e6, 'baud': 250000, 'bandwidth': 540000,  'power': -10}, # Debug: -10 (Rule: -60)
    'blue_jam_1':     {'freq': 434.92e6, 'baud': 500000, 'bandwidth': 1040000, 'power': -10},
    'blue_jam_2':     {'freq': 434.52e6, 'baud': 285000, 'bandwidth': 610000,  'power': 10},
    'blue_jam_3':     {'freq': 433.92e6, 'baud': 200000, 'bandwidth': 440000,  'power': -10},
    # 别名 (默认红方)
    'jam_1':          {'freq': 432.20e6, 'baud': 500000, 'bandwidth': 1040000, 'power': -10},
    'jam_2':          {'freq': 432.60e6, 'baud': 285000, 'bandwidth': 610000,  'power': 10},
    'jam_3':          {'freq': 433.20e6, 'baud': 200000, 'bandwidth': 440000,  'power': -10},
}

def get_signal_params(signal_type: str) -> dict:
    """获取信号参数"""
    return SIGNAL_SPECS.get(signal_type, {'freq': 433.5e6, 'baud': 250000})

def generate_rrc_coeffs(alpha, samples_per_symbol, span, fs, symbol_rate):
    """
    生成 RRC (Root Raised Cosine) 滤波器系数
    """
    try:
        from gnuradio.filter import firdes
        
        # Match GRC implementation exactly:
        gain = float(samples_per_symbol)  # TX Interpolation gain = SPS
        ntaps = 11 * samples_per_symbol  # Approximately 88 for sps=8
        
        coeffs = firdes.root_raised_cosine(
            gain,           # Gain = SPS for interpolation
            fs,             # Sampling frequency
            symbol_rate,    # Symbol rate
            alpha,          # Roll-off factor
            ntaps           # Number of taps
        )
        return np.array(coeffs)
        
    except ImportError:
        print("Warning: GNU Radio not found, falling back to simple RRC implementation")
        # Fallback implementation
        if samples_per_symbol <= 0: return np.array([1.0])
        t = np.arange(-span*samples_per_symbol, span*samples_per_symbol + 1) / samples_per_symbol
        coeffs = np.zeros_like(t)
        for i, ti in enumerate(t):
            if ti == 0:
                coeffs[i] = 1 - alpha + 4*alpha/np.pi
            elif abs(abs(ti) - 1/(4*alpha)) < 1e-5:
                coeffs[i] = (alpha/np.sqrt(2)) * ((1+2/np.pi)*np.sin(np.pi/(4*alpha)) + (1-2/np.pi)*np.cos(np.pi/(4*alpha)))
            else:
                num = np.sin(np.pi*ti*(1-alpha)) + 4*alpha*ti*np.cos(np.pi*ti*(1+alpha))
                denom = np.pi*ti*(1 - (4*alpha*ti)**2)
                coeffs[i] = num / denom
        # Normalize to unit energy, then scale by samples_per_symbol
        return (coeffs / np.sum(coeffs)) * samples_per_symbol

def _construct_frame(payload: bytes, cmd_id: int = 0x0201) -> bytes:
    """
    构造 RoboMaster 协议帧
    Preamble (4B) + SOF (1B) + Len (2B) + Seq (1B) + CRC8 (1B) + CmdID (2B) + Data (N) + CRC16 (2B)
    """
    # Preamble: [3,1,-1,-3] repeated 32 times -> 0xE4 repeated 32 times
    # Increased from 4 to 32 to allow RX AGC/Clock Recovery to lock before SOF
    PREAMBLE = bytes([0xE4] * 32)
    SOF = 0xA5
    
    data_len = len(payload)
    seq = 0x00 # Sequence number (fixed for broadcast)
    
    # Header: SOF + Len(2, LE) + Seq + CRC8
    # CRC8 covers [SOF, Len, Seq]
    header_data = struct.pack('<BHB', SOF, data_len, seq)
    header_with_crc = append_crc8_check_sum(header_data)
    
    # Body: CmdID(2, LE) + Data
    body = struct.pack('<H', cmd_id) + payload
    
    # Frame for CRC16: Header(with CRC8) + Body
    # Note: CRC8 is INCLUDED in CRC16 calculation (per some RM implementations)
    # Actually standard RM protocol: CRC16 covers whole frame from SOF to end of Data
    
    frame_content = header_with_crc + body
    frame_with_crc16 = append_crc16_check_sum(frame_content)
    
    return PREAMBLE + frame_with_crc16

def generate_signal(signal_type: str, payload: str = None, sample_rate: int = 2000000) -> np.ndarray:
    """
    生成不同类型的信号数据 (复数 float32)
    所有信号(包括干扰)均为 4-RRC-FSK 调制
    """
    params = get_signal_params(signal_type)
    baud_rate = params['baud']
    return _generate_4rrc_fsk(payload, sample_rate, baud_rate)

def _generate_4rrc_fsk(payload: str, fs: int, symbol_rate: int) -> np.ndarray:
    """
    生成 4-RRC-FSK 调制信号 
    """
    alpha = 0.25
    sps = int(fs / symbol_rate) 
    if sps < 2: sps = 2 
    
    # 1. Payload to Bytes
    if not payload:
        # 无载荷时使用随机数据 (但仍封装为帧?)
        # 干扰信号可能不需要帧结构，但在我们的 verify_tx_chain 中，我们需要帧
        # 这里为了简单，如果是随机数据，就不封装帧了 (或者是简单的干扰)
        # 但如果是 'ABCD'... 则认为是测试 payload
        num_symbols = int(symbol_rate * 0.05) # short burst
        payload_bytes = np.random.randint(0, 256, size=num_symbols//4, dtype=np.uint8).tobytes()
        frame_bytes = payload_bytes # Raw random data
    else:
        # 解析用户提供的载荷
        try:
            user_data = bytes.fromhex(payload)
        except:
            user_data = payload.encode('utf-8')
            
        # 构造完整协议帧
        frame_bytes = _construct_frame(user_data)
        
    # Mapping: 00->-3, 01->-1, 10->1, 11->3
    # Bytes to 2-bit chunks
    sym_val_map = {
        0: -3.0, # 00
        1: -1.0, # 01
        2:  1.0, # 10
        3:  3.0  # 11
    }
    
    symbols = []
    for b in frame_bytes:
        symbols.append(sym_val_map[(b >> 6) & 0x03])
        symbols.append(sym_val_map[(b >> 4) & 0x03])
        symbols.append(sym_val_map[(b >> 2) & 0x03])
        symbols.append(sym_val_map[(b) & 0x03])
        
    # 2. Upsample (Impulse Train)
    upsampled = np.zeros(len(symbols) * sps)
    upsampled[::sps] = symbols
    
    # 3. RRC Filtering (Interpolation)
    rrc_coeffs = generate_rrc_coeffs(alpha, sps, span=6, fs=fs, symbol_rate=symbol_rate)
    
    # Apply interpolation filter (convolve with upsampled signal)
    freq_trajectory = np.convolve(upsampled, rrc_coeffs, mode='full')
    
    # 4. FM Modulation
    sensitivity = 0.54
    phase = np.cumsum(sensitivity * freq_trajectory)
    
    # 5. IQ Generation
    iq = np.exp(1j * phase).astype(np.complex64)
    
    # Amplitude Control
    iq = iq * 0.9 
    
    # Cyclic Buffer Logic (Ensure min size)
    MIN_SAMPLES = 32768
    if len(iq) < MIN_SAMPLES and len(iq) > 0:
        repeats = int(np.ceil(MIN_SAMPLES / len(iq)))
        iq = np.tile(iq, repeats)
    
    return iq
