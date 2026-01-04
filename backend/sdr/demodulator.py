"""
4-RRC-FSK Demodulator Module
实现完整的 4-RRC-FSK 接收解调链路
"""

import numpy as np
from typing import Tuple, Optional
from dataclasses import dataclass

try:
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
        
    def _generate_rrc_taps(self) -> np.ndarray:
        """生成 RRC 匹配滤波器系数"""
        sps = self.config.samples_per_symbol
        alpha = self.config.rrc_alpha
        ntaps = 11 * sps
        
        if GNURADIO_AVAILABLE:
            taps = firdes.root_raised_cosine(
                1.0,                        # Gain
                self.config.sample_rate,    # Sampling rate
                self.config.symbol_rate,    # Symbol rate
                alpha,                      # Alpha
                ntaps                       # Num taps
            )
            return np.array(taps)
        else:
            # Fallback: 简化 RRC 实现
            t = np.arange(-ntaps//2, ntaps//2 + 1) / sps
            coeffs = np.zeros_like(t, dtype=float)
            for i, ti in enumerate(t):
                if ti == 0:
                    coeffs[i] = 1 - alpha + 4*alpha/np.pi
                elif abs(abs(ti) - 1/(4*alpha)) < 1e-5:
                    coeffs[i] = (alpha/np.sqrt(2)) * ((1+2/np.pi)*np.sin(np.pi/(4*alpha)) + (1-2/np.pi)*np.cos(np.pi/(4*alpha)))
                else:
                    num = np.sin(np.pi*ti*(1-alpha)) + 4*alpha*ti*np.cos(np.pi*ti*(1+alpha))
                    denom = np.pi*ti*(1 - (4*alpha*ti)**2)
                    if abs(denom) > 1e-10:
                        coeffs[i] = num / denom
            return coeffs / np.sum(np.abs(coeffs))
    
    def fm_demodulate(self, iq_samples: np.ndarray) -> np.ndarray:
        """
        FM 解调: 通过相位差分提取瞬时频率
        
        Args:
            iq_samples: 复数 IQ 样本数组
            
        Returns:
            瞬时频率数组 (与符号值成正比)
        """
        if len(iq_samples) < 2:
            return np.array([])
            
        # 相位差分法: θ[n] = angle(iq[n] * conj(iq[n-1]))
        # 这给出瞬时相位变化，与瞬时频率成正比
        phase_diff = np.angle(iq_samples[1:] * np.conj(iq_samples[:-1]))
        
        # 归一化到符号值范围 [-3, 3]
        # phase_diff = sensitivity * symbol_value
        # symbol_value = phase_diff / sensitivity
        freq_estimate = phase_diff / self.config.sensitivity
        
        return freq_estimate
    
    def apply_rrc_filter(self, signal: np.ndarray) -> np.ndarray:
        """
        应用 RRC 匹配滤波器
        
        Args:
            signal: FM 解调后的频率估计信号
            
        Returns:
            滤波后的信号
        """
        if len(signal) < len(self._rrc_taps):
            return signal
        return np.convolve(signal, self._rrc_taps, mode='same')
    
    def clock_recovery_gardner(self, signal: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Gardner 时钟恢复算法 (Timing Error Detector)
        
        Gardner TED 公式:
        e[n] = (y[n] - y[n-1]) * y[n-0.5]
        
        其中 y[n-0.5] 是符号中点的插值样本
        
        Args:
            signal: RRC 滤波后的信号
            
        Returns:
            (采样时刻索引, 采样值)
        """
        sps = self.config.samples_per_symbol
        
        if len(signal) < sps * 4:
            # 信号太短，使用简单方法
            sample_indices = np.arange(0, len(signal), sps)
            return sample_indices, signal[sample_indices] if len(sample_indices) > 0 else np.array([])
        
        # Gardner 环路参数
        # 环路带宽 (BL) 影响收敛速度和稳定性
        loop_bw = 0.01  # 归一化环路带宽
        
        # 计算环路系数 (二阶环路)
        damping = 1.0  # 阻尼因子
        theta = loop_bw / (damping + 0.25 / damping)
        d = 1 + 2*damping*theta + theta**2
        
        # 比例和积分增益
        K1 = 4*damping*theta / d  # 比例增益
        K2 = 4*theta**2 / d       # 积分增益
        
        # 初始化
        mu = 0.0  # 分数间隔 (0 <= mu < 1)
        strobe = False
        
        # 输出
        symbols_out = []
        indices_out = []
        
        # 环路滤波器状态
        v_p = 0.0  # 比例分量
        v_i = 0.0  # 积分分量
        
        # 历史样本用于插值
        d_0 = 0.0  # 当前符号
        d_1 = 0.0  # 中点样本
        d_2 = 0.0  # 上一个符号
        
        i = 2 * sps  # 从第 2 个符号开始以确保有足够历史
        
        while i < len(signal) - 1:
            # 线性插值获取当前位置的样本
            if i + 1 < len(signal):
                # 在位置 i + mu 进行线性插值
                y = signal[i] + mu * (signal[i+1] - signal[i])
            else:
                y = signal[i]
            
            # 更新样本历史
            d_2 = d_1
            d_1 = d_0
            d_0 = y
            
            # 每 sps 个样本输出一个符号
            strobe = (i % sps == 0)
            
            if strobe and len(symbols_out) > 0:
                # Gardner 时间误差检测
                # e = (d_0 - d_2) * d_1
                # d_1 是中点样本 (在 d_0 和 d_2 之间)
                
                # 获取中点样本 (大约在半个符号周期前)
                mid_idx = max(0, i - sps // 2)
                if mid_idx < len(signal):
                    d_mid = signal[mid_idx]
                else:
                    d_mid = d_1
                
                # 时间误差
                timing_error = (d_0 - d_2) * d_mid
                
                # 环路滤波器
                v_p = K1 * timing_error
                v_i = v_i + K2 * timing_error
                
                # 更新分数间隔
                mu = mu + v_p + v_i
                
                # 限制 mu 范围
                while mu >= 1.0:
                    mu -= 1.0
                    i += 1  # 跳过一个样本
                while mu < 0.0:
                    mu += 1.0
                    i -= 1  # 回退一个样本
            
            if strobe:
                symbols_out.append(y)
                indices_out.append(i)
            
            i += 1
        
        return np.array(indices_out), np.array(symbols_out)
    
    def symbol_decision(self, samples: np.ndarray) -> np.ndarray:
        """
        符号判决: 将采样值映射到最近的符号 (-3, -1, 1, 3)
        
        Args:
            samples: 时钟恢复后的采样值
            
        Returns:
            判决后的符号值数组 (-3, -1, 1, 3)
        """
        # 计算每个样本到每个符号值的距离
        # 选择最近的符号
        distances = np.abs(samples[:, np.newaxis] - self.SYMBOL_VALUES[np.newaxis, :])
        nearest_indices = np.argmin(distances, axis=1)
        symbols = self.SYMBOL_VALUES[nearest_indices]
        
        return symbols
    
    def symbols_to_bits(self, symbols: np.ndarray) -> np.ndarray:
        """
        将符号值转换为比特
        
        Args:
            symbols: 符号值数组 (-3, -1, 1, 3)
            
        Returns:
            比特数组 (每个符号产生 2 比特)
        """
        bits = []
        for sym in symbols:
            # 找到最接近的符号索引
            idx = np.argmin(np.abs(sym - self.SYMBOL_VALUES))
            bits.extend(self.SYMBOL_BITS[idx])
        return np.array(bits, dtype=np.uint8)
    
    def symbols_to_bytes(self, symbols: np.ndarray) -> bytes:
        """
        将符号值转换为字节
        
        Args:
            symbols: 符号值数组 (-3, -1, 1, 3)
            
        Returns:
            解码后的字节数据
        """
        bits = self.symbols_to_bits(symbols)
        
        # 确保比特数是 8 的倍数
        num_bytes = len(bits) // 8
        bits = bits[:num_bytes * 8]
        
        # 比特转字节
        byte_data = bytearray()
        for i in range(0, len(bits), 8):
            byte_val = 0
            for j in range(8):
                byte_val = (byte_val << 1) | bits[i + j]
            byte_data.append(byte_val)
        
        return bytes(byte_data)
    
    def demodulate(self, iq_samples: np.ndarray) -> Tuple[np.ndarray, bytes]:
        """
        完整解调流程
        
        Args:
            iq_samples: 复数 IQ 样本数组
            
        Returns:
            (符号值数组, 解码字节)
        """
        if len(iq_samples) < self.config.samples_per_symbol * 2:
            return np.array([]), b''
        
        # 1. FM 解调
        freq_estimate = self.fm_demodulate(iq_samples)
        
        # 2. RRC 匹配滤波
        filtered = self.apply_rrc_filter(freq_estimate)
        
        # 3. 时钟恢复
        _, sample_values = self.clock_recovery_gardner(filtered)
        
        # 4. 符号判决
        symbols = self.symbol_decision(sample_values)
        
        # 5. 转换为字节
        decoded_bytes = self.symbols_to_bytes(symbols)
        
        return symbols, decoded_bytes


# 便捷函数
def create_demodulator(sample_rate: int = 2_000_000, 
                       symbol_rate: int = 250_000) -> Demodulator:
    """创建解调器实例"""
    config = DemodulatorConfig(
        sample_rate=sample_rate,
        symbol_rate=symbol_rate
    )
    return Demodulator(config)
