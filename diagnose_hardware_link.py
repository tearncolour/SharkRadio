#!/usr/bin/env python3
"""
双机硬件链路诊断脚本
无需前端，直接驱动硬件测试 RF 链路
"""
import time
import sys
import threading
import numpy as np

# Add backend to path
sys.path.append('backend')

try:
    import iio
    import adi
except ImportError:
    print("错误: 需要安装 pyadi-iio 库 (pip install pyadi-iio)")
    sys.exit(1)

from sdr.signal_generator import generate_signal
from sdr.demodulator import Demodulator, DemodulatorConfig
from protocol.packet_parser import PacketParser

def get_connected_uris():
    """扫描连接的 Pluto"""
    uris = []
    try:
        ctxs = iio.scan_contexts()
        print(f"DEBUG: Scan result: {ctxs}")
        if isinstance(ctxs, dict):
            for uri, desc in ctxs.items():
                if 'PlutoSDR' in desc or 'ip:' in uri or 'usb:' in uri:
                    uris.append(uri)
        elif isinstance(ctxs, set) or isinstance(ctxs, list):
             for item in ctxs:
                # If item is string (URI)
                if isinstance(item, str):
                    if 'ip:' in item or 'usb:' in item:
                        uris.append(item)
                # If item handles object
                elif hasattr(item, 'uri'):
                     if 'PlutoSDR' in getattr(item, 'description', '') or 'ip:' in item.uri or 'usb:' in item.uri:
                        uris.append(item.uri)
    except Exception as e:
        print(f"Scan error: {e}")

    # Fallback / Common defaults if scan fails or returns nothing
    if not uris:
        # Check default IP
        try:
           ctx = iio.Context("ip:192.168.2.1")
           if 'PlutoSDR' in ctx.name:
               uris.append("ip:192.168.2.1")
        except: pass
        
    return uris

def run_rx(uri, duration=10, stop_event=None):
    """RX 接收线程"""
    print(f"[{uri}] RX: 连接中...")
    sdr = adi.Pluto(uri)
    sdr.rx_lo = 433200000
    sdr.sample_rate = 2000000
    sdr.rx_rf_bandwidth = 1000000
    sdr.rx_buffer_size = 16384
    sdr.gain_control_mode_chan0 = "manual"
    sdr.rx_hardwaregain_chan0 = 50.0 # 50dB 增益
    
    # 预热
    for _ in range(10): sdr.rx()
    
    print(f"[{uri}] RX: 开始接收 (433.2 MHz, Gain 50dB)...")
    
    demod_config = DemodulatorConfig.from_signal_type('red_broadcast', sample_rate=2000000)
    demod = Demodulator(demod_config)
    parser = PacketParser()
    
    valid_packets = 0
    total_bytes = 0
    max_rssi = -100
    
    start_time = time.time()
    while time.time() - start_time < duration:
        if stop_event and stop_event.is_set():
            break
            
        try:
            samples = sdr.rx()
            
            # 计算 RSSI (粗略)
            # Pluto full scale is approx 0 dBm? No, ADC full scale. 
            # Let's just look at amplitude.
            amp = np.mean(np.abs(samples))
            rssi = 20 * np.log10(amp + 1e-12)
            if rssi > max_rssi: max_rssi = rssi
            
            # 解调
            symbols, decoded_bytes = demod.demodulate(samples)
            total_bytes += len(decoded_bytes)
            
            # Print stats for first few buffers
            if total_bytes < 5000: # Only early debugging
                 # Analyze symbols
                 if len(symbols) > 0:
                     print(f"[{uri}] DEBUG Symbols: Min={np.min(symbols):.2f}, Max={np.max(symbols):.2f}, Mean={np.mean(symbols):.2f}")
                     uniq, counts = np.unique(np.round(symbols), return_counts=True)
                     print(f"[{uri}] DEBUG Symbol Dist: {dict(zip(uniq, counts))}")
                 # Analyze bytes
                 if len(decoded_bytes) > 0:
                     hex_bytes = bytes(decoded_bytes[:20]).hex().upper()
                     print(f"[{uri}] DEBUG Raw Bytes: {hex_bytes}...")
                     
                     # Check for Preamble pattern E4 (11100100)
                     e4_count = decoded_bytes.count(0xE4)
                     a5_count = decoded_bytes.count(0xA5)
                     if e4_count > 0 or a5_count > 0:
                         print(f"[{uri}] FOUND E4={e4_count}, A5={a5_count}")
            
            # 解析
            if decoded_bytes:
                packets = parser.feed_bytes(decoded_bytes)
                if packets:
                    valid_packets += len(packets)
                    print(f"[{uri}] ★ 收到 {len(packets)} 个数据包! 最后: {packets[-1].hex_string[:20]}...")
                    
        except Exception as e:
            print(f"[{uri}] RX Error: {e}")
            break
            
    print(f"[{uri}] RX 结束:")
    print(f"  - 最大信号强度 (dBFS): {max_rssi:.2f}")
    if max_rssi < -50:
        print("    ⚠️ 信号非常弱 (<-50 dBFS)，可能未接收到 TX 信号")
    else:
        print("    ✓ 信号强度良好")
        
    print(f"  - 解码字节数: {total_bytes}")
    print(f"  - 有效数据包: {valid_packets}")
    
    # 释放资源
    del sdr

