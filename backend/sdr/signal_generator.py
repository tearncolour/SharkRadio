import numpy as np
import math

# 信号规格定义 (频率, 波特率, 带宽, 功率dBm)
# Ref: Implementation Plan - RoboMaster 2026 规则
SIGNAL_SPECS = {
    # 红方信号
    'red_broadcast':  {'freq': 433.20e6, 'baud': 250000, 'bandwidth': 540000,  'power': -60},
    'red_jam_1':      {'freq': 432.20e6, 'baud': 500000, 'bandwidth': 1040000, 'power': -10},
    'red_jam_2':      {'freq': 432.60e6, 'baud': 285000, 'bandwidth': 610000,  'power': 10},
    'red_jam_3':      {'freq': 433.20e6, 'baud': 200000, 'bandwidth': 440000,  'power': -10},
    # 蓝方信号
    'blue_broadcast': {'freq': 433.92e6, 'baud': 250000, 'bandwidth': 540000,  'power': -60},
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
    使用 GNU Radio 库实现，参数匹配 GRC
    
    Args:
        alpha: Roll-off factor
        samples_per_symbol: Samples per symbol (interpolation factor)
        span: Filter span in symbols (not used with firdes, for fallback)
        fs: Actual sampling frequency (Hz)
        symbol_rate: Actual symbol rate (Hz)
    """
    try:
        from gnuradio.filter import firdes
        
        # Match GRC implementation exactly:
        # firdes.root_raised_cosine(gain, samp_rate, symbol_rate, alpha, ntaps)
        # gain = 1.0 (GRC uses 1.0, not sps)
        # ntaps = 88 (GRC fixed value, roughly 11 * sps for sps=8)
        
        gain = 1.0  # GRC uses 1.0
        ntaps = 11 * samples_per_symbol  # Approximately 88 for sps=8
        
        coeffs = firdes.root_raised_cosine(
            gain,           # Gain (1.0 as in GRC)
            fs,             # Sampling frequency (actual, e.g. 2e6)
            symbol_rate,    # Symbol rate (actual, e.g. 250e3)
            alpha,          # Roll-off factor (0.25)
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
    # 纯载荷重复模式：使用用户提供的载荷直接重复
    
    if not payload:
        # 无载荷时使用随机数据 (0.5秒)
        num_symbols = int(symbol_rate * 0.5)
        payload_bytes = np.random.randint(0, 256, size=num_symbols//4, dtype=np.uint8).tobytes()
    else:
        # 解析用户提供的载荷（会在后续被循环重复）
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
    
    # 3. RRC Filtering (Interpolation)
    # Match GRC: interp_fir_filter with RRC coefficients
    rrc_coeffs = generate_rrc_coeffs(alpha, sps, span=6, fs=fs, symbol_rate=symbol_rate)
    
    # Apply interpolation filter (convolve with upsampled signal)
    freq_trajectory = np.convolve(upsampled, rrc_coeffs, mode='full')
    
    # 4. FM Modulation
    # Match GRC: analog.frequency_modulator_fc with sensitivity 0.54
    # This is phase sensitivity (radians per sample per input unit)
    # For symbol values [-3, -1, 1, 3], max symbol = 3
    # Instantaneous frequency = sensitivity * input
    
    # Use GRC's sensitivity directly
    sensitivity = 0.54
    
    # Calculate instantaneous phase change per sample
    # phase_change[n] = sensitivity * freq_trajectory[n]
    # Cumulative phase
    phase = np.cumsum(sensitivity * freq_trajectory)
    
    # 5. IQ Generation
    iq = np.exp(1j * phase).astype(np.complex64)
    
    # Amplitude Control (0.9 FS)
    iq = iq * 0.9 
    
    # Ensure minimum buffer size for stable Cyclic TX
    # Small buffers (< 4096 samples) can cause underflow/instability in Pluto DMA
    MIN_SAMPLES = 32768 # 16k is safe, 32k is safer for 2MSPS
    if len(iq) < MIN_SAMPLES and len(iq) > 0:
        repeats = int(np.ceil(MIN_SAMPLES / len(iq)))
        iq = np.tile(iq, repeats)
    
    return iq
