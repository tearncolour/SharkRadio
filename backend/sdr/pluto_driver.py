"""
ADI PLUTO SDR 驱动模块
用于连接和控制 ADI PLUTO SDR 设备
"""

import numpy as np
from typing import Optional, Tuple, Callable
from dataclasses import dataclass
import threading
import time

try:
    import adi
except ImportError:
    adi = None
    print("Warning: PyADI-IIO not installed. SDR functionality will be limited.")


@dataclass
class PlutoConfig:
    """PLUTO SDR 配置参数"""
    # 基本参数
    sample_rate: int = 2_000_000  # 2 MHz 采样率
    center_freq: float = 433.5e6  # 433.5 MHz 中心频率 (红蓝方之间)
    rf_bandwidth: int = 4_000_000  # 4 MHz RF 带宽
    
    # 接收增益
    rx_gain_mode: str = "manual"  # 增益模式: manual, fast_attack, slow_attack
    rx_gain: int = 50  # 接收增益 (dB)
    
    # 发射参数
    tx_freq: float = 433.5e6  # 发射频率
    tx_gain: int = -10  # 发射增益 (dB, 负值衰减)
    tx_rf_bandwidth: int = 4_000_000  # 发射 RF 带宽
    
    # 缓冲区
    buffer_size: int = 16384  # IQ 样本缓冲区大小
    
    # 设备 URI
    uri: str = "ip:192.168.2.1"  # 默认 PLUTO IP 地址
    
    # 设备模式
    mode: str = "rx"  # rx, tx, txrx


