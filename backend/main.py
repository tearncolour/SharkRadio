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

def create_stream_callback(device_id: str):
    """创建特定设备的数据流回调"""
    processor = SignalProcessor(sample_rate=2000000) # 默认 2M，理想情况应从配置获取
    
    def callback(samples: np.ndarray):
        if not MAIN_LOOP:
            return
            
        try:
            # 获取当前中心频率
            sdr_mgr = get_sdr_manager()
            driver = sdr_mgr.get_device(device_id)
            center_freq = 0.0
            
            if driver:
                # 优先使用配置中的中心频率
                center_freq = driver.config.center_freq
            
            spectrum = processor.compute_spectrum(samples, center_freq=center_freq)
            
            if manager.active_connections:
                data = {
                    "type": "spectrum",
                    "device_id": device_id,
                    "frequencies": spectrum.frequencies[::10],
                    "power": spectrum.power_db[::10],
                    "overflow": getattr(driver, '_rx_overflow', False) if driver else False,
                    "underflow": getattr(driver, '_tx_underflow', False) if driver else False
                }
                asyncio.run_coroutine_threadsafe(
                    manager.broadcast(json.dumps(data)), 
                    MAIN_LOOP
                )
        except Exception as e:
            print(f"Processing error for {device_id}: {e}")
            
    return callback

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
                response["success"] = sdr_manager.start_tx_signal(device_id, signal_type, payload)
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
            if device_id:
                callback = create_stream_callback(device_id)
                response["success"] = sdr_manager.start_streaming(device_id, callback)
            else:
                response["error"] = "缺少 device_id"

        elif cmd == "stop_streaming":
            device_id = params.get("device_id")
            if device_id:
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
