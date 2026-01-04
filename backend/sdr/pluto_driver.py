"""
ADI PLUTO SDR 驱动模块
用于连接和控制 ADI PLUTO SDR 设备
"""

import numpy as np
from typing import Optional, Tuple, Callable
from dataclasses import dataclass
import threading
import time
import queue

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
    center_freq: float = 433.5e6  # 433.5 MHz 中心频率
    rf_bandwidth: int = 4_000_000  # 4 MHz RF 带宽
    
    # 接收增益
    rx_gain_mode: str = "manual"  # 增益模式: manual, fast_attack, slow_attack
    rx_gain: int = 50  # 接收增益 (dB)
    
    # 发射参数
    tx_freq: float = 433.5e6  # 发射频率
    tx_gain: int = -10  # 发射增益 (dB, 负值衰减)
    tx_rf_bandwidth: int = 540_000  # 发射 RF 带宽 (匹配 GRC 设置)
    
    # 缓冲区
    buffer_size: int = 16384  # IQ 样本缓冲区大小
    
    # 设备 URI
    uri: str = "ip:192.168.2.1"  # 默认 PLUTO IP 地址
    
    # 设备模式
    mode: str = "rx"  # rx, tx, txrx


class PlutoDriver:
    """
    ADI PLUTO SDR 驱动类
    """
    
    def __init__(self, config: Optional[PlutoConfig] = None):
        self.config = config or PlutoConfig()
        self._sdr: Optional[adi.Pluto] = None
        self._is_connected = False
        self._is_streaming = False
        self._stream_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # Status Monitoring
        self._last_rx_time = 0
        self._rx_overflow = False
        self._tx_underflow = False

    @property
    def is_connected(self) -> bool:
        return self._is_connected
    
    @property
    def is_streaming(self) -> bool:
        return self._is_streaming
    
    def connect(self, uri: Optional[str] = None) -> bool:
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
            
            # Reset monitor vars
            self._last_rx_time = 0
            self._rx_overflow = False
            self._tx_underflow = False
            
            return True
        except Exception as e:
            print(f"Failed to connect to PLUTO SDR: {e}")
            self._is_connected = False
            return False

    def disconnect(self):
        if self._is_streaming:
            self.stop_streaming()
        
        if self._sdr:
            del self._sdr
            self._sdr = None
        
        self._is_connected = False
        print("PLUTO SDR disconnected")

    def _configure_rx(self):
        """配置接收参数"""
        if not self._sdr: return
        
        try:
            self._sdr.rx_lo = int(self.config.center_freq)
            self._sdr.sample_rate = int(self.config.sample_rate)
            self._sdr.rx_rf_bandwidth = int(self.config.rf_bandwidth)
            self._sdr.rx_buffer_size = int(self.config.buffer_size)
            self._sdr.gain_control_mode_chan0 = self.config.rx_gain_mode
            if self.config.rx_gain_mode == 'manual':
                self._sdr.rx_hardwaregain_chan0 = int(self.config.rx_gain)
                
            print(f"RX configured: {self.config.sample_rate/1e6} MHz sample rate, {self.config.center_freq/1e6} MHz center freq")
        except Exception as e:
            print(f"Error configuration RX: {e}")

    def set_center_frequency(self, freq: float):
        self.config.center_freq = freq
        if self._sdr:
            self._sdr.rx_lo = int(freq)
            print(f"Center frequency set to {freq/1e6:.3f} MHz")

    def set_gain(self, gain: int):
        self.config.rx_gain = gain
        if self._sdr:
            self._sdr.rx_hardwaregain_chan0 = int(gain)
            print(f"RX gain set to {gain} dB")

    def set_tx_frequency(self, freq: float):
        self.config.tx_freq = freq
        if self._sdr:
            self._sdr.tx_lo = int(freq)
            print(f"TX frequency set to {freq/1e6:.3f} MHz")

    def set_tx_gain(self, gain: int):
        """设置 TX 增益 (dB)
        
        Pluto SDR TX 增益范围: -89.75 dB 到 0 dB (衰减模式)
        正值会被约束到 0 dB
        """
        # Pluto SDR TX gain 范围约束
        MIN_GAIN = -89
        MAX_GAIN = 0
        
        constrained_gain = max(MIN_GAIN, min(MAX_GAIN, gain))
        if constrained_gain != gain:
            print(f"Warning: TX gain {gain} dB out of range [{MIN_GAIN}, {MAX_GAIN}], using {constrained_gain} dB")
        
        self.config.tx_gain = constrained_gain
        if self._sdr:
            self._sdr.tx_hardwaregain_chan0 = int(constrained_gain)
            print(f"TX gain set to {constrained_gain} dB")

    def set_tx_rf_bandwidth(self, bandwidth: int):
        """设置 TX RF 带宽 (Hz)"""
        # Pluto SDR 最小 RF 带宽约 200kHz，最大约 20MHz
        MIN_BW = 200_000
        MAX_BW = 20_000_000
        
        # 约束带宽在有效范围内
        constrained_bw = max(MIN_BW, min(MAX_BW, bandwidth))
        if constrained_bw != bandwidth:
            print(f"Warning: TX RF bandwidth {bandwidth/1e6:.3f} MHz out of range, using {constrained_bw/1e6:.3f} MHz")
        
        self.config.tx_rf_bandwidth = constrained_bw
        if self._sdr:
            try:
                self._sdr.tx_rf_bandwidth = int(constrained_bw)
                print(f"TX RF bandwidth set to {constrained_bw/1e6:.3f} MHz")
            except Exception as e:
                print(f"Error setting TX RF bandwidth: {e}")

    def configure_tx(self):
        """配置发射参数 (Lazy init when needed)"""
        if not self._sdr: return
        try:
            self._sdr.tx_lo = int(self.config.tx_freq)
            self._sdr.tx_cyclic_buffer = True # Default to cyclic for continuous transmission
            self._sdr.tx_hardwaregain_chan0 = int(self.config.tx_gain)
            self._sdr.tx_rf_bandwidth = int(self.config.tx_rf_bandwidth)
            print(f"TX configured: {self.config.tx_freq/1e6} MHz, {self.config.tx_gain} dB gain")
        except Exception as e:
            print(f"Error configuring TX: {e}")

    def enable_tx(self):
        """Enable TX (configure if needed)"""
        self.configure_tx()

    def disable_tx(self):
        """Disable TX"""
        self.stop_transmission()

    def transmit_samples(self, samples: np.ndarray):
        if not self._sdr: return
        
        try:
            # STOP previous TX first to allow reconfiguration/re-creation of buffer
            self.stop_transmission()

            # Ensure TX is configured
            self.configure_tx()
            
            # Scale samples for AD9361 DAC (expects values around 2^14 range, not 0-1)
            # Signal Generator creates 0.9 max amplitude.
            # We scale by 2**14 (16384) to drive DAC.
            samples_scaled = samples * (2**14)
            self._sdr.tx(samples_scaled)
            print("TX enabled")
        except Exception as e:
            print(f"Error during transmission: {e}")
            self._tx_underflow = True

    def stop_transmission(self):
        if not self._sdr: return
        try:
            self._sdr.tx_destroy_buffer()
            print("TX buffer destroyed")
        except:
            pass

    def receive_samples(self) -> Optional[np.ndarray]:
        if not self._is_connected or self._sdr is None:
            return None
            
        try:
            now = time.time()
            expected_duration = self.config.buffer_size / self.config.sample_rate
            
            # Basic Overflow Detection
            # 使用较宽松的阈值，考虑解调处理时间
            if self._last_rx_time > 0 and (now - self._last_rx_time) > (expected_duration * 3.0):
                self._rx_overflow = True
            else:
                self._rx_overflow = False
            
            samples = self._sdr.rx()
            
            self._last_rx_time = time.time()
            return np.array(samples, dtype=np.complex64)
            
        except Exception as e:
            # print(f"Error receiving samples: {e}")
            return None

    def start_streaming(self, callback: Callable[[np.ndarray], None]):
        if self._is_streaming: return
        
        self._is_streaming = True
        self._stop_event.clear()
        
        def stream_loop():
            print("Streaming started")
            while not self._stop_event.is_set():
                samples = self.receive_samples()
                if samples is not None and len(samples) > 0:
                    try:
                        callback(samples)
                    except Exception as e:
                        print(f"Callback error: {e}")
                # else: time.sleep(0.001) # Avoid tight loop if no samples? receive_samples blocks usually.
            print("Streaming stopped")
            
        self._stream_thread = threading.Thread(target=stream_loop)
        self._stream_thread.daemon = True
        self._stream_thread.start()

    def stop_streaming(self):
        if not self._is_streaming: return
        self._stop_event.set()
        if self._stream_thread:
            self._stream_thread.join(timeout=1.0)
        self._is_streaming = False

    def get_status(self) -> dict:
        return {
            "connected": self._is_connected,
            "streaming": self._is_streaming,
            "sample_rate": self.config.sample_rate,
            "center_freq": self.config.center_freq,
            "rf_bandwidth": self.config.rf_bandwidth,
            "rx_gain": self.config.rx_gain,
            "buffer_size": self.config.buffer_size,
            "uri": self.config.uri,
            "overflow": self._rx_overflow,
            "underflow": self._tx_underflow
        }