class PlutoDriver:
    """
    ADI PLUTO SDR 驱动类
    
    功能:
    - 连接/断开 PLUTO SDR
    - 配置采样率、中心频率、增益等参数
    - 实时采集 IQ 数据
    - 支持回调函数进行流式处理
    """
    
    def __init__(self, config: Optional[PlutoConfig] = None):
        self.config = config or PlutoConfig()
        self._sdr: Optional[adi.Pluto] = None
        self._is_connected = False
        self._is_streaming = False
        self._stream_thread: Optional[threading.Thread] = None
        self._stream_callback: Optional[Callable[[np.ndarray], None]] = None
        self._stop_event = threading.Event()
        
    @property
    def is_connected(self) -> bool:
        """检查是否已连接到 SDR"""
        return self._is_connected
    
    @property
    def is_streaming(self) -> bool:
        """检查是否正在流式传输"""
        return self._is_streaming
    
    def connect(self, uri: Optional[str] = None) -> bool:
        """
        连接到 PLUTO SDR
        
        Args:
            uri: 设备 URI (可选，默认使用配置中的 URI)
            
        Returns:
            连接是否成功
        """
        if adi is None:
            print("Error: PyADI-IIO not available")
            return False
            
        try:
            device_uri = uri or self.config.uri
            print(f"Connecting to PLUTO SDR at {device_uri}...")
            
            self._sdr = adi.Pluto(uri=device_uri)
            
            # 配置接收参数
            self._configure_rx()
            
            self._is_connected = True
            print("PLUTO SDR connected successfully!")
            return True
            
        except Exception as e:
            print(f"Failed to connect to PLUTO SDR: {e}")
            self._is_connected = False
            return False
    
    def disconnect(self):
        """断开与 SDR 的连接"""
        self.stop_streaming()
        
        if self._sdr is not None:
            self._sdr = None
            
        self._is_connected = False
        print("PLUTO SDR disconnected")
    
    def _configure_rx(self):
        """配置接收参数"""
        if self._sdr is None:
            return
            
        # 设置采样率
        self._sdr.sample_rate = self.config.sample_rate
        
        # 设置中心频率
        self._sdr.rx_lo = int(self.config.center_freq)
        
        # 设置 RF 带宽
        self._sdr.rx_rf_bandwidth = self.config.rf_bandwidth
        
        # 设置增益模式和增益值
        self._sdr.gain_control_mode_chan0 = self.config.rx_gain_mode
        if self.config.rx_gain_mode == "manual":
            self._sdr.rx_hardwaregain_chan0 = self.config.rx_gain
        
        # 设置缓冲区大小
        self._sdr.rx_buffer_size = self.config.buffer_size
        
        print(f"RX configured: {self.config.sample_rate/1e6:.1f} MHz sample rate, "
              f"{self.config.center_freq/1e6:.3f} MHz center freq")
    
    def set_center_frequency(self, freq_hz: float):
        """
        设置中心频率
        
        Args:
            freq_hz: 频率 (Hz)
        """
        self.config.center_freq = freq_hz
        if self._sdr is not None:
            self._sdr.rx_lo = int(freq_hz)
            print(f"Center frequency set to {freq_hz/1e6:.3f} MHz")
    
    def set_gain(self, gain_db: int):
        """
        设置接收增益
        
        Args:
            gain_db: 增益值 (dB)
        """
        self.config.rx_gain = gain_db
        if self._sdr is not None and self.config.rx_gain_mode == "manual":
            self._sdr.rx_hardwaregain_chan0 = gain_db
            print(f"RX gain set to {gain_db} dB")
    
    # ============ TX (发射) 功能 ============
    
    def _configure_tx(self):
        """配置发射参数"""
        if self._sdr is None:
            return
        
        try:
            # 设置发射频率
            self._sdr.tx_lo = int(self.config.tx_freq)
            
            # 设置发射 RF 带宽
            self._sdr.tx_rf_bandwidth = self.config.tx_rf_bandwidth
            
            # 设置发射增益 (衰减)
            self._sdr.tx_hardwaregain_chan0 = self.config.tx_gain
            
            # 设置 TX 缓冲区
            self._sdr.tx_buffer_size = self.config.buffer_size
            
            print(f"TX configured: {self.config.tx_freq/1e6:.3f} MHz, {self.config.tx_gain} dB gain")
        except Exception as e:
            print(f"TX configuration error: {e}")
    
    def set_tx_frequency(self, freq_hz: float):
        """
        设置发射频率
        
        Args:
            freq_hz: 频率 (Hz)
        """
        self.config.tx_freq = freq_hz
        if self._sdr is not None:
            try:
                self._sdr.tx_lo = int(freq_hz)
                print(f"TX frequency set to {freq_hz/1e6:.3f} MHz")
            except Exception as e:
                print(f"Error setting TX frequency: {e}")
    
    def set_tx_gain(self, gain_db: int):
        """
        设置发射增益
        
        Args:
            gain_db: 增益值 (dB, 通常为负值表示衰减)
        """
        self.config.tx_gain = gain_db
        if self._sdr is not None:
            try:
                self._sdr.tx_hardwaregain_chan0 = gain_db
                print(f"TX gain set to {gain_db} dB")
            except Exception as e:
                print(f"Error setting TX gain: {e}")
    
    def transmit_samples(self, samples: np.ndarray) -> bool:
        """
        发送 IQ 样本
        
        Args:
            samples: 复数 IQ 样本数组
            
        Returns:
            发送是否成功
        """
        if not self._is_connected or self._sdr is None:
            return False
        
        try:
            self._sdr.tx(samples)
            return True
        except Exception as e:
            print(f"Error transmitting samples: {e}")
            return False
    
    def enable_tx(self):
        """启用发射功能"""
        if self._sdr is not None:
            self._configure_tx()
            self.config.mode = "txrx" if "rx" in self.config.mode else "tx"
            print("TX enabled")
    
    def disable_tx(self):
        """禁用发射功能"""
        if self._sdr is not None:
            try:
                # 发送零样本以停止发射
                self._sdr.tx_destroy_buffer()
            except:
                pass
            self.config.mode = "rx" if "rx" in self.config.mode else ""
            print("TX disabled")

    
    def receive_samples(self) -> Optional[np.ndarray]:
        """
        接收一批 IQ 样本
        
        Returns:
            复数 IQ 样本数组，如果失败则返回 None
        """
        if not self._is_connected or self._sdr is None:
            return None
            
        try:
            # 接收 IQ 数据
            samples = self._sdr.rx()
            return np.array(samples, dtype=np.complex64)
            
        except Exception as e:
            print(f"Error receiving samples: {e}")
            return None
    
    def start_streaming(self, callback: Callable[[np.ndarray], None]):
        """
        开始流式接收数据
        
        Args:
            callback: 每次接收到数据时调用的回调函数
        """
        if self._is_streaming:
            print("Already streaming")
            return
            
        if not self._is_connected:
            print("Not connected to SDR")
            return
            
        self._stream_callback = callback
        self._stop_event.clear()
        self._stream_thread = threading.Thread(target=self._stream_loop, daemon=True)
        self._stream_thread.start()
        self._is_streaming = True
        print("Streaming started")
    
    def stop_streaming(self):
        """停止流式接收"""
        if not self._is_streaming:
            return
            
        self._stop_event.set()
        
        if self._stream_thread is not None:
            self._stream_thread.join(timeout=2.0)
            self._stream_thread = None
            
        self._is_streaming = False
        print("Streaming stopped")
    
    def _stream_loop(self):
        """流式接收循环（在独立线程中运行）"""
        while not self._stop_event.is_set():
            samples = self.receive_samples()
            
            if samples is not None and self._stream_callback is not None:
                try:
                    self._stream_callback(samples)
                except Exception as e:
                    print(f"Error in stream callback: {e}")
            
            # 小延迟以避免 CPU 过载
            time.sleep(0.001)
    
    def get_status(self) -> dict:
        """
        获取 SDR 状态信息
        
        Returns:
            状态字典
        """
        return {
            "connected": self._is_connected,
            "streaming": self._is_streaming,
            "sample_rate": self.config.sample_rate,
            "center_freq": self.config.center_freq,
            "rf_bandwidth": self.config.rf_bandwidth,
            "rx_gain": self.config.rx_gain,
            "buffer_size": self.config.buffer_size,
            "uri": self.config.uri
        }


# 模拟模式用于测试（当没有实际 SDR 时）
class PlutoDriverSimulated(PlutoDriver):
    """模拟 PLUTO SDR 驱动，用于测试"""
    
    def connect(self, uri: Optional[str] = None) -> bool:
        print("Connecting to SIMULATED PLUTO SDR...")
        self._is_connected = True
        print("Simulated PLUTO SDR connected!")
        return True
    
    def receive_samples(self) -> Optional[np.ndarray]:
        if not self._is_connected:
            return None
            
        # 生成模拟的 433 MHz 信号
        t = np.arange(self.config.buffer_size) / self.config.sample_rate
        
        # 模拟红方广播信号 (433.2 MHz)
        f_offset_red = 433.2e6 - self.config.center_freq
        signal_red = 0.1 * np.exp(2j * np.pi * f_offset_red * t)
        
        # 模拟蓝方广播信号 (433.92 MHz)
        f_offset_blue = 433.92e6 - self.config.center_freq
        signal_blue = 0.1 * np.exp(2j * np.pi * f_offset_blue * t)
        
        # 添加噪声
        noise = 0.01 * (np.random.randn(self.config.buffer_size) + 
                        1j * np.random.randn(self.config.buffer_size))
        
        return (signal_red + signal_blue + noise).astype(np.complex64)
