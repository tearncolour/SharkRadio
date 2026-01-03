"""
WebSocket Handler
FastAPI + WebSocket for streaming data to frontend
支持多 SDR 设备管理
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import List, Dict, Any
import json
import asyncio

from sdr.sdr_manager import get_sdr_manager, SDRDeviceInfo
from sdr.pluto_driver import PlutoConfig


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
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                pass
            
    async def broadcast_bytes(self, data: bytes):
        for connection in self.active_connections:
            try:
                await connection.send_bytes(data)
            except:
                pass

    async def send_json(self, websocket: WebSocket, data: Dict[str, Any]):
        """发送 JSON 响应"""
        await websocket.send_text(json.dumps(data, ensure_ascii=False))


manager = ConnectionManager()
app = FastAPI()


def device_info_to_dict(device: SDRDeviceInfo) -> dict:
    """将 SDRDeviceInfo 转换为 dict"""
    return {
        "id": device.id,
        "name": device.name,
        "uri": device.uri,
        "serial": device.serial,
        "product": device.product,
        "is_available": device.is_available
    }


async def handle_command(websocket: WebSocket, command: dict) -> dict:
    """
    处理 WebSocket 命令
    
    支持的命令:
    - scan_devices: 扫描可用设备
    - connect_device: 连接设备
    - disconnect_device: 断开设备
    - select_device: 选择活动设备
    - configure_device: 配置设备参数
    - get_device_status: 获取设备状态
    - get_connected_devices: 获取已连接设备列表
    """
    cmd = command.get("cmd", "")
    params = command.get("params", {})
    sdr_manager = get_sdr_manager()
    
    response = {"cmd": cmd, "success": False, "data": None, "error": None}
    
    try:
        if cmd == "scan_devices":
            # 扫描可用设备
            devices = sdr_manager.scan_devices()
            response["data"] = [device_info_to_dict(d) for d in devices]
            response["success"] = True
            
        elif cmd == "connect_device":
            # 连接设备
            device_id = params.get("device_id")
            if not device_id:
                response["error"] = "缺少 device_id 参数"
            else:
                config = None
                if "config" in params:
                    config = PlutoConfig(**params["config"])
                success = sdr_manager.connect_device(device_id, config)
                response["success"] = success
                if not success:
                    response["error"] = f"连接设备 {device_id} 失败"
                    
        elif cmd == "disconnect_device":
            # 断开设备
            device_id = params.get("device_id")
            if device_id:
                sdr_manager.disconnect_device(device_id)
                response["success"] = True
            else:
                response["error"] = "缺少 device_id 参数"
                
        elif cmd == "select_device":
            # 选择活动设备
            device_id = params.get("device_id")
            if device_id:
                response["success"] = sdr_manager.set_active_device(device_id)
                if not response["success"]:
                    response["error"] = f"设备 {device_id} 未连接"
            else:
                response["error"] = "缺少 device_id 参数"
                
        elif cmd == "configure_device":
            # 配置设备
            device_id = params.get("device_id")
            rx_config = params.get("rx_config")
            tx_config = params.get("tx_config")
            
            if device_id:
                response["success"] = sdr_manager.configure_device(
                    device_id, rx_config, tx_config
                )
                if not response["success"]:
                    response["error"] = f"配置设备 {device_id} 失败"
            else:
                response["error"] = "缺少 device_id 参数"
                
        elif cmd == "get_device_status":
            # 获取设备状态
            device_id = params.get("device_id")
            driver = sdr_manager.get_device(device_id) if device_id else sdr_manager.get_active_device()
            
            if driver:
                response["data"] = driver.get_status()
                response["success"] = True
            else:
                response["error"] = "设备未连接"
                
        elif cmd == "get_connected_devices":
            # 获取已连接设备列表
            devices = sdr_manager.get_connected_devices()
            response["data"] = [device_info_to_dict(d) for d in devices]
            response["success"] = True
            
        elif cmd == "start_streaming":
            # 开始流式接收
            device_id = params.get("device_id")
            driver = sdr_manager.get_device(device_id) if device_id else sdr_manager.get_active_device()
            
            if driver:
                # 注意: 实际的流式回调需要在 main.py 中设置
                response["data"] = {"message": "请通过 main.py 设置流式回调"}
                response["success"] = True
            else:
                response["error"] = "设备未连接"
                
        elif cmd == "stop_streaming":
            # 停止流式接收
            device_id = params.get("device_id")
            driver = sdr_manager.get_device(device_id) if device_id else sdr_manager.get_active_device()
            
            if driver:
                driver.stop_streaming()
                response["success"] = True
            else:
                response["error"] = "设备未连接"
                
        elif cmd == "enable_tx":
            # 启用发射
            device_id = params.get("device_id")
            driver = sdr_manager.get_device(device_id) if device_id else sdr_manager.get_active_device()
            
            if driver:
                driver.enable_tx()
                response["success"] = True
            else:
                response["error"] = "设备未连接"
                
        elif cmd == "disable_tx":
            # 禁用发射
            device_id = params.get("device_id")
            driver = sdr_manager.get_device(device_id) if device_id else sdr_manager.get_active_device()
            
            if driver:
                driver.disable_tx()
                response["success"] = True
            else:
                response["error"] = "设备未连接"
                
        else:
            response["error"] = f"未知命令: {cmd}"
            
    except Exception as e:
        response["error"] = str(e)
        
    return response


@app.websocket("/ws/sdr")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # 接收命令或 ping
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
            except asyncio.TimeoutError:
                # 发送心跳保持连接
                await websocket.send_text('{"type": "ping"}')
                continue
            
            # 处理 ping
            if data == 'ping' or data == '{"type":"ping"}':
                await websocket.send_text('{"type": "pong"}')
                continue
            
            try:
                command = json.loads(data)
                response = await handle_command(websocket, command)
                await manager.send_json(websocket, response)
            except json.JSONDecodeError:
                await manager.send_json(websocket, {
                    "error": "无效的 JSON 格式"
                })
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket)

