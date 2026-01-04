"""
Signal Processor Module - GNU Radio Implementation
"""

import numpy as np
from gnuradio import fft
from gnuradio.fft import window
import math

class SignalProcessor:
    """信号处理器: 使用 GNU Radio FFT"""
    
    def __init__(self, sample_rate: int, fft_size: int = 1024):
        self.sample_rate = sample_rate
        self.fft_size = fft_size
        
        # Windows
        self.win = window.hanning(fft_size)
    
    def compute_spectrum(self, samples: np.ndarray, center_freq: float = 0.0):
        """
        计算频谱 (PSD)
        """
        if len(samples) < self.fft_size:
            if len(samples) == 0:
                pass # return empty
            pad_len = self.fft_size - len(samples)
            samples = np.pad(samples, (0, pad_len), 'constant')
        else:
            samples = samples[-self.fft_size:]
            
        # 使用 numpy，等效于 GR 的 FFT 模块逻辑
        windowed = samples * self.win
        fft_result = np.fft.fft(windowed) / self.fft_size # Normalize
        fft_result = np.fft.fftshift(fft_result)
        
        power = np.abs(fft_result)**2
        power_db = 10 * np.log10(power + 1e-20)
        
        # 计算相对频率并加上中心频率偏移
        freqs_relative = np.fft.fftshift(np.fft.fftfreq(self.fft_size, 1.0/self.sample_rate))
        freqs = freqs_relative + center_freq
        
        # 兼容 SpectrumData 接口
        # 为了避免循环引用，我们返回简单的对象或 dict
        class SpectrumDataStub:
            def __init__(self, f, p):
                self.frequencies = f.tolist()
                self.power_db = p.tolist()
                
        return SpectrumDataStub(freqs, power_db)
