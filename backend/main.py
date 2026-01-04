"""
RoboMaster Radar SDR Backend Main Entry
"""

import asyncio
import json
import threading
import time
import numpy as np
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import List, Dict, Any

from sdr.pluto_driver import PlutoDriver, PlutoConfig
from sdr.signal_processor import SignalProcessor
from sdr.sdr_manager import get_sdr_manager


# ============ WebSocket 管理器 ============
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                disconnected.append(connection)
        for conn in disconnected:
            self.disconnect(conn)
            
    async def send_json(self, websocket: WebSocket, data: Dict[str, Any]):
        try:
            await websocket.send_text(json.dumps(data, ensure_ascii=False))
        except:
            pass


manager = ConnectionManager()


# ============ SDR 系统 ============
class SDRSystem:
    def __init__(self):
        self.config = PlutoConfig(
            center_freq=433.5e6,
            sample_rate=2_000_000
        )
        self.driver = PlutoDriver(self.config)
        self.processor = SignalProcessor(sample_rate=self.config.sample_rate)
        self.running = False
        self.loop_ref = None
        
    def start(self, loop):
        if self.running:
            return
            
        self.loop_ref = loop
        print("Starting SDR System...")
        
        if not self.driver.connect():
            print("Trying simulation mode...")
            from sdr.pluto_driver import PlutoDriverSimulated
            self.driver = PlutoDriverSimulated(self.config)
            self.driver.connect()
            
        self.running = True
        self.driver.start_streaming(self._process_callback)
        print("SDR System started")

    def stop(self):
        self.running = False
        if self.driver:
            self.driver.stop_streaming()
            self.driver.disconnect()
        print("SDR System stopped")

    def _process_callback(self, samples: np.ndarray):
        if not self.running or not self.loop_ref:
            return
            
        try:
            # Spectrum
            spectrum = self.processor.compute_spectrum(samples)
            
            if manager.active_connections:
                data = {
                    "type": "spectrum",
                    "frequencies": spectrum.frequencies[::10],
                    "power": spectrum.power_db[::10]
                }
                asyncio.run_coroutine_threadsafe(
                    manager.broadcast(json.dumps(data)), 
                    self.loop_ref
                )
                
        except Exception as e:
            print(f"Processing error: {e}")


sdr_system = SDRSystem()



# ============ WebSocket 命令处理 ============
MAIN_LOOP = None

# 用于跟踪每个设备的解调工作线程和停止事件
_demod_workers: dict[str, dict] = {}

