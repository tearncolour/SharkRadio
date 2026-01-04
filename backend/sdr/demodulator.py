
"""
4-RRC-FSK Demodulator Module
实现完整的 4-RRC-FSK 接收解调链路
"""

import numpy as np
from typing import Tuple, Optional
from dataclasses import dataclass

try:
    from gnuradio import digital, gr
    from gnuradio.filter import firdes
    GNURADIO_AVAILABLE = True
except ImportError:
    GNURADIO_AVAILABLE = False
    print("Warning: GNU Radio not available for demodulator")


@dataclass
class DemodulatorConfig:
    """解调器配置参数"""
    sample_rate: int = 2_000_000      # 采样率 2 MHz
    symbol_rate: int = 250_000        # 符号率 250 kbaud
    sensitivity: float = 0.54         # FM 调制灵敏度 (与 TX 一致)
    rrc_alpha: float = 0.25           # RRC 滚降因子
    
    @property
    def samples_per_symbol(self) -> int:
        return self.sample_rate // self.symbol_rate

    @staticmethod
    def from_signal_type(signal_type: str, sample_rate: int = 2_000_000) -> 'DemodulatorConfig':
        """
        根据信号类型创建配置
        
        Args:
            signal_type: 信号类型 ('red_broadcast', 'red_jam_1', etc.)
            sample_rate: 采样率
            
        Returns:
            DemodulatorConfig 实例
        """
        # 默认 250k
        symbol_rate = 250_000
        
        if 'jam_1' in signal_type:
            symbol_rate = 500_000
        elif 'jam_2' in signal_type:
            symbol_rate = int(2_000_000 / 7) # ~285.7k (SPS=7)
        elif 'jam_3' in signal_type:
            symbol_rate = 200_000
            
        print(f"[Demodulator] Creating config for signal_type={signal_type}, symbol_rate={symbol_rate}")
        
        return DemodulatorConfig(
            sample_rate=sample_rate,
            symbol_rate=symbol_rate
        )


