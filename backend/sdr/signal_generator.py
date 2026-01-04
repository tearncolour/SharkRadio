import numpy as np
import math

# 信号规格定义 (频率, 波特率, [功率dBm])
# Ref: Implementation Plan
SIGNAL_SPECS = {
    'red_broadcast':  {'freq': 433.20e6, 'baud': 250000},
    'blue_broadcast': {'freq': 433.92e6, 'baud': 250000},
    # Red Interference
    'red_jam_1':      {'freq': 432.20e6, 'baud': 500000},
    'red_jam_2':      {'freq': 432.60e6, 'baud': 285000},
    'red_jam_3':      {'freq': 433.20e6, 'baud': 200000},
    # Blue Interference
    'blue_jam_1':     {'freq': 434.92e6, 'baud': 500000},
    'blue_jam_2':     {'freq': 434.52e6, 'baud': 285000},
    'blue_jam_3':     {'freq': 433.92e6, 'baud': 200000},
    # Aliases
    'jam_1':          {'freq': 432.20e6, 'baud': 500000}, # Default to Red
    'jam_2':          {'freq': 432.60e6, 'baud': 285000},
    'jam_3':          {'freq': 433.20e6, 'baud': 200000},
}

def get_signal_params(signal_type: str) -> dict:
    """获取信号参数"""
    return SIGNAL_SPECS.get(signal_type, {'freq': 433.5e6, 'baud': 250000})

def generate_rrc_coeffs(alpha, samples_per_symbol, span):
    """
    生成 RRC (Root Raised Cosine) 滤波器系数
    """
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
            
    return coeffs / np.max(np.abs(coeffs))

def generate_signal(signal_type: str, payload: str = None, sample_rate: int = 2000000) -> np.ndarray:
    """
    生成不同类型的信号数据 (复数 float32)
    所有信号(包括干扰)均为 4-RRC-FSK 调制
    """
    
    # 获取规格参数
    params = get_signal_params(signal_type)
    baud_rate = params['baud']
    
    # 所有类型都统一使用 4-RRC-FSK 生成 (Baseband)
    # 调用者负责设置 LO 频率
    return _generate_4rrc_fsk(payload, sample_rate, baud_rate)


def _generate_4rrc_fsk(payload: str, fs: int, symbol_rate: int) -> np.ndarray:
    """
    生成 4-RRC-FSK 调制信号 
    """
    alpha = 0.25
    sps = int(fs / symbol_rate) 
    if sps < 2: sps = 2 # Prevent too low oversampling
    
    # 1. Payload to Symbols
    if not payload:
        # 随机载荷模拟干扰/广播
        # 生成足够长的随机序列 (e.g. 0.5s)
        num_symbols = int(symbol_rate * 0.5) 
        # Generate random 0-3 symbols
        # For 'Broadcast', standard recommends Preamble, but for general 'Start Signal' test, random or pattern is fine.
        # If Jamming, random is good.
        payload_bytes = np.random.randint(0, 256, size=num_symbols//4, dtype=np.uint8).tobytes()
    else:
        try:
            payload_bytes = bytes.fromhex(payload)
        except:
            payload_bytes = payload.encode('utf-8')

    # Mapping: 00->-3, 01->-1, 10->1, 11->3
    # Bytes to 2-bit chunks
    sym_val_map = {
        0: -3.0, # 00
        1: -1.0, # 01
        2:  1.0, # 10
        3:  3.0  # 11
    }
    
    symbols = []
    for b in payload_bytes:
        symbols.append(sym_val_map[(b >> 6) & 0x03])
        symbols.append(sym_val_map[(b >> 4) & 0x03])
        symbols.append(sym_val_map[(b >> 2) & 0x03])
        symbols.append(sym_val_map[(b) & 0x03])
        
    # 2. Upsample (Impulse Train)
    upsampled = np.zeros(len(symbols) * sps)
    upsampled[::sps] = symbols
    
    # 3. RRC Filtering
    rrc_coeffs = generate_rrc_coeffs(alpha, sps, span=6)
    freq_trajectory = np.convolve(upsampled, rrc_coeffs, mode='full')
    
    # 4. FM Modulation
    # Scaling factor appropriate for 4-RRC-FSK
    # Based on standard modulation index or bandwidth constraints
    # Keep deviation reasonable relative to symbol rate
    # Let's use a factor such that peak (3.0) gives approx h=0.5 shift
    # Deviation = h * Rb / 2 ?
    # Let's stick to the previous empirical factor but scaled by baud/250k
    # old factor 30000 for 250k.
    # New factor = 30000 * (baud / 250000)
    
    scaling_factor = 30000.0 * (symbol_rate / 250000.0)
                             
    dt = 1.0 / fs
    instantaneous_freq = freq_trajectory * scaling_factor
    phase = 2 * np.pi * np.cumsum(instantaneous_freq) * dt
    
    # 5. IQ Generation
    iq = np.exp(1j * phase).astype(np.complex64)
    
    # Amplitude Control (0.9 FS)
    iq = iq * 0.9 
    
    return iq
