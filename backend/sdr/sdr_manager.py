"""
SDR 设备管理器
用于枚举、选择和管理多个 PLUTO SDR 设备
"""

import threading
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
import iio
import numpy as np

from .pluto_driver import PlutoDriver, PlutoConfig


@dataclass
class SDRDeviceInfo:
    """SDR 设备信息"""
    id: str  # 唯一标识符 (如 URI)
    name: str  # 设备名称
    uri: str  # 连接 URI
    serial: str = ""  # 序列号
    mac: str = ""     # MAC地址
    product: str = ""  # 产品名称
    is_available: bool = True  # 是否可用


@dataclass
class SDRInstance:
    """SDR 设备实例"""
    device_info: SDRDeviceInfo
    driver: PlutoDriver
    mode: str = "rx"  # rx, tx, txrx
    is_active: bool = False
    is_streaming: bool = False


class SDRManager:
    """
    SDR 设备管理器
    
    功能:
    - 扫描可用的 IIO/PLUTO SDR 设备
    - 管理多个 SDR 实例
    - 支持设备选择和配置
    """
    
    def __init__(self):
        self._devices: Dict[str, SDRInstance] = {}
        self._active_device_id: Optional[str] = None
        self._lock = threading.Lock()
    
    def _get_mac_from_arp(self, ip_addr: str) -> str:
        """从 ARP 表获取 MAC 地址"""
        try:
            # 如果是 hostname，尝试解析
            if any(c.isalpha() for c in ip_addr):
                import socket
                try:
                    ip_addr = socket.gethostbyname(ip_addr)
                except:
                    pass
            
            with open('/proc/net/arp', 'r') as f:
                lines = f.readlines()[1:] # Skip header
                for line in lines:
                    parts = line.split()
                    if len(parts) >= 4 and parts[0] == ip_addr:
                        return parts[3]
        except Exception:
            pass
        return ""

    def scan_devices(self) -> List[SDRDeviceInfo]:
        """
        扫描所有可用的 IIO 设备
        
        Returns:
            设备信息列表
        """
        devices = []
        
        try:
            # 扫描本地 USB 设备
            ctx_info = iio.scan_contexts()
            
            for uri, description in ctx_info.items():
                # 如果设备已连接及管理中，直接使用现有信息
                if uri in self._devices:
                    devices.append(self._devices[uri].device_info)
                    continue

                # 尝试获取更多设备信息
                try:
                    ctx = iio.Context(uri)
                    
                    # 检查是否是 PLUTO 设备
                    is_pluto = False
                    for dev in ctx.devices:
                        if 'pluto' in dev.name.lower() or 'ad936' in dev.name.lower():
                            is_pluto = True
                            break
                    
                    if is_pluto or 'pluto' in description.lower() or 'pluto' in uri.lower():
                        # 尝试获取序列号
                        serial = getattr(ctx, 'serial', '') or ''
                        if not serial:
                            serial = ctx.attrs.get('hw_serial', '')
                        if not serial:
                            serial = ctx.attrs.get('serial', '')
                            
                        # 尝试获取 MAC
                        mac = ""
                        if 'ip:' in uri:
                            ip_part = uri.replace('ip:', '')
                            mac = self._get_mac_from_arp(ip_part)

                        device_info = SDRDeviceInfo(
                            id=uri,
                            name=ctx.name or f"PLUTO SDR ({uri})",
                            uri=uri,
                            serial=serial,
                            mac=mac,
                            product="ADI PLUTO SDR",
                            is_available=True
                        )
                        devices.append(device_info)
                        
                    # Explicit context cleanup
                    del ctx
                        
                except Exception as e:
                    print(f"无法连接设备 {uri}: {e}")
                    devices.append(SDRDeviceInfo(
                        id=uri,
                        name=f"未知设备 ({uri})",
                        uri=uri,
                        is_available=False
                    ))
            
            # 如果没有扫描到设备，添加默认 IP 地址
            if not devices:
                default_uris = [
                    "ip:192.168.2.1",
                    "ip:192.168.3.1",
                ]
                for uri in default_uris:
                    try:
                        ctx = iio.Context(uri)
                        
                        serial = getattr(ctx, 'serial', '') or ''
                        if not serial:
                            serial = ctx.attrs.get('hw_serial', '')
                            
                        mac = self._get_mac_from_arp(uri.replace('ip:', ''))
                        
                        devices.append(SDRDeviceInfo(
                            id=uri,
                            name=f"PLUTO SDR ({uri})",
                            uri=uri,
                            serial=serial,
                            mac=mac,
                            product="ADI PLUTO SDR",
                            is_available=True
                        ))
                    except:
                        pass
                        
        except Exception as e:
            print(f"扫描设备时出错: {e}")
        
        return devices
    
    def get_device(self, device_id: str) -> Optional[PlutoDriver]:
        """
        获取指定设备的驱动实例
        
        Args:
            device_id: 设备 ID (URI)
            
        Returns:
            PlutoDriver 实例，如果不存在则返回 None
        """
        with self._lock:
            instance = self._devices.get(device_id)
            return instance.driver if instance else None
    
    def connect_device(self, device_id: str, config: Optional[PlutoConfig] = None) -> bool:
        """
        连接到指定设备
        
        Args:
            device_id: 设备 ID (URI)
            config: 可选的配置参数
            
        Returns:
            连接是否成功
        """
        with self._lock:
            # 如果已存在，先断开
            if device_id in self._devices:
                self._devices[device_id].driver.disconnect()
            
            # 创建配置
            if config is None:
                config = PlutoConfig(uri=device_id)
            else:
                config.uri = device_id
            
            # 创建驱动并连接
            driver = PlutoDriver(config)
            if driver.connect(device_id):
                self._devices[device_id] = SDRInstance(
                    device_info=SDRDeviceInfo(
                        id=device_id,
                        name=f"PLUTO SDR ({device_id})",
                        uri=device_id,
                        mac=self._get_mac_from_arp(device_id.replace('ip:', '')) if 'ip:' in device_id else "",
                        product="ADI PLUTO SDR"
                    ),
                    driver=driver,
                    is_active=True
                )
                return True
            
            return False
    
    def disconnect_device(self, device_id: str):
        """
        断开指定设备
        
        Args:
            device_id: 设备 ID
        """
        with self._lock:
            if device_id in self._devices:
                self._devices[device_id].driver.disconnect()
                del self._devices[device_id]
                
                if self._active_device_id == device_id:
                    self._active_device_id = None
    
    def set_active_device(self, device_id: str) -> bool:
        """
        设置当前活动设备
        
        Args:
            device_id: 设备 ID
            
        Returns:
            是否成功
        """
        with self._lock:
            if device_id in self._devices:
                self._active_device_id = device_id
                return True
            return False
    
    def get_active_device(self) -> Optional[PlutoDriver]:
        """
        获取当前活动设备
        
        Returns:
            活动设备的驱动实例
        """
        with self._lock:
            if self._active_device_id and self._active_device_id in self._devices:
                return self._devices[self._active_device_id].driver
            return None
    
    def get_connected_devices(self) -> List[SDRDeviceInfo]:
        """
        获取所有已连接设备的信息
        
        Returns:
            已连接设备列表
        """
        with self._lock:
            return [inst.device_info for inst in self._devices.values()]
    
    def configure_device(self, device_id: str, 
                         rx_config: Optional[dict] = None,
                         tx_config: Optional[dict] = None) -> bool:
        """
        配置指定设备
        
        Args:
            device_id: 设备 ID
            rx_config: RX 配置参数
            tx_config: TX 配置参数
            
        Returns:
            配置是否成功
        """
        with self._lock:
            if device_id not in self._devices:
                return False
            
            driver = self._devices[device_id].driver
            
            # 应用 RX 配置
            if rx_config:
                if 'center_freq' in rx_config:
                    driver.set_center_frequency(rx_config['center_freq'])
                if 'gain' in rx_config:
                    driver.set_gain(rx_config['gain'])
            
            # 应用 TX 配置 (需要 PlutoDriver 支持 TX)
            if tx_config:
                if hasattr(driver, 'set_tx_frequency') and 'center_freq' in tx_config:
                    driver.set_tx_frequency(tx_config['center_freq'])
                if hasattr(driver, 'set_tx_gain') and 'gain' in tx_config:
                    driver.set_tx_gain(tx_config['gain'])
            
            return True
    
    def start_tx_signal(self, device_id: str, signal_type: str, payload: Optional[str] = None) -> bool:
        """
        开始发射指定类型的信号
        
        Args:
            device_id: 设备 ID
            signal_type: 信号类型 (red_broadcast, blue_broadcast, jam_1, jam_2, jam_3)
            payload: 信号载荷 (可选, ASCII 字符串或 Hex)
            
        Returns:
            (是否成功启动, 预览频谱数据)
        """
        with self._lock:
            if device_id not in self._devices:
                return False
            
            # 这里简化实现：目前仅打印日志，实际需要生成对应波形并循环发送
            # 将来可以在这里启动一个后台线程持续发送 samples
            print(f"Starting TX signal '{signal_type}' on device {device_id} (Payload: {payload})")
            
            try:
                from sdr.signal_generator import generate_signal, get_signal_params
                
                # 获取信号参数
                params = get_signal_params(signal_type)
                target_freq = params.get('freq')
                target_bandwidth = params.get('bandwidth', 540000)  # 默认 540kHz
                target_power = params.get('power', -10)  # 默认 -10 dBm
                
                driver = self._devices[device_id].driver
                
                # 自动配置发射参数 (带详细错误处理)
                try:
                    if target_freq and hasattr(driver, 'set_tx_frequency'):
                        driver.set_tx_frequency(target_freq)
                except Exception as e:
                    print(f"Error setting TX frequency: {e}")
                    raise
                
                try:
                    if hasattr(driver, 'set_tx_gain'):
                        driver.set_tx_gain(target_power)
                except Exception as e:
                    print(f"Error setting TX gain: {e}")
                    raise
                
                try:
                    if hasattr(driver, 'set_tx_rf_bandwidth'):
                        driver.set_tx_rf_bandwidth(target_bandwidth)
                except Exception as e:
                    print(f"Error setting TX bandwidth: {e}")
                    raise
                
                try:
                    samples = generate_signal(signal_type, payload, self._devices[device_id].driver.config.sample_rate)
                except Exception as e:
                    print(f"Error generating signal: {e}")
                    raise
                
                try:
                    # 设置 cyclic buffer 以持续发送
                    self._devices[device_id].driver.transmit_samples(samples)
                    print(f"Transmitting {len(samples)} samples (Cyclic) at {target_freq/1e6:.2f} MHz")
                except Exception as e:
                    print(f"Error transmitting samples: {e}")
                    raise
                
                # Generate Packet Preview Spectrum
                # Use FFT with windowing for consistent dBFS scaling with RX spectrum
                
                # Use a reasonable segment for FFT
                fft_size = 2048
                preview_len = min(len(samples), fft_size * 8)  # Average over 8 segments
                preview_samples = samples[:preview_len]
                
                sample_rate = self._devices[device_id].driver.config.sample_rate
                
                # Average multiple FFTs for smoother spectrum
                num_segments = preview_len // fft_size
                if num_segments < 1:
                    num_segments = 1
                    fft_size = len(preview_samples)
                
                window = np.hamming(fft_size)
                window_sum = np.sum(window)
                
                avg_power = np.zeros(fft_size)
                for i in range(num_segments):
                    segment = preview_samples[i*fft_size : (i+1)*fft_size]
                    if len(segment) < fft_size:
                        continue
                    fft_vals = np.fft.fft(segment * window)
                    # Amplitude normalization for dBFS
                    magnitude = np.abs(fft_vals) / window_sum
                    avg_power += magnitude ** 2
                
                avg_power /= num_segments
                power_db = 10 * np.log10(avg_power + 1e-12)
                
                # Shift to center
                freqs = np.fft.fftfreq(fft_size, 1/sample_rate)
                freqs = np.fft.fftshift(freqs)
                power_db = np.fft.fftshift(power_db)
                
                # Downsample for UI
                step = max(1, len(freqs) // 256)
                preview_data = {
                    "frequencies": freqs[::step].tolist(), 
                    "power": power_db[::step].tolist(),
                    "center_freq": target_freq
                }
                
                return True, preview_data
                
            except Exception as e:
                print(f"Failed to start TX signal: {e}")
                return False, None
            
            return True, None

    def stop_tx_signal(self, device_id: str) -> bool:
        """停止信号发射"""
        with self._lock:
            if device_id not in self._devices:
                return False
            print(f"Stopping TX signal on device {device_id}")
            
            try:
                self._devices[device_id].driver.stop_transmission()
            except:
                pass
                
            return True

    def start_streaming(self, device_id: str, callback: Callable[[np.ndarray], None]) -> bool:
        """
        启动指定设备的数据流
        
        Args:
            device_id: 设备 ID
            callback: 数据处理回调函数
            
        Returns:
            是否成功
        """
        with self._lock:
            instance = self._devices.get(device_id)
            if not instance:
                return False
            
            if instance.is_streaming:
                return True
                
            try:
                if hasattr(instance.driver, 'start_streaming'):
                    instance.driver.start_streaming(callback)
                    instance.is_streaming = True
                    return True
            except Exception as e:
                print(f"启动流失败: {e}")
                return False
        return False

    def stop_streaming(self, device_id: str) -> bool:
        """
        停止指定设备的数据流
        
        Args:
            device_id: 设备 ID
            
        Returns:
            是否成功
        """
        with self._lock:
            instance = self._devices.get(device_id)
            if not instance:
                return False
            
            if not instance.is_streaming:
                return True
                
            try:
                if hasattr(instance.driver, 'stop_streaming'):
                    instance.driver.stop_streaming()
                    instance.is_streaming = False
                    return True
            except Exception as e:
                print(f"停止流失败: {e}")
                return False
        return False

    def disconnect_all(self):
        """断开所有设备"""
        with self._lock:
            for device_id in list(self._devices.keys()):
                try:
                    self._devices[device_id].driver.disconnect()
                except:
                    pass
            self._devices.clear()
            self._active_device_id = None


# 全局单例
_manager_instance: Optional[SDRManager] = None


def get_sdr_manager() -> SDRManager:
    """获取 SDR 管理器单例"""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = SDRManager()
    return _manager_instance