class Demodulator:
    """
    4-RRC-FSK 解调器
    
    信号处理链路:
    IQ Samples -> FM Demod -> RRC Filter -> Clock Recovery -> Symbol Decision
    """
    
    # 符号映射: 频率偏移值 -> 2-bit 索引
    # TX: 00->-3, 01->-1, 10->1, 11->3
    # RX 需要反向映射
    SYMBOL_VALUES = np.array([-3.0, -1.0, 1.0, 3.0])
    SYMBOL_BITS = [(0, 0), (0, 1), (1, 0), (1, 1)]
    
    def __init__(self, config: Optional[DemodulatorConfig] = None):
        self.config = config or DemodulatorConfig()
        self._rrc_taps = self._generate_rrc_taps()
        
        # Streaming state for clock recovery
        self._last_offset = None  # Persistent optimal offset
        self._sample_buffer = np.array([], dtype=np.float32)  # Edge samples buffer
        
    def _generate_rrc_taps(self) -> np.ndarray:
        """生成 RRC 匹配滤波器系数
        
        注意: RX 端使用 gain=1.0 进行匹配滤波
        TX 端使用 gain=sps 进行插值补偿
        """
        sps = self.config.samples_per_symbol
        alpha = self.config.rrc_alpha
        ntaps = 11 * sps
        
        if GNURADIO_AVAILABLE:
            taps = firdes.root_raised_cosine(
                float(sps),                 # Gain = sps for matched filter output scaling
                self.config.sample_rate,    # Sampling rate
                self.config.symbol_rate,    # Symbol rate
                alpha,                      # Alpha
                ntaps                       # Num taps
            )
        else:
            # Fallback implementation
            t = np.arange(-ntaps//2, ntaps//2 + 1) / self.config.sample_rate
            ts = 1 / self.config.symbol_rate
            
            # Avoid division by zero
            t = t + 1e-9
            
            val = (np.sin(np.pi * t / ts * (1 - alpha)) + 
                   4 * alpha * t / ts * np.cos(np.pi * t / ts * (1 + alpha))) / \
                  (np.pi * t / ts * (1 - (4 * alpha * t / ts)**2))
            
            taps = val / np.sqrt(np.sum(val**2))  # Normalize for RX
            
        return np.array(taps)
    
    def fm_demodulate(self, samples: np.ndarray) -> np.ndarray:
        """
        FM 解调: 计算相位差
        Output = angle(sample[n] * conj(sample[n-1]))
        """
        # 相位差分
        phase_diff = np.angle(samples[1:] * np.conj(samples[:-1]))
        
        # 归一化: map to symbol range
        # Phase diff = 2*pi * f_dev * T_sample
        # f_dev = symbol_val * h * symbol_rate / 2
        # where deviation h=0.5 (MSK-like)? No, specific sensitivity
        
        # 使用配置的灵敏度进行归一化
        demod = phase_diff / self.config.sensitivity
        
        return demod.astype(np.float32)

    def apply_rrc_filter(self, signal: np.ndarray) -> np.ndarray:
        """应用 RRC 匹配滤波"""
        if len(signal) < len(self._rrc_taps):
            return signal
        return np.convolve(signal, self._rrc_taps, mode='valid')

    def symbol_decision(self, symbols: np.ndarray) -> np.ndarray:
        """
        硬判决: 将连续值映射到 {-3, -1, 1, 3}
        """
        # 简单阈值判决
        # -3: < -2
        # -1: -2 ~ 0
        #  1: 0 ~ 2
        #  3: > 2
        
        decisions = np.zeros_like(symbols)
        
        decisions[symbols < -2.0] = -3.0
        decisions[(symbols >= -2.0) & (symbols < 0.0)] = -1.0
        decisions[(symbols >= 0.0) & (symbols < 2.0)] = 1.0
        decisions[symbols >= 2.0] = 3.0
        
        return decisions

    def symbols_to_bytes(self, symbols: np.ndarray) -> bytes:
        """
        将符号序列转换为字节流
        Mapping depends on protocol. 
        Usually 4 symbols = 1 byte (2 bits/symbol)
        """
        # 假设:
        # 3 -> 11
        # 1 -> 10
        # -1 -> 01
        # -3 -> 00
        
        # Verify length
        n_bytes = len(symbols) // 4
        byte_data = bytearray()
        
        for i in range(n_bytes):
            val = 0
            for j in range(4):
                sym = symbols[i*4 + j]
                bits = 0
                if sym > 2.0: bits = 0b11
                elif sym > 0.0: bits = 0b10
                elif sym > -2.0: bits = 0b01
                else: bits = 0b00
                
                val = (val << 2) | bits
            byte_data.append(val)
            
        return bytes(byte_data)

    def clock_recovery_gnuradio(self, signal: np.ndarray) -> np.ndarray:
        """
        快速矢量化时钟恢复 (支持流式处理)
        
        使用最小 MSE 法找到最佳采样偏移 (相对于理想符号电平)
        对于流式处理，使用上一次的偏移作为初始值
        
        Args:
            signal: RRC 滤波后的信号 (float32)
            
        Returns:
            符号采样值数组
        """
        sps = self.config.samples_per_symbol
        n_samples = len(signal)
        
        if n_samples < sps * 4:
            offset = self._last_offset if self._last_offset is not None else sps // 2
            return signal[offset::sps]
        
        # 理想符号电平
        ideal_levels = np.array([-3.0, -1.0, 1.0, 3.0])
        
        # 如果有之前的偏移，先测试它是否仍然有效
        if self._last_offset is not None:
            samples = signal[self._last_offset::sps]
            if len(samples) >= 10:
                distances = np.abs(samples[:, np.newaxis] - ideal_levels)
                min_distances = np.min(distances, axis=1)
                current_mse = np.mean(min_distances ** 2)
                
                # 如果 MSE 足够小 (< 0.5)，继续使用上次的偏移
                if current_mse < 0.5:
                    return samples
        
        # 需要重新搜索最佳偏移
        best_offset = self._last_offset if self._last_offset is not None else 0
        best_mse = float('inf')
        
        for offset in range(sps):
            samples = signal[offset::sps]
            if len(samples) < 10:
                continue
            
            distances = np.abs(samples[:, np.newaxis] - ideal_levels)
            min_distances = np.min(distances, axis=1)
            mse = np.mean(min_distances ** 2)
            
            if mse < best_mse:
                best_mse = mse
                best_offset = offset
        
        # 保存偏移供下次使用
        self._last_offset = best_offset
        
        symbols = signal[best_offset::sps]
        return symbols

    def demodulate(self, iq_samples: np.ndarray) -> Tuple[np.ndarray, bytes]:
        """
        解调 IQ 信号
        
        Returns:
            (symbols, decoded_bytes)
        """
        # 1. FM Demodulation
        fm_demod = self.fm_demodulate(iq_samples)
        
        # 2. RRC Filter
        filtered = self.apply_rrc_filter(fm_demod)
        
        # 3. Clock Recovery (Symbol Sync)
        # Normalize signal amplitude to help Clock Recovery loop stability
        # Use Adaptive Normalization (AGC-like) to handle varying RX Gains
        # Target amplitude: ±3.0 (ideal for symbol decision)
        
        # Calculate recent peak amplitude (simple block-based AGC)
        peak_amp = np.max(np.abs(filtered))
        if peak_amp > 1e-6:
            # Smooth scaling factor could be better, but block-based is fine for now
            # if buffer size is large enough.
            scale_factor = 3.0 / peak_amp
            filtered = filtered * scale_factor
        
        symbols = self.clock_recovery_gnuradio(filtered)
        
        # 4. Symbol Decision (Hard)
        decisions = self.symbol_decision(symbols)
        
        # 5. Convert to Bytes
        decoded_bytes = self.symbols_to_bytes(decisions)
        
        return decisions, decoded_bytes


# 便捷函数
def create_demodulator(sample_rate: int = 2_000_000, 
                       symbol_rate: int = 250_000) -> Demodulator:
    """创建解调器实例"""
    config = DemodulatorConfig(
        sample_rate=sample_rate,
        symbol_rate=symbol_rate
    )
    return Demodulator(config)