def create_stream_callback(device_id: str, signal_type: str = 'red_broadcast', rx_enabled: bool = True):
    """创建特定设备的数据流回调 (生产者-消费者模式)
    
    Args:
        device_id: 设备 ID
        signal_type: 信号类型 (red_broadcast, blue_jam_1, 等)
        rx_enabled: 是否启用 RX 解调 (仅发射时为 False)
    """
    from sdr.demodulator import Demodulator, DemodulatorConfig
    from protocol.packet_parser import PacketParser
    import queue
    import threading
    
    # 如果该设备已有 worker，先停止它
    if device_id in _demod_workers:
        old = _demod_workers[device_id]
        old['stop_event'].set()
        if old['thread'].is_alive():
            old['thread'].join(timeout=1.0)
        del _demod_workers[device_id]
    
    processor = SignalProcessor(sample_rate=2000000)  # 默认 2M
    
    # 根据信号类型创建解调器配置
    demod_config = DemodulatorConfig.from_signal_type(signal_type, sample_rate=2000000)
    demodulator = Demodulator(demod_config)
    packet_parser = PacketParser()
    
    # 生产者-消费者队列 (有限容量防止内存溢出)
    sample_queue = queue.Queue(maxsize=10)
    stop_event = threading.Event()
    
    def demod_worker():
        """解调工作线程 (消费者)"""
        # 如果 RX 未启用，直接消费队列但不处理
        if not rx_enabled:
            print(f"[DEBUG] RX disabled for {device_id}, demod worker will drain queue only")
            while not stop_event.is_set():
                try:
                    sample_queue.get(timeout=0.5)  # 只消费，不处理
                except queue.Empty:
                    pass
            return
            
        print(f"[DEBUG] Demod worker started for {device_id}")
        process_count = 0
        while not stop_event.is_set():
            try:
                # 从队列获取样本 (超时以便检查停止事件)
                samples, center_freq = sample_queue.get(timeout=0.5)
                process_count += 1
                
                # 解调 IQ 样本
                symbols, decoded_bytes = demodulator.demodulate(samples)
                
                # 每 50 次处理打印一次调试信息
                if process_count % 50 == 0:
                    print(f"[DEBUG] Processed {process_count} buffers, last decoded {len(decoded_bytes)} bytes, {len(symbols)} symbols")
                
                # 每 500 次检查是否有 SOF (0xA5) 和 Preamble (0xE4) 出现
                if process_count % 500 == 0:
                    sof_count = decoded_bytes.count(0xA5)
                    preamble_count = decoded_bytes.count(0xE4)
                    print(f"[DEBUG] SOF (0xA5) count: {sof_count}, Preamble (0xE4) count: {preamble_count} in {len(decoded_bytes)} bytes")
                
                # 解析数据包 (使用字节级 SOF 同步)
                if len(decoded_bytes) > 0:
                    packets = packet_parser.feed_bytes(decoded_bytes)
                    
                    if packets:
                        print(f"[DEBUG] Decoded {len(packets)} packets!")
                    
                    # 发送解码的数据包到前端
                    if not MAIN_LOOP:
                         print("[DEBUG] WARNING: MAIN_LOOP is None!")
                    if not manager.active_connections:
                         # 仅当确定连接时才打印警告，避免泛滥
                         # print("[DEBUG] WARNING: No active connections!")
                         pass

                    if MAIN_LOOP and manager.active_connections and packets:
                        for pkt in packets:
                            try:
                                packet_data = {
                                    "type": "packet",
                                    "device_id": device_id,
                                    "timestamp": pkt.timestamp,
                                    "hex": pkt.hex_string,
                                    "packet_type": pkt.packet_type,
                                    "is_valid": pkt.is_valid
                                }
                                json_str = json.dumps(packet_data)
                                # 限制打印频率或长度以免刷屏
                                if process_count % 10 == 0:
                                     print(f"[DEBUG] Broadcasting packet: {json_str[:50]}...")
                                
                                asyncio.run_coroutine_threadsafe(
                                    manager.broadcast(json_str), 
                                    MAIN_LOOP
                                )
                            except Exception as e:
                                print(f"[DEBUG] JSON serialize/broadcast error: {e}")
                    elif packets and not manager.active_connections:
                        print("[DEBUG] Packets dropped - no active WebSocket connections")
                
                sample_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Demod worker error: {e}")
                import traceback
                traceback.print_exc()
        print(f"[DEBUG] Demod worker stopped for {device_id}")
    
    # 启动解调工作线程
    worker_thread = threading.Thread(target=demod_worker, daemon=True)
    worker_thread.start()
    
    # 注册到全局字典，以便 stop_streaming 时能停止
    _demod_workers[device_id] = {
        'stop_event': stop_event,
        'thread': worker_thread,
        'queue': sample_queue
    }
    
    def callback(samples: np.ndarray):
        """采样回调 (生产者) - 保持轻量级"""
        if not MAIN_LOOP:
            return
        
        # 检查是否已停止
        if stop_event.is_set():
            return
            
        try:
            # 获取当前中心频率
            sdr_mgr = get_sdr_manager()
            driver = sdr_mgr.get_device(device_id)
            center_freq = 0.0
            
            if driver:
                center_freq = driver.config.center_freq
            
            # 1. 计算频谱 (FFT) - 轻量级处理，不阻塞
            spectrum = processor.compute_spectrum(samples, center_freq=center_freq)
            
            # 2. 将样本入队供解调线程处理 (非阻塞)
            try:
                sample_queue.put_nowait((samples.copy(), center_freq))
            except queue.Full:
                # 队列满则丢弃最旧的样本
                try:
                    sample_queue.get_nowait()
                    sample_queue.put_nowait((samples.copy(), center_freq))
                except:
                    pass
            
            # 3. 发送频谱数据
            if manager.active_connections:
                spectrum_data = {
                    "type": "spectrum",
                    "device_id": device_id,
                    "frequencies": spectrum.frequencies[::10],
                    "power": spectrum.power_db[::10],
                    "overflow": getattr(driver, '_rx_overflow', False) if driver else False,
                    "underflow": getattr(driver, '_tx_underflow', False) if driver else False
                }
                asyncio.run_coroutine_threadsafe(
                    manager.broadcast(json.dumps(spectrum_data)), 
                    MAIN_LOOP
                )
        except Exception as e:
            print(f"Processing error for {device_id}: {e}")
            
    return callback


def stop_demod_worker(device_id: str):
    """停止指定设备的解调工作线程"""
    if device_id in _demod_workers:
        worker_info = _demod_workers[device_id]
        print(f"[DEBUG] Stopping demod worker for {device_id}")
        worker_info['stop_event'].set()
        if worker_info['thread'].is_alive():
            worker_info['thread'].join(timeout=1.0)
        del _demod_workers[device_id]
        print(f"[DEBUG] Demod worker stopped for {device_id}")