def run_tx(uri, duration=10, stop_event=None):
    """TX 发射线程"""
    print(f"[{uri}] TX: 连接中...")
    sdr = adi.Pluto(uri)
    sdr.tx_lo = 433200000
    sdr.sample_rate = 2000000
    sdr.tx_rf_bandwidth = 540000
    sdr.tx_cyclic_buffer = True
    sdr.tx_hardwaregain_chan0 = -10 # -10dB 增益
    
    print(f"[{uri}] TX: 生成信号 (Red Broadcast, -10dB)...")
    # 生成信号 (使用修正后的 signal_generator)
    iq = generate_signal('red_broadcast', 'ABCD1234', 2000000)
    # 确保幅度安全
    iq = iq * 0.5 
    iq = (iq * 2**14).astype(np.complex64) # Scaling for Pluto? 
    # PyADI-IIO handles complex64 automatically if float?
    # Usually it expects complex64 (float) or complex128.
    # Let's keep it complex64 with range <= 1.0.
    iq = generate_signal('red_broadcast', 'ABCD1234', 2000000) * 0.8
    
    print(f"[{uri}] TX: 开始发射...")
    sdr.tx(iq)
    
    time.sleep(duration)
    
    print(f"[{uri}] TX: 停止发射")
    sdr.tx_destroy_buffer()
    del sdr

def main():
    print("=== RoboMaster 雷达 双机链路诊断 ===")
    uris = get_connected_uris()
    if len(uris) < 2:
        print(f"⚠️ 仅发现 {len(uris)} 个设备: {uris}")
        print("需要至少两个 Pluto SDR 才能进行可靠的链路测试。")
        print("尝试在单设备上进行 RX 测试 (请确保附近有其他 TX 源)...")
        if len(uris) == 1:
            run_rx(uris[0], duration=15)
        return

    # User requested back to original:
    tx_dev = uris[0]
    rx_dev = uris[1]
    
    print(f"\n--- 测试配置 ---")
    print(f"TX 设备: {tx_dev}")
    print(f"RX 设备: {rx_dev}")
    print(f"频率: 433.20 MHz")
    print(f"TX 功率: -10 dB")
    print("----------------\n")
    
    # 启动 RX
    stop_event = threading.Event()
    rx_thread = threading.Thread(target=run_rx, args=(rx_dev, 10, stop_event))
    rx_thread.start()
    
    # 等待 RX 准备好
    time.sleep(2)
    
    # 启动 TX
    tx_thread = threading.Thread(target=run_tx, args=(tx_dev, 6, stop_event))
    tx_thread.start()
    
    tx_thread.join()
    time.sleep(1) # Let RX finish processing
    stop_event.set()
    rx_thread.join()
    
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    main()