async def handle_command(command: dict) -> dict:
    cmd = command.get("cmd", "")
    params = command.get("params", {})
    sdr_manager = get_sdr_manager()
    
    response = {"cmd": cmd, "success": False, "data": None, "error": None}
    
    try:
        if cmd == "scan_devices":
            devices = sdr_manager.scan_devices()
            response["data"] = [{"id": d.id, "name": d.name, "uri": d.uri, 
                                 "serial": d.serial, "mac": d.mac,
                                 "is_available": d.is_available} for d in devices]
            response["success"] = True
            
        elif cmd == "connect_device":
            device_id = params.get("device_id")
            if device_id:
                response["success"] = sdr_manager.connect_device(device_id)
            else:
                response["error"] = "缺少 device_id"
                
        elif cmd == "disconnect_device":
            device_id = params.get("device_id")
            if device_id:
                sdr_manager.disconnect_device(device_id)
                response["success"] = True
            else:
                response["error"] = "缺少 device_id"
                
        elif cmd == "get_status":
            response["data"] = sdr_system.driver.get_status() if sdr_system.driver else None
            response["success"] = True
            
        elif cmd == "configure_device":
            device_id = params.get("device_id")
            rx_config = params.get("rx_config")
            tx_config = params.get("tx_config")
            if device_id:
                response["success"] = sdr_manager.configure_device(device_id, rx_config, tx_config)
            else:
                response["error"] = "缺少 device_id"

        elif cmd == "enable_tx":
            device_id = params.get("device_id")
            if device_id:
                driver = sdr_manager.get_device(device_id)
                if driver:
                    driver.enable_tx()
                    response["success"] = True
                else:
                    response["error"] = "设备未找到"
            else:
                response["error"] = "缺少 device_id"
                
        elif cmd == "disable_tx":
            device_id = params.get("device_id")
            if device_id:
                driver = sdr_manager.get_device(device_id)
                if driver:
                    driver.disable_tx()
                    response["success"] = True
                else:
                    response["error"] = "设备未找到"
            else:
                response["error"] = "缺少 device_id"

        elif cmd == "start_tx_signal":
            device_id = params.get("device_id")
            signal_type = params.get("signal_type")
            payload = params.get("payload")
            if device_id and signal_type:
                success, preview_data = sdr_manager.start_tx_signal(device_id, signal_type, payload)
                response["success"] = success
                if preview_data:
                    response["data"] = preview_data
            else:
                response["error"] = "缺少参数"
                
        elif cmd == "stop_tx_signal":
            device_id = params.get("device_id")
            if device_id:
                response["success"] = sdr_manager.stop_tx_signal(device_id)
            else:
                response["error"] = "缺少 device_id"

        elif cmd == "start_streaming":
            device_id = params.get("device_id")
            signal_type = params.get("signal_type", "red_broadcast")  # 默认红方广播
            rx_enabled = params.get("rx_enabled", True)  # 默认启用 RX
            if device_id:
                callback = create_stream_callback(device_id, signal_type, rx_enabled)
                response["success"] = sdr_manager.start_streaming(device_id, callback)
            else:
                response["error"] = "缺少 device_id"

        elif cmd == "stop_streaming":
            device_id = params.get("device_id")
            if device_id:
                # 先停止解调工作线程
                stop_demod_worker(device_id)
                response["success"] = sdr_manager.stop_streaming(device_id)
            else:
                response["error"] = "缺少 device_id"

        else:
            response["error"] = f"未知命令: {cmd}"
            
    except Exception as e:
        response["error"] = str(e)
        
    return response


# ============ FastAPI 应用 ============
@asynccontextmanager
async def lifespan(app: FastAPI):
    global MAIN_LOOP
    MAIN_LOOP = asyncio.get_running_loop()
    # sdr_system.start(loop) # 暂时禁用旧的自动启动，转为手动控制
    yield
    # sdr_system.stop()


app = FastAPI(lifespan=lifespan)


@app.websocket("/ws/sdr")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    print(f"WebSocket client connected, total: {len(manager.active_connections)}")
    
    try:
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=60.0)
            except asyncio.TimeoutError:
                # 发送心跳
                try:
                    await websocket.send_text('{"type":"ping"}')
                except:
                    break
                continue
            
            # 处理 ping
            if data in ('ping', '{"type":"ping"}'):
                await websocket.send_text('{"type":"pong"}')
                continue
            
            # 处理命令
            try:
                command = json.loads(data)
                response = await handle_command(command)
                await manager.send_json(websocket, response)
            except json.JSONDecodeError:
                await manager.send_json(websocket, {"error": "无效的 JSON"})
                
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        manager.disconnect(websocket)
        print(f"WebSocket client disconnected, remaining: {len(manager.active_connections)}")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
